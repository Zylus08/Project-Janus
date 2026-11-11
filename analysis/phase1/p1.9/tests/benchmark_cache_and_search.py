#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 5: Search & Evaluation Cache Hierarchy Performance Benchmark
Compares X7, X10, X12, X13, and Refined E11 across 12 canonical positions.
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "cache_performance_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

BENCHMARK_POSITIONS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bq1rk1/pp4pp/2n2p2/1BbpP3/5Q2/2N5/PP3PPP/R1B1K1NR w KQ - 3 11",
    "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15",
    "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40",
    "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10",
    "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9",
    "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7",
    "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9",
    "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
    "8/8/4k3/8/4K3/8/8/8 w - - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
]

CONFIGS = [
    {"id": "X7_1T",       "name": "X7 (1T, Flat Eval E5, No Pawn Hash)",         "exe": EXE_X7,  "threads": 1, "eval": "E5"},
    {"id": "X10_1T",      "name": "X10 (1T, E10 Eval, 64K Shared Pawn Hash)",    "exe": EXE_X10, "threads": 1, "eval": "E10"},
    {"id": "X12_4T",      "name": "X12 (4T, E10 Eval, 64K Shared Pawn Hash)",    "exe": EXE_X12, "threads": 4, "eval": "E10"},
    {"id": "X13_4T",      "name": "X13 (4T, E10 Eval, 16K Thread-Local Hash)",   "exe": EXE_X13, "threads": 4, "eval": "E10"},
    {"id": "Refined_E11", "name": "Refined E11 (4T, E11 Eval, 16K Thread-Local)", "exe": EXE_ABL, "threads": 4, "eval": "E14"}
]

def run_bench(exe, fen, threads, eval_mode, movetime_ms=500):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=10)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None

    for line in out.splitlines():
        if "info depth" in line:
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {"depth": depth, "nodes": nodes, "nps": nps, "bestmove": bestmove, "elapsed_s": round(dur, 4)}

def main():
    print("=== PROJECT JANUS P1.9: PHASE 5 MEMORY & SEARCH PERFORMANCE BENCHMARK ===")
    results = {}

    for cfg in CONFIGS:
        cid = cfg["id"]
        cname = cfg["name"]
        print(f"\nBenchmarking {cid}: {cname}...")
        total_depth = 0
        total_nodes = 0
        total_time = 0.0
        pos_results = {}

        for fen in BENCHMARK_POSITIONS:
            res = run_bench(cfg["exe"], fen, cfg["threads"], cfg["eval"], movetime_ms=400)
            pos_results[fen] = res
            total_depth += res["depth"]
            total_nodes += res["nodes"]
            total_time += res["elapsed_s"]

        avg_depth = round(total_depth / len(BENCHMARK_POSITIONS), 2)
        avg_nps = int(total_nodes / total_time) if total_time > 0 else 0

        results[cid] = {
            "name": cname,
            "threads": cfg["threads"],
            "avg_depth": avg_depth,
            "avg_nps": avg_nps,
            "total_elapsed_s": round(total_time, 2)
        }
        print(f"  -> Depth: {avg_depth} plies | NPS: {avg_nps:,} in {results[cid]['total_elapsed_s']}s")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved memory & search benchmarks to {RAW_OUT}")

if __name__ == "__main__":
    main()

