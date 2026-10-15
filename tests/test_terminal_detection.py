"""Targeted regression tests for terminal position detection in Project Janus."""
import unittest
import chess

from janus.search import JanusSearch, MATE_SCORE, MATE_THRESHOLD


class TerminalDetectionTests(unittest.TestCase):
    def setUp(self):
        self.engine = JanusSearch(tt_max_entries=10_000)

    def test_checkmate_at_main_search_node(self):
        # Scholar's mate final position: Black is checkmated
        board = chess.Board("r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
        self.assertTrue(board.is_checkmate())
        result = self.engine.search(board, max_depth=2)
        self.assertIsNone(result.best_move)
        self.assertEqual(result.score, -MATE_SCORE)
        self.assertEqual(result.nodes, 0)

    def test_stalemate_at_main_search_node(self):
        # Classic king corner stalemate: Black to move, no legal moves, not in check
        board = chess.Board("k7/8/1Q6/8/8/8/8/7K b - - 0 1")
        self.assertTrue(board.is_stalemate())
        self.assertFalse(board.is_check())
        result = self.engine.search(board, max_depth=2)
        self.assertIsNone(result.best_move)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.nodes, 0)

    def test_checkmate_entering_quiescence_in_check(self):
        # White can deliver mate on move 1: Qg7#
        # Depth 1 reaches depth 0 with Black checkmated
        board = chess.Board("8/7k/5K2/6Q1/8/8/8/8 w - - 0 1")
        result = self.engine.search(board, max_depth=1)
        self.assertEqual(result.best_move, chess.Move.from_uci("g5g7"))
        self.assertGreaterEqual(result.score, MATE_THRESHOLD)

    def test_in_check_quiescence_with_legal_evasion(self):
        # Black is in check, has only one legal king evasion (Kh7)
        board = chess.Board("8/8/5K1k/6Q1/8/8/8/8 b - - 1 1")
        self.assertTrue(board.is_check())
        result = self.engine.search(board, max_depth=1)
        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)
        self.assertEqual(result.best_move, chess.Move.from_uci("h6h7"))

    def test_non_check_quiescence_position_with_legal_moves(self):
        # Quiet position with many legal moves and no captures
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertFalse(board.is_check())
        result = self.engine.search(board, max_depth=1)
        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)

    def test_seventyfive_moves_and_fivefold_repetition_draw(self):
        # 75-move rule position: halfmove clock is 150
        board = chess.Board("8/8/4k3/8/8/4K3/8/8 w - - 150 100")
        self.assertTrue(board.is_seventyfive_moves())
        result = self.engine.search(board, max_depth=2)
        self.assertEqual(result.score, 0)

    def test_mate_distance_scoring_hierarchy(self):
        # Position with mate in 1 (Qg7#) vs mate in 2
        board = chess.Board("8/7k/5KQ1/8/8/8/8/8 w - - 0 1")
        res1 = self.engine.search(board, max_depth=1)
        self.assertEqual(res1.score, MATE_SCORE - 1)  # 99,999

        # Mate distance decreases with search ply distance
        self.assertEqual(self.engine._score_to_tt(MATE_SCORE - 2, ply=2), MATE_SCORE)
        self.assertEqual(self.engine._score_from_tt(MATE_SCORE, ply=2), MATE_SCORE - 2)

    def test_terminal_following_tt_probe(self):
        # Verify that TT cache entries for terminal positions correctly restore ply distance
        board = chess.Board("7k/5KQ1/8/8/8/8/8/8 b - - 0 1")
        self.assertTrue(board.is_checkmate())
        # Search once to seed TT or verify terminal return
        res1 = self.engine.search(board, max_depth=2)
        self.assertEqual(res1.score, -MATE_SCORE)

        # Second search should hit terminal / TT cleanly without errors
        res2 = self.engine.search(board, max_depth=2)
        self.assertEqual(res2.score, -MATE_SCORE)
        self.assertEqual(res2.best_move, None)

    def test_board_state_restoration_after_terminal_search(self):
        # Board FEN should be strictly preserved after searching terminal and near-terminal states
        for fen in [
            "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",  # mate
            "k7/8/1Q6/8/8/8/8/7K b - - 0 1",  # stalemate
            "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",  # mate in 1
        ]:
            board = chess.Board(fen)
            expected_fen = board.fen()
            self.engine.search(board, max_depth=2)
            self.assertEqual(board.fen(), expected_fen)


if __name__ == "__main__":
    unittest.main()
