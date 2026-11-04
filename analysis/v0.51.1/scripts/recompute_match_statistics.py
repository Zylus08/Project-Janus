"""Project Janus v0.51.1 - Independent Statistical Reconciliation.

Recomputes:
1. Paired difference statistics with exact Student-t degrees of freedom (df=99)
   via regularized incomplete beta function (avoiding standard normal approximation).
2. 100,000-sample deterministic paired bootstrap for:
   - Mean paired delta
   - Win percentage
   - Asymmetric Elo difference interval
3. Sensitivity analyses across adjudication classifications:
   - S1: Exclude 9 horizon games
   - S2: Conservative rescore (K0 gets wins where K0 had material advantage: Games 18, 21, 123, 186)
   - S3: Adversarial worst-case (all 9 horizon games awarded to K0)
4. Saves raw output to analysis/v0.51.1/raw/corrected_statistics.json
"""

import math
import random
import json
import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
PAIR_LEDGER = ROOT / "analysis" / "v0.51.1" / "raw" / "independent_pair_ledger.csv"
GAME_LEDGER = ROOT / "analysis" / "v0.51.1" / "raw" / "independent_game_ledger.csv"
OUT_JSON = ROOT / "analysis" / "v0.51.1" / "raw" / "corrected_statistics.json"


# Exact Student-t survival function via Regularized Incomplete Beta
def betacf(a, b, x):
    MAXIT = 500
    EPS = 3.0e-16
    FPMIN = 1.0e-300
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
        del_h = d * c
        h *= del_h
        if abs(del_h - 1.0) < EPS:
            break
    return h


def ibeta(a, b, x):
    if x < 0.0 or x > 1.0:
        raise ValueError("x out of bounds")
    if x == 0.0: return 0.0
    if x == 1.0: return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    factor = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return factor * betacf(a, b, x) / a
    else:
        return 1.0 - factor * betacf(b, a, 1.0 - x) / b


def student_t_sf(t, df):
    x = df / (df + t * t)
    return 0.5 * ibeta(df / 2.0, 0.5, x)


def compute_elo(score_fraction):
    if score_fraction <= 0.0: return -1000.0
    if score_fraction >= 1.0: return +1000.0
    return -400.0 * math.log10(1.0 / score_fraction - 1.0)


def main():
    print("Executing independent statistical reconciliation...")

    # Load pair ledger
    pairs = []
    with open(PAIR_LEDGER, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            pairs.append({
                "pair_id": int(r["pair_id"]),
                "opening_id": r["opening_id"],
                "n2_pair_score": float(r["n2_pair_score"]),
                "k0_pair_score": float(r["k0_pair_score"]),
                "pair_delta": float(r["pair_delta"]),
                "game_a_id": int(r["game_a_id"]),
                "game_b_id": int(r["game_b_id"]),
                "game_a_term": r["game_a_term"],
                "game_b_term": r["game_b_term"]
            })

    # Load game ledger
    games = []
    with open(GAME_LEDGER, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            games.append(r)

    n_pairs = len(pairs)
    deltas = [p["pair_delta"] for p in pairs]
    mean_delta = sum(deltas) / n_pairs
    variance_delta = sum((d - mean_delta) ** 2 for d in deltas) / (n_pairs - 1)
    std_delta = math.sqrt(variance_delta)
    se_delta = std_delta / math.sqrt(n_pairs)
    t_stat = mean_delta / se_delta
    df = n_pairs - 1

    # Exact p-values
    p_val_one_tailed = student_t_sf(t_stat, df)
    p_val_two_tailed = 2.0 * p_val_one_tailed

    # Normal approximation (reported in v0.51)
    p_val_normal_approx = math.erfc(t_stat / math.sqrt(2.0))

    # Match score
    total_games = len(games)
    n2_total_pts = sum(float(g["n2_score"]) for g in games)
    win_fraction = n2_total_pts / total_games
    point_elo = compute_elo(win_fraction)

    # 1. v0.51 Linear Delta-Method Elo Interval
    se_elo_linear = 400.0 / (math.log(10) * win_fraction * (1.0 - win_fraction) * math.sqrt(total_games))
    linear_elo_low = point_elo - 1.96 * se_elo_linear
    linear_elo_high = point_elo + 1.96 * se_elo_linear

    # 2. 100,000-Sample Paired Bootstrap
    random.seed(42)
    boot_deltas = []
    boot_pcts = []
    boot_elos = []

    B = 100000
    for _ in range(B):
        sample = random.choices(pairs, k=n_pairs)
        d_mean = sum(p["pair_delta"] for p in sample) / n_pairs
        n2_pts = sum(p["n2_pair_score"] for p in sample)
        pct = (n2_pts / total_games) * 100.0
        frac = n2_pts / total_games
        elo_sample = compute_elo(frac)
        boot_deltas.append(d_mean)
        boot_pcts.append(pct)
        boot_elos.append(elo_sample)

    boot_deltas.sort()
    boot_pcts.sort()
    boot_elos.sort()

    delta_ci_95 = [boot_deltas[int(0.025 * B)], boot_deltas[int(0.975 * B)]]
    pct_ci_95 = [boot_pcts[int(0.025 * B)], boot_pcts[int(0.975 * B)]]
    elo_ci_95 = [boot_elos[int(0.025 * B)], boot_elos[int(0.975 * B)]]

    # Sensitivity Analyses
    # S1: Exclude 9 horizon games (Pairs with horizon games rescored or excluded)
    horizon_game_ids = {18, 21, 73, 88, 121, 123, 133, 148, 186}
    clean_pairs = [p for p in pairs if p["game_a_id"] not in horizon_game_ids and p["game_b_id"] not in horizon_game_ids]
    s1_n_pairs = len(clean_pairs)
    s1_deltas = [p["pair_delta"] for p in clean_pairs]
    s1_mean_delta = sum(s1_deltas) / s1_n_pairs
    s1_std_delta = math.sqrt(sum((d - s1_mean_delta) ** 2 for d in s1_deltas) / (s1_n_pairs - 1))
    s1_se = s1_std_delta / math.sqrt(s1_n_pairs)
    s1_t = s1_mean_delta / s1_se
    s1_p = 2.0 * student_t_sf(s1_t, s1_n_pairs - 1)
    s1_pts = sum(p["n2_pair_score"] for p in clean_pairs)
    s1_total_g = s1_n_pairs * 2
    s1_pct = (s1_pts / s1_total_g) * 100.0
    s1_elo = compute_elo(s1_pts / s1_total_g)

    # S2: Conservative Rescore
    # Games where K0 had material advantage awarded to K0 (18, 21, 123, 186); remaining 5 remain draws
    # Original N2 got 0.5 in all 9. In S2, N2 gets 0.0 in 4 games (-2.0 pts total)
    s2_n2_pts = n2_total_pts - 2.0  # 188.0 - 2.0 = 186.0
    s2_pct = (s2_n2_pts / total_games) * 100.0  # 186 / 200 = 93.0%
    s2_elo = compute_elo(s2_n2_pts / total_games)
    # S2 deltas: pairs with games 18, 21, 123, 186 reduced by 1.0 delta each
    s2_deltas = list(deltas)
    for p_idx, p in enumerate(pairs):
        p_id = p["pair_id"]
        # pairs corresponding to games:
        # Game 18: pair 9
        # Game 21: pair 11
        # Game 123: pair 62
        # Game 186: pair 93
        if p_id in (9, 11, 62, 93):
            s2_deltas[p_idx] -= 1.0
    s2_mean_delta = sum(s2_deltas) / n_pairs
    s2_std_delta = math.sqrt(sum((d - s2_mean_delta) ** 2 for d in s2_deltas) / (n_pairs - 1))
    s2_se = s2_std_delta / math.sqrt(n_pairs)
    s2_t = s2_mean_delta / s2_se
    s2_p = 2.0 * student_t_sf(s2_t, n_pairs - 1)

    # S3: Adversarial Worst Case (All 9 horizon games awarded to K0)
    # N2 loses 0.5 in 9 games = -4.5 pts
    s3_n2_pts = n2_total_pts - 4.5  # 183.5 / 200 = 91.75%
    s3_pct = (s3_n2_pts / total_games) * 100.0
    s3_elo = compute_elo(s3_n2_pts / total_games)
    s3_deltas = list(deltas)
    horizon_pair_ids = {9, 11, 37, 44, 61, 62, 67, 74, 93}
    for p_idx, p in enumerate(pairs):
        if p["pair_id"] in horizon_pair_ids:
            s3_deltas[p_idx] -= 1.0
    s3_mean_delta = sum(s3_deltas) / n_pairs
    s3_std_delta = math.sqrt(sum((d - s3_mean_delta) ** 2 for d in s3_deltas) / (n_pairs - 1))
    s3_se = s3_std_delta / math.sqrt(n_pairs)
    s3_t = s3_mean_delta / s3_se
    s3_p = 2.0 * student_t_sf(s3_t, n_pairs - 1)

    results = {
        "sample_size": {
            "total_games": total_games,
            "total_pairs": n_pairs,
            "degrees_of_freedom": df
        },
        "score_results": {
            "n2_points": n2_total_pts,
            "k0_points": total_games - n2_total_pts,
            "n2_win_fraction": win_fraction,
            "n2_score_pct": win_fraction * 100.0,
            "point_elo_estimate": point_elo
        },
        "paired_statistics": {
            "mean_paired_delta": mean_delta,
            "sample_stdev": std_delta,
            "standard_error": se_delta,
            "paired_t_statistic": t_stat,
            "exact_student_t_p_two_tailed": p_val_two_tailed,
            "exact_student_t_p_one_tailed": p_val_one_tailed,
            "normal_approx_p_two_tailed_reported_v051": p_val_normal_approx,
            "p_value_ratio": p_val_two_tailed / p_val_normal_approx if p_val_normal_approx > 0 else None
        },
        "bootstrap_results_100k": {
            "resamples": B,
            "random_seed": 42,
            "delta_ci_95": delta_ci_95,
            "pct_ci_95": pct_ci_95,
            "asymmetric_elo_ci_95": elo_ci_95
        },
        "linear_delta_method_elo_reported_v051": {
            "point_elo": point_elo,
            "se_elo_linear": se_elo_linear,
            "elo_ci_95": [linear_elo_low, linear_elo_high]
        },
        "sensitivity_analyses": {
            "S1_exclude_horizon_games": {
                "clean_pairs_count": s1_n_pairs,
                "clean_games_count": s1_total_g,
                "n2_points": s1_pts,
                "n2_pct": s1_pct,
                "point_elo": s1_elo,
                "mean_delta": s1_mean_delta,
                "t_stat": s1_t,
                "p_value": s1_p
            },
            "S2_conservative_rescore_4_k0_wins": {
                "n2_points": s2_n2_pts,
                "n2_pct": s2_pct,
                "point_elo": s2_elo,
                "mean_delta": s2_mean_delta,
                "t_stat": s2_t,
                "p_value": s2_p
            },
            "S3_adversarial_rescore_all_9_k0_wins": {
                "n2_points": s3_n2_pts,
                "n2_pct": s3_pct,
                "point_elo": s3_elo,
                "mean_delta": s3_mean_delta,
                "t_stat": s3_t,
                "p_value": s3_p
            }
        }
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("Independent statistical reconciliation complete.")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
