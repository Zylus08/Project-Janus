#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 7: Controlled Multithreading Factorial Ablation Matrix
Evaluates:
  B0: Frozen X7 (1T Control)
  B1: Frozen X10 (1T Reference)
  B2: Frozen X11 (1T)
  B2_2T: Frozen X11 (2T)
  B3: Frozen X11 (4T)
  B4: X11 with Private TTs (4T) [engine_t1]
  B5: X11 with Improved TT Policy (4T) [engine_t4]
  B6: X11 with Improved Worker Coordination (4T) [engine_w3]
  B7_2T: Selected Integrated X12 Candidate (2T) [janus_classical_x12]
  B7_4T: Selected Integrated X12 Candidate (4T) [janus_classical_x12]
Across 12 benchmark positions at 500ms and 1000ms.
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
TEST_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "tests"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.7" / "raw" / "multithread_factorial_raw.json"

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X11 = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
EXE_T1  = TEST_DIR / "engine_t1.exe"
EXE_T4  = TEST_DIR / "engine_t4.exe"
EXE_W3  = TEST_DIR / "engine_w3.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"

BENCHMARK_SUITE = [
    {"name": "quiet_middlegame", "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10", "expected": None},
    {"name": "open_tactical", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "expected": None},
    {"name": "closed_pawn", "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8", "expected": None},
    {"name": "defensive_pos", "fen": "2r2rk1/1b2bppp/pp2p3/3qN3/3P4/P2B1P2/1P2Q1PP/2RR2K1 b - - 0 20", "expected": None},
    {"name": "endgame_transition", "fen": "4k3/1p3pp1/p3p3/3pP3/3P1P2/P3K3/1P6/8 b - - 0 35", "expected": None},
    {"name": "passed_pawn_race", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "expected": "b4f4"},
    {"name": "forced_check_mate", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected": "h5f7"},
    {"name": "multi_candidate_1", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "expected": None},
    {"name": "multi_candidate_2", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "expected": "e2a6"},
    {"name": "tactical_sacrifice", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected": "d5f6"},
    {"name": "opposite_bishops_draw", "fen": "8/4b3/8/2k5/8/8/4B3/4K3 w - - 0 1", "expected": None},
    {"name": "rook_pawn_breakthrough", "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40", "expected": "d3c3"}
]

CONFIGS = [
    {"id": "B0_X7_1T", "exe": EXE_X7, "threads": 1, "desc": "Frozen X7 Control (1T)"},
    {"id": "B1_X10_1T", "exe": EXE_X10, "threads": 1, "desc": "Frozen X10 Reference (1T)"},
    {"id": "B2_X11_1T", "exe": EXE_X11, "threads": 1, "desc": "Frozen X11 (1T)"},
    {"id": "B2_X11_2T", "exe": EXE_X11, "threads": 2, "desc": "Frozen X11 (2T)"},
    {"id": "B3_X11_4T", "exe": EXE_X11, "threads": 4, "desc": "Frozen X11 (4T)"},
    {"id": "B4_T1_PrivateTT_4T", "exe": EXE_T1, "threads": 4, "desc": "X11 + Private TTs (4T)"},
    {"id": "B5_T4_SmartTT_4T", "exe": EXE_T4, "threads": 4, "desc": "X11 + 64B Smart TT (4T)"},
    {"id": "B6_W3_WorkerCoord_4T", "exe": EXE_W3, "threads": 4, "desc": "X11 + Worker Coord + Smart TT (4T)"},
    {"id": "B7_X12_2T", "exe": EXE_X12, "threads": 2, "desc": "Candidate X12 (2T)"},
    {"id": "B7_X12_4T", "exe": EXE_X12, "threads": 4, "desc": "Candidate X12 (4T)"}
]

def run_bench(exe, fen, movetime_ms, threads):
    cmds = f"uci\nsetoption name Threads value {threads}\nisready\nposition fen {fen}\ngo movetime {movetime_ms}\nquit\n"
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate(cmds, timeout=15)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None
    score_cp = 0

    for line in out.splitlines():
        if line.startswith("info depth"):
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "depth": depth,
        "nodes": nodes,
        "score_cp": score_cp,
        "bestmove": bestmove,
        "elapsed_s": round(dur, 4),
        "nps": nps
    }

def main():
    print(f"=== PROJECT JANUS P1.7: PHASE 7 MULTITHREAD FACTORIAL ABLATION ===")
    print(f"Configurations: {len(CONFIGS)} | Positions: {len(BENCHMARK_SUITE)} | Budgets: [500ms, 1000ms]")

    results = {}
    
    for cfg in CONFIGS:
        cid = cfg["id"]
        exe = cfg["exe"]
        th = cfg["threads"]
        print(f"\nEvaluating {cid} ({cfg['desc']}) ...")
        assert exe.exists(), f"Binary {exe} does not exist!"

        results[cid] = {
            "desc": cfg["desc"],
            "threads": th,
            "exe": str(exe),
            "runs_500ms": {},
            "runs_1000ms": {},
            "stability": 0,
            "tactics_solved": 0,
            "avg_depth_1000ms": 0.0,
            "avg_nps_1000ms": 0,
            "speedup_vs_1t": 1.0
        }

        total_nodes_1000 = 0
        total_time_1000 = 0.0
        total_depth_1000 = 0
        stable_moves = 0
        tactics_solved = 0

        for pos in BENCHMARK_SUITE:
            pname = pos["name"]
            fen = pos["fen"]
            exp = pos["expected"]

            # Run 500ms
            r500 = run_bench(exe, fen, 500, th)
            # Run 1000ms
            r1000 = run_bench(exe, fen, 1000, th)

            results[cid]["runs_500ms"][pname] = r500
            results[cid]["runs_1000ms"][pname] = r1000

            if r500["bestmove"] == r1000["bestmove"]:
                stable_moves += 1

            if exp:
                if r1000["bestmove"] == exp:
                    tactics_solved += 1

            total_nodes_1000 += r1000["nodes"]
            total_time_1000 += r1000["elapsed_s"]
            total_depth_1000 += r1000["depth"]

        results[cid]["stability"] = round(stable_moves / len(BENCHMARK_SUITE) * 100.0, 1)
        results[cid]["tactics_solved"] = tactics_solved
        results[cid]["avg_depth_1000ms"] = round(total_depth_1000 / len(BENCHMARK_SUITE), 2)
        results[cid]["avg_nps_1000ms"] = int(total_nodes_1000 / total_time_1000) if total_time_1000 > 0 else 0

        print(f"  -> Avg Depth (1000ms): {results[cid]['avg_depth_1000ms']} | Avg NPS: {results[cid]['avg_nps_1000ms']:,} | Move Stability: {results[cid]['stability']}% | Tactics: {tactics_solved}/5")

    # Compute Speedups vs B2_X11_1T
    base_nps = results["B2_X11_1T"]["avg_nps_1000ms"]
    for cid in results:
        results[cid]["speedup_vs_1t"] = round(results[cid]["avg_nps_1000ms"] / base_nps, 2)

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved raw factorial matrix to {RAW_OUT}")

if __name__ == "__main__":
    main()

