#!/usr/bin/env python3
"""
test_search_eval_compatibility.py
Milestone P1.20 Phase 5: Static Evaluation vs Search Compatibility Audit.
Measures how static evaluation changes (backward pawns in X24 vs X22)
propagate through alpha-beta search mechanisms:
  - Reverse Futility Pruning (RFP)
  - Null Move Pruning (NMP)
  - Late Move Reductions (LMR)
  - Aspiration Window re-searches
  - Quiescence Search entry
Evaluates 30 structurally diverse positions at fixed depth 8.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
EXE_X24 = ROOT / "analysis" / "phase1" / "p1.19" / "control" / "janus_classical_x24.exe"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DIAGNOSTIC_FENS = [
    # Sicilian backward d6
    {"id": "COMP_01", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "type": "Sicilian d6 backward"},
    {"id": "COMP_02", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQ1RK1 w kq - 0 7", "type": "French e6 backward"},
    {"id": "COMP_03", "fen": "r1bq1rk1/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQ - 0 7", "theme": "Semi-Slav backward c-pawn"},
    {"id": "COMP_04", "fen": "r1bqk2r/pp1n1ppp/2p1pn2/3p4/2PP4/2P1PN2/P4PPP/R1BQKB1R w KQkq - 1 7", "theme": "White backward c3"},
    {"id": "COMP_05", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PN4/2N3P1/PP2PPBP/R1BQ1RK1 b - - 0 8", "theme": "Dragon d6 backward"},
    # IQP d4 positions
    {"id": "COMP_06", "fen": "r1bq1rk1/pp1n1ppp/4pn2/8/2BP4/P1N1PN2/1P3PPP/R1BQK2R b KQ - 0 9", "theme": "White d4 IQP"},
    {"id": "COMP_07", "fen": "r1b2rk1/pp3ppp/2n1pn2/a7/2BP4/P1N1PN2/1P3PPP/R1BQK2R w KQ - 1 10", "theme": "IQP d4 blockade"},
    {"id": "COMP_08", "fen": "r2q1rk1/pp1nbppp/4pn2/8/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 w - - 0 9", "theme": "White IQP kingside attack"},
    # Tactical sharp positions
    {"id": "COMP_09", "fen": "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5", "theme": "Queen mate threat"},
    {"id": "COMP_10", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "theme": "KiwiPete tactical crossroad"},
    # Connected passers vs isolated
    {"id": "COMP_11", "fen": "8/5pk1/4p1p1/P1P4p/8/6P1/5PKP/8 w - - 0 35", "theme": "Outside connected passers"},
    {"id": "COMP_12", "fen": "8/8/4k1p1/2P1P3/8/5K2/8/8 w - - 0 45", "theme": "Central connected passers"},
    # Rook endgames
    {"id": "COMP_13", "fen": "8/8/4k3/R7/8/3K4/8/7r w - - 0 55", "theme": "Philidor rook defense"},
    {"id": "COMP_14", "fen": "8/5pk1/7p/R6P/8/3K4/8/7r w - - 0 56", "theme": "Tarrasch rook behind pawn"},
    {"id": "COMP_15", "fen": "8/8/4k3/3R4/8/3K4/8/7r w - - 0 57", "theme": "Active rook cutting off king"},
    # Quiet middlegames
    {"id": "COMP_16", "fen": "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8", "theme": "Symmetrical central struggle"},
    {"id": "COMP_17", "fen": "r2q1rk1/1bp1bppp/p1n1pn2/1p6/3P4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 11", "theme": "QID central tension"},
    {"id": "COMP_18", "fen": "r1b2rk1/ppqn1ppp/2pbpn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 b - - 0 10", "theme": "Capablanca freeing maneuver"},
    {"id": "COMP_19", "fen": "r1bq1rk1/1pp2ppp/p1np1n2/4p3/B3P3/2PP1N2/PP1N1PPP/R2Q1RK1 b - - 1 9", "theme": "Ruy Lopez delayed exchange"},
    {"id": "COMP_20", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "theme": "English symmetric development"},
    # Endgames with pawn structure tension
    {"id": "COMP_21", "fen": "8/5pk1/4e1p1/8/3K4/5B2/8/8 w - - 0 50", "theme": "Opposite colored bishops"},
    {"id": "COMP_22", "fen": "8/5pk1/6p1/4b3/3K4/5B2/8/8 w - - 0 52", "theme": "Bishop trade decision"},
    {"id": "COMP_23", "fen": "8/5pk1/6p1/8/3Kn3/5N2/8/8 w - - 0 53", "theme": "Knight centralization"},
    {"id": "COMP_24", "fen": "8/5pk1/4b1p1/8/3K4/5N2/8/8 w - - 0 55", "theme": "Knight vs bishop"},
    {"id": "COMP_25", "fen": "8/1P6/8/8/8/8/1p6/k1K5 w - - 0 1", "theme": "Pawn race promotion"},
    {"id": "COMP_26", "fen": "8/8/8/p7/P7/8/8/k1K5 w - - 0 1", "theme": "Square of the king rule"},
    {"id": "COMP_27", "fen": "8/8/8/8/4k3/8/4p3/4K3 w - - 0 1", "theme": "King in front of pawn fortress"},
    {"id": "COMP_28", "fen": "8/8/8/4p3/4k3/8/4P3/4K3 w - - 0 1", "theme": "Opposition zugzwang"},
    {"id": "COMP_29", "fen": "8/8/8/4k3/4p3/4P3/8/4K3 w - - 0 1", "theme": "Mutual zugzwang"},
    {"id": "COMP_30", "fen": "8/8/4k3/8/4P3/4K3/8/8 b - - 0 1", "theme": "Key square cession"}
]

class SearchAuditor:
    def __init__(self, exe_path: Path, name: str, bp: int = 0):
        self.exe_path = exe_path
        self.name = name
        self.bp = bp
        self.proc = None

    def start(self):
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
        self.send(f"setoption name UCI_BackwardPawns value {'true' if self.bp else 'false'}")
        self.send("setoption name Hash value 64")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            self.start()
        try:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
        except Exception:
            self.start()
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def evaluate_static(self, fen: str) -> Optional[int]:
        self.send(f"position fen {fen}")
        self.send("go depth 1")
        score = None
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
            if line_str.startswith("bestmove"):
                break
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break
        return score

    def search_fixed_depth(self, fen: str, depth: int) -> Dict[str, Any]:
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        bestmove = ""
        score_cp = None
        nodes = 0
        nps = 0
        depth_reached = 0

        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("info"):
                parts = line_str.split()
                if "depth" in parts:
                    try:
                        depth_reached = int(parts[parts.index("depth") + 1])
                    except Exception:
                        pass
                if "score" in parts and "cp" in parts:
                    try:
                        score_cp = int(parts[parts.index("cp") + 1])
                    except Exception:
                        pass
                if "nodes" in parts:
                    try:
                        nodes = int(parts[parts.index("nodes") + 1])
                    except Exception:
                        pass
                if "nps" in parts:
                    try:
                        nps = int(parts[parts.index("nps") + 1])
                    except Exception:
                        pass
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break

        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

        return {
            "depth_target": depth,
            "depth_reached": depth_reached,
            "bestmove": bestmove,
            "score_cp": score_cp,
            "nodes": nodes,
            "nps": nps
        }

    def stop(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

def run_compatibility_audit():
    print("=" * 80)
    print("PHASE 5: STATIC EVALUATION VS SEARCH COMPATIBILITY AUDIT (30 POSITIONS)")
    print("=" * 80)

    e_x22 = SearchAuditor(EXE_X22, "Reference X22", bp=0)
    e_x24 = SearchAuditor(EXE_X24, "Candidate X24", bp=1)
    e_x22.start()
    e_x24.start()

    results = []
    total_nodes_x22 = 0
    total_nodes_x24 = 0
    move_mismatches = 0
    large_score_deltas = 0

    for idx, item in enumerate(DIAGNOSTIC_FENS):
        pos_id = item["id"]
        fen = item["fen"]

        static_x22 = e_x22.evaluate_static(fen)
        static_x24 = e_x24.evaluate_static(fen)

        search_x22 = e_x22.search_fixed_depth(fen, 8)
        search_x24 = e_x24.search_fixed_depth(fen, 8)

        total_nodes_x22 += search_x22["nodes"]
        total_nodes_x24 += search_x24["nodes"]

        delta_static = (static_x24 or 0) - (static_x22 or 0)
        delta_search = (search_x24["score_cp"] or 0) - (search_x22["score_cp"] or 0)

        match_move = (search_x22["bestmove"] == search_x24["bestmove"])
        if not match_move:
            move_mismatches += 1
        if abs(delta_search) >= 25:
            large_score_deltas += 1

        results.append({
            "id": pos_id,
            "fen": fen,
            "theme": item.get("theme", item.get("type", "")),
            "static_x22": static_x22,
            "static_x24": static_x24,
            "delta_static": delta_static,
            "search_x22": search_x22,
            "search_x24": search_x24,
            "delta_search": delta_search,
            "move_match": match_move
        })

        print(f"[{idx+1:2d}/30] {pos_id}: Move Match={match_move} | Static Delta={delta_static:+3d} cp | Search Delta={delta_search:+3d} cp | Nodes X22={search_x22['nodes']} X24={search_x24['nodes']}")

    e_x22.stop()
    e_x24.stop()

    node_ratio = (total_nodes_x24 / max(1, total_nodes_x22))

    summary = {
        "total_tested": len(DIAGNOSTIC_FENS),
        "move_agreement_rate": round((len(DIAGNOSTIC_FENS) - move_mismatches) / len(DIAGNOSTIC_FENS) * 100, 1),
        "move_mismatches": move_mismatches,
        "large_score_deltas": large_score_deltas,
        "total_nodes_x22": total_nodes_x22,
        "total_nodes_x24": total_nodes_x24,
        "node_ratio_x24_to_x22": round(node_ratio, 4),
        "positions": results
    }

    out_file = RAW_DIR / "static_eval_search_compatibility.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("PHASE 5 COMPATIBILITY AUDIT COMPLETE!")
    print(f"Move Agreement: {summary['move_agreement_rate']}% | Node Ratio (X24/X22): {summary['node_ratio_x24_to_x22']:.4f}")
    print(f"Saved to: {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    run_compatibility_audit()
