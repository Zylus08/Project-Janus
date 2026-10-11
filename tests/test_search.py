import unittest
import chess

from janus.search import JanusSearch


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = JanusSearch(tt_max_entries=10_000)

    def test_returns_legal_move(self):
        board = chess.Board()
        result = self.engine.search(board, max_depth=2)
        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)
        self.assertGreaterEqual(result.depth, 1)

    def test_finds_mate_in_one(self):
        # White: Kf6, Qg7; Black: Kh8. White has Qg8#.
        board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        result = self.engine.search(board, max_depth=2)
        self.assertIsNotNone(result.best_move)
        board.push(result.best_move)
        self.assertTrue(board.is_checkmate())

    def test_does_not_mutate_root_board(self):
        board = chess.Board()
        before = board.fen()
        self.engine.search(board, max_depth=2)
        self.assertEqual(board.fen(), before)


if __name__ == "__main__":
    unittest.main()
