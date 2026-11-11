#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 1: Thread-Level Search Forensics Instrumentation & Benchmark
Builds an instrumented X11 engine, executes thread-level forensics across 1T, 2T, 4T,
and measures TT contention, shallower overwrites, worker depths, and move stability.
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
FORENSICS_CPP = TEST_DIR / "forensics_engine.cpp"
FORENSICS_EXE = TEST_DIR / "forensics_engine.exe"
RAW_OUT = P17_DIR / "raw" / "thread_forensics_raw.json"
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

def generate_instrumented_code():
    with open(BASE_CPP, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Add Telemetry Structs
    target_cluster = "struct alignas(64) TTCluster {"
    telemetry_structs = """
struct TTTelemetry {
    std::atomic<uint64_t> probes{0};
    std::atomic<uint64_t> hits{0};
    std::atomic<uint64_t> cutoffs{0};
    std::atomic<uint64_t> stores{0};
    std::atomic<uint64_t> same_key_overwrites{0};
    std::atomic<uint64_t> shallower_overwrites{0};
    std::atomic<uint64_t> cross_key_evictions{0};
    std::atomic<uint64_t> lock_spins{0};

    void reset() {
        probes.store(0);
        hits.store(0);
        cutoffs.store(0);
        stores.store(0);
        same_key_overwrites.store(0);
        shallower_overwrites.store(0);
        cross_key_evictions.store(0);
        lock_spins.store(0);
    }
};

static TTTelemetry g_tt_telemetry;
EXPORT void native_move_to_uci(uint16_t m, char* out_str);

struct alignas(64) TTCluster {"""
    assert target_cluster in code, "Target cluster not found"
    code = code.replace(target_cluster, telemetry_structs, 1)

    # 2. Hook probe in ParallelTranspositionTable
    old_probe_lock = """        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }"""
    new_probe_lock = """        g_tt_telemetry.probes.fetch_add(1, std::memory_order_relaxed);
        while (c.lock.test_and_set(std::memory_order_acquire)) {
            g_tt_telemetry.lock_spins.fetch_add(1, std::memory_order_relaxed);
            _mm_pause();
        }"""
    assert old_probe_lock in code, "Old probe lock not found"
    code = code.replace(old_probe_lock, new_probe_lock, 1)

    # 3. Hook hits and cutoffs in probe
    old_hit_assign = """                    if (flag == TT_EXACT) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_LOWER && tt_score >= beta) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_UPPER && tt_score <= alpha) {
                        out_score = tt_score;
                        hit = true;
                    }"""
    new_hit_assign = """                    g_tt_telemetry.hits.fetch_add(1, std::memory_order_relaxed);
                    if (flag == TT_EXACT) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_LOWER && tt_score >= beta) {
                        out_score = tt_score;
                        hit = true;
                    } else if (flag == TT_UPPER && tt_score <= alpha) {
                        out_score = tt_score;
                        hit = true;
                    }
                    if (hit) g_tt_telemetry.cutoffs.fetch_add(1, std::memory_order_relaxed);"""
    assert old_hit_assign in code, "Old hit assign not found"
    code = code.replace(old_hit_assign, new_hit_assign, 1)

    # 4. Hook store
    old_store_lock = """        while (c.lock.test_and_set(std::memory_order_acquire)) {
            _mm_pause();
        }

        int replace_idx = -1;
        int lowest_depth = 999;
        int oldest_age_diff = -1;

        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                replace_idx = i;
                break;
            }"""
    new_store_lock = """        g_tt_telemetry.stores.fetch_add(1, std::memory_order_relaxed);
        while (c.lock.test_and_set(std::memory_order_acquire)) {
            g_tt_telemetry.lock_spins.fetch_add(1, std::memory_order_relaxed);
            _mm_pause();
        }

        int replace_idx = -1;
        int lowest_depth = 999;
        int oldest_age_diff = -1;

        for (int i = 0; i < 4; ++i) {
            if (c.entries[i].key == key) {
                replace_idx = i;
                g_tt_telemetry.same_key_overwrites.fetch_add(1, std::memory_order_relaxed);
                if (depth < c.entries[i].depth) {
                    g_tt_telemetry.shallower_overwrites.fetch_add(1, std::memory_order_relaxed);
                }
                break;
            }"""
    assert old_store_lock in code, "Old store lock not found"
    code = code.replace(old_store_lock, new_store_lock, 1)

    # 5. Hook cross key eviction
    old_evict_hook = """        if (replace_idx >= 0) {
            c.entries[replace_idx].key = key;"""
    new_evict_hook = """        if (replace_idx >= 0) {
            if (c.entries[replace_idx].key != 0 && c.entries[replace_idx].key != key) {
                g_tt_telemetry.cross_key_evictions.fetch_add(1, std::memory_order_relaxed);
            }
            c.entries[replace_idx].key = key;"""
    assert old_evict_hook in code, "Old evict hook not found"
    code = code.replace(old_evict_hook, new_evict_hook, 1)

    # 6. Add Worker Forensics printing in native_search
    target_uci_print = 'if (out_res->best_move == 0) {'
    forensics_print = """
    std::cout << "forensics_tt probes=" << g_tt_telemetry.probes.load()
              << " hits=" << g_tt_telemetry.hits.load()
              << " cutoffs=" << g_tt_telemetry.cutoffs.load()
              << " stores=" << g_tt_telemetry.stores.load()
              << " same_key_overwrites=" << g_tt_telemetry.same_key_overwrites.load()
              << " shallower_overwrites=" << g_tt_telemetry.shallower_overwrites.load()
              << " cross_key_evictions=" << g_tt_telemetry.cross_key_evictions.load()
              << " lock_spins=" << g_tt_telemetry.lock_spins.load()
              << std::endl;
    for (int wi = 0; wi < n_threads; ++wi) {
        char wm_str[16] = "-";
        if (w_res[wi].best_move != 0) native_move_to_uci(w_res[wi].best_move, wm_str);
        std::cout << "forensics_worker id=" << wi
                  << " depth=" << w_res[wi].depth
                  << " score=" << w_res[wi].score
                  << " nodes=" << w_res[wi].nodes
                  << " bestmove=" << wm_str
                  << std::endl;
    }

    if (out_res->best_move == 0) {"""
    assert target_uci_print in code, "Target uci print not found"
    code = code.replace(target_uci_print, forensics_print, 1)

    # Reset telemetry at start of search
    target_start_search = "g_stop_search.store(false, std::memory_order_relaxed);"
    new_start_search = "g_stop_search.store(false, std::memory_order_relaxed);\n    g_tt_telemetry.reset();"
    assert target_start_search in code, "Target start search not found"
    code = code.replace(target_start_search, new_start_search, 1)

    with open(FORENSICS_CPP, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Wrote instrumented source to {FORENSICS_CPP} ({len(code):,} bytes)")

def compile_forensics_engine():
    print("[COMPILING] Building forensics_engine.exe...")
    cmd = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc forensics_engine.cpp /Fe:forensics_engine.exe"'
    res = subprocess.run(cmd, cwd=str(TEST_DIR), shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print("BUILD FAILED:\n", res.stdout, res.stderr)
        sys.exit(1)
    print("[COMPILING] forensics_engine.exe built successfully.")

def run_forensics_test(exe_path, fen, movetime_ms, threads):
    cmds = f"uci\nsetoption name Threads value {threads}\nisready\nposition fen {fen}\ngo movetime {movetime_ms}\nquit\n"
    p = subprocess.Popen([str(exe_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate(cmds, timeout=15)
    
    tt_stats = {}
    workers_stats = []
    final_bestmove = None
    final_depth = 0
    final_nodes = 0

    for line in out.splitlines():
        if line.startswith("forensics_tt"):
            tokens = line.split()[1:]
            for tok in tokens:
                k, v = tok.split("=")
                tt_stats[k] = int(v)
        elif line.startswith("forensics_worker"):
            tokens = line.split()[1:]
            w_dict = {}
            for tok in tokens:
                k, v = tok.split("=")
                w_dict[k] = int(v) if k != "bestmove" else v
            workers_stats.append(w_dict)
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                final_bestmove = parts[1]
        elif line.startswith("info depth"):
            import re
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            if m_d: final_depth = int(m_d.group(1))
            if m_n: final_nodes = int(m_n.group(1))

    return {
        "final_bestmove": final_bestmove,
        "final_depth": final_depth,
        "final_nodes": final_nodes,
        "tt": tt_stats,
        "workers": workers_stats
    }

def main():
    generate_instrumented_code()
    compile_forensics_engine()

    time_budgets_ms = [100, 250, 500, 1000]
    thread_counts = [1, 2, 4]

    print("\n=======================================================")
    print("RUNNING THREAD-LEVEL SEARCH FORENSICS BENCHMARK")
    print(f"Positions: {len(DIAGNOSTIC_SUITE)}, Time Budgets: {time_budgets_ms}, Threads: {thread_counts}")
    print("=======================================================")

    results = {}

    for tb in time_budgets_ms:
        results[f"time_{tb}ms"] = {}
        for tc in thread_counts:
            cfg_key = f"threads_{tc}"
            print(f"\n[RUN] Time Budget = {tb} ms | Threads = {tc}")
            pos_results = []
            total_shallower_overwrites = 0
            total_spins = 0
            total_probes = 0
            total_stores = 0

            for pos in DIAGNOSTIC_SUITE:
                res = run_forensics_test(FORENSICS_EXE, pos["fen"], tb, tc)
                res["position_name"] = pos["name"]
                pos_results.append(res)
                
                tt = res.get("tt", {})
                total_shallower_overwrites += tt.get("shallower_overwrites", 0)
                total_spins += tt.get("lock_spins", 0)
                total_probes += tt.get("probes", 0)
                total_stores += tt.get("stores", 0)

            results[f"time_{tb}ms"][cfg_key] = {
                "aggregate_shallower_overwrites": total_shallower_overwrites,
                "aggregate_lock_spins": total_spins,
                "aggregate_probes": total_probes,
                "aggregate_stores": total_stores,
                "positions": pos_results
            }
            print(f"  Aggregates -> Probes: {total_probes:,}, Stores: {total_stores:,}, Shallower Overwrites: {total_shallower_overwrites:,}, Lock Spins: {total_spins:,}")

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Forensics data written to {RAW_OUT}")

if __name__ == "__main__":
    main()
