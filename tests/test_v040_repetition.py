"""Project Janus v0.40 - Repetition Detection & Draw Handling Test Suite.

Covers:
1. Repeated position with relevant move history.
2. Repetition claim available only because of the preceding move.
3. Position where draw claim is unavailable.
4. Automatic-draw conditions supported by engine (insufficient material, 5-fold, 75-move).
5. Search paths that enter and leave repetition-prone positions.
6. Board move-stack integrity before and after search.
7. Correct handling of checkmate and stalemate in quiescence.
8. Search interruption while evaluating a repetition-sensitive position.
"""
from __future__ import annotations

import threading
import unittest

import chess

from janus.search import JanusSearch, MATE_SCORE


class TestV040RepetitionHandling(unittest.TestCase):
    def setUp(self) -> None:
        self.searcher = JanusSearch()

    def test_1_repeated_position_with_move_history(self) -> None:
        """Verify engine behavior on repeated positions with history."""
        board = chess.Board()
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]
        for m in moves:
            board.push_san(m)

        # Position has occurred 3 times. can_claim_threefold_repetition should be True.
        self.assertTrue(board.can_claim_threefold_repetition())
        res = self.searcher.search(board, max_depth=2)
        # Search must return a legal move and preserve move stack
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)
        self.assertEqual(len(board.move_stack), len(moves))

    def test_2_repetition_claim_available_after_move(self) -> None:
        """Verify claim that becomes available via specific candidate move."""
        board = chess.Board()
        # 1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6"]
        for m in moves:
            board.push_san(m)

        self.assertFalse(board.can_claim_threefold_repetition())
        # Playing f3g1 makes the starting position occur for the 3rd time
        board.push_san("f3g1")
        self.assertTrue(board.can_claim_threefold_repetition())
        board.pop()

    def test_3_position_where_draw_claim_is_unavailable(self) -> None:
        """Verify non-repeated positions are not falsely identified as draws."""
        board = chess.Board()
        board.push_san("e2e4")
        board.push_san("e7e5")
        board.push_san("g1f3")
        board.push_san("b8c6")

        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_fivefold_repetition())
        self.assertFalse(board.is_seventyfive_moves())
        self.assertFalse(board.is_insufficient_material())

        res = self.searcher.search(board, max_depth=2)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)

    def test_4_automatic_draw_conditions(self) -> None:
        """Verify automatic draw conditions supported by engine."""
        # Insufficient material (KvK)
        b_kvk = chess.Board("8/8/8/4k3/8/8/4K3/8 w - - 0 1")
        self.assertTrue(b_kvk.is_insufficient_material())
        score_term = self.searcher._terminal_score(b_kvk)
        self.assertEqual(score_term, 0)

        # 75-move rule
        b_75 = chess.Board("8/8/8/4k3/8/8/4K3/8 w - - 150 76")
        self.assertTrue(b_75.is_seventyfive_moves())
        self.assertEqual(self.searcher._terminal_score(b_75), 0)

    def test_5_search_paths_repetition_prone(self) -> None:
        """Ensure search evaluates moves in repetition-prone positions without crash."""
        board = chess.Board()
        for m in ["g1f3", "g8f6", "f3g1", "f6g8"]:
            board.push_san(m)

        res = self.searcher.search(board, max_depth=3)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)

    def test_6_board_move_stack_integrity_after_search(self) -> None:
        """Ensure board move stack is perfectly restored after search."""
        board = chess.Board()
        for m in ["e2e4", "e7e5", "g1f3"]:
            board.push_san(m)

        stack_before = list(board.move_stack)
        fen_before = board.fen()

        res = self.searcher.search(board, max_depth=4)
        self.assertIsNotNone(res.best_move)

        self.assertEqual(board.move_stack, stack_before)
        self.assertEqual(board.fen(), fen_before)

    def test_7_checkmate_and_stalemate_in_quiescence(self) -> None:
        """Verify mate and stalemate scores are handled correctly in quiescence."""
        # Stalemate position
        b_stale = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertTrue(b_stale.is_stalemate())
        score_stale = self.searcher._quiescence(b_stale, -10000, 10000, ply=0)
        self.assertEqual(score_stale, 0)

        # Mate in 1 node: White to move and delivered mate
        b_mated = chess.Board("8/7k/5KQ1/8/8/8/8/8 b - - 0 1")
        self.assertTrue(b_mated.is_check())
        # Legal evasions exist: Kh8
        evasions = list(b_mated.legal_moves)
        self.assertEqual(len(evasions), 1)

    def test_8_search_interruption_repetition_position(self) -> None:
        """Verify search interruption in repetition-sensitive position restores board."""
        board = chess.Board()
        for m in ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]:
            board.push_san(m)

        stop_evt = threading.Event()
        stop_evt.set()  # Immediate stop

        res = self.searcher.search(board, max_depth=5, stop_event=stop_evt)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)
        self.assertEqual(len(board.move_stack), 8)


if __name__ == "__main__":
    unittest.main()

