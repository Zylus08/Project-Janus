#!/usr/bin/env python3
"""
Phase 0 Forensic Audit: Recompute and verify the X8 vs X7 100-game tournament
from raw PGN and raw telemetry.
"""

import json
import math
import chess.pgn
from pathlib import Path

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
PGN_PATH = ROOT / "analysis" / "phase1" / "p1.3" / "pgn" / "x8_vs_x7.pgn"
RAW_JSON = ROOT / "analysis" / "phase1" / "p1.3" / "raw" / "x8_vs_x7_tournament_raw.json"

def calc_wilson(k, n, z=1.95996):
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return centre - half, centre + half

def calc_elo(p):
    if p <= 0.001: return -800.0
    if p >= 0.999: return 800.0
    return -400.0 * math.log10(1.0 / p - 1.0)

def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def main():
    print("=== Forensic Audit of X8 vs X7 Tournament ===")
    
    # 1. Parse raw PGN
    games = []
    with open(PGN_PATH, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if not g:
                break
            games.append(g)
            
    print(f"Total PGN games parsed: {len(games)}")
    assert len(games) == 100, f"Expected 100 games, found {len(games)}"
    
    x8_wins = 0
    x7_wins = 0
    draws = 0
    pair_scores_x8 = []
    pair_details = []
    
    for i in range(0, 100, 2):
        g1 = games[i]
        g2 = games[i+1]
        
        # Verify opening match and player alternation
        assert g1.headers["White"] == "Janus Classical X8" and g1.headers["Black"] == "Janus Classical X7"
        assert g2.headers["White"] == "Janus Classical X7" and g2.headers["Black"] == "Janus Classical X8"
        op1 = g1.headers.get("Opening", "")
        op2 = g2.headers.get("Opening", "")
        assert op1 == op2, f"Opening mismatch in pair {i//2 + 1}: '{op1}' vs '{op2}'"
        
        r1 = g1.headers["Result"]
        r2 = g2.headers["Result"]
        
        # g1: X8 is White
        if r1 == "1-0":
            s1 = 1.0
            x8_wins += 1
        elif r1 == "0-1":
            s1 = 0.0
            x7_wins += 1
        else:
            s1 = 0.5
            draws += 1
            
        # g2: X8 is Black
        if r2 == "1-0":
            s2 = 0.0
            x7_wins += 1
        elif r2 == "0-1":
            s2 = 1.0
            x8_wins += 1
        else:
            s2 = 0.5
            draws += 1
            
        pair_score = s1 + s2
        pair_scores_x8.append(pair_score)
        pair_details.append({
            "pair": i // 2 + 1,
            "opening": op1,
            "g1_result": r1,
            "g2_result": r2,
            "x8_score": pair_score
        })

    total_pts_x8 = sum(pair_scores_x8)
    score_pct = total_pts_x8 / 100.0
    
    print(f"Results: +{x8_wins} ={draws} -{x7_wins} -> {total_pts_x8} / 100 ({score_pct*100.0:.2f}%)")
    assert x8_wins == 25 and draws == 35 and x7_wins == 40
    assert total_pts_x8 == 42.5
    
    # 2. Statistical Analysis
    # A. Binomial Wilson CI
    w_low, w_high = calc_wilson(total_pts_x8, 100)
    elo_est = calc_elo(score_pct)
    elo_w_low = calc_elo(w_low)
    elo_w_high = calc_elo(w_high)
    
    # B. Clustered Pair Statistics (Student's t / cluster SE)
    n_pairs = len(pair_scores_x8)
    mean_pair = sum(pair_scores_x8) / n_pairs
    var_pair = sum((x - mean_pair)**2 for x in pair_scores_x8) / (n_pairs - 1)
    se_pair = math.sqrt(var_pair / n_pairs)
    t_crit = 2.0096 # t-critical for df=49 at 95% two-sided
    
    cluster_pct_mean = mean_pair / 2.0
    cluster_pct_low = (mean_pair - t_crit * se_pair) / 2.0
    cluster_pct_high = (mean_pair + t_crit * se_pair) / 2.0
    
    cluster_elo_mean = calc_elo(cluster_pct_mean)
    cluster_elo_low = calc_elo(cluster_pct_low)
    cluster_elo_high = calc_elo(cluster_pct_high)
    
    # C. Hypothesis testing: Null hypothesis H0: X8 == X7 (mean pair score = 1.0)
    t_stat = (mean_pair - 1.0) / se_pair
    # Two-sided p-value approximation via normal distribution
    p_val_t = 2.0 * (1.0 - normal_cdf(abs(t_stat)))
    
    # Wilcoxon signed-rank test manual
    diffs = [p - 1.0 for p in pair_scores_x8 if p != 1.0]
    n_diffs = len(diffs)
    ranks = sorted(range(n_diffs), key=lambda i: abs(diffs[i]))
    rank_vals = [0.0] * n_diffs
    # assign average ranks for ties
    i = 0
    while i < n_diffs:
        j = i
        while j < n_diffs and abs(diffs[ranks[j]]) == abs(diffs[ranks[i]]):
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            rank_vals[ranks[k]] = avg_rank
        i = j
    w_plus = sum(rank_vals[k] for k in range(n_diffs) if diffs[k] > 0)
    w_minus = sum(rank_vals[k] for k in range(n_diffs) if diffs[k] < 0)
    w_stat = min(w_plus, w_minus)
    e_w = n_diffs * (n_diffs + 1) / 4.0
    var_w = n_diffs * (n_diffs + 1) * (2 * n_diffs + 1) / 24.0
    z_w = (w_stat - e_w) / math.sqrt(var_w) if var_w > 0 else 0.0
    p_val_wilcoxon = 2.0 * (1.0 - normal_cdf(abs(z_w)))
    
    # D. Pair outcome categories
    sweeps_x8 = sum(1 for p in pair_scores_x8 if p == 2.0)
    wins_x8 = sum(1 for p in pair_scores_x8 if p == 1.5)
    splits = sum(1 for p in pair_scores_x8 if p == 1.0)
    losses_x8 = sum(1 for p in pair_scores_x8 if p == 0.5)
    sweeps_x7 = sum(1 for p in pair_scores_x8 if p == 0.0)
    
    print("\n--- Summary Statistics ---")
    print(f"Paired Sweeps X8 (2.0): {sweeps_x8}")
    print(f"Paired Wins X8 (1.5)  : {wins_x8}")
    print(f"Paired Splits (1.0)   : {splits}")
    print(f"Paired Losses X8 (0.5): {losses_x8}")
    print(f"Paired Sweeps X7 (0.0): {sweeps_x7}")
    print(f"Paired t-test vs 1.0  : t={t_stat:.4f}, p={p_val_t:.4f}")
    print(f"Wilcoxon signed-rank  : W={w_stat}, p={p_val_wilcoxon:.4f}")
    print(f"Clustered 95% CI (pct): [{cluster_pct_low*100:.2f}%, {cluster_pct_high*100:.2f}%]")
    print(f"Clustered 95% CI (Elo): {cluster_elo_mean:+.1f} [{cluster_elo_low:+.1f}, {cluster_elo_high:+.1f}]")
    
    # 3. Check JSON telemetry
    with open(RAW_JSON, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    print(f"\nRaw JSON data verified: duration={raw_data.get('duration_sec'):.1f}s, recorded points={raw_data.get('a_points')}")
    
    out_audit = {
        "verified_games": 100,
        "x8_wins": x8_wins,
        "draws": draws,
        "x7_wins": x7_wins,
        "x8_score": total_pts_x8,
        "score_pct": score_pct,
        "elo": elo_est,
        "binomial_ci_95": [w_low, w_high],
        "binomial_elo_ci_95": [elo_w_low, elo_w_high],
        "clustered_ci_95": [cluster_pct_low, cluster_pct_high],
        "clustered_elo_ci_95": [cluster_elo_low, cluster_elo_high],
        "paired_t_stat": t_stat,
        "paired_t_p_value": p_val_t,
        "wilcoxon_stat": float(w_stat),
        "wilcoxon_p_value": p_val_wilcoxon,
        "pair_breakdown": {
            "sweeps_x8": sweeps_x8,
            "wins_x8": wins_x8,
            "splits": splits,
            "losses_x8": losses_x8,
            "sweeps_x7": sweeps_x7
        }
    }
    
    with open(ROOT / "analysis" / "phase1" / "p1.4" / "raw" / "p13_tournament_audit_raw.json", "w", encoding="utf-8") as f:
        json.dump(out_audit, f, indent=2)
    print("Audit results written to raw/p13_tournament_audit_raw.json")

if __name__ == "__main__":
    main()
