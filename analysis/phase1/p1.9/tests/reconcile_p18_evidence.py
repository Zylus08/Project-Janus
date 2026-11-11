#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 0: Independent P1.8 Tournament and Evidence Reconciliation
Parses raw P1.8 PGNs directly and verifies:
  1. Match A: X13 (1T) vs X7 (1T) [200 games / 100 pairs]
  2. Match B: X13 (4T) vs X12 (4T) [200 games / 100 pairs]
  3. Match C: X13 (4T) vs X12 (4T) [40 games / 20 pairs @ 3s+100ms]
  4. Match SF: X13 (4T) vs Stockfish 19 (4T) [40 games / 20 pairs @ 2s+50ms]
"""

import sys
import os
import json
import math
import hashlib
from pathlib import Path
from collections import Counter
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.8" / "pgn"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "p18_reconciliation_summary.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

def student_t_pvalue(t_val: float, df: int) -> float:
    if df <= 0: return 1.0
    t = abs(t_val)
    x = df / (df + t * t)
    a = df / 2.0
    b = 0.5
    n_steps = 1000
    h = x / n_steps
    def integrand(u):
        if u <= 0.0 or u >= 1.0: return 0.0
        return (u ** (a - 1.0)) * ((1.0 - u) ** (b - 1.0))
    integral = integrand(0.0) + integrand(x)
    for i in range(1, n_steps):
        u = i * h
        weight = 4.0 if (i % 2 == 1) else 2.0
        integral += weight * integrand(u)
    integral *= (h / 3.0)
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    beta_val = math.exp(log_beta)
    cdf = integral / beta_val
    return max(0.0, min(1.0, cdf))

def calc_wilson_ci(k: float, n: int, z: float = 1.95996):
    if n == 0: return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))

def parse_pgn_match(pgn_path: Path, engine_a_name_fragment: str):
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None: break
            games.append(g)

    total_games = len(games)
    assert total_games % 2 == 0, f"Odd number of games in {pgn_path}: {total_games}"
    num_pairs = total_games // 2

    pair_diffs = []
    a_wins = 0
    b_wins = 0
    draws = 0

    for i in range(num_pairs):
        g1 = games[2 * i]
        g2 = games[2 * i + 1]

        # In Game 1: A is White, B is Black
        r1 = g1.headers["Result"]
        # In Game 2: B is White, A is Black
        r2 = g2.headers["Result"]

        # Score for A in Game 1
        if r1 == "1-0":
            s1 = 1.0
            a_wins += 1
        elif r1 == "0-1":
            s1 = 0.0
            b_wins += 1
        else:
            s1 = 0.5
            draws += 1

        # Score for A in Game 2
        if r2 == "0-1":
            s2 = 1.0
            a_wins += 1
        elif r2 == "1-0":
            s2 = 0.0
            b_wins += 1
        else:
            s2 = 0.5
            draws += 1

        pair_score_a = s1 + s2
        pair_diff = pair_score_a - 1.0  # Even = 0.0, +1.0 = 2-0, -1.0 = 0-2
        pair_diffs.append(pair_diff)

    points_a = a_wins + 0.5 * draws
    score_pct = points_a / total_games

    mean_d = sum(pair_diffs) / num_pairs
    variance_d = sum((x - mean_d) ** 2 for x in pair_diffs) / (num_pairs - 1) if num_pairs > 1 else 0.0
    se_d = math.sqrt(variance_d / num_pairs) if num_pairs > 0 else 0.0
    t_stat = (mean_d / se_d) if se_d > 0 else 0.0
    df = num_pairs - 1
    p_val = student_t_pvalue(t_stat, df)

    ci_low_p, ci_high_p = calc_wilson_ci(points_a, total_games)

    elo_delta = None
    if 0.0001 < score_pct < 0.9999:
        elo_delta = -400.0 * math.log10(1.0 / score_pct - 1.0)

    elo_ci = [None, None]
    if ci_low_p > 0.0001:
        elo_ci[0] = round(-400.0 * math.log10(1.0 / ci_low_p - 1.0), 1)
    if ci_high_p < 0.9999:
        elo_ci[1] = round(-400.0 * math.log10(1.0 / ci_high_p - 1.0), 1)

    return {
        "pgn_file": str(pgn_path.name),
        "total_games": total_games,
        "num_pairs": num_pairs,
        "wins_a": a_wins,
        "draws": draws,
        "wins_b": b_wins,
        "points_a": points_a,
        "score_pct": round(score_pct * 100.0, 2),
        "wilson_ci_95": [round(ci_low_p, 4), round(ci_high_p, 4)],
        "elo_delta": round(elo_delta, 1) if elo_delta is not None else None,
        "elo_ci_95": elo_ci,
        "t_statistic": round(t_stat, 4),
        "degrees_of_freedom": df,
        "p_value": round(p_val, 6),
        "statistically_significant": bool(p_val < 0.05)
    }

def main():
    print("=== PROJECT JANUS P1.9: PHASE 0 RECONCILIATION AUDIT ===")
    matches = {
        "Match_A_1T": (PGN_DIR / "x13_1t_vs_x7_1t.pgn", "X13"),
        "Match_B_4T_Blitz": (PGN_DIR / "x13_4t_vs_x12_4t.pgn", "X13"),
        "Match_C_4T_Slow": (PGN_DIR / "x13_4t_vs_x12_4t_slow.pgn", "X13"),
        "Match_SF_4T": (PGN_DIR / "x13_4t_vs_sf19_4t.pgn", "X13")
    }

    results = {}
    for mname, (pgn_file, frag) in matches.items():
        if not pgn_file.exists():
            print(f"PGN missing: {pgn_file}")
            continue
        res = parse_pgn_match(pgn_file, frag)
        results[mname] = res
        print(f"\n{mname} ({pgn_file.name}):")
        print(f"  Score: {res['wins_a']}W - {res['draws']}D - {res['wins_b']}L = {res['points_a']}/{res['total_games']} ({res['score_pct']}%)")
        print(f"  Elo: {res['elo_delta']} (CI: {res['elo_ci_95']}) | Wilson 95%: {res['wilson_ci_95']}")
        print(f"  t-stat: {res['t_statistic']} (df={res['degrees_of_freedom']}) | p-value: {res['p_value']} | Significant (p<0.05): {res['statistically_significant']}")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved reconciliation summary to {RAW_OUT}")

if __name__ == "__main__":
    main()

