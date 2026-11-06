"""Project Janus v0.59 - Phase 1 Statistical Analysis Script.

Processes phase1_influence_raw.json to generate empirical findings for NEURAL_ORDERING_INFLUENCE.md.
"""

import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "analysis" / "v0.59" / "raw" / "phase1_influence_raw.json"


def analyze():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    data = raw["data"]
    target_depths = raw["depths"]

    print("=" * 80)
    print("PHASE 1 STATISTICAL SUMMARY & ROOT MOVE-ORDERING TELEMETRY")
    print("=" * 80)

    # 1. Root legal move count distribution
    move_counts = [pos["n8_candidate"]["4"]["root_telemetry"]["root_move_count"] for pos in data]
    print(f"\n1. Root Legal Move Count Distribution (N=50 positions):")
    print(f"   Mean:   {np.mean(move_counts):.2f} moves")
    print(f"   Median: {np.median(move_counts):.1f} moves")
    print(f"   Min:    {np.min(move_counts)} moves")
    print(f"   Max:    {np.max(move_counts)} moves")

    # 2. Per-depth analysis
    for d in target_depths:
        d_str = str(d)
        print(f"\n" + "-" * 60)
        print(f"DEPTH {d} DETAILED METRICS (50 Positions)")
        print("-" * 60)

        spearman_list = []
        moves_reordered_pct = []
        neural_top_equals_classical_top_count = 0
        neural_top_searched_first_count = 0
        override_reasons = {}

        pv_is_neural_top1 = 0
        pv_is_neural_top3 = 0
        pv_is_classical_top1 = 0

        disagree_count = 0
        disagree_classical_won = 0
        disagree_neural_won = 0
        disagree_neither_won = 0

        c1_nodes_total = 0
        n8_nodes_total = 0
        c1_time_total = 0.0
        n8_time_total = 0.0

        c1_cutoffs_move0_sum = 0
        c1_cutoffs_total_sum = 0
        n8_cutoffs_move0_sum = 0
        n8_cutoffs_total_sum = 0

        neural_evals_total = 0
        neural_time_us_total = 0

        for pos in data:
            c1_rec = pos["c1_baseline"][d_str]
            n8_rec = pos["n8_candidate"][d_str]

            c1_telem = c1_rec["root_telemetry"]
            n8_telem = n8_rec["root_telemetry"]

            c1_nodes_total += c1_rec["nodes"]
            n8_nodes_total += n8_rec["nodes"]
            c1_time_total += c1_rec["elapsed"]
            n8_time_total += n8_rec["elapsed"]

            c1_cutoffs_move0_sum += c1_rec["ordering_telemetry"]["cutoff_move_1"]
            c1_cutoffs_total_sum += c1_rec["ordering_telemetry"]["total_cutoffs"]
            n8_cutoffs_move0_sum += n8_rec["ordering_telemetry"]["cutoff_move_1"]
            n8_cutoffs_total_sum += n8_rec["ordering_telemetry"]["total_cutoffs"]

            neural_evals_total += n8_rec["neural_telemetry"]["evaluations"]
            neural_time_us_total += n8_rec["neural_telemetry"]["inference_time_us"]

            # Correlation from N8-A telemetry
            sp = n8_telem.get("spearman_correlation", 0.0)
            spearman_list.append(sp)

            n_moves = n8_telem["root_move_count"]
            reordered = n8_telem["moves_reordered_count"]
            moves_reordered_pct.append(reordered / n_moves * 100.0)

            # Agreement
            if n8_telem["neural_top_equals_classical_top"]:
                neural_top_equals_classical_top_count += 1
            else:
                disagree_count += 1
                c_top = n8_telem["classical_top_move"]
                neu_top = n8_telem["neural_top_move"]
                pv = n8_telem["eventual_pv_move"]
                if pv == c_top:
                    disagree_classical_won += 1
                elif pv == neu_top:
                    disagree_neural_won += 1
                else:
                    disagree_neither_won += 1

            if n8_telem["neural_top_searched_first"]:
                neural_top_searched_first_count += 1
            else:
                reason = n8_telem.get("override_reason", "unknown")
                override_reasons[reason] = override_reasons.get(reason, 0) + 1

            # Eventual PV accuracy
            pv_neural_rank = n8_telem.get("eventual_pv_neural_rank", 0)
            pv_classical_rank = n8_telem.get("eventual_pv_classical_rank", 0)
            if pv_neural_rank == 1:
                pv_is_neural_top1 += 1
            if 1 <= pv_neural_rank <= 3:
                pv_is_neural_top3 += 1
            if pv_classical_rank == 1:
                pv_is_classical_top1 += 1

        print(f"a. Move Ranking Correlation:")
        print(f"   Spearman correlation mean:   {np.mean(spearman_list):+.4f} (std: {np.std(spearman_list):.4f})")
        print(f"   Moves priority changed:      {np.mean(moves_reordered_pct):.1f}% of root moves")

        print(f"\nb. Top Move Agreement & Override Mechanics:")
        print(f"   Neural Top == Classical Top: {neural_top_equals_classical_top_count}/50 ({neural_top_equals_classical_top_count/50*100:.1f}%)")
        print(f"   Neural Top Searched First:   {neural_top_searched_first_count}/50 ({neural_top_searched_first_count/50*100:.1f}%)")
        print(f"   Neural Top Overridden:       {50 - neural_top_searched_first_count}/50 ({(50 - neural_top_searched_first_count)/50*100:.1f}%)")
        print(f"   Override Reason Breakdown:")
        for r, cnt in sorted(override_reasons.items(), key=lambda x: -x[1]):
            print(f"     {r:20s}: {cnt:2d} ({cnt/50*100:.1f}%)")

        print(f"\nc. Disagreement Resolution (when Neural != Classical, N={disagree_count}):")
        if disagree_count > 0:
            print(f"   Eventual PV matched Classical Top: {disagree_classical_won} ({disagree_classical_won/disagree_count*100:.1f}%)")
            print(f"   Eventual PV matched Neural Top:    {disagree_neural_won} ({disagree_neural_won/disagree_count*100:.1f}%)")
            print(f"   Eventual PV matched Neither:       {disagree_neither_won} ({disagree_neither_won/disagree_count*100:.1f}%)")

        print(f"\nd. Eventual PV Move Prediction Accuracy (N=50):")
        print(f"   Classical Top-1 Accuracy: {pv_is_classical_top1}/50 ({pv_is_classical_top1/50*100:.1f}%)")
        print(f"   Neural Top-1 Accuracy:    {pv_is_neural_top1}/50 ({pv_is_neural_top1/50*100:.1f}%)")
        print(f"   Neural Top-3 Accuracy:    {pv_is_neural_top3}/50 ({pv_is_neural_top3/50*100:.1f}%)")

        print(f"\ne. Search Tree & Efficiency Impact:")
        print(f"   C1 Nodes: {c1_nodes_total:,d}  |  N8-A Nodes: {n8_nodes_total:,d}  (Delta: {((n8_nodes_total - c1_nodes_total)/c1_nodes_total)*100:+.2f}%)")
        print(f"   C1 Elapsed: {c1_time_total:.3f}s |  N8-A Elapsed: {n8_time_total:.3f}s (Delta: {((n8_time_total - c1_time_total)/c1_time_total)*100:+.2f}%)")
        c1_cutoff_rate = c1_cutoffs_move0_sum / c1_cutoffs_total_sum if c1_cutoffs_total_sum > 0 else 0
        n8_cutoff_rate = n8_cutoffs_move0_sum / n8_cutoffs_total_sum if n8_cutoffs_total_sum > 0 else 0
        print(f"   C1 First-Move Cutoff Rate:   {c1_cutoff_rate*100:.2f}% ({c1_cutoffs_move0_sum:,d} / {c1_cutoffs_total_sum:,d})")
        print(f"   N8-A First-Move Cutoff Rate: {n8_cutoff_rate*100:.2f}% ({n8_cutoffs_move0_sum:,d} / {n8_cutoffs_total_sum:,d})")
        print(f"   Neural Inferences:           {neural_evals_total} calls ({neural_time_us_total/1000:.2f} ms total, {neural_time_us_total/max(1, neural_evals_total):.1f} us/call)")


if __name__ == "__main__":
    analyze()

