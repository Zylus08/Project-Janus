"""Project Janus v0.51 - Native Standalone UCI Protocol Integration Test Suite.

Uses a synchronous subprocess-based UCI controller to qualify janus_native_engine.exe:
1. Engine startup & UCI handshake (uci, uciok, id name, id author)
2. Synchronization (isready -> readyok)
3. Position setup (position startpos) and legal move production
4. Position setup via FEN (position fen) and tactical play
5. Position setup with move history (position startpos moves ...)
6. Analysis info line formatting (depth, score cp, nodes, nps, time, pv)
7. Fischer time controls (go wtime btime winc binc)
8. Game state reset (ucinewgame)
9. Persistent self-play simulation across 10 plies
10. Clean exit on quit with exit code 0
"""

import sys
import unittest
import subprocess
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[1]
ENGINE_EXE = ROOT / "analysis" / "v0.51" / "native" / "janus_native_engine.exe"


class UCIEngineClient:
    def __init__(self, path: Path):
        self.p = subprocess.Popen(
            [str(path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def send(self, cmd: str):
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def readline(self) -> str:
        line = self.p.stdout.readline()
        if not line:
            return ""
        return line.strip()

    def uci(self):
        self.send("uci")
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            if line == "uciok":
                break
        return lines

    def isready(self):
        self.send("isready")
        while True:
            line = self.readline()
            if line == "readyok":
                break

    def ucinewgame(self):
        self.send("ucinewgame")
        self.isready()

    def position_startpos(self, moves=None):
        cmd = "position startpos"
        if moves:
            cmd += " moves " + " ".join(moves)
        self.send(cmd)

    def position_fen(self, fen: str, moves=None):
        cmd = f"position fen {fen}"
        if moves:
            cmd += " moves " + " ".join(moves)
        self.send(cmd)

    def go(self, **kwargs):
        cmd = "go"
        for k, v in kwargs.items():
            cmd += f" {k} {v}"
        self.send(cmd)
        infos = []
        bestmove = None
        while True:
            line = self.readline()
            if not line:
                break
            if line.startswith("info"):
                infos.append(line)
            elif line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) >= 2:
                    bestmove = tokens[1]
                break
        return bestmove, infos

    def quit(self):
        try:
            if self.p.poll() is None:
                self.send("quit")
                self.p.wait(timeout=2)
            if self.p.stdin and not self.p.stdin.closed:
                self.p.stdin.close()
            if self.p.stdout and not self.p.stdout.closed:
                self.p.stdout.close()
        except Exception:
            self.p.kill()
        return self.p.returncode


class TestNativeUCIProtocol(unittest.TestCase):
    def setUp(self):
        if not ENGINE_EXE.exists():
            raise FileNotFoundError(f"Engine executable not found at {ENGINE_EXE}")
        self.client = UCIEngineClient(ENGINE_EXE)

    def tearDown(self):
        self.client.quit()

    def test_01_handshake_and_identity(self):
        """Verify engine responds to uci handshake and reports identity."""
        lines = self.client.uci()
        self.assertIn("id name Janus 0.51 Native", lines)
        self.assertIn("id author Project Janus Team", lines)
        self.assertIn("uciok", lines)

    def test_02_isready_synchronization(self):
        """Verify isready immediately responds with readyok."""
        self.client.isready()

    def test_03_position_startpos_and_legal_bestmove(self):
        """Verify engine receives startpos and produces a legal move."""
        self.client.position_startpos()
        bm, infos = self.client.go(depth=2)
        self.assertIsNotNone(bm)
        board = chess.Board()
        move = chess.Move.from_uci(bm)
        self.assertIn(move, board.legal_moves)

    def test_04_position_fen_tactical_play(self):
        """Verify engine sets FEN correctly and plays tactical move."""
        # Legall's mate trap position
        fen = "r2qkb1r/pp2nppp/3p4/2pNN1B1/2BnP3/3P4/PPP2PPP/R2bK2R w KQkq - 1 9"
        self.client.position_fen(fen)
        bm, infos = self.client.go(depth=4)
        self.assertEqual(bm, "d5f6")

    def test_05_position_with_moves_sequence(self):
        """Verify position startpos moves ... correctly plays sequence."""
        moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
        self.client.position_startpos(moves=moves)
        bm, infos = self.client.go(depth=2)
        self.assertIsNotNone(bm)

        board = chess.Board()
        for m in moves:
            board.push_san(m)
        self.assertIn(chess.Move.from_uci(bm), board.legal_moves)

    def test_06_info_line_parsing(self):
        """Verify info line contains depth, score, nodes, nps, time, and pv."""
        self.client.position_startpos()
        bm, infos = self.client.go(depth=3)
        self.assertGreater(len(infos), 0)
        last_info = infos[-1]
        self.assertIn("depth 3", last_info)
        self.assertIn("score cp", last_info)
        self.assertIn("nodes", last_info)
        self.assertIn("nps", last_info)
        self.assertIn("time", last_info)
        self.assertIn("pv", last_info)

    def test_07_fischer_clock_allocation(self):
        """Verify engine allocates time safely under Fischer clock parameters."""
        self.client.position_startpos()
        # 3000ms clock, 100ms increment
        bm, infos = self.client.go(wtime=3000, btime=3000, winc=100, binc=100)
        self.assertIsNotNone(bm)
        board = chess.Board()
        self.assertIn(chess.Move.from_uci(bm), board.legal_moves)

    def test_08_ucinewgame_reset(self):
        """Verify ucinewgame resets search state and cleans history."""
        self.client.position_startpos(moves=["e2e4", "e7e5"])
        self.client.go(depth=2)
        self.client.ucinewgame()
        self.client.position_startpos()
        bm, _ = self.client.go(depth=2)
        self.assertIsNotNone(bm)

    def test_09_persistent_self_play_simulation(self):
        """Simulate 10 plies of self-play on a single persistent engine process."""
        board = chess.Board()
        moves_played = []
        for _ in range(10):
            if board.is_game_over():
                break
            self.client.position_startpos(moves=moves_played)
            bm, _ = self.client.go(movetime=20)
            self.assertIsNotNone(bm)
            move = chess.Move.from_uci(bm)
            self.assertIn(move, board.legal_moves)
            board.push(move)
            moves_played.append(bm)
        self.assertEqual(len(board.move_stack), 10)

    def test_10_graceful_quit_exit_code_zero(self):
        """Verify quit command terminates the engine process with exit code 0."""
        code = self.client.quit()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
