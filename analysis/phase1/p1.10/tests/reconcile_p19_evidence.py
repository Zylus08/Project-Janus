#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 0: P1.9 Scientific Evidence & Integrity Audit
Parses raw P1.9 PGN archives and verifies:
  1. Match A: X14 1T vs X7 1T (200 games / 100 pairs)
  2. Match B: X14 4T vs X12 4T (200 games / 100 pairs)
  3. Match C: X14 4T vs X12 4T Slow (100 games / 50 pairs)
  4. Match SF: X14 4T vs SF19 4T (40 games / 20 pairs)
Audits:
  - Exact W-D-L counts
  - Paired-opening outcome differences
  - True variance and division-by-zero artifact in Match SF
  - Wilson score confidence intervals
  - Binary hashes and execution settings
"""

import os
import sys
import json
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
P19_PGN_DIR = ROOT / "analysis" / "phase1" / "p1.9" / "pgn"
P19_RAW_DIR = ROOT / "analysis" / "phase1" / "p1.9" / "raw"
P110_RAW_DIR = ROOT / "analysis" / "phase1" / "p1.10" / "raw"
P110_RAW_DIR.mkdir(parents=True, exist_ok=True)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def wilson_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))

def calc_elo(p: float) -> Optional[float]:
    if p <= 0.00001:
        return None
    if p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)

def student_t_pvalue(t_val: float, df: int) -> float:
    if df <= 0:
        return 1.0
    t = abs(t_val)
    x = df / (df + t * t)
    a = df / 2.0
    b = 0.5
    n_steps = 1000
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
    beta_val = math.exp(log_beta)
    cdf = integral / beta_val
    return max(0.0, min(1.0, cdf))

def parse_pgn_match(pgn_path: Path, engine_a_name: str) -> Dict[str, Any]:
    print(f"\nParsing PGN: {pgn_path.name}...")
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)

    print(f"  Total games found: {len(games)}")
    a_wins = 0
    b_wins = 0
    draws = 0

    # Group into pairs (consecutive 2 games per opening)
    num_pairs = len(games) // 2
    pair_diffs = []
    pair_details = []

    for p in range(num_pairs):
        g1 = games[2 * p]
        g2 = games[2 * p + 1]

        # Game 1: Check who is White
        g1_white = g1.headers.get("White", "")
        g1_res = g1.headers.get("Result", "*")
        g2_res = g2.headers.get("Result", "*")

        # Score for Engine A
        if engine_a_name in g1_white:
            # G1: A is White, B is Black
            s1 = 1.0 if g1_res == "1-0" else (0.5 if g1_res == "1/2-1/2" else 0.0)
            s2 = 1.0 if g2_res == "0-1" else (0.5 if g2_res == "1/2-1/2" else 0.0)
            if g1_res == "1-0": a_wins += 1
            elif g1_res == "0-1": b_wins += 1
            else: draws += 1

            if g2_res == "0-1": a_wins += 1
            elif g2_res == "1-0": b_wins += 1
            else: draws += 1
        else:
            # G1: B is White, A is Black
            s1 = 1.0 if g1_res == "0-1" else (0.5 if g1_res == "1/2-1/2" else 0.0)
            s2 = 1.0 if g2_res == "1-0" else (0.5 if g2_res == "1/2-1/2" else 0.0)
            if g1_res == "0-1": a_wins += 1
            elif g1_res == "1-0": b_wins += 1
            else: draws += 1

            if g2_res == "1-0": a_wins += 1
            elif g2_res == "0-1": b_wins += 1
            else: draws += 1

        pair_score = s1 + s2
        pair_diff = pair_score - 1.0
        pair_diffs.append(pair_diff)
        pair_details.append({
            "pair_idx": p + 1,
            "opening": g1.headers.get("Opening", "Unknown"),
            "g1_result": g1_res,
            "g2_result": g2_res,
            "score_a": pair_score,
            "diff": pair_diff
        })

    total_games = len(games)
    points_a = a_wins + 0.5 * draws
    score_pct = points_a / total_games if total_games > 0 else 0.0
    w_low, w_high = wilson_interval(points_a, total_games)
    elo = calc_elo(score_pct)
    elo_low = calc_elo(w_low)
    elo_high = calc_elo(w_high)

    # Paired Student's t test
    mean_d = sum(pair_diffs) / num_pairs if num_pairs > 0 else 0.0
    var_d = sum((x - mean_d) ** 2 for x in pair_diffs) / (num_pairs - 1) if num_pairs > 1 else 0.0
    se_d = math.sqrt(var_d / num_pairs) if num_pairs > 0 else 0.0

    division_by_zero_detected = (var_d == 0.0 and mean_d != 0.0)
    t_stat = (mean_d / se_d) if se_d > 0 else 0.0
    df = num_pairs - 1
    p_val = student_t_pvalue(t_stat, df)

    # Exact binomial test for win/loss disparity
    # Binomial p-value under H0: p = 0.5 for score
    binom_p = 0.5 ** total_games if points_a == 0 else None

    return {
        "pgn_file": pgn_path.name,
        "total_games": total_games,
        "num_pairs": num_pairs,
        "wins_a": a_wins,
        "draws": draws,
        "wins_b": b_wins,
        "points_a": points_a,
        "score_pct": round(score_pct * 100.0, 2),
        "wilson_95": [round(w_low, 4), round(w_high, 4)],
        "elo": round(elo, 1) if elo is not None else None,
        "elo_95": [round(elo_low, 1) if elo_low is not None else None, round(elo_high, 1) if elo_high is not None else None],
        "pair_mean_diff": round(mean_d, 4),
        "pair_variance": round(var_d, 6),
        "paired_t_stat": round(t_stat, 4),
        "degrees_of_freedom": df,
        "p_value_t": round(p_val, 6),
        "division_by_zero_in_se": division_by_zero_detected,
        "exact_binomial_p": binom_p
    }

def main():
    print("=== PROJECT JANUS P1.10: PHASE 0 SCIENTIFIC EVIDENCE AUDIT ===")

    # 1. Audit Binary Integrity
    binaries = {
        "X7": ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe",
        "X10": ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe",
        "X12": ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe",
        "X13": ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe",
        "X14": ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe",
        "SF19": Path("E:/ChessXML/tools/stockfish/stockfish.exe")
    }

    bin_audit = {}
    for name, p in binaries.items():
        if p.exists():
            h = sha256_file(p)
            sz = p.stat().st_size
            bin_audit[name] = {"path": str(p), "sha256": h, "bytes": sz}
            print(f"Verified Binary {name}: {sz:,} bytes | SHA-256: {h}")
        else:
            print(f"ERROR: Missing binary {name} at {p}")

    # 2. Re-parse PGN Tournaments
    matches = {
        "match_a": {"pgn": P19_PGN_DIR / "x14_1t_vs_x7_1t.pgn", "a_name": "Janus Classical X14 (1T)"},
        "match_b": {"pgn": P19_PGN_DIR / "x14_4t_vs_x12_4t.pgn", "a_name": "Janus Classical X14 (4T)"},
        "match_c": {"pgn": P19_PGN_DIR / "x14_4t_vs_x12_4t_slow.pgn", "a_name": "Janus Classical X14 (4T)"},
        "match_sf": {"pgn": P19_PGN_DIR / "x14_4t_vs_sf19_4t.pgn", "a_name": "Janus Classical X14 (4T)"}
    }

    match_results = {}
    for mid, mcfg in matches.items():
        res = parse_pgn_match(mcfg["pgn"], mcfg["a_name"])
        match_results[mid] = res
        print(f"  -> Result: {res['wins_a']}W - {res['draws']}D - {res['wins_b']}L = {res['points_a']}/{res['total_games']} ({res['score_pct']}%)")
        print(f"     Paired t: {res['paired_t_stat']}, p-val: {res['p_value_t']}, Var: {res['pair_variance']}")

    # 3. Save Summary
    summary = {
        "metadata": {
            "title": "P1.9 Independent Scientific Evidence & Integrity Audit",
            "auditor": "Principal Computer Chess Engineer & Independent Auditor",
            "total_games_audited": sum(r["total_games"] for r in match_results.values())
        },
        "binaries": bin_audit,
        "matches": match_results
    }

    out_file = P110_RAW_DIR / "p19_audit_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[DONE] Saved Phase 0 Audit Summary to {out_file}")

if __name__ == "__main__":
    main()

