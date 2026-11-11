#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 3: Helper Worker Search Quality & Cooperation Matrix
Tests:
  W0: Historical X11 worker strategy (Worker 2 starts d=2, wide aspiration, blank helper history)
  W1: Warm History Inheritance (helpers inherit master thread history at root)
  W2: Canonical Root Move Diversification (all workers start at d=1, root move ordering staggered)
  W3: Combined W1 + W2 with T4 Packed Transposition Table
  W4: Selective Worker Participation (fast-clock gating for budgets < 150ms)
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
RAW_OUT = P17_DIR / "raw" / "worker_cooperation_raw.json"
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

def generate_worker_variant_source(variant_id: str, output_path: Path):
    with open(BASE_CPP, "r", encoding="utf-8") as f:
        code = f.read()

    # Forward decl before TTCluster
    code = code.replace("struct alignas(64) TTCluster {", "EXPORT void native_move_to_uci(uint16_t m, char* out_str);\nextern thread_local int t_thread_id;\nstruct alignas(64) TTCluster {", 1)

    # Always add Master History Storage so master history can be copied
    old_hist_decl = "thread_local int g_history_table[SIDES][SQUARES][SQUARES];"
    new_hist_decl = "thread_local int g_history_table[SIDES][SQUARES][SQUARES];\nstatic int g_master_history_table[SIDES][SQUARES][SQUARES];"
    code = code.replace(old_hist_decl, new_hist_decl, 1)

    if variant_id in ["W1", "W3", "W4"]:
        # Warm history copy in run_worker_search
        old_worker_init = """    g_game_history_len = g_master_game_history_len;
    for (int i = 0; i < g_master_game_history_len; ++i) {
        g_game_history[i] = g_master_game_history[i];
    }
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));"""
        new_worker_init = """    g_game_history_len = g_master_game_history_len;
    for (int i = 0; i < g_master_game_history_len; ++i) {
        g_game_history[i] = g_master_game_history[i];
    }
    if (thread_id > 0) {
        std::memcpy(g_history_table, g_master_history_table, sizeof(g_history_table));
    }
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));"""
        code = code.replace(old_worker_init, new_worker_init, 1)

        # In native_search, master thread copies its history to g_master_history_table before launching helpers
        old_master_hist_prep = """    g_master_game_history_len = g_game_history_len;
    for (int i = 0; i < g_game_history_len; ++i) {
        g_master_game_history[i] = g_game_history[i];
    }"""
        new_master_hist_prep = """    g_master_game_history_len = g_game_history_len;
    for (int i = 0; i < g_game_history_len; ++i) {
        g_master_game_history[i] = g_game_history[i];
    }
    std::memcpy(g_master_history_table, g_history_table, sizeof(g_history_table));"""
        code = code.replace(old_master_hist_prep, new_master_hist_prep, 1)

    if variant_id in ["W2", "W3", "W4"]:
        # Fix depth staggering: all workers start at depth 1!
        code = code.replace("int start_depth = (thread_id == 2) ? 2 : 1;", "int start_depth = 1;", 1)
        # Standardize aspiration window
        code = code.replace("int asp_delta = (thread_id == 1) ? (g_aspiration_delta * 2) : g_aspiration_delta;", "int asp_delta = g_aspiration_delta;", 1)

    if variant_id in ["W3", "W4"]:
        # Use T4 packed 64-byte TT
        target_cluster = """struct alignas(64) TTCluster {
    std::atomic_flag lock;
    TTEntry entries[4];
};

constexpr size_t NUM_TT_CLUSTERS = 262144; // 1,048,576 entries (32 MB)"""

        new_cluster = """struct alignas(64) TTCluster {
    std::atomic_flag lock;
    uint8_t pad[4];
    TTEntry entries[3];
    uint8_t tail_pad[8];
};

constexpr size_t NUM_TT_CLUSTERS = 524288;"""
        code = code.replace(target_cluster, new_cluster, 1)
        code = code.replace("for (int i = 0; i < 4; ++i) {", "for (int i = 0; i < 3; ++i) {", 2)

        # Smart replacement logic
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
        code = code.replace(old_store_logic, new_store_logic, 1)

    if variant_id == "W4":
        # Fast clock gating: if time_limit_sec < 0.15, force single thread
        target_threads = "int n_threads = std::max(1, g_num_threads);"
        new_threads = """int n_threads = std::max(1, g_num_threads);
    if (time_limit_sec < 0.150) {
        n_threads = 1;
    }"""
        code = code.replace(target_threads, new_threads, 1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Generated {output_path} ({len(code):,} bytes)")

def compile_variant(cpp_path: Path, exe_path: Path):
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
    print("PHASE 3: HELPER WORKER SEARCH QUALITY & COOPERATION MATRIX")
    print("==================================================================")

    variants = [
        {"id": "W0", "name": "W0: Historical X11 Worker Strategy (4T)"},
        {"id": "W1", "name": "W1: Warm History Inheritance (4T)"},
        {"id": "W2", "name": "W2: Canonical Depth-1 Start (No Stagger Skip) (4T)"},
        {"id": "W3", "name": "W3: Warm History + Depth-1 + T4 Packed TT (4T)"},
        {"id": "W4", "name": "W4: W3 + Fast-Clock Gating (<150ms 1T fallback) (4T)"}
    ]

    for v in variants:
        vid = v["id"]
        cpp_path = TEST_DIR / f"engine_{vid.lower()}.cpp"
        exe_path = TEST_DIR / f"engine_{vid.lower()}.exe"
        generate_worker_variant_source(vid, cpp_path)
        compile_variant(cpp_path, exe_path)
        v["exe"] = exe_path

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
            res = run_uci_benchmark(v["exe"], p["fen"], movetime_ms=MOVETIME, threads=4)
            res["position"] = p["name"]
            pos_details.append(res)
            tot_nodes += res["nodes"]
            tot_depth += res["depth"]
            tot_time += res["elapsed_sec"]

        avg_depth = round(tot_depth / len(DIAGNOSTIC_SUITE), 2)
        nps = int(tot_nodes / tot_time) if tot_time > 0 else 0
        results[vid] = {
            "name": vname,
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

    print(f"\n[COMPLETE] Worker Cooperation Matrix saved to {RAW_OUT}")
    print("\n" + "=" * 90)
    print(f"{'Variant ID & Name':<55} | {'Avg Depth':<9} | {'Nodes':<10} | {'NPS':<10}")
    print("-" * 90)
    for vid, r in results.items():
        print(f"{r['name']:<55} | {r['avg_depth']:<9} | {r['total_nodes']:<10,d} | {r['nps']:<10,d}")
    print("=" * 90)

if __name__ == "__main__":
    main()

