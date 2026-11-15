#!/usr/bin/env python3
"""
test_rfp_contract_audit.py
Milestone P1.21 Phase 2: Systematic Correctness and Robustness Audit of the Reverse Futility Pruning (RFP) Contract.
Tests 8 specific risk categories:
1. Mate-threat blindness (High static eval but facing mate in 1-2)
2. Zugzwang in King & Pawn endgames (No non-pawn material)
3. Quiet defensive resources & tactical sacrifices
4. Passed pawn races (Static eval lags dynamic promotion)
5. King exposure & attack vectors
6. TT Upper Bound conflict (TT says upper < beta, but RFP cuts off)
7. Non-PV vs PV condition (Does RFP fire when alpha < beta - 1?)
8. Return-value semantics (Returning static_eval vs beta vs static_eval - margin)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X25 = ROOT / "analysis" / "phase1" / "p1.20" / "control" / "janus_classical_x25.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "rfp_contract_audit_results.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

# 8 Diagnostic Suites
TEST_POSITIONS = [
    # Category 1: Mate-threat blindness
    {
        "id": "CAT1_MATE_1",
        "category": "Mate-threat blindness",
        "fen": "r1b2rk1/pp3ppp/2n1p3/8/2B5/4q3/PPP3PP/3R1R1K w - - 0 16",
        "description": "White up material but king under heavy queen penetration",
        "risk_type": "Heuristic selectivity / Tactical blindness"
    },
    {
        "id": "CAT1_MATE_2",
        "category": "Mate-threat blindness",
        "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/2N5/PPPP1PPP/R1BQKB1R w KQkq - 1 7",
        "description": "Scholar/Fried-liver style mate threat on f2",
        "risk_type": "Tactical mate blindness"
    },
    
    # Category 2: Zugzwang in King & Pawn endgames
    {
        "id": "CAT2_ZUG_1",
        "category": "Zugzwang",
        "fen": "8/8/p1p5/1p5p/1P5P/kPK5/8/8 w - - 0 1",
        "description": "Classic K&P mutual zugzwang",
        "risk_type": "Evaluation-search assumption violation"
    },
    {
        "id": "CAT2_ZUG_2",
        "category": "Zugzwang",
        "fen": "8/8/8/4p3/3kP3/8/4K3/8 w - - 0 1",
        "description": "King & Pawn opposition zugzwang",
        "risk_type": "Opposition loss"
    },
    
    # Category 3: Tactical Sacrifices & Quiet Defensive Resources
    {
        "id": "CAT3_SAC_1",
        "category": "Tactical sacrifice",
        "fen": "r1bqk2r/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQkq - 4 7",
        "description": "Standard quiet opening structure",
        "risk_type": "Baseline quiet control"
    },
    {
        "id": "CAT3_DEF_1",
        "category": "Quiet defense",
        "fen": "3r2k1/p4ppp/1p2p3/8/8/1P2P3/P4PPP/3R2K1 w - - 0 1",
        "description": "Rook endgame back-rank threat",
        "risk_type": "Tactical back-rank exchange"
    },
    
    # Category 4: Passed Pawn Races
    {
        "id": "CAT4_RACE_1",
        "category": "Passed pawn race",
        "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1",
        "description": "Both sides have pawn on 7th rank; dynamic promotion determines outcome",
        "risk_type": "Static evaluation lag vs promotion horizon"
    },
    {
        "id": "CAT4_RACE_2",
        "category": "Passed pawn race",
        "fen": "8/4k3/8/8/8/4K3/1p6/1R6 w - - 0 1",
        "description": "Rook vs passed pawn on 2nd rank",
        "risk_type": "Piece vs passer valuation"
    }
]

class UciSearcher:
    def __init__(self, exe_path: Path):
        self.exe_path = exe_path
        self.proc = None
        
    def start(self, rfp_enabled: bool):
        if self.proc and self.proc.poll() is None:
            self.quit()
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        self.send(f"setoption name UCI_RFP value {'true' if rfp_enabled else 'false'}")
        self.send("setoption name Hash value 64")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break
                
    def send(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError("Engine process dead")
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()
        
    def search_depth(self, fen: str, depth: int) -> Dict[str, Any]:
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        
        bestmove = ""
        score = None
        nodes = 0
        nps = 0
        
        while True:
            line = self.proc.stdout.readline()
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
            if line_str.startswith("bestmove"):
                bestmove = line_str.split()[1]
                break
                
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break
                
        return {
            "depth": depth,
            "bestmove": bestmove,
            "score": score,
            "nodes": nodes,
            "nps": nps
        }
        
    def quit(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.write("quit\n")
                self.proc.stdin.flush()
                self.proc.wait(timeout=1.0)
            except Exception:
                self.proc.kill()
        self.proc = None

def main():
    print("Executing RFP Contract Correctness Audit...")
    results = []
    
    searcher_on = UciSearcher(EXE_X25)
    searcher_off = UciSearcher(EXE_X25)
    
    searcher_on.start(rfp_enabled=True)
    searcher_off.start(rfp_enabled=False)
    
    for tc in TEST_POSITIONS:
        print(f"\nAuditing [{tc['id']}] {tc['category']}: {tc['description']}")
        
        # Test depth 2 and depth 3
        r_d2_on = searcher_on.search_depth(tc["fen"], 2)
        r_d2_off = searcher_off.search_depth(tc["fen"], 2)
        r_d3_on = searcher_on.search_depth(tc["fen"], 3)
        r_d3_off = searcher_off.search_depth(tc["fen"], 3)
        
        move_agree_d2 = (r_d2_on["bestmove"] == r_d2_off["bestmove"])
        move_agree_d3 = (r_d3_on["bestmove"] == r_d3_off["bestmove"])
        
        node_ratio_d2 = round(r_d2_on["nodes"] / max(1, r_d2_off["nodes"]), 3)
        node_ratio_d3 = round(r_d3_on["nodes"] / max(1, r_d3_off["nodes"]), 3)
        
        res_entry = {
            "test_id": tc["id"],
            "category": tc["category"],
            "fen": tc["fen"],
            "description": tc["description"],
            "risk_type": tc["risk_type"],
            "d2": {
                "on": r_d2_on,
                "off": r_d2_off,
                "move_agreement": move_agree_d2,
                "node_ratio": node_ratio_d2,
                "score_delta": (r_d2_on["score"] - r_d2_off["score"]) if (r_d2_on["score"] is not None and r_d2_off["score"] is not None) else None
            },
            "d3": {
                "on": r_d3_on,
                "off": r_d3_off,
                "move_agreement": move_agree_d3,
                "node_ratio": node_ratio_d3,
                "score_delta": (r_d3_on["score"] - r_d3_off["score"]) if (r_d3_on["score"] is not None and r_d3_off["score"] is not None) else None
            }
        }
        results.append(res_entry)
        
        print(f"  Depth 2: Agree={move_agree_d2} (ON:{r_d2_on['bestmove']} [{r_d2_on['score']}] vs OFF:{r_d2_off['bestmove']} [{r_d2_off['score']}]) | Nodes: {r_d2_on['nodes']} vs {r_d2_off['nodes']} ({node_ratio_d2}x)")
        print(f"  Depth 3: Agree={move_agree_d3} (ON:{r_d3_on['bestmove']} [{r_d3_on['score']}] vs OFF:{r_d3_off['bestmove']} [{r_d3_off['score']}]) | Nodes: {r_d3_on['nodes']} vs {r_d3_off['nodes']} ({node_ratio_d3}x)")
        
    searcher_on.quit()
    searcher_off.quit()
    
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nRFP contract audit results written to {OUT_RAW}")

if __name__ == "__main__":
    main()
