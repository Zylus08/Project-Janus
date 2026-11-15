#!/usr/bin/env python3
"""
run_controlled_ablations.py
Milestone P1.21 Phase 10: Controlled Ablation Matrix (B0 vs B1 vs B2 vs B3).

Evaluates:
- B0: Legacy RFP (mode 0)
- B1: B0 + Non-PV Guard (mode 1)
- B2: B1 + TT Lower Bound Storage (mode 2)
- B3: B2 + TT Conflict Guard + Non-Pawn Material Guard (mode 3)

Across 12 diagnostic positions at depths 4, 6, and 8.
Measures:
- Root bestmove & score
- Total nodes & relative search tree compression
- Main nodes vs Qsearch nodes
- RFP probes, cutoffs, and cutoff percentage
- Move agreement with B3 (Full X26)
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
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "controlled_ablations_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

ABLATIONS = [
    {"id": "B0", "name": "Legacy RFP", "mode": 0},
    {"id": "B1", "name": "Non-PV Guard", "mode": 1},
    {"id": "B2", "name": "TT Lower Store", "mode": 2},
    {"id": "B3", "name": "Full X26 Repair", "mode": 3}
]

POSITIONS = [
    {"id": "CF_Q1", "name": "Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "CF_Q2", "name": "Semi-Slav Quiet", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQ - 0 7"},
    {"id": "CF_Q3", "name": "French Advance", "fen": "r1bqk2r/pp1nbppp/2n1p3/2ppP3/3P1P2/2N1BN2/PPP3PP/R2QKB1R w KQkq - 1 8"},
    {"id": "CF_T1", "name": "Fried Liver Fork", "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/2N5/PPPP1PPP/R1BQKB1R w KQkq - 1 7"},
    {"id": "CF_T2", "name": "King Defense Queen Attack", "fen": "r1b2rk1/pp3ppp/2n1p3/8/2B5/4q3/PPP3PP/3R1R1K w - - 0 16"},
    {"id": "CF_T3", "name": "Scheveningen Attack", "fen": "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18"},
    {"id": "CF_E1", "name": "Rook 4v3 Endgame", "fen": "8/5pk1/4p1p1/1R5p/8/6P1/r4PKP/8 w - - 0 35"},
    {"id": "CF_E2", "name": "Lucena Rook Endgame", "fen": "1K1k4/1P6/8/8/8/8/r7/2R5 w - - 0 1"},
    {"id": "CF_E3", "name": "Mutual KP Zugzwang", "fen": "8/8/p1p5/1p5p/1P5P/kPK5/8/8 w - - 0 1"},
    {"id": "CF_P1", "name": "Passed Pawn Race", "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1"},
    {"id": "CF_P2", "name": "Connected Passers", "fen": "8/5k2/8/1P1P4/8/8/4K3/8 w - - 0 1"},
    {"id": "CF_P3", "name": "Blockaded Passers", "fen": "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1"}
]

def search_ablation(fen: str, depth: int, rfp_mode: int) -> Dict[str, Any]:
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
            
    send("setoption name Hash value 64")
    send(f"setoption name UCI_RfpRepairMode value {rfp_mode}")
    send("telemetry_reset")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break
            
    send(f"position fen {fen}")
    t0 = time.perf_counter()
    send(f"go depth {depth}")
    
    bestmove = ""
    nodes = 0
    score = None
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
            
    t1 = time.perf_counter()
    wall_ms = round((t1 - t0) * 1000.0, 2)
    
    # Telemetry
    telem = {}
    try:
        send("telemetry_report")
        send("isready")
        in_t = False
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if "TELEMETRY_START" in line_str:
                in_t = True
                continue
            if "TELEMETRY_END" in line_str:
                break
            if in_t:
                parts = line_str.split()
                if len(parts) == 2:
                    k, v = parts[0], parts[1]
                    try:
                        telem[k] = int(v)
                    except ValueError:
                        telem[k] = v
    except Exception as e:
        telem["error"] = str(e)
        
    try:
        send("quit")
        proc.wait(timeout=1.0)
    except Exception:
        proc.kill()
        
    return {
        "bestmove": bestmove,
        "score": score,
        "nodes": nodes,
        "wall_ms": wall_ms,
        "pv": pv,
        "telemetry": telem
    }

def main():
    print("Executing Phase 10 Controlled Ablations (B0 vs B1 vs B2 vs B3)...")
    results = []
    
    for pos in POSITIONS:
        pid = pos["id"]
        pname = pos["name"]
        fen = pos["fen"]
        print(f"\nEvaluating Position [{pid}] {pname}...")
        
        pos_entry = {
            "id": pid,
            "name": pname,
            "fen": fen,
            "depths": {}
        }
        
        for d in [4, 6, 8]:
            d_entry = {}
            for ab in ABLATIONS:
                ab_id = ab["id"]
                mode = ab["mode"]
                res = search_ablation(fen, d, mode)
                t = res.get("telemetry", {})
                
                rfp_p = t.get("rfp_probes", 0)
                rfp_c = t.get("rfp_cutoffs", 0)
                rfp_pct = round((rfp_c / rfp_p * 100.0), 1) if rfp_p > 0 else 0.0
                
                d_entry[ab_id] = {
                    "bestmove": res["bestmove"],
                    "score": res["score"],
                    "nodes": res["nodes"],
                    "main_nodes": t.get("main_nodes", 0),
                    "qsearch_nodes": t.get("qsearch_nodes", 0),
                    "rfp_probes": rfp_p,
                    "rfp_cutoffs": rfp_c,
                    "rfp_cutoff_pct": rfp_pct,
                    "wall_ms": res["wall_ms"],
                    "pv": res["pv"]
                }
                
            pos_entry["depths"][f"d{d}"] = d_entry
            
            # Print comparative summary at this depth
            b0 = d_entry["B0"]
            b1 = d_entry["B1"]
            b2 = d_entry["B2"]
            b3 = d_entry["B3"]
            
            agree = (b0["bestmove"] == b3["bestmove"])
            node_ratio = round(b3["nodes"] / b0["nodes"], 3) if b0["nodes"] > 0 else 1.0
            print(f"  Depth {d}: B0={b0['bestmove']} ({b0['nodes']:,}n) | B1={b1['bestmove']} ({b1['nodes']:,}n) | B2={b2['bestmove']} ({b2['nodes']:,}n) | B3={b3['bestmove']} ({b3['nodes']:,}n) | MoveAgree(B0,B3)={agree} | B3/B0={node_ratio}x")
            
        results.append(pos_entry)
        
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nAll ablation results successfully saved to: {OUT_RAW}")

if __name__ == "__main__":
    main()
