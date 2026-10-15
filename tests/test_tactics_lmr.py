"""Tactical validation suite comparing search decisions with LMR enabled and disabled."""
import unittest
import chess

from janus.search import JanusSearch


class LMRTacticalValidationTests(unittest.TestCase):
    def setUp(self):
        self.s_base = JanusSearch(enable_lmr=False)
        self.s_lmr = JanusSearch(enable_lmr=True)

    def test_mate_in_one_preserved(self):
        """Mate in 1 is preserved with LMR enabled."""
        board = chess.Board("8/7k/5K2/6Q1/8/8/8/8 w - - 0 1")
        r_base = self.s_base.search(board.copy(), max_depth=3)
        r_lmr = self.s_lmr.search(board.copy(), max_depth=3)

        self.assertEqual(r_lmr.best_move, chess.Move.from_uci("g5g7"))
        self.assertEqual(r_lmr.score, r_base.score)

    def test_mate_in_two_preserved(self):
        """Mate in 2 / Scholar's mate attack is resolved with LMR enabled."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5")
        r_base = self.s_base.search(board.copy(), max_depth=3)
        r_lmr = self.s_lmr.search(board.copy(), max_depth=3)

        self.assertEqual(r_lmr.best_move, r_base.best_move)
        self.assertEqual(r_lmr.score, r_base.score)

    def test_promotion_tactic_preserved(self):
        """Promotion tactic preserves winning move and score."""
        board = chess.Board("8/P7/8/8/8/4k3/8/4K3 w - - 0 1")
        r_base = self.s_base.search(board.copy(), max_depth=3)
        r_lmr = self.s_lmr.search(board.copy(), max_depth=3)

        self.assertEqual(r_lmr.best_move, chess.Move.from_uci("a7a8q"))
        self.assertEqual(r_lmr.score, r_base.score)

    def test_defensive_move_against_threat_preserved(self):
        """Defensive move preventing mate/promotion threat is found under LMR."""
        board = chess.Board("r2qk3/pp2pp2/2P2n1Q/1B2p2b/4P2p/2N5/PPP3PP/2K4R b q - 0 19")
        r_base = self.s_base.search(board.copy(), max_depth=4)
        r_lmr = self.s_lmr.search(board.copy(), max_depth=4)

        self.assertEqual(r_lmr.best_move, chess.Move.from_uci("e7e6"))
        self.assertEqual(r_lmr.score, r_base.score)

    def test_knight_fork_tactics_preserved(self):
        """Tactical knight fork winning a rook or queen is identified."""
        # White can play Nc7+ forking King on e8 and Rook on a8
        board = chess.Board("r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R1B1K2R w KQkq - 0 1")
        r_base = self.s_base.search(board.copy(), max_depth=3)
        r_lmr = self.s_lmr.search(board.copy(), max_depth=3)

        self.assertEqual(r_lmr.best_move, chess.Move.from_uci("d5c7"))
        self.assertEqual(r_lmr.score, r_base.score)

    def test_pin_skewer_tactic_preserved(self):
        """Tactical pin along file is preserved."""
        # White Rook pins Black Knight to Black King
        board = chess.Board("4k3/8/8/4n3/8/8/8/4R1K1 w - - 0 1")
        r_base = self.s_base.search(board.copy(), max_depth=3)
        r_lmr = self.s_lmr.search(board.copy(), max_depth=3)

        self.assertEqual(r_lmr.best_move, r_base.best_move)
        self.assertEqual(r_lmr.score, r_base.score)


if __name__ == "__main__":
    unittest.main()
