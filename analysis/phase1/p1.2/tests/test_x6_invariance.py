#!/usr/bin/env python3
"""
Test strict bit-exact invariance between frozen X6 control and newly compiled Janus Classical X with UCI_Variant X6.
"""

import subprocess
from pathlib import Path

FROZEN_X6 = Path(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.2\control\janus_classical_x6.exe")
NEW_ENGINE = Path(r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.exe")

TEST_POSITIONS = [
    # (name, fen, depth)
    ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 6),
    ("KiwiPete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 5),
    ("Middlegame Pos 3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 7),
    ("Tactical Pos 4", "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5", 6),
    ("Endgame Pos 5", "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", 8),
]

def run_engine(exe: Path, is_x6_mode: bool, fen: str, depth: int):
    p = subprocess.Popen(
        [str(exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    commands = ["uci", "isready"]
    if is_x6_mode:
        commands.append("setoption name UCI_Variant value X6")
    commands.append("ucinewgame")
    commands.append("isready")
    commands.append(f"position fen {fen}")
    commands.append(f"go depth {depth}")
    commands.append("quit\n")
    
    out, _ = p.communicate("\n".join(commands))
    
    # Parse last info depth line and bestmove
    last_info = None
    bestmove = None
    for line in out.splitlines():
        if line.startswith(f"info depth {depth}"):
            last_info = line
        elif line.startswith("bestmove"):
            bestmove = line.split()[1]
            
    return last_info, bestmove, out

def main():
    print("=== Testing Bit-Exact Parity (Frozen X6 vs New Engine in UCI_Variant X6) ===")
    all_passed = True
    for name, fen, depth in TEST_POSITIONS:
        info_x6, bm_x6, out_x6 = run_engine(FROZEN_X6, False, fen, depth)
        info_new, bm_new, out_new = run_engine(NEW_ENGINE, True, fen, depth)
        
        # Extract nodes and score
        def parse_line(line):
            toks = line.split()
            score = toks[toks.index("score") + 2] if "score" in toks else "?"
            nodes = toks[toks.index("nodes") + 1] if "nodes" in toks else "?"
            return score, nodes

        score_x6, nodes_x6 = parse_line(info_x6)
        score_new, nodes_new = parse_line(info_new)
        
        match = (score_x6 == score_new) and (nodes_x6 == nodes_new) and (bm_x6 == bm_new)
        status = "PASS" if match else "FAIL"
        if not match:
            all_passed = False
            
        print(f"[{status}] {name} (d={depth}):")
        print(f"  Frozen X6 : nodes={nodes_x6}, score={score_x6}, bestmove={bm_x6}")
        print(f"  New (X6)  : nodes={nodes_new}, score={score_new}, bestmove={bm_new}")
        if not match:
            print("  FAIL DETAILS:")
            print("  X6 stdout:\n", out_x6)
            print("  New stdout:\n", out_new)

    if all_passed:
        print("\nALL INVARIANCE TESTS PASSED! Strict bit-exact parity verified with frozen X6.")
    else:
        print("\nINVARIANCE TEST FAILED!")

if __name__ == "__main__":
    main()

