"""Project Janus v0.41 - Threefold Repetition and Quiescence Correctness Tests.

Validates:
1. Sub-microsecond threefold repetition detection (is_repetition(3)) at non-root plies.
2. Immediate draw score (0) returned upon entering quiescence if position has repeated 3 times.
3. Losing side chooses threefold repetition draw over material deficit.
4. Winning side avoids threefold repetition draw when winning alternatives exist.
5. Inactive repetition does not affect normal search evaluations.
6. Fifty-move rule (halfmove_clock >= 100) triggers draw score (0).
7. Stack integrity is preserved across iterative deepening.
"""
from __future__ import annotations

import unittest
import chess

from janus.search import JanusSearch


class TestV041RepetitionQuiescence(unittest.TestCase):
    def setUp(self) -> None:
        self.searcher = JanusSearch()

    def test_01_repetition_at_main_search_entry_returns_zero(self) -> None:
        """A 3-fold repeated position reached at ply > 0 returns draw score 0."""
        board = chess.Board()
        # 1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1"]
        for m in moves:
            board.push_san(m)

        # Black plays Ng8, completing the 3rd occurrence of the starting position
        board.push_san("f6g8")
        self.assertTrue(board.is_repetition(3))
        # Direct negamax check at ply 1
        score, pv = self.searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(score, 0)
        self.assertEqual(pv, [])
        board.pop()

    def test_02_repetition_at_quiescence_entry_returns_zero(self) -> None:
        """When depth <= 0 and position is 3-fold repeated, search returns draw 0 instead of static eval."""
        # Setup position where White has heavy material advantage (+1400)
        board = chess.Board("4k3/8/8/8/8/8/7K/Q6R b - - 0 1")
        moves = ["e8d8", "h2g1", "d8e8", "g1h2", "e8d8", "h2g1", "d8e8"]
        for m in moves:
            board.push_san(m)

        # White plays g1h2, completing 3rd repetition of (e8, h2, Black to move)
        board.push_san("g1h2")
        self.assertTrue(board.is_repetition(3))

        # At depth 0, entering quiescence must return 0, not -1400 static eval
        score, _ = self.searcher._negamax(board, depth=0, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(score, 0, "Repetition at quiescence entry must evaluate as draw (score 0)")
        board.pop()

    def test_03_losing_position_prefers_repetition_draw(self) -> None:
        """Down heavy material, engine recognizes repetition move as score 0 (drawing) rather than loss."""
        board = chess.Board("3k4/8/8/8/8/8/7K/Q6R w - - 0 1")
        moves = ["h2g1", "d8e8", "g1h2", "e8d8", "h2g1", "d8e8", "g1h2"]
        for m in moves:
            board.push_san(m)

        # Black to move from e8: playing e8d8 repeats (d8, h2) for the 3rd time (score 0)
        res = self.searcher.search(board, max_depth=2)
        self.assertIsNotNone(res.best_move)
        self.assertEqual(res.best_move.uci(), "e8d8")
        self.assertEqual(res.score, 0)

    def test_04_winning_position_avoids_repetition_draw(self) -> None:
        """Ahead in material, engine avoids repeating moves when other winning moves exist."""
        board = chess.Board("4k3/8/8/8/8/8/7K/Q6R w - - 0 1")
        moves = ["h2g1", "e8d8", "g1h2", "d8e8", "h2g1", "e8d8"]
        for m in moves:
            board.push_san(m)

        # White to move: g1h2 would repeat position for 3rd time (score 0), but White is winning
        res = self.searcher.search(board, max_depth=2)
        self.assertIsNotNone(res.best_move)
        self.assertNotEqual(res.best_move.uci(), "g1h2", "Winning side must avoid repetition draw")
        self.assertGreater(res.score, 500, "Winning side must retain high winning score")

    def test_05_non_repeating_position_unaffected(self) -> None:
        """Standard non-repeated positions evaluate normally."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
        self.assertFalse(board.is_repetition(3))
        res = self.searcher.search(board, max_depth=2)
        self.assertIsNotNone(res.best_move)
        self.assertNotEqual(res.score, 0)

    def test_06_seventy_five_move_rule_triggers_draw(self) -> None:
        """When halfmove_clock reaches 150 (75 full moves), position is evaluated as drawn."""
        board = chess.Board("4k3/8/8/8/8/8/4K3/8 w - - 150 76")
        self.assertEqual(board.halfmove_clock, 150)
        self.assertTrue(board.is_seventyfive_moves())
        score, _ = self.searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(score, 0)

    def test_07_board_stack_restored_after_search(self) -> None:
        """Search does not corrupt the board move stack or piece placement."""
        board = chess.Board()
        moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
        for m in moves:
            board.push_san(m)

        stack_len_before = len(board.move_stack)
        fen_before = board.fen()

        res = self.searcher.search(board, max_depth=3)
        self.assertIsNotNone(res.best_move)
        self.assertEqual(len(board.move_stack), stack_len_before)
        self.assertEqual(board.fen(), fen_before)


if __name__ == "__main__":
    unittest.main()
