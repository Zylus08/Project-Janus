#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.8
Phase 6: Search-Evaluation Co-Design Factorial Ablation
Evaluates:
  B0: Frozen X7 (1T, X7 Search, X7 Eval E5)
  B1: Frozen X10 (1T, X10 Search, X10 Eval E10)
  B2: Frozen X12 (1T, X12 Search, X7 Eval E5)
  B3: Frozen X12 (4T, X12 Search, X7 Eval E5)
  B4: Frozen X12 (1T, X12 Search, X10 Eval E10)
  B5: Frozen X12 (4T, X12 Search, X10 Eval E10)
Across 12 development benchmark positions at 500ms and 1000ms.
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.8" / "raw" / "search_eval_factorial_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"

DEV_POSITIONS = [
    {"id": "DEV_01_PAWN_WEAK", "fen": "r1bq1rk1/pp4pp/2n2p2/1BbpP3/5Q2/2N5/PP3PPP/R1B1K1NR w KQ - 3 11", "expected": None},
    {"id": "DEV_02_KING_ATTACK", "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15", "expected": None},
    {"id": "DEV_03_ROOK_ENDGAME", "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40", "expected": "d3c3"},
    {"id": "DEV_04_IQP", "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10", "expected": None},
    {"id": "DEV_05_KNIGHT_OUTPOST", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9", "expected": None},
    {"id": "DEV_06_BACKWARD_PAWN", "fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "expected": None},
    {"id": "DEV_07_TACTICAL_DEFENSE", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected": "d5f6"},
    {"id": "DEV_08_TACTICAL_DEFLECTION", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected": "h5f7"},
    {"id": "DEV_09_PAWN_OPPOSITION", "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1", "expected": None},
    {"id": "DEV_10_PASSED_PAWN_RACE", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "expected": "b4f4"},
    {"id": "DEV_11_CLOSED_CHAIN", "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8", "expected": None},
    {"id": "DEV_12_PARALLEL_STABILITY", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "expected": "e2a6"}
]

CONFIGS = [
    {"id": "B0_X7_X7_1T",   "exe": EXE_X7,  "threads": 1, "emode": "E5",  "desc": "Frozen X7 (1T, X7 Search, X7 Eval E5)"},
    {"id": "B1_X10_X10_1T", "exe": EXE_X10, "threads": 1, "emode": "E10", "desc": "Frozen X10 (1T, X10 Search, X10 Eval E10)"},
    {"id": "B2_X12_X7_1T",  "exe": EXE_X12, "threads": 1, "emode": "E5",  "desc": "X12 Search (1T, X7 Eval E5)"},
    {"id": "B3_X12_X7_4T",  "exe": EXE_X12, "threads": 4, "emode": "E5",  "desc": "X12 Search (4T, X7 Eval E5)"},
    {"id": "B4_X12_X10_1T", "exe": EXE_X12, "threads": 1, "emode": "E10", "desc": "X12 Search (1T, X10 Eval E10)"},
    {"id": "B5_X12_X10_4T", "exe": EXE_X12, "threads": 4, "emode": "E10", "desc": "X12 Search (4T, X10 Eval E10)"}
]

def run_search(exe, fen, movetime_ms, threads, emode):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_ClassicalEval value {emode}",
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=15)
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
        "nps": nps,
        "elapsed_s": round(dur, 4)
    }

def main():
    print("=== PROJECT JANUS P1.8: PHASE 6 SEARCH-EVAL FACTORIAL MATRIX ===")
    results = {}

    for cfg in CONFIGS:
        cid = cfg["id"]
        exe = cfg["exe"]
        th = cfg["threads"]
        emode = cfg["emode"]
        print(f"\nEvaluating {cid} ({cfg['desc']})...")

        results[cid] = {
            "desc": cfg["desc"],
            "threads": th,
            "emode": emode,
            "runs_500ms": {},
            "runs_1000ms": {},
            "avg_depth_1000ms": 0.0,
            "avg_nps_1000ms": 0,
            "tactics_solved": 0,
            "stability": 0.0
        }

        total_depth_1000 = 0
        total_nodes_1000 = 0
        total_time_1000 = 0.0
        tactics_solved = 0
        stable_moves = 0

        for pos in DEV_POSITIONS:
            pid = pos["id"]
            fen = pos["fen"]
            exp = pos["expected"]

            r500 = run_search(exe, fen, 500, th, emode)
            r1000 = run_search(exe, fen, 1000, th, emode)

            results[cid]["runs_500ms"][pid] = r500
            results[cid]["runs_1000ms"][pid] = r1000

            if r500["bestmove"] == r1000["bestmove"]:
                stable_moves += 1

            if exp and r1000["bestmove"] == exp:
                tactics_solved += 1

            total_depth_1000 += r1000["depth"]
            total_nodes_1000 += r1000["nodes"]
            total_time_1000 += r1000["elapsed_s"]

        results[cid]["avg_depth_1000ms"] = round(total_depth_1000 / len(DEV_POSITIONS), 2)
        results[cid]["avg_nps_1000ms"] = int(total_nodes_1000 / total_time_1000) if total_time_1000 > 0 else 0
        results[cid]["tactics_solved"] = tactics_solved
        results[cid]["stability"] = round(stable_moves / len(DEV_POSITIONS) * 100.0, 1)

        print(f"  -> Depth: {results[cid]['avg_depth_1000ms']} | NPS: {results[cid]['avg_nps_1000ms']:,} | Stability: {results[cid]['stability']}% | Tactics: {tactics_solved}/4")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved factorial matrix to {RAW_OUT}")

if __name__ == "__main__":
    main()

