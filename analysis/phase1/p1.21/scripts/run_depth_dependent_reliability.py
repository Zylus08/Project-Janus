#!/usr/bin/env python3
"""
run_depth_dependent_reliability.py
Milestone P1.21 Phase 5: Depth-Dependent Search Reliability Audit.
Compares E0 (X22), E1 (X24 Backward Pawns), and E2 (X25 Connected Passers)
across depths 4, 5, 6, 7, 8 on 9 provenance-tracked archetypes:
1. Quiet middlegame
2. Tactical middlegame
3. Closed pawn structure
4. Open-file position
5. Rook endgame
6. Passed-pawn race
7. Zugzwang
8. Defensive quiet move
9. King attack
Measures root move stability, score trajectory, and pruning activity.
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
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "depth_dependent_reliability_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

PROVENANCE_SUITE = [
    # 1. Quiet middlegame
    {"id": "ARCH_01_QUIET", "archetype": "Quiet Middlegame", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQ - 0 7", "expected_concept": "Development / Piece Coordination"},
    # 2. Tactical middlegame
    {"id": "ARCH_02_TACTICAL", "archetype": "Tactical Middlegame", "fen": "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18", "expected_concept": "Tactical breakthrough d4e6"},
    # 3. Closed pawn structure
    {"id": "ARCH_03_CLOSED", "archetype": "Closed Pawn Structure", "fen": "r1bqk2r/pp1nbppp/2n1p3/2ppP3/3P1P2/2N1BN2/PPP3PP/R2QKB1R w KQkq - 1 8", "expected_concept": "French pawn chain tension"},
    # 4. Open-file position
    {"id": "ARCH_04_OPEN_FILE", "archetype": "Open-File Position", "fen": "r1b2rk1/pp3ppp/2n1p3/8/2B5/4q3/PPP3PP/3R1R1K w - - 0 16", "expected_concept": "Rook open d-file / Queen infiltration"},
    # 5. Rook endgame
    {"id": "ARCH_05_ROOK_END", "archetype": "Rook Endgame", "fen": "8/5pk1/4p1p1/1R5p/8/6P1/r4PKP/8 w - - 0 35", "expected_concept": "Rook 4v3 passive defense vs active cut"},
    # 6. Passed-pawn race
    {"id": "ARCH_06_PASSER_RACE", "archetype": "Passed-Pawn Race", "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1", "expected_concept": "Dynamic promotion timing"},
    # 7. Zugzwang
    {"id": "ARCH_07_ZUGZWANG", "archetype": "Zugzwang", "fen": "8/8/p1p5/1p5p/1P5P/kPK5/8/8 w - - 0 1", "expected_concept": "King tempo / Opposition preservation"},
    # 8. Defensive quiet move
    {"id": "ARCH_08_QUIET_DEF", "archetype": "Defensive Quiet Move", "fen": "3r2k1/p4ppp/1p2p3/8/8/1P2P3/P4PPP/3R2K1 w - - 0 1", "expected_concept": "Back-rank defense or rook exchange"},
    # 9. King attack
    {"id": "ARCH_09_KING_ATTACK", "archetype": "King Attack", "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/2N5/PPPP1PPP/R1BQKB1R w KQkq - 1 7", "expected_concept": "Immediate mate threat on f2"}
]

CONFIGS = [
    {"name": "E0_X22", "bp": False, "conn": False},
    {"name": "E1_X24", "bp": True,  "conn": False},
    {"name": "E2_X25", "bp": False, "conn": True}
]

def search_at_depth(fen: str, depth: int, cfg: Dict[str, Any]) -> Dict[str, Any]:
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
            
    send(f"setoption name UCI_BackwardPawns value {'true' if cfg['bp'] else 'false'}")
    send(f"setoption name UCI_ConnectedPawns value {'true' if cfg['conn'] else 'false'}")
    send("setoption name UCI_SyntheticPerturbation value 0")
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
    print("Executing Depth-Dependent Search Reliability Audit (Depths 4 through 8)...")
    results = []
    
    for entry in PROVENANCE_SUITE:
        pid = entry["id"]
        arch = entry["archetype"]
        fen = entry["fen"]
        print(f"\nEvaluating [{pid}] ({arch})")
        
        pos_data = {
            "id": pid,
            "archetype": arch,
            "fen": fen,
            "expected_concept": entry["expected_concept"],
            "depth_traces": {}
        }
        
        for d in [4, 5, 6, 7, 8]:
            d_entry = {}
            for cfg in CONFIGS:
                res = search_at_depth(fen, d, cfg)
                d_entry[cfg["name"]] = res
                
            e0_m = d_entry["E0_X22"]["bestmove"]
            e1_m = d_entry["E1_X24"]["bestmove"]
            e2_m = d_entry["E2_X25"]["bestmove"]
            
            agree_e1 = (e1_m == e0_m)
            agree_e2 = (e2_m == e0_m)
            
            d_entry["stability"] = {
                "e1_matches_e0": agree_e1,
                "e2_matches_e0": agree_e2,
                "e0_move": e0_m,
                "e1_move": e1_m,
                "e2_move": e2_m
            }
            pos_data["depth_traces"][f"d{d}"] = d_entry
            print(f"  Depth {d}: E0={e0_m:<6} [{d_entry['E0_X22']['score']}] | E1={e1_m:<6} [{d_entry['E1_X24']['score']}] (Match={agree_e1}) | E2={e2_m:<6} [{d_entry['E2_X25']['score']}] (Match={agree_e2}) | Nodes(E0/E1/E2): {d_entry['E0_X22']['nodes']}/{d_entry['E1_X24']['nodes']}/{d_entry['E2_X25']['nodes']}")
            
        results.append(pos_data)
        
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nDepth-dependent reliability results written to {OUT_RAW}")

if __name__ == "__main__":
    main()
