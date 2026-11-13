#!/usr/bin/env python3
"""
Scientific Reconciliation Audit of Milestone P1.11 Tournaments.
Independently reconstructs all game outcomes, paired metrics, pentanomial counts,
Student's t statistics, and TOST equivalence statistics directly from raw PGN files.
"""

import math
import json
from pathlib import Path
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.11" / "pgn"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.12" / "raw" / "p111_reconciliation_audit_raw.json"


def regularized_incomplete_beta(x: float, a: float, b: float, n_steps: int = 1000) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    h = x / n_steps

    def integrand(u):
        if u <= 0.0 or u >= 1.0:
            return 0.0
        return (u ** (a - 1.0)) * ((1.0 - u) ** (b - 1.0))

    integral = integrand(0.0) + integrand(x)
    for i in range(1, n_steps):
        u = i * h
        weight = 4.0 if (i % 2 == 1) else 2.0
        integral += weight * integrand(u)
    integral *= (h / 3.0)
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    return max(0.0, min(1.0, integral / math.exp(log_beta)))


def student_t_cdf(t: float, df: int) -> float:
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    ibeta = regularized_incomplete_beta(x, df / 2.0, 0.5)
    return 1.0 - 0.5 * ibeta if t >= 0 else 0.5 * ibeta


def student_t_two_tailed(t_val: float, df: int) -> float:
    if df <= 0:
        return 1.0
    x = df / (df + t_val * t_val)
    return regularized_incomplete_beta(x, df / 2.0, 0.5)


def calc_confidence_interval(k: float, n: int, z: float = 1.95996):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def calc_elo(p: float):
    if p <= 0.00001 or p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)


def audit_pgn(pgn_path: Path):
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            games.append(g)

    num_games = len(games)
    num_pairs = num_games // 2
    wins_a, draws, wins_b = 0, 0, 0
    pair_diffs = []
    penta = {"2.0": 0, "1.5": 0, "1.0": 0, "0.5": 0, "0.0": 0}

    for i in range(num_pairs):
        g1 = games[2 * i]
        g2 = games[2 * i + 1]

        r1 = g1.headers.get("Result", "*")
        r2 = g2.headers.get("Result", "*")

        s_a = 0.0
        if r1 == "1-0":
            wins_a += 1
            s_a += 1.0
        elif r1 == "0-1":
            wins_b += 1
        elif r1 == "1/2-1/2":
            draws += 1
            s_a += 0.5

        if r2 == "0-1":
            wins_a += 1
            s_a += 1.0
        elif r2 == "1-0":
            wins_b += 1
        elif r2 == "1/2-1/2":
            draws += 1
            s_a += 0.5

        if abs(s_a - 2.0) < 1e-5:
            penta["2.0"] += 1
        elif abs(s_a - 1.5) < 1e-5:
            penta["1.5"] += 1
        elif abs(s_a - 1.0) < 1e-5:
            penta["1.0"] += 1
        elif abs(s_a - 0.5) < 1e-5:
            penta["0.5"] += 1
        else:
            penta["0.0"] += 1

        pair_diffs.append(s_a - 1.0)

    pts_a = wins_a + 0.5 * draws
    pct = pts_a / num_games
    elo = calc_elo(pct)
    ci_l, ci_h = calc_confidence_interval(pts_a, num_games)
    elo_l = calc_elo(ci_l)
    elo_h = calc_elo(ci_h)

    mean_d = sum(pair_diffs) / num_pairs
    var_d = sum((x - mean_d) ** 2 for x in pair_diffs) / (num_pairs - 1) if num_pairs > 1 else 0.0
    se_d = math.sqrt(var_d / num_pairs) if num_pairs > 0 else 0.0
    df = num_pairs - 1
    t_stat = mean_d / se_d if se_d > 0 else 0.0
    p_val = student_t_two_tailed(t_stat, df)

    delta_eq = 0.10
    t1 = (mean_d - (-delta_eq)) / se_d if se_d > 0 else 0.0
    t2 = (mean_d - (+delta_eq)) / se_d if se_d > 0 else 0.0
    p1 = 1.0 - student_t_cdf(t1, df)
    p2 = student_t_cdf(t2, df)
    p_tost = max(p1, p2)

    return {
        "games": num_games,
        "pairs": num_pairs,
        "wins_a": wins_a,
        "draws": draws,
        "wins_b": wins_b,
        "points_a": pts_a,
        "score_pct": round(pct * 100.0, 2),
        "elo": round(elo, 1) if elo is not None else None,
        "elo_ci_95": [round(elo_l, 1) if elo_l is not None else None, round(elo_h, 1) if elo_h is not None else None],
        "pentanomial": penta,
        "mean_pair_diff": round(mean_d, 4),
        "std_error": round(se_d, 4),
        "paired_t_statistic": round(t_stat, 4),
        "degrees_of_freedom": df,
        "p_value": p_val,
        "p_tost": round(p_tost, 4),
        "tost_equivalent": bool(p_tost < 0.05)
    }


def main():
    files = [
        ("x16_1t_vs_x7_1t.pgn", "Match A: Janus Classical X16-S (1T) vs Janus Classical X7 (1T)"),
        ("x16_4t_vs_x12_4t.pgn", "Match B: Janus Classical X16-P (4T) vs Janus Classical X12 (4T)"),
        ("x16_4t_vs_x12_4t_slow.pgn", "Match C: Janus Classical X16-P (4T) vs Janus Classical X12 (4T) [Slow TC]"),
        ("x16_1t_vs_sf19_1t.pgn", "Match SF-1T: Janus Classical X16-S (1T) vs Stockfish 19 (1T)"),
        ("x16_4t_vs_sf19_4t.pgn", "Match SF-4T: Janus Classical X16-P (4T) vs Stockfish 19 (4T)")
    ]

    reconstructed = {}
    total_reconstructed_games = 0

    print("=" * 80)
    print("INDEPENDENT RECONSTRUCTION OF ALL P1.11 TOURNAMENT MATCHES FROM RAW PGNS")
    print("=" * 80)

    for fn, label in files:
        res = audit_pgn(PGN_DIR / fn)
        reconstructed[fn] = res
        total_reconstructed_games += res["games"]

        print(f"\n{label}")
        print(f"  File: {fn} -> {res['games']} games ({res['pairs']} pairs)")
        print(f"  Score: +{res['wins_a']} ={res['draws']} -{res['wins_b']} = {res['points_a']}/{res['games']} ({res['score_pct']}%)")
        print(f"  Elo: {res['elo']} [95% CI: {res['elo_ci_95'][0]}, {res['elo_ci_95'][1]}]")
        print(f"  Pentanomial: ww={res['pentanomial']['2.0']}, wd={res['pentanomial']['1.5']}, dd/wl={res['pentanomial']['1.0']}, ld={res['pentanomial']['0.5']}, ll={res['pentanomial']['0.0']}")
        print(f"  Paired t-statistic: {res['paired_t_statistic']} (df={res['degrees_of_freedom']}), p-value: {res['p_value']:.2e}")
        print(f"  TOST Equivalence (margin=0.10): p_tost={res['p_tost']} -> Equivalent: {res['tost_equivalent']}")

    print("\n" + "=" * 80)
    print(f"TOTAL RECONSTRUCTED GAMES ACROSS ALL 5 MATCHES: {total_reconstructed_games}")
    print("=" * 80)

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(reconstructed, f, indent=2)
    print(f"Saved raw audit results to {OUT_RAW}")


if __name__ == "__main__":
    main()

