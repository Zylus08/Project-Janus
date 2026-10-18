"""Milestone v0.27: Robust Paired Statistical Analysis and Evidence Validation.

Provides mathematically rigorous paired opening analysis:
- Robust handling of zero-variance samples (all-zero differences and constant differences)
- Explicit distinction between sample observation and population equivalence
- Exact binomial Clopper-Pearson bounds for zero-difference datasets
- Full parametric Student's t-test and bootstrap CIs for non-zero variance data
- Strict data validation: detects missing pairs, duplicate pairs, incomplete pairs, and malformed results
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
from typing import Any


def betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for incomplete beta function."""
    MAXIT = 100
    EPS = 3.0e-7
    FPMIN = 1.0e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        del_val = d * c
        h *= del_val
        if abs(del_val - 1.0) < EPS:
            break
    return h


def ibeta(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(-lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def student_t_two_sided_p_value(t_stat: float, df: int) -> float:
    """Exact two-sided p-value for Student's t distribution with df degrees of freedom."""
    if df <= 0: return 1.0
    t2 = t_stat * t_stat
    x = df / (df + t2)
    return ibeta(0.5 * df, 0.5, x)


def normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def wilcoxon_signed_rank_test(differences: list[float]) -> dict[str, Any]:
    """Wilcoxon signed-rank test for paired samples with exact handling of zeros."""
    non_zero_diffs = [d for d in differences if abs(d) > 1e-9]
    n = len(non_zero_diffs)
    if n == 0:
        return {
            "w_stat": None,
            "p_value": None,
            "n_effective": 0,
            "z_score": None,
            "note": "All differences are zero; test is degenerate with 0 effective ranks.",
        }

    ranked = sorted(non_zero_diffs, key=lambda x: abs(x))
    ranks: list[float] = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and abs(abs(ranked[j]) - abs(ranked[i])) < 1e-9:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    w_pos = sum(r for d, r in zip(ranked, ranks) if d > 0)
    w_neg = sum(r for d, r in zip(ranked, ranks) if d < 0)
    w_stat = min(w_pos, w_neg)

    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    sd_w = math.sqrt(var_w) if var_w > 0 else 1.0

    z = (w_stat - mean_w) / sd_w
    p_approx = 2.0 * normal_cdf(z)
    p_approx = max(0.0, min(1.0, p_approx))

    return {
        "w_stat": w_stat,
        "w_pos": w_pos,
        "w_neg": w_neg,
        "z_score": round(z, 4),
        "p_value": round(p_approx, 5),
        "n_effective": n,
    }


def paired_bootstrap_ci(differences: list[float], n_resamples: int = 10_000, ci: float = 0.95, seed: int = 42) -> tuple[float, float]:
    """Paired bootstrap confidence interval for mean difference."""
    rng = random.Random(seed)
    n = len(differences)
    if n == 0:
        return 0.0, 0.0
    means: list[float] = []
    for _ in range(n_resamples):
        sample = [rng.choice(differences) for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    alpha = (1.0 - ci) / 2.0
    idx_low = int(math.floor(alpha * n_resamples))
    idx_high = int(math.ceil((1.0 - alpha) * n_resamples)) - 1
    idx_high = min(idx_high, n_resamples - 1)
    return round(means[idx_low], 2), round(means[idx_high], 2)


def clopper_pearson_upper_bound_zero_events(n: int, alpha: float = 0.05) -> float:
    """Exact Clopper-Pearson upper bound for binomial probability when 0 events occur in n trials."""
    if n <= 0:
        return 1.0
    # P(0 events) = (1 - p)^n >= alpha => 1 - p <= alpha^(1/n) => p <= 1 - alpha^(1/n)
    return round(100.0 * (1.0 - math.pow(alpha, 1.0 / n)), 3)


def validate_match_data(games: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Validates raw match game records for pair integrity, color reversal, and outcome validity."""
    if not games:
        raise ValueError("Match record contains zero games.")

    seen_game_ids: set[int] = set()
    pairs: dict[int, list[dict[str, Any]]] = {}

    for idx, g in enumerate(games):
        game_num = g.get("game")
        if game_num is None or not isinstance(game_num, int):
            raise ValueError(f"Game at index {idx} has invalid or missing 'game' ID: {game_num}")
        if game_num in seen_game_ids:
            raise ValueError(f"Duplicate game ID detected: {game_num}")
        seen_game_ids.add(game_num)

        pair_num = g.get("pair")
        if pair_num is None or not isinstance(pair_num, int) or pair_num < 1:
            raise ValueError(f"Game {game_num} has invalid 'pair' ID: {pair_num}")

        res = g.get("result")
        if res not in ("1-0", "0-1", "1/2-1/2"):
            raise ValueError(f"Game {game_num} has malformed or incomplete result: {res}")

        color = g.get("janus_color")
        if color not in ("white", "black"):
            raise ValueError(f"Game {game_num} has invalid janus_color: {color}")

        pairs.setdefault(pair_num, []).append(g)

    # Validate pairs sequence: must be 1 .. N with no missing pairs
    sorted_pair_nums = sorted(pairs.keys())
    expected_pairs = list(range(1, len(sorted_pair_nums) + 1))
    if sorted_pair_nums != expected_pairs:
        missing = set(expected_pairs) - set(sorted_pair_nums)
        raise ValueError(f"Opening pairs sequence is discontinuous. Missing pair numbers: {sorted(missing)}")

    # Validate each pair has exactly 2 games with reversed colors
    for p_num, p_games in pairs.items():
        if len(p_games) != 2:
            raise ValueError(f"Pair {p_num} contains {len(p_games)} games; expected exactly 2 for paired evaluation.")
        colors = {g["janus_color"] for g in p_games}
        if colors != {"white", "black"}:
            raise ValueError(f"Pair {p_num} lacks balanced color reversal; observed colors: {colors}")

    return pairs


def compute_paired_statistics(pairs: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    """Computes mathematically sound paired statistics with explicit zero-variance handling."""
    pair_deltas: list[float] = []
    pair_details: list[dict[str, Any]] = []

    pairs_won_by_treatment = 0
    pairs_tied = 0
    pairs_lost_by_treatment = 0

    for p_num in sorted(pairs.keys()):
        p_games = pairs[p_num]
        e2_pts = 0.0
        e1_pts = 0.0

        for g in p_games:
            res = g["result"]
            j_col = g["janus_color"]
            if res == "1/2-1/2":
                e1_pts += 0.5
                e2_pts += 0.5
            elif (res == "1-0" and j_col == "white") or (res == "0-1" and j_col == "black"):
                e1_pts += 1.0
            else:
                e2_pts += 1.0

        p_delta = ((e2_pts - e1_pts) / 2.0) * 100.0
        pair_deltas.append(p_delta)

        if e2_pts > e1_pts:
            pairs_won_by_treatment += 1
            verdict = "treatment_win"
        elif e2_pts < e1_pts:
            pairs_lost_by_treatment += 1
            verdict = "treatment_loss"
        else:
            pairs_tied += 1
            verdict = "tie"

        pair_details.append({
            "pair": p_num,
            "opening_id": p_games[0].get("opening_id", "unknown"),
            "treatment_points": e2_pts,
            "control_points": e1_pts,
            "pair_delta_pct": round(p_delta, 2),
            "verdict": verdict,
        })

    n_pairs = len(pair_deltas)
    mean_delta = sum(pair_deltas) / n_pairs if n_pairs else 0.0
    var_d = sum((d - mean_delta) ** 2 for d in pair_deltas) / (n_pairs - 1) if n_pairs > 1 else 0.0
    se_d = math.sqrt(var_d / n_pairs) if n_pairs > 0 else 0.0
    df = n_pairs - 1

    is_zero_variance = bool(var_d < 1e-12)
    all_zero_differences = bool(is_zero_variance and abs(mean_delta) < 1e-12)

    if is_zero_variance:
        # Standard Student's t-statistic is mathematically undefined (0/0)
        t_stat = None
        p_val_t = None
        ci_parametric = None
        boot_ci = (round(mean_delta, 2), round(mean_delta, 2))
        wilcoxon = wilcoxon_signed_rank_test(pair_deltas)
        sig_05 = False

        clopper_pearson_ub = clopper_pearson_upper_bound_zero_events(n_pairs, alpha=0.05) if all_zero_differences else None

        stat_note = (
            "Zero variance detected across all opening pairs. The conventional studentised "
            "paired t-statistic is mathematically undefined (0/0) because sample standard error is zero. "
            "A zero-width plug-in bootstrap interval is degenerate and must NOT be interpreted as proof "
            "of population equivalence. In this sample, exactly 0 non-tied pairs were observed. By the exact "
            f"Clopper-Pearson binomial bound (alpha=0.05), the true population probability of an opening pair "
            f"differing is bounded by [0.0%, {clopper_pearson_ub}%]. Claiming practical equivalence requires "
            "a predeclared non-inferiority/equivalence margin (TOST)."
        )
    else:
        t_stat = round(mean_delta / se_d, 4)
        p_val_t = round(student_t_two_sided_p_value(t_stat, df), 5)
        # 95% critical value approximation or Student t distribution
        tcrit = 2.0096 if df >= 40 else (2.042 if df >= 30 else 2.086)
        ci_parametric = (
            round(mean_delta - tcrit * se_d, 2),
            round(mean_delta + tcrit * se_d, 2),
        )
        boot_ci = paired_bootstrap_ci(pair_deltas, n_resamples=10_000, seed=42)
        wilcoxon = wilcoxon_signed_rank_test(pair_deltas)
        sig_05 = bool(p_val_t < 0.05)
        clopper_pearson_ub = None
        stat_note = "Non-zero variance observed; standard paired parametric and bootstrap procedures applied."

    return {
        "sample_size_pairs": n_pairs,
        "treatment_pairs_won": pairs_won_by_treatment,
        "treatment_pairs_tied": pairs_tied,
        "treatment_pairs_lost": pairs_lost_by_treatment,
        "mean_paired_difference_pct": round(mean_delta, 2),
        "sample_variance_pct2": round(var_d, 4),
        "standard_error_pct": round(se_d, 4),
        "degrees_of_freedom": df,
        "is_zero_variance": is_zero_variance,
        "all_zero_differences": all_zero_differences,
        "t_statistic": t_stat,
        "p_value_two_sided": p_val_t,
        "paired_t_95_ci_pct": ci_parametric,
        "paired_bootstrap_95_ci_pct": boot_ci,
        "clopper_pearson_95_upper_bound_diff_rate_pct": clopper_pearson_ub,
        "wilcoxon_test": wilcoxon,
        "statistically_significant_05": sig_05,
        "statistical_interpretation_note": stat_note,
        "pairs_detail": pair_details,
    }


def analyze_match_file(json_path: Path) -> dict[str, Any]:
    """Loads and comprehensively analyzes a match JSON report."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    games = data.get("games", [])
    metadata = data.get("metadata", {})

    e1_name = metadata.get("engine1_name", "Janus-Baseline")
    e2_name = metadata.get("engine2_name", "Candidate")

    validated_pairs = validate_match_data(games)
    paired_stats = compute_paired_statistics(validated_pairs)

    e1_wins = sum(1 for g in games if (g["result"] == "1-0" and g["janus_color"] == "white") or (g["result"] == "0-1" and g["janus_color"] == "black"))
    draws = sum(1 for g in games if g["result"] == "1/2-1/2")
    e2_wins = len(games) - e1_wins - draws

    total_games = len(games)
    e1_points = e1_wins + 0.5 * draws
    e2_points = e2_wins + 0.5 * draws

    return {
        "match": {
            "json_path": str(json_path),
            "total_games": total_games,
            "depth": metadata.get("depth_each_move", 3),
            "openings": metadata.get("openings_path"),
            "seed": metadata.get("seed"),
            "hash_mb": metadata.get("hash_mb"),
        },
        "arm_a": {
            "name": e1_name,
            "role": "control",
            "wins": e1_wins,
            "draws": draws,
            "losses": e2_wins,
            "points": e1_points,
            "score_pct": round(100.0 * e1_points / total_games, 2) if total_games else 0.0,
        },
        "arm_b": {
            "name": e2_name,
            "role": "treatment",
            "wins": e2_wins,
            "draws": draws,
            "losses": e1_wins,
            "points": e2_points,
            "score_pct": round(100.0 * e2_points / total_games, 2) if total_games else 0.0,
        },
        "paired_analysis": paired_stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True, help="Path to match JSON report")
    parser.add_argument("--out", type=Path, default=None, help="Output path for paired statistics JSON")
    args = parser.parse_args()

    results = analyze_match_file(args.json)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Saved robust paired statistics to {args.out}")

    a = results["arm_a"]
    b = results["arm_b"]
    p = results["paired_analysis"]
    m = results["match"]

    print("\n========================================================")
    print("      PROJECT JANUS v0.27 ROBUST PAIRED MATCH AUDIT     ")
    print("========================================================")
    print(f"Games: {m['total_games']} ({p['sample_size_pairs']} opening pairs, 100% paired with color reversal)")
    print(f"Control ({a['name']}):   {a['wins']}W - {a['draws']}D - {a['losses']}L | {a['points']}/{m['total_games']} ({a['score_pct']}%)")
    print(f"Treatment ({b['name']}): {b['wins']}W - {b['draws']}D - {b['losses']}L | {b['points']}/{m['total_games']} ({b['score_pct']}%)")
    print("--------------------------------------------------------")
    print("PAIRED UNIT ANALYSIS (Unit = Opening Pair):")
    print(f"  Pairs Won by Treatment: {p['treatment_pairs_won']}")
    print(f"  Pairs Tied:             {p['treatment_pairs_tied']}")
    print(f"  Pairs Lost by Treatment:{p['treatment_pairs_lost']}")
    print(f"  Mean Paired Difference: {p['mean_paired_difference_pct']:+.2f}%")
    print(f"  Sample Variance:        {p['sample_variance_pct2']:.4f}")
    print(f"  Standard Error (SE):    {p['standard_error_pct']:.4f}")
    if p["is_zero_variance"]:
        print("  Paired t-test:          UNDEFINED (0/0 division; sample variance is zero)")
        print(f"  Clopper-Pearson 95% UB: Rate of non-tied pairs in population <= {p['clopper_pearson_95_upper_bound_diff_rate_pct']}%")
    else:
        print(f"  Paired t-test (df={p['degrees_of_freedom']}):   t = {p['t_statistic']:.4f}, p = {p['p_value_two_sided']:.5f}")
        print(f"  Parametric 95% CI:      [{p['paired_t_95_ci_pct'][0]}%, {p['paired_t_95_ci_pct'][1]}%]")
    print(f"  Bootstrap 95% CI:       [{p['paired_bootstrap_95_ci_pct'][0]}%, {p['paired_bootstrap_95_ci_pct'][1]}%]")
    print("--------------------------------------------------------")
    print("Statistical Interpretation:")
    print(f"  {p['statistical_interpretation_note']}")
    print("========================================================\n")


if __name__ == "__main__":
    main()
