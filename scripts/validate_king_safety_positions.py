"""Project Janus v0.40 - King Safety Pre-Match Validation Script.

Compares candidate K0 (uncastled king safety enabled) vs K1 (uncastled king safety disabled)
on a frozen suite of positions:
1. Symmetrical starting position
2. Castled White king vs Castled Black king
3. Uncastled White king on open central e-file vs Castled Black king
4. Uncastled Black king on open central e-file vs Castled White king (Symmetry test)
5. Uncastled king in pure endgame (Fading verification: penalty must vanish)
6. Semi-open central file vs closed central file
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

import chess

from janus.evaluation import CONFIG_V034_TAPERED, evaluate_white

ROOT = Path(__file__).resolve().parents[1]

FROZEN_SUITE = [
    {
        "id": "startpos_symmetric",
        "description": "Standard initial position (perfect White/Black symmetry)",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    },
    {
        "id": "both_castled",
        "description": "Both White and Black castled kingside behind intact pawn shields",
        "fen": "r1bq1rk1/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPPBPPP/R1BQ1RK1 w - - 4 6",
    },
    {
        "id": "white_uncastled_open_e_file",
        "description": "White king stranded on e1 with wide-open e-file; Black castled kingside",
        "fen": "r1bq1rk1/ppp2ppp/2n5/8/8/2N2N2/PPP2PPP/R1BQKB1R w - - 0 8",
    },
    {
        "id": "black_uncastled_open_e_file",
        "description": "Black king stranded on e8 with wide-open e-file; White castled kingside",
        "fen": "r1bqkb1r/ppp2ppp/2n5/8/8/2N2N2/PPP2PPP/R1BQ1RK1 b - - 0 8",
    },
    {
        "id": "pure_endgame_uncastled_kings",
        "description": "Pure pawn endgame (game phase = 0); uncastled central kings",
        "fen": "8/4k3/4p3/4P3/8/4K3/8/8 w - - 0 40",
    },
    {
        "id": "white_uncastled_semi_open_e_file",
        "description": "White king on e1 with semi-open e-file (White pawn gone, Black e7 pawn intact)",
        "fen": "r1bq1rk1/pppp1ppp/2n2n2/8/8/2N2N2/PPPP1PPP/R1BQKB1R w - - 0 6",
    },
]


def run_validation() -> Dict[str, Any]:
    cfg_k0 = replace(CONFIG_V034_TAPERED, enable_uncastled_king_safety=True)
    cfg_k1 = replace(CONFIG_V034_TAPERED, enable_uncastled_king_safety=False)

    results = []
    print("Running King Safety Frozen Position Validation (K0 vs K1)...")

    for pos in FROZEN_SUITE:
        b = chess.Board(pos["fen"])
        score_k0 = evaluate_white(b, cfg_k0)
        score_k1 = evaluate_white(b, cfg_k1)
        delta_k0_minus_k1 = score_k0 - score_k1

        results.append({
            "id": pos["id"],
            "description": pos["description"],
            "fen": pos["fen"],
            "score_k0_cp": score_k0,
            "score_k1_cp": score_k1,
            "delta_cp": delta_k0_minus_k1,
        })
        print(f"[{pos['id']}] K0={score_k0} cp, K1={score_k1} cp, Delta={delta_k0_minus_k1:+d} cp")

    # Invariant checks:
    # 1. Symmetry on startpos: K0 score == K1 score (delta == 0)
    assert results[0]["delta_cp"] == 0, "Symmetry violated on startpos!"
    # 2. Both castled: K0 score == K1 score (delta == 0)
    assert results[1]["delta_cp"] == 0, "Castled king terms affected by uncastled toggle!"
    # 3. White uncastled with open e-file: K0 must be lower (penalized) than K1
    assert results[2]["delta_cp"] < 0, "K0 failed to penalize White exposed king!"
    # 4. Black uncastled with open e-file: K0 must be higher (penalizing Black) than K1
    assert results[3]["delta_cp"] > 0, "K0 failed to penalize Black exposed king!"
    # 5. Exact colour symmetry: White penalty == - Black penalty (within 1 cp due to phase integer rounding)
    assert abs(results[2]["delta_cp"] + results[3]["delta_cp"]) <= 1, f"Colour asymmetry: W={results[2]['delta_cp']}, B={results[3]['delta_cp']}"
    # 6. Pure endgame fading: In pure endgame (phase=0), delta must be exactly 0
    assert results[4]["delta_cp"] == 0, f"King safety did not fade in endgame! delta={results[4]['delta_cp']}"

    print("ALL 6 INVARIANT CHECKS PASSED PERFECTLY!")

    out_file = ROOT / "analysis" / "v0.40" / "king_safety_frozen_suite.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return {"results": results, "checks_passed": True}


if __name__ == "__main__":
    run_validation()
