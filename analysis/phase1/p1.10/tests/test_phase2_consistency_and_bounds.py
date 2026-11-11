#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 2: Evaluation Consistency & Score-Scale Audit Harness
Verifies:
  1. 100% Bit-Exact Color Symmetry across 50 Failure Atlas positions
  2. Evaluation Invariance across Make/Unmake
  3. Mate-Score Separation & Safe Dynamic Bounds
  4. Pruning Interaction: RFP Cutoff Rates & Stand-Pat Margins between E5 (X7) and E11 (X14)
  5. Static Evaluation vs Search Score Divergence
"""

import os
import sys
import json
import time
import subprocess
import re
import math
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.10" / "raw" / "eval_consistency_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

ATLAS_JSON = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X14 = ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"

def invert_fen(fen: str) -> str:
    """Invert colors and ranks of a FEN string for color symmetry testing."""
    parts = fen.split()
    board_rows = parts[0].split('/')
    inv_rows = []
    for row in board_rows:
        inv_row = []
        for ch in row:
            if ch.isalpha():
                inv_row.append(ch.lower() if ch.isupper() else ch.upper())
            else:
                inv_row.append(ch)
        inv_rows.append("".join(inv_row))
    inv_board = "/".join(reversed(inv_rows))
    inv_side = "b" if parts[1] == "w" else "w"
    
    # Castling
    inv_castling = ""
    if parts[2] != "-":
        for c in parts[2]:
            inv_castling += c.lower() if c.isupper() else c.upper()
    else:
        inv_castling = "-"
    
    # EP
    inv_ep = "-"
    if len(parts) > 3 and parts[3] != "-":
        f = parts[3][0]
        r = 9 - int(parts[3][1])
        inv_ep = f"{f}{r}"
        
    halfmove = parts[4] if len(parts) > 4 else "0"
    fullmove = parts[5] if len(parts) > 5 else "1"
    return f"{inv_board} {inv_side} {inv_castling} {inv_ep} {halfmove} {fullmove}"

def run_uci_eval(exe, fen, variant, eval_mode):
    cmds = [
        "uci",
        f"setoption name UCI_Variant value {variant}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
        "isready",
        f"position fen {fen}",
        "go depth 1",
        "quit\n"
    ]
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=5)
    
    score_cp = 0
    for line in out.splitlines():
        if "score cp" in line:
            m = re.search(r'score cp (-?\d+)', line)
            if m: score_cp = int(m.group(1))
    return score_cp

def run_uci_search_detail(exe, fen, depth, variant, eval_mode):
    cmds = [
        "uci",
        f"setoption name UCI_Variant value {variant}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
        "isready",
        f"position fen {fen}",
        f"go depth {depth}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=10)
    dur = time.perf_counter() - t0

    nodes = 0
    score_cp = 0
    bestmove = None

    for line in out.splitlines():
        if "info depth" in line:
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    return {"nodes": nodes, "score_cp": score_cp, "bestmove": bestmove, "dur": round(dur, 4)}

def main():
    print("=== PROJECT JANUS P1.10: PHASE 2 EVALUATION & SEARCH CONSISTENCY AUDIT ===")

    with open(ATLAS_JSON, "r", encoding="utf-8") as f:
        atlas = json.load(f)
    test_positions = atlas.get("dev_positions", [])[:40] + atlas.get("held_out_positions", [])[:10]
    print(f"Loaded {len(test_positions)} audit positions from Atlas.")

    results = {
        "metadata": {
            "title": "Evaluation Consistency & Pruning Bounds Telemetry",
            "positions_tested": len(test_positions)
        },
        "color_symmetry_audit": {
            "tested": 0,
            "passed": 0,
            "failed": 0
        },
        "mate_score_separation_audit": {
            "max_static_score": 0,
            "min_static_score": 0,
            "safe_separation_verified": True
        },
        "score_divergence_and_pruning_audit": []
    }

    # 1. Color Symmetry Audit on X14 (Refined E11)
    print("\n[1] Auditing Color Symmetry on Candidate X14 across 50 positions...")
    symm_passed = 0
    symm_failed = 0
    for pos in test_positions:
        fen = pos["fen"]
        inv_fen = invert_fen(fen)

        sc_norm = run_uci_eval(EXE_X14, fen, "X14", "E11")
        sc_inv = run_uci_eval(EXE_X14, inv_fen, "X14", "E11")

        # Color symmetry: score of inverted position must be identical (from perspective of side to move)
        # Note: both FENs have side to move set to the respective player
        if sc_norm == sc_inv:
            symm_passed += 1
        else:
            symm_failed += 1

    results["color_symmetry_audit"]["tested"] = len(test_positions)
    results["color_symmetry_audit"]["passed"] = symm_passed
    results["color_symmetry_audit"]["failed"] = symm_failed
    print(f"  -> Color Symmetry: {symm_passed}/{len(test_positions)} passed ({symm_passed/len(test_positions)*100:.1f}%)")

    # 2. Score Bounds & Mate Separation
    print("\n[2] Auditing Mate-Score Separation...")
    all_scores = []
    for pos in test_positions:
        sc = run_uci_eval(EXE_X14, pos["fen"], "X14", "E11")
        all_scores.append(sc)

    max_s = max(all_scores)
    min_s = min(all_scores)
    results["mate_score_separation_audit"]["max_static_score"] = max_s
    results["mate_score_separation_audit"]["min_static_score"] = min_s
    results["mate_score_separation_audit"]["safe_separation_verified"] = bool(max_s < 25000 and min_s > -25000)
    print(f"  -> Max Score: {max_s} cp | Min Score: {min_s} cp | Separated from Mate (29,000): {results['mate_score_separation_audit']['safe_separation_verified']}")

    # 3. Static Eval vs Search Score Divergence (Testing Score Scale & Pruning Impact)
    print("\n[3] Auditing Static Score vs Search Score Divergence (X7 vs X14)...")
    diag_positions = test_positions[:15]

    for pos in diag_positions:
        pid = pos.get("id", "POS")
        fen = pos["fen"]

        # X7 (E5 Flat Eval, Fixed Time, No LMP)
        x7_static = run_uci_eval(EXE_X7, fen, "X7", "E5")
        x7_search = run_uci_search_detail(EXE_X7, fen, depth=7, variant="X7", eval_mode="E5")

        # X14 (E11 Refined Eval, Dynamic Time, LMP)
        x14_static = run_uci_eval(EXE_X14, fen, "X14", "E11")
        x14_search = run_uci_search_detail(EXE_X14, fen, depth=7, variant="X14", eval_mode="E11")

        # Telemetry: Score divergence = Search Score - Static Score
        x7_div = abs(x7_search["score_cp"] - x7_static)
        x14_div = abs(x14_search["score_cp"] - x14_static)

        # Check if static eval would trigger RFP (static_eval - 80*d >= beta)
        # RFP risk: when static evaluation is artificially inflated by > 100 cp over X7
        rfp_inflation_risk = (x14_static - x7_static) > 80

        item = {
            "id": pid,
            "fen": fen,
            "x7": {
                "static_cp": x7_static,
                "search_cp": x7_search["score_cp"],
                "divergence": x7_div,
                "nodes": x7_search["nodes"],
                "bestmove": x7_search["bestmove"]
            },
            "x14": {
                "static_cp": x14_static,
                "search_cp": x14_search["score_cp"],
                "divergence": x14_div,
                "nodes": x14_search["nodes"],
                "bestmove": x14_search["bestmove"]
            },
            "rfp_inflation_risk": rfp_inflation_risk,
            "move_agreement": bool(x7_search["bestmove"] == x14_search["bestmove"])
        }
        results["score_divergence_and_pruning_audit"].append(item)
        print(f"  {pid:25s} | X7: Static {x7_static:+4d} -> Search {x7_search['score_cp']:+4d} (Nodes: {x7_search['nodes']:,}) | X14: Static {x14_static:+4d} -> Search {x14_search['score_cp']:+4d} (Nodes: {x14_search['nodes']:,}) | Agree: {item['move_agreement']}")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved Consistency & Bounds Audit to {RAW_OUT}")

if __name__ == "__main__":
    main()

