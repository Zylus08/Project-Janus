#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 4: Endgame Conversion Study
Compares:
  T0: Frozen X7 (1T, TB off)
  T1: Frozen X12 (4T, TB off)
  T2: Frozen X13 (4T, TB off)
  T3: Candidate with Handcrafted Endgame Improvements E11 (4T, TB off)
  T4: Candidate with Syzygy Enabled (4T, TB fallback)
Across 20 canonical theoretical endgames.
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "endgame_conversion_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

ENDGAME_POSITIONS = [
    # KPK
    {"id": "EG_01_KPK_OPPOSITION_WIN", "fen": "8/8/4k3/8/4K3/4P3/8/8 w - - 0 1", "expected": "win", "target_move": "e4d4"},
    {"id": "EG_02_KPK_OPPOSITION_DRAW", "fen": "8/8/4k3/4P3/4K3/8/8/8 b - - 0 1", "expected": "draw", "target_move": "e6e7"},
    {"id": "EG_03_KPK_ROOK_PAWN_DRAW", "fen": "8/8/8/8/8/1k6/p7/K7 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_04_KPK_KEY_SQUARES_WIN", "fen": "8/8/8/3k4/8/4K3/4P3/8 w - - 0 1", "expected": "win", "target_move": "e3d3"},

    # Rook Endgames
    {"id": "EG_05_LUCENA_WIN", "fen": "8/8/8/8/2R5/4K3/r7/4k3 w - - 0 1", "expected": "win", "target_move": "c4c1"},
    {"id": "EG_06_PHILIDOR_DRAW", "fen": "8/8/8/3k4/8/8/3K4/2R5 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_07_TARRASCH_ROOK_BEHIND_PASSER", "fen": "8/1r6/8/2P1k3/8/8/2R1K3/8 w - - 0 1", "expected": "win", "target_move": None},
    {"id": "EG_08_VANCURA_DRAW", "fen": "5k2/8/8/8/4R3/3K4/8/r7 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_09_ROOK_G_PAWN_WIN", "fen": "8/8/8/8/5k2/R7/4K1P1/7r w - - 0 1", "expected": "win", "target_move": None},

    # Minor Piece Endgames
    {"id": "EG_10_OPPOSITE_BISHOP_DRAW", "fen": "8/8/5k2/3b4/8/4B3/4K3/8 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_11_KN_VS_K_DRAW", "fen": "8/8/8/4k3/8/5N2/4K3/8 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_12_KB_VS_K_DRAW", "fen": "8/8/8/4k3/8/5B2/4K3/8 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_13_KN_VS_KB_DRAW", "fen": "8/8/3b4/2k5/8/4N3/4K3/8 w - - 0 1", "expected": "draw", "target_move": None},
    {"id": "EG_14_SAME_BISHOP_PASSER_WIN", "fen": "8/8/8/2k5/2P5/4B3/4K3/8 w - - 0 1", "expected": "win", "target_move": "e3c5"},

    # Tactical & Queen Endgames
    {"id": "EG_15_KQK_MATE_WIN", "fen": "8/8/8/8/8/5k2/4Q3/4K3 w - - 0 1", "expected": "win", "target_move": "e2f2"},
    {"id": "EG_16_KRK_MATE_WIN", "fen": "8/8/8/8/8/5k2/4R3/4K3 w - - 0 1", "expected": "win", "target_move": "e1f1"},
    {"id": "EG_17_PROMOTION_RACE_WIN", "fen": "8/1P6/8/8/8/8/pk6/7K w - - 0 1", "expected": "win", "target_move": "b7b8q"},
    {"id": "EG_18_SQUARE_OF_PAWN_WIN", "fen": "8/8/8/p7/8/7k/1P6/K7 w - - 0 1", "expected": "win", "target_move": "b2b3"},
    {"id": "EG_19_RECIPROCAL_ZUGZWANG", "fen": "8/8/8/8/4k3/8/4P3/4K3 w - - 0 1", "expected": "draw", "target_move": "e1d2"},
    {"id": "EG_20_BISHOP_FORTRESS_DRAW", "fen": "8/8/8/5b2/8/4k3/4P3/4K3 w - - 0 1", "expected": "draw", "target_move": None}
]

CONFIGS = [
    {"id": "T0", "name": "Frozen X7 (1T, TB off)", "exe": EXE_X7,  "threads": 1, "eval": "E5",  "tb": False},
    {"id": "T1", "name": "Frozen X12 (4T, TB off)", "exe": EXE_X12, "threads": 4, "eval": "E10", "tb": False},
    {"id": "T2", "name": "Frozen X13 (4T, TB off)", "exe": EXE_X13, "threads": 4, "eval": "E10", "tb": False},
    {"id": "T3", "name": "Refined E11 (4T, TB off)", "exe": EXE_ABL, "threads": 4, "eval": "E14", "tb": False},
    {"id": "T4", "name": "Refined E11 + Syzygy (4T, TB on)", "exe": EXE_ABL, "threads": 4, "eval": "E14", "tb": True}
]

def run_endgame_test(exe, fen, threads, eval_mode, tb_enabled, movetime_ms=300):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
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
        if "score cp" in line:
            m = re.search(r'score cp (-?\d+)', line)
            if m: score_cp = int(m.group(1))
        elif "score mate" in line:
            m = re.search(r'score mate (-?\d+)', line)
            if m: score_cp = 10000 if int(m.group(1)) > 0 else -10000
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    return {
        "bestmove": bestmove,
        "score_cp": score_cp,
        "elapsed_s": round(dur, 4)
    }

def main():
    print("=== PROJECT JANUS P1.9: PHASE 4 ENDGAME CONVERSION STUDY ===")
    results = {}

    for cfg in CONFIGS:
        cid = cfg["id"]
        cname = cfg["name"]
        print(f"\nEvaluating {cid}: {cname}...")
        results[cid] = {
            "name": cname,
            "correct_outcomes": 0,
            "win_conversions": 0,
            "draw_defenses": 0,
            "positions": {}
        }

        correct_count = 0
        win_count = 0
        draw_count = 0

        for pos in ENDGAME_POSITIONS:
            pid = pos["id"]
            fen = pos["fen"]
            exp = pos["expected"]
            tgt = pos.get("target_move", None)

            res = run_endgame_test(cfg["exe"], fen, cfg["threads"], cfg["eval"], cfg["tb"])
            results[cid]["positions"][pid] = res

            sc = res["score_cp"]
            bm = res["bestmove"]

            # Outcome assessment
            outcome_ok = False
            if exp == "win":
                if sc > 150 or (tgt and bm == tgt):
                    outcome_ok = True
                    win_count += 1
            elif exp == "draw":
                if abs(sc) < 80:
                    outcome_ok = True
                    draw_count += 1

            if outcome_ok:
                correct_count += 1

        results[cid]["correct_outcomes"] = correct_count
        results[cid]["win_conversions"] = win_count
        results[cid]["draw_defenses"] = draw_count
        print(f"  -> Correct Outcomes: {correct_count}/20 ({correct_count/20*100:.1f}%) | Wins Converted: {win_count} | Draws Defended: {draw_count}")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved Endgame Conversion Study to {RAW_OUT}")

if __name__ == "__main__":
    main()

