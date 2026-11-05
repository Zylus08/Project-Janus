"""Unit tests for Project Janus v0.52 Tournament Controller Adjudication.

Verifies:
1. Exact FIDE checkmate adjudication (White & Black)
2. Exact FIDE stalemate adjudication
3. Exact FIDE insufficient material adjudication
4. Exact FIDE 75-move mandatory automatic draw
5. Exact FIDE fivefold repetition mandatory automatic draw
6. Controller claimable threefold repetition policy
7. Controller claimable 50-move rule policy
8. Non-FIDE safety horizon classification (safety_limit_300_plies)
"""

import unittest
import chess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "v0.52" / "tests"))

from tournament_controller import adjudicate_board


class TestTournamentControllerAdjudication(unittest.TestCase):

    def test_01_checkmate_white_and_black(self):
        # Scholar's mate
        b_w = chess.Board()
        for m in ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]:
            b_w.push_san(m)
        is_over, res, term = adjudicate_board(b_w, 7, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1-0")
        self.assertEqual(term, "checkmate_white")

        # Fool's mate
        b_b = chess.Board()
        for m in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            b_b.push_san(m)
        is_over, res, term = adjudicate_board(b_b, 4, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "0-1")
        self.assertEqual(term, "checkmate_black")

    def test_02_stalemate(self):
        b = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        is_over, res, term = adjudicate_board(b, 50, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "draw_stalemate")

    def test_03_insufficient_material(self):
        # King vs King
        b = chess.Board("8/8/8/4k3/8/8/4K3/8 w - - 0 1")
        is_over, res, term = adjudicate_board(b, 80, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "draw_insufficient_material")

    def test_04_seventyfive_moves(self):
        b = chess.Board("8/8/8/4k3/8/8/4K3/R7 w - - 150 76")
        is_over, res, term = adjudicate_board(b, 150, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "draw_seventyfive_moves")

    def test_05_fivefold_repetition(self):
        b = chess.Board()
        # 4 knight cycles (5 total occurrences)
        for _ in range(4):
            for m in ["Nf3", "Nf6", "Ng1", "Ng8"]:
                b.push_san(m)
        is_over, res, term = adjudicate_board(b, 32, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "draw_fivefold_repetition")

    def test_06_threefold_repetition_claim(self):
        b = chess.Board()
        # 2 knight cycles (3 total occurrences)
        for _ in range(2):
            for m in ["Nf3", "Nf6", "Ng1", "Ng8"]:
                b.push_san(m)
        is_over, res, term = adjudicate_board(b, 16, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "draw_threefold_repetition")

    def test_07_fifty_moves_claim(self):
        b = chess.Board("8/8/8/4k3/8/8/4K3/R7 w - - 100 51")
        is_over, res, term = adjudicate_board(b, 100, 300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "draw_fifty_moves")

    def test_08_safety_limit_explicit_classification(self):
        # A normal position reaching 300 plies without 50 moves or repetition
        b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        is_over, res, term = adjudicate_board(b, 300, max_plies=300)
        self.assertTrue(is_over)
        self.assertEqual(res, "1/2-1/2")
        self.assertEqual(term, "safety_limit_300_plies")
        # Ensure it is NOT labeled as a FIDE draw
        self.assertNotIn("fide", term)
        self.assertNotIn("repetition", term)
        self.assertNotIn("moves", term)


if __name__ == "__main__":
    unittest.main()

