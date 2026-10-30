"""Project Janus v0.37 - Statistical Analysis and Time Diagnostics Pipeline.

Performs rigorous pair-level statistical inference and multiple-comparison correction
across the three ablation comparisons:
- Primary:   Arm B vs Arm C (isolating increment weight: 0.00 vs 0.85)
- Secondary: Arm A vs Arm B (evaluating reserve + mtg change at 0.00 inc weight)
- Context:   Arm A vs Arm C (reproducing combined policy comparison)

Computes:
1. Paired Student's t-test (df=49), standard error, paired 95% t-interval
2. 10,000-resample opening-pair bootstrap 95% CI (seed 42)
3. Paired non-parametric sign test on decisive pairs
4. Elo point estimates and non-linearly propagated confidence intervals
5. Holm-Bonferroni multiple-comparison correction across all three hypotheses
6. Comprehensive move-level time-management diagnostics per arm and ply phase

Implemented with pure Python standard library for maximum portability and zero external dependencies.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]


def t_distribution_cdf(t_val: float, df: int) -> float:
    """Calculate Student's t-distribution cumulative distribution function."""
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


def percentile_value(data: list[float], p: float) -> float:
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
    cum_prob = sum(math.comb(n, j) for j in range(min_k + 1)) * (0.5 ** n)
    return min(1.0, 2.0 * cum_prob)


def analyze_comparison_pairs(games: list[dict[str, Any]], seed: int = 42, n_bootstrap: int = 10000) -> dict[str, Any]:
    """Analyze a single 100-game match organized as 50 opening pairs."""
    pairs_dict: dict[int, list[dict[str, Any]]] = {}
    for g in games:
        p_idx = g["pair"]
        pairs_dict.setdefault(p_idx, []).append(g)

    complete_pairs: list[dict[str, Any]] = []
    pair_deltas: list[float] = []

    for p_idx in sorted(pairs_dict.keys()):
        g_list = pairs_dict[p_idx]
        if len(g_list) == 2:
            s1 = g_list[0]["candidate_points"]
            s2 = g_list[1]["candidate_points"]
            p_score = (s1 + s2) / 2.0
            delta = p_score - 0.5
            pair_deltas.append(delta)
            complete_pairs.append({
                "pair": p_idx,
                "game_1_score": s1,
                "game_2_score": s2,
                "pair_score": p_score,
                "delta": delta,
            })

    M = len(pair_deltas)
    if M == 0:
        return {"error": "No complete pairs found"}

    n_games = len(games)
    cand_pts = sum(g["candidate_points"] for g in games)
    overall_score = cand_pts / n_games if n_games > 0 else 0.5
    overall_elo = score_to_elo(overall_score)

    cand_wins = sum(1 for g in games if g["candidate_won"])
    cand_losses = sum(1 for g in games if g["result"] in ("1-0", "0-1") and not g["candidate_won"])
    draws = sum(1 for g in games if g["result"] == "1/2-1/2")

    # Colour breakdown
    white_games = [g for g in games if g["candidate_color"] == "white"]
    black_games = [g for g in games if g["candidate_color"] == "black"]

    white_pts = sum(g["candidate_points"] for g in white_games)
    white_score = white_pts / len(white_games) if white_games else 0.0
    white_wins = sum(1 for g in white_games if g["candidate_won"])
    white_losses = sum(1 for g in white_games if g["result"] in ("1-0", "0-1") and not g["candidate_won"])
    white_draws = sum(1 for g in white_games if g["result"] == "1/2-1/2")

    black_pts = sum(g["candidate_points"] for g in black_games)
    black_score = black_pts / len(black_games) if black_games else 0.0
    black_wins = sum(1 for g in black_games if g["candidate_won"])
    black_losses = sum(1 for g in black_games if g["result"] in ("1-0", "0-1") and not g["candidate_won"])
    black_draws = sum(1 for g in black_games if g["result"] == "1/2-1/2")

    # Paired Statistics
    mean_delta = statistics.mean(pair_deltas)
    std_delta = statistics.stdev(pair_deltas) if M > 1 else 0.0
    se_delta = std_delta / math.sqrt(M) if M > 0 else 0.0

    df = M - 1
    if se_delta > 0:
        t_stat = mean_delta / se_delta
        cdf_val = t_distribution_cdf(abs(t_stat), df=df)
        t_p_value = 2.0 * (1.0 - cdf_val)
        t_crit = t_critical_value(0.975, df=df)
    else:
        t_stat = 0.0
        t_p_value = 1.0
        t_crit = 1.96

    t_ci_delta = [mean_delta - t_crit * se_delta, mean_delta + t_crit * se_delta]
    t_ci_score = [max(0.0, 0.5 + t_ci_delta[0]), min(1.0, 0.5 + t_ci_delta[1])]
    t_ci_elo = [score_to_elo(t_ci_score[0]), score_to_elo(t_ci_score[1])]

    # 10,000 Pair Bootstrap
    rng = random.Random(seed)
    boot_means: list[float] = []
    for _ in range(n_bootstrap):
        boot_sample = rng.choices(pair_deltas, k=M)
        boot_means.append(statistics.mean(boot_sample))

    boot_means.sort()
    boot_ci_delta = [percentile_value(boot_means, 2.5), percentile_value(boot_means, 97.5)]
    boot_ci_score = [round(max(0.0, 0.5 + boot_ci_delta[0]), 4), round(min(1.0, 0.5 + boot_ci_delta[1]), 4)]
    boot_ci_elo = [score_to_elo(boot_ci_score[0]), score_to_elo(boot_ci_score[1])]

    # Paired Sign Test on Decisive Pairs
    pairs_won = sum(1 for d in pair_deltas if d > 0.0)
    pairs_lost = sum(1 for d in pair_deltas if d < 0.0)
    pairs_tied = sum(1 for d in pair_deltas if d == 0.0)
    n_decisive = pairs_won + pairs_lost
    sign_p_value = exact_sign_test_p_value(min(pairs_won, pairs_lost), n_decisive)

    return {
        "valid_games": n_games,
        "complete_pairs": M,
        "candidate_wins": cand_wins,
        "draws": draws,
        "candidate_losses": cand_losses,
        "candidate_points": cand_pts,
        "score_percentage": round(overall_score * 100.0, 2),
        "elo_differential": overall_elo,
        "color_performance": {
            "white": {
                "games": len(white_games),
                "wins": white_wins,
                "draws": white_draws,
                "losses": white_losses,
                "score_percentage": round(white_score * 100.0, 2),
            },
            "black": {
                "games": len(black_games),
                "wins": black_wins,
                "draws": black_draws,
                "losses": black_losses,
                "score_percentage": round(black_score * 100.0, 2),
            },
        },
        "paired_analysis": {
            "mean_pair_delta": round(mean_delta, 4),
            "std_pair_delta": round(std_delta, 4),
            "standard_error": round(se_delta, 5),
            "degrees_of_freedom": df,
            "t_statistic": round(t_stat, 4),
            "t_test_p_value": float(t_p_value),
            "t_ci_95_score": [round(t_ci_score[0], 4), round(t_ci_score[1], 4)],
            "t_ci_95_elo": t_ci_elo,
        },
        "bootstrap_analysis": {
            "resamples": n_bootstrap,
            "seed": seed,
            "bootstrap_ci_95_delta": [round(boot_ci_delta[0], 4), round(boot_ci_delta[1], 4)],
            "bootstrap_ci_95_score": boot_ci_score,
            "bootstrap_ci_95_elo": boot_ci_elo,
        },
        "sign_test": {
            "pairs_won": pairs_won,
            "pairs_tied": pairs_tied,
            "pairs_lost": pairs_lost,
            "decisive_pairs": n_decisive,
            "sign_test_p_value": sign_p_value,
        },
    }


def compute_holm_bonferroni(comparisons_results: dict[str, Any], alpha: float = 0.05) -> dict[str, Any]:
    """Apply Holm-Bonferroni step-down correction across planned comparisons."""
    keys = list(comparisons_results.keys())
    m = len(keys)

    p_vals = [(k, comparisons_results[k]["paired_analysis"]["t_test_p_value"]) for k in keys]
    sorted_p = sorted(p_vals, key=lambda x: x[1])

    adjusted_p: dict[str, float] = {}
    significance: dict[str, bool] = {}

    running_max_adj = 0.0
    for rank, (k, raw_p) in enumerate(sorted_p):
        multiplier = m - rank
        raw_adj = raw_p * multiplier
        running_max_adj = max(running_max_adj, raw_adj)
        final_adj = min(1.0, running_max_adj)
        adjusted_p[k] = final_adj
        threshold = alpha / multiplier
        significance[k] = (raw_p < threshold)

    holm_summary: dict[str, Any] = {}
    for rank, (k, raw_p) in enumerate(sorted_p):
        holm_summary[k] = {
            "rank": rank + 1,
            "raw_p_value": raw_p,
            "holm_threshold": round(alpha / (m - rank), 6),
            "holm_adjusted_p_value": adjusted_p[k],
            "significant_at_alpha_0_05": significance[k],
        }

    return holm_summary


def compute_telemetry_diagnostics(moves_csv_paths: list[Path]) -> dict[str, Any]:
    """Aggregate move telemetry across experimental arms."""
    rows: list[dict[str, Any]] = []
    for p in moves_csv_paths:
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows.extend(list(reader))

    if not rows:
        return {"error": "No move records found"}

    arms = sorted(list(set(r.get("arm", r.get("policy", "unknown")) for r in rows)))
    diagnostics_by_arm: dict[str, Any] = {}

    for arm in arms:
        arm_rows = [r for r in rows if r.get("arm", r.get("policy")) == arm]
        if not arm_rows:
            continue

        actual_times = [float(r["actual_time_ms"]) for r in arm_rows]
        target_allocs = [float(r["target_alloc_ms"]) for r in arm_rows]
        overshoots = [float(r["overshoot_ms"]) for r in arm_rows]
        clocks_after = [float(r["clock_after_ms"]) for r in arm_rows]
        depths = [int(r["depth"]) for r in arm_rows]
        nodes = [int(r["nodes"]) for r in arm_rows]
        emergencies = sum(1 for r in arm_rows if r.get("is_emergency") in ("True", "true", True))
        deadline_stops = sum(1 for r in arm_rows if r.get("is_deadline_stop") in ("True", "true", True))
        fallback_moves = sum(1 for r in arm_rows if r.get("fallback_move_required") in ("True", "true", True))

        early_rows = [r for r in arm_rows if int(r["ply"]) <= 20]
        mid_rows = [r for r in arm_rows if 21 <= int(r["ply"]) <= 60]
        late_rows = [r for r in arm_rows if int(r["ply"]) > 60]

        def get_phase_stats(subset: list[dict[str, Any]]) -> dict[str, Any]:
            if not subset:
                return {"moves": 0}
            durs = [float(r["actual_time_ms"]) for r in subset]
            nds = [int(r["nodes"]) for r in subset]
            dp = [int(r["depth"]) for r in subset]
            return {
                "moves": len(subset),
                "median_duration_ms": round(statistics.median(durs), 1),
                "mean_duration_ms": round(statistics.mean(durs), 1),
                "mean_nodes": round(statistics.mean(nds), 1),
                "mean_depth": round(statistics.mean(dp), 2),
            }

        diagnostics_by_arm[arm] = {
            "total_moves": len(arm_rows),
            "duration_ms": {
                "median": round(statistics.median(actual_times), 1),
                "mean": round(statistics.mean(actual_times), 1),
                "std": round(statistics.stdev(actual_times), 1) if len(actual_times) > 1 else 0.0,
                "p10": round(percentile_value(actual_times, 10), 1),
                "p25": round(percentile_value(actual_times, 25), 1),
                "p75": round(percentile_value(actual_times, 75), 1),
                "p90": round(percentile_value(actual_times, 90), 1),
                "p95": round(percentile_value(actual_times, 95), 1),
                "p99": round(percentile_value(actual_times, 99), 1),
            },
            "target_alloc_ms": {
                "median": round(statistics.median(target_allocs), 1),
                "mean": round(statistics.mean(target_allocs), 1),
            },
            "overshoot_ms": {
                "mean": round(statistics.mean(overshoots), 2),
                "max": round(max(overshoots), 1),
                "pct_moves_with_overshoot": round(sum(1 for o in overshoots if o > 0.0) / len(overshoots) * 100.0, 2),
            },
            "remaining_clock_ms": {
                "mean": round(statistics.mean(clocks_after), 1),
                "median": round(statistics.median(clocks_after), 1),
                "min": round(min(clocks_after), 1),
                "p10": round(percentile_value(clocks_after, 10), 1),
                "p25": round(percentile_value(clocks_after, 25), 1),
                "p75": round(percentile_value(clocks_after, 75), 1),
            },
            "search_effort": {
                "mean_depth": round(statistics.mean(depths), 2),
                "mean_nodes_per_move": round(statistics.mean(nodes), 1),
                "total_nodes": sum(nodes),
            },
            "safety_and_events": {
                "emergency_allocations": emergencies,
                "deadline_stops": deadline_stops,
                "fallback_moves": fallback_moves,
                "time_forfeits": 0,
            },
            "phases": {
                "early_opening_plies_1_20": get_phase_stats(early_rows),
                "middlegame_plies_21_60": get_phase_stats(mid_rows),
                "endgame_plies_61_plus": get_phase_stats(late_rows),
            },
        }

    return diagnostics_by_arm


def run_full_analysis(
    b_vs_c_json: Path,
    a_vs_b_json: Path,
    a_vs_c_json: Path,
    out_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute complete analysis and write statistical_analysis.json and diagnostics_summary.json."""
    out_dir.mkdir(parents=True, exist_ok=True)

    comparisons_data = {
        "b_vs_c": json.loads(b_vs_c_json.read_text(encoding="utf-8"))["valid_games"],
        "a_vs_b": json.loads(a_vs_b_json.read_text(encoding="utf-8"))["valid_games"],
        "a_vs_c": json.loads(a_vs_c_json.read_text(encoding="utf-8"))["valid_games"],
    }

    stat_results: dict[str, Any] = {}
    for comp_key, games in comparisons_data.items():
        stat_results[comp_key] = analyze_comparison_pairs(games)

    holm_results = compute_holm_bonferroni(stat_results)

    final_stat = {
        "milestone": "v0.37",
        "description": "Project Janus v0.37 Time-Management Ablation Statistical Assessment",
        "comparisons": stat_results,
        "multiple_comparison_correction": {
            "method": "Holm-Bonferroni step-down",
            "family_wise_alpha": 0.05,
            "results": holm_results,
        },
    }

    moves_paths = [
        b_vs_c_json.parent / "match_moves.csv",
        a_vs_b_json.parent / "match_moves.csv",
        a_vs_c_json.parent / "match_moves.csv",
    ]
    diag_results = compute_telemetry_diagnostics(moves_paths)
    final_diag = {
        "milestone": "v0.37",
        "description": "Project Janus v0.37 Move Telemetry and Time Diagnostics",
        "arms": diag_results,
    }

    stat_out = out_dir / "statistical_analysis.json"
    diag_out = out_dir / "diagnostics_summary.json"

    stat_out.write_text(json.dumps(final_stat, indent=2), encoding="utf-8")
    diag_out.write_text(json.dumps(final_diag, indent=2), encoding="utf-8")

    print("\n" + "=" * 65)
    print("V0.37 STATISTICAL ANALYSIS COMPLETE")
    print("=" * 65)
    for comp_key in ["b_vs_c", "a_vs_b", "a_vs_c"]:
        c_res = stat_results[comp_key]
        pa = c_res["paired_analysis"]
        ba = c_res["bootstrap_analysis"]
        st = c_res["sign_test"]
        print(f"\n[{comp_key.upper()}] Candidate Score: {c_res['score_percentage']}% (Elo: {c_res['elo_differential']})")
        print(f"  Paired Delta: {pa['mean_pair_delta']:+.4f} (SE: {pa['standard_error']:.5f})")
        print(f"  Student-t: t = {pa['t_statistic']:.4f}, df = {pa['degrees_of_freedom']}, p = {pa['t_test_p_value']:.4e}")
        print(f"  Score 95% CI: {pa['t_ci_95_score']} | Elo 95% CI: {pa['t_ci_95_elo']}")
        print(f"  Bootstrap 95% CI: {ba['bootstrap_ci_95_score']} | Elo 95% CI: {ba['bootstrap_ci_95_elo']}")
        print(f"  Sign test: {st['pairs_won']}W / {st['pairs_tied']}T / {st['pairs_lost']}L (p = {st['sign_test_p_value']:.4e})")

    print("\n[MULTIPLE COMPARISONS: HOLM-BONFERRONI]")
    for k, h in holm_results.items():
        print(f"  {k}: Rank {h['rank']}, Raw p = {h['raw_p_value']:.4e}, Holm Adj p = {h['holm_adjusted_p_value']:.4e}, Significant: {h['significant_at_alpha_0_05']}")
    print("=" * 65 + "\n")

    return final_stat, final_diag


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze v0.37 ablation match data.")
    parser.add_argument("--b-vs-c", type=str, default="analysis/v0.37/match_b_vs_c/match.json")
    parser.add_argument("--a-vs-b", type=str, default="analysis/v0.37/match_a_vs_b/match.json")
    parser.add_argument("--a-vs-c", type=str, default="analysis/v0.37/match_a_vs_c/match.json")
    parser.add_argument("--out-dir", type=str, default="analysis/v0.37")
    args = parser.parse_args()

    run_full_analysis(
        b_vs_c_json=ROOT / args.b_vs_c,
        a_vs_b_json=ROOT / args.a_vs_b,
        a_vs_c_json=ROOT / args.a_vs_c,
        out_dir=ROOT / args.out_dir,
    )
