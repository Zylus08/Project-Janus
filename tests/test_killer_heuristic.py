import unittest
import chess

from janus.search import JanusSearch


class KillerHeuristicTests(unittest.TestCase):
    def setUp(self):
        self.engine = JanusSearch(tt_max_entries=10_000, max_killers_ply=64)

    def test_initial_state_empty_killers(self):
        self.assertEqual(len(self.engine.killers), 64)
        for slot in self.engine.killers:
            self.assertEqual(slot, [None, None])

    def test_move_order_score_hierarchy(self):
        board = chess.Board()
        quiet_move = chess.Move.from_uci("g1f3")
        tt_move = chess.Move.from_uci("e2e4")
        killer1_move = chess.Move.from_uci("d2d4")
        killer2_move = chess.Move.from_uci("c2c4")

        self.engine.killers[0][0] = killer1_move
        self.engine.killers[0][1] = killer2_move

        # TT move
        score_tt = self.engine._move_order_score(board, tt_move, tt_move=tt_move, ply=0)
        self.assertEqual(score_tt, 10_000_000)

        # Killer 1
        score_k1 = self.engine._move_order_score(board, killer1_move, ply=0)
        self.assertEqual(score_k1, 700_000)

        # Killer 2
        score_k2 = self.engine._move_order_score(board, killer2_move, ply=0)
        self.assertEqual(score_k2, 600_000)

        # Other quiet move
        score_quiet = self.engine._move_order_score(board, quiet_move, ply=0)
        self.assertEqual(score_quiet, 0)

        # Hierarchy check: TT > Killer 1 > Killer 2 > Quiet
        self.assertGreater(score_tt, score_k1)
        self.assertGreater(score_k1, score_k2)
        self.assertGreater(score_k2, score_quiet)

    def test_captures_and_promotions_outrank_killers(self):
        # Tactical position with captures and quiet moves
        board = chess.Board("r1bqk2r/pppp1ppp/2n5/4p3/1b2P3/2NP1N2/PPP2PPP/R1BQKB1R w KQkq - 1 5")
        capture_move = chess.Move.from_uci("f3e5")  # NxP capture
        quiet_move = chess.Move.from_uci("a2a3")
        self.engine.killers[0][0] = quiet_move

        score_capture = self.engine._move_order_score(board, capture_move, ply=0)
        score_killer = self.engine._move_order_score(board, quiet_move, ply=0)

        self.assertGreaterEqual(score_capture, 980_000)
        self.assertEqual(score_killer, 700_000)
        self.assertGreater(score_capture, score_killer)

    def test_killer_move_ordered_before_quiet_moves(self):
        board = chess.Board()
        killer_move = chess.Move.from_uci("b1c3")
        self.engine.killers[0][0] = killer_move

        ordered = self.engine._ordered_moves(board, ply=0)
        self.assertEqual(ordered[0], killer_move)

    def test_killer_slot_shift_and_duplicate_prevention(self):
        # Start at a fresh ply 2
        ply = 2
        move_a = chess.Move.from_uci("e2e4")
        move_b = chess.Move.from_uci("d2d4")

        # Simulate first quiet beta cutoff: move_a
        self.engine.killers[ply][1] = self.engine.killers[ply][0]
        self.engine.killers[ply][0] = move_a
        self.assertEqual(self.engine.killers[ply], [move_a, None])

        # Simulate second quiet beta cutoff: move_b
        if self.engine.killers[ply][0] != move_b:
            self.engine.killers[ply][1] = self.engine.killers[ply][0]
            self.engine.killers[ply][0] = move_b
        self.assertEqual(self.engine.killers[ply], [move_b, move_a])

        # Simulate duplicate cutoff with move_b: should NOT duplicate into slot 1
        if self.engine.killers[ply][0] != move_b:
            self.engine.killers[ply][1] = self.engine.killers[ply][0]
            self.engine.killers[ply][0] = move_b
        self.assertEqual(self.engine.killers[ply], [move_b, move_a])

    def test_search_stores_killer_on_beta_cutoff(self):
        # Position where White has a quiet refutation that causes a cutoff
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        # Run search to depth 3
        self.engine.search(board, max_depth=3)
        # Verify that at least one killer move was recorded across the search plies
        recorded_killers = [
            (ply, k) for ply, k in enumerate(self.engine.killers) if k[0] is not None
        ]
        self.assertGreater(len(recorded_killers), 0)
        # Ensure all recorded killers are valid chess.Move instances
        for _, (k1, k2) in recorded_killers:
            self.assertIsInstance(k1, chess.Move)
            if k2 is not None:
                self.assertIsInstance(k2, chess.Move)

    def test_root_search_resets_killers(self):
        self.engine.killers[0][0] = chess.Move.from_uci("e2e4")
        self.engine.killers[0][1] = chess.Move.from_uci("d2d4")
        board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        self.engine.search(board, max_depth=1)
        # In mate in one, ply 0 has no beta-cutoffs (root node); killers[0] should be reset
        self.assertEqual(self.engine.killers[0], [None, None])

    def test_overflow_protection_at_deep_ply(self):
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        # Should safely return 0 without raising IndexError
        score = self.engine._move_order_score(board, move, ply=100)
        self.assertEqual(score, 0)


if __name__ == "__main__":
    unittest.main()
