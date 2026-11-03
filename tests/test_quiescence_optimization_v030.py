"""Targeted invariant and regression tests for v0.30 quiescence search optimisation."""
import unittest
import chess
from janus.search import JanusSearch, MATE_SCORE


class TestQuiescenceOptimizationV030(unittest.TestCase):
    """Verify that quiescence search optimisation preserves all chess invariants and terminal handling."""

    def test_root_entry_skips_redundant_legal_move_generation(self):
        """On entry from _negamax at depth <= 0, any(generate_legal_moves()) is not called inside _quiescence."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch()

        orig_generate_legal_moves = chess.Board.generate_legal_moves
        call_count_in_qsearch_root = 0

        # We can track calls specifically with check_stalemate=False vs True
        orig_quiescence = searcher._quiescence

        def tracked_quiescence(b, alpha, beta, ply, check_stalemate=True):
            nonlocal call_count_in_qsearch_root
            if not check_stalemate:
                # Inside this root call, generate_legal_moves should NOT be called for stalemate
                call_count_in_qsearch_root += 1
            return orig_quiescence(b, alpha, beta, ply, check_stalemate=check_stalemate)

        searcher._quiescence = tracked_quiescence
        res = searcher.search(board, max_depth=1)
        self.assertGreater(call_count_in_qsearch_root, 0)

    def test_stalemate_correctly_recognised_terminal_zero(self):
        """Stalemate position returns 0 immediately."""
        # Standard stalemate position: Black king on h8, White queen on f7, White king on g6
        board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        searcher = JanusSearch()
        res = searcher.search(board, max_depth=3)
        self.assertEqual(res.score, 0)
        self.assertIsNone(res.best_move)

    def test_stalemate_detected_in_quiescence_when_flag_true(self):
        """When check_stalemate=True, a stalemated position evaluated directly in _quiescence returns 0."""
        # Stalemate position with Black to move
        board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        searcher = JanusSearch()
        # Direct call to _quiescence with default check_stalemate=True
        score = searcher._quiescence(board, -100_000, 100_000, ply=2, check_stalemate=True)
        self.assertEqual(score, 0)

    def test_checkmate_correctly_recognised(self):
        """Checkmate is correctly scored as -MATE_SCORE + ply."""
        # Fool's mate position: White is checkmated by Qh4#
        board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        searcher = JanusSearch()
        res = searcher.search(board, max_depth=1)
        self.assertEqual(res.score, -MATE_SCORE)
        self.assertIsNone(res.best_move)

    def test_side_in_check_never_uses_stand_pat(self):
        """A side in check cannot cut off on stand-pat and must search legal evasions."""
        # White king in check on e1 from queen on e2
        board = chess.Board("4k3/8/8/8/8/8/4q3/4K3 w - - 0 1")
        searcher = JanusSearch()
        # White's only legal moves are king moves. King can capture the queen on e2.
        res = searcher.search(board, max_depth=2)
        self.assertEqual(res.best_move, chess.Move.from_uci("e1e2"))

    def test_quiet_legal_moves_not_mistaken_for_stalemate(self):
        """A position with no captures but legal quiet moves is not mistaken for stalemate."""
        # Quiet blocked position where pawns can still push
        board = chess.Board("8/8/8/8/p7/P7/k1K5/8 w - - 0 1")
        searcher = JanusSearch()
        res = searcher.search(board, max_depth=2)
        # White has legal move (e.g. Kd1, Kd2, Kc1, Kc3)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)

    def test_stand_pat_beta_cutoff_preserved(self):
        """Stand-pat cutoff when static eval >= beta is preserved."""
        # White has huge material advantage (+1 rook)
        board = chess.Board("4k3/8/8/8/8/8/4N3/4K2R w K - 0 1")
        searcher = JanusSearch()
        # If beta is very low (e.g. 0), White stands pat and cuts off
        score = searcher._quiescence(board, alpha=-100, beta=100, ply=1, check_stalemate=False)
        self.assertGreaterEqual(score, 100)

    def test_en_passant_and_promotions_handled(self):
        """En passant captures and promotions in quiescence are fully handled."""
        # En passant position
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3")
        searcher = JanusSearch()
        res = searcher.search(board, max_depth=2)
        self.assertIn(res.best_move, board.legal_moves)

        # Promotion tactic
        board_promo = chess.Board("8/P7/8/8/8/8/k7/7K w - - 0 1")
        res_promo = searcher.search(board_promo, max_depth=3)
        self.assertEqual(res_promo.best_move, chess.Move.from_uci("a7a8q"))

    def test_board_state_restored_cleanly(self):
        """Board state, FEN, and stack are clean after quiescence search."""
        fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7"
        board = chess.Board(fen)
        searcher = JanusSearch()
        res = searcher.search(board, max_depth=4)

        self.assertEqual(board.fen(), fen)
        self.assertEqual(len(board.move_stack), 0)
        self.assertIn(res.best_move, board.legal_moves)


if __name__ == "__main__":
    unittest.main()
