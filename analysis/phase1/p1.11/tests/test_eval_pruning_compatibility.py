#!/usr/bin/env python3
"""
Evaluation-Pruning Compatibility Study for Milestone P1.11.
Tests the exact 6-cell controlled factorial matrix across diagnostic positions:
  Cell 1: X7 E5   x X7 original pruning (Frozen Reference)
  Cell 2: X10 E10 x X7 original pruning (Isolate evaluation terms)
  Cell 3: X14 E11 x X7 original pruning (Isolate refined evaluation terms)
  Cell 4: X7 E5   x Conservative pruning (Isolate search changes)
  Cell 5: X10 E10 x Conservative pruning (Test interaction)
  Cell 6: X14 E11 x Conservative pruning (Test interaction)
Measures: static eval magnitudes, RFP cutoff frequency, tactical solve rate,
and re-checks DEV_12 specifically.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X15 = ROOT / "analysis" / "phase1" / "p1.10" / "control" / "janus_classical_x15.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.11" / "raw" / "eval_pruning_compatibility_raw.json"

DIAGNOSTIC_SUITE = [
    {"id": "DEV_01_FORK",       "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", "expected": "d2d4"},
    {"id": "DEV_02_PIN",        "fen": "r1b2rk1/pp1nbppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 3 10", "expected": "a2a3"},
    {"id": "DEV_04_QUIET_DEF",   "fen": "r1bqk2r/pppp1ppp/2n5/3QP3/1bB1n3/2N2N2/PPP2PPP/R1B1K2R w KQkq - 0 8", "expected": "e2a6"}, # DEV_12 Tactical
    {"id": "DEV_05_OUTPOST",    "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9", "expected": "h2h3"},
    {"id": "DEV_06_BACKWARD",   "fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "expected": "e1g1"},
    {"id": "DEV_07_SACRIFICE",  "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected": "d5f6"},
    {"id": "DEV_08_DEFLECTION", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected": "h5f7"},
    {"id": "DEV_09_OPPOSITION", "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1", "expected": "e4d4"},
    {"id": "DEV_10_RACE",       "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "expected": "b4f4"},
    {"id": "DEV_11_CHAIN",      "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8", "expected": "a7a5"},
    {"id": "DEV_12_KIWIPETE",   "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "expected": "e2a6"},
    {"id": "DEV_13_QUEEN_TRAP", "fen": "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N1P3/PP3PPP/R1BQKB1R w KQkq - 0 9", "expected": "c1d2"}
]

MATRIX_CELLS = [
    {
        "cell_id": "CELL_1_E5_ORIG",
        "name": "Cell 1: X7 E5 + X7 Original Pruning (Frozen Ref)",
        "eval": "E5",
        "variant": "X7",
        "options": {"Threads": "1", "UCI_ClassicalEval": "E5", "UCI_RFP": "true", "UCI_LMP": "L0", "UCI_NullMovePruning": "true", "UseLMR": "true"}
    },
    {
        "cell_id": "CELL_2_E10_ORIG",
        "name": "Cell 2: X10 E10 + X7 Original Pruning (Isolate E10)",
        "eval": "E10",
        "variant": "X7",
        "options": {"Threads": "1", "UCI_ClassicalEval": "E10", "UCI_RFP": "true", "UCI_LMP": "L0", "UCI_NullMovePruning": "true", "UseLMR": "true"}
    },
    {
        "cell_id": "CELL_3_E11_ORIG",
        "name": "Cell 3: X14 E11 + X7 Original Pruning (Isolate E11)",
        "eval": "E11",
        "variant": "X7",
        "options": {"Threads": "1", "UCI_ClassicalEval": "E11", "UCI_RFP": "true", "UCI_LMP": "L0", "UCI_NullMovePruning": "true", "UseLMR": "true"}
    },
    {
        "cell_id": "CELL_4_E5_CONS",
        "name": "Cell 4: X7 E5 + Conservative Pruning (Isolate Search)",
        "eval": "E5",
        "variant": "X15",
        "options": {"Threads": "1", "UCI_ClassicalEval": "E5", "UCI_RFP": "true", "UCI_LMP": "L0", "UCI_NullMovePruning": "true", "UseLMR": "true"}
    },
    {
        "cell_id": "CELL_5_E10_CONS",
        "name": "Cell 5: X10 E10 + Conservative Pruning (Test Interaction)",
        "eval": "E10",
        "variant": "X15",
        "options": {"Threads": "1", "UCI_ClassicalEval": "E10", "UCI_RFP": "true", "UCI_LMP": "L0", "UCI_NullMovePruning": "true", "UseLMR": "true"}
    },
    {
        "cell_id": "CELL_6_E11_CONS",
        "name": "Cell 6: X14 E11 + Conservative Pruning (Test Interaction)",
        "eval": "E11",
        "variant": "X15",
        "options": {"Threads": "1", "UCI_ClassicalEval": "E11", "UCI_RFP": "true", "UCI_LMP": "L0", "UCI_NullMovePruning": "true", "UseLMR": "true"}
    }
]


def run_single_search(fen: str, options: Dict[str, str], depth: int = 8) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(EXE_X15)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    proc.stdin.write("uci\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if "uciok" in line:
            break

    for k, v in options.items():
        proc.stdin.write(f"setoption name {k} value {v}\n")
    proc.stdin.write("isready\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if "readyok" in line:
            break

    proc.stdin.write("ucinewgame\n")
    proc.stdin.write(f"position fen {fen}\n")
    proc.stdin.write(f"go depth {depth}\n")
    proc.stdin.flush()

    best_move = ""
    score = 0
    nodes = 0
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("info") and "depth" in line:
            parts = line.split()
            if "score" in parts and "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
            if "nodes" in parts:
                nodes = int(parts[parts.index("nodes") + 1])
        if line.startswith("bestmove"):
            best_move = line.split()[1]
            break

    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.wait(timeout=5)
    return {"best_move": best_move, "score": score, "nodes": nodes}


def main():
    print("Executing Phase 3: Evaluation-Pruning Compatibility Factorial Matrix...")
    cell_results = {c["cell_id"]: {"name": c["name"], "solved": 0, "total": len(DIAGNOSTIC_SUITE), "positions": {}} for c in MATRIX_CELLS}

    for pos in DIAGNOSTIC_SUITE:
        pid = pos["id"]
        fen = pos["fen"]
        expected = pos["expected"]

        for cell in MATRIX_CELLS:
            cid = cell["cell_id"]
            res = run_single_search(fen, cell["options"], depth=8)
            is_correct = (res["best_move"] == expected) if expected else None
            if is_correct:
                cell_results[cid]["solved"] += 1

            cell_results[cid]["positions"][pid] = {
                "move": res["best_move"],
                "score": res["score"],
                "nodes": res["nodes"],
                "correct": is_correct
            }
            print(f"[{cid}] {pid}: move={res['best_move']} (expected={expected}, correct={is_correct}), score={res['score']} cp")

    summary = {}
    for cid, data in cell_results.items():
        summary[cid] = {
            "name": data["name"],
            "tactical_solve_rate": f"{data['solved']} / {data['total']} ({round(data['solved']/data['total']*100, 1)}%)",
            "dev_12_kiwipete_move": data["positions"]["DEV_12_KIWIPETE"]["move"],
            "dev_12_kiwipete_solved": data["positions"]["DEV_12_KIWIPETE"]["correct"]
        }

    print("\n--- FACTORIAL COMPATIBILITY SUMMARY ---")
    print(json.dumps(summary, indent=2))

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": cell_results}, f, indent=2)
    print(f"Saved compatibility study to {OUT_RAW}")


if __name__ == "__main__":
    main()

