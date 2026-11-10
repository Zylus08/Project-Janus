#!/usr/bin/env python3
"""
Test history score range across a search tree.
"""

import subprocess
from pathlib import Path

EXE_PATH = Path(r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.exe")

def test_history_range():
    p = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Run a search on startpos to depth 8
    commands = [
        "uci",
        "isready",
        "ucinewgame",
        "isready",
        "position startpos",
        "go depth 8",
        "quit\n"
    ]
    out, _ = p.communicate("\n".join(commands))
    print("Search completed. Output length:", len(out))

if __name__ == "__main__":
    test_history_range()

