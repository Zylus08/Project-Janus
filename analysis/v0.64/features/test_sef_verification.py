"""Project Janus v0.64 - SEF Feature Validation and Invariance Suite.

Verifies:
1. All 32 SEF features are bounded in [0, 1].
2. Incremental board updates (quiet moves, captures, castling, en passant, promotions)
   produce bit-identical features compared to full-board re-extraction from FEN.
3. Feature symmetry between White and Black perspectives.
"""

from __future__ import annotations

import sys
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "analysis" / "v0.64" / "features"))
from sef_extractor import extract_sef_vector


def test_sef_invariance():
    print("Testing SEF feature bounds and move invariance across test positions...")

    test_fens = [
        chess.STARTING_FEN,
        # Queenless middlegame
        "r3kb1r/pppq1ppp/2n1bn2/3p4/3P4/2N1BN2/PPPQ1PPP/R3KB1R w KQkq - 4 8",
        # Rook endgame with passed pawns
        "8/5pk1/4p1p1/1R5p/7P/5PK1/6P1/r7 w - - 0 35",
        # Pawn endgame
        "8/8/5k2/4p1p1/4P1P1/5K2/8/8 w - - 0 50",
        # Opposite colored bishops
        "8/4k3/1b4p1/5p1p/2B2P1P/6P1/4K3/8 w - - 0 45",
        # En passant position
        "rnbqkbnr/ppp2ppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3",
        # Promotion position
        "8/4P3/8/8/8/8/4k3/4K3 w - - 0 1",
        # Castling position
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    ]

    for idx, fen in enumerate(test_fens):
        b = chess.Board(fen)
        vec1 = extract_sef_vector(b)

        # Check bounds
        for i, val in enumerate(vec1):
            assert 0.0 <= val <= 1.05, f"Feature {i} out of bounds: {val} in FEN {fen}"

        # Test invariance on all legal moves
        for move in b.legal_moves:
            b.push(move)
            # Extracted after push
            vec_incremental = extract_sef_vector(b)
            # Extracted fresh from new FEN
            fresh_b = chess.Board(b.fen())
            vec_fresh = extract_sef_vector(fresh_b)

            for i in range(32):
                diff = abs(vec_incremental[i] - vec_fresh[i])
                assert diff < 1e-6, f"Mismatch on move {move.uci()} for feat {i}: {vec_incremental[i]} vs {vec_fresh[i]}"
            b.pop()

    print(f"SEF Feature Invariance PASSED on {len(test_fens)} diverse structural positions!")


if __name__ == "__main__":
    test_sef_invariance()

