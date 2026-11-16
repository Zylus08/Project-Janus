#!/usr/bin/env python3
"""
profile_r1_efficiency.py
Milestone P1.22 Phase 8: Search Efficiency & Selectivity Profiling.
Comparative benchmarking across 8 diagnostic positions at depths 4, 6, 8 for:
1. Frozen Baseline X7 (1T control)
2. Frozen Reference X22 (1T control)
3. Archived Candidate X26 (1T control)
4. Clean-Sheet Janus Classical R1.0
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT = Path("E:/ChessXML/project-janus-phase1")
OUT_JSON = ROOT / "analysis" / "phase1" / "p1.22" / "raw" / "r1_search_efficiency_raw.json"
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

ENGINES = [
    ("X7", ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe", {}),
    ("X22", ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe", {}),
    ("X26", ROOT / "analysis" / "phase1" / "p1.21" / "control" / "janus_classical_x26.exe", {}),
    ("R1", ROOT / "engine" / "classical_x" / "janus_classical_x.exe", {"UCI_Variant": "R1"}),
]

DIAGNOSTIC_POSITIONS = [
    ("CF_Q1", "Startpos (Symmetric Quiet)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("CF_Q2", "Semi-Slav (Positional Pawn)", "rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5"),
    ("CF_Q3", "French Advance (Closed Chain)", "rnbqkbnr/pp2pppp/2p5/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3"),
    ("CF_T1", "Fried Liver (Tactical Queen)", "r1b1k2r/pppp1ppp/8/8/1B1qn3/8/PPP2PPP/RN1QKB1R w KQkq - 0 1"),
    ("CF_T2", "Threat on f2 (Tactical Defense)", "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"),
    ("CF_T3", "Scheveningen Attack (Sacrifice)", "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18"),
    ("CF_E1", "Rook 4v3 (Rook Endgame)", "8/5pk1/7p/1R6/8/8/5rPP/6K1 b - - 0 1"),
    ("CF_P1", "Passed Pawn Race (K+P Race)", "8/4k3/8/8/8/4K3/1p6/1R6 w - - 0 1"),
]

DEPTHS = [4, 6, 8]

class UciRunner:
    def __init__(self, exe: Path, options: Dict[str, str]):
        self.exe = exe
        self.options = options
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe)],
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
        for k, v in self.options.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def go_depth(self, fen: str, depth: int) -> Dict[str, Any]:
        self.send("ucinewgame")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        bestmove = ""
        score = 0
        nodes = 0
        nps = 0
        time_ms = 0
        pv = ""

        t0 = time.perf_counter()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("info") and f"depth {depth}" in line_str:
                parts = line_str.split()
                if "score" in parts:
                    idx = parts.index("score")
                    if idx + 2 < len(parts) and parts[idx+1] == "cp":
                        try: score = int(parts[idx+2])
                        except ValueError: pass
                    elif idx + 2 < len(parts) and parts[idx+1] == "mate":
                        try: score = 30000 if int(parts[idx+2]) > 0 else -30000
                        except ValueError: pass
                if "nodes" in parts:
                    idx = parts.index("nodes")
                    if idx + 1 < len(parts):
                        try: nodes = int(parts[idx+1])
                        except ValueError: pass
                if "nps" in parts:
                    idx = parts.index("nps")
                    if idx + 1 < len(parts):
                        try: nps = int(parts[idx+1])
                        except ValueError: pass
                if "time" in parts:
                    idx = parts.index("time")
                    if idx + 1 < len(parts):
                        try: time_ms = int(parts[idx+1])
                        except ValueError: pass
                if "pv" in parts:
                    idx = parts.index("pv")
                    pv = " ".join(parts[idx+1:])

            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) > 1:
                    bestmove = parts[1]
                break

        wall_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "depth": depth,
            "bestmove": bestmove,
            "score": score,
            "nodes": nodes,
            "nps": nps,
            "reported_time_ms": time_ms,
            "wall_ms": round(wall_ms, 2),
            "pv": pv
        }

    def quit(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()
            self.proc = None

def main():
    print("=" * 85)
    print("PHASE 8: SEARCH EFFICIENCY & SELECTIVITY PROFILING (R1 vs X7 vs X22 vs X26)")
    print("=" * 85)

    profile_results = []

    for pos_id, desc, fen in DIAGNOSTIC_POSITIONS:
        print(f"\n--- Position {pos_id}: {desc} ---")
        pos_data = {"id": pos_id, "desc": desc, "fen": fen, "depths": {}}

        for d in DEPTHS:
            depth_key = f"d{d}"
            pos_data["depths"][depth_key] = {}
            print(f"  [Depth {d}]")

            for eng_id, exe_path, opts in ENGINES:
                runner = UciRunner(exe_path, opts)
                runner.start()
                res = runner.go_depth(fen, d)
                runner.quit()

                pos_data["depths"][depth_key][eng_id] = res
                print(f"    {eng_id:4} | Move: {res['bestmove']:5} | Score: {res['score']:+5} cp | Nodes: {res['nodes']:8,} | Wall: {res['wall_ms']:6.1f} ms | NPS: {res['nps']:,}")

            # Calculate R1 efficiency ratios
            r1_nodes = pos_data["depths"][depth_key]["R1"]["nodes"]
            x7_nodes = pos_data["depths"][depth_key]["X7"]["nodes"]
            x22_nodes = pos_data["depths"][depth_key]["X22"]["nodes"]
            x26_nodes = pos_data["depths"][depth_key]["X26"]["nodes"]

            ratio_x7 = round(r1_nodes / x7_nodes, 3) if x7_nodes > 0 else 1.0
            ratio_x22 = round(r1_nodes / x22_nodes, 3) if x22_nodes > 0 else 1.0
            ratio_x26 = round(r1_nodes / x26_nodes, 3) if x26_nodes > 0 else 1.0

            r1_move = pos_data["depths"][depth_key]["R1"]["bestmove"]
            x22_move = pos_data["depths"][depth_key]["X22"]["bestmove"]
            agree_x22 = (r1_move == x22_move)

            pos_data["depths"][depth_key]["r1_ratios"] = {
                "nodes_vs_x7": ratio_x7,
                "nodes_vs_x22": ratio_x22,
                "nodes_vs_x26": ratio_x26,
                "move_agree_vs_x22": agree_x22
            }
            print(f"    --> R1 Node Ratios: vs X7={ratio_x7}x | vs X22={ratio_x22}x | vs X26={ratio_x26}x | Move Agree vs X22={agree_x22}")

        profile_results.append(pos_data)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(profile_results, f, indent=2)

    print("\n" + "=" * 85)
    print(f"Authoritative search efficiency raw JSON saved to:\n  {OUT_JSON}")
    print("=" * 85)

if __name__ == "__main__":
    main()
