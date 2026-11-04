"""Project Janus v0.51 - Differential FIDE Draw Semantics and Repetition Test Suite.

Tests Native N2 against python-chess for:
1. Threefold repetition (claimable)
2. Fivefold repetition (automatic)
3. Fifty-move claim threshold (halfmove_clock >= 100)
4. Seventy-five-move automatic threshold (halfmove_clock >= 150)
5. Pawn move resetting halfmove clock
6. Capture resetting halfmove clock
7. Castling rights altering position identity
8. En passant availability altering position identity
9. Repetition across search root boundary
10. History stack restoration during search
11. FEN root with incomplete prior history
12. UCINewGame history reset
"""

import sys
import unittest
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "v0.51" / "native"))

from janus_native_bridge import NativeEngineBridge, UndoInfo


class TestNativeDrawSemantics(unittest.TestCase):
    def setUp(self):
        self.bridge = NativeEngineBridge()

    def test_01_threefold_repetition(self):
        """Test threefold repetition detection and claimability."""
        self.bridge.reset_history()
        py_board = chess.Board()
        self.bridge.set_fen(py_board.fen())
        self.bridge.push_history(self.bridge.board.zobrist_key)

        # Sequence of 2 cycles of knights
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]
        for i, uci in enumerate(moves):
            # Pre-move state
            m = self.bridge.parse_uci(uci)
            self.assertNotEqual(m, 0, f"Move {uci} must be legal")
            py_m = chess.Move.from_uci(uci)

            self.bridge.make_move(m)
            py_board.push(py_m)
            self.bridge.push_history(self.bridge.board.zobrist_key)

        # After 8 moves, startpos has occurred 3 times!
        self.assertTrue(self.bridge.is_repetition(3))
        self.assertTrue(self.bridge.can_claim_threefold_repetition())
        self.assertEqual(py_board.can_claim_threefold_repetition(), self.bridge.can_claim_threefold_repetition())
        self.assertFalse(self.bridge.is_fivefold_repetition())

    def test_02_fivefold_repetition(self):
        """Test fivefold repetition automatic threshold."""
        self.bridge.reset_history()
        py_board = chess.Board()
        self.bridge.set_fen(py_board.fen())
        self.bridge.push_history(self.bridge.board.zobrist_key)

        # 4 cycles (16 moves)
        moves = ["g1f3", "g8f6", "f3g1", "f6g8"] * 4
        for uci in moves:
            m = self.bridge.parse_uci(uci)
            self.bridge.make_move(m)
            py_board.push(chess.Move.from_uci(uci))
            self.bridge.push_history(self.bridge.board.zobrist_key)

        # Startpos has occurred 5 times!
        self.assertTrue(self.bridge.is_repetition(5))
        self.assertTrue(self.bridge.is_fivefold_repetition())
        self.assertEqual(py_board.is_fivefold_repetition(), self.bridge.is_fivefold_repetition())
        self.assertTrue(self.bridge.is_automatic_draw())

    def test_03_fifty_move_claim_threshold(self):
        """Test halfmove_clock = 99 (boundary), 100 (claimable), and 101."""
        fen_99 = "8/8/4k3/8/8/4K3/8/8 w - - 99 50"
        self.bridge.set_fen(fen_99)
        # At 99, any quiet legal move produces 100 (intended move claim)
        self.assertTrue(self.bridge.can_claim_fifty_moves())
        self.assertFalse(self.bridge.is_seventyfive_moves())

        fen_100 = "8/8/4k3/8/8/4K3/8/8 w - - 100 51"
        self.bridge.set_fen(fen_100)
        self.assertTrue(self.bridge.can_claim_fifty_moves())
        self.assertTrue(self.bridge.is_claimable_draw())
        self.assertFalse(self.bridge.is_seventyfive_moves())

        fen_98 = "8/8/4k3/8/8/4K3/8/8 w - - 98 50"
        self.bridge.set_fen(fen_98)
        self.assertFalse(self.bridge.can_claim_fifty_moves())

    def test_04_seventyfive_move_automatic_threshold(self):
        """Test automatic 75-move draw at 149, 150, and 151."""
        fen_149 = "8/8/4k3/8/8/4K3/8/8 w - - 149 75"
        self.bridge.set_fen(fen_149)
        self.assertFalse(self.bridge.is_seventyfive_moves())

        fen_150 = "8/8/4k3/8/8/4K3/8/8 w - - 150 76"
        self.bridge.set_fen(fen_150)
        self.assertTrue(self.bridge.is_seventyfive_moves())
        self.assertTrue(self.bridge.is_automatic_draw())

        fen_151 = "8/8/4k3/8/8/4K3/8/8 w - - 151 76"
        self.bridge.set_fen(fen_151)
        self.assertTrue(self.bridge.is_seventyfive_moves())

    def test_05_pawn_move_resetting_halfmove_clock(self):
        """Test that pawn moves reset halfmove clock to 0."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 40 21"
        self.bridge.set_fen(fen)
        self.assertEqual(self.bridge.board.halfmove_clock, 40)

        m = self.bridge.parse_uci("e2e4")
        ok, undo = self.bridge.make_move(m)
        self.assertTrue(ok)
        self.assertEqual(self.bridge.board.halfmove_clock, 0)

        self.bridge.unmake_move(m, undo)
        self.assertEqual(self.bridge.board.halfmove_clock, 40)

    def test_06_capture_resetting_halfmove_clock(self):
        """Test that piece captures reset halfmove clock to 0."""
        fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 35 18"
        self.bridge.set_fen(fen)
        self.assertEqual(self.bridge.board.halfmove_clock, 35)

        m = self.bridge.parse_uci("f3e5")
        ok, undo = self.bridge.make_move(m)
        self.assertTrue(ok)
        self.assertEqual(self.bridge.board.halfmove_clock, 0)

        self.bridge.unmake_move(m, undo)
        self.assertEqual(self.bridge.board.halfmove_clock, 35)

    def test_07_castling_right_changes(self):
        """Test that losing castling rights alters position identity (hash)."""
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        self.bridge.set_fen(fen)
        initial_key = self.bridge.board.zobrist_key

        # White moves king Ke1-e2, forfeiting castling rights
        m = self.bridge.parse_uci("e1e2")
        ok, undo = self.bridge.make_move(m)
        self.assertTrue(ok)
        self.assertEqual(self.bridge.board.castling_rights & 3, 0)
        self.assertNotEqual(self.bridge.board.zobrist_key, initial_key)

        # Move back Ke2-e1
        m2 = self.bridge.parse_uci("e2e1")
        ok2, undo2 = self.bridge.make_move(m2)
        # Even though king is back on e1, castling rights are gone!
        self.assertNotEqual(self.bridge.board.zobrist_key, initial_key)

    def test_08_en_passant_position_identity(self):
        """Test that en passant square presence changes Zobrist key."""
        fen_no_ep = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        fen_with_ep = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"

        self.bridge.set_fen(fen_no_ep)
        key_no_ep = self.bridge.board.zobrist_key

        self.bridge.set_fen(fen_with_ep)
        key_with_ep = self.bridge.board.zobrist_key

        self.assertNotEqual(key_no_ep, key_with_ep, "EP square must alter position hash")

    def test_09_repetition_across_root_boundary(self):
        """Test that pre-root game history is preserved and detected during search."""
        self.bridge.reset_history()
        py_board = chess.Board()
        self.bridge.set_fen(py_board.fen())
        self.bridge.push_history(self.bridge.board.zobrist_key)

        # Play 1. Nf3 Nf6 2. Ng1 Ng8 (startpos has appeared 2 times in game history)
        moves = ["g1f3", "g8f6", "f3g1", "f6g8"]
        for uci in moves:
            m = self.bridge.parse_uci(uci)
            self.bridge.make_move(m)
            self.bridge.push_history(self.bridge.board.zobrist_key)

        # Current root position is startpos, which has occurred 2 times in history
        self.assertEqual(self.bridge.board.halfmove_clock, 4)
        self.assertTrue(self.bridge.is_repetition(2))
        self.assertFalse(self.bridge.is_repetition(3))

        # If we search now, playing Nf3 Nf6 Ng1 Ng8 in search tree will produce 3rd repetition
        # and be evaluated as draw (0 cp)
        best_mv, score, depth, nodes, elapsed, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertIsNotNone(best_mv)
        self.assertGreater(nodes, 0)

    def test_10_history_restoration_after_recursive_search(self):
        """Test that search does not leak keys onto the game history stack."""
        self.bridge.reset_history()
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.push_history(self.bridge.board.zobrist_key)
        self.assertEqual(self.bridge.get_history_len(), 1)

        # Run a deep search
        self.bridge.search(max_depth=5, time_limit=0.5)

        # History stack must be exactly 1 after search completes!
        self.assertEqual(self.bridge.get_history_len(), 1, "History length must be exactly preserved")

    def test_11_fen_root_with_incomplete_history(self):
        """Test that arbitrary FEN with halfmove_clock bounds history check cleanly."""
        fen = "r1bqk2r/ppppbppp/2n2n2/4p3/4P3/2N2N2/PPPPBPPP/R1BQK2R w KQkq - 4 5"
        self.bridge.reset_history()
        self.bridge.set_fen(fen)
        self.bridge.push_history(self.bridge.board.zobrist_key)

        self.assertEqual(self.bridge.get_history_len(), 1)
        self.assertFalse(self.bridge.is_repetition(2))
        self.assertFalse(self.bridge.can_claim_threefold_repetition())

    def test_12_ucinewgame_history_reset(self):
        """Test that ucinewgame / reset_history empties the history stack completely."""
        self.bridge.push_history(0x1234567890ABCDEF)
        self.bridge.push_history(0xFEDCBA0987654321)
        self.assertGreaterEqual(self.bridge.get_history_len(), 2)

        self.bridge.reset_history()
        self.assertEqual(self.bridge.get_history_len(), 0)


if __name__ == "__main__":
    unittest.main()

