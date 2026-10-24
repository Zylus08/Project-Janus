"""Project Janus v0.33 - Match Analysis and Statistical Significance Tool."""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


def analyze_v033_match(json_path: str, output_path: str | None = None) -> dict[str, Any]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    summary = data.get("summary", {})
    games = data.get("games", [])

    print("=" * 80)
    print("PROJECT JANUS v0.33 — PLAYING-STRENGTH VALIDATION AUDIT")
    print("=" * 80)
    print(f"Match: {metadata.get('candidate_name', 'Janus-v0.33')} vs {metadata.get('baseline_name', 'Janus-v0.30')}")
    print(f"Time Control: {metadata.get('time_control')}")
    print(f"Completed Games: {summary.get('completed_games')}/{summary.get('games_total')}")
    print("-" * 80)

    # 1. Primary Score & Wald CI
    wins = summary.get("candidate_wins", 0)
    draws = summary.get("draws", 0)
    losses = summary.get("candidate_losses", 0)
    pts = summary.get("candidate_points", 0.0)
    score_pct = summary.get("candidate_score_pct", 0.0)
    ci_wald = summary.get("score_ci_95_wald", [0.0, 0.0])
    delta_elo = summary.get("delta_elo")

    print(f"Candidate Score: {pts:.1f} / {summary.get('completed_games')} ({score_pct:.1f}%)")
    print(f"Record (W-D-L):  {wins}W - {draws}D - {losses}L")
    print(f"95% Wald CI:     [{ci_wald[0]:.1f}%, {ci_wald[1]:.1f}%]")

    N = summary.get("completed_games", 0)
    S = pts / N if N > 0 else 0.5

    # Elo Uncertainty (Delta Method)
    elo_se = None
    elo_ci = None
    if 0 < S < 1 and N > 1:
        game_scores = [g["candidate_score"] for g in games]
        sample_var = sum((s - S) ** 2 for s in game_scores) / (N - 1)
        se_game = math.sqrt(sample_var / N)
        d_elo_ds = 400.0 / (math.log(10) * S * (1.0 - S))
        elo_se = round(d_elo_ds * se_game, 1)
        if delta_elo is not None:
            elo_ci = [round(delta_elo - 1.96 * elo_se, 1), round(delta_elo + 1.96 * elo_se, 1)]

    if delta_elo is not None:
        print(f"Estimated Delta Elo:  {delta_elo:+0.1f} (SE: +- {elo_se} Elo, 95% CI: [{elo_ci[0]}, {elo_ci[1]}])")
    else:
        print("Estimated Delta Elo:  N/A")

    # 2. Performance by Colour
    by_col = summary.get("by_color", {})
    w_stat = by_col.get("white", {})
    b_stat = by_col.get("black", {})
    print("\nPerformance by Colour:")
    print(f"  As White: {w_stat.get('wins', 0)}W - {w_stat.get('draws', 0)}D - {w_stat.get('losses', 0)}L | "
          f"Score: {w_stat.get('score_pts', 0):.1f}/{w_stat.get('games', 0)} ({w_stat.get('score_pct', 0.0)}%)")
    print(f"  As Black: {b_stat.get('wins', 0)}W - {b_stat.get('draws', 0)}D - {b_stat.get('losses', 0)}L | "
          f"Score: {b_stat.get('score_pts', 0):.1f}/{b_stat.get('games', 0)} ({b_stat.get('score_pct', 0.0)}%)")

    # 3. Opening-Pair Level Analysis
    p_comp = summary.get("pairs_completed", 0)
    p_won = summary.get("pairs_won", 0)
    p_drawn = summary.get("pairs_drawn", 0)
    p_lost = summary.get("pairs_lost", 0)
    p_boot_ci = summary.get("pair_bootstrap_ci_95")

    print("\nOpening-Pair Breakdown (Colour-Reversed Pairs):")
    print(f"  Pairs Completed: {p_comp}/{summary.get('pairs_total', 0)}")
    print(f"  Pairs Won:       {p_won} ({p_won/p_comp*100:.1f}%)" if p_comp else "  Pairs Won: 0")
    print(f"  Pairs Drawn:     {p_drawn} ({p_drawn/p_comp*100:.1f}%)" if p_comp else "  Pairs Drawn: 0")
    print(f"  Pairs Lost:      {p_lost} ({p_lost/p_comp*100:.1f}%)" if p_comp else "  Pairs Lost: 0")
    if p_boot_ci:
        print(f"  95% Bootstrap Pair CI: [{p_boot_ci[0]:.1f}%, {p_boot_ci[1]:.1f}%]")

    # Sign test on decisive pairs
    n_decisive = p_won + p_lost
    p_val_sign = None
    if n_decisive > 0:
        k_min = min(p_won, p_lost)
        p_val_sign = 2.0 * sum(math.comb(n_decisive, k) * (0.5 ** n_decisive) for k in range(0, k_min + 1))
        p_val_sign = min(1.0, round(p_val_sign, 4))
        print(f"  Decisive Pairs: {n_decisive} (Sign Test two-tailed p-value: {p_val_sign})")

    # 4. Search Characteristics Under Fixed Time
    s_stats = summary.get("search_stats", {})
    cand_depth = s_stats.get("candidate_avg_depth")
    base_depth = s_stats.get("baseline_avg_depth")
    cand_time = s_stats.get("candidate_avg_move_time_s")
    base_time = s_stats.get("baseline_avg_move_time_s")

    print("\nSearch Characteristics Under Fixed Time:")
    print(f"  Average Depth:     v0.33 = {cand_depth} plies | v0.30 = {base_depth} plies")
    print(f"  Average Move Time: v0.33 = {cand_time}s | v0.30 = {base_time}s")

    # 5. Terminations
    term_counts: dict[str, int] = {}
    for g in games:
        t = g.get("termination", "unknown")
        term_counts[t] = term_counts.get(t, 0) + 1

    print("\nGame Terminations:")
    for term, cnt in sorted(term_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {term:<30}: {cnt} ({cnt/len(games)*100:.1f}%)")
    print("=" * 80)

    analysis_result = {
        "metadata": metadata,
        "summary": summary,
        "elo_statistics": {
            "delta_elo": delta_elo,
            "elo_se": elo_se,
            "elo_ci_95": elo_ci,
        },
        "paired_statistics": {
            "decisive_pairs": n_decisive,
            "sign_test_p_value": p_val_sign,
        },
        "terminations": term_counts,
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, indent=2)
        print(f"Saved analysis to {output_path}")

    return analysis_result


def main():
    parser = argparse.ArgumentParser(description="Analyze v0.33 match results")
    parser.add_argument("json_path", help="Path to match JSON file")
    parser.add_argument("--output", help="Optional path to output analysis JSON")
    args = parser.parse_args()

    analyze_v033_match(args.json_path, args.output)


if __name__ == "__main__":
    main()
