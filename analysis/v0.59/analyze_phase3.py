"""Project Janus v0.59 - Phase 3 Statistical Analysis Script.

Processes phase3_gating_ablation_raw.json to generate findings for SEARCH_GATING_ABLATION.md.
"""

import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "analysis" / "v0.59" / "raw" / "phase3_gating_ablation_raw.json"


def analyze():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    depth_data = raw["fixed_depth_results"]
    time_data = raw["fixed_time_results"]

    print("=" * 80)
    print("PHASE 3 SEARCH GATING STATISTICAL REPORT")
    print("=" * 80)

    # 1. Part A: Fixed Depth Evaluation
    print("\n" + "=" * 75)
    print("PART A: FIXED DEPTH SEARCH GATING (N=50 positions)")
    print("=" * 75)

    cfgs = ["C0", "G1", "G2", "G3"]
    for d in [5, 6]:
        d_str = str(d)
        print(f"\n--- Depth {d} Performance ---")
        print(f"{'Config':8s} | {'Nodes Total':12s} | {'Delta vs C0':12s} | {'Cutoff Rate':12s} | {'Neural Calls':13s} | {'Neural Time':12s}")
        print("-" * 75)

        c0_tot_nodes = sum(p["depths"][d_str]["C0"]["nodes"] for p in depth_data)
        for cfg in cfgs:
            tot_nodes = sum(p["depths"][d_str][cfg]["nodes"] for p in depth_data)
            delta = ((tot_nodes - c0_tot_nodes) / c0_tot_nodes) * 100.0
            mean_cr = np.mean([p["depths"][d_str][cfg]["first_move_cutoff_rate"] for p in depth_data]) * 100.0
            tot_evals = sum(p["depths"][d_str][cfg]["neural_evals"] for p in depth_data)
            tot_time_ms = sum(p["depths"][d_str][cfg]["neural_time_us"] for p in depth_data) / 1000.0
            print(f"{cfg:8s} | {tot_nodes:12,d} | {delta:+11.2f}% | {mean_cr:11.2f}% | {tot_evals:13,d} | {tot_time_ms:10.2f} ms")

    # 2. Part B: Fixed Time Evaluation with Latency Budgets
    print("\n" + "=" * 80)
    print("PART B: FIXED TIME SEARCH WITH BOUNDED INFERENCE BUDGETS (N=50 positions)")
    print("=" * 80)

    for t_ms in [50, 100]:
        t_str = str(t_ms)
        print(f"\n--- Time Limit: {t_ms} ms ---")
        print(f"{'Config':16s} | {'Mean Depth':11s} | {'Median Depth':12s} | {'Total Nodes':12s} | {'NPS':10s} | {'Move Agree':12s} | {'Inference Time':15s}")
        print("-" * 88)

        # C0 Baseline
        c0_depths = [p["times"][t_str]["C0"]["depth"] for p in time_data]
        c0_nodes = [p["times"][t_str]["C0"]["nodes"] for p in time_data]
        c0_tot_nodes = sum(c0_nodes)
        c0_nps = int(c0_tot_nodes / (t_ms * 50 / 1000.0))
        print(f"{'C0 (Baseline)':16s} | {np.mean(c0_depths):10.2f} | {np.median(c0_depths):12.1f} | {c0_tot_nodes:12,d} | {c0_nps:10,d} | 50/50 (100.0%) | {'0.00 ms (0.0%)':15s}")

        for gid in ["G1", "G2", "G3"]:
            for b_label in ["0.5pct", "1.0pct", "2.0pct"]:
                name = f"{gid} ({b_label})"
                depths = [p["times"][t_str][gid][b_label]["depth"] for p in time_data]
                nodes = [p["times"][t_str][gid][b_label]["nodes"] for p in time_data]
                tot_nodes = sum(nodes)
                nps = int(tot_nodes / (t_ms * 50 / 1000.0))
                
                agree = sum(1 for p in time_data if p["times"][t_str][gid][b_label]["best_move"] == p["times"][t_str]["C0"]["best_move"])
                agree_pct = agree / len(time_data) * 100.0

                tot_inf_ms = sum(p["times"][t_str][gid][b_label]["neural_time_us"] for p in time_data) / 1000.0
                actual_pct = (tot_inf_ms / (t_ms * 50)) * 100.0

                print(f"{name:16s} | {np.mean(depths):10.2f} | {np.median(depths):12.1f} | {tot_nodes:12,d} | {nps:10,d} | {agree:2d}/50 ({agree_pct:4.1f}%) | {tot_inf_ms:7.2f}ms ({actual_pct:3.2f}%)")


if __name__ == "__main__":
    analyze()

