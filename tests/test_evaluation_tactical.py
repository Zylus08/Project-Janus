import unittest

import chess

from janus.evaluation import evaluate_white


class EvaluationTacticalBlindSpotTests(unittest.TestCase):
    def test_quiet_queen_retreats_have_same_static_score(self):
        fen = "3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
        moves = ["d1e2", "d1a4", "d1f3", "d1g4"]
        scores = []

        for uci in moves:
            board = chess.Board(fen)
            move = chess.Move.from_uci(uci)
            self.assertIn(move, board.legal_moves)
            board.push(move)
            scores.append(evaluate_white(board))

        self.assertEqual(len(set(scores)), 1)

    def test_poisoned_capture_and_recapture_restore_material_imbalance(self):
        fen = "3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
        board = chess.Board(fen)

        baseline = evaluate_white(board)

        # White captures the rook.
        board.push_uci("d1d5")
        after_capture = evaluate_white(board)

        # Black's queen recaptures White's queen.
        board.push_uci("d8d5")
        after_recapture = evaluate_white(board)

        self.assertGreater(after_capture, baseline)
        self.assertLess(after_recapture, baseline)


if __name__ == "__main__":
    unittest.main()
