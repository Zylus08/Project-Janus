#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 2: Shared Transposition Table Isolation Matrix
Evaluates:
  T0: Single-thread baseline (1T)
  T1: Multiple threads with independent Private TTs (4T)
  T2: Shared TT with existing X11 synchronization (4T, reproducible baseline)
  T3: Shared TT with restricted helper writes (4T, depth protection)
  T4: Shared TT with cache-line packed (64B) cluster and smart replacement policy (4T)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
BASE_CPP = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
P17_DIR = ROOT / "analysis" / "phase1" / "p1.7"
TEST_DIR = P17_DIR / "tests"
RAW_OUT = P17_DIR / "raw" / "tt_isolation_raw.json"
VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

DIAGNOSTIC_SUITE = [
    {"name": "startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"name": "kiwipete", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"},
    {"name": "pos3_endgame", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"},
    {"name": "sharp_sicilian", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6"},
    {"name": "closed_french", "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8"},
    {"name": "king_safety_sharp", "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15"},
    {"name": "opposite_bishops", "fen": "8/4b3/8/2k5/8/8/4B3/4K3 w - - 0 1"},
    {"name": "rook_endgame", "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40"},
    {"name": "scholars_mate", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"},
    {"name": "legals_mate", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9"}
]

# We will create an engine variant generator that can be compiled with different TT modes
# Mode 0: T0 / T2 (original)
# Mode 1: T1 (Private TT per thread)
# Mode 3: T3 (Restricted helper writes - depth protection)
# Mode 4: T4 (Packed 64-byte cluster, 3 entries, smart replacement)

def generate_variant_source(variant_mode: str, output_path: Path):
    with open(BASE_CPP, "r", encoding="utf-8") as f:
        code = f.read()

    # Forward decl before TTCluster
    code = code.replace("struct alignas(64) TTCluster {", "EXPORT void native_move_to_uci(uint16_t m, char* out_str);\nextern thread_local int t_thread_id;\nstruct alignas(64) TTCluster {", 1)

    if variant_mode == "T1": # Private TT per thread
        # Replace g_parallel_tt with thread_local private TT
        target_tt = """class ParallelTranspositionTable {"""
        new_tt = """
constexpr size_t PRIVATE_TT_SIZE = 262144; // 262,144 entries = 4 MB per thread
struct PrivateTT {
    TTEntry entries[PRIVATE_TT_SIZE];
    uint8_t current_age{0};
    void clear() { std::memset(entries, 0, sizeof(entries)); }
    bool probe(uint64_t key, int depth, int ply, int alpha, int beta, int& out_score, uint16_t& out_move, bool allow_cutoff) {
        size_t idx = (key ^ (key >> 32)) % PRIVATE_TT_SIZE;
        TTEntry& e = entries[idx];
        if (e.key == key) {
            out_move = e.best_move;
            if (allow_cutoff && e.depth >= depth) {
                int tt_score = score_from_tt(e.score, ply);
                if (e.flag == TT_EXACT) { out_score = tt_score; return true; }
                if (e.flag == TT_LOWER && tt_score >= beta) { out_score = tt_score; return true; }
                if (e.flag == TT_UPPER && tt_score <= alpha) { out_score = tt_score; return true; }
            }
        }
        return false;
    }
    void store(uint64_t key, int score, int8_t depth, uint8_t flag, int ply, uint16_t best_move) {
        size_t idx = (key ^ (key >> 32)) % PRIVATE_TT_SIZE;
        TTEntry& e = entries[idx];
        if (e.key == key && depth < e.depth && e.age == current_age) return;
        e.key = key;
        e.score = score_to_tt(score, ply);
        e.depth = depth;
        e.flag = flag;
        e.age = current_age;
        if (best_move != 0 || e.best_move == 0) e.best_move = best_move;
    }
};
thread_local PrivateTT t_private_tt;

class ParallelTranspositionTable {"""
        code = code.replace(target_tt, new_tt, 1)

        # In probe and store calls in negamax, use t_private_tt
        code = code.replace("g_parallel_tt.probe(", "t_private_tt.probe(", 1)
        code = code.replace("g_parallel_tt.store(", "t_private_tt.store(", 1)

    elif variant_mode == "T3": # Restricted Helper Writes
        old_store = """    void store(uint64_t key, int score, int8_t depth, uint8_t flag, int ply, uint16_t best_move) {"""
        new_store = """    void store(uint64_t key, int score, int8_t depth, uint8_t flag, int ply, uint16_t best_move) {
        // T3 Policy: If helper thread (t_thread_id > 0), only allow store if depth >= 4 and not aborted
        if (t_thread_id > 0 && depth < 4) return;"""
        code = code.replace(old_store, new_store, 1)

        # Also add depth protection on same key
        old_same_key = """            if (c.entries[i].key == key) {
                replace_idx = i;
                break;
            }"""
        new_same_key = """            if (c.entries[i].key == key) {
                // If same key, do not overwrite if new depth is shallower than existing depth!
                if (depth < c.entries[i].depth && age == c.entries[i].age) {
                    // Only update best_move if existing has none
                    if (c.entries[i].best_move == 0 && best_move != 0) {
                        c.entries[i].best_move = best_move;
                    }
                    c.lock.clear(std::memory_order_release);
                    return;
                }
                replace_idx = i;
                break;
            }"""
        code = code.replace(old_same_key, new_same_key, 1)

    elif variant_mode == "T4": # Packed 64-byte cluster, 3 entries, smart replacement
        target_cluster = """struct alignas(64) TTCluster {
    std::atomic_flag lock;
    TTEntry entries[4];
};

constexpr size_t NUM_TT_CLUSTERS = 262144; // 1,048,576 entries (32 MB)"""

        new_cluster = """struct alignas(64) TTCluster {
    std::atomic_flag lock;
    uint8_t pad[4];
    TTEntry entries[3]; // Exactly 4 + 4 + 48 = 56 bytes <= 64 bytes! Fits in 1 cache line!
    uint8_t tail_pad[8];
};

constexpr size_t NUM_TT_CLUSTERS = 524288; // 524,288 * 64B = exactly 33,554,432 bytes (32 MB)! 1,572,864 entries!"""
        assert target_cluster in code, "Target cluster not found"
        code = code.replace(target_cluster, new_cluster, 1)

        # Replace probe loop for 3 entries
        code = code.replace("for (int i = 0; i < 4; ++i) {", "for (int i = 0; i < 3; ++i) {", 2)

        # Replace store replacement logic
        old_store_logic = """        for (int i = 0; i < 3; ++i) {
            if (c.entries[i].key == key) {
                replace_idx = i;
                break;
            }
            if (c.entries[i].key == 0) {
                replace_idx = i;
                break;
            }
            int age_diff = (int)age - (int)c.entries[i].age;
            if (age_diff > oldest_age_diff) {
                oldest_age_diff = age_diff;
                replace_idx = i;
            } else if (age_diff == oldest_age_diff && c.entries[i].depth < lowest_depth) {
                lowest_depth = c.entries[i].depth;
                replace_idx = i;
            }
        }"""
        new_store_logic = """        for (int i = 0; i < 3; ++i) {
            if (c.entries[i].key == key) {
                // If same key, preserve deep entry unless new is deeper or exact
                if (depth < c.entries[i].depth && age == c.entries[i].age && flag != TT_EXACT) {
                    if (c.entries[i].best_move == 0 && best_move != 0) {
                        c.entries[i].best_move = best_move;
                    }
                    c.lock.clear(std::memory_order_release);
                    return;
                }
                replace_idx = i;
                break;
            }
            if (c.entries[i].key == 0) {
                replace_idx = i;
                break;
            }
            int age_diff = (int)age - (int)c.entries[i].age;
            int score_cand = (age_diff * 8) - (int)c.entries[i].depth;
            if (score_cand > oldest_age_diff) {
                oldest_age_diff = score_cand;
                replace_idx = i;
            }
        }"""
        assert old_store_logic in code, "Old store logic not found"
        code = code.replace(old_store_logic, new_store_logic, 1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Generated {output_path} ({len(code):,} bytes)")

def compile_engine(cpp_path: Path, exe_path: Path):
    cmd = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc {cpp_path.name} /Fe:{exe_path.name}"'
    res = subprocess.run(cmd, cwd=str(cpp_path.parent), shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED TO COMPILE {cpp_path.name}:\n", res.stdout, res.stderr)
        sys.exit(1)
    print(f"Successfully compiled {exe_path.name}")

def run_uci_benchmark(exe_path, fen, movetime_ms=500, threads=4):
    cmds = f"uci\nsetoption name Threads value {threads}\nisready\nposition fen {fen}\ngo movetime {movetime_ms}\nquit\n"
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate(cmds, timeout=10)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None
    score = 0
    for line in out.splitlines():
        if line.startswith("info depth"):
            import re
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score = int(m_s.group(1))
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    return {
        "bestmove": bestmove,
        "depth": depth,
        "nodes": nodes,
        "score": score,
        "elapsed_sec": round(dur, 4)
    }

def main():
    print("==================================================================")
    print("PHASE 2: SHARED TRANSPOSITION TABLE ISOLATION MATRIX")
    print("==================================================================")

    variants = [
        {"id": "T0", "name": "T0: Single-Thread Baseline (1T)", "mode": "T0", "threads": 1},
        {"id": "T1", "name": "T1: Independent Private TTs (4T)", "mode": "T1", "threads": 4},
        {"id": "T2", "name": "T2: Existing X11 Shared TT (4T)", "mode": "T0", "threads": 4},
        {"id": "T3", "name": "T3: Restricted Helper Writes (4T)", "mode": "T3", "threads": 4},
        {"id": "T4", "name": "T4: 64B Cache-Packed Cluster + Smart Replacement (4T)", "mode": "T4", "threads": 4}
    ]

    built_exes = {}

    for v in variants:
        v_mode = v["mode"]
        if v_mode not in built_exes:
            cpp_path = TEST_DIR / f"engine_{v_mode.lower()}.cpp"
            exe_path = TEST_DIR / f"engine_{v_mode.lower()}.exe"
            generate_variant_source(v_mode, cpp_path)
            compile_engine(cpp_path, exe_path)
            built_exes[v_mode] = exe_path
        v["exe"] = built_exes[v_mode]

    # Run benchmark across 10 positions at 500 ms movetime
    MOVETIME = 500
    results = {}

    for v in variants:
        vid = v["id"]
        vname = v["name"]
        print(f"\n[RUNNING] {vname} across 10 diagnostic positions (movetime={MOVETIME}ms)...")
        tot_nodes = 0
        tot_depth = 0
        tot_time = 0.0
        pos_details = []

        for p in DIAGNOSTIC_SUITE:
            res = run_uci_benchmark(v["exe"], p["fen"], movetime_ms=MOVETIME, threads=v["threads"])
            res["position"] = p["name"]
            pos_details.append(res)
            tot_nodes += res["nodes"]
            tot_depth += res["depth"]
            tot_time += res["elapsed_sec"]

        avg_depth = round(tot_depth / len(DIAGNOSTIC_SUITE), 2)
        nps = int(tot_nodes / tot_time) if tot_time > 0 else 0
        results[vid] = {
            "name": vname,
            "threads": v["threads"],
            "total_nodes": tot_nodes,
            "total_elapsed_sec": round(tot_time, 3),
            "avg_depth": avg_depth,
            "nps": nps,
            "positions": pos_details
        }
        print(f"  Summary -> Nodes: {tot_nodes:,}, Depth: {avg_depth}, NPS: {nps:,}")

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] TT Isolation Matrix saved to {RAW_OUT}")

    print("\n" + "=" * 95)
    print(f"{'Variant ID & Name':<50} | {'Thr':<3} | {'Avg Depth':<9} | {'Nodes':<10} | {'NPS':<10}")
    print("-" * 95)
    for vid, r in results.items():
        print(f"{r['name']:<50} | {r['threads']:<3} | {r['avg_depth']:<9} | {r['total_nodes']:<10,d} | {r['nps']:<10,d}")
    print("=" * 95)

if __name__ == "__main__":
    main()

