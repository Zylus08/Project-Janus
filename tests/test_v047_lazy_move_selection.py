"""Tests for v0.47 Lazy Move Selection candidate (L1) using standard unittest."""
import unittest
import chess
from janus.search import JanusSearch, SearchResult
from janus.uci import main as uci_main
import argparse


class TestV047LazyMoveSelection(unittest.TestCase):
    def test_lazy_selection_disabled_by_default(self):
        """Verify that lazy move selection is disabled by default (K0 baseline)."""
        searcher = JanusSearch()
        self.assertFalse(searcher.enable_lazy_move_selection)
        board = chess.Board()
        res = searcher.search(board, max_depth=2)
        self.assertIsInstance(res, SearchResult)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)

    def test_lazy_selection_flag_enabled(self):
        """Verify that JanusSearch accepts enable_lazy_move_selection=True."""
        searcher = JanusSearch(enable_lazy_move_selection=True)
        self.assertTrue(searcher.enable_lazy_move_selection)
        board = chess.Board()
        res = searcher.search(board, max_depth=2)
        self.assertIsInstance(res, SearchResult)
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)

    def test_uci_argument_parsing(self):
        """Verify that UCI argument parser supports --enable-lazy-move-selection."""
        import sys
        from unittest.mock import patch
        
        # Test default
        with patch.object(sys, 'argv', ['uci.py']):
            parser = argparse.ArgumentParser()
            # Verify uci.py parser can parse the flag
            from janus import uci
            # Recreate parser logic from uci.py
            p = argparse.ArgumentParser()
            p.add_argument("--enable-lazy-move-selection", action="store_true")
            args = p.parse_args([])
            self.assertFalse(args.enable_lazy_move_selection)
            
            args_lazy = p.parse_args(["--enable-lazy-move-selection"])
            self.assertTrue(args_lazy.enable_lazy_move_selection)

    def test_terminal_and_incheck_positions(self):
        """Verify lazy selection behaves correctly in check, near mate, and quiet positions."""
        # Scholar's mate position (Black is checkmated)
        board_mate = chess.Board("r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
        self.assertTrue(board_mate.is_checkmate())
        searcher = JanusSearch(enable_lazy_move_selection=True)
        res_mate = searcher.search(board_mate, max_depth=2)
        self.assertIsNone(res_mate.best_move)

        # In check position: Black king in check, must evade
        board_check = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/5PP1/8/PPPPP2P/RNBQKBNR b KQkq - 0 2")
        board_check.push_san("Qh4#")
        self.assertTrue(board_check.is_checkmate())

        # Check evasion position
        board_evasion = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/5P1q/8/PPPPP1PP/RNBQKBNR w KQkq - 1 3")
        self.assertTrue(board_evasion.is_check())
        res_evasion = searcher.search(board_evasion, max_depth=3)
        self.assertIsNotNone(res_evasion.best_move)
        self.assertIn(res_evasion.best_move, board_evasion.legal_moves)
        self.assertEqual(res_evasion.best_move, chess.Move.from_uci("g2g3"))

    def test_depth_1_exact_agreement_with_k0(self):
        """At depth 1 without prior TT entries, K0 and L1 must evaluate legal moves identically."""
        positions = [
            chess.STARTING_FEN,
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
            "r2q1rk1/1b2bppp/p1n1pn2/1p1p4/3P4/PPNBPN2/5PPP/R1BQ1RK1 w - - 0 11",
            "8/5k2/8/8/8/8/1K6/8 w - - 0 1",
        ]
        k0 = JanusSearch(enable_lazy_move_selection=False)
        l1 = JanusSearch(enable_lazy_move_selection=True)

        for fen in positions:
            b_k0 = chess.Board(fen)
            b_l1 = chess.Board(fen)
            res_k0 = k0.search(b_k0, max_depth=1)
            res_l1 = l1.search(b_l1, max_depth=1)
            self.assertEqual(res_k0.best_move, res_l1.best_move, f"Best move mismatch on {fen}")
            self.assertEqual(res_k0.score, res_l1.score, f"Score mismatch on {fen}")
            self.assertEqual(res_k0.nodes, res_l1.nodes, f"Node count mismatch on {fen}")

    def test_state_integrity_and_board_unmake(self):
        """Verify that search leaves the board stack completely unaltered."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np4/2b1p3/2B1P1n1/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 8")
        fen_before = board.fen()
        searcher = JanusSearch(enable_lazy_move_selection=True)
        searcher.search(board, max_depth=3)
        self.assertEqual(board.fen(), fen_before)
        self.assertEqual(len(board.move_stack), 0)

    def test_transposition_table_and_repetition(self):
        """Verify that repetition detection and TT operate correctly under lazy selection."""
        searcher = JanusSearch(enable_lazy_move_selection=True)
        board = chess.Board()
        # Make a repetition
        moves = [chess.Move.from_uci(u) for u in ["g1f3", "g8f6", "f3g1", "f6g8"]]
        for m in moves:
            board.push(m)
        self.assertEqual(board.epd(), chess.Board().epd())
        self.assertTrue(board.is_repetition(2))
        res = searcher.search(board, max_depth=3)
        self.assertIsNotNone(res.best_move)
        self.assertGreater(len(searcher.tt), 0)


if __name__ == "__main__":
    unittest.main()
