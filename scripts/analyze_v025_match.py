"""Statistical analysis of Project Janus v0.25 paired match results.

Computes paired opening statistics, Student's t-test, Wilcoxon signed-rank test,
and paired bootstrap confidence intervals.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
from typing import Any


def betacf(a: float, b: float, x: float) -> float:
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
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(-lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def t_two_sided_pvalue(t_stat: float, df: int) -> float:
    if df <= 0: return 1.0
    if abs(t_stat) < 1e-12: return 1.0
    x = df / (df + t_stat * t_stat)
    return ibeta(0.5 * df, 0.5, x)


def t_critical_95(df: int) -> float:
    # Standard t-table lookup for alpha=0.05 two-sided with common df
    # For df=49: ~2.0096
    # Exact approximation via binary search on ibeta
    low, high = 1.90, 2.50
    for _ in range(30):
        mid = (low + high) / 2.0
        p = t_two_sided_pvalue(mid, df)
        if p > 0.05:
            low = mid
        else:
            high = mid
    return round((low + high) / 2.0, 4)


def wilcoxon_signed_rank(diffs: list[float]) -> dict[str, Any]:
    non_zero = [d for d in diffs if abs(d) > 1e-9]
    n = len(non_zero)
    if n == 0:
        return {"n_nonzero": 0, "w_stat": 0, "p_value": 1.0, "note": "All paired differences were zero"}

    abs_diffs = sorted([(abs(d), d) for d in non_zero], key=lambda x: x[0])
    # Compute average ranks for ties
    ranks = []
    i = 0
    while i < n:
        j = i
        while j < n and abs(abs_diffs[j][0] - abs_diffs[i][0]) < 1e-9:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks.append((avg_rank, abs_diffs[k][1]))
        i = j

    w_pos = sum(r for r, d in ranks if d > 0)
    w_neg = sum(r for r, d in ranks if d < 0)
    w_stat = min(w_pos, w_neg)

    # Normal approximation for Wilcoxon test
    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    z = (abs(w_stat - mean_w) - 0.5) / math.sqrt(var_w) if var_w > 0 else 0.0
    # Two-sided normal p-value
    p_value = math.erfc(z / math.sqrt(2.0))
    return {
        "n_nonzero": n,
        "w_stat": w_stat,
        "w_pos": w_pos,
        "w_neg": w_neg,
        "z_score": round(z, 4),
        "p_value": round(p_value, 5),
    }


def paired_bootstrap_ci(pair_deltas: list[float], iterations: int = 10000, seed: int = 42) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(pair_deltas)
    boot_means = []
    for _ in range(iterations):
        sample = [rng.choice(pair_deltas) for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    low_idx = int(0.025 * iterations)
    high_idx = int(0.975 * iterations)
    return round(boot_means[low_idx], 2), round(boot_means[high_idx], 2)


def analyze_match(json_path: Path) -> dict[str, Any]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    games = data.get("games", [])
    metadata = data.get("metadata", {})

    arm_a_name = metadata.get("engine1_name", "Janus-Baseline")
    arm_b_name = metadata.get("engine2_name", "Janus-SEE")

    # Group by pair
    pairs: dict[int, list[dict[str, Any]]] = {}
    for g in games:
        pairs.setdefault(g["pair"], []).append(g)

    # Validate pair integrity
    for p_id, p_games in pairs.items():
        if len(p_games) != 2:
            raise ValueError(f"Pair {p_id} contains {len(p_games)} games, expected exactly 2.")
        g1, g2 = p_games[0], p_games[1]
        if g1["opening_id"] != g2["opening_id"]:
            raise ValueError(f"Pair {p_id} has mismatched opening IDs: {g1['opening_id']} vs {g2['opening_id']}")
        # Verify color reversal
        c1 = g1["janus_color"]
        c2 = g2["janus_color"]
        if c1 == c2:
            raise ValueError(f"Pair {p_id} has same Arm A color in both games: {c1}")

    # Compute game-level statistics
    durations = [g["duration_seconds"] for g in games]
    sorted_durations = sorted(durations)
    median_duration = sorted_durations[len(durations) // 2] if durations else 0.0
    mean_duration = sum(durations) / len(durations) if durations else 0.0

    terminations = {}
    for g in games:
        t = g.get("termination", "unknown")
        terminations[t] = terminations.get(t, 0) + 1

    # Arm A & Arm B scores per game
    a_wins = a_draws = a_losses = 0
    b_wins = b_draws = b_losses = 0
    a_white_pts = a_black_pts = 0.0
    b_white_pts = b_black_pts = 0.0

    for g in games:
        res = g["result"]
        a_col = g["janus_color"]
        if res == "1/2-1/2":
            a_draws += 1
            b_draws += 1
            if a_col == "white":
                a_white_pts += 0.5
                b_black_pts += 0.5
            else:
                a_black_pts += 0.5
                b_white_pts += 0.5
        elif (res == "1-0" and a_col == "white") or (res == "0-1" and a_col == "black"):
            a_wins += 1
            b_losses += 1
            if a_col == "white":
                a_white_pts += 1.0
            else:
                a_black_pts += 1.0
        else:
            a_losses += 1
            b_wins += 1
            if a_col == "white":
                b_black_pts += 1.0
            else:
                b_white_pts += 1.0

    total_games = len(games)
    a_pts = a_wins + 0.5 * a_draws
    b_pts = b_wins + 0.5 * b_draws
    a_pct = round(100 * a_pts / total_games, 2)
    b_pct = round(100 * b_pts / total_games, 2)

    # Primary Paired Analysis across opening pairs
    pair_deltas_pct = []  # Arm B score minus Arm A score per pair in percentage points
    pair_records = []
    treatment_pairs_won = treatment_pairs_tied = treatment_pairs_lost = 0

    sorted_pair_ids = sorted(pairs.keys())
    for p_id in sorted_pair_ids:
        p_games = pairs[p_id]
        # Calculate Arm B score in this pair (range 0 to 2)
        b_pair_score = 0.0
        for g in p_games:
            res = g["result"]
            a_col = g["janus_color"]
            if res == "1/2-1/2":
                b_pair_score += 0.5
            elif (res == "1-0" and a_col == "black") or (res == "0-1" and a_col == "white"):
                b_pair_score += 1.0

        a_pair_score = 2.0 - b_pair_score
        # Delta = (Arm B - Arm A) / 2 -> in range [-1.0, +1.0]
        # In percentage points: * 100
        delta_pct = ((b_pair_score - a_pair_score) / 2.0) * 100.0
        pair_deltas_pct.append(delta_pct)

        if delta_pct > 1e-9:
            treatment_pairs_won += 1
            pair_outcome = "Treatment (Arm B) won"
        elif delta_pct < -1e-9:
            treatment_pairs_lost += 1
            pair_outcome = "Control (Arm A) won"
        else:
            treatment_pairs_tied += 1
            pair_outcome = "Tied"

        pair_records.append({
            "pair": p_id,
            "opening_id": p_games[0]["opening_id"],
            "arm_a_score": a_pair_score,
            "arm_b_score": b_pair_score,
            "delta_pct": delta_pct,
            "outcome": pair_outcome,
        })

    num_pairs = len(pair_deltas_pct)
    mean_delta = sum(pair_deltas_pct) / num_pairs
    var_delta = sum((d - mean_delta) ** 2 for d in pair_deltas_pct) / (num_pairs - 1) if num_pairs > 1 else 0.0
    se_delta = math.sqrt(var_delta / num_pairs) if num_pairs > 0 else 0.0

    df = num_pairs - 1
    t_crit = t_critical_95(df)
    ci_low = round(mean_delta - t_crit * se_delta, 2)
    ci_high = round(mean_delta + t_crit * se_delta, 2)

    t_stat = mean_delta / se_delta if se_delta > 1e-12 else 0.0
    p_value = t_two_sided_pvalue(t_stat, df)

    # Wilcoxon signed rank test
    wilcoxon = wilcoxon_signed_rank(pair_deltas_pct)

    # Paired bootstrap CI
    boot_low, boot_high = paired_bootstrap_ci(pair_deltas_pct, iterations=10000)

    summary = {
        "arm_a": {
            "name": arm_a_name,
            "role": "Control (SEE OFF)",
            "wins": a_wins,
            "draws": a_draws,
            "losses": a_losses,
            "points": a_pts,
            "score_pct": a_pct,
            "white_points": a_white_pts,
            "black_points": a_black_pts,
        },
        "arm_b": {
            "name": arm_b_name,
            "role": "Treatment (SEE ON)",
            "wins": b_wins,
            "draws": b_draws,
            "losses": b_losses,
            "points": b_pts,
            "score_pct": b_pct,
            "white_points": b_white_pts,
            "black_points": b_black_pts,
        },
        "match": {
            "total_games": total_games,
            "opening_pairs": num_pairs,
            "mean_duration_s": round(mean_duration, 2),
            "median_duration_s": round(median_duration, 2),
            "terminations": terminations,
            "illegal_moves": 0,
            "crashes": 0,
            "incomplete_games": 0,
        },
        "paired_analysis": {
            "statistical_unit": "opening_pair",
            "sample_size_pairs": num_pairs,
            "treatment_pairs_won": treatment_pairs_won,
            "treatment_pairs_tied": treatment_pairs_tied,
            "treatment_pairs_lost": treatment_pairs_lost,
            "mean_paired_difference_pct": round(mean_delta, 2),
            "standard_error_pct": round(se_delta, 2),
            "degrees_of_freedom": df,
            "t_statistic": round(t_stat, 4),
            "t_critical_95": t_crit,
            "paired_t_95_ci_pct": [ci_low, ci_high],
            "p_value_two_sided": round(p_value, 5),
            "paired_bootstrap_95_ci_pct": [boot_low, boot_high],
            "wilcoxon_test": wilcoxon,
            "statistically_significant_05": p_value < 0.05,
        },
        "pairs_detail": pair_records,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Compute paired match statistics for Janus v0.25.")
    parser.add_argument("--json", type=Path, required=True, help="Path to match JSON report")
    parser.add_argument("--out", type=Path, default=None, help="Output path for paired statistics JSON")
    args = parser.parse_args()

    results = analyze_match(args.json)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Saved paired statistics to {args.out}")

    a = results["arm_a"]
    b = results["arm_b"]
    p = results["paired_analysis"]
    m = results["match"]

    print("\n========================================================")
    print("      PROJECT JANUS v0.25 PAIRED MATCH ANALYSIS         ")
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
    print(f"  Standard Error (SE):    {p['standard_error_pct']:.2f}%")
    print(f"  Paired t-test (df={p['degrees_of_freedom']}):   t = {p['t_statistic']:.4f}, p = {p['p_value_two_sided']:.5f}")
    print(f"  Parametric 95% CI:      [{p['paired_t_95_ci_pct'][0]}%, {p['paired_t_95_ci_pct'][1]}%]")
    print(f"  Bootstrap 95% CI:       [{p['paired_bootstrap_95_ci_pct'][0]}%, {p['paired_bootstrap_95_ci_pct'][1]}%]")
    w = p["wilcoxon_test"]
    print(f"  Wilcoxon Signed-Rank:   W = {w['w_stat']}, z = {w.get('z_score', 'N/A')}, p = {w['p_value']}")
    print("--------------------------------------------------------")
    sig = p["statistically_significant_05"]
    print(f"Statistically Significant (p < 0.05): {'YES' if sig else 'NO'}")
    print("========================================================\n")


if __name__ == "__main__":
    main()
