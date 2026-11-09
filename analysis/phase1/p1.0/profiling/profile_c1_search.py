#!/usr/bin/env python3
"""
Project Janus Phase 1 — Milestone P1.0
C1 Search Profiler & Instrumentation Pipeline (Updated).

Instruments Classical C1 without modifying frozen baseline binary.
Measures:
  - Total nodes & quiescence nodes
  - TT hit rate & TT cutoff rate
  - Beta-cutoff counts & first-move cutoff rate
  - Move generation cost (time & call counts)
  - Static evaluation call frequency & cost
  - Maximum selective depth
  - Effective branching factor
  - Nodes per second (NPS)
  - Ordering cutoffs breakdown (TT move, Killer 1, Killer 2, History, Captures, Quiets)
  - Function time breakdown
  - Instrumentation measurement overhead vs frozen C1 baseline
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
C1_SRC = ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp"
C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
PROF_DIR = ROOT / "analysis" / "phase1" / "p1.0" / "profiling"
PROF_CPP = PROF_DIR / "janus_profile.cpp"
PROF_EXE = PROF_DIR / "janus_profile_engine.exe"

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

BENCHMARK_POSITIONS = [
    {
        "id": "POS_01_STARTPOS",
        "category": "Opening",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    },
    {
        "id": "POS_02_ITALIAN",
        "category": "Opening",
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5"
    },
    {
        "id": "POS_03_SICILIAN_NAJDORF",
        "category": "Opening",
        "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6"
    },
    {
        "id": "POS_04_TACTICAL_MIDDLEGAME",
        "category": "Middlegame",
        "fen": "r1b2rk1/pp1nbppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 3 10"
    },
    {
        "id": "POS_05_COMPLEX_TACTIC",
        "category": "Middlegame",
        "fen": "r2q1rk1/1pp1bppp/p1np1nb1/4p3/B3P1P1/2PP1N1P/PP3P2/RNBQR1K1 w - - 1 11"
    },
    {
        "id": "POS_06_CLOSED_KING_SAFETY",
        "category": "Middlegame",
        "fen": "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1BN2/PP2BPPP/R2Q1RK1 w - - 0 10"
    },
    {
        "id": "POS_07_ROOK_ENDGAME",
        "category": "Endgame",
        "fen": "8/5pk1/4p1p1/7p/7P/4r1P1/R4PK1/8 b - - 1 42"
    },
    {
        "id": "POS_08_QUEENLESS_MIDDLEGAME",
        "category": "Endgame",
        "fen": "r4rk1/pp3ppp/2n1p3/3p4/3P4/2N2B2/PPP2PPP/R4RK1 w - - 0 14"
    },
    {
        "id": "POS_09_MINOR_PIECE_ENDGAME",
        "category": "Endgame",
        "fen": "8/8/4k3/3p4/3K4/5B2/8/8 w - - 0 1"
    },
    {
        "id": "POS_10_PURE_PAWN_RACE",
        "category": "Endgame",
        "fen": "8/pk6/8/8/8/8/6KP/8 w - - 0 1"
    }
]

def build_profile_engine():
    print("[PROFILER] Generating instrumented source from C1...")
    with open(C1_SRC, "r", encoding="utf-8") as f:
        code = f.read()

    telemetry_decl = """
// ============================================================================
// Janus Search Profiler Telemetry Counters (Phase 1 P1.0)
// ============================================================================
struct SearchProfilerTelemetry {
    uint64_t total_nodes = 0;
    uint64_t qnodes = 0;
    uint64_t tt_probes = 0;
    uint64_t tt_hits = 0;
    uint64_t tt_cutoffs = 0;
    uint64_t eval_calls = 0;
    int max_seldepth = 0;
    uint64_t movegen_time_ns = 0;
    uint64_t eval_time_ns = 0;
};

static SearchProfilerTelemetry g_prof;
"""
    # Insert telemetry struct right after globals
    code = code.replace("static uint64_t g_pvs_full_window_searches = 0;",
                        "static uint64_t g_pvs_full_window_searches = 0;\n" + telemetry_decl)

    # Instrument native_evaluate
    eval_hook = """EXPORT int native_evaluate(const NativeBoard* b) {
    g_prof.eval_calls++;
    auto t_start = std::chrono::high_resolution_clock::now();
"""
    eval_end_hook = """    auto t_dur = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now() - t_start).count();
    g_prof.eval_time_ns += t_dur;
    return (b->side_to_move == WHITE) ? score : -score;
}"""
    code = code.replace("EXPORT int native_evaluate(const NativeBoard* b) {", eval_hook)
    code = code.replace("return (b->side_to_move == WHITE) ? score : -score;\n}", eval_end_hook)

    # Instrument TT probe & cutoffs in negamax
    old_tt_probe = """    // TT Probe
    uint64_t key = b->zobrist_key;
    size_t tt_idx = key % TT_SIZE;
    TTEntry& entry = g_tt[tt_idx];
    uint16_t tt_move = 0;

    if (entry.key == key) {
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }"""

    new_tt_probe = """    // TT Probe (Instrumented)
    g_prof.tt_probes++;
    uint64_t key = b->zobrist_key;
    size_t tt_idx = key % TT_SIZE;
    TTEntry& entry = g_tt[tt_idx];
    uint16_t tt_move = 0;

    if (entry.key == key) {
        g_prof.tt_hits++;
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) { g_prof.tt_cutoffs++; return tt_score; }
            if (entry.flag == TT_LOWER && tt_score >= beta) { g_prof.tt_cutoffs++; return tt_score; }
            if (entry.flag == TT_UPPER && tt_score <= alpha) { g_prof.tt_cutoffs++; return tt_score; }
        }
    }"""
    assert old_tt_probe in code, "old_tt_probe not found"
    code = code.replace(old_tt_probe, new_tt_probe)

    # Instrument quiescence calls & seldepth
    code = code.replace("static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {",
                        "static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted, int ply = 0) {\n    g_prof.qnodes++;\n    if (ply > g_prof.max_seldepth) g_prof.max_seldepth = ply;")

    code = code.replace("int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted);",
                        "int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted, ply + 1);")

    code = code.replace("return quiescence(b, alpha, beta, nodes, deadline, aborted);",
                        "return quiescence(b, alpha, beta, nodes, deadline, aborted, ply);")

    # Instrument movegen in negamax
    old_movegen = """    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);"""
    new_movegen = """    auto mg_start = std::chrono::high_resolution_clock::now();
    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    g_prof.movegen_time_ns += std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now() - mg_start).count();"""
    assert old_movegen in code, "old_movegen not found"
    code = code.replace(old_movegen, new_movegen)

    # Add UCI profiler output command
    code = code.replace(
        'std::cout << "id name Janus 0.56 Native (N7 Candidate)" << std::endl;',
        'std::cout << "id name Janus Search Profiler Engine (Phase 1)" << std::endl;'
    )

    prof_cmd = """
        } else if (cmd == "profile_report") {
            std::cout << "PROF_START" << std::endl;
            std::cout << "total_nodes " << g_prof.total_nodes << std::endl;
            std::cout << "qnodes " << g_prof.qnodes << std::endl;
            std::cout << "tt_probes " << g_prof.tt_probes << std::endl;
            std::cout << "tt_hits " << g_prof.tt_hits << std::endl;
            std::cout << "tt_cutoffs " << g_prof.tt_cutoffs << std::endl;
            std::cout << "total_cutoffs " << g_ordering_total_cutoffs << std::endl;
            std::cout << "cutoff_move_1 " << g_ordering_cutoff_move_1 << std::endl;
            std::cout << "cutoff_move_2 " << g_ordering_cutoff_move_2 << std::endl;
            std::cout << "cutoff_move_3 " << g_ordering_cutoff_move_3 << std::endl;
            std::cout << "cutoff_move_4plus " << g_ordering_cutoff_move_4plus << std::endl;
            std::cout << "cutoff_tt " << g_ordering_cutoff_tt << std::endl;
            std::cout << "cutoff_killer1 " << g_ordering_cutoff_killer1 << std::endl;
            std::cout << "cutoff_killer2 " << g_ordering_cutoff_killer2 << std::endl;
            std::cout << "cutoff_history " << g_ordering_cutoff_history << std::endl;
            std::cout << "cutoff_captures " << g_ordering_cutoff_captures << std::endl;
            std::cout << "cutoff_quiet " << g_ordering_cutoff_quiet << std::endl;
            std::cout << "eval_calls " << g_prof.eval_calls << std::endl;
            std::cout << "max_seldepth " << g_prof.max_seldepth << std::endl;
            std::cout << "movegen_time_ms " << (g_prof.movegen_time_ns / 1000000.0) << std::endl;
            std::cout << "eval_time_ms " << (g_prof.eval_time_ns / 1000000.0) << std::endl;
            std::cout << "PROF_END" << std::endl;
        } else if (cmd == "profile_reset") {
            g_prof = SearchProfilerTelemetry();
            native_reset_ordering_telemetry();
            std::cout << "profile_reset_ok" << std::endl;
"""
    code = code.replace("} else if (cmd == \"ucinewgame\") {", prof_cmd + "        } else if (cmd == \"ucinewgame\") {")

    with open(PROF_CPP, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[PROFILER] Wrote {PROF_CPP} ({len(code):,} bytes).")

    full_cmd = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc janus_profile.cpp /Fe:janus_profile_engine.exe""'
    print("[PROFILER] Compiling janus_profile_engine.exe...")
    res = subprocess.run(full_cmd, cwd=str(PROF_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print("[PROFILER] Build error:\n", res.stderr, res.stdout)
        raise RuntimeError("Failed to build profiler engine")
    print(f"[PROFILER] Build success! Size: {PROF_EXE.stat().st_size:,} bytes")

def run_uci_search(engine_path, fen, depth=7, movetime=None):
    cmd_lines = [
        "uci",
        "isready",
        "ucinewgame",
        f"position fen {fen}",
    ]
    if movetime:
        cmd_lines.append(f"go movetime {movetime}")
    else:
        cmd_lines.append(f"go depth {depth}")
    cmd_lines.append("profile_report")
    cmd_lines.append("quit")
    stdin_input = "\n".join(cmd_lines) + "\n"

    t0 = time.perf_counter()
    p = subprocess.run(
        [str(engine_path)],
        input=stdin_input,
        capture_output=True,
        text=True,
        timeout=30
    )
    t1 = time.perf_counter()

    lines = p.stdout.strip().splitlines()
    bestmove = None
    info_line = None
    prof_data = {}
    is_prof = False

    for line in lines:
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) > 1:
                bestmove = parts[1]
        elif line.startswith("info depth") and "pv" in line:
            info_line = line
        elif line == "PROF_START":
            is_prof = True
        elif line == "PROF_END":
            is_prof = False
        elif is_prof:
            parts = line.split()
            if len(parts) == 2:
                try:
                    prof_data[parts[0]] = float(parts[1]) if "." in parts[1] else int(parts[1])
                except ValueError:
                    prof_data[parts[0]] = parts[1]

    # Parse info line
    nodes = 0
    nps = 0
    score = 0
    completed_depth = 0
    if info_line:
        tokens = info_line.split()
        for i, tok in enumerate(tokens):
            if tok == "depth" and i + 1 < len(tokens):
                completed_depth = int(tokens[i+1])
            elif tok == "nodes" and i + 1 < len(tokens):
                nodes = int(tokens[i+1])
            elif tok == "nps" and i + 1 < len(tokens):
                nps = int(tokens[i+1])
            elif tok == "cp" and i + 1 < len(tokens):
                score = int(tokens[i+1])

    return {
        "bestmove": bestmove,
        "completed_depth": completed_depth,
        "nodes": nodes,
        "nps": nps,
        "score": score,
        "elapsed_wall_sec": round(t1 - t0, 4),
        "telemetry": prof_data
    }

def main():
    build_profile_engine()

    results = {
        "metadata": {
            "milestone": "P1.0",
            "date": "2026-11-09",
            "c1_baseline_exe": str(C1_EXE),
            "profile_exe": str(PROF_EXE),
            "search_depth": 7,
            "num_positions": len(BENCHMARK_POSITIONS)
        },
        "positions": []
    }

    print("\n" + "=" * 80)
    print("RUNNING PROFILING BENCHMARK (10 STANDARDIZED POSITIONS AT DEPTH 7)")
    print("=" * 80)

    total_c1_nodes = 0
    total_c1_time = 0.0
    total_prof_nodes = 0
    total_prof_time = 0.0

    sum_tt_probes = 0
    sum_tt_hits = 0
    sum_tt_cutoffs = 0
    sum_total_cutoffs = 0
    sum_cutoff_m1 = 0
    sum_cutoff_tt = 0
    sum_cutoff_k1 = 0
    sum_cutoff_k2 = 0
    sum_cutoff_hist = 0
    sum_cutoff_caps = 0
    sum_cutoff_quiet = 0

    sum_qnodes = 0
    sum_eval_calls = 0
    sum_movegen_ms = 0.0
    sum_eval_ms = 0.0

    for pos in BENCHMARK_POSITIONS:
        pid = pos["id"]
        cat = pos["category"]
        fen = pos["fen"]

        # Run Frozen C1 Baseline
        c1_res = run_uci_search(C1_EXE, fen, depth=7)
        # Run Instrumented Profile Engine
        prof_res = run_uci_search(PROF_EXE, fen, depth=7)

        total_c1_nodes += c1_res["nodes"]
        total_c1_time += c1_res["elapsed_wall_sec"]
        total_prof_nodes += prof_res["nodes"]
        total_prof_time += prof_res["elapsed_wall_sec"]

        t = prof_res["telemetry"]
        sum_tt_probes += t.get("tt_probes", 0)
        sum_tt_hits += t.get("tt_hits", 0)
        sum_tt_cutoffs += t.get("tt_cutoffs", 0)
        sum_total_cutoffs += t.get("total_cutoffs", 0)
        sum_cutoff_m1 += t.get("cutoff_move_1", 0)
        sum_cutoff_tt += t.get("cutoff_tt", 0)
        sum_cutoff_k1 += t.get("cutoff_killer1", 0)
        sum_cutoff_k2 += t.get("cutoff_killer2", 0)
        sum_cutoff_hist += t.get("cutoff_history", 0)
        sum_cutoff_caps += t.get("cutoff_captures", 0)
        sum_cutoff_quiet += t.get("cutoff_quiet", 0)

        sum_qnodes += t.get("qnodes", 0)
        sum_eval_calls += t.get("eval_calls", 0)
        sum_movegen_ms += t.get("movegen_time_ms", 0.0)
        sum_eval_ms += t.get("eval_time_ms", 0.0)

        tt_hit_rate = (t.get("tt_hits", 0) / t.get("tt_probes", 1)) * 100.0 if t.get("tt_probes", 0) > 0 else 0.0
        first_move_rate = (t.get("cutoff_move_1", 0) / t.get("total_cutoffs", 1)) * 100.0 if t.get("total_cutoffs", 0) > 0 else 0.0
        overhead_pct = ((prof_res["elapsed_wall_sec"] - c1_res["elapsed_wall_sec"]) / max(c1_res["elapsed_wall_sec"], 0.001)) * 100.0

        pos_record = {
            "id": pid,
            "category": cat,
            "fen": fen,
            "c1_baseline": c1_res,
            "profiler": prof_res,
            "metrics": {
                "tt_hit_rate_pct": round(tt_hit_rate, 2),
                "first_move_cutoff_rate_pct": round(first_move_rate, 2),
                "overhead_pct": round(overhead_pct, 2)
            }
        }
        results["positions"].append(pos_record)

        print(f"[{pid}] ({cat})")
        print(f"  C1 Baseline  : nodes={c1_res['nodes']:,} | time={c1_res['elapsed_wall_sec']:.3f}s | nps={c1_res['nps']:,} | move={c1_res['bestmove']}")
        print(f"  Profiled Eng : nodes={prof_res['nodes']:,} | time={prof_res['elapsed_wall_sec']:.3f}s | TT hit={tt_hit_rate:.1f}% | 1st cut={first_move_rate:.1f}% | move={prof_res['bestmove']}")
        print(f"  Overhead     : {overhead_pct:+.2f}%")

    # Overall Summary
    total_tt_hit_rate = (sum_tt_hits / max(sum_tt_probes, 1)) * 100.0
    total_tt_cutoff_rate = (sum_tt_cutoffs / max(sum_tt_probes, 1)) * 100.0
    total_first_move_rate = (sum_cutoff_m1 / max(sum_total_cutoffs, 1)) * 100.0
    qnode_ratio = (sum_qnodes / max(total_prof_nodes, 1)) * 100.0
    total_overhead = ((total_prof_time - total_c1_time) / max(total_c1_time, 0.001)) * 100.0

    ebf = (total_c1_nodes / len(BENCHMARK_POSITIONS)) ** (1.0 / 7.0)

    summary = {
        "aggregate": {
            "total_c1_nodes": total_c1_nodes,
            "total_c1_time_sec": round(total_c1_time, 4),
            "c1_avg_nps": int(total_c1_nodes / max(total_c1_time, 0.001)),
            "total_prof_nodes": total_prof_nodes,
            "total_prof_time_sec": round(total_prof_time, 4),
            "prof_avg_nps": int(total_prof_nodes / max(total_prof_time, 0.001)),
            "instrumentation_overhead_pct": round(total_overhead, 2),
            "effective_branching_factor_ebf": round(ebf, 3),
            "tt_probes": sum_tt_probes,
            "tt_hits": sum_tt_hits,
            "tt_hit_rate_pct": round(total_tt_hit_rate, 2),
            "tt_cutoffs": sum_tt_cutoffs,
            "tt_cutoff_rate_pct": round(total_tt_cutoff_rate, 2),
            "total_beta_cutoffs": sum_total_cutoffs,
            "first_move_cutoffs": sum_cutoff_m1,
            "first_move_cutoff_rate_pct": round(total_first_move_rate, 2),
            "cutoff_by_tt_move": sum_cutoff_tt,
            "cutoff_by_killer1": sum_cutoff_k1,
            "cutoff_by_killer2": sum_cutoff_k2,
            "cutoff_by_history": sum_cutoff_hist,
            "cutoff_by_captures": sum_cutoff_caps,
            "cutoff_by_quiet": sum_cutoff_quiet,
            "total_qnodes": sum_qnodes,
            "qnode_ratio_pct": round(qnode_ratio, 2),
            "total_eval_calls": sum_eval_calls,
            "movegen_total_time_ms": round(sum_movegen_ms, 2),
            "eval_total_time_ms": round(sum_eval_ms, 2)
        }
    }
    results["summary"] = summary

    out_json = PROF_DIR / "c1_search_profile_raw.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("PROFILING AGGREGATE SUMMARY:")
    print("=" * 80)
    print(f"Total Nodes Searched   : {total_c1_nodes:,} (Profiled: {total_prof_nodes:,})")
    print(f"Quiescence Nodes       : {sum_qnodes:,} ({qnode_ratio:.1f}% of search tree)")
    print(f"Transposition Table    : Probes={sum_tt_probes:,} | Hits={sum_tt_hits:,} ({total_tt_hit_rate:.2f}%) | Cutoffs={sum_tt_cutoffs:,} ({total_tt_cutoff_rate:.2f}%)")
    print(f"Beta Cutoffs           : Total={sum_total_cutoffs:,} | 1st Move={sum_cutoff_m1:,} ({total_first_move_rate:.2f}%)")
    print(f"  Cutoff by TT Move    : {sum_cutoff_tt:,} ({(sum_cutoff_tt / max(sum_total_cutoffs, 1)) * 100:.1f}%)")
    print(f"  Cutoff by Killer 1   : {sum_cutoff_k1:,} ({(sum_cutoff_k1 / max(sum_total_cutoffs, 1)) * 100:.1f}%)")
    print(f"  Cutoff by Killer 2   : {sum_cutoff_k2:,} ({(sum_cutoff_k2 / max(sum_total_cutoffs, 1)) * 100:.1f}%)")
    print(f"  Cutoff by History    : {sum_cutoff_hist:,} ({(sum_cutoff_hist / max(sum_total_cutoffs, 1)) * 100:.1f}%)")
    print(f"  Cutoff by Captures   : {sum_cutoff_caps:,} ({(sum_cutoff_caps / max(sum_total_cutoffs, 1)) * 100:.1f}%)")
    print(f"Static Eval Calls      : {sum_eval_calls:,} calls ({sum_eval_ms:.2f} ms total)")
    print(f"Movegen Time           : {sum_movegen_ms:.2f} ms total")
    print(f"Effective Branching    : EBF = {ebf:.3f}")
    print(f"C1 Baseline NPS        : {summary['aggregate']['c1_avg_nps']:,} nodes/sec")
    print(f"Profiler Overhead      : {total_overhead:+.2f}%")
    print(f"Saved raw data to {out_json}")

if __name__ == "__main__":
    main()
