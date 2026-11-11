#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.8
Phase 2: X10 Evaluation Transfer Audit & Controlled Feature Attribution
Compares E0 (X7 base), E1' (pawn), E2' (king), E3' (mobility), E4' (endgame), E6 (X10 combined)
across the 12 development positions. Also performs color-inversion symmetry tests.
"""

import os
import sys
import json
import time
import subprocess
import re
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.8" / "raw" / "x10_evaluation_transfer_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"

DEV_POSITIONS = [
    {"id": "DEV_01_PAWN_WEAK", "fen": "r1bq1rk1/pp4pp/2n2p2/1BbpP3/5Q2/2N5/PP3PPP/R1B1K1NR w KQ - 3 11"},
    {"id": "DEV_02_KING_ATTACK", "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15"},
    {"id": "DEV_03_ROOK_ENDGAME", "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40"},
    {"id": "DEV_04_IQP", "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10"},
    {"id": "DEV_05_KNIGHT_OUTPOST", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9"},
    {"id": "DEV_06_BACKWARD_PAWN", "fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7"},
    {"id": "DEV_07_TACTICAL_DEFENSE", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9"},
    {"id": "DEV_08_TACTICAL_DEFLECTION", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"},
    {"id": "DEV_09_PAWN_OPPOSITION", "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1"},
    {"id": "DEV_10_PASSED_PAWN_RACE", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"},
    {"id": "DEV_11_CLOSED_CHAIN", "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8"},
    {"id": "DEV_12_PARALLEL_STABILITY", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"}
]

EVAL_VARIANTS = [
    {"code": "E0", "desc": "Base Classical Material + PST only (emode=0)"},
    {"code": "E5", "desc": "Frozen X7 Baseline Positional Evaluation (emode=5)"},
    {"code": "E6", "desc": "X10 Enhanced Pawn Structure only (emode=6)"},
    {"code": "E7", "desc": "X10 Enhanced King Safety only (emode=7)"},
    {"code": "E8", "desc": "X10 Enhanced Piece Activity & Coordination only (emode=8)"},
    {"code": "E9", "desc": "X10 Enhanced Endgame Positional only (emode=9)"},
    {"code": "E10", "desc": "Full Enhanced Classical Evaluation (Candidate X10/X12, emode=10)"}
]

def invert_fen_color(fen: str) -> str:
    """Flips FEN colors and ranks for symmetry testing."""
    board = chess.Board(fen)
    mirrored = board.mirror()
    return mirrored.fen()

def probe_eval_search(exe: Path, fen: str, emode: str, movetime_ms: int = 500):
    cmds = [
        "uci",
        "setoption name Threads value 1",
        f"setoption name UCI_ClassicalEval value {emode}",
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
    score_cp = 0
    bestmove = None

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
        "bestmove": bestmove,
        "depth": depth,
        "nodes": nodes,
        "score_cp": score_cp,
        "nps": nps,
        "elapsed_s": round(dur, 4)
    }

def main():
    print("=== PROJECT JANUS P1.8: PHASE 2 EVALUATION TRANSFER AUDIT ===")
    
    # 1. Color Symmetry Invariance Audit
    print("\n[1] Testing Color Symmetry Invariance across E0, E5, E10...")
    symmetry_results = []
    test_fens = [
        DEV_POSITIONS[0]["fen"],
        DEV_POSITIONS[3]["fen"],
        DEV_POSITIONS[4]["fen"],
        DEV_POSITIONS[8]["fen"]
    ]
    
    for fen in test_fens:
        inv_fen = invert_fen_color(fen)
        for emode in ["E0", "E5", "E10"]:
            r1 = probe_eval_search(EXE_X12, fen, emode, movetime_ms=100)
            r2 = probe_eval_search(EXE_X12, inv_fen, emode, movetime_ms=100)
            diff = r1["score_cp"] + r2["score_cp"] # For exact symmetry, score(w) == -score(b) -> sum == 0
            is_symmetric = (abs(diff) <= 2) # Allow small rounding tolerance
            symmetry_results.append({
                "fen": fen,
                "emode": emode,
                "score_white": r1["score_cp"],
                "score_black": r2["score_cp"],
                "sum": diff,
                "is_symmetric": is_symmetric
            })
            print(f"  Emode {emode:4}: White={r1['score_cp']:+5d} | Black_mirror={r2['score_cp']:+5d} | Sum={diff:+2d} | Symm: {is_symmetric}")

    # 2. Controlled Feature Matrix on Dev Positions
    print("\n[2] Evaluating 12 Dev Positions across Evaluation Variants E0..E10...")
    matrix_results = {}
    
    for v in EVAL_VARIANTS:
        code = v["code"]
        print(f"\nEvaluating Variant {code} ({v['desc']})...")
        matrix_results[code] = {
            "desc": v["desc"],
            "positions": {},
            "avg_depth": 0.0,
            "avg_nps": 0
        }
        tot_depth = 0
        tot_nodes = 0
        tot_time = 0.0
        
        for pos in DEV_POSITIONS:
            pid = pos["id"]
            fen = pos["fen"]
            res = probe_eval_search(EXE_X12, fen, code, movetime_ms=500)
            matrix_results[code]["positions"][pid] = res
            tot_depth += res["depth"]
            tot_nodes += res["nodes"]
            tot_time += res["elapsed_s"]
            
        matrix_results[code]["avg_depth"] = round(tot_depth / len(DEV_POSITIONS), 2)
        matrix_results[code]["avg_nps"] = int(tot_nodes / tot_time) if tot_time > 0 else 0
        print(f"  -> Avg Depth: {matrix_results[code]['avg_depth']} | Avg NPS: {matrix_results[code]['avg_nps']:,}")

    summary = {
        "milestone": "P1.8",
        "phase": "Phase 2 Evaluation Transfer Audit",
        "symmetry_audit": symmetry_results,
        "feature_matrix": matrix_results
    }

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[DONE] Saved evaluation transfer audit to {RAW_OUT}")

if __name__ == "__main__":
    main()

