"""Project Janus v0.59 - Phase 4 Statistical Analysis Script.

Processes phase4_evaluation_raw.json to generate findings for SEARCH_PERFORMANCE_REPORT.md.
"""

import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "analysis" / "v0.59" / "raw" / "phase4_evaluation_raw.json"


def analyze():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    depth_data = raw["depth_runs"]
    time_data = raw["time_runs"]
    configs = ["C1", "N8-A", "N8-B", "N8-C"]

    print("=" * 80)
    print("PHASE 4 HELD-OUT EVALUATION STATISTICAL REPORT (50 Positions)")
    print("=" * 80)

    # 1. Fixed Depth Performance
    print("\n" + "=" * 75)
    print("PART A: HELD-OUT FIXED DEPTH PERFORMANCE (Depths 5 & 6)")
    print("=" * 75)

    for d in [5, 6]:
        d_str = str(d)
        print(f"\n--- Nominal Depth {d} ---")
        print(f"{'Config':8s} | {'Nodes Total':12s} | {'Delta vs C1':12s} | {'Cutoff Rate':12s} | {'Move Agree':12s} | {'Neural Time':12s}")
        print("-" * 75)

        c1_tot_nodes = sum(p["depths"][d_str]["C1"]["nodes"] for p in depth_data)
        for cfg in configs:
            tot_nodes = sum(p["depths"][d_str][cfg]["nodes"] for p in depth_data)
            delta = ((tot_nodes - c1_tot_nodes) / c1_tot_nodes) * 100.0
            mean_cr = np.mean([p["depths"][d_str][cfg]["first_move_cutoff_rate"] for p in depth_data]) * 100.0
            agree = sum(1 for p in depth_data if p["depths"][d_str][cfg]["best_move"] == p["depths"][d_str]["C1"]["best_move"])
            agree_pct = agree / len(depth_data) * 100.0
            tot_inf_ms = sum(p["depths"][d_str][cfg]["neural_time_us"] for p in depth_data) / 1000.0
            print(f"{cfg:8s} | {tot_nodes:12,d} | {delta:+11.2f}% | {mean_cr:11.2f}% | {agree:2d}/50 ({agree_pct:4.1f}%) | {tot_inf_ms:10.2f} ms")

    # 2. Fixed Time Performance
    print("\n" + "=" * 80)
    print("PART B: HELD-OUT FIXED TIME PERFORMANCE (50ms & 100ms)")
    print("=" * 80)

    for t_ms in [50, 100]:
        t_str = str(t_ms)
        print(f"\n--- Fixed Time: {t_ms} ms ---")
        print(f"{'Config':8s} | {'Mean Depth':11s} | {'Median Depth':12s} | {'Total Nodes':12s} | {'NPS':10s} | {'Move Agree':12s} | {'Inference Time':15s}")
        print("-" * 88)

        for cfg in configs:
            depths = [p["times"][t_str][cfg]["depth"] for p in time_data]
            nodes = [p["times"][t_str][cfg]["nodes"] for p in time_data]
            tot_nodes = sum(nodes)
            nps = int(tot_nodes / (t_ms * 50 / 1000.0))

            agree = sum(1 for p in time_data if p["times"][t_str][cfg]["best_move"] == p["times"][t_str]["C1"]["best_move"])
            agree_pct = agree / len(time_data) * 100.0

            tot_inf_ms = sum(p["times"][t_str][cfg]["neural_time_us"] for p in time_data) / 1000.0
            pct_budget = (tot_inf_ms / (t_ms * 50)) * 100.0
            print(f"{cfg:8s} | {np.mean(depths):10.2f} | {np.median(depths):12.1f} | {tot_nodes:12,d} | {nps:10,d} | {agree:2d}/50 ({agree_pct:4.1f}%) | {tot_inf_ms:7.2f}ms ({pct_budget:3.2f}%)")

    # 3. Game Phase Breakdown (at 100ms)
    print("\n" + "=" * 80)
    print("PART C: PERFORMANCE BREAKDOWN BY GAME PHASE (100ms)")
    print("=" * 80)

    phases = sorted(list(set(p["phase"] for p in time_data)))
    for ph in phases:
        ph_positions = [p for p in time_data if p["phase"] == ph]
        n_pos = len(ph_positions)
        print(f"\n--- Phase: {ph.upper()} (N={n_pos} positions) ---")
        print(f"{'Config':8s} | {'Mean Depth':11s} | {'Total Nodes':12s} | {'NPS':10s} | {'Move Agree with C1':18s}")
        print("-" * 65)

        for cfg in configs:
            depths = [p["times"]["100"][cfg]["depth"] for p in ph_positions]
            nodes = [p["times"]["100"][cfg]["nodes"] for p in ph_positions]
            tot_nodes = sum(nodes)
            nps = int(tot_nodes / (100 * n_pos / 1000.0))
            agree = sum(1 for p in ph_positions if p["times"]["100"][cfg]["best_move"] == p["times"]["100"]["C1"]["best_move"])
            agree_pct = agree / n_pos * 100.0
            print(f"{cfg:8s} | {np.mean(depths):10.2f} | {tot_nodes:12,d} | {nps:10,d} | {agree:2d}/{n_pos} ({agree_pct:4.1f}%)")


if __name__ == "__main__":
    analyze()
