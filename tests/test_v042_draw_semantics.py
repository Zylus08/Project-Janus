"""Project Janus v0.42 - Comprehensive Draw Rule Semantics Regression Tests.

Validates:
1. Automatic 75-move rule draw (halfmove_clock >= 150) in _terminal_score, _quiescence, and _negamax.
2. Automatic fivefold repetition (is_fivefold_repetition()) in search.
3. Threefold repetition draw behavior at ply > 0 vs root (ply == 0).
4. Claimable 50-move threshold (halfmove_clock == 100) is NOT treated as an automatic draw.
5. TT cutoff suppression when halfmove_clock + depth >= 150.
6. Pruning suppression when halfmove_clock >= 140 (RFP and NMP draw-proximity guards).
7. Winning side avoids repetition when clear win exists.
"""
from __future__ import annotations

import unittest
import chess

from janus.search import JanusSearch


class TestV042DrawSemantics(unittest.TestCase):
    def setUp(self) -> None:
        self.searcher = JanusSearch()

    def test_01_seventyfive_moves_in_all_search_contexts(self) -> None:
        """75-move rule (halfmove_clock >= 150) returns 0 in terminal_score, quiescence, and negamax."""
        board = chess.Board("4k3/8/8/8/8/8/4K3/8 w - - 150 76")
        self.assertTrue(board.is_seventyfive_moves())

        # 1. _terminal_score
        term = self.searcher._terminal_score(board, ply=1)
        self.assertEqual(term, 0)

        # 2. _quiescence
        q_score = self.searcher._quiescence(board, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(q_score, 0)

        # 3. _negamax
        n_score, n_pv = self.searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(n_score, 0)
        self.assertEqual(n_pv, [])

    def test_02_fivefold_repetition_triggers_draw(self) -> None:
        """Fivefold repetition is recognized as automatic draw in search."""
        board = chess.Board("4k3/8/8/8/8/8/7K/Q6R w - - 0 1")
        # 4 full cycles of g1/h2 and d8/e8:
        # Initial: (h2, e8)
        # 1. Kh2-g1 Ke8-d8 2. Kg1-h2 Kd8-e8 (rep 2)
        # 3. Kh2-g1 Ke8-d8 4. Kg1-h2 Kd8-e8 (rep 3)
        # 5. Kh2-g1 Ke8-d8 6. Kg1-h2 Kd8-e8 (rep 4)
        # 7. Kh2-g1 Ke8-d8 8. Kg1-h2 Kd8-e8 (rep 5)
        moves = [
            "h2g1", "e8d8", "g1h2", "d8e8",
            "h2g1", "e8d8", "g1h2", "d8e8",
            "h2g1", "e8d8", "g1h2", "d8e8",
            "h2g1", "e8d8", "g1h2", "d8e8",
        ]
        for m in moves:
            board.push_san(m)
        self.assertTrue(board.is_fivefold_repetition())
        score, pv = self.searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=0)
        self.assertEqual(score, 0)

    def test_03_threefold_at_nonroot_vs_root(self) -> None:
        """Threefold repetition is treated as draw at ply > 0, but root (ply=0) searches alternatives."""
        board = chess.Board("4k3/8/8/8/8/8/7K/Q6R b - - 0 1")
        # Setup position with 3 occurrences of same position
        moves = ["e8d8", "h2g1", "d8e8", "g1h2", "e8d8", "h2g1", "d8e8", "g1h2"]
        for m in moves:
            board.push_san(m)
        self.assertTrue(board.is_repetition(3))

        # At ply > 0: evaluated directly as 0
        score_ply1, _ = self.searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(score_ply1, 0)

        # At root (ply = 0): terminal_score returns None (not auto-drawn at root)
        term_root = self.searcher._terminal_score(board, ply=0)
        self.assertIsNone(term_root)

    def test_04_fifty_move_rule_not_automatic_draw(self) -> None:
        """halfmove_clock == 100 (claimable 50-move rule) is NOT treated as an automatic draw."""
        # King and queen vs King at halfmove_clock = 100
        board = chess.Board("4k3/8/8/8/8/8/4K3/4Q3 w - - 100 51")
        self.assertFalse(board.is_seventyfive_moves())
        self.assertEqual(board.halfmove_clock, 100)

        # _terminal_score must NOT return 0 because it's not an automatic draw
        term = self.searcher._terminal_score(board, ply=1)
        self.assertIsNone(term)

    def test_05_tt_cutoff_suppressed_near_seventyfive_moves(self) -> None:
        """TT entries with non-zero scores cannot produce a cutoff when halfmove_clock + depth >= 150."""
        board = chess.Board("4k3/8/8/8/8/8/4K3/4Q3 w - - 149 75")
        key = self.searcher._key(board)
        # Store an exact win score (500 cp) at depth 2
        self.searcher._store_tt(key, depth=2, score=500, flag="exact", best_move=None, ply=1)

        # Probe TT directly
        entry, _ = self.searcher._probe_tt(key, effective_depth=2)
        self.assertIsNotNone(entry)
        self.assertFalse(board.halfmove_clock + 2 < 150)

        # In _negamax at ply=1, depth=2, even though TT entry depth >= 2 and flag=='exact',
        # the cutoff is suppressed by the guard (board.halfmove_clock + effective_depth < 150 or entry.score == 0).
        # We verify by checking that tt_cutoffs is not incremented at this step.
        initial_tt_cutoffs = self.searcher.tt_cutoffs
        # Reset nodes and search shallowly
        self.searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(self.searcher.tt_cutoffs, initial_tt_cutoffs)

    def test_06_rfp_suppressed_near_draw_threshold(self) -> None:
        """RFP is suppressed when halfmove_clock >= 140 to prevent pruning into draw positions."""
        rfp_searcher = JanusSearch(enable_rfp=True)
        # Position with large static advantage but halfmove_clock = 142
        board = chess.Board("4k3/8/8/8/8/8/7K/4Q3 w - - 142 72")
        self.assertGreaterEqual(board.halfmove_clock, 140)

        # Search at depth 1, ply 1: RFP should NOT fire cutoff due to halfmove_clock guard
        rfp_searcher.rfp_considered = 0
        rfp_searcher.rfp_cutoffs = 0
        rfp_searcher._negamax(board, depth=1, alpha=-1000, beta=1000, ply=1)
        self.assertEqual(rfp_searcher.rfp_cutoffs, 0)

    def test_07_winning_side_avoids_repetition_in_endgame(self) -> None:
        """In endgame with decisive advantage, search prefers non-repeating winning moves over draw."""
        board = chess.Board("4k3/8/8/8/8/8/7K/Q6R w - - 0 1")
        # White repeats twice:
        moves = ["h2g1", "e8d8", "g1h2", "d8e8", "h2g1", "e8d8"]
        for m in moves:
            board.push_san(m)
        res = self.searcher.search(board, max_depth=3)
        self.assertIsNotNone(res.best_move)
        # Playing g1h2 would make the 3rd repetition (score 0), so it must be avoided
        self.assertNotEqual(res.best_move.uci(), "g1h2")
        self.assertGreater(res.score, 500)


if __name__ == "__main__":
    unittest.main()
