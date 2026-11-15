#!/usr/bin/env python3
"""
reconcile_p120.py
Independent statistical audit and scientific reconciliation of Milestone P1.20 deliverables.
Audits all 17 PGN files (950 games total) across Phase 2, Phase 9, and Authoritative Matches 1-8.
"""

import os
import re
import math
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple

ROOT = Path("E:/ChessXML/project-janus-phase1")
P120_PGN_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "pgn"
P120_RAW_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
OUT_DIR = ROOT / "analysis" / "phase1" / "p1.21" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def parse_pgn_games(pgn_path: Path) -> List[Dict[str, Any]]:
    games = []
    current_headers = {}
    current_moves = []
    
    with open(pgn_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                m = re.match(r'\[(\w+)\s+"(.*)"\]', line)
                if m:
                    current_headers[m.group(1)] = m.group(2)
            else:
                # Move line or termination
                if "Result" in current_headers and ("1-0" in line or "0-1" in line or "1/2-1/2" in line or "*" in line):
                    current_moves.append(line)
                    # End of game
                    games.append({
                        "headers": current_headers.copy(),
                        "moves": " ".join(current_moves),
                        "result": current_headers.get("Result", "*"),
                        "white": current_headers.get("White", ""),
                        "black": current_headers.get("Black", ""),
                        "round": current_headers.get("Round", ""),
                        "event": current_headers.get("Event", "")
                    })
                    current_headers = {}
                    current_moves = []
                else:
                    current_moves.append(line)
                    
    # Handle any trailing game
    if "Result" in current_headers:
        games.append({
            "headers": current_headers.copy(),
            "moves": " ".join(current_moves),
            "result": current_headers.get("Result", "*"),
            "white": current_headers.get("White", ""),
            "black": current_headers.get("Black", ""),
            "round": current_headers.get("Round", ""),
            "event": current_headers.get("Event", "")
        })
        
    return games

def calc_elo(p: float) -> Any:
    if p <= 0.00001:
        return "-inf"
    if p >= 0.99999:
        return "+inf"
    return -400.0 * math.log10(1.0 / p - 1.0)

def audit_pgn_group(pgn_name: str, cand_name: str, ref_name: str) -> Dict[str, Any]:
    pgn_path = P120_PGN_DIR / pgn_name
    games = parse_pgn_games(pgn_path)
    total_games = len(games)
    
    # Process paired games
    pairs = []
    wins = 0
    draws = 0
    losses = 0
    
    # Each opening pair has 2 games: game 1 where Cand is White/Black, game 2 inverted
    num_pairs = total_games // 2
    pentanomial = [0, 0, 0, 0, 0] # [2.0, 1.5, 1.0, 0.5, 0.0] points per pair for candidate
    pair_scores = []
    
    for p in range(num_pairs):
        g1 = games[2 * p]
        g2 = games[2 * p + 1]
        
        # Determine score of g1 for candidate
        s1 = 0.0
        if cand_name in g1["white"]:
            if g1["result"] == "1-0": s1 = 1.0
            elif g1["result"] == "1/2-1/2": s1 = 0.5
            else: s1 = 0.0
        else:
            if g1["result"] == "0-1": s1 = 1.0
            elif g1["result"] == "1/2-1/2": s1 = 0.5
            else: s1 = 0.0
            
        # Determine score of g2 for candidate
        s2 = 0.0
        if cand_name in g2["white"]:
            if g2["result"] == "1-0": s2 = 1.0
            elif g2["result"] == "1/2-1/2": s2 = 0.5
            else: s2 = 0.0
        else:
            if g2["result"] == "0-1": s2 = 1.0
            elif g2["result"] == "1/2-1/2": s2 = 0.5
            else: s2 = 0.0
            
        pair_pts = s1 + s2
        pair_scores.append(pair_pts / 2.0)
        
        if pair_pts == 2.0: pentanomial[0] += 1
        elif pair_pts == 1.5: pentanomial[1] += 1
        elif pair_pts == 1.0: pentanomial[2] += 1
        elif pair_pts == 0.5: pentanomial[3] += 1
        elif pair_pts == 0.0: pentanomial[4] += 1
        
        for s in (s1, s2):
            if s == 1.0: wins += 1
            elif s == 0.5: draws += 1
            else: losses += 1
            
    cand_pts = wins + 0.5 * draws
    score_pct = (cand_pts / total_games) * 100.0 if total_games > 0 else 0.0
    elo = calc_elo(cand_pts / total_games) if total_games > 0 else 0.0
    
    # Paired confidence interval and two-sided p-value against H0: mu = 0.5
    mean_p = sum(pair_scores) / num_pairs if num_pairs > 0 else 0.0
    var_p = sum((x - mean_p) ** 2 for x in pair_scores) / (num_pairs - 1) if num_pairs > 1 else 0.0
    se = math.sqrt(var_p / num_pairs) if num_pairs > 0 else 0.0
    
    ci_low = max(0.0, mean_p - 1.95996 * se)
    ci_high = min(1.0, mean_p + 1.95996 * se)
    
    t_stat = (mean_p - 0.5) / se if se > 1e-7 else 0.0
    p2 = math.erfc(abs(t_stat) / math.sqrt(2.0))
    
    # Also compute Wilson score interval for raw proportion (especially for 0-score matches)
    z = 1.95996
    n = total_games
    p_hat = cand_pts / n if n > 0 else 0.0
    wilson_denom = 1.0 + z*z / n
    wilson_center = (p_hat + z*z / (2.0 * n)) / wilson_denom
    wilson_half = (z * math.sqrt(p_hat * (1.0 - p_hat) / n + z*z / (4.0 * n * n))) / wilson_denom
    wilson_low = max(0.0, wilson_center - wilson_half)
    wilson_high = min(1.0, wilson_center + wilson_half)
    
    return {
        "pgn_name": pgn_name,
        "candidate": cand_name,
        "reference": ref_name,
        "total_games": total_games,
        "opening_pairs": num_pairs,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": cand_pts,
        "score_pct": round(score_pct, 2),
        "elo": round(elo, 1) if isinstance(elo, float) else elo,
        "pentanomial": pentanomial,
        "mean_pair_score": round(mean_p, 4),
        "standard_error": round(se, 4),
        "ci_low": round(ci_low * 100.0, 2),
        "ci_high": round(ci_high * 100.0, 2),
        "wilson_ci_low": round(wilson_low * 100.0, 2),
        "wilson_ci_high": round(wilson_high * 100.0, 2),
        "t_stat": round(t_stat, 4),
        "p_value": round(p2, 6)
    }

def main():
    print("Executing Milestone P1.20 Scientific Reconciliation...")
    
    # Define all 17 PGN files and candidate/reference assignments
    pgn_configs = [
        # Phase 2: Factorial Battery (300 games)
        ("p120_t1_x24_vs_x22_fast.pgn", "X24", "X22", "Phase 2 T1 Fast (1.0s+50ms)"),
        ("p120_t1_x24_vs_x22_slow.pgn", "X24", "X22", "Phase 2 T1 Slow (3.0s+100ms)"),
        ("p120_t2_x24_vs_x7_fast.pgn", "X24", "X7", "Phase 2 T2 Fast (1.0s+50ms)"),
        ("p120_t2_x24_vs_x7_slow.pgn", "X24", "X7", "Phase 2 T2 Slow (3.0s+100ms)"),
        ("p120_t3_x22_vs_x7_fast.pgn", "X22", "X7", "Phase 2 T3 Fast (1.0s+50ms)"),
        ("p120_t3_x22_vs_x7_slow.pgn", "X22", "X7", "Phase 2 T3 Slow (3.0s+100ms)"),
        
        # Phase 9: Development Ablations (150 games)
        ("p120_dev_m1_b1_vs_b0_fast.pgn", "B1_Connected", "B0_Ref", "Phase 9 Dev M1 Fast (1.0s+50ms)"),
        ("p120_dev_m2_b1_vs_b0_slow.pgn", "B1_Connected", "B0_Ref", "Phase 9 Dev M2 Slow (3.0s+100ms)"),
        ("p120_dev_m3_b1_vs_b2_fast.pgn", "B1_Connected", "B2_BP", "Phase 9 Dev M3 Fast (1.0s+50ms)"),
        
        # Authoritative Matches 1-8 (500 games)
        ("p120_match_1_x25-s_vs_x22-s_fast.pgn", "X25", "X22", "Match 1: X25-S vs X22-S Fast"),
        ("p120_match_2_x25-s_vs_x22-s_slow.pgn", "X25", "X22", "Match 2: X25-S vs X22-S Slow"),
        ("p120_match_3_x25-s_vs_x7_fast.pgn", "X25", "X7", "Match 3: X25-S vs X7 Fast"),
        ("p120_match_4_x25-p_vs_x12_fast.pgn", "X25", "X12", "Match 4: X25-P vs X12 Fast (4T)"),
        ("p120_match_5_x25-s_vs_x7_slow.pgn", "X25", "X7", "Match 5: X25-S vs X7 Slow"),
        ("p120_match_6_x25-s_vs_sf4.pgn", "X25", "Stockfish 4", "Match 6: X25-S vs Stockfish 4"),
        ("p120_match_7_x25-s_vs_sf11.pgn", "X25", "Stockfish 11", "Match 7: X25-S vs Stockfish 11"),
        ("p120_match_8_x25-s_vs_sf19.pgn", "X25", "Stockfish 19", "Match 8: X25-S vs Stockfish 19 NNUE"),
    ]
    
    results = {}
    total_reconstructed_games = 0
    
    for pgn_file, cand, ref, label in pgn_configs:
        res = audit_pgn_group(pgn_file, cand, ref)
        res["label"] = label
        results[pgn_file] = res
        total_reconstructed_games += res["total_games"]
        print(f"[{label}] {res['points']}/{res['total_games']} (+{res['wins']} ={res['draws']} -{res['losses']}) | {res['score_pct']}% | Elo: {res['elo']} | CI: [{res['ci_low']}%, {res['ci_high']}%] | p: {res['p_value']}")
        
    print(f"\nTotal independently reconstructed games: {total_reconstructed_games}")
    
    # Save raw audit summary
    summary_path = OUT_DIR / "p120_scientific_reconciliation_audit.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Reconciliation summary written to {summary_path}")

if __name__ == "__main__":
    main()
