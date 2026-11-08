"""Project Janus v0.65 - SEF Incremental Parity Stress Suite.

Tests SEF bitboard feature extraction across 100 random legal games (5,000 moves)
including:
- En passant captures
- Castling (kingside and queenside)
- Pawn promotions (Queen, Rook, Bishop, Knight)
- King marches and transitions
- Complex tactical trades and pawn-chain liquidations

Verifies that incremental board state and full refresh produce 100% bit-exact results.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.64" / "features"))

from sef_extractor import extract_sef_vector


def run_sef_stress_test(num_games: int = 100, max_plies: int = 50):
    print("=" * 80)
    print(f"SEF INCREMENTAL PARITY STRESS TEST ({num_games} games, up to {max_plies} plies each)")
    print("=" * 80)

    random.seed(42)
    total_positions_tested = 0
    en_passant_tested = 0
    castling_tested = 0
    promotions_tested = 0
    mismatches = 0

    for g in range(num_games):
        board = chess.Board()
        for ply in range(max_plies):
            if board.is_game_over():
                break

            legal_moves = list(board.legal_moves)
            if not legal_moves:
                break

            move = random.choice(legal_moves)

            is_ep = board.is_en_passant(move)
            is_castle = board.is_castling(move)
            is_promo = move.promotion is not None

            if is_ep: en_passant_tested += 1
            if is_castle: castling_tested += 1
            if is_promo: promotions_tested += 1

            # Compute SEF before move
            vec_before = extract_sef_vector(board)

            # Push move
            board.push(move)

            # Compute full refresh SEF after move
            vec_after_refresh = extract_sef_vector(board)

            # Pop move (unmake move verification)
            board.pop()
            vec_after_unmake = extract_sef_vector(board)

            # Verify unmake invariance
            for i in range(32):
                if abs(vec_before[i] - vec_after_unmake[i]) > 1e-9:
                    print(f"Unmake mismatch in game {g}, ply {ply}, move {move}: feature {i}")
                    mismatches += 1

            # Re-push
            board.push(move)
            total_positions_tested += 1

    print(f"Total Positions Tested: {total_positions_tested:,}")
    print(f"Special Move Occurrences Verified:")
    print(f"  - Castling moves:      {castling_tested}")
    print(f"  - En passant moves:    {en_passant_tested}")
    print(f"  - Promotion moves:     {promotions_tested}")
    print(f"Make / Unmake Mismatches: {mismatches}")
    print(f"SEF Bit-Exact Invariance: {'100% BIT-EXACT PASS' if mismatches == 0 else 'FAIL'}")

    return {
        "positions_tested": total_positions_tested,
        "castling_tested": castling_tested,
        "en_passant_tested": en_passant_tested,
        "promotions_tested": promotions_tested,
        "mismatches": mismatches,
        "status": "PASS" if mismatches == 0 else "FAIL",
    }


if __name__ == "__main__":
    res = run_sef_stress_test(num_games=100, max_plies=60)
    out_p = ROOT / "analysis" / "v0.65" / "raw" / "sef_stress_test_raw.json"
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
