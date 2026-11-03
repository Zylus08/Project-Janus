"""Comprehensive Statistical Analysis and Diagnostics Collector for Project Janus v0.36.

Performs:
1. Primary endpoint evaluation: Candidate match score S = (W + 0.5D) / N
2. Primary paired statistical inference over complete opening pairs:
   - Mean paired score difference Delta_bar
   - Paired Student's t-test with df = 49 and exact two-sided p-value
   - Non-parametric pair bootstrap CI (B = 10,000, seed = 42)
   - Paired sign test on decisive opening pairs with explicit tie accounting
3. Elo conversion and nonlinear uncertainty propagation
4. Colour-separated performance (White vs Black)
5. Comprehensive move-level time-management diagnostics:
   - Actual duration and target allocation percentiles
   - Remaining clock distributions and minimum clock drawdowns
   - Emergency allocation frequencies
   - Deadline stops and fallback move frequencies
   - Maximum deadline overshoot
   - Phase-dependent timing breakdown (Opening, Middlegame, Endgame)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def t_distribution_cdf(t_val: float, df: int) -> float:
    """Calculate Student's t-distribution cumulative distribution function."""
    if df <= 0:
        raise ValueError("Degrees of freedom must be positive")
    # For df=49, use regularized incomplete beta function approximation or continued fraction
    x = df / (df + t_val * t_val)
    # Using incomplete beta function via math.gamma / integration
    # For exactness with df=49, let's use the numerical integration / Simpson's rule on t-density
    if t_val == 0.0:
        return 0.5

    def t_pdf(u: float) -> float:
        c = math.gamma((df + 1) / 2.0) / (math.sqrt(df * math.pi) * math.gamma(df / 2.0))
        return c * (1.0 + (u * u) / df) ** (-(df + 1) / 2.0)

    # Integrate from 0 to abs(t_val)
    n_steps = 1000
    b = abs(t_val)
    h = b / n_steps
    integral = t_pdf(0.0) + t_pdf(b)
    for i in range(1, n_steps):
        u = i * h
        weight = 4.0 if (i % 2 == 1) else 2.0
        integral += weight * t_pdf(u)
    integral *= (h / 3.0)

    if t_val > 0:
        return min(1.0, 0.5 + integral)
    else:
        return max(0.0, 0.5 - integral)


def t_critical_value(p: float, df: int) -> float:
    """Inverse Student's t CDF approximation via bisection."""
    low = 0.0
    high = 10.0
    while high - low > 1e-6:
        mid = (low + high) / 2.0
        if t_distribution_cdf(mid, df) < p:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def score_to_elo(score: float) -> Optional[float]:
    """Convert score percentage (0 to 1) to Elo difference."""
    if score <= 0.0 or score >= 1.0:
        return None
    return -400.0 * math.log10((1.0 - score) / score)


def run_statistical_analysis(
    match_json_path: Path,
    moves_csv_path: Path,
    output_dir: Path,
    bootstrap_seed: int = 42,
    bootstrap_samples: int = 10000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)

    match_data = json.loads(match_json_path.read_text(encoding="utf-8"))
    valid_games = match_data["valid_games"]
    total_games = len(valid_games)

    if total_games == 0:
        raise ValueError("Match dataset contains 0 valid games")

    # 1. Game-level aggregation
    cand_wins = sum(1 for g in valid_games if (g["result"] == "1-0" and g["candidate_color"] == "white") or (g["result"] == "0-1" and g["candidate_color"] == "black"))
    cand_draws = sum(1 for g in valid_games if g["result"] == "1/2-1/2")
    cand_losses = total_games - cand_wins - cand_draws
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_games) * 100.0

    # Colour breakdown
    white_games = [g for g in valid_games if g["candidate_color"] == "white"]
    black_games = [g for g in valid_games if g["candidate_color"] == "black"]

    w_wins = sum(1 for g in white_games if g["result"] == "1-0")
    w_draws = sum(1 for g in white_games if g["result"] == "1/2-1/2")
    w_losses = len(white_games) - w_wins - w_draws
    w_score = w_wins + 0.5 * w_draws
    w_pct = (w_score / len(white_games) * 100.0) if white_games else 0.0

    b_wins = sum(1 for g in black_games if g["result"] == "0-1")
    b_draws = sum(1 for g in black_games if g["result"] == "1/2-1/2")
    b_losses = len(black_games) - b_wins - b_draws
    b_score = b_wins + 0.5 * b_draws
    b_pct = (b_score / len(black_games) * 100.0) if black_games else 0.0

    # 2. Opening-pair level aggregation
    pairs_dict: dict[int, list[dict[str, Any]]] = {}
    for g in valid_games:
        pairs_dict.setdefault(g["pair"], []).append(g)

    pair_deltas: list[float] = []
    pair_scores: list[float] = []
    pairs_won = 0
    pairs_drawn = 0
    pairs_lost = 0

    for p_num in sorted(pairs_dict.keys()):
        p_games = pairs_dict[p_num]
        if len(p_games) != 2:
            continue
        p_cand_pts = 0.0
        for g in p_games:
            res = g["result"]
            c = g["candidate_color"]
            if res == "1/2-1/2":
                p_cand_pts += 0.5
            elif (res == "1-0" and c == "white") or (res == "0-1" and c == "black"):
                p_cand_pts += 1.0
        pair_avg = p_cand_pts / 2.0
        pair_scores.append(pair_avg)
        delta_i = pair_avg - 0.5
        pair_deltas.append(delta_i)

        if pair_avg > 0.5:
            pairs_won += 1
        elif pair_avg < 0.5:
            pairs_lost += 1
        else:
            pairs_drawn += 1

    M = len(pair_deltas)
    if M == 0:
        raise ValueError("Zero complete opening pairs found")

    mean_delta = statistics.mean(pair_deltas)
    std_delta = statistics.stdev(pair_deltas) if M > 1 else 0.0
    se_delta = std_delta / math.sqrt(M) if M > 0 else 0.0

    # Student's t-test (df = M - 1)
    df = M - 1
    t_stat = (mean_delta / se_delta) if se_delta > 0 else 0.0
    p_val_one_sided = 1.0 - t_distribution_cdf(abs(t_stat), df)
    p_val_two_sided = min(1.0, 2.0 * p_val_one_sided)

    t_crit = t_critical_value(0.975, df)
    t_ci_delta_low = mean_delta - t_crit * se_delta
    t_ci_delta_high = mean_delta + t_crit * se_delta

    t_ci_score_low = 0.5 + t_ci_delta_low
    t_ci_score_high = 0.5 + t_ci_delta_high

    # Paired non-parametric bootstrap (resampling opening pairs)
    rng = random.Random(bootstrap_seed)
    boot_means = []
    for _ in range(bootstrap_samples):
        resampled_deltas = [rng.choice(pair_deltas) for _ in range(M)]
        boot_means.append(statistics.mean(resampled_deltas))
    boot_means.sort()

    boot_delta_low = boot_means[int(0.025 * bootstrap_samples)]
    boot_delta_high = boot_means[int(0.975 * bootstrap_samples)]
    boot_score_low = 0.5 + boot_delta_low
    boot_score_high = 0.5 + boot_delta_high

    # Paired sign test
    decisive_pairs = pairs_won + pairs_lost
    if decisive_pairs > 0:
        k = min(pairs_won, pairs_lost)
        sign_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        sign_p = min(1.0, sign_p)
    else:
        sign_p = 1.0

    # Elo conversions
    elo_point = score_to_elo(cand_score / total_games)
    elo_t_ci = [
        round(score_to_elo(max(0.01, min(0.99, t_ci_score_low))), 1) if t_ci_score_low > 0 and t_ci_score_low < 1 else None,
        round(score_to_elo(max(0.01, min(0.99, t_ci_score_high))), 1) if t_ci_score_high > 0 and t_ci_score_high < 1 else None,
    ]
    elo_boot_ci = [
        round(score_to_elo(max(0.01, min(0.99, boot_score_low))), 1) if boot_score_low > 0 and boot_score_low < 1 else None,
        round(score_to_elo(max(0.01, min(0.99, boot_score_high))), 1) if boot_score_high > 0 and boot_score_high < 1 else None,
    ]

    stat_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_valid_games": total_games,
        "complete_opening_pairs": M,
        "candidate": {
            "name": match_data["metadata"]["candidate_name"],
            "wins": cand_wins,
            "draws": cand_draws,
            "losses": cand_losses,
            "score": cand_score,
            "score_pct": round(cand_score_pct, 2),
            "estimated_elo": round(elo_point, 1) if elo_point is not None else None,
            "elo_t_ci_95": elo_t_ci,
            "elo_bootstrap_ci_95": elo_boot_ci,
        },
        "colour_performance": {
            "white": {
                "games": len(white_games),
                "wins": w_wins,
                "draws": w_draws,
                "losses": w_losses,
                "score": w_score,
                "score_pct": round(w_pct, 2),
            },
            "black": {
                "games": len(black_games),
                "wins": b_wins,
                "draws": b_draws,
                "losses": b_losses,
                "score": b_score,
                "score_pct": round(b_pct, 2),
            },
        },
        "paired_inference": {
            "pairs_count": M,
            "pairs_won": pairs_won,
            "pairs_drawn": pairs_drawn,
            "pairs_lost": pairs_lost,
            "decisive_pairs": decisive_pairs,
            "mean_paired_score": round(0.5 + mean_delta, 4),
            "mean_paired_delta": round(mean_delta, 4),
            "std_paired_delta": round(std_delta, 4),
            "se_paired_delta": round(se_delta, 4),
            "t_statistic": round(t_stat, 4),
            "t_test_df": df,
            "t_test_two_sided_p_value": round(p_val_two_sided, 5),
            "t_ci_95_delta": [round(t_ci_delta_low, 4), round(t_ci_delta_high, 4)],
            "t_ci_95_score": [round(t_ci_score_low, 4), round(t_ci_score_high, 4)],
            "bootstrap_samples": bootstrap_samples,
            "bootstrap_seed": bootstrap_seed,
            "bootstrap_ci_95_delta": [round(boot_delta_low, 4), round(boot_delta_high, 4)],
            "bootstrap_ci_95_score": [round(boot_score_low, 4), round(boot_score_high, 4)],
            "paired_sign_test_p_value": round(sign_p, 5),
        },
    }

    # 3. Move-level time management diagnostics
    move_rows = []
    if moves_csv_path.is_file():
        with open(moves_csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                move_rows.append(row)

    cand_moves = [r for r in move_rows if r["policy"] == "adaptive"]
    base_moves = [r for r in move_rows if r["policy"] == "reference"]

    def analyze_moves(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {}
        durations = [float(r["actual_time_ms"]) for r in rows]
        targets = [float(r["target_alloc_ms"]) for r in rows]
        overshoots = [float(r["overshoot_ms"]) for r in rows]
        clocks_after = [float(r["clock_after_ms"]) for r in rows]
        depths = [int(r["depth"]) for r in rows]
        nodes = [int(r["nodes"]) for r in rows]

        ratios = [(d / t) for d, t in zip(durations, targets) if t > 0]
        emergencies = sum(1 for r in rows if r["is_emergency"] in ("True", "true", True))
        deadlines = sum(1 for r in rows if r["is_deadline_stop"] in ("True", "true", True))
        fallbacks = sum(1 for r in rows if r["fallback_move_required"] in ("True", "true", True))

        durations.sort()
        targets.sort()
        clocks_after.sort()

        def pct(lst: list[float], p: float) -> float:
            idx = int(p * (len(lst) - 1))
            return round(lst[idx], 1)

        return {
            "move_count": len(rows),
            "actual_time_ms": {
                "median": pct(durations, 0.50),
                "p25": pct(durations, 0.25),
                "p75": pct(durations, 0.75),
                "p95": pct(durations, 0.95),
                "p99": pct(durations, 0.99),
                "max": round(max(durations), 1),
            },
            "target_alloc_ms": {
                "median": pct(targets, 0.50),
                "p25": pct(targets, 0.25),
                "p75": pct(targets, 0.75),
                "p95": pct(targets, 0.95),
                "p99": pct(targets, 0.99),
            },
            "actual_to_target_ratio": {
                "median": round(statistics.median(ratios), 3) if ratios else 0.0,
                "mean": round(statistics.mean(ratios), 3) if ratios else 0.0,
            },
            "remaining_clock_ms": {
                "median": pct(clocks_after, 0.50),
                "p25": pct(clocks_after, 0.25),
                "p75": pct(clocks_after, 0.75),
                "min": round(min(clocks_after), 1),
            },
            "overshoot_ms": {
                "median": round(statistics.median(overshoots), 1),
                "mean": round(statistics.mean(overshoots), 1),
                "max": round(max(overshoots), 1),
            },
            "emergency_allocations_count": emergencies,
            "deadline_stops_count": deadlines,
            "fallback_moves_count": fallbacks,
            "median_depth": round(statistics.median(depths), 1),
            "mean_depth": round(statistics.mean(depths), 2),
            "mean_nodes": int(statistics.mean(nodes)),
        }

    # Phase breakdown
    def analyze_by_phase(rows: list[dict[str, Any]]) -> dict[str, Any]:
        phases = {
            "opening (plies 1-20)": [r for r in rows if int(r["ply"]) <= 20],
            "middlegame (plies 21-60)": [r for r in rows if 20 < int(r["ply"]) <= 60],
            "endgame (plies > 60)": [r for r in rows if int(r["ply"]) > 60],
        }
        res = {}
        for p_label, p_rows in phases.items():
            if not p_rows:
                continue
            durs = [float(r["actual_time_ms"]) for r in p_rows]
            deps = [int(r["depth"]) for r in p_rows]
            nds = [int(r["nodes"]) for r in p_rows]
            clks = [float(r["clock_after_ms"]) for r in p_rows]
            res[p_label] = {
                "move_count": len(p_rows),
                "mean_duration_ms": round(statistics.mean(durs), 1),
                "mean_depth": round(statistics.mean(deps), 2),
                "mean_nodes": int(statistics.mean(nds)),
                "mean_clock_after_ms": round(statistics.mean(clks), 1),
            }
        return res

    diag_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_moves_analyzed": len(move_rows),
        "adaptive_policy": analyze_moves(cand_moves),
        "reference_policy": analyze_moves(base_moves),
        "phase_breakdown": {
            "adaptive": analyze_by_phase(cand_moves),
            "reference": analyze_by_phase(base_moves),
        },
    }

    stat_file = output_dir / "statistical_analysis.json"
    diag_file = output_dir / "diagnostics_summary.json"

    stat_file.write_text(json.dumps(stat_report, indent=2), encoding="utf-8")
    diag_file.write_text(json.dumps(diag_report, indent=2), encoding="utf-8")

    print(f"Statistical analysis saved to {stat_file}")
    print(f"Diagnostics summary saved to {diag_file}")

    return stat_report, diag_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze v0.36 Match Results")
    parser.add_argument("--match-json", type=Path, default=ROOT / "analysis" / "v0.36" / "match" / "fischer_100_match.json")
    parser.add_argument("--moves-csv", type=Path, default=ROOT / "analysis" / "v0.36" / "match" / "fischer_100_match_moves.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "analysis" / "v0.36")
    args = parser.parse_args()

    run_statistical_analysis(args.match_json, args.moves_csv, args.output_dir)
