"""Independent statistical analysis and verification for Project Janus v0.34 match data."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def analyze_v034_data(json_path: Path) -> dict[str, Any]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    summary = data.get("summary", {})
    games = data.get("games", [])

    total_games = len(games)
    cand_wins = 0
    cand_draws = 0
    cand_losses = 0

    by_color = {
        "white": {"wins": 0, "draws": 0, "losses": 0, "score": 0.0, "games": 0},
        "black": {"wins": 0, "draws": 0, "losses": 0, "score": 0.0, "games": 0},
    }

    pairs: dict[int, list[dict[str, Any]]] = {}
    cand_move_times: list[float] = []
    base_move_times: list[float] = []
    cand_depths: list[float] = []
    base_depths: list[float] = []
    cand_nodes: list[float] = []
    base_nodes: list[float] = []

    for g in games:
        pair = g["pair"]
        pairs.setdefault(pair, []).append(g)

        cand_color = g["candidate_color"]
        res = g["result"]

        if res == "1-0":
            if cand_color == "white":
                cand_wins += 1
                by_color["white"]["wins"] += 1
                by_color["white"]["score"] += 1.0
            else:
                cand_losses += 1
                by_color["black"]["losses"] += 1
        elif res == "0-1":
            if cand_color == "white":
                cand_losses += 1
                by_color["white"]["losses"] += 1
            else:
                cand_wins += 1
                by_color["black"]["wins"] += 1
                by_color["black"]["score"] += 1.0
        elif res == "1/2-1/2":
            cand_draws += 1
            by_color[cand_color]["draws"] += 1
            by_color[cand_color]["score"] += 0.5

        by_color[cand_color]["games"] += 1

        if g.get("avg_cand_move_time") is not None:
            cand_move_times.append(g["avg_cand_move_time"])
        if g.get("avg_base_move_time") is not None:
            base_move_times.append(g["avg_base_move_time"])
        if g.get("avg_cand_depth") is not None:
            cand_depths.append(g["avg_cand_depth"])
        if g.get("avg_base_depth") is not None:
            base_depths.append(g["avg_base_depth"])
        if g.get("avg_cand_nodes") is not None:
            cand_nodes.append(g["avg_cand_nodes"])
        if g.get("avg_base_nodes") is not None:
            base_nodes.append(g["avg_base_nodes"])

    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_games * 100.0) if total_games > 0 else 0.0

    # Elo Point Estimate & Standard Error
    p = cand_score / total_games if total_games > 0 else 0.5
    if 0 < p < 1:
        elo_diff = -400.0 * math.log10((1.0 - p) / p)
        se_p = math.sqrt((p * (1.0 - p)) / total_games)
        se_elo = (400.0 / (math.log(10) * p * (1.0 - p))) * se_p
        elo_ci = [round(elo_diff - 1.96 * se_elo, 1), round(elo_diff + 1.96 * se_elo, 1)]
    else:
        elo_diff = None
        se_elo = None
        elo_ci = None

    # Pair analysis
    pair_scores: list[float] = []
    pair_diffs: list[float] = []
    won_pairs = 0
    drawn_pairs = 0
    lost_pairs = 0

    for p_id, p_games in sorted(pairs.items()):
        if len(p_games) == 2:
            s = 0.0
            for g in p_games:
                r = g["result"]
                c = g["candidate_color"]
                if r == "1/2-1/2":
                    s += 0.5
                elif (r == "1-0" and c == "white") or (r == "0-1" and c == "black"):
                    s += 1.0
            pair_scores.append(s)
            diff = s - 1.0  # +1.0, 0.0, or -1.0
            pair_diffs.append(diff)
            if diff > 0:
                won_pairs += 1
            elif diff < 0:
                lost_pairs += 1
            else:
                drawn_pairs += 1

    decisive_pairs = won_pairs + lost_pairs
    sign_test_p = None
    if decisive_pairs > 0:
        k = min(won_pairs, lost_pairs)
        sign_test_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        sign_test_p = min(1.0, sign_test_p)

    # Paired t-test
    n_pairs = len(pair_diffs)
    if n_pairs > 1:
        mean_d = sum(pair_diffs) / n_pairs
        var_d = sum((d - mean_d) ** 2 for d in pair_diffs) / (n_pairs - 1)
        se_d = math.sqrt(var_d / n_pairs) if var_d > 0 else 0.0
        t_stat = (mean_d / se_d) if se_d > 0 else 0.0

        # Approximate two-tailed p-value via normal CDF for large N (df ~ 49)
        z = abs(t_stat)
        p_approx = math.erfc(z / math.sqrt(2))
    else:
        mean_d = 0.0
        se_d = 0.0
        t_stat = 0.0
        p_approx = 1.0

    return {
        "metadata": meta,
        "match_record": {
            "total_games": total_games,
            "candidate_wins": cand_wins,
            "candidate_draws": cand_draws,
            "candidate_losses": cand_losses,
            "candidate_points": cand_score,
            "candidate_score_pct": round(cand_score_pct, 2),
            "estimated_elo": round(elo_diff, 1) if elo_diff is not None else None,
            "elo_se": round(se_elo, 1) if se_elo is not None else None,
            "elo_95_ci": elo_ci,
        },
        "by_color": by_color,
        "pairs_analysis": {
            "total_pairs": len(pairs),
            "completed_pairs": n_pairs,
            "won_pairs": won_pairs,
            "drawn_pairs": drawn_pairs,
            "lost_pairs": lost_pairs,
            "decisive_pairs": decisive_pairs,
            "pair_score_points": sum(pair_scores),
            "pair_win_rate_pct": round((sum(pair_scores) / (2 * n_pairs)) * 100.0, 2) if n_pairs > 0 else 0.0,
            "paired_diff_mean": round(mean_d, 4),
            "paired_diff_se": round(se_d, 4),
            "paired_t_statistic": round(t_stat, 4),
            "paired_t_p_value_approx": round(p_approx, 4),
            "sign_test_p_value": round(sign_test_p, 4) if sign_test_p is not None else None,
            "statistically_significant_at_05": (p_approx < 0.05),
        },
        "search_and_timing_diagnostics": {
            "cand_mean_depth": round(sum(cand_depths) / len(cand_depths), 2) if cand_depths else None,
            "base_mean_depth": round(sum(base_depths) / len(base_depths), 2) if base_depths else None,
            "cand_mean_move_time_s": round(sum(cand_move_times) / len(cand_move_times), 4) if cand_move_times else None,
            "base_mean_move_time_s": round(sum(base_move_times) / len(base_move_times), 4) if base_move_times else None,
            "cand_mean_nodes": round(sum(cand_nodes) / len(cand_nodes), 0) if cand_nodes else None,
            "base_mean_nodes": round(sum(base_nodes) / len(base_nodes), 0) if base_nodes else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Janus v0.34 Match")
    parser.add_argument("--json", type=str, default="analysis/v0.34/match/v034_match_500ms.json")
    parser.add_argument("--out", type=str, default="analysis/v0.34/match/v034_analysis_report.json")
    args = parser.parse_args()

    json_path = Path(args.json)
    out_path = Path(args.out)

    if not json_path.is_file():
        print(f"Error: match json not found at {json_path}")
        sys.exit(1)

    report = analyze_v034_data(json_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    rec = report["match_record"]
    p_info = report["pairs_analysis"]
    print("\n" + "=" * 60)
    print("JANUS v0.34 MATCH ANALYSIS REPORT")
    print("=" * 60)
    print(f"Games: {rec['total_games']} | Candidate: {rec['candidate_wins']}W-{rec['candidate_draws']}D-{rec['candidate_losses']}L ({rec['candidate_score_pct']}%)")
    print(f"Estimated Elo: {rec['estimated_elo']:+.1f} (SE: +/-{rec['elo_se']}, 95% CI: {rec['elo_95_ci']})")
    print(f"Pairs: {p_info['won_pairs']} won, {p_info['drawn_pairs']} drawn, {p_info['lost_pairs']} lost (Net: {p_info['won_pairs'] - p_info['lost_pairs']:+d})")
    print(f"Sign test p-value: {p_info['sign_test_p_value']}")
    print(f"Paired t-test: t = {p_info['paired_t_statistic']}, p = {p_info['paired_t_p_value_approx']}")
    print(f"Statistically significant (p < 0.05): {p_info['statistically_significant_at_05']}")
    print(f"Report saved to {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
