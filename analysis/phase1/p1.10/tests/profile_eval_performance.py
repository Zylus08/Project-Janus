#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 5: Evaluation Performance & Throughput Profiling Harness
Profiles:
  - Evaluation calls per second (Raw leaf throughput)
  - Search NPS across 1T and 4T configurations
  - Pawn hash hit rate and probe latency
  - Verification of 15.5% throughput deficit recovery
"""

import os
import sys
import json
import time
import re
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.10" / "raw" / "eval_performance_recovery_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X14 = ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"

BENCH_POSITIONS = [
    {"id": "STARTPOS", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "KIWIPETE", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"},
    {"id": "MID_OPEN", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R w KQ - 1 9"},
    {"id": "MID_CLOSED","fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7"},
    {"id": "END_ROOK",  "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40"},
    {"id": "END_PAWN",  "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1"}
]

CONFIGS = [
    {"id": "X7_1T",     "name": "Frozen X7 Baseline (1T)",   "exe": EXE_X7,  "threads": 1, "opts": {}},
    {"id": "X14_1T",    "name": "Frozen X14 (1T Mode)",      "exe": EXE_X14, "threads": 1, "opts": {}},
    {"id": "CAND_S_1T", "name": "Candidate S (1T Lean)",    "exe": EXE_ABL, "threads": 1, "opts": {"UCI_Variant": "X7", "UCI_ClassicalEval": "E13", "UCI_LMP": "L0", "UCI_DynamicTime": "false"}},
    {"id": "X12_4T",     "name": "Frozen X12 Baseline (4T)", "exe": EXE_X12, "threads": 4, "opts": {}},
    {"id": "X14_4T",    "name": "Frozen X14 Platform (4T)",  "exe": EXE_X14, "threads": 4, "opts": {}},
    {"id": "CAND_P_4T", "name": "Candidate P (4T Hash Opt)","exe": EXE_ABL, "threads": 4, "opts": {"UCI_Variant": "X12", "UCI_ClassicalEval": "E13", "UCI_LMP": "L1", "UCI_DynamicTime": "true", "UCI_PawnHash": "true"}}
]

def run_bench(exe, threads, opts, fen, movetime_ms=800):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}"
    ]
    for opt, val in opts.items():
        cmds.append(f"setoption name {opt} value {val}")
    cmds.extend([
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ])

    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=10)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    for line in out.splitlines():
        if "info depth" in line:
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "depth": depth,
        "nodes": nodes,
        "nps": nps,
        "elapsed_s": round(dur, 4)
    }

def main():
    print("=== PROJECT JANUS P1.10: PHASE 5 EVALUATION PERFORMANCE PROFILING ===")
    results = {}

    for cfg in CONFIGS:
        cid = cfg["id"]
        cname = cfg["name"]
        print(f"\nBenchmarking {cid}: {cname}...")

        total_nodes = 0
        total_time = 0.0
        depth_sum = 0
        pos_results = {}

        for p in BENCH_POSITIONS:
            pid = p["id"]
            fen = p["fen"]
            res = run_bench(cfg["exe"], cfg["threads"], cfg["opts"], fen, movetime_ms=800)
            pos_results[pid] = res
            total_nodes += res["nodes"]
            total_time += res["elapsed_s"]
            depth_sum += res["depth"]
            print(f"  [{pid}] Depth: {res['depth']} | NPS: {res['nps']:,} | Nodes: {res['nodes']:,}")

        avg_nps = int(total_nodes / total_time) if total_time > 0 else 0
        avg_depth = round(depth_sum / len(BENCH_POSITIONS), 2)
        print(f"--> {cid} Aggregate: Avg Depth: {avg_depth} | Aggregate NPS: {avg_nps:,} | Total Nodes: {total_nodes:,}")

        results[cid] = {
            "name": cname,
            "threads": cfg["threads"],
            "avg_depth": avg_depth,
            "aggregate_nps": avg_nps,
            "total_nodes": total_nodes,
            "total_time_s": round(total_time, 2),
            "positions": pos_results
        }

    # Relative Throughput Calculations
    x7_nps = results["X7_1T"]["aggregate_nps"]
    x14_1t_nps = results["X14_1T"]["aggregate_nps"]
    cand_s_nps = results["CAND_S_1T"]["aggregate_nps"]

    x12_nps = results["X12_4T"]["aggregate_nps"]
    x14_4t_nps = results["X14_4T"]["aggregate_nps"]
    cand_p_nps = results["CAND_P_4T"]["aggregate_nps"]

    throughput_comparison = {
        "single_thread": {
            "X7_Baseline_NPS": x7_nps,
            "X14_Regressed_NPS": x14_1t_nps,
            "X14_Throughput_Delta": f"{(x14_1t_nps - x7_nps) / x7_nps * 100:.2f}%",
            "Candidate_S_NPS": cand_s_nps,
            "Candidate_S_Delta_vs_X7": f"{(cand_s_nps - x7_nps) / x7_nps * 100:.2f}%",
            "Candidate_S_Recovery_vs_X14": f"{(cand_s_nps - x14_1t_nps) / x14_1t_nps * 100:+.2f}%"
        },
        "four_thread": {
            "X12_Baseline_NPS": x12_nps,
            "X14_Platform_NPS": x14_4t_nps,
            "X14_Throughput_Delta": f"{(x14_4t_nps - x12_nps) / x12_nps * 100:.2f}%",
            "Candidate_P_NPS": cand_p_nps,
            "Candidate_P_Delta_vs_X12": f"{(cand_p_nps - x12_nps) / x12_nps * 100:+.2f}%",
            "Candidate_P_Advantage_vs_X14": f"{(cand_p_nps - x14_4t_nps) / x14_4t_nps * 100:+.2f}%"
        }
    }

    results["throughput_comparison"] = throughput_comparison

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved raw performance data to {RAW_OUT}")
    print("\nThroughput Analysis Summary:")
    print(json.dumps(throughput_comparison, indent=2))

if __name__ == "__main__":
    main()

