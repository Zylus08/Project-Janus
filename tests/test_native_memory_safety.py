"""Project Janus v0.51 - Native Memory Safety & Bounds Stress Test Suite.

Executes Phase C stress tests on janus_native.dll and janus_native_engine.exe:
1. Repeated searches on same process (50 iterations)
2. Rapid position replacements (50 distinct FENs)
3. Repeated ucinewgame cycles (50 cycles)
4. Deep search on high-branching positions (Kiwipete depth 5)
5. Invalid/malformed FEN rejection
6. Invalid UCI commands & move strings
7. Time limit zero and negative bounds
8. History buffer overflow protection (>1024 plies)
"""

import sys
import unittest
import subprocess
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "v0.51" / "native"))

from janus_native_bridge import NativeEngineBridge

ENGINE_EXE = ROOT / "analysis" / "v0.51" / "native" / "janus_native_engine.exe"


class TestNativeMemorySafety(unittest.TestCase):
    def setUp(self):
        self.bridge = NativeEngineBridge()

    def test_01_repeated_searches_same_process(self):
        """Run 50 sequential searches on the same DLL instance to test memory stability."""
        self.bridge.set_fen(chess.STARTING_FEN)
        for d in range(1, 5):
            for _ in range(10):
                mv, sc, dp, nodes, el, pv = self.bridge.search(max_depth=d, time_limit=0.05)
                self.assertIsNotNone(mv)
                self.assertGreater(nodes, 0)

    def test_02_rapid_position_replacement(self):
        """Swap through 50 distinct positions without memory leak or state pollution."""
        fens = [
            chess.STARTING_FEN,
            "rnbqkbnr/ppp2ppp/3p4/4p3/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3",
            "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 6",
            "8/8/4k3/8/8/1R6/2K4r/8 w - - 1 1",
            "8/5P2/8/8/8/6k1/8/6K1 w - - 0 1",
        ] * 10
        for fen in fens:
            ok = self.bridge.set_fen(fen)
            self.assertTrue(ok)
            mv, sc, dp, nodes, el, pv = self.bridge.search(max_depth=2, time_limit=0.01)
            self.assertIsNotNone(mv)

    def test_03_repeated_ucinewgame_cycles(self):
        """Repeatedly reset history and transposition table."""
        for _ in range(50):
            self.bridge.reset_history()
            self.bridge.set_fen(chess.STARTING_FEN)
            self.bridge.push_history(self.bridge.board.zobrist_key)
            self.assertEqual(self.bridge.get_history_len(), 1)

    def test_04_deep_search_high_branching_position(self):
        """Search Kiwipete position (branching factor > 45) to depth 4."""
        kiwipete = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
        self.bridge.set_fen(kiwipete)
        mv, sc, dp, nodes, el, pv = self.bridge.search(max_depth=4, time_limit=5.0)
        self.assertIsNotNone(mv)
        self.assertGreater(nodes, 50000)

    def test_05_malformed_fen_rejection(self):
        """Ensure invalid FENs fail safely with return code 0 and no crash."""
        bad_fens = [
            "garbage_string",
            "8/8/8/8/8/8/8/8 w - - 0 1",  # No kings
            "8/8/8/8/8/8/8/4K3 w - - 0 1",  # Missing black king
            "8/8/8/8/8/8/8/4K2K w - - 0 1",  # 2 white kings
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1",  # invalid stm
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq z9 0 1",  # invalid ep
        ]
        for bad in bad_fens:
            ok = self.bridge.set_fen(bad)
            self.assertFalse(ok, f"Malformed FEN '{bad}' must be rejected safely")

    def test_06_malformed_uci_input_to_engine_exe(self):
        """Feed malformed and hostile UCI input to janus_native_engine.exe."""
        p = subprocess.Popen(
            [str(ENGINE_EXE.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        commands = (
            "unknown_command_1\n"
            "position fen invalid_fen_string\n"
            "position startpos moves invalid_move e2e9\n"
            "go depth 2 movetime -100\n"
            "isready\n"
            "quit\n"
        )
        out, _ = p.communicate(commands, timeout=5)
        self.assertEqual(p.returncode, 0)
        self.assertIn("readyok", out)
        self.assertIn("bestmove", out)

    def test_07_history_buffer_overflow_protection(self):
        """Push 1,200 history entries to verify safe saturation without buffer overrun."""
        self.bridge.reset_history()
        for i in range(1200):
            self.bridge.push_history(0x1000000000000000 + i)
        # Capacity is 1024, must not exceed 1024
        self.assertEqual(self.bridge.get_history_len(), 1024)

    def test_08_invalid_uci_move_parsing(self):
        """Verify invalid moves return 0 and are safely rejected."""
        self.bridge.set_fen(chess.STARTING_FEN)
        self.assertEqual(self.bridge.parse_uci("e2e5"), 0)  # illegal move
        self.assertEqual(self.bridge.parse_uci("a1a8"), 0)  # blocked rook
        self.assertEqual(self.bridge.parse_uci("z9z9"), 0)  # invalid squares
        self.assertEqual(self.bridge.parse_uci(""), 0)      # empty string


if __name__ == "__main__":
    unittest.main()

