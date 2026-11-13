#!/usr/bin/env python3
"""
audit_p112_reconciliation.py
Phase 0 Forensic Audit & Statistical Reconciliation of P1.12 Tournament Datasets
Project Janus — Phase 1, Milestone P1.13
"""

import os
import sys
import json
import math
import chess.pgn

def wilson_score_interval(k, n, confidence=0.95):
    if n == 0:
        return (0.0, 0.0)
    z = 1.959963984540054  # 95% two-sided
    p_hat = k / n
    denom = 1.0 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    spread = (z * math.sqrt((p_hat * (1 - p_hat) + (z**2) / (4 * n)) / n)) / denom
    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return (lower, upper)

def clopper_pearson_upper(k, n, confidence=0.95):
    # For k=0: upper bound = 1 - (1 - conf)^(1/n) = 1 - (0.05)^(1/n)
    if k == 0 and n > 0:
        return 1.0 - (1.0 - confidence) ** (1.0 / n)
    return None

def elo_from_score(score_fraction):
    if score_fraction <= 0.0:
        return -float('inf')
    if score_fraction >= 1.0:
        return float('inf')
    return -400.0 * math.log10(1.0 / score_fraction - 1.0)

def audit_pgn_file(fpath):
    games = []
    with open(fpath, 'r', encoding='utf-8') as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            white = game.headers.get("White", "Unknown")
            black = game.headers.get("Black", "Unknown")
            res = game.headers.get("Result", "*")
            eco = game.headers.get("ECO", "")
            opening = game.headers.get("Opening", "")
            fen = game.headers.get("FEN", "")
            games.append({
                "white": white,
                "black": black,
                "result": res,
                "eco": eco,
                "opening": opening,
                "fen": fen
            })
    return games

def analyze_match(fname, games, engine_focus="Janus"):
    total = len(games)
    wins = 0
    draws = 0
    losses = 0
    
    for g in games:
        res = g["result"]
        w = g["white"]
        b = g["black"]
        is_focus_white = engine_focus.lower() in w.lower()
        is_focus_black = engine_focus.lower() in b.lower()
        
        if res == "1-0":
            if is_focus_white:
                wins += 1
            else:
                losses += 1
        elif res == "0-1":
            if is_focus_black:
                wins += 1
            else:
                losses += 1
        elif res == "1/2-1/2":
            draws += 1
        else:
            # unfinished
            pass
            
    score = wins + 0.5 * draws
    score_frac = score / total if total > 0 else 0.0
    w_low, w_high = wilson_score_interval(score, total)
    cp_upper = clopper_pearson_upper(wins + draws, total) if score == 0 else None
    
    elo = elo_from_score(score_frac)
    elo_low = elo_from_score(w_low) if w_low > 0 else -float('inf')
    elo_high = elo_from_score(w_high) if w_high < 1 else float('inf')
    
    # Opening pairs (consecutive 2 games: even idx white, odd idx black)
    pairs_count = total // 2
    pentanomial = {"WW": 0, "WD": 0, "DD_WL": 0, "LD": 0, "LL": 0}
    for i in range(pairs_count):
        g1 = games[2 * i]
        g2 = games[2 * i + 1]
        
        # calculate points for focus in g1 and g2
        def get_pts(g):
            w = g["white"]
            r = g["result"]
            fw = engine_focus.lower() in w.lower()
            if r == "1-0": return 1.0 if fw else 0.0
            if r == "0-1": return 0.0 if fw else 1.0
            if r == "1/2-1/2": return 0.5
            return 0.5
            
        pts = get_pts(g1) + get_pts(g2)
        if pts == 2.0:
            pentanomial["WW"] += 1
        elif pts == 1.5:
            pentanomial["WD"] += 1
        elif pts == 1.0:
            pentanomial["DD_WL"] += 1
        elif pts == 0.5:
            pentanomial["LD"] += 1
        elif pts == 0.0:
            pentanomial["LL"] += 1

    return {
        "file": fname,
        "total_games": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": score,
        "score_pct": score_frac * 100.0,
        "wilson_ci_pct": (w_low * 100.0, w_high * 100.0),
        "clopper_pearson_upper_pct": cp_upper * 100.0 if cp_upper else None,
        "elo": elo,
        "elo_ci": (elo_low, elo_high),
        "pairs_count": pairs_count,
        "pentanomial": pentanomial
    }

def main():
    pgn_dir = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.12\pgn"
    files = [
        ("x17_1t_vs_x7_1t.pgn", "X17"),
        ("x17_1t_vs_x7_1t_slow.pgn", "X17"),
        ("x17_4t_vs_x12_4t.pgn", "X17"),
        ("x17_1t_vs_sf11_1t.pgn", "X17"),
        ("x17_4t_vs_sf11_4t.pgn", "X17"),
        ("x17_1t_vs_sf19_1t.pgn", "X17"),
        ("x17_4t_vs_sf19_4t.pgn", "X17"),
    ]
    
    results = []
    total_games_all = 0
    print("================================================================================")
    print("PHASE 0: P1.12 TOURNAMENT AUDIT & RECONCILIATION")
    print("================================================================================")
    
    for fname, focus in files:
        fpath = os.path.join(pgn_dir, fname)
        if not os.path.exists(fpath):
            print(f"ERROR: Missing file {fpath}")
            continue
        games = audit_pgn_file(fpath)
        stats = analyze_match(fname, games, focus)
        results.append(stats)
        total_games_all += stats["total_games"]
        
        print(f"File: {fname}")
        print(f"  Total Games: {stats['total_games']}")
        print(f"  Score: +{stats['wins']} ={stats['draws']} -{stats['losses']} ({stats['points']}/{stats['total_games']} = {stats['score_pct']:.2f}%)")
        print(f"  Wilson 95% CI: [{stats['wilson_ci_pct'][0]:.2f}%, {stats['wilson_ci_pct'][1]:.2f}%]")
        if stats['clopper_pearson_upper_pct'] is not None:
            print(f"  Clopper-Pearson 95% Upper Bound: {stats['clopper_pearson_upper_pct']:.2f}%")
        print(f"  Elo: {stats['elo']:.1f} (95% CI: [{stats['elo_ci'][0]:.1f}, {stats['elo_ci'][1]:.1f}])")
        print(f"  Pentanomial: {stats['pentanomial']}")
        print()

    print("================================================================================")
    print(f"TOTAL AUDITED GAMES ACROSS ALL ARCHIVES: {total_games_all}")
    print("================================================================================")
    
    # Save to json
    out_json = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.13\raw\p112_audit_reconciliation.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_games": total_games_all,
            "matches": results
        }, f, indent=2)
    print(f"Saved audit results to {out_json}")

if __name__ == "__main__":
    main()

