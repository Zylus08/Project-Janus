#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.6
Phase 7: Factorial Ablation Matrix (LMP & Parallel Search Interactions)
Evaluates 6 configurations across 20 representative openings:
  B0: Baseline X7 (1T Control, Frozen)
  B1: X7 + Safe LMP L1 (1T)
  B2: X7 + Lazy SMP Infrastructure (1T, LMP L0)
  B3: X7 + Lazy SMP Multithreaded (4T, LMP L0)
  B4: Full Candidate X11 (4T, LMP L1, Advanced Eval)
  B5: Reference X10 (1T Reference, Frozen)
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
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.6" / "raw" / "factorial_ablation_raw.json"

MOVETIME_MS = 400
NUM_POSITIONS = 20

def load_positions(count=20):
    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item["fen"] for item in data[:count]]

def run_uci(exe, commands, timeout_sec=15):
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def run_ablation_variant(variant_def, positions):
    name = variant_def["name"]
    exe = variant_def["exe"]
    threads = variant_def.get("threads", 1)
    var_opt = variant_def.get("variant", None)
    lmp_opt = variant_def.get("lmp", None)

    print(f"\n[ABLATION] Testing {name} (Threads={threads}, Variant={var_opt}, LMP={lmp_opt})...")
    total_nodes = 0
    total_depth = 0
    total_elapsed = 0.0

    init_cmds = "uci\n"
    if threads is not None:
        init_cmds += f"setoption name Threads value {threads}\n"
    if var_opt is not None:
        init_cmds += f"setoption name UCI_Variant value {var_opt}\n"
    if lmp_opt is not None:
        init_cmds += f"setoption name UCI_LMP value {lmp_opt}\n"
    init_cmds += "isready\n"

    pos_records = []
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
        pos_records.append({
            "pos": idx + 1,
            "depth": max_depth,
            "nodes": nodes,
            "elapsed_sec": round(elapsed, 4)
        })

    avg_depth = round(total_depth / len(positions), 2)
    agg_nps = int(total_nodes / total_elapsed) if total_elapsed > 0 else 0

    print(f"  Finished: Nodes={total_nodes:,}, Time={total_elapsed:.2f}s, AvgDepth={avg_depth}, NPS={agg_nps:,}")
    return {
        "name": name,
        "threads": threads,
        "variant_opt": var_opt,
        "lmp_opt": lmp_opt,
        "positions_count": len(positions),
        "total_nodes": total_nodes,
        "total_elapsed_sec": round(total_elapsed, 3),
        "avg_completed_depth": avg_depth,
        "aggregate_nps": agg_nps,
        "sample_positions": pos_records[:3]
    }

def main():
    positions = load_positions(NUM_POSITIONS)
    print(f"Loaded {len(positions)} positions for Factorial Ablation Matrix.")

    matrix = [
        {
            "id": "B0",
            "name": "B0: Baseline X7 (1T Control)",
            "exe": X7_EXE,
            "threads": 1,
            "variant": None,
            "lmp": None
        },
        {
            "id": "B1",
            "name": "B1: X7 + Safe LMP L1 (1T)",
            "exe": X11_EXE,
            "threads": 1,
            "variant": "X7",
            "lmp": "L1"
        },
        {
            "id": "B2",
            "name": "B2: X7 + Lazy SMP Harness (1T, LMP L0)",
            "exe": X11_EXE,
            "threads": 1,
            "variant": "X7",
            "lmp": "L0"
        },
        {
            "id": "B3",
            "name": "B3: X7 + Lazy SMP Parallel (4T, LMP L0)",
            "exe": X11_EXE,
            "threads": 4,
            "variant": "X7",
            "lmp": "L0"
        },
        {
            "id": "B4",
            "name": "B4: Full Candidate X11 (4T, LMP L1, Advanced Eval)",
            "exe": X11_EXE,
            "threads": 4,
            "variant": "X11",
            "lmp": "L1"
        },
        {
            "id": "B5",
            "name": "B5: Reference X10 (1T Reference)",
            "exe": X10_EXE,
            "threads": 1,
            "variant": None,
            "lmp": None
        }
    ]

    results = {}
    for item in matrix:
        res = run_ablation_variant(item, positions)
        results[item["id"]] = res

    # Compute comparisons against B0 baseline
    b0_nodes = results["B0"]["total_nodes"]
    b0_depth = results["B0"]["avg_completed_depth"]
    b0_nps = results["B0"]["aggregate_nps"]

    for k, v in results.items():
        v["node_ratio_vs_b0"] = round(v["total_nodes"] / b0_nodes, 3) if b0_nodes > 0 else 1.0
        v["depth_delta_vs_b0"] = round(v["avg_completed_depth"] - b0_depth, 2)
        v["speedup_vs_b0"] = round(v["aggregate_nps"] / b0_nps, 3) if b0_nps > 0 else 1.0

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Factorial Ablation Matrix saved to {RAW_OUT}")
    print("\n" + "=" * 95)
    print(f"{'Variant ID & Description':<40} | {'Thr':<3} | {'Avg Depth':<9} | {'Nodes':<10} | {'Agg NPS':<10} | {'Node Ratio':<10} | {'Depth Δ':<8}")
    print("-" * 95)
    for k, v in results.items():
        print(f"{v['name']:<40} | {v['threads']:<3} | {v['avg_completed_depth']:<9} | {v['total_nodes']:<10,d} | {v['aggregate_nps']:<10,d} | {v['node_ratio_vs_b0']:<10.2f} | {v['depth_delta_vs_b0']:+<7.2f}")
    print("=" * 95)

if __name__ == "__main__":
    main()

