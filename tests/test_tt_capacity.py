"""Unit and stress tests for Transposition Table capacity limits and replacement policies."""
import unittest
import chess

from janus.search import JanusSearch, TTEntry, TranspositionTable


class TTCapacityTests(unittest.TestCase):
    def test_strict_capacity_bound_always_replace(self):
        capacity = 50
        engine = JanusSearch(tt_max_entries=capacity, tt_replacement_policy="always_replace")
        # Store 200 distinct keys
        for key in range(200):
            engine._store_tt(key=key, depth=3, score=10, flag="exact", best_move=None, ply=0)
            self.assertLessEqual(len(engine.tt), capacity)
        self.assertGreater(engine.tt_clears, 0, "Should have triggered table clears under pressure")

    def test_strict_capacity_bound_depth_preferred(self):
        capacity = 50
        engine = JanusSearch(tt_max_entries=capacity, tt_replacement_policy="depth_preferred")
        for key in range(200):
            engine._store_tt(key=key, depth=3, score=10, flag="exact", best_move=None, ply=0)
            self.assertLessEqual(len(engine.tt), capacity)
        self.assertGreater(engine.tt_clears, 0)

    def test_strict_capacity_bound_two_tier(self):
        capacity = 50
        engine = JanusSearch(tt_max_entries=capacity, tt_replacement_policy="two_tier")
        for key in range(200):
            # Alternate depths to exercise both tiers
            depth = 1 if key % 2 == 0 else 3
            engine._store_tt(key=key, depth=depth, score=10, flag="exact", best_move=None, ply=0)
            total_entries = len(engine.tt) + len(engine.tt_recent)
            self.assertLessEqual(total_entries, capacity, f"Total entries {total_entries} exceeded capacity {capacity}")
        self.assertGreater(engine.tt_clears, 0)

    def test_two_tier_clear_wipes_both_tiers(self):
        engine = JanusSearch(tt_max_entries=100, tt_replacement_policy="two_tier")
        engine._store_tt(key=101, depth=4, score=100, flag="exact", best_move=None, ply=0)
        engine._store_tt(key=102, depth=1, score=50, flag="upper", best_move=None, ply=0)
        self.assertGreater(len(engine.tt) + len(engine.tt_recent), 0)
        engine.tt.clear()
        self.assertEqual(len(engine.tt), 0)
        self.assertEqual(len(engine.tt_recent), 0)

    def test_same_key_updates_under_capacity_pressure(self):
        engine = JanusSearch(tt_max_entries=10, tt_replacement_policy="depth_preferred")
        # Fill table
        for k in range(10):
            engine._store_tt(key=k, depth=2, score=10, flag="lower", best_move=chess.Move.from_uci("e2e4"), ply=0)
        self.assertEqual(len(engine.tt), 10)
        self.assertEqual(engine.tt_clears, 0)

        # Same-key update with deeper search should succeed without triggering a clear
        engine._store_tt(key=5, depth=4, score=50, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)
        self.assertEqual(len(engine.tt), 10)
        self.assertEqual(engine.tt_clears, 0)
        self.assertEqual(engine.tt_same_key_updates, 1)
        self.assertEqual(engine.tt_same_key_overwrites, 1)
        self.assertEqual(engine.tt[5].depth, 4)

        # Same-key update with shallower search should be rejected without triggering a clear
        engine._store_tt(key=5, depth=1, score=20, flag="upper", best_move=None, ply=0)
        self.assertEqual(len(engine.tt), 10)
        self.assertEqual(engine.tt_clears, 0)
        self.assertEqual(engine.tt_same_key_rejected, 1)
        self.assertEqual(engine.tt[5].depth, 4)

    def test_search_correctness_under_severe_capacity_pressure(self):
        """Verify search produces legal PV and correct move even with microscopic TT."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        for policy in ["always_replace", "depth_preferred", "two_tier"]:
            engine = JanusSearch(tt_max_entries=20, tt_replacement_policy=policy)
            res = engine.search(board, max_depth=3)
            self.assertIsNotNone(res.best_move)
            self.assertIn(res.best_move, board.legal_moves)
            self.assertGreater(len(res.pv), 0)
            self.assertEqual(res.pv[0], res.best_move)
            # Verify PV legality
            b = board.copy()
            for m in res.pv:
                self.assertIn(m, b.legal_moves)
                b.push(m)


if __name__ == "__main__":
    unittest.main()
