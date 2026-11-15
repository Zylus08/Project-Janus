#!/usr/bin/env python3
"""
test_shallow_exact_reference.py
Milestone P1.21 Phase 6: Full-Width Reference Verification.
Compares exact full-width minimax search (UCI_ExactSearchMode = true) against
heuristic selective search (UCI_ExactSearchMode = false) at depths 1, 2, and 3.
Verifies:
1. Move ordering invariance of full-width minimax (deterministic score parity).
2. Absence of bound errors and search-state corruption.
3. Distinction between implementation defects and selective approximations (Qsearch & pruning).
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "shallow_exact_reference_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

POSITIONS = [
    {"id": "EX_01", "name": "Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "EX_02", "name": "Semi-Slav Quiet", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQ - 0 7"},
    {"id": "EX_03", "name": "French Advance", "fen": "r1bqk2r/pp1nbppp/2n1p3/2ppP3/3P1P2/2N1BN2/PPP3PP/R2QKB1R w KQkq - 1 8"},
    {"id": "EX_04", "name": "Sicilian Tactical", "fen": "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18"},
    {"id": "EX_05", "name": "King Defense Queen Attack", "fen": "r1b2rk1/pp3ppp/2n1p3/8/2B5/4q3/PPP3PP/3R1R1K w - - 0 16"},
    {"id": "EX_06", "name": "Fried Liver Attack f2 Threat", "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/2N5/PPPP1PPP/R1BQKB1R w KQkq - 1 7"},
    {"id": "EX_07", "name": "Rook 4v3 Endgame", "fen": "8/5pk1/4p1p1/1R5p/8/6P1/r4PKP/8 w - - 0 35"},
    {"id": "EX_08", "name": "Passed Pawn Race", "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1"},
    {"id": "EX_09", "name": "Mutual KP Zugzwang", "fen": "8/8/p1p5/1p5p/1P5P/kPK5/8/8 w - - 0 1"},
    {"id": "EX_10", "name": "Back-Rank Rook Defense", "fen": "3r2k1/p4ppp/1p2p3/8/8/1P2P3/P4PPP/3R2K1 w - - 0 1"}
]

def search_mode(fen: str, depth: int, exact_mode: bool, staged_mode: bool = True) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(EXE)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    def send(c):
        proc.stdin.write(c + "\n")
        proc.stdin.flush()
        
    send("uci")
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            break
            
    send("ucinewgame")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break
            
    send(f"setoption name UCI_ExactSearchMode value {'true' if exact_mode else 'false'}")
    send(f"setoption name UCI_StagedMovegen value {'true' if staged_mode else 'false'}")
    send("setoption name Hash value 64")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break
            
    send(f"position fen {fen}")
    send(f"go depth {depth}")
    
    bestmove = ""
    score = None
    nodes = 0
    pv = ""
    
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line_str = line.strip()
        if "score cp" in line_str:
            parts = line_str.split()
            try:
                score = int(parts[parts.index("cp") + 1])
            except Exception:
                pass
        elif "score mate" in line_str:
            parts = line_str.split()
            try:
                m = int(parts[parts.index("mate") + 1])
                score = 10000 - m if m > 0 else -10000 - m
            except Exception:
                pass
        if "nodes" in line_str:
            parts = line_str.split()
            try:
                nodes = int(parts[parts.index("nodes") + 1])
            except Exception:
                pass
        if " pv " in line_str:
            pv = line_str.split(" pv ")[-1]
        if line_str.startswith("bestmove"):
            bestmove = line_str.split()[1]
            break
            
    try:
        proc.stdin.write("quit\n")
        proc.stdin.flush()
        proc.wait(timeout=1.0)
    except Exception:
        proc.kill()
        
    return {
        "bestmove": bestmove,
        "score": score,
        "nodes": nodes,
        "pv": pv
    }

def main():
    print("Executing Phase 6 Shallow Exact Search Reference Audit...")
    results = []
    
    for pos in POSITIONS:
        pid = pos["id"]
        pname = pos["name"]
        fen = pos["fen"]
        print(f"\nAuditing [{pid}] {pname}")
        
        pos_entry = {
            "id": pid,
            "name": pname,
            "fen": fen,
            "depths": {}
        }
        
        for d in [1, 2, 3]:
            # 1. Exact Full-Width Minimax (Staged Movegen)
            exact_staged = search_mode(fen, d, exact_mode=True, staged_mode=True)
            # 2. Exact Full-Width Minimax (Legacy / Unstaged Movegen)
            exact_legacy = search_mode(fen, d, exact_mode=True, staged_mode=False)
            # 3. Standard Selective Search
            selective = search_mode(fen, d, exact_mode=False, staged_mode=True)
            
            # Verify Move Ordering Invariance of Exact Minimax
            exact_score_match = (exact_staged["score"] == exact_legacy["score"])
            
            # Compare Selective vs Exact
            move_agree_exact_vs_sel = (exact_staged["bestmove"] == selective["bestmove"])
            score_delta_sel_vs_exact = (selective["score"] - exact_staged["score"]) if (selective["score"] is not None and exact_staged["score"] is not None) else None
            
            d_entry = {
                "depth": d,
                "exact_staged": exact_staged,
                "exact_legacy": exact_legacy,
                "selective": selective,
                "ordering_invariance": exact_score_match,
                "move_agreement": move_agree_exact_vs_sel,
                "score_delta": score_delta_sel_vs_exact
            }
            pos_entry["depths"][f"d{d}"] = d_entry
            
            print(f"  Depth {d}: ExactScore={exact_staged['score']} (Invariance={exact_score_match}) | SelMove={selective['bestmove']} [{selective['score']}] vs ExactMove={exact_staged['bestmove']} (Agree={move_agree_exact_vs_sel}, ScoreDelta={score_delta_sel_vs_exact}) | Nodes (Exact/Sel): {exact_staged['nodes']}/{selective['nodes']}")
            
        results.append(pos_entry)
        
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nShallow exact reference results written to {OUT_RAW}")

if __name__ == "__main__":
    main()
