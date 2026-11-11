#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 6: Search-Evaluation Interaction Factorial Matrix
Configurations:
  B0: X7 1T, Flat Eval E5, TB off
  B1: X10 1T, E10 Eval, TB off
  B2: X12 4T, E10 Eval, TB off
  B3: X13 4T, E10 Eval, TB off
  B4: X12 4T, Refined E11 Eval, TB off
  B5: X12 4T, Refined E11 Eval, TB on (fallback mode)
  B6: X13 4T, Refined E11 Eval, TB off
Across 12 diagnostic positions at 500ms and 1000ms.
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "search_eval_factorial_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"

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
    {"id": "B0", "name": "X7 1T, Flat Eval E5, TB off",                     "exe": EXE_X7,  "threads": 1, "variant": "X7",  "eval": "E5",  "tb": False},
    {"id": "B1", "name": "X10 1T, E10 Eval, TB off",                       "exe": EXE_X10, "threads": 1, "variant": "X10", "eval": "E10", "tb": False},
    {"id": "B2", "name": "X12 4T, E10 Eval, TB off",                       "exe": EXE_X12, "threads": 4, "variant": "X12", "eval": "E10", "tb": False},
    {"id": "B3", "name": "X13 4T, E10 Eval, TB off",                       "exe": EXE_X13, "threads": 4, "variant": "X13", "eval": "E10", "tb": False},
    {"id": "B4", "name": "X12 4T, Refined E11 Eval, TB off",               "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E14", "tb": False},
    {"id": "B5", "name": "X12 4T, Refined E11 Eval, TB on (fallback mode)", "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E14", "tb": True},
    {"id": "B6", "name": "X13 4T, Refined E11 Eval, TB off",               "exe": EXE_ABL, "threads": 4, "variant": "X13", "eval": "E14", "tb": False}
]

def run_search(exe, fen, movetime_ms, threads, variant, eval_mode, tb):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}"
    ]
    if variant:
        cmds.append(f"setoption name UCI_Variant value {variant}")
    if eval_mode:
        cmds.append(f"setoption name UCI_ClassicalEval value {eval_mode}")
    if tb:
        cmds.append("setoption name SyzygyPath value C:/nonexistent_syzygy_path")
    cmds.extend([
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ])

    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=15)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None
    score_cp = 0

    for line in out.splitlines():
        if "info depth" in line:
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
    print("=== PROJECT JANUS P1.9: PHASE 6 SEARCH-EVALUATION FACTORIAL MATRIX ===")
    results = {}

    for cfg in CONFIGS:
        cid = cfg["id"]
        cname = cfg["name"]
        print(f"\nEvaluating Config {cid}: {cname}...")

        results[cid] = {
            "name": cname,
            "threads": cfg["threads"],
            "variant": cfg["variant"],
            "eval": cfg["eval"],
            "tb": cfg["tb"],
            "runs_500ms": {},
            "runs_1000ms": {},
            "avg_depth_500ms": 0.0,
            "avg_depth_1000ms": 0.0,
            "avg_nps_500ms": 0,
            "avg_nps_1000ms": 0,
            "tactics_solved_1000ms": 0,
            "move_stability_pct": 0.0
        }

        total_depth_500 = 0
        total_nodes_500 = 0
        total_time_500 = 0.0

        total_depth_1000 = 0
        total_nodes_1000 = 0
        total_time_1000 = 0.0

        tactics_solved = 0
        stable_moves = 0

        for pos in DEV_POSITIONS:
            pid = pos["id"]
            fen = pos["fen"]
            exp = pos["expected"]

            r500 = run_search(cfg["exe"], fen, 500, cfg["threads"], cfg["variant"], cfg["eval"], cfg["tb"])
            r1000 = run_search(cfg["exe"], fen, 1000, cfg["threads"], cfg["variant"], cfg["eval"], cfg["tb"])

            results[cid]["runs_500ms"][pid] = r500
            results[cid]["runs_1000ms"][pid] = r1000

            if r500["bestmove"] == r1000["bestmove"]:
                stable_moves += 1

            if exp and r1000["bestmove"] == exp:
                tactics_solved += 1

            total_depth_500 += r500["depth"]
            total_nodes_500 += r500["nodes"]
            total_time_500 += r500["elapsed_s"]

            total_depth_1000 += r1000["depth"]
            total_nodes_1000 += r1000["nodes"]
            total_time_1000 += r1000["elapsed_s"]

        avg_depth_500 = round(total_depth_500 / len(DEV_POSITIONS), 2)
        avg_nps_500 = int(total_nodes_500 / total_time_500) if total_time_500 > 0 else 0

        avg_depth_1000 = round(total_depth_1000 / len(DEV_POSITIONS), 2)
        avg_nps_1000 = int(total_nodes_1000 / total_time_1000) if total_time_1000 > 0 else 0

        stability_pct = round(stable_moves / len(DEV_POSITIONS) * 100.0, 1)

        results[cid]["avg_depth_500ms"] = avg_depth_500
        results[cid]["avg_depth_1000ms"] = avg_depth_1000
        results[cid]["avg_nps_500ms"] = avg_nps_500
        results[cid]["avg_nps_1000ms"] = avg_nps_1000
        results[cid]["tactics_solved_1000ms"] = tactics_solved
        results[cid]["move_stability_pct"] = stability_pct

        print(f"  -> 500ms: Depth {avg_depth_500} | NPS {avg_nps_500:,}")
        print(f"  -> 1000ms: Depth {avg_depth_1000} | NPS {avg_nps_1000:,} | Stability: {stability_pct}% | Tactics: {tactics_solved}/5")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved search-eval factorial matrix to {RAW_OUT}")

if __name__ == "__main__":
    main()

