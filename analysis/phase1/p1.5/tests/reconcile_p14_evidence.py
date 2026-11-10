import json
import math
import os
import re

def elo_diff(score_frac):
    if score_frac <= 0.0:
        return -800.0
    if score_frac >= 1.0:
        return 800.0
    return -400.0 * math.log10((1.0 - score_frac) / score_frac)

def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def t_distribution_pvalue(t_val, df):
    p_norm = 2.0 * (1.0 - normal_cdf(abs(t_val)))
    return p_norm

def paired_t_test(pair_diffs):
    n = len(pair_diffs)
    mean_d = sum(pair_diffs) / n
    variance = sum((d - mean_d) ** 2 for d in pair_diffs) / (n - 1)
    se = math.sqrt(variance / n) if variance > 0 else 1e-9
    t_val = mean_d / se
    p_val = t_distribution_pvalue(t_val, n - 1)
    return mean_d, se, t_val, p_val

def audit():
    results = {}

    # 1. Audit X8 vs X7 (P1.3)
    p13_raw_path = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.3/raw/x8_vs_x7_tournament_raw.json"
    with open(p13_raw_path, 'r', encoding='utf-8') as f:
        p13_raw = json.load(f)
    
    x8_wins = p13_raw['a_wins']
    x8_draws = p13_raw['draws']
    x8_losses = p13_raw['b_wins']
    total_x8 = p13_raw['a_points']
    n_games_8 = p13_raw['total_games']
    
    diffs_x8 = []
    for pr in p13_raw['pair_results']:
        a_score = pr['a_score'] # out of 2.0
        b_score = 2.0 - a_score
        diffs_x8.append(a_score - b_score)
    
    mean_d8, se8, t8, p8 = paired_t_test(diffs_x8)
    ci8_lower_score = (total_x8 / n_games_8) - 1.96 * (se8 / 2.0)
    ci8_upper_score = (total_x8 / n_games_8) + 1.96 * (se8 / 2.0)

    results['x8_vs_x7'] = {
        'total_games': n_games_8,
        'pairs': len(diffs_x8),
        'record': f"{x8_wins}W - {x8_draws}D - {x8_losses}L",
        'score': total_x8,
        'percentage': total_x8 / n_games_8,
        'elo_delta': elo_diff(total_x8 / n_games_8),
        'elo_ci_95': [elo_diff(ci8_lower_score), elo_diff(ci8_upper_score)],
        'paired_t': t8,
        'paired_p': p8,
        'statistically_significant_regression': bool(p8 < 0.05 and t8 < 0)
    }

    # 2. Audit X9 vs X7 (P1.4)
    p14_raw_path = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.4/raw/x9_vs_x7_tournament_raw.json"
    with open(p14_raw_path, 'r', encoding='utf-8') as f:
        p14_raw = json.load(f)
    
    x9_wins = p14_raw['a_wins']
    x9_draws = p14_raw['draws']
    x9_losses = p14_raw['b_wins']
    total_x9 = p14_raw['a_points']
    n_games_9 = p14_raw['total_games']
    
    diffs_x9 = []
    for pr in p14_raw['pair_results']:
        a_score = pr['a_score']
        b_score = 2.0 - a_score
        diffs_x9.append(a_score - b_score)
    
    mean_d9, se9, t9, p9 = paired_t_test(diffs_x9)
    ci9_lower_score = (total_x9 / n_games_9) - 1.96 * (se9 / 2.0)
    ci9_upper_score = (total_x9 / n_games_9) + 1.96 * (se9 / 2.0)

    results['x9_vs_x7'] = {
        'total_games': n_games_9,
        'pairs': len(diffs_x9),
        'record': f"{x9_wins}W - {x9_draws}D - {x9_losses}L",
        'score': total_x9,
        'percentage': total_x9 / n_games_9,
        'elo_delta': elo_diff(total_x9 / n_games_9),
        'elo_ci_95': [elo_diff(ci9_lower_score), elo_diff(ci9_upper_score)],
        'paired_t': t9,
        'paired_p': p9,
        'statistically_distinguishable': bool(p9 < 0.05)
    }

    # 3. Audit Matched Stockfish 19 Progress
    sf_raw_path = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.4/raw/matched_stockfish19_progress_raw.json"
    with open(sf_raw_path, 'r', encoding='utf-8') as f:
        sf_raw = json.load(f)
    
    d_x7 = sf_raw['x7_vs_sf19']
    d_x9 = sf_raw['x9_vs_sf19']
    
    results['x7_vs_stockfish19'] = {
        'total_games': d_x7['total_games'],
        'record': f"{d_x7['a_wins']}W - {d_x7['draws']}D - {d_x7['b_wins']}L",
        'score': d_x7['a_points'],
        'percentage': d_x7['a_points'] / d_x7['total_games'],
        'elo_delta': d_x7['clustered_elo'],
        'elo_ci_95': d_x7['clustered_elo_95']
    }

    results['x9_vs_stockfish19'] = {
        'total_games': d_x9['total_games'],
        'record': f"{d_x9['a_wins']}W - {d_x9['draws']}D - {d_x9['b_wins']}L",
        'score': d_x9['a_points'],
        'percentage': d_x9['a_points'] / d_x9['total_games'],
        'elo_delta': d_x9['clustered_elo'],
        'elo_ci_95': d_x9['clustered_elo_95']
    }

    out_path = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.5/raw/p14_evidence_reconciliation.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print("Reconciliation results written to", out_path)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    audit()
