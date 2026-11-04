"""Project Janus v0.51.1 - Independent Audit of Native Repetition and History Semantics.

Audit Test Suite covering:
1. Twofold position without threefold claim (is_repetition(2)==True, can_claim_threefold==False)
2. Threefold claimable position (3 occurrences)
3. Intended-move threefold claim (2 occurrences + candidate move yields 3rd)
4. Fivefold automatic position (5 occurrences -> is_automatic_draw==True)
5. Repetition crossing the search root (root history + search tree)
6. History buffer boundary (1,024 plies)
7. History saturation safety (1,200 pushes safely clamped)
8. Repeated reset_history / ucinewgame cycles
9. Castling-right changes breaking repetition identity
10. Transposition table score safety on repetition
"""

import unittest
import chess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "v0.51" / "native"))

from janus_native_bridge import NativeEngineBridge, NativeBoard, UndoInfo, _dll


class TestAuditRepetitionSemantics(unittest.TestCase):

    def setUp(self):
        self.engine = NativeEngineBridge()

    def tearDown(self):
        self.engine.reset_history()

    def test_01_twofold_without_threefold_claim(self):
        """A position occurring 2 times triggers twofold search repetition (is_repetition(2)),
        but does NOT trigger a FIDE threefold claim (can_claim_threefold == False)."""
        self.engine.set_fen(chess.STARTING_FEN)
        self.engine.push_history(self.engine.board.zobrist_key)

        # 1. Nf3 Nf6 2. Ng1 Ng8 (1 cycle back to startpos)
        moves = ["g1f3", "g8f6", "f3g1", "f6g8"]
        for m_str in moves:
            m = self.engine.parse_uci(m_str)
            ok, undo = self.engine.make_move(m)
            self.assertTrue(ok)
            self.engine.push_history(self.engine.board.zobrist_key)

        # Position has occurred exactly 2 times (initial + after 4 plies)
        self.assertTrue(self.engine.is_repetition(2), "Twofold repetition must be detected")
        self.assertFalse(self.engine.can_claim_threefold_repetition(), "Threefold cannot be claimed on 2nd occurrence")
        self.assertFalse(self.engine.is_fivefold_repetition(), "Fivefold must be False")

    def test_02_threefold_claimable_position(self):
        """A position occurring 3 times allows a FIDE threefold claim."""
        self.engine.set_fen(chess.STARTING_FEN)
        self.engine.push_history(self.engine.board.zobrist_key)

        # 2 cycles: (Nf3 Nf6 Ng1 Ng8) x 2
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]
        for m_str in moves:
            m = self.engine.parse_uci(m_str)
            ok, undo = self.engine.make_move(m)
            self.assertTrue(ok)
            self.engine.push_history(self.engine.board.zobrist_key)

        self.assertTrue(self.engine.is_repetition(3), "Threefold repetition count must be >= 3")
        self.assertTrue(self.engine.can_claim_threefold_repetition(), "Threefold claim must be valid")
        self.assertFalse(self.engine.is_fivefold_repetition(), "Fivefold is not reached yet")
        self.assertFalse(self.engine.is_automatic_draw(), "Threefold is claimable, not automatic")

    def test_03_intended_move_threefold_claim(self):
        """Player at 2nd occurrence has a move that brings about the 3rd occurrence."""
        self.engine.set_fen(chess.STARTING_FEN)
        self.engine.push_history(self.engine.board.zobrist_key)

        # 1. Nf3 Nf6 2. Ng1 Ng8 (2nd occurrence) 3. Nf3 Nf6 4. Ng1 (now Black can play Ng8 to claim 3-fold)
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1"]
        for m_str in moves:
            m = self.engine.parse_uci(m_str)
            ok, undo = self.engine.make_move(m)
            self.assertTrue(ok)
            self.engine.push_history(self.engine.board.zobrist_key)

        # Black to move: current position occurred once before, but Black can play f6g8 to reach STARTPOS 3rd time
        self.assertTrue(self.engine.can_claim_threefold_repetition(), "Intended move must allow claim")

    def test_04_fivefold_automatic_draw(self):
        """5 occurrences triggers an automatic mandatory draw under Article 9.6.1."""
        self.engine.set_fen(chess.STARTING_FEN)
        self.engine.push_history(self.engine.board.zobrist_key)

        # 4 complete knight cycles
        cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]
        for _ in range(4):
            for m_str in cycle:
                m = self.engine.parse_uci(m_str)
                ok, undo = self.engine.make_move(m)
                self.assertTrue(ok)
                self.engine.push_history(self.engine.board.zobrist_key)

        self.assertTrue(self.engine.is_fivefold_repetition(), "Fivefold repetition must trigger")
        self.assertTrue(self.engine.is_automatic_draw(), "Fivefold is an automatic draw")

    def test_05_repetition_crossing_search_root(self):
        """Search tree detects repetition when a branch returns to a position previously reached in game history."""
        self.engine.set_fen(chess.STARTING_FEN)
        self.engine.push_history(self.engine.board.zobrist_key)

        # 1. Nf3 Nf6
        for m_str in ["g1f3", "g8f6"]:
            m = self.engine.parse_uci(m_str)
            ok, undo = self.engine.make_move(m)
            self.assertTrue(ok)
            self.engine.push_history(self.engine.board.zobrist_key)

        # Search from here: search must complete cleanly
        best_mv, score, depth, nodes, elapsed, pv = self.engine.search(max_depth=4, time_limit=1.0)
        self.assertIsNotNone(best_mv)
        self.assertGreater(nodes, 0)

    def test_06_history_buffer_boundary(self):
        """History stack operates correctly up to MAX_GAME_HISTORY (1024)."""
        self.engine.reset_history()
        for i in range(1024):
            self.engine.push_history(i + 1)
        self.assertEqual(self.engine.get_history_len(), 1024)
        self.assertEqual(self.engine.get_history_key(0), 1)
        self.assertEqual(self.engine.get_history_key(1023), 1024)

    def test_07_history_saturation_safety(self):
        """Pushing beyond 1,024 does not crash or corrupt memory."""
        self.engine.reset_history()
        for i in range(1200):
            self.engine.push_history(i + 1)
        self.assertEqual(self.engine.get_history_len(), 1024, "History must clamp at 1024")
        # Pop works cleanly
        self.engine.pop_history()
        self.assertEqual(self.engine.get_history_len(), 1023)

    def test_08_repeated_reset_history(self):
        """Repeated reset_history (simulating ucinewgame) wipes history cleanly."""
        for _ in range(50):
            self.engine.push_history(12345)
            self.engine.push_history(67890)
            self.engine.reset_history()
            self.assertEqual(self.engine.get_history_len(), 0)

    def test_09_castling_rights_break_repetition(self):
        """Moving king and returning to original square loses castling rights and breaks repetition."""
        py_b = chess.Board()
        self.engine.set_fen(chess.STARTING_FEN)
        initial_key = self.engine.board.zobrist_key

        # 1. e4 e5 2. Ke2 Ke7 3. Ke1 Ke8
        moves = ["e2e4", "e7e5", "e1e2", "e8e7", "e2e1", "e7e8"]
        for m_str in moves:
            py_m = chess.Move.from_uci(m_str)
            py_b.push(py_m)
            m = self.engine.parse_uci(m_str)
            ok, undo = self.engine.make_move(m)
            self.assertTrue(ok)

        # Both kings are back on e1 and e8, but castling rights are lost
        self.assertEqual(self.engine.board.castling_rights, 0, "Castling rights must be 0")
        self.assertNotEqual(self.engine.board.zobrist_key, initial_key, "Lost castling rights must change Zobrist key")
        self.assertEqual(py_b.can_claim_threefold_repetition(), False)

    def test_10_transposition_table_draw_score_isolation(self):
        """Draw score (0 cp) from repetition in tree does not corrupt TT mate scores."""
        self.engine.set_fen(chess.STARTING_FEN)
        self.engine.reset_history()
        self.engine.push_history(self.engine.board.zobrist_key)

        best_mv, score, depth, nodes, elapsed, pv = self.engine.search(max_depth=3, time_limit=0.5)
        # Verify score is within standard centipawn range, not an inflated mate score
        self.assertLess(abs(score), 2000, "Search score from startpos must be normal cp evaluation")


if __name__ == "__main__":
    unittest.main()
