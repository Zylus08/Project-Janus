"""Project Janus v0.40 - Search Invariants and Correctness Test Suite.

Covers the 14 mandatory search invariants:
1. Checkmate at the root.
2. Stalemate at the root.
3. Legal check evasions.
4. Positions with no legal check evasions.
5. Losing check evasion score not replaced by neutral evaluation.
6. Quiescence reaching its hard ply limit.
7. Search interruption before depth 1 completes.
8. Search interruption during a deeper iteration.
9. Preservation of last fully completed iteration's best move.
10. Legal fallback selection when no completed iteration exists.
11. Correct mate-score sign and ply-distance handling.
12. Board-state restoration after search.
13. Repetition-sensitive search paths.
14. Deterministic behavior under identical settings.
"""
from __future__ import annotations

import threading
import time
import unittest

import chess

from janus.search import JanusSearch, MATE_SCORE, MATE_THRESHOLD


class TestV040SearchInvariants(unittest.TestCase):
    def setUp(self) -> None:
        self.searcher = JanusSearch()

    def test_01_checkmate_at_root(self) -> None:
        """Invariant 1: Checkmate at root returns score -MATE_SCORE and None move."""
        # Fool's mate position: Black has mated White
        b = chess.Board("rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertTrue(b.is_checkmate())
        res = self.searcher.search(b, max_depth=3)
        self.assertIsNone(res.best_move)
        self.assertEqual(res.score, -MATE_SCORE)
        self.assertEqual(res.depth, 0)

    def test_02_stalemate_at_root(self) -> None:
        """Invariant 2: Stalemate at root returns score 0 and None move."""
        b = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertTrue(b.is_stalemate())
        res = self.searcher.search(b, max_depth=3)
        self.assertIsNone(res.best_move)
        self.assertEqual(res.score, 0)
        self.assertEqual(res.depth, 0)

    def test_03_legal_check_evasions(self) -> None:
        """Invariant 3: In check, engine returns a legal check evasion."""
        b = chess.Board("rnbqkbnr/ppppp1pp/8/5p1Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 1 2")
        self.assertTrue(b.is_check())
        res = self.searcher.search(b, max_depth=3)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, b.legal_moves)
        b.push(res.best_move)
        self.assertFalse(b.is_check())  # Evasion must successfully relieve check

    def test_04_no_legal_check_evasions(self) -> None:
        """Invariant 4: When mated (no legal evasions), terminal score is recognized."""
        b = chess.Board("8/8/8/8/8/5K2/6Q1/7k b - - 0 1")
        self.assertTrue(b.is_checkmate())
        self.assertEqual(len(list(b.legal_moves)), 0)
        term = self.searcher._terminal_score(b, ply=2)
        self.assertEqual(term, -MATE_SCORE + 2)

    def test_05_losing_check_evasion_negative_score(self) -> None:
        """Invariant 5: Losing check evasions must not be masked by neutral score."""
        # White bare king in check from Black Queen: evasion Kg2 exists, but White is down a queen
        b = chess.Board("7k/8/8/8/8/8/8/4q1K1 w - - 0 1")
        self.assertTrue(b.is_check())
        res = self.searcher.search(b, max_depth=2)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, b.legal_moves)
        # Score must be strongly negative (down a full queen), not 0 or positive
        self.assertLess(res.score, -500)

    def test_06_quiescence_hard_ply_limit(self) -> None:
        """Invariant 6: Quiescence reaches hard ply ceiling without recursion error."""
        b = chess.Board()
        # Search at depth that triggers quiescence with low ceiling
        limited_searcher = JanusSearch(qsearch_max_ply=2)
        score = limited_searcher._quiescence(b, -10000, 10000, ply=0)
        self.assertIsInstance(score, int)

    def test_07_search_interruption_before_depth_1(self) -> None:
        """Invariant 7: Immediate interruption before depth 1 returns legal fallback and depth 0."""
        b = chess.Board()
        stop_evt = threading.Event()
        stop_evt.set()  # Stop immediately

        res = self.searcher.search(b, max_depth=5, stop_event=stop_evt)
        self.assertEqual(res.depth, 0)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, b.legal_moves)

    def test_08_search_interruption_during_deeper_iteration(self) -> None:
        """Invariant 8: Timeout during depth 4 preserves completed depth >= 1."""
        b = chess.Board()
        # Run with short time budget that allows depth 1-2 but interrupts depth 5
        res = self.searcher.search(b, max_depth=10, time_limit=0.030)
        self.assertGreaterEqual(res.depth, 1)
        self.assertLess(res.depth, 10)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, b.legal_moves)

    def test_09_preservation_last_completed_iteration(self) -> None:
        """Invariant 9: Interrupted iteration does not overwrite completed best move/pv."""
        b = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        res1 = self.searcher.search(b, max_depth=2)
        best_d2 = res1.best_move
        score_d2 = res1.score

        # If interrupted on depth 3 after depth 2 finished, best_move must match d2
        stop_evt = threading.Event()

        # Custom hook: set stop event after depth 2
        original_negamax = self.searcher._negamax
        def mock_negamax(board, depth, alpha, beta, ply, *args, **kwargs):
            if depth >= 3:
                stop_evt.set()
                from janus.search import SearchTimeout
                raise SearchTimeout
            return original_negamax(board, depth, alpha, beta, ply, *args, **kwargs)

        self.searcher._negamax = mock_negamax
        try:
            res_interrupted = self.searcher.search(b, max_depth=5, stop_event=stop_evt)
            self.assertEqual(res_interrupted.depth, 2)
            self.assertEqual(res_interrupted.best_move, best_d2)
            self.assertEqual(res_interrupted.score, score_d2)
        finally:
            self.searcher._negamax = original_negamax

    def test_10_legal_fallback_selection_no_completed_iteration(self) -> None:
        """Invariant 10: Defensive fallback selected using move ordering when depth 0."""
        b = chess.Board("r1bqkb1r/pppp1ppp/2n5/4P3/4n3/5N2/PPP1QPPP/RNB1KB1R b KQkq - 1 5")
        stop_evt = threading.Event()
        stop_evt.set()

        res = self.searcher.search(b, max_depth=5, stop_event=stop_evt)
        self.assertEqual(res.depth, 0)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, b.legal_moves)

    def test_11_mate_score_sign_and_ply_distance(self) -> None:
        """Invariant 11: Mate scores reflect correct sign and ply distance."""
        # White delivers mate in 1: 1. Qg7#
        b = chess.Board("8/7k/5K2/6Q1/8/8/8/8 w - - 0 1")
        res = self.searcher.search(b, max_depth=3)
        self.assertEqual(res.best_move, chess.Move.from_uci("g5g7"))
        # Mate in 1 ply: score is MATE_SCORE - 1
        self.assertGreaterEqual(res.score, MATE_THRESHOLD)
        self.assertEqual(res.score, MATE_SCORE - 1)

    def test_12_board_state_restoration(self) -> None:
        """Invariant 12: Board FEN and move stack are strictly identical before and after search."""
        b = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        fen_initial = b.fen()
        moves_initial = list(b.move_stack)

        _ = self.searcher.search(b, max_depth=3)
        self.assertEqual(b.fen(), fen_initial)
        self.assertEqual(list(b.move_stack), moves_initial)

    def test_13_repetition_sensitive_paths(self) -> None:
        """Invariant 13: Repetition-prone moves do not crash or corrupt search state."""
        b = chess.Board()
        for m in ["g1f3", "g8f6", "f3g1", "f6g8"]:
            b.push_san(m)
        res = self.searcher.search(b, max_depth=3)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, b.legal_moves)

    def test_14_deterministic_behavior(self) -> None:
        """Invariant 14: Search produces identical moves and scores on fixed position."""
        b = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        s1 = JanusSearch()
        res1 = s1.search(b, max_depth=3)

        s2 = JanusSearch()
        res2 = s2.search(b, max_depth=3)

        self.assertEqual(res1.best_move, res2.best_move)
        self.assertEqual(res1.score, res2.score)
        self.assertEqual(res1.nodes, res2.nodes)


if __name__ == "__main__":
    unittest.main()
