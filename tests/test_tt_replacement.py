"""Unit and regression tests for Transposition Table replacement policies in Project Janus."""
import unittest
import chess

from janus.search import JanusSearch, TTEntry, MATE_SCORE, MATE_THRESHOLD, INF


class TTReplacementPolicyTests(unittest.TestCase):
    def test_unknown_replacement_policy_raises_value_error(self):
        with self.assertRaises(ValueError):
            JanusSearch(tt_replacement_policy="non_existent_policy")

    def test_always_replace_unconditional_overwrite(self):
        engine = JanusSearch(tt_replacement_policy="always_replace", tt_max_entries=1000)
        board = chess.Board()
        key = engine._key(board)

        # Store depth 5 exact entry
        engine._store_tt(key, depth=5, score=150, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)
        self.assertEqual(engine.tt[key].depth, 5)
        self.assertEqual(engine.tt[key].flag, "exact")
        self.assertEqual(engine.tt[key].best_move, chess.Move.from_uci("e2e4"))

        # Under always_replace, a shallower depth 2 upper-bound overwrites depth 5
        engine._store_tt(key, depth=2, score=-50, flag="upper", best_move=None, ply=0)
        self.assertEqual(engine.tt[key].depth, 2)
        self.assertEqual(engine.tt[key].flag, "upper")
        self.assertIsNone(engine.tt[key].best_move)
        self.assertEqual(engine.tt_same_key_updates, 1)
        self.assertEqual(engine.tt_same_key_overwrites, 1)
        self.assertEqual(engine.tt_same_key_rejected, 0)

    def test_depth_preferred_protects_deeper_entry(self):
        engine = JanusSearch(tt_replacement_policy="depth_preferred", tt_max_entries=1000)
        board = chess.Board()
        key = engine._key(board)

        # Store deep entry: depth 5, lower bound
        engine._store_tt(key, depth=5, score=200, flag="lower", best_move=chess.Move.from_uci("e2e4"), ply=0)

        # Attempt to store shallower entry: depth 2, lower bound
        engine._store_tt(key, depth=2, score=100, flag="lower", best_move=chess.Move.from_uci("d2d4"), ply=0)

        # Deep entry must be preserved!
        self.assertEqual(engine.tt[key].depth, 5)
        self.assertEqual(engine.tt[key].score, 200)
        self.assertEqual(engine.tt[key].best_move, chess.Move.from_uci("e2e4"))
        self.assertEqual(engine.tt_same_key_updates, 1)
        self.assertEqual(engine.tt_same_key_rejected, 1)
        self.assertEqual(engine.tt_same_key_overwrites, 0)

    def test_depth_preferred_allows_greater_depth(self):
        engine = JanusSearch(tt_replacement_policy="depth_preferred", tt_max_entries=1000)
        board = chess.Board()
        key = engine._key(board)

        # Store depth 3 entry
        engine._store_tt(key, depth=3, score=100, flag="lower", best_move=chess.Move.from_uci("e2e4"), ply=0)

        # Store depth 5 entry with same key
        engine._store_tt(key, depth=5, score=150, flag="exact", best_move=chess.Move.from_uci("g1f3"), ply=0)

        # Deeper entry replaces shallower entry
        self.assertEqual(engine.tt[key].depth, 5)
        self.assertEqual(engine.tt[key].score, 150)
        self.assertEqual(engine.tt[key].flag, "exact")
        self.assertEqual(engine.tt[key].best_move, chess.Move.from_uci("g1f3"))
        self.assertEqual(engine.tt_same_key_overwrites, 1)

    def test_depth_preferred_allows_exact_upgrade(self):
        engine = JanusSearch(tt_replacement_policy="depth_preferred", tt_max_entries=1000)
        board = chess.Board()
        key = engine._key(board)

        # Store depth 4 lower bound
        engine._store_tt(key, depth=4, score=100, flag="lower", best_move=chess.Move.from_uci("e2e4"), ply=0)

        # Store depth 4 exact bound
        engine._store_tt(key, depth=4, score=120, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)

        # Exact bound replaces non-exact bound at equal depth
        self.assertEqual(engine.tt[key].flag, "exact")
        self.assertEqual(engine.tt[key].score, 120)
        self.assertEqual(engine.tt_same_key_overwrites, 1)

    def test_depth_preferred_preserves_best_move_on_fail_low(self):
        engine = JanusSearch(tt_replacement_policy="depth_preferred", tt_max_entries=1000)
        board = chess.Board()
        key = engine._key(board)

        # Position had best_move = e2e4 at depth 3
        engine._store_tt(key, depth=3, score=50, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)

        # Later, depth 4 fails low (upper bound, best_move = None)
        engine._store_tt(key, depth=4, score=-20, flag="upper", best_move=None, ply=0)

        # Depth 4 replaces depth 3, BUT best_move = e2e4 is preserved!
        self.assertEqual(engine.tt[key].depth, 4)
        self.assertEqual(engine.tt[key].flag, "upper")
        self.assertEqual(engine.tt[key].score, -20)
        self.assertEqual(engine.tt[key].best_move, chess.Move.from_uci("e2e4"))

    def test_depth_preferred_backfills_best_move_if_missing(self):
        engine = JanusSearch(tt_replacement_policy="depth_preferred", tt_max_entries=1000)
        board = chess.Board()
        key = engine._key(board)

        # Deep entry had no best_move (fail-low)
        engine._store_tt(key, depth=6, score=-50, flag="upper", best_move=None, ply=0)

        # Shallower search finds a move
        engine._store_tt(key, depth=3, score=0, flag="exact", best_move=chess.Move.from_uci("c2c4"), ply=0)

        # Depth 6 is retained, but best_move is backfilled with c2c4!
        self.assertEqual(engine.tt[key].depth, 6)
        self.assertEqual(engine.tt[key].score, -50)
        self.assertEqual(engine.tt[key].best_move, chess.Move.from_uci("c2c4"))

    def test_two_tier_partition_and_probe(self):
        engine = JanusSearch(tt_replacement_policy="two_tier", tt_max_entries=100)
        b1 = chess.Board()
        b2 = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        k1 = engine._key(b1)
        k2 = engine._key(b2)

        # Shallow entry (< depth 2) goes to recent tier
        engine._store_tt(k1, depth=1, score=10, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)
        self.assertNotIn(k1, engine.tt)
        self.assertIn(k1, engine.tt_recent)

        # Deep entry (>= depth 2) goes to deep tier (engine.tt)
        engine._store_tt(k2, depth=3, score=40, flag="exact", best_move=chess.Move.from_uci("f1b5"), ply=0)
        self.assertIn(k2, engine.tt)
        self.assertNotIn(k2, engine.tt_recent)

        # Both entries must be probed successfully
        entry1, move1 = engine._probe_tt(k1, effective_depth=1)
        self.assertIsNotNone(entry1)
        self.assertEqual(move1, chess.Move.from_uci("e2e4"))

        entry2, move2 = engine._probe_tt(k2, effective_depth=3)
        self.assertIsNotNone(entry2)
        self.assertEqual(move2, chess.Move.from_uci("f1b5"))

    def test_two_tier_promotion_from_recent_to_deep(self):
        engine = JanusSearch(tt_replacement_policy="two_tier", tt_max_entries=100)
        board = chess.Board()
        key = engine._key(board)

        # Store depth 1 -> recent tier
        engine._store_tt(key, depth=1, score=10, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)
        self.assertIn(key, engine.tt_recent)
        self.assertNotIn(key, engine.tt)

        # Next iteration searches at depth 3 -> promoted to deep tier!
        engine._store_tt(key, depth=3, score=15, flag="exact", best_move=chess.Move.from_uci("e2e4"), ply=0)
        self.assertIn(key, engine.tt)
        self.assertNotIn(key, engine.tt_recent)
        self.assertEqual(engine.tt[key].depth, 3)

    def test_two_tier_clear_clears_both_tiers(self):
        engine = JanusSearch(tt_replacement_policy="two_tier", tt_max_entries=100)
        b1 = chess.Board()
        b2 = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        k1 = engine._key(b1)
        k2 = engine._key(b2)

        engine._store_tt(k1, depth=1, score=10, flag="exact", best_move=None, ply=0)
        engine._store_tt(k2, depth=4, score=40, flag="exact", best_move=None, ply=0)
        self.assertGreater(len(engine.tt), 0)
        self.assertGreater(len(engine.tt_recent), 0)

        # engine.tt.clear() must clear both tiers!
        engine.tt.clear()
        self.assertEqual(len(engine.tt), 0)
        self.assertEqual(len(engine.tt_recent), 0)

    def test_capacity_pressure_stays_within_budget(self):
        for policy in ("always_replace", "depth_preferred", "two_tier"):
            with self.subTest(policy=policy):
                max_entries = 20
                engine = JanusSearch(tt_replacement_policy=policy, tt_max_entries=max_entries)
                board = chess.Board()
                moves = list(board.legal_moves)

                # Store 50 distinct positions
                for i, m in enumerate(moves[:15]):
                    board.push(m)
                    k = engine._key(board)
                    d = 1 + (i % 5)
                    engine._store_tt(k, depth=d, score=10 * i, flag="exact", best_move=None, ply=0)
                    for m2 in list(board.legal_moves)[:3]:
                        board.push(m2)
                        k2 = engine._key(board)
                        engine._store_tt(k2, depth=d, score=5 * i, flag="lower", best_move=None, ply=0)
                        board.pop()
                    board.pop()

                if policy == "two_tier":
                    total_stored = len(engine.tt) + len(engine.tt_recent)
                else:
                    total_stored = len(engine.tt)

                self.assertLessEqual(total_stored, max_entries)
                self.assertGreater(engine.tt_clears, 0)

    def test_mate_score_round_trip_across_policies(self):
        for policy in ("always_replace", "depth_preferred", "two_tier"):
            with self.subTest(policy=policy):
                engine = JanusSearch(tt_replacement_policy=policy)
                board = chess.Board()
                key = engine._key(board)

                # Mate in 2 from ply 3 -> raw score = MATE_SCORE - 4
                raw_win_mate = MATE_SCORE - 4
                engine._store_tt(key, depth=3, score=raw_win_mate, flag="exact", best_move=None, ply=3)
                entry, _ = engine._probe_tt(key, effective_depth=3)
                self.assertIsNotNone(entry)
                # Stored score is normalized to root: raw + ply = MATE_SCORE - 1
                self.assertEqual(entry.score, MATE_SCORE - 1)
                # Probed from ply 5: score_from_tt should subtract 5 -> MATE_SCORE - 6
                self.assertEqual(engine._score_from_tt(entry.score, ply=5), MATE_SCORE - 6)

                # Losing mate: mated in 1 at ply 2 -> raw score = -MATE_SCORE + 2
                raw_lose_mate = -MATE_SCORE + 2
                engine._store_tt(key, depth=4, score=raw_lose_mate, flag="exact", best_move=None, ply=2)
                entry, _ = engine._probe_tt(key, effective_depth=4)
                # Stored score: raw - ply = -MATE_SCORE + 0
                self.assertEqual(entry.score, -MATE_SCORE)
                # Probed from ply 4: score_from_tt should add 4 -> -MATE_SCORE + 4
                self.assertEqual(engine._score_from_tt(entry.score, ply=4), -MATE_SCORE + 4)

    def test_search_stability_and_pv_legality(self):
        # Test tactical position under all 3 replacement policies
        fen = "r1bqk2r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1"
        for policy in ("always_replace", "depth_preferred", "two_tier"):
            with self.subTest(policy=policy):
                engine = JanusSearch(tt_replacement_policy=policy)
                board = chess.Board(fen)
                res = engine.search(board, max_depth=3)
                self.assertEqual(res.best_move, chess.Move.from_uci("h5f7"))
                self.assertGreaterEqual(res.score, MATE_THRESHOLD)
                # Verify complete PV is legal
                test_b = board.copy()
                for m in res.pv:
                    self.assertIn(m, test_b.legal_moves)
                    test_b.push(m)

    def test_telemetry_counters_reset_each_search(self):
        engine = JanusSearch(tt_replacement_policy="depth_preferred")
        board = chess.Board()

        # Run first search
        res1 = engine.search(board, max_depth=2)
        self.assertGreater(res1.tt_probes, 0)
        self.assertGreater(res1.tt_stores, 0)
        probes_1 = res1.tt_probes

        # Run second search
        res2 = engine.search(board, max_depth=2)
        self.assertEqual(res2.tt_probes, probes_1)

    def test_insufficient_depth_entry_move_ordering(self):
        for policy in ("always_replace", "depth_preferred", "two_tier"):
            with self.subTest(policy=policy):
                engine = JanusSearch(tt_replacement_policy=policy)
                board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
                key = engine._key(board)
                move = chess.Move.from_uci("f1b5")
                # Shallow entry: depth 1
                engine._store_tt(key, depth=1, score=100, flag="exact", best_move=move, ply=0)

                # Search at depth 3: depth 1 cannot cutoff, but f1b5 should be first move ordered
                entry, tt_move = engine._probe_tt(key, effective_depth=3)
                self.assertIsNotNone(entry)
                self.assertEqual(tt_move, move)
                res = engine.search(board, max_depth=3)
                self.assertIsNotNone(res.best_move)
                self.assertIn(res.best_move, board.legal_moves)

    def test_tt_clear_resets_table_state(self):
        for policy in ("always_replace", "depth_preferred", "two_tier"):
            with self.subTest(policy=policy):
                engine = JanusSearch(tt_replacement_policy=policy)
                board = chess.Board()
                res1 = engine.search(board, max_depth=3)
                self.assertGreater(len(engine.tt) + len(engine.tt_recent), 0)

                # Clear TT
                engine.tt.clear()
                self.assertEqual(len(engine.tt), 0)
                self.assertEqual(len(engine.tt_recent), 0)

                # Rerun cold-start search
                res2 = engine.search(board, max_depth=3)
                self.assertEqual(res1.nodes, res2.nodes)
                self.assertEqual(res1.score, res2.score)
                self.assertEqual(res1.best_move, res2.best_move)


if __name__ == "__main__":
    unittest.main()

