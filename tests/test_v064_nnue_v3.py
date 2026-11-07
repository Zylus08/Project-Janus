"""Unit and regression tests for Project Janus v0.64 NNUE-V3 architecture."""

from __future__ import annotations

import unittest
import chess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "v0.64" / "features"))

from sef_extractor import extract_sef_vector


def compute_board_phase(board: chess.Board) -> int:
    phase = 0
    phase += len(board.pieces(chess.KNIGHT, chess.WHITE)) * 1
    phase += len(board.pieces(chess.KNIGHT, chess.BLACK)) * 1
    phase += len(board.pieces(chess.BISHOP, chess.WHITE)) * 1
    phase += len(board.pieces(chess.BISHOP, chess.BLACK)) * 1
    phase += len(board.pieces(chess.ROOK, chess.WHITE)) * 2
    phase += len(board.pieces(chess.ROOK, chess.BLACK)) * 2
    phase += len(board.pieces(chess.QUEEN, chess.WHITE)) * 4
    phase += len(board.pieces(chess.QUEEN, chess.BLACK)) * 4
    return min(24, phase)


class TestNNUEV3Architecture(unittest.TestCase):
    """Test suite for v0.64 NNUE-V3 structural endgame features and blending."""

    def test_sef_dimension(self):
        board = chess.Board()
        vec = extract_sef_vector(board)
        self.assertEqual(len(vec), 32)

    def test_startpos_sef_values(self):
        board = chess.Board()
        vec = extract_sef_vector(board)
        # Passed pawns should be 0
        self.assertEqual(vec[0], 0.0)   # white passed count
        self.assertEqual(vec[16], 0.0)  # black passed count
        # Bishop pairs should be 1.0
        self.assertEqual(vec[12], 1.0)  # white bishop pair
        self.assertEqual(vec[28], 1.0)  # black bishop pair
        # Active turn should be 1.0 for white, 0.0 for black
        self.assertEqual(vec[15], 1.0)  # white turn
        self.assertEqual(vec[31], 0.0)  # black turn

    def test_sef_vector_shape_and_bounds(self):
        board = chess.Board()
        vec = extract_sef_vector(board)
        self.assertEqual(len(vec), 32)
        for val in vec:
            self.assertTrue(0.0 <= val <= 1.0 or val == 0.0 or val == 1.0)

    def test_phase_taper_computation(self):
        # Full middlegame: phase = 24 -> blend = 50%
        start_board = chess.Board()
        p_start = compute_board_phase(start_board)
        self.assertEqual(p_start, 24)
        alpha_start = 0.50 * (p_start / 24.0)
        self.assertAlmostEqual(alpha_start, 0.50)

        # Pawn endgame: only kings and pawns -> phase = 0 -> blend = 0%
        pawn_board = chess.Board("8/4k3/8/8/8/8/4K3/8 w - - 0 1")
        p_pawn = compute_board_phase(pawn_board)
        self.assertEqual(p_pawn, 0)
        alpha_pawn = 0.50 * (p_pawn / 24.0)
        self.assertAlmostEqual(alpha_pawn, 0.0)

        # Rook endgame: 2 rooks -> phase = 4 -> blend = 8.33%
        rook_board = chess.Board("8/4k3/8/8/8/8/4K3/R6r w - - 0 1")
        p_rook = compute_board_phase(rook_board)
        self.assertEqual(p_rook, 4)
        alpha_rook = 0.50 * (p_rook / 24.0)
        self.assertAlmostEqual(alpha_rook, 0.50 * (4.0 / 24.0))

    def test_passed_pawn_detection(self):
        # White has passed pawn on e5, Black has no pawns on d, e, f files
        board = chess.Board("8/4k3/8/4P3/8/8/4K3/8 w - - 0 1")
        vec = extract_sef_vector(board)
        self.assertGreater(vec[0], 0.0)   # white passed count > 0
        self.assertEqual(vec[16], 0.0)    # black passed count == 0


if __name__ == "__main__":
    unittest.main()
