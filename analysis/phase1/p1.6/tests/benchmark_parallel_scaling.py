#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.6
Phase 4: Parallel Scaling & Throughput Benchmark
Evaluates X7 (1T), X10 (1T), X11 (1T), X11 (2T), X11 (4T) across 50 standard opening positions.
"""

import subprocess
import json
import time
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
OPENINGS_FILE = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
X7_EXE = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
X10_EXE = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
X11_EXE = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.6" / "raw" / "parallel_scaling_raw.json"

MOVETIME_MS = 400

def load_positions(count=50):
    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item["fen"] for item in data[:count]]

def run_uci(exe, commands, timeout_sec=15):
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def evaluate_config(exe, name, threads=1, variant=None, positions=[]):
    print(f"\n[BENCHMARK] Evaluating {name} (Threads={threads})...")
    total_nodes = 0
    total_depth = 0
    total_elapsed = 0.0
    pos_data = []

    init_cmds = "uci\n"
    if threads is not None:
        init_cmds += f"setoption name Threads value {threads}\n"
    if variant is not None:
        init_cmds += f"setoption name UCI_Variant value {variant}\n"
    init_cmds += "isready\n"

    for idx, fen in enumerate(positions):
        cmds = init_cmds + f"position fen {fen}\ngo movetime {MOVETIME_MS}\nquit\n"
        t0 = time.perf_counter()
        out = run_uci(exe, cmds, timeout_sec=10)
        elapsed = time.perf_counter() - t0

        max_depth = 0
        nodes = 0
        for line in out.splitlines():
            if "info" in line:
                m_depth = re.search(r'depth (\d+)', line)
                m_nodes = re.search(r'nodes (\d+)', line)
                if m_depth:
                    d = int(m_depth.group(1))
                    if d > max_depth:
                        max_depth = d
                if m_nodes:
                    nodes = int(m_nodes.group(1))

        total_nodes += nodes
        total_depth += max_depth
        total_elapsed += elapsed
        pos_data.append({
            "pos_index": idx + 1,
            "depth": max_depth,
            "nodes": nodes,
            "elapsed_sec": round(elapsed, 4)
        })

    avg_depth = round(total_depth / len(positions), 2)
    agg_nps = int(total_nodes / total_elapsed) if total_elapsed > 0 else 0

    print(f"  Completed: Nodes={total_nodes:,}, Time={total_elapsed:.2f}s, AvgDepth={avg_depth}, AggNPS={agg_nps:,}")
    return {
        "engine": name,
        "threads": threads,
        "positions_count": len(positions),
        "total_nodes": total_nodes,
        "total_elapsed_sec": round(total_elapsed, 3),
        "avg_completed_depth": avg_depth,
        "aggregate_nps": agg_nps,
        "per_position_sample": pos_data[:5]
    }

def main():
    positions = load_positions(50)
    print(f"Loaded {len(positions)} benchmark positions from {OPENINGS_FILE}")

    configs = [
        {"exe": X7_EXE, "name": "Janus Classical X7 (Control)", "threads": 1, "variant": None},
        {"exe": X10_EXE, "name": "Janus Classical X10 (Reference)", "threads": 1, "variant": None},
        {"exe": X11_EXE, "name": "Janus Classical X11 (1T)", "threads": 1, "variant": "X11"},
        {"exe": X11_EXE, "name": "Janus Classical X11 (2T)", "threads": 2, "variant": "X11"},
        {"exe": X11_EXE, "name": "Janus Classical X11 (4T)", "threads": 4, "variant": "X11"}
    ]

    results = {}
    for cfg in configs:
        key = cfg["name"]
        res = evaluate_config(cfg["exe"], key, cfg["threads"], cfg["variant"], positions)
        results[key] = res

    # Calculate scaling metrics relative to X11 (1T)
    base_nps = results["Janus Classical X11 (1T)"]["aggregate_nps"]
    base_depth = results["Janus Classical X11 (1T)"]["avg_completed_depth"]

    for name, data in results.items():
        nps = data["aggregate_nps"]
        speedup = round(nps / base_nps, 3) if base_nps > 0 else 1.0
        eff = round((speedup / data["threads"]) * 100.0, 1) if data["threads"] > 0 else 100.0
        depth_diff = round(data["avg_completed_depth"] - base_depth, 2)
        data["speedup_vs_x11_1t"] = speedup
        data["efficiency_pct"] = eff
        data["depth_advantage_vs_x11_1t"] = depth_diff

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Scaling benchmark saved to {RAW_OUT}")
    print("\nSummary Table:")
    print(f"{'Engine / Configuration':<32} | {'Threads':<7} | {'Avg Depth':<10} | {'Nodes':<12} | {'Agg NPS':<12} | {'Speedup':<8} | {'Efficiency':<10}")
    print("-" * 102)
    for name, d in results.items():
        print(f"{name:<32} | {d['threads']:<7} | {d['avg_completed_depth']:<10} | {d['total_nodes']:<12,d} | {d['aggregate_nps']:<12,d} | {d['speedup_vs_x11_1t']:<8.2f} | {d['efficiency_pct']:<9.1f}%")

if __name__ == "__main__":
    main()

