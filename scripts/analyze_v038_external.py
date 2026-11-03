"""Project Janus v0.38 - Statistical Analysis and Diagnostics Pipeline.

Performs rigorous pair-level statistical inference and time diagnostics across
the three external engine benchmarks:
1. Primary Benchmark: Janus Adaptive vs Stockfish 19 (Fischer 3000ms+100ms)
2. Historical Comparison Benchmark: Janus vs Stockfish 19 (Fixed Depth 3)
3. Calibrated Opponent Benchmark: Janus Adaptive vs Stockfish 19 (Elo 1320)

Computes:
- Paired Student's t-test (t-statistic, df, p-value, SE, paired 95% CI)
- 10,000-resample opening-pair bootstrap 95% CI (seed 42)
- Paired non-parametric exact binomial sign test on decisive pairs
- Elo point estimates and non-linearly mapped confidence bounds
- Anchored performance rating against calibrated 1320 baseline
- Move-level time management and completed search depth distributions
- Full JSON export for audit and report generation

Pure standard library implementation (no numpy/scipy dependencies).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]


def t_distribution_cdf(t_val: float, df: int) -> float:
    """Calculate Student's t-distribution cumulative distribution function using Simpson's rule."""
    if df <= 0:
        raise ValueError("Degrees of freedom must be positive")
    if t_val == 0.0:
        return 0.5

    def t_pdf(u: float) -> float:
        c = math.gamma((df + 1) / 2.0) / (math.sqrt(df * math.pi) * math.gamma(df / 2.0))
        return c * (1.0 + (u * u) / df) ** (-(df + 1) / 2.0)

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
    """Convert match score S in (0, 1) to Elo difference."""
    if score <= 0.0 or score >= 1.0:
        return None
    return round(-400.0 * math.log10((1.0 / score) - 1.0), 1)


def percentile_value(data: List[float], p: float) -> float:
    """Compute p-th percentile (0 <= p <= 100) using linear interpolation."""
    if not data:
        return 0.0
    s_data = sorted(data)
    if p <= 0:
        return s_data[0]
    if p >= 100:
        return s_data[-1]
    rank = (p / 100.0) * (len(s_data) - 1)
    low_idx = int(math.floor(rank))
    high_idx = int(math.ceil(rank))
    weight = rank - low_idx
    return (1.0 - weight) * s_data[low_idx] + weight * s_data[high_idx]


def exact_sign_test_p_value(k: int, n: int) -> float:
    """Two-sided exact binomial sign test p-value under H0: p = 0.5."""
    if n == 0:
        return 1.0
    min_k = min(k, n - k)
    cum_prob = 0.0
    for i in range(min_k + 1):
        cum_prob += math.comb(n, i) * (0.5 ** n)
    p_val = 2.0 * cum_prob
    return min(1.0, p_val)


def analyze_paired_games(games: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform pair-level statistical inference on a collection of games."""
    # Group by opening pair
    pairs: Dict[int, List[Dict[str, Any]]] = {}
    for g in games:
        p_id = g.get("pair") or g.get("opening_pair_id")
        if p_id is not None:
            pairs.setdefault(int(p_id), []).append(g)

    pair_stats: List[Dict[str, Any]] = []
    pair_scores: List[float] = []

    for p_id in sorted(pairs.keys()):
        g_list = pairs[p_id]
        if len(g_list) != 2:
            continue
        white_g = next((g for g in g_list if g["janus_color"] == "white"), None)
        black_g = next((g for g in g_list if g["janus_color"] == "black"), None)
        if not white_g or not black_g:
            continue

        w_pts = float(white_g["janus_points"])
        b_pts = float(black_g["janus_points"])
        pair_pts = w_pts + b_pts  # out of 2.0
        norm_score = pair_pts / 2.0  # in [0, 1]

        diff = w_pts + b_pts - 1.0  # net pair advantage (+1, +0.5, 0, -0.5, -1)

        pair_stats.append({
            "pair": p_id,
            "white_points": w_pts,
            "black_points": b_pts,
            "total_points": pair_pts,
            "normalized_score": norm_score,
            "net_difference": diff,
        })
        pair_scores.append(norm_score)

    n_pairs = len(pair_scores)
    n_games = n_pairs * 2

    janus_wins = sum(1 for g in games if g["janus_points"] == 1.0)
    janus_draws = sum(1 for g in games if g["janus_points"] == 0.5)
    janus_losses = sum(1 for g in games if g["janus_points"] == 0.0)
    total_pts = sum(g["janus_points"] for g in games)
    score_pct = (total_pts / len(games) * 100.0) if games else 0.0

    # Color breakdown
    white_games = [g for g in games if g["janus_color"] == "white"]
    black_games = [g for g in games if g["janus_color"] == "black"]

    white_w = sum(1 for g in white_games if g["janus_points"] == 1.0)
    white_d = sum(1 for g in white_games if g["janus_points"] == 0.5)
    white_l = sum(1 for g in white_games if g["janus_points"] == 0.0)
    white_score_pct = (sum(g["janus_points"] for g in white_games) / len(white_games) * 100.0) if white_games else 0.0

    black_w = sum(1 for g in black_games if g["janus_points"] == 1.0)
    black_d = sum(1 for g in black_games if g["janus_points"] == 0.5)
    black_l = sum(1 for g in black_games if g["janus_points"] == 0.0)
    black_score_pct = (sum(g["janus_points"] for g in black_games) / len(black_games) * 100.0) if black_games else 0.0

    # Paired Student's t-test
    mean_pair_score = statistics.mean(pair_scores) if pair_scores else 0.0
    stdev_pair = statistics.stdev(pair_scores) if n_pairs > 1 else 0.0
    se_pair = (stdev_pair / math.sqrt(n_pairs)) if n_pairs > 1 else 0.0
    df = n_pairs - 1

    t_stat = ((mean_pair_score - 0.5) / se_pair) if se_pair > 0 else 0.0
    p_val_t = 2.0 * (1.0 - t_distribution_cdf(abs(t_stat), df)) if df > 0 else 1.0
    t_crit = t_critical_value(0.975, df) if df > 0 else 1.96

    t_ci_low = max(0.0, mean_pair_score - t_crit * se_pair)
    t_ci_high = min(1.0, mean_pair_score + t_crit * se_pair)

    # Bootstrap 95% CI (10,000 resamples of opening pairs)
    random.seed(42)
    boot_means = []
    if pair_scores:
        for _ in range(10000):
            sample = [random.choice(pair_scores) for _ in range(n_pairs)]
            boot_means.append(statistics.mean(sample))
    boot_ci_low = percentile_value(boot_means, 2.5) if boot_means else 0.0
    boot_ci_high = percentile_value(boot_means, 97.5) if boot_means else 0.0

    # Sign test on decisive pairs (pair score != 0.5)
    decisive_pairs = [p for p in pair_scores if p != 0.5]
    pos_pairs = sum(1 for p in decisive_pairs if p > 0.5)
    neg_pairs = sum(1 for p in decisive_pairs if p < 0.5)
    sign_test_p = exact_sign_test_p_value(pos_pairs, len(decisive_pairs))

    # Elo difference
    elo_est = score_to_elo(mean_pair_score)
    elo_t_low = score_to_elo(t_ci_low) if t_ci_low > 0 else None
    elo_t_high = score_to_elo(t_ci_high) if t_ci_high < 1 else None
    elo_boot_low = score_to_elo(boot_ci_low) if boot_ci_low > 0 else None
    elo_boot_high = score_to_elo(boot_ci_high) if boot_ci_high < 1 else None

    return {
        "n_games": len(games),
        "n_pairs": n_pairs,
        "score": {
            "janus_wins": janus_wins,
            "draws": janus_draws,
            "losses": janus_losses,
            "total_points": total_pts,
            "score_pct": round(score_pct, 2),
            "mean_pair_score": round(mean_pair_score, 4),
        },
        "color_breakdown": {
            "white": {
                "games": len(white_games),
                "wins": white_w,
                "draws": white_d,
                "losses": white_l,
                "score_pct": round(white_score_pct, 2),
            },
            "black": {
                "games": len(black_games),
                "wins": black_w,
                "draws": black_d,
                "losses": black_l,
                "score_pct": round(black_score_pct, 2),
            },
        },
        "paired_t_test": {
            "df": df,
            "t_statistic": round(t_stat, 4),
            "p_value": p_val_t,
            "standard_error": round(se_pair, 4),
            "ci_95_t_interval": [round(t_ci_low, 4), round(t_ci_high, 4)],
            "ci_95_t_score_pct": [round(t_ci_low * 100.0, 2), round(t_ci_high * 100.0, 2)],
        },
        "pair_bootstrap_10k": {
            "ci_95_bootstrap": [round(boot_ci_low, 4), round(boot_ci_high, 4)],
            "ci_95_boot_score_pct": [round(boot_ci_low * 100.0, 2), round(boot_ci_high * 100.0, 2)],
        },
        "paired_sign_test": {
            "decisive_pairs": len(decisive_pairs),
            "positive_pairs": pos_pairs,
            "negative_pairs": neg_pairs,
            "two_tailed_p_value": round(sign_test_p, 6),
        },
        "elo": {
            "point_estimate": elo_est,
            "ci_95_t": [elo_t_low, elo_t_high],
            "ci_95_bootstrap": [elo_boot_low, elo_boot_high],
        },
    }


def analyze_move_telemetry(csv_path: Path) -> Dict[str, Any]:
    """Extract and analyze move-level metrics from match_moves.csv."""
    if not csv_path.exists():
        return {}

    moves: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            moves.append(row)

    if not moves:
        return {}

    janus_moves = [m for m in moves if m.get("is_janus") in (True, "True", "1") or "Janus" in m.get("player", "")]
    sf_moves = [m for m in moves if m.get("is_janus") in (False, "False", "0") or "Stockfish" in m.get("player", "")]

    def extract_stats(subset: List[Dict[str, Any]], key: str, is_float: bool = True) -> Dict[str, Any]:
        vals = []
        for m in subset:
            raw = m.get(key, "")
            if raw != "" and raw != "None":
                try:
                    vals.append(float(raw) if is_float else int(raw))
                except (ValueError, TypeError):
                    pass
        if not vals:
            return {"count": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0, "min": 0.0}
        return {
            "count": len(vals),
            "mean": round(statistics.mean(vals), 3),
            "median": round(percentile_value(vals, 50.0), 3),
            "p95": round(percentile_value(vals, 95.0), 3),
            "max": round(max(vals), 3),
            "min": round(min(vals), 3),
        }

    # Janus move time by phase
    opening_moves = [m for m in janus_moves if int(m.get("ply", 1)) <= 20]
    middlegame_moves = [m for m in janus_moves if 21 <= int(m.get("ply", 1)) <= 60]
    endgame_moves = [m for m in janus_moves if int(m.get("ply", 1)) > 60]

    return {
        "janus_move_count": len(janus_moves),
        "sf_move_count": len(sf_moves),
        "janus_time_ms": extract_stats(janus_moves, "actual_time_ms"),
        "janus_time_by_phase": {
            "opening_plies_1_20": extract_stats(opening_moves, "actual_time_ms"),
            "middlegame_plies_21_60": extract_stats(middlegame_moves, "actual_time_ms"),
            "endgame_plies_gt_60": extract_stats(endgame_moves, "actual_time_ms"),
        },
        "janus_depth": extract_stats(janus_moves, "depth", is_float=True),
        "janus_depth_by_phase": {
            "opening_plies_1_20": extract_stats(opening_moves, "depth", is_float=True),
            "middlegame_plies_21_60": extract_stats(middlegame_moves, "depth", is_float=True),
            "endgame_plies_gt_60": extract_stats(endgame_moves, "depth", is_float=True),
        },
        "sf_depth": extract_stats(sf_moves, "depth", is_float=True),
        "sf_time_ms": extract_stats(sf_moves, "actual_time_ms"),
        "clock_safety": {
            "min_janus_clock_remaining_ms": extract_stats(janus_moves, "clock_after_ms")["min"] if janus_moves else None,
            "zero_clock_violations": sum(1 for m in janus_moves if float(m.get("clock_after_ms", 1.0) or 1.0) <= 0.0),
        },
    }


def run_full_analysis(benchmark_dirs: Dict[str, Path], output_path: Path) -> Dict[str, Any]:
    """Execute analysis across all three benchmark directories."""
    results: Dict[str, Any] = {
        "milestone": "v0.38",
        "description": "Project Janus v0.38 External Engine Benchmark Statistical Analysis",
        "benchmarks": {},
    }

    for key, b_dir in benchmark_dirs.items():
        json_file = b_dir / "match_results.json"
        moves_csv = b_dir / "match_moves.csv"

        if not json_file.exists():
            print(f"Warning: {json_file} does not exist, skipping {key}")
            continue

        data = json.loads(json_file.read_text(encoding="utf-8"))
        valid_games = data.get("valid_games", [])
        paired_analysis = analyze_paired_games(valid_games)
        telemetry = analyze_move_telemetry(moves_csv)

        b_entry = {
            "mode": key,
            "metadata": data.get("metadata", {}),
            "match_summary": data.get("match_summary", {}),
            "paired_analysis": paired_analysis,
            "telemetry": telemetry,
        }

        # For calibrated elo, add calibrated rating estimate
        if key == "calibrated_elo":
            s_frac = paired_analysis["score"]["mean_pair_score"]
            sf_elo_anchor = 1320
            diff = score_to_elo(s_frac)
            perf_rating = (sf_elo_anchor + diff) if diff is not None else None
            b_entry["calibrated_performance"] = {
                "opponent_elo": sf_elo_anchor,
                "elo_difference": diff,
                "janus_performance_rating": round(perf_rating, 1) if perf_rating is not None else None,
            }

        # For historical depth 3, add comparison against v0.5 baseline
        if key == "historical_depth3":
            # Historical v0.5 result: 2W / 11D / 37L (7.5/50 = 15.0%)
            hist_score_pct = 15.0
            cur_score_pct = paired_analysis["score"]["score_pct"]
            b_entry["historical_comparison"] = {
                "v05_historical_score_pct": hist_score_pct,
                "v038_score_pct": cur_score_pct,
                "delta_score_pct": round(cur_score_pct - hist_score_pct, 2),
                "is_stronger_than_v05": cur_score_pct > hist_score_pct,
            }

        results["benchmarks"][key] = b_entry

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Statistical analysis successfully written to: {output_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze v0.38 match results.")
    parser.add_argument("--primary-dir", type=str, default="analysis/v0.38/primary_fischer")
    parser.add_argument("--depth3-dir", type=str, default="analysis/v0.38/historical_depth3")
    parser.add_argument("--calibrated-dir", type=str, default="analysis/v0.38/calibrated_elo")
    parser.add_argument("--output", type=str, default="analysis/v0.38/statistical_analysis.json")
    args = parser.parse_args()

    dirs = {
        "primary_fischer": ROOT / args.primary_dir,
        "historical_depth3": ROOT / args.depth3_dir,
        "calibrated_elo": ROOT / args.calibrated_dir,
    }
    run_full_analysis(dirs, ROOT / args.output)
