"""Project Janus v0.59 - Phase 2 Statistical Analysis Script.

Processes phase2_causal_ablation_raw.json to generate findings for CAUSAL_POLICY_ABLATION.md.
"""

import json
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "analysis" / "v0.59" / "raw" / "phase2_causal_ablation_raw.json"


def analyze():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    data = raw["data"]
    depths = raw["depths"]
    cond_ids = [c["id"] for c in raw["conditions"]]

    print("=" * 80)
    print("PHASE 2 CAUSAL CONTROL EXPERIMENTS STATISTICAL REPORT")
    print("=" * 80)

    for d in depths:
        d_str = str(d)
        print(f"\n" + "-" * 70)
        print(f"DEPTH {d} CAUSAL COMPARISON (N=50 positions)")
        print("-" * 70)

        nodes_by_cond = {c: [] for c in cond_ids}
        time_by_cond = {c: [] for c in cond_ids}
        cutoff_rate_by_cond = {c: [] for c in cond_ids}
        bm_agreement = {c: 0 for c in cond_ids}

        for pos in data:
            c0_bm = pos["runs"]["C0"][d_str]["best_move"]
            for c in cond_ids:
                rec = pos["runs"][c][d_str]
                nodes_by_cond[c].append(rec["nodes"])
                time_by_cond[c].append(rec["elapsed"])
                cutoff_rate_by_cond[c].append(rec["first_move_cutoff_rate"])
                if rec["best_move"] == c0_bm:
                    bm_agreement[c] += 1

        print(f"{'Condition':10s} | {'Total Nodes':12s} | {'Delta vs C0':12s} | {'Mean Time':10s} | {'Cutoff Rate':12s} | {'Move Agree':12s}")
        print("-" * 78)

        tot_c0_nodes = sum(nodes_by_cond["C0"])
        for c in cond_ids:
            tot_nodes = sum(nodes_by_cond[c])
            delta_pct = ((tot_nodes - tot_c0_nodes) / tot_c0_nodes) * 100.0
            mean_time = np.mean(time_by_cond[c])
            mean_cr = np.mean(cutoff_rate_by_cond[c]) * 100.0
            agr = bm_agreement[c]
            agr_pct = agr / len(data) * 100.0
            print(f"{c:10s} | {tot_nodes:12,d} | {delta_pct:+11.2f}% | {mean_time:8.4f}s | {mean_cr:11.2f}% | {agr:2d}/50 ({agr_pct:4.1f}%)")

        # Paired statistics for Depth d
        print(f"\nPaired Node Difference Hypothesis Tests (df=49):")
        def paired_test(c_treat, c_ctrl):
            diffs = [nodes_by_cond[c_treat][i] - nodes_by_cond[c_ctrl][i] for i in range(len(data))]
            mean_diff = np.mean(diffs)
            std_diff = np.std(diffs, ddof=1)
            se_diff = std_diff / math.sqrt(len(diffs))
            t_stat = mean_diff / se_diff if se_diff > 0 else 0.0
            return mean_diff, se_diff, t_stat

        comparisons = [
            ("C1 (Trained)", "C0 (Classical)", "C1", "C0"),
            ("C2 (Random)",  "C0 (Classical)", "C2", "C0"),
            ("C3 (Shuffled)","C0 (Classical)", "C3", "C0"),
            ("C1 (Trained)", "C2 (Random)",    "C1", "C2"),
            ("C1 (Trained)", "C3 (Shuffled)",  "C1", "C3"),
        ]

        for name1, name2, c1, c2 in comparisons:
            m_diff, se, t_val = paired_test(c1, c2)
            rel_diff = m_diff / np.mean(nodes_by_cond[c2]) * 100.0
            p_approx = "p > 0.05 (not sig)" if abs(t_val) < 2.009 else "p < 0.05 *"
            print(f"  {name1:14s} vs {name2:14s}: Mean Δ = {m_diff:+8.1f} nodes ({rel_diff:+5.2f}%), t = {t_val:+6.3f} [{p_approx}]")


if __name__ == "__main__":
    analyze()

