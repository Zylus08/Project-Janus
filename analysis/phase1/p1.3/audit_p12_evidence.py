#!/usr/bin/env python3
"""
Project Janus — Milestone P1.3 Phase 0 Forensic Audit Script
Audits:
  1. Tournament 1 (X7 vs X6) PGN and raw telemetry, pair-by-pair score reconciliation.
  2. Dynamic LMR activation analysis across L0, L1, L2, L3.
  3. External benchmark comparisons (X6 vs SF19 in P1.1 vs X7 vs SF19 in P1.2).
"""

import json
import math
from pathlib import Path
import chess.pgn
import io

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
P12_RAW = ROOT / "analysis" / "phase1" / "p1.2" / "raw"
P12_PGN = ROOT / "analysis" / "phase1" / "p1.2" / "pgn"
P11_RAW = ROOT / "analysis" / "phase1" / "p1.1" / "raw"

def audit_tournament_accounting():
    print("=== PART A: TOURNAMENT ACCOUNTING AUDIT (X7 vs X6) ===")
    json_path = P12_RAW / "x7_vs_x6_tournament_raw.json"
    pgn_path = P12_PGN / "x7_vs_x6.pgn"
    
    with open(json_path, "r", encoding="utf-8") as f:
        t_data = json.load(f)
        
    print(f"Reported in JSON:")
    print(f"  Total games: {t_data['total_games']}")
    print(f"  Pairs count: {t_data['pairs_count']}")
    print(f"  X7 Wins: {t_data['a_wins']}, Draws: {t_data['draws']}, X6 Wins: {t_data['b_wins']}")
    print(f"  Points: {t_data['a_points']} / {t_data['total_games']} ({t_data['score_pct']*100:.2f}%)")
    
    # Audit pair_results from JSON
    pair_results = t_data["pair_results"]
    pair_scores = [pr["a_score"] for pr in pair_results]
    print(f"\nAudit of pair_results list in JSON ({len(pair_results)} pairs):")
    pair_buckets = {2.0: 0, 1.5: 0, 1.0: 0, 0.5: 0, 0.0: 0}
    sum_pair_pts = 0.0
    for ps in pair_scores:
        sum_pair_pts += ps
        pair_buckets[ps] = pair_buckets.get(ps, 0) + 1
        
    for score_val in [2.0, 1.5, 1.0, 0.5, 0.0]:
        print(f"  Pairs with {score_val} pts: {pair_buckets.get(score_val, 0)}")
    print(f"  Sum of pair points: {sum_pair_pts:.1f}")
    
    # Audit PGN directly
    print("\nParsing PGN directly:")
    with open(pgn_path, "r", encoding="utf-8") as f:
        pgn_text = f.read()
        
    pgn_io = io.StringIO(pgn_text)
    game_idx = 0
    pgn_w7, pgn_w6, pgn_dr = 0, 0, 0
    pgn_pairs = []
    
    curr_pair = {}
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        game_idx += 1
        white = game.headers.get("White", "")
        black = game.headers.get("Black", "")
        result = game.headers.get("Result", "*")
        
        is_x7_white = ("X7" in white)
        if result == "1-0":
            if is_x7_white:
                pgn_w7 += 1
                g_score = 1.0
            else:
                pgn_w6 += 1
                g_score = 0.0
        elif result == "0-1":
            if is_x7_white:
                pgn_w6 += 1
                g_score = 0.0
            else:
                pgn_w7 += 1
                g_score = 1.0
        elif result == "1/2-1/2":
            pgn_dr += 1
            g_score = 0.5
        else:
            g_score = 0.0
            
        if game_idx % 2 == 1:
            curr_pair = {"g1_res": result, "g1_pts": g_score}
        else:
            curr_pair["g2_res"] = result
            curr_pair["g2_pts"] = g_score
            curr_pair["tot_pts"] = curr_pair["g1_pts"] + curr_pair["g2_pts"]
            pgn_pairs.append(curr_pair)
            curr_pair = {}
            
    print(f"  Total games parsed from PGN: {game_idx}")
    print(f"  PGN WDL: X7 Wins: {pgn_w7}, Draws: {pgn_dr}, X6 Wins: {pgn_w6}")
    pgn_total_pts = pgn_w7 + 0.5 * pgn_dr
    print(f"  PGN Total Points: {pgn_total_pts} / {game_idx} ({pgn_total_pts / game_idx * 100:.2f}%)")
    
    pgn_buckets = {2.0: 0, 1.5: 0, 1.0: 0, 0.5: 0, 0.0: 0}
    for p in pgn_pairs:
        tot = p["tot_pts"]
        pgn_buckets[tot] = pgn_buckets.get(tot, 0) + 1
        
    print(f"\nPGN Exact Pair Distribution ({len(pgn_pairs)} pairs):")
    pgn_pair_sum = 0.0
    for score_val in [2.0, 1.5, 1.0, 0.5, 0.0]:
        cnt = pgn_buckets.get(score_val, 0)
        pts = cnt * score_val
        pgn_pair_sum += pts
        print(f"  {score_val} pts: {cnt:2d} pairs ({pts:4.1f} pts)")
    print(f"  Sum of PGN pair points: {pgn_pair_sum:.1f}")

def audit_dynamic_lmr():
    print("\n=== PART B: DYNAMIC LMR ACTIVATION AUDIT ===")
    json_path = P12_RAW / "dynamic_lmr_raw.json"
    with open(json_path, "r", encoding="utf-8") as f:
        lmr_data = json.load(f)
        
    for k in ["L0", "L1", "L2", "L3"]:
        info = lmr_data[k]
        print(f"Mode {k} ({info['label']}):")
        print(f"  Total Nodes: {info['total_nodes']:,}")
        print(f"  Reductions reported: {info['total_reduced']:,}")
        print(f"  FMC Rate: {info['fmc_rate_pct']:.2f}%")
        print(f"  Wall Time: {info['elapsed_wall_sec']:.2f}s")

def audit_stockfish_comparison():
    print("\n=== PART C: STOCKFISH COMPARISON AUDIT ===")
    p11_sf_path = P11_RAW / "janus_x_vs_sf19_diagnostic_raw.json"
    p12_sf_path = P12_RAW / "matched_sf19_progress_raw.json"
    
    if p11_sf_path.exists():
        with open(p11_sf_path, "r", encoding="utf-8") as f:
            p11_data = json.load(f)
        games = p11_data.get("games", [])
        print(f"P1.1 (X6 vs SF19):")
        print(f"  Games: {len(games)}")
        print(f"  Result: {p11_data.get('score', 'N/A')}")
        w, d, l = 0, 0, 0
        for g in games:
            res = g.get("result", "")
            if "1/2" in res: d += 1
            elif res == "1-0":
                if "Classical" in g.get("white", ""): w += 1
                else: l += 1
            elif res == "0-1":
                if "Classical" in g.get("black", ""): w += 1
                else: l += 1
        print(f"  Parsed: +{w} ={d} -{l}")
        plies_11 = [g.get("plies", 0) for g in games]
        print(f"  Mean plies: {sum(plies_11)/len(plies_11):.1f}")
        print(f"  Openings used (first 3): {[g.get('opening', '') for g in games[:3]]}")
        
    if p12_sf_path.exists():
        with open(p12_sf_path, "r", encoding="utf-8") as f:
            p12_data = json.load(f)
        print(f"\nP1.2 (X7 vs SF19):")
        print(f"  Games: {p12_data.get('total_games', 0)}")
        print(f"  Score: +{p12_data.get('a_wins', 0)} ={p12_data.get('draws', 0)} -{p12_data.get('b_wins', 0)}")
        pairs = p12_data.get("pair_results", [])
        print(f"  Pairs count: {len(pairs)}")
        print(f"  Openings used (first 3): {[p.get('opening', '') for p in pairs[:3]]}")

if __name__ == "__main__":
    audit_tournament_accounting()
    audit_dynamic_lmr()
    audit_stockfish_comparison()

