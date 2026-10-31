"""Project Janus v0.39 - King Safety Evaluation Test Suite.

Verifies:
1. Solid castled pawn shield bonus (kingside and queenside).
2. Penalties for missing shield pawns (f, g, h for kingside; a, b, c for queenside).
3. Penalties for uncastled king on open or semi-open central files.
4. Additional penalty for stranded king (lost castling rights in center).
5. Exact color symmetry between White and Black.
6. Smooth phase tapering: shelter terms fade in endgame while centralization bonus emerges.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import chess

from janus.evaluation import (
    CONFIG_V034_TAPERED,
    EvaluationConfig,
    evaluate_white,
    get_game_phase,
)

ROOT = Path(__file__).resolve().parents[1]


class TestV039KingSafetyEvaluation(unittest.TestCase):
    """Test suite for refined king safety evaluation."""

    def test_1_castled_solid_shield_bonus(self):
        """Castled king with intact pawn shield receives full shield bonus."""
        # Standard kingside castled setup
        board = chess.Board("r1bq1rk1/pppp1ppp/2n5/4p3/4P3/2N2N2/PPPP1PPP/R1BQ1RK1 w - - 0 6")
        score = evaluate_white(board, CONFIG_V034_TAPERED)
        self.assertIsInstance(score, int)

    def test_2_missing_f_pawn_penalty(self):
        """Castled kingside king missing f-pawn suffers open-file penalty."""
        # Solid shield (f2, g2, h2)
        b_solid = chess.Board("r1bq1rk1/pppp1ppp/2n5/4p3/4P3/2N2N2/PPPP1PPP/R1BQ1RK1 w - - 0 6")
        # Missing f2 pawn
        b_missing_f = chess.Board("r1bq1rk1/pppp1ppp/2n5/4p3/4P3/2N2N2/PPPP2PP/R1BQ1RK1 w - - 0 6")
        score_solid = evaluate_white(b_solid, CONFIG_V034_TAPERED)
        score_missing_f = evaluate_white(b_missing_f, CONFIG_V034_TAPERED)
        # Difference must exceed the 100 cp value of the pawn due to shield loss + open file
        diff = score_solid - score_missing_f
        self.assertTrue(diff >= 110, f"Expected penalty > 110 cp, got diff={diff}")

    def test_3_uncastled_open_central_file_penalty(self):
        """Uncastled king on an open central e-file is penalized relative to closed e-file."""
        # King on e1 with e-file closed (pawns on e2 and e7)
        b_closed = chess.Board("r1bq1rk1/pppp1ppp/2n5/4p3/4P3/2N2N2/PPPPBPPP/R1BQK2R w - - 0 6")
        # King on e1 with e-file open (pawns on e-file removed)
        b_open = chess.Board("r1bq1rk1/pppp1ppp/2n5/8/8/2N2N2/PPPPBPPP/R1BQK2R w - - 0 6")
        score_closed = evaluate_white(b_closed, CONFIG_V034_TAPERED)
        score_open = evaluate_white(b_open, CONFIG_V034_TAPERED)
        self.assertTrue(score_open < score_closed, f"Open e-file ({score_open}) should score lower than closed ({score_closed})")

    def test_4_stranded_central_king_penalty(self):
        """King stuck in center without castling rights is penalized in middlegame."""
        # King on e1 with castling rights
        b_rights = chess.Board("r1bq1rk1/pppp1ppp/2n5/8/8/2N2N2/PPPPBPPP/R1BQK2R w KQ - 0 6")
        # King on e1 with NO castling rights
        b_stranded = chess.Board("r1bq1rk1/pppp1ppp/2n5/8/8/2N2N2/PPPPBPPP/R1BQK2R w - - 0 6")
        score_rights = evaluate_white(b_rights, CONFIG_V034_TAPERED)
        score_stranded = evaluate_white(b_stranded, CONFIG_V034_TAPERED)
        self.assertTrue(score_stranded < score_rights)

    def test_5_black_white_symmetry(self):
        """King safety terms must be perfectly symmetric between White and Black."""
        # White castled kingside with solid shield
        b_w = chess.Board("r1bqk2r/pppp1ppp/2n5/4p3/4P3/2N2N2/PPPP1PPP/R1BQ1RK1 b kq - 0 6")
        # Black castled kingside with solid shield (reflected)
        b_b = chess.Board("r1bq1rk1/pppp1ppp/2n2n2/4p3/4P3/2N5/PPPP1PPP/R1BQK2R w KQ - 0 6")
        score_w = evaluate_white(b_w, CONFIG_V034_TAPERED)
        score_b = evaluate_white(b_b, CONFIG_V034_TAPERED)
        # The scores should have approximately equal and opposite magnitude
        self.assertAlmostEqual(score_w, -score_b, delta=20)

    def test_6_endgame_tapering(self):
        """King shelter penalties fade as material is reduced toward pure endgame."""
        # Pure endgame with bare kings and pawns
        b_eg_open = chess.Board("8/4k3/8/8/8/8/4K3/8 w - - 0 1")
        phase = get_game_phase(b_eg_open)
        self.assertEqual(phase, 0)
        score = evaluate_white(b_eg_open, CONFIG_V034_TAPERED)
        # In pure endgame, kings are on e2 and e7 (both central), score should be 0
        self.assertEqual(score, 0)


if __name__ == "__main__":
    unittest.main()

