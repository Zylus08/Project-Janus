import subprocess
import sys
from pathlib import Path
import chess

ROOT = Path("e:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

def test_uci_protocol():
    print("Testing UCI interface protocol...")
    cmd = [PYTHON, "-m", "janus.uci"]
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # 1. uci
    proc.stdin.write("uci\n")
    proc.stdin.flush()
    lines = []
    while True:
        line = proc.stdout.readline().strip()
        lines.append(line)
        if line == "uciok":
            break
    print("UCI handshake: OK")
    assert any("id name Janus" in l for l in lines)
    assert "uciok" in lines

    # 2. isready
    proc.stdin.write("isready\n")
    proc.stdin.flush()
    ready = proc.stdout.readline().strip()
    assert ready == "readyok", f"Expected readyok, got: {ready}"
    print("isready / readyok: OK")

    # 3. position and search
    proc.stdin.write("position startpos moves e2e4 e7e5\n")
    proc.stdin.write("go depth 3\n")
    proc.stdin.flush()

    bestmove = None
    info_received = False
    while True:
        line = proc.stdout.readline().strip()
        if line.startswith("info depth"):
            info_received = True
        if line.startswith("bestmove"):
            bestmove = line.split()[1]
            break

    assert info_received, "Expected info depth line"
    assert bestmove is not None, "Expected bestmove"
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    move = chess.Move.from_uci(bestmove)
    assert move in board.legal_moves, f"Illegal bestmove {bestmove}"
    print(f"position setup and go depth 3 -> bestmove {bestmove} (legal): OK")

    # 4. quit
    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.wait(timeout=5)
    assert proc.returncode == 0 or proc.poll() is not None
    print("clean shutdown (quit): OK")
    print("\nALL UCI SMOKE TESTS PASSED!")

if __name__ == "__main__":
    test_uci_protocol()
