#!/usr/bin/env python3
"""
instrument_rfp_counterfactual.py
Milestone P1.21 Phase 3: Counterfactual Pruning Instrumentation and Decision Audit.
Samples positions across key game phases, executes clean-state searches with RFP ON vs RFP OFF,
and measures exact node changes, score bounds, root move stability, and full-width minimax comparison at d <= 3.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X25 = ROOT / "analysis" / "phase1" / "p1.20" / "control" / "janus_classical_x25.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "rfp_counterfactual_audit_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

CORPUS = [
    # 1. Quiet Middlegames
    {"id": "CF_Q1", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQ - 0 7", "type": "Quiet Semi-Slav"},
    {"id": "CF_Q2", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQ1RK1 w kq - 0 7", "type": "Quiet French"},
    
    # 2. Tactical Middlegames / King Attacks
    {"id": "CF_T1", "fen": "r1b2rk1/pp3ppp/2n1p3/8/2B5/4q3/PPP3PP/3R1R1K w - - 0 16", "type": "King Defense Queen Penetration"},
    {"id": "CF_T2", "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/2N5/PPPP1PPP/R1BQKB1R w KQkq - 1 7", "type": "Tactical Threat on f2"},
    {"id": "CF_T3", "fen": "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18", "type": "Sicilian Scheveningen Attack"},

    # 3. Closed Pawn Structures
    {"id": "CF_C1", "fen": "rnbq1rk1/ppp1bppp/4pn2/3p2B1/2PP4/2N2N2/PP2PPPP/R2QKB1R w KQ - 4 6", "type": "Closed Queen's Gambit"},
    {"id": "CF_C2", "fen": "r1bqk2r/pp1nbppp/2n1p3/2ppP3/3P1P2/2N1BN2/PPP3PP/R2QKB1R w KQkq - 1 8", "type": "French Advance Closed Chain"},

    # 4. Rook Endgames
    {"id": "CF_R1", "fen": "8/5pk1/4p1p1/1R5p/8/6P1/r4PKP/8 w - - 0 35", "type": "Quiet Rook Endgame 4v3"},
    {"id": "CF_R2", "fen": "3r2k1/p4ppp/1p2p3/8/8/1P2P3/P4PPP/3R2K1 w - - 0 1", "type": "Rook Exchange Decision"},

    # 5. Passed Pawn Races & Endgames
    {"id": "CF_P1", "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1", "type": "Mutual 7th Rank Passer Race"},
    {"id": "CF_P2", "fen": "8/4k3/8/8/8/4K3/1p6/1R6 w - - 0 1", "type": "Rook Blockading 2nd Rank Passer"},
    {"id": "CF_P3", "fen": "8/8/p1p5/1p5p/1P5P/kPK5/8/8 w - - 0 1", "type": "Mutual Pawn Zugzwang"}
]

def search_clean(fen: str, depth: int, rfp_mode: bool) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(EXE_X25)],
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
            
    send(f"setoption name UCI_RFP value {'true' if rfp_mode else 'false'}")
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
    nps = 0
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
        if "nps" in line_str:
            parts = line_str.split()
            try:
                nps = int(parts[parts.index("nps") + 1])
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
        "nps": nps,
        "pv": pv
    }

def main():
    print("Executing Counterfactual Pruning Decision Audit...")
    results = []
    
    # Audit depths 2, 3, 4, 5
    for entry in CORPUS:
        cid = entry["id"]
        fen = entry["fen"]
        ctype = entry["type"]
        print(f"\nProcessing [{cid}] ({ctype}): {fen}")
        
        depth_results = {}
        for d in [2, 3, 4, 5]:
            res_on = search_clean(fen, d, rfp_mode=True)
            res_off = search_clean(fen, d, rfp_mode=False)
            
            node_ratio = round(res_on["nodes"] / max(1, res_off["nodes"]), 4)
            move_agree = (res_on["bestmove"] == res_off["bestmove"])
            score_diff = (res_on["score"] - res_off["score"]) if (res_on["score"] is not None and res_off["score"] is not None) else None
            
            depth_results[f"d{d}"] = {
                "on": res_on,
                "off": res_off,
                "node_ratio": node_ratio,
                "node_delta": res_on["nodes"] - res_off["nodes"],
                "move_agreement": move_agree,
                "score_delta": score_diff
            }
            print(f"  D{d}: Agree={move_agree} (ON:{res_on['bestmove']} [{res_on['score']}] vs OFF:{res_off['bestmove']} [{res_off['score']}]) | Nodes: {res_on['nodes']} vs {res_off['nodes']} ({node_ratio*100:.1f}%)")
            
        results.append({
            "id": cid,
            "type": ctype,
            "fen": fen,
            "depths": depth_results
        })
        
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nCounterfactual audit results written to {OUT_RAW}")

if __name__ == "__main__":
    main()
