#!/usr/bin/env python3
"""
run_eval_perturbation_study.py
Milestone P1.21 Phase 4: Static Evaluation Perturbation Study.
Measures the causal propagation of static evaluation changes through alpha-beta pruning mechanisms:
  E0: X22 Original Evaluation
  E1: X22 + Backward-Pawn Penalty (-10 mg / -15 eg)
  E2: X22 + Connected/Supported Passed Pawns (+30/+55 advanced, +20/+35 base)
  E3: X22 + Synthetic Diagnostic Perturbation (+30 cp)
Evaluates 16 diagnostic positions at depth 6 with full internal telemetry capture.
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
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "eval_perturbation_study_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

POSITIONS = [
    # Sicilian backward d6
    {"id": "P01_SIC_D6", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "archetype": "Backward d6"},
    {"id": "P02_FR_E6",  "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQ1RK1 w kq - 0 7", "archetype": "Backward e6"},
    {"id": "P03_SLAV_C6","fen": "r1bq1rk1/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQ - 0 7", "archetype": "Backward c-pawn"},
    {"id": "P04_ISOL_D4","fen": "r1bqk2r/pp1n1ppp/2p1pn2/3p4/2PP4/2P1PN2/P4PPP/R1BQKB1R w KQkq - 1 7", "archetype": "Semi-open center"},
    
    # Connected Passed Pawns & Endgames
    {"id": "P05_CONN_P", "fen": "8/5k2/8/1P1P4/8/8/4K3/8 w - - 0 1", "archetype": "Connected Passer Pair"},
    {"id": "P06_SUPP_P", "fen": "8/8/4k3/1P6/2P5/8/4K3/8 w - - 0 1", "archetype": "Supported Passer"},
    {"id": "P07_ISOL_P", "fen": "8/8/4k3/1P6/8/8/4K3/8 w - - 0 1", "archetype": "Isolated Passer"},
    {"id": "P08_RACE",   "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1", "archetype": "Passed Pawn Race"},
    
    # Sharp Tactical Attacks
    {"id": "P09_ATT_F2", "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/2N5/PPPP1PPP/R1BQKB1R w KQkq - 1 7", "archetype": "Tactical Mate Attack"},
    {"id": "P10_SCHEV",  "fen": "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18", "archetype": "Kingside Attack Break"},
    {"id": "P11_PENETR", "fen": "r1b2rk1/pp3ppp/2n1p3/8/2B5/4q3/PPP3PP/3R1R1K w - - 0 16", "archetype": "Queen Infiltration"},
    {"id": "P12_K_EXPO", "fen": "r1bq1rk1/ppp1bppp/2n1pn2/3p4/2PP4/2N2NP1/PP2PPBP/R1BQ1RK1 w - - 0 7", "archetype": "King Shelter G3"},
    
    # Quiet Positional & Closed Chains
    {"id": "P13_Q_SLAV", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQ - 0 7", "archetype": "Quiet Middlegame"},
    {"id": "P14_FR_ADV", "fen": "r1bqk2r/pp1nbppp/2n1p3/2ppP3/3P1P2/2N1BN2/PPP3PP/R2QKB1R w KQkq - 1 8", "archetype": "French Closed Chain"},
    {"id": "P15_RK_END", "fen": "8/5pk1/4p1p1/1R5p/8/6P1/r4PKP/8 w - - 0 35", "archetype": "Rook 4v3 Endgame"},
    {"id": "P16_ZUGZW",  "fen": "8/8/p1p5/1p5p/1P5P/kPK5/8/8 w - - 0 1", "archetype": "Pawn Zugzwang"}
]

CONFIGS = [
    {"name": "E0_Ref_X22",      "bp": False, "conn": False, "synth": 0,   "desc": "X22 Original Evaluation"},
    {"name": "E1_BackwardPawns","bp": True,  "conn": False, "synth": 0,   "desc": "X22 + Backward Pawn Penalty (-10/-15)"},
    {"name": "E2_ConnectedPawns","bp": False, "conn": True,  "synth": 0,   "desc": "X22 + Connected Passers (+30/+55)"},
    {"name": "E3_SyntheticBias", "bp": False, "conn": False, "synth": 30,  "desc": "X22 + Synthetic Diagnostic Bias (+30 cp)"}
]

def run_probe(fen: str, depth: int, cfg: Dict[str, Any]) -> Dict[str, Any]:
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
            
    # Apply configuration options
    send(f"setoption name UCI_BackwardPawns value {'true' if cfg['bp'] else 'false'}")
    send(f"setoption name UCI_ConnectedPawns value {'true' if cfg['conn'] else 'false'}")
    send(f"setoption name UCI_SyntheticPerturbation value {cfg['synth']}")
    send("setoption name Hash value 64")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break
            
    t0 = time.time()
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
            
    elapsed = time.time() - t0
    
    # Query telemetry
    telemetry = {}
    try:
        send("isready")
        while True:
            line = proc.stdout.readline()
            if not line or "readyok" in line:
                break
        send("telemetry_report")
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str == "TELEMETRY_END":
                break
            if " " in line_str and not line_str.startswith("TELEMETRY_"):
                parts = line_str.split()
                try:
                    telemetry[parts[0]] = int(parts[1]) if parts[1].isdigit() else parts[1]
                except Exception:
                    telemetry[parts[0]] = parts[1]
    except Exception:
        pass
                
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
        "elapsed_sec": round(elapsed, 4),
        "pv": pv,
        "telemetry": {
            "rfp_probes": telemetry.get("rfp_probes", 0),
            "rfp_cutoffs": telemetry.get("rfp_cutoffs", 0),
            "nmp_probes": telemetry.get("nmp_probes", 0),
            "nmp_cutoffs": telemetry.get("nmp_cutoffs", 0),
            "lmr_reduced": telemetry.get("dynamic_lmr_reduced", 0),
            "eval_calls": telemetry.get("eval_calls", 0),
            "total_cutoffs": telemetry.get("total_cutoffs", 0)
        }
    }

def main():
    print("Executing Phase 4 Static Evaluation Perturbation Study (Depth 6)...")
    results = []
    
    for p_idx, pos in enumerate(POSITIONS, 1):
        pid = pos["id"]
        fen = pos["fen"]
        arch = pos["archetype"]
        print(f"\n[{p_idx}/{len(POSITIONS)}] Auditing {pid} ({arch})")
        
        pos_entry = {
            "id": pid,
            "fen": fen,
            "archetype": arch,
            "runs": {}
        }
        
        for cfg in CONFIGS:
            cname = cfg["name"]
            res = run_probe(fen, depth=6, cfg=cfg)
            pos_entry["runs"][cname] = res
            print(f"  {cname:<20}: BestMove={res['bestmove']:<6} Score={str(res['score']):<5} Nodes={res['nodes']:<7} RFP={res['telemetry']['rfp_cutoffs']}/{res['telemetry']['rfp_probes']} NMP={res['telemetry']['nmp_cutoffs']}/{res['telemetry']['nmp_probes']} LMR={res['telemetry']['lmr_reduced']}")
            
        results.append(pos_entry)
        
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nEvaluation perturbation study results written to {OUT_RAW}")

if __name__ == "__main__":
    main()
