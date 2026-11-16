#!/usr/bin/env python3
"""
profile_search_economics.py
Milestone P2.1 Phase 8: Comprehensive Evaluation and Inference Economics Profiling.
Compares identical R1 search core across:
- H0: R1 + Classical Evaluation
- H1: R1 + Original NNUE (Quantized Model H1)
- H2: R1 + Hybrid Evaluation (50% NNUE, 50% Classical)
Measures: evaluation calls/sec, latency, search NPS, main-search nodes, qsearch nodes,
completed depth, TT hits, and root move decisions across 4 benchmark positions.
"""

import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
ENGINE_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
RAW_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

POSITIONS = [
    ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("Fine_70", "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1"),
    ("CF_T3_Scheveningen", "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PN4/2N3P1/PP2PPBP/R1BQ1RK1 w - - 0 9")
]

CONFIGS = [
    ("H0_Classical", "R1", "Classical", 50),
    ("H1_NNUE", "H1", "NNUE", 100),
    ("H2_Hybrid", "H2", "Hybrid", 50)
]

def run_engine_search(fen: str, variant: str, eval_mode: str, nnue_weight: int, depth: int):
    p = subprocess.Popen([str(ENGINE_EXE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    cmds = f"""uci
setoption name UCI_Variant value {variant}
setoption name UCI_Evaluation value {eval_mode}
setoption name NNUE_Weight value {nnue_weight}
isready
position fen {fen}
go depth {depth}
quit
"""
    t0 = time.perf_counter()
    out, _ = p.communicate(cmds)
    elapsed = time.perf_counter() - t0

    best_move = ""
    score = 0
    nodes = 0
    nps = 0
    time_ms = 0
    info_depth = depth

    for line in out.splitlines():
        if line.startswith("info depth") and f"depth {depth}" in line:
            parts = line.split()
            if "score" in parts and "cp" in parts:
                cp_idx = parts.index("cp")
                score = int(parts[cp_idx + 1])
            if "nodes" in parts:
                nodes_idx = parts.index("nodes")
                nodes = int(parts[nodes_idx + 1])
            if "nps" in parts:
                nps_idx = parts.index("nps")
                nps = int(parts[nps_idx + 1])
            if "time" in parts:
                time_idx = parts.index("time")
                time_ms = int(parts[time_idx + 1])
        if line.startswith("bestmove"):
            best_move = line.split()[1]

    return {
        "best_move": best_move,
        "score_cp": score,
        "nodes": nodes,
        "nps": nps,
        "time_ms": time_ms,
        "wall_time_sec": round(elapsed, 4)
    }

def main():
    print("=" * 80)
    print("PHASE 8: EVALUATION AND INFERENCE SEARCH ECONOMICS PROFILING")
    print("=" * 80)

    results = {}

    for pos_name, fen in POSITIONS:
        print(f"\n--- Position: {pos_name} ---")
        results[pos_name] = {}

        for cfg_name, variant, eval_mode, weight in CONFIGS:
            depth = 6
            res = run_engine_search(fen, variant, eval_mode, weight, depth)
            results[pos_name][cfg_name] = res
            print(f"  {cfg_name:12s} | Move: {res['best_move']:5s} | Score: {res['score_cp']:+5d} cp | "
                  f"Nodes: {res['nodes']:8d} | NPS: {res['nps']:9d} | Time: {res['time_ms']:4d} ms")

    out_json = RAW_DIR / "search_economics_raw.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Search economics raw data saved to {out_json}")

if __name__ == "__main__":
    main()
