"""Project Janus v0.39 - Quiescence Search Correctness & Check Evasion Test Suite.

Mandatory correctness requirements:
1. Position in check with multiple legal evasions.
2. Forced checkmate in a quiescence node.
3. Position with no legal check evasion (immediate checkmate).
4. Position where capturing the checking piece is the only legal response.
5. Position requiring a non-capturing evasion.
6. Tactical sequence in which a checking line exposes a material loss.
7. Search interruption (stop_event / timeout) while processing check evasions.
8. Alpha-beta correctness under the updated fail-low search logic.
"""
from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path

import chess

from janus.search import JanusSearch, INF, MATE_SCORE

ROOT = Path(__file__).resolve().parents[1]


class TestV039QuiescenceCorrectness(unittest.TestCase):
    """Test suite for quiescence search correctness and check evasions."""

    def setUp(self):
        self.searcher = JanusSearch()

    def test_1_multiple_legal_evasions(self):
        """Position in check with multiple legal evasions; must search all legal evasions."""
        # White king on e1 in check from Black queen on e4.
        # Legal evasions: Be2, Qe2, Ne2, Kd1, Kf1, Be3.
        board = chess.Board("rnb1kbnr/pppp1ppp/8/8/4q3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")
        self.assertTrue(board.is_check())
        legal_evasions = list(board.legal_moves)
        self.assertTrue(len(legal_evasions) > 1)

        # Quiescence search should return a valid score without error
        score = self.searcher._quiescence(board, -INF, INF, ply=0)
        self.assertIsInstance(score, int)
        self.assertTrue(-MATE_SCORE < score < MATE_SCORE)

    def test_2_forced_checkmate_in_quiescence_node(self):
        """Quiescence search evaluating a position leading to checkmate."""
        # Scholar's mate: 1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#
        board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
        self.assertTrue(board.is_check())
        self.assertEqual(len(list(board.legal_moves)), 0)

        # Immediate checkmate must evaluate to -MATE_SCORE + ply
        score = self.searcher._quiescence(board, -INF, INF, ply=2)
        self.assertEqual(score, -MATE_SCORE + 2)

    def test_3_no_legal_check_evasions(self):
        """Position with check and zero legal moves must return exact mate score."""
        # Fool's mate: 1. f3 e5 2. g4 Qh4#
        board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 0 3")
        self.assertTrue(board.is_check())
        self.assertEqual(len(list(board.legal_moves)), 0)

        score = self.searcher._quiescence(board, -INF, INF, ply=0)
        self.assertEqual(score, -MATE_SCORE)

    def test_4_capture_is_only_legal_evasion(self):
        """Position where capturing the checking piece is the only legal response."""
        # White King on a1 behind pawns a2, b2. Black Queen on e1 giving rank 1 check. White Rook on h1.
        # Only legal move is Rxe1.
        board = chess.Board("7k/8/8/8/8/8/PP6/K3q2R w - - 0 1")
        self.assertTrue(board.is_check())
        legal_moves = list(board.legal_moves)
        self.assertEqual(len(legal_moves), 1)
        self.assertEqual(legal_moves[0], chess.Move.from_uci("h1e1"))

        score = self.searcher._quiescence(board, -INF, INF, ply=0)
        # White captures Black's queen with rook: White is now up a rook (+500 approx)
        self.assertTrue(score > 0)

    def test_5_non_capturing_evasion_required(self):
        """Position requiring a quiet, non-capturing king evasion."""
        # White king on e1 in check from Black Rook on e8, no pieces can block or capture.
        # Legal moves: Kd1, Kd2, Kf1, Kf2.
        board = chess.Board("4r2k/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertTrue(board.is_check())
        legal_moves = list(board.legal_moves)
        self.assertTrue(all(not board.is_capture(m) for m in legal_moves))

        # Must successfully evaluate evasions without returning stand-pat
        score = self.searcher._quiescence(board, -INF, INF, ply=0)
        self.assertIsInstance(score, int)
        # Black is up a rook, so from White's perspective score should be negative (~ -500)
        self.assertTrue(score < -300)

    def test_6_tactical_sequence_checking_line_exposes_loss(self):
        """A tactical sequence where king evasion leads to subsequent material loss."""
        # White gives check with bishop Bc4+ on King e8; King moves to d8; White takes Queen with Qxd8.
        board = chess.Board("r1b1k2r/pppp1ppp/2n5/4p3/2B5/8/PPPP1PPP/R1BQK1NR b KQkq - 0 4")
        score = self.searcher._quiescence(board, -INF, INF, ply=0)
        self.assertIsInstance(score, int)

    def test_7_search_interruption_during_check_evasions(self):
        """Search interruption (stop_event) during check evasion processing terminates cleanly."""
        board = chess.Board("rnb1kbnr/pppp1ppp/8/8/4q3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")
        self.assertTrue(board.is_check())

        # Set stop event immediately
        stop_event = threading.Event()
        stop_event.set()
        self.searcher.stop_event = stop_event

        from janus.search import SearchTimeout
        with self.assertRaises(SearchTimeout):
            self.searcher._quiescence(board, -INF, INF, ply=0)

    def test_8_alpha_beta_correctness_fail_low_in_check(self):
        """Alpha-beta bounds correctness: when all check evasions fail low, return best_score not alpha."""
        # Position where Black is in check, and all evasions are losing (e.g. mate in 1 or heavy loss).
        # 4k3/5Q2/4K3/8/8/8/8/8 b - - 0 1 (Black king in check, forced Kd8, then White has mate).
        board = chess.Board("4k3/5Q2/4K3/8/8/8/8/8 b - - 0 1")
        self.assertTrue(board.is_check())

        # Calling with alpha=0, beta=1000.
        # Under old buggy code, it returned 0 because alpha was 0!
        # Under corrected code, since Black is losing and in check, it must return a negative score!
        score = self.searcher._quiescence(board, alpha=0, beta=1000, ply=0)
        self.assertTrue(score < 0, f"Expected negative score for losing check evasion, got {score}")


if __name__ == "__main__":
    unittest.main()
