import unittest

import chess

from janus.search import JanusSearch


class HumanRobustnessTests(unittest.TestCase):
    def test_captures_hanging_queen(self):
        """Janus should immediately exploit an undefended queen."""
        board = chess.Board(
            "4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1"
        )

        result = JanusSearch().search(board, max_depth=2)

        self.assertEqual(
            result.best_move,
            chess.Move.from_uci("d1d5"),
        )

    def test_captures_hanging_rook(self):
        """Janus should capture a free rook rather than overlook it."""
        board = chess.Board(
            "4k3/8/8/3r4/8/8/8/3RK3 w - - 0 1"
        )

        result = JanusSearch().search(board, max_depth=2)

        self.assertEqual(
            result.best_move,
            chess.Move.from_uci("d1d5"),
        )

    def test_promotes_passed_pawn(self):
        """Janus should recognise a winning promotion opportunity."""
        board = chess.Board(
            "8/P7/8/8/8/4k3/8/4K3 w - - 0 1"
        )

        result = JanusSearch().search(board, max_depth=2)

        self.assertEqual(
            result.best_move,
            chess.Move.from_uci("a7a8q"),
        )

    def test_avoids_poisoned_queen_capture(self):
        board = chess.Board(
            "3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
        )

        result = JanusSearch().search(board, max_depth=4)

        self.assertIsNotNone(result.best_move)
        self.assertNotEqual(
            result.best_move,
            chess.Move.from_uci("d1d5"),
            "Janus must not capture the defended rook and lose its queen.",
        )


if __name__ == "__main__":
    unittest.main()
