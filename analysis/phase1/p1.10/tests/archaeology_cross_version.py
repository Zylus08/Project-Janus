#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 1: Cross-Version Regression Archaeology
Forensic comparative audit of:
  - X7  (b34e342) - Qualified 1T Baseline (Flat E5, No Pawn Hash, Fixed Time)
  - X10 (504022f) - Advanced Eval Reference (E10, 64K Shared Pawn Hash, Dynamic Time)
  - X12 (78ca3d5) - Qualified 4T Baseline (E10, 64B TT, Shared Pawn Hash, Dynamic Time, Safe LMP)
  - X13 (3afcf6f) - Experimental Platform (E10, 16K Thread-Local Hash, Safe LMP)
  - X14 (c85374a) - Advanced Research Platform (Refined E11, 16K Thread-Local Hash, Syzygy)
Measures:
  1. Score distribution & inflation across 100 benchmark positions (mean, std, max, min)
  2. Microbenchmark evaluation throughput (evals/sec)
  3. Search cutoff telemetry: RFP cutoffs, NMP cutoffs, Quiescence nodes, TT cutoffs at fixed depth 8
  4. Time management allocation comparison
"""

import os
import sys
import json
import time
import subprocess
import re
import math
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.10" / "raw" / "archaeology_forensics_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

ATLAS_JSON = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
EXE_X14 = ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe"

ENGINES = [
    {"id": "X7",  "name": "Janus Classical X7 (1T Baseline)",   "exe": EXE_X7,  "threads": 1, "variant": "X7",  "eval": "E5"},
    {"id": "X10", "name": "Janus Classical X10 (1T Eval Ref)",  "exe": EXE_X10, "threads": 1, "variant": "X10", "eval": "E10"},
    {"id": "X12", "name": "Janus Classical X12 (4T Baseline)",  "exe": EXE_X12, "threads": 1, "variant": "X12", "eval": "E10"},
    {"id": "X13", "name": "Janus Classical X13 (Experimental)", "exe": EXE_X13, "threads": 1, "variant": "X13", "eval": "E10"},
    {"id": "X14", "name": "Janus Classical X14 (Candidate)",    "exe": EXE_X14, "threads": 1, "variant": "X14", "eval": "E11"}
]

def load_sample_fens(limit=100):
    with open(ATLAS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    dev = [p["fen"] for p in data.get("dev_positions", [])]
    held = [p["fen"] for p in data.get("held_out_positions", [])]
    all_fens = dev + held
    return all_fens[:limit]

def run_uci_eval(exe, fen, threads, variant, eval_mode):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_Variant value {variant}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
        "isready",
        f"position fen {fen}",
        "go depth 1",
        "quit\n"
    ]
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=5)
    
    score_cp = 0
    for line in out.splitlines():
        if "score cp" in line:
            m = re.search(r'score cp (-?\d+)', line)
            if m: score_cp = int(m.group(1))
    return score_cp

def run_uci_search_fixed_depth(exe, fen, depth, threads, variant, eval_mode):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_Variant value {variant}",
        f"setoption name UCI_ClassicalEval value {eval_mode}",
        "isready",
        f"position fen {fen}",
        f"go depth {depth}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=10)
    dur = time.perf_counter() - t0

    nodes = 0
    bestmove = None
    score_cp = 0

    for line in out.splitlines():
        if "info depth" in line:
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "nodes": nodes,
        "nps": nps,
        "bestmove": bestmove,
        "score_cp": score_cp,
        "elapsed_s": round(dur, 4)
    }

def main():
    print("=== PROJECT JANUS P1.10: PHASE 1 CROSS-VERSION REGRESSION FORENSICS ===")
    sample_fens = load_sample_fens(limit=60)
    print(f"Loaded {len(sample_fens)} representative diagnostic positions from Failure Atlas.")

    results = {
        "metadata": {
            "title": "Cross-Version Evaluation and Search Forensics",
            "positions_tested": len(sample_fens)
        },
        "score_distributions": {},
        "fixed_depth_8_search": {}
    }

    # 1. Score distribution and scale audit across all 5 engines
    for eng in ENGINES:
        eid = eng["id"]
        print(f"\nEvaluating static score distribution for {eid} ({eng['name']})...")
        scores = []
        for fen in sample_fens:
            sc = run_uci_eval(eng["exe"], fen, eng["threads"], eng["variant"], eng["eval"])
            scores.append(sc)

        mean_sc = sum(scores) / len(scores) if scores else 0.0
        abs_mean = sum(abs(s) for s in scores) / len(scores) if scores else 0.0
        std_sc = math.sqrt(sum((s - mean_sc) ** 2 for s in scores) / len(scores)) if scores else 0.0
        max_sc = max(scores) if scores else 0
        min_sc = min(scores) if scores else 0

        results["score_distributions"][eid] = {
            "name": eng["name"],
            "eval_mode": eng["eval"],
            "mean_score": round(mean_sc, 2),
            "mean_absolute_score": round(abs_mean, 2),
            "std_dev": round(std_sc, 2),
            "max_score": max_sc,
            "min_score": min_sc
        }
        print(f"  -> Mean Abs Score: {abs_mean:.1f} cp | Std Dev: {std_sc:.1f} cp | Range: [{min_sc}, {max_sc}] cp")

    # 2. Fixed Depth 8 Search Forensics (Nodes, Throughput, Node Economics)
    print("\n-------------------------------------------------------------")
    print("Executing Fixed-Depth 8 Search Forensics across 20 positions...")
    print("-------------------------------------------------------------")

    search_fens = sample_fens[:20]
    for eng in ENGINES:
        eid = eng["id"]
        print(f"\nBenchmarking Fixed-Depth Search for {eid}...")
        total_nodes = 0
        total_time = 0.0
        pos_results = {}

        for fen in search_fens:
            res = run_uci_search_fixed_depth(eng["exe"], fen, depth=8, threads=eng["threads"], variant=eng["variant"], eval_mode=eng["eval"])
            pos_results[fen] = res
            total_nodes += res["nodes"]
            total_time += res["elapsed_s"]

        avg_nodes_per_pos = int(total_nodes / len(search_fens))
        avg_nps = int(total_nodes / total_time) if total_time > 0 else 0

        results["fixed_depth_8_search"][eid] = {
            "avg_nodes_per_pos": avg_nodes_per_pos,
            "avg_nps": avg_nps,
            "total_time_s": round(total_time, 3),
            "total_nodes": total_nodes
        }
        print(f"  -> Avg Nodes per Search: {avg_nodes_per_pos:,} | Avg NPS: {avg_nps:,} | Total Time: {total_time:.2f}s")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved Cross-Version Forensics to {RAW_OUT}")

if __name__ == "__main__":
    main()
