import unittest
import chess

from janus.evaluation import evaluate_white, evaluate_side_to_move


class EvaluationTests(unittest.TestCase):
    def test_start_position_is_near_balanced(self):
        board = chess.Board()
        self.assertLess(abs(evaluate_white(board)), 100)

    def test_side_to_move_sign_flips(self):
        board = chess.Board()
        white_score = evaluate_side_to_move(board)
        board.push_uci("e2e4")
        black_score = evaluate_side_to_move(board)
        self.assertEqual(black_score, -evaluate_white(board))
        self.assertIsInstance(white_score, int)

    def test_material_advantage(self):
        board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
        self.assertGreater(evaluate_white(board), 500)


if __name__ == "__main__":
    unittest.main()
