#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 7: Time-Control Generalization & Reversal Investigation
Systematic diagnostic time-budget series:
  100ms, 250ms, 500ms, 1000ms, 3000ms, 5000ms
Across 8 matched diagnostic positions.
Compares:
  - X12_4T (Frozen X12, 4T, Shared Pawn Hash, E10)
  - X13_4T (Frozen X13, 4T, Thread-Local Hash, E10)
  - Refined_E11_4T (Candidate Refined E11, 4T, Thread-Local Hash, E14)
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "time_control_generalization_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"

TIME_BUDGETS_MS = [100, 250, 500, 1000, 3000, 5000]

TEST_POSITIONS = [
    {
        "id": "POS_01_OPEN_TACTIC",
        "fen": "r1bq1rk1/pp4pp/2n2p2/1BbpP3/5Q2/2N5/PP3PPP/R1B1K1NR w KQ - 3 11",
        "desc": "Open center pawn break & tactical pin"
    },
    {
        "id": "POS_02_KING_ATTACK",
        "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15",
        "desc": "Middlegame king attack / open c-file"
    },
    {
        "id": "POS_03_COMPLEX_MIDDLE",
        "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10",
        "desc": "IQP / quiet maneuvering"
    },
    {
        "id": "POS_04_KNIGHT_OUTPOST",
        "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9",
        "desc": "Knight outpost & central pawn tension"
    },
    {
        "id": "POS_05_PAWN_OPPOSITION",
        "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1",
        "desc": "Theoretical pawn endgame opposition"
    },
    {
        "id": "POS_06_ROOK_ENDGAME",
        "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40",
        "desc": "King & pawn breakthrough / rook ending"
    },
    {
        "id": "POS_07_PASSED_PAWN_RACE",
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "desc": "Rook behind passed pawn race"
    },
    {
        "id": "POS_08_PARALLEL_STABILITY",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "desc": "Complex tactical double check & pins"
    }
]

ENGINES = [
    {
        "id": "X12_4T",
        "name": "Janus Classical X12 (4T, Shared 64K TT, E10)",
        "exe": EXE_X12,
        "threads": 4,
        "variant": "X12",
        "eval": "E10"
    },
    {
        "id": "X13_4T",
        "name": "Janus Classical X13 (4T, Thread-Local 16K, E10)",
        "exe": EXE_X13,
        "threads": 4,
        "variant": "X13",
        "eval": "E10"
    },
    {
        "id": "Refined_E11_4T",
        "name": "Janus Candidate Refined E11 (4T, Thread-Local 16K, E14)",
        "exe": EXE_ABL,
        "threads": 4,
        "variant": "X13",
        "eval": "E14"
    }
]

def run_single_search(exe, fen, movetime_ms, threads, variant, eval_mode):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}"
    ]
    if variant:
        cmds.append(f"setoption name UCI_Variant value {variant}")
    if eval_mode:
        cmds.append(f"setoption name UCI_ClassicalEval value {eval_mode}")
    cmds.extend([
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ])

    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=movetime_ms / 1000.0 + 10.0)
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
    print("=== PROJECT JANUS P1.9: PHASE 7 TIME-CONTROL REVERSAL INVESTIGATION ===")
    results = {
        "metadata": {
            "title": "Time-Control Generalization & Reversal Audit",
            "time_budgets_ms": TIME_BUDGETS_MS,
            "positions_tested": len(TEST_POSITIONS)
        },
        "engines": {}
    }

    for eng in ENGINES:
        eid = eng["id"]
        ename = eng["name"]
        print(f"\n=======================================================")
        print(f"Benchmarking Engine: {eid} ({ename})")
        print(f"=======================================================")

        results["engines"][eid] = {
            "name": ename,
            "threads": eng["threads"],
            "variant": eng["variant"],
            "eval": eng["eval"],
            "time_budgets": {}
        }

        for tb in TIME_BUDGETS_MS:
            print(f"\n--- Testing Time Budget: {tb}ms ---")
            tb_key = f"{tb}ms"
            total_depth = 0
            total_nodes = 0
            total_time = 0.0
            pos_data = {}

            for pos in TEST_POSITIONS:
                pid = pos["id"]
                res = run_single_search(eng["exe"], pos["fen"], tb, eng["threads"], eng["variant"], eng["eval"])
                pos_data[pid] = res
                total_depth += res["depth"]
                total_nodes += res["nodes"]
                total_time += res["elapsed_s"]

            avg_d = round(total_depth / len(TEST_POSITIONS), 2)
            avg_nps = int(total_nodes / total_time) if total_time > 0 else 0

            results["engines"][eid]["time_budgets"][tb_key] = {
                "avg_depth": avg_d,
                "avg_nps": avg_nps,
                "total_nodes": total_nodes,
                "total_time_s": round(total_time, 3),
                "positions": pos_data
            }
            print(f"  -> Avg Depth: {avg_d} plies | Avg NPS: {avg_nps:,} | Total Nodes: {total_nodes:,}")

    # Compute move churn across consecutive time budgets for each engine
    for eid, edata in results["engines"].items():
        churn_count = 0
        total_transitions = 0
        for pos in TEST_POSITIONS:
            pid = pos["id"]
            prev_move = None
            for tb in TIME_BUDGETS_MS:
                tb_key = f"{tb}ms"
                curr_move = edata["time_budgets"][tb_key]["positions"][pid]["bestmove"]
                if prev_move is not None:
                    total_transitions += 1
                    if curr_move != prev_move:
                        churn_count += 1
                prev_move = curr_move

        churn_rate = round(churn_count / total_transitions * 100.0, 1) if total_transitions > 0 else 0.0
        edata["root_move_churn_pct"] = churn_rate
        print(f"\nEngine {eid} Total Root Move Churn: {churn_rate}% ({churn_count}/{total_transitions} shifts)")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved Phase 7 time-control reversal data to {RAW_OUT}")

if __name__ == "__main__":
    main()

