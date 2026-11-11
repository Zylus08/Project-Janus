#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 3: Isolated Evaluation Feature Ablation Harness
Tests:
  Single-Thread Study (Starting from X7 search: 1T, fixed time, no LMP):
    - E0: Frozen X7 Baseline (Flat E5, No LMP, Fixed Time)
    - E1: Pawn Structure v2 only (E1)
    - E2: King Safety v2 only (E2)
    - E3: Piece Activity v2 only (E3)
    - E4: Endgame Positional v2 only (E4)
    - E5: Full E10 on X7 search (E10, No LMP)
    - E6: Refined E11 on X7 search (E14, No LMP)
    - E7: Full Frozen X14 (Refined E11, Quadratic LMP, Dynamic Time)

  Four-Thread Study (Starting from X12 search: 4T, 64B TT, LMP, Dynamic Time):
    - T0: Frozen X12 Baseline (4T, E10 Eval, LMP L1)
    - T1: X12 Search + Pawn Refinements (E11)
    - T2: X12 Search + King Refinements (E12)
    - T3: X12 Search + Endgame Refinements (E13)
    - T4: X12 Search + Full Refined E11 (E14, LMP L1)
    - T5: X12 Search + Full Refined E11 with LMP OFF (E14, LMP L0)

Across 12 diagnostic positions at 500ms.
Tracks: Completed depth, NPS, nodes, tactical solve rate, and root move stability.
"""

import os
import sys
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.10" / "raw" / "eval_feature_ablation_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X14 = ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe"
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

# Single-Thread Variants
ST_VARIANTS = [
    {"id": "E0_X7_BASE",   "name": "E0: Frozen X7 Baseline (Flat E5, No LMP, Fixed Time)",     "exe": EXE_X7,  "threads": 1, "variant": "X7",  "eval": "E5",  "lmp": "L0", "dyntime": False},
    {"id": "E1_PAWN_E10",  "name": "E1: X7 Search + Pawn Structure v2 only",                   "exe": EXE_ABL, "threads": 1, "variant": "X7",  "eval": "E1",  "lmp": "L0", "dyntime": False},
    {"id": "E2_KING_E10",  "name": "E2: X7 Search + King Safety v2 only",                       "exe": EXE_ABL, "threads": 1, "variant": "X7",  "eval": "E2",  "lmp": "L0", "dyntime": False},
    {"id": "E3_ACT_E10",   "name": "E3: X7 Search + Piece Activity v2 only",                   "exe": EXE_ABL, "threads": 1, "variant": "X7",  "eval": "E3",  "lmp": "L0", "dyntime": False},
    {"id": "E4_END_E10",   "name": "E4: X7 Search + Endgame Positional v2 only",               "exe": EXE_ABL, "threads": 1, "variant": "X7",  "eval": "E4",  "lmp": "L0", "dyntime": False},
    {"id": "E5_E10_FULL",  "name": "E5: X7 Search + Full E10 Eval (No LMP, Fixed Time)",       "exe": EXE_ABL, "threads": 1, "variant": "X7",  "eval": "E10", "lmp": "L0", "dyntime": False},
    {"id": "E6_E11_FULL",  "name": "E6: X7 Search + Refined E11 Eval (No LMP, Fixed Time)",   "exe": EXE_ABL, "threads": 1, "variant": "X7",  "eval": "E14", "lmp": "L0", "dyntime": False},
    {"id": "E7_X14_FULL",  "name": "E7: Full Frozen X14 (Refined E11, Quadratic LMP, DynTime)","exe": EXE_X14, "threads": 1, "variant": "X14", "eval": "E11", "lmp": "L1", "dyntime": True}
]

# 4-Thread Variants
MT_VARIANTS = [
    {"id": "T0_X12_BASE",   "name": "T0: Frozen X12 Baseline (4T, E10 Eval, LMP L1)",           "exe": EXE_X12, "threads": 4, "variant": "X12", "eval": "E10", "lmp": "L1", "dyntime": True},
    {"id": "T1_PAWN_REFINED","name": "T1: X12 Search + Refined Pawn Structure (E11)",          "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E11", "lmp": "L1", "dyntime": True},
    {"id": "T2_KING_REFINED","name": "T2: X12 Search + Refined King Safety (E12)",             "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E12", "lmp": "L1", "dyntime": True},
    {"id": "T3_END_REFINED", "name": "T3: X12 Search + Refined Endgame Terms (E13)",            "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E13", "lmp": "L1", "dyntime": True},
    {"id": "T4_FULL_E11",    "name": "T4: X12 Search + Full Refined E11 (E14, LMP L1)",         "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E14", "lmp": "L1", "dyntime": True},
    {"id": "T5_NO_LMP",      "name": "T5: X12 Search + Full Refined E11 with LMP OFF (LMP L0)", "exe": EXE_ABL, "threads": 4, "variant": "X12", "eval": "E14", "lmp": "L0", "dyntime": True}
]

def run_ablation_search(exe, fen, movetime_ms, threads, variant, eval_mode, lmp, dyntime):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_Variant value {variant}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
        f"setoption name UCI_LMP value {lmp}",
        f"setoption name UCI_DynamicTime value {'true' if dyntime else 'false'}",
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=10)
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
        "nps": nps,
        "score_cp": score_cp,
        "bestmove": bestmove,
        "elapsed_s": round(dur, 4)
    }

def evaluate_variant_group(group_name, variants, movetime_ms=400):
    print(f"\n=================================================================")
    print(f"Executing Variant Group: {group_name} ({len(variants)} configurations)")
    print(f"=================================================================")
    group_results = {}

    for var in variants:
        vid = var["id"]
        vname = var["name"]
        print(f"\nEvaluating {vid}: {vname}...")

        total_depth = 0
        total_nodes = 0
        total_time = 0.0
        tactics_solved = 0
        pos_data = {}

        for pos in DEV_POSITIONS:
            pid = pos["id"]
            fen = pos["fen"]
            exp = pos["expected"]

            res = run_ablation_search(var["exe"], fen, movetime_ms, var["threads"], var["variant"], var["eval"], var["lmp"], var["dyntime"])
            pos_data[pid] = res
            total_depth += res["depth"]
            total_nodes += res["nodes"]
            total_time += res["elapsed_s"]

            if exp and res["bestmove"] == exp:
                tactics_solved += 1

        avg_depth = round(total_depth / len(DEV_POSITIONS), 2)
        avg_nps = int(total_nodes / total_time) if total_time > 0 else 0

        group_results[vid] = {
            "name": vname,
            "threads": var["threads"],
            "variant": var["variant"],
            "eval": var["eval"],
            "lmp": var["lmp"],
            "dyntime": var["dyntime"],
            "avg_depth": avg_depth,
            "avg_nps": avg_nps,
            "tactics_solved": tactics_solved,
            "total_nodes": total_nodes,
            "total_time_s": round(total_time, 2)
        }
        print(f"  -> Depth: {avg_depth} plies | NPS: {avg_nps:,} | Tactics: {tactics_solved}/5 | Total Nodes: {total_nodes:,}")

    return group_results

def main():
    print("=== PROJECT JANUS P1.10: PHASE 3 ISOLATED EVALUATION FEATURE ABLATIONS ===")
    results = {
        "metadata": {
            "title": "Phase 3 Isolated Evaluation Feature Ablations",
            "positions_tested": len(DEV_POSITIONS),
            "movetime_ms": 400
        },
        "single_thread_study": evaluate_variant_group("Single-Thread Study (X7 Search Base)", ST_VARIANTS, movetime_ms=400),
        "four_thread_study": evaluate_variant_group("Four-Thread Study (X12 Search Base)", MT_VARIANTS, movetime_ms=400)
    }

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved Phase 3 Ablation Results to {RAW_OUT}")

if __name__ == "__main__":
    main()

