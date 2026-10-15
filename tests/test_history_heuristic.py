"""Targeted regression tests for the quiet-move history heuristic in Project Janus."""
import unittest
import chess

from janus.search import JanusSearch, MAX_HISTORY_SCORE


class HistoryHeuristicTests(unittest.TestCase):
    def setUp(self):
        self.engine = JanusSearch(tt_max_entries=10_000, enable_history=True)

    def test_history_scores_remain_bounded_under_repeated_updates(self):
        move = chess.Move.from_uci("g1f3")
        for _ in range(10_000):
            self.engine._update_history(move, depth=8)
        score = self.engine.history[move.from_square][move.to_square]
        self.assertEqual(score, MAX_HISTORY_SCORE)
        self.assertLess(score, 600_000)  # Strictly below Killer 2

    def test_captures_do_not_receive_history_updates(self):
        # Position where White knight can capture Black pawn on e5
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        capture_move = chess.Move.from_uci("f3e5")
        self.assertTrue(board.is_capture(capture_move))

        # Search position to cause cutoffs
        self.engine.search(board, max_depth=3)
        # Capture move must not have an entry in the quiet history table
        self.assertEqual(self.engine.history[capture_move.from_square][capture_move.to_square], 0)

    def test_promotions_do_not_receive_history_updates(self):
        # Position with passed pawn near promotion
        board = chess.Board("8/P7/8/8/8/4k3/8/4K3 w - - 0 1")
        promo_move = chess.Move.from_uci("a7a8q")
        self.engine.search(board, max_depth=3)
        self.assertEqual(self.engine.history[promo_move.from_square][promo_move.to_square], 0)

    def test_move_ordering_hierarchy_preserved(self):
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        tt_move = chess.Move.from_uci("c1e3")
        capture_move = chess.Move.from_uci("c4f7")
        killer1_move = chess.Move.from_uci("a2a3")
        killer2_move = chess.Move.from_uci("h2h3")
        hist_move = chess.Move.from_uci("c3a4")
        unscored_quiet = chess.Move.from_uci("g1h1")

        # Set up killers and history
        self.engine.killers[1][0] = killer1_move
        self.engine.killers[1][1] = killer2_move
        self.engine.history[hist_move.from_square][hist_move.to_square] = 400_000

        tt_score = self.engine._move_order_score(board, tt_move, tt_move=tt_move, ply=1)
        cap_score = self.engine._move_order_score(board, capture_move, tt_move=tt_move, ply=1)
        k1_score = self.engine._move_order_score(board, killer1_move, tt_move=tt_move, ply=1)
        k2_score = self.engine._move_order_score(board, killer2_move, tt_move=tt_move, ply=1)
        hist_score = self.engine._move_order_score(board, hist_move, tt_move=tt_move, ply=1)
        quiet_score = self.engine._move_order_score(board, unscored_quiet, tt_move=tt_move, ply=1)

        # Strict hierarchy verification
        self.assertGreater(tt_score, cap_score, "TT move must outrank capture")
        self.assertGreater(cap_score, k1_score, "Capture must outrank Killer 1")
        self.assertGreater(k1_score, k2_score, "Killer 1 must outrank Killer 2")
        self.assertGreater(k2_score, hist_score, "Killer 2 must outrank history move")
        self.assertGreater(hist_score, quiet_score, "History move must outrank unscored quiet move")
        self.assertEqual(quiet_score, 0)

    def test_move_ordering_responds_to_different_history_scores(self):
        board = chess.Board()
        move_a = chess.Move.from_uci("g1f3")
        move_b = chess.Move.from_uci("b1c3")

        self.engine.history[move_a.from_square][move_a.to_square] = 50
        self.engine.history[move_b.from_square][move_b.to_square] = 300

        score_a = self.engine._move_order_score(board, move_a)
        score_b = self.engine._move_order_score(board, move_b)
        self.assertGreater(score_b, score_a)

        ordered = self.engine._ordered_moves(board)
        idx_a = ordered.index(move_a)
        idx_b = ordered.index(move_b)
        self.assertLess(idx_b, idx_a, "Move B with higher history score must be ordered before Move A")

    def test_history_resets_between_independent_searches(self):
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        self.engine.search(board, max_depth=3)

        # Check that some history was populated
        total_history = sum(sum(row) for row in self.engine.history)
        self.assertGreater(total_history, 0)

        # Searching again initializes a fresh history table at root start
        # Directly test search() entry clears prior history
        new_board = chess.Board()
        self.engine.search(new_board, max_depth=1)
        # In a depth 1 search on startpos, there are no beta cutoffs below root (depth <= 0 is terminal/qsearch)
        # So history table will be entirely 0 after depth 1
        new_total_history = sum(sum(row) for row in self.engine.history)
        self.assertEqual(new_total_history, 0)

    def test_history_toggle_disables_updates_and_scoring(self):
        disabled_engine = JanusSearch(enable_history=False)
        move = chess.Move.from_uci("g1f3")
        disabled_engine._update_history(move, depth=4)
        self.assertEqual(disabled_engine.history[move.from_square][move.to_square], 0)

        board = chess.Board()
        score = disabled_engine._move_order_score(board, move)
        self.assertEqual(score, 0)

    def test_board_state_restoration_after_search(self):
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        fen_before = board.fen()
        self.engine.search(board, max_depth=3)
        self.assertEqual(board.fen(), fen_before)

    def test_returned_moves_are_legal(self):
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        result = self.engine.search(board, max_depth=3)
        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)
        for m in result.pv:
            self.assertIn(m, board.legal_moves)
            board.push(m)


    def test_ordered_moves_single_or_empty_move_short_circuit(self):
        # Empty board or position with 0 legal moves
        stalemate_board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertEqual(len(list(stalemate_board.legal_moves)), 0)
        self.assertEqual(self.engine._ordered_moves(stalemate_board), [])

        # Position with exactly 1 legal move: king corner evasion Kh7
        evasion_board = chess.Board("8/8/5K1k/6Q1/8/8/8/8 b - - 1 1")
        self.assertEqual(len(list(evasion_board.legal_moves)), 1)
        ordered = self.engine._ordered_moves(evasion_board)
        self.assertEqual(ordered, [chess.Move.from_uci("h6h7")])

    def test_ordered_moves_ranking_matches_move_order_score(self):
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        tt_move = chess.Move.from_uci("c1e3")
        self.engine.killers[1][0] = chess.Move.from_uci("a2a3")
        self.engine.history[chess.Move.from_uci("c3a4").from_square][chess.Move.from_uci("c3a4").to_square] = 200

        ordered = self.engine._ordered_moves(board, tt_move=tt_move, ply=1)
        # Verify that moves in ordered list have non-increasing scores
        scores = [self.engine._move_order_score(board, m, tt_move=tt_move, ply=1) for m in ordered]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
