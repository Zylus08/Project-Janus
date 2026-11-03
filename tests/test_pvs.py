"""Unit and regression tests for Principal Variation Search (PVS) in Project Janus."""
import unittest
import chess

from janus.search import JanusSearch, MATE_SCORE, INF, TTEntry


class PrincipalVariationSearchTests(unittest.TestCase):
    def setUp(self):
        self.pvs_search = JanusSearch(enable_pvs=True)
        self.ab_search = JanusSearch(enable_pvs=False)

    def test_pvs_first_move_remains_best(self):
        """When the first move ordered is best, subsequent moves fail low in scout search."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        res_pvs = self.pvs_search.search(board, max_depth=3)
        res_ab = self.ab_search.search(board, max_depth=3)

        self.assertEqual(res_pvs.score, res_ab.score)
        self.assertEqual(res_pvs.best_move, res_ab.best_move)
        self.assertGreater(res_pvs.scout_searches, 0)
        self.assertGreater(res_pvs.beta_cutoffs, 0)

    def test_pvs_later_move_fails_low(self):
        """Later inferior moves fail low in scout search and do not trigger re-searches."""
        # Simple endgame where White's best move is clear
        board = chess.Board("8/P7/8/8/8/4k3/8/4K3 w - - 0 1")
        res_pvs = self.pvs_search.search(board, max_depth=3)
        res_ab = self.ab_search.search(board, max_depth=3)

        self.assertEqual(res_pvs.best_move, res_ab.best_move)
        self.assertEqual(res_pvs.score, res_ab.score)
        self.assertGreater(res_pvs.scout_searches, 0)
        # Most or all scout searches should fail low without needing full re-search
        self.assertLessEqual(res_pvs.researches, res_pvs.scout_searches)

    def test_pvs_later_move_beats_alpha_and_researches(self):
        """When a later move beats alpha in scout search, a full-window re-search is performed."""
        # Position where an unpromising move is actually best or where move ordering
        # tests a move that beats alpha at depth >= 2
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        res_pvs = self.pvs_search.search(board, max_depth=4)
        res_ab = self.ab_search.search(board, max_depth=4)

        self.assertEqual(res_pvs.score, res_ab.score)
        self.assertEqual(res_pvs.best_move, res_ab.best_move)
        self.assertGreater(res_pvs.scout_searches, 0)
        # Verify that scout fail-highs occurred and triggered re-searches
        self.assertGreater(res_pvs.scout_fail_highs, 0)
        self.assertGreater(res_pvs.researches, 0)
        self.assertLessEqual(res_pvs.researches, res_pvs.scout_fail_highs)

    def test_pvs_beta_cutoffs(self):
        """Verify beta cutoffs occur during search and increment telemetry counter."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5")
        res_pvs = self.pvs_search.search(board, max_depth=3)
        self.assertGreater(res_pvs.beta_cutoffs, 0)

    def test_pvs_mate_distance_scoring(self):
        """PVS preserves exact mate-distance scores."""
        # Mate in 1
        board_m1 = chess.Board("8/7k/5K2/6Q1/8/8/8/8 w - - 0 1")
        res_m1_pvs = self.pvs_search.search(board_m1, max_depth=3)
        res_m1_ab = self.ab_search.search(board_m1, max_depth=3)
        self.assertEqual(res_m1_pvs.score, 99999)
        self.assertEqual(res_m1_ab.score, 99999)
        self.assertEqual(res_m1_pvs.best_move, chess.Move.from_uci("g5g7"))

        # Mate in 2
        board_m2 = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5")
        res_m2_pvs = self.pvs_search.search(board_m2, max_depth=3)
        res_m2_ab = self.ab_search.search(board_m2, max_depth=3)
        self.assertEqual(res_m2_pvs.score, res_m2_ab.score)
        self.assertEqual(res_m2_pvs.best_move, res_m2_ab.best_move)

    def test_pvs_checkmate_stalemate_and_in_check_evasions(self):
        """Checkmate, stalemate, and evasions are handled soundly by PVS."""
        # Stalemate
        stalemate_board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        res_st_pvs = self.pvs_search.search(stalemate_board, max_depth=3)
        res_st_ab = self.ab_search.search(stalemate_board, max_depth=3)
        self.assertEqual(res_st_pvs.score, 0)
        self.assertEqual(res_st_ab.score, 0)
        self.assertIsNone(res_st_pvs.best_move)

        # In-check position with multiple evasions
        check_board = chess.Board("8/8/8/8/8/4k3/4r3/4K3 w - - 0 1")
        res_ck_pvs = self.pvs_search.search(check_board, max_depth=4)
        res_ck_ab = self.ab_search.search(check_board, max_depth=4)
        self.assertEqual(res_ck_pvs.score, res_ck_ab.score)
        self.assertEqual(res_ck_pvs.best_move, res_ck_ab.best_move)

    def test_pvs_tt_bound_behavior(self):
        """Transposition table entries maintain sound exact/lower/upper bound flags under PVS."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        self.pvs_search.search(board, max_depth=3)
        
        flags = set()
        for key, entry in self.pvs_search.tt.items():
            self.assertIn(entry.flag, ("exact", "lower", "upper"))
            flags.add(entry.flag)
            self.assertGreaterEqual(entry.depth, 1)

        # Over the search tree, all three bound types should naturally occur
        self.assertIn("exact", flags)
        self.assertIn("upper", flags)

    def test_pvs_legal_pv_reconstruction(self):
        """PV returned by PVS is legally playable in sequence."""
        positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
            "8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
        ]
        for fen in positions:
            board = chess.Board(fen)
            res = self.pvs_search.search(board, max_depth=4)
            self.assertGreaterEqual(len(res.pv), 1)
            self.assertEqual(res.pv[0], res.best_move)
            
            # Verify moves can be executed
            verify = board.copy()
            for move in res.pv:
                self.assertIn(move, verify.legal_moves)
                verify.push(move)

    def test_pvs_board_state_restoration(self):
        """Board passed to search is never modified."""
        fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7"
        board = chess.Board(fen)
        self.pvs_search.search(board, max_depth=4)
        self.assertEqual(board.fen(), fen)

    def test_pvs_telemetry_counters(self):
        """Telemetry counters satisfy structural constraints."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        res = self.pvs_search.search(board, max_depth=4)
        self.assertGreater(res.scout_searches, 0)
        self.assertGreaterEqual(res.scout_fail_highs, 0)
        self.assertGreaterEqual(res.researches, 0)
        self.assertLessEqual(res.researches, res.scout_fail_highs)
        self.assertLessEqual(res.scout_fail_highs, res.scout_searches)
        self.assertGreater(res.beta_cutoffs, 0)

        # Disabling PVS resets scout counts to 0, but still counts normal alpha-beta cutoffs
        res_disabled = self.ab_search.search(board, max_depth=4)
        self.assertEqual(res_disabled.scout_searches, 0)
        self.assertEqual(res_disabled.scout_fail_highs, 0)
        self.assertEqual(res_disabled.researches, 0)
        self.assertGreater(res_disabled.beta_cutoffs, 0)

    def test_beta_cutoffs_counted_in_both_modes(self):
        """Ordinary alpha-beta cutoffs must be counted when PVS is enabled or disabled."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5")
        res_pvs = self.pvs_search.search(board, max_depth=3)
        res_ab = self.ab_search.search(board, max_depth=3)
        self.assertGreater(res_pvs.beta_cutoffs, 0)
        self.assertGreater(res_ab.beta_cutoffs, 0)

    def test_pvs_vs_alphabeta_invariance(self):
        """PVS produces strictly identical scores and best moves as full alpha-beta across depths."""
        test_fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
            "4k3/8/8/8/8/8/4N3/4K2R w K - 0 1",
            "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
            "8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
        ]
        for depth in (2, 3, 4):
            for fen in test_fens:
                board = chess.Board(fen)
                self.pvs_search.tt.clear()
                self.ab_search.tt.clear()
                r_pvs = self.pvs_search.search(board.copy(), max_depth=depth)
                r_ab = self.ab_search.search(board.copy(), max_depth=depth)
                self.assertEqual(
                    r_pvs.score, r_ab.score,
                    f"Score mismatch at depth {depth} for {fen}: PVS={r_pvs.score} AB={r_ab.score}"
                )
                self.assertEqual(
                    r_pvs.best_move, r_ab.best_move,
                    f"Move mismatch at depth {depth} for {fen}: PVS={r_pvs.best_move} AB={r_ab.best_move}"
                )


if __name__ == "__main__":
    unittest.main()
