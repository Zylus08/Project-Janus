"""Statistical analysis of Project Janus v0.26 paired match results.

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


def student_t_two_sided_p_value(t_stat: float, df: int) -> float:
    if df <= 0: return 1.0
    t2 = t_stat * t_stat
    x = df / (df + t2)
    return ibeta(0.5 * df, 0.5, x)


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def wilcoxon_signed_rank_test(differences: list[float]) -> dict[str, Any]:
    non_zero_diffs = [d for d in differences if abs(d) > 1e-9]
    n = len(non_zero_diffs)
    if n == 0:
        return {"w_stat": 0.0, "p_value": 1.0, "n_effective": 0, "z_score": 0.0}

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


def analyze_match(json_path: Path) -> dict[str, Any]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    games = data.get("games", [])
    metadata = data.get("metadata", {})

    e1_name = metadata.get("engine1_name", "Janus-Baseline")
    e2_name = metadata.get("engine2_name", "Candidate")

    e1_wins = 0
    draws = 0
    e2_wins = 0

    pairs: dict[int, list[dict[str, Any]]] = {}
    for g in games:
        p_num = g.get("pair", 1)
        pairs.setdefault(p_num, []).append(g)

        res = g["result"]
        j_col = g["janus_color"]
        if res == "1/2-1/2":
            draws += 1
        elif (res == "1-0" and j_col == "white") or (res == "0-1" and j_col == "black"):
            e1_wins += 1
        else:
            e2_wins += 1

    total_games = len(games)
    e1_points = e1_wins + 0.5 * draws
    e2_points = e2_wins + 0.5 * draws
    e1_score_pct = round(100.0 * e1_points / total_games, 2) if total_games else 0.0
    e2_score_pct = round(100.0 * e2_points / total_games, 2) if total_games else 0.0

    pair_deltas: list[float] = []
    pair_details: list[dict[str, Any]] = []

    pairs_won_by_e2 = 0
    pairs_tied = 0
    pairs_lost_by_e2 = 0

    for p_num in sorted(pairs.keys()):
        p_games = pairs[p_num]
        if len(p_games) != 2:
            raise ValueError(f"Opening pair {p_num} has {len(p_games)} games, expected exactly 2 for paired analysis.")

        colors = {g["janus_color"] for g in p_games}
        if colors != {"white", "black"}:
            raise ValueError(f"Opening pair {p_num} lacks balanced colors: {colors}")

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
            pairs_won_by_e2 += 1
            verdict = "treatment_win"
        elif e2_pts < e1_pts:
            pairs_lost_by_e2 += 1
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

    t_stat = (mean_delta / se_d) if se_d > 1e-12 else 0.0
    p_val_t = student_t_two_sided_p_value(t_stat, df) if df > 0 else 1.0

    ci_parametric = (
        round(mean_delta - 2.0096 * se_d, 2),
        round(mean_delta + 2.0096 * se_d, 2),
    )
    boot_ci = paired_bootstrap_ci(pair_deltas, n_resamples=10_000, seed=42)
    wilcoxon = wilcoxon_signed_rank_test(pair_deltas)

    sig_05 = bool(p_val_t < 0.05)

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
            "score_pct": e1_score_pct,
        },
        "arm_b": {
            "name": e2_name,
            "role": "treatment",
            "wins": e2_wins,
            "draws": draws,
            "losses": e1_wins,
            "points": e2_points,
            "score_pct": e2_score_pct,
        },
        "paired_analysis": {
            "sample_size_pairs": n_pairs,
            "treatment_pairs_won": pairs_won_by_e2,
            "treatment_pairs_tied": pairs_tied,
            "treatment_pairs_lost": pairs_lost_by_e2,
            "mean_paired_difference_pct": round(mean_delta, 2),
            "standard_error_pct": round(se_d, 2),
            "degrees_of_freedom": df,
            "t_statistic": round(t_stat, 4),
            "p_value_two_sided": round(p_val_t, 5),
            "paired_t_95_ci_pct": ci_parametric,
            "paired_bootstrap_95_ci_pct": boot_ci,
            "wilcoxon_test": wilcoxon,
            "statistically_significant_05": sig_05,
        },
        "pairs": pair_details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
    print("      PROJECT JANUS v0.26 PAIRED MATCH ANALYSIS         ")
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
