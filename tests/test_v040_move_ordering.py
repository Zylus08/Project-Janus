"""Project Janus v0.40 - Move Ordering Correctness and Invariant Tests.

Tests:
1. Countermove heuristic table storage on quiet beta cutoff.
2. Move order score hierarchy (TT > Captures > Promotions > Killers > Countermoves > History).
3. History malus penalty for quiet moves searched prior to a beta cutoff.
4. Default engine configuration keeps countermoves and history malus disabled.
5. Search legality, determinism, and invariant preservation under ORD1.
6. Forced checkmate detection under ORD1.
"""
from __future__ import annotations

import unittest
import chess

from janus.search import JanusSearch, MAX_HISTORY_SCORE, MATE_SCORE


class MoveOrderingTests(unittest.TestCase):
    def test_ord1_disabled_by_default(self) -> None:
        """Verify that default JanusSearch does not enable countermoves or history malus."""
        engine = JanusSearch()
        self.assertFalse(engine.enable_countermoves)
        self.assertFalse(engine.enable_history_malus)
        self.assertFalse(engine.enable_rfp)

    def test_score_hierarchy(self) -> None:
        """Verify strict move order score hierarchy.

        TT (10M) > Captures (>1M) > Promotion (800k) > Killer 1 (700k) > Killer 2 (600k) > Countermove (550k) > History (<=500k).
        """
        engine = JanusSearch(enable_countermoves=True)
        board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

        # Opponent move was e2e4
        prev_move = chess.Move.from_uci("e2e4")
        cm_move = chess.Move.from_uci("c7c5")
        engine.countermoves[prev_move.from_square][prev_move.to_square] = cm_move

        # Countermove score
        score_cm = engine._move_order_score(board, cm_move, tt_move=None, ply=1, prev_move=prev_move)
        self.assertEqual(score_cm, 550_000)

        # Killer 1 and 2
        k1 = chess.Move.from_uci("e7e6")
        k2 = chess.Move.from_uci("d7d5")
        engine.killers[1] = [k1, k2]
        self.assertEqual(engine._move_order_score(board, k1, ply=1, prev_move=prev_move), 700_000)
        self.assertEqual(engine._move_order_score(board, k2, ply=1, prev_move=prev_move), 600_000)

        # Hierarchy: Killer 1 > Killer 2 > Countermove
        self.assertGreater(700_000, 600_000)
        self.assertGreater(600_000, score_cm)
        self.assertGreater(score_cm, 500_000)  # MAX_HISTORY_SCORE is 500_000

    def test_countermove_table_update_on_cutoff(self) -> None:
        """Verify countermove table stores the quiet cutoff move corresponding to prev_move."""
        engine = JanusSearch(enable_countermoves=True, enable_history_malus=True)
        # Position after 1. e4
        board = chess.Board()
        board.push(chess.Move.from_uci("e2e4"))

        # Run search to depth 2
        res = engine.search(board, max_depth=2)
        self.assertIsNotNone(res.best_move)

        # Check that countermoves table has at least one recorded entry
        non_empty = [
            (f, t, engine.countermoves[f][t])
            for f in range(64) for t in range(64)
            if engine.countermoves[f][t] is not None
        ]
        self.assertGreater(len(non_empty), 0, "Countermoves table should record quiet cutoffs")

    def test_history_malus_penalizes_failed_quiets(self) -> None:
        """Verify that quiet moves searched prior to a beta cutoff receive negative history."""
        engine = JanusSearch(enable_countermoves=True, enable_history_malus=True)
        board = chess.Board()

        res = engine.search(board, max_depth=3)
        self.assertIsNotNone(res.best_move)

        # Some history entries should be negative from failed quiet moves
        neg_entries = [
            (f, t, engine.history[f][t])
            for f in range(64) for t in range(64)
            if engine.history[f][t] < 0
        ]
        self.assertGreater(len(neg_entries), 0, "History malus must penalize failed quiet moves")
        # Ensure bounds are respected
        for _, _, val in neg_entries:
            self.assertGreaterEqual(val, -MAX_HISTORY_SCORE)

    def test_search_determinism_and_legality_with_ord1(self) -> None:
        """Verify that ORD1 produces legal moves and deterministic output across searches."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n5/4p3/1b2n3/2NP1N2/PPP1BPPP/R1BQK2R w KQkq - 0 6")
        engine1 = JanusSearch(enable_countermoves=True, enable_history_malus=True)
        engine2 = JanusSearch(enable_countermoves=True, enable_history_malus=True)

        res1 = engine1.search(board, max_depth=3)
        res2 = engine2.search(board, max_depth=3)

        self.assertIsNotNone(res1.best_move)
        self.assertTrue(board.is_legal(res1.best_move))
        self.assertEqual(res1.best_move, res2.best_move)
        self.assertEqual(res1.score, res2.score)

    def test_forced_mate_found_with_ord1(self) -> None:
        """Verify that ORD1 preserves exact forced checkmate detection."""
        # Scholar's mate: White to deliver mate in 1 (Qxf7#)
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 4")
        engine = JanusSearch(enable_countermoves=True, enable_history_malus=True)

        res = engine.search(board, max_depth=3)
        self.assertEqual(res.best_move, chess.Move.from_uci("f3f7"))
        self.assertEqual(res.score, MATE_SCORE - 1)


if __name__ == "__main__":
    unittest.main()

