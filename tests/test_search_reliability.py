import threading
import unittest

import chess

from janus.search import JanusSearch, MATE_THRESHOLD
from janus.uci import _score_to_uci


class SearchReliabilityTests(unittest.TestCase):
    def test_mate_in_one_and_uci_score(self):
        board = chess.Board("8/7k/5KQ1/8/8/8/8/8 w - - 0 1")
        result = JanusSearch().search(board, max_depth=3)
        self.assertIsNotNone(result.best_move)
        board.push(result.best_move)
        self.assertTrue(board.is_checkmate())
        self.assertGreaterEqual(result.score, MATE_THRESHOLD)
        self.assertEqual(_score_to_uci(result.score), "mate 1")

    def test_stalemate_is_draw(self):
        board = chess.Board("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1")
        self.assertTrue(board.is_stalemate())
        result = JanusSearch().search(board, max_depth=3)
        self.assertIsNone(result.best_move)
        self.assertEqual(result.score, 0)

    def test_search_does_not_mutate_root_board(self):
        board = chess.Board()
        before = board.fen()
        JanusSearch().search(board, max_depth=3)
        self.assertEqual(board.fen(), before)

    def test_root_reports_requested_depth_after_prior_deeper_search(self):
        board = chess.Board()
        engine = JanusSearch()
        first = engine.search(board, max_depth=4)
        second = engine.search(board, max_depth=2)
        self.assertEqual(first.depth, 4)
        self.assertEqual(second.depth, 2)
        self.assertGreater(second.nodes, 2)

    def test_stop_event_preserves_fallback_move(self):
        board = chess.Board()
        stop = threading.Event()
        stop.set()
        result = JanusSearch().search(board, max_depth=8, stop_event=stop)
        self.assertIsNotNone(result.best_move)
        self.assertEqual(result.depth, 0)
        self.assertEqual(board.fen(), chess.Board().fen())

    
    def test_finds_defensive_move_against_promotion_threat(self):
        board = chess.Board(
            "r2qk3/pp2pp2/2P2n1Q/1B2p2b/4P2p/2N5/PPP3PP/2K4R b q - 0 19"
        )

        result = JanusSearch().search(board, max_depth=4)

        self.assertIsNotNone(result.best_move)
        self.assertEqual(result.best_move, chess.Move.from_uci("e7e6"))


if __name__ == "__main__":
    unittest.main()
