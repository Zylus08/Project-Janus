import os
import json
import math
from pathlib import Path
import chess
import chess.pgn

P113_PGN_DIR = Path(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.13\pgn")
OUT_RAW = Path(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.14\raw\p113_reconciliation_raw.json")

TOURNAMENT_MATCHES = [
    ("x18_1t_vs_x7_1t", "Janus-X18-1T", "Janus-X7-1T", 100),
    ("x18_1t_vs_x7_1t_slow", "Janus-X18-1T", "Janus-X7-1T", 50),
    ("x18_4t_vs_x12_4t", "Janus-X18-4T", "Janus-X12-4T", 100),
    ("x18_1t_vs_sf4_1t", "Janus-X18-1T", "Stockfish-4-1T", 40),
    ("x18_1t_vs_sf11_1t", "Janus-X18-1T", "Stockfish-11-1T", 40),
    ("x18_1t_vs_sf19_1t", "Janus-X18-1T", "Stockfish-19-1T", 40),
    ("x18_4t_vs_sf19_4t", "Janus-X18-4T", "Stockfish-19-4T", 40),
]

CALIBRATION_MATCHES = [
    ("sf4_1t_vs_sf6_1t", "Stockfish-4-1T", "Stockfish-6-1T", 20),
    ("sf6_1t_vs_sf8_1t", "Stockfish-6-1T", "Stockfish-8-1T", 20),
    ("x7_1t_vs_sf4_1t", "Janus-X7-1T", "Stockfish-4-1T", 20),
    ("x7_1t_vs_sf6_1t", "Janus-X7-1T", "Stockfish-6-1T", 20),
    ("x7_1t_vs_sf8_1t", "Janus-X7-1T", "Stockfish-8-1T", 20),
    ("x12_4t_vs_sf4_4t", "Janus-X12-4T", "Stockfish-4-4T", 20),
]

def calc_wilson(pts, n, z=1.96):
    p = pts / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    spread = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - spread), min(1.0, centre + spread)

def calc_elo(score_pct):
    if score_pct <= 0.0: return None
    if score_pct >= 1.0: return None
    return -400.0 * math.log10(1.0 / score_pct - 1.0)

def parse_pgn_file(pgn_path, eng_a, eng_b, expected_games):
    assert pgn_path.exists(), f"File missing: {pgn_path}"
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if not g:
                break
            games.append(g)
    
    assert len(games) == expected_games, f"Game count mismatch in {pgn_path.name}: {len(games)} vs {expected_games}"
    
    wins_a, draws, losses_a = 0, 0, 0
    crashes, time_forfeits, illegal_moves = 0, 0, 0
    pairs = []
    
    for i in range(0, len(games), 2):
        g1 = games[i]
        g2 = games[i+1]
        
        # Check color reversal
        w1, b1 = g1.headers.get("White"), g1.headers.get("Black")
        w2, b2 = g2.headers.get("White"), g2.headers.get("Black")
        assert (w1 == eng_a and b1 == eng_b and w2 == eng_b and b2 == eng_a) or \
               (w1 == eng_b and b1 == eng_a and w2 == eng_a and b2 == eng_b), f"Pair color inconsistency at {i}"
        
        # Opening check
        op1 = g1.headers.get("Opening")
        op2 = g2.headers.get("Opening")
        eco1 = g1.headers.get("ECO")
        eco2 = g2.headers.get("ECO")
        assert op1 == op2, f"Opening mismatch in pair {i//2}: {op1} != {op2}"
        
        def score_for_a(g):
            w = g.headers.get("White")
            res = g.headers.get("Result")
            term = g.headers.get("Termination", "")
            nonlocal crashes, time_forfeits, illegal_moves
            if "illegal" in term: illegal_moves += 1
            if "forfeit" in term or "time" in term: time_forfeits += 1
            if "crash" in term or "no_move" in term: crashes += 1
            
            if res == "1-0":
                return 1.0 if w == eng_a else 0.0
            elif res == "0-1":
                return 0.0 if w == eng_a else 1.0
            elif res == "1/2-1/2":
                return 0.5
            else:
                raise ValueError(f"Unknown result: {res}")
                
        s1 = score_for_a(g1)
        s2 = score_for_a(g2)
        pair_score = s1 + s2
        pairs.append({
            "pair_index": i // 2,
            "opening": op1,
            "eco": eco1,
            "g1": {"white": w1, "black": b1, "result": g1.headers.get("Result"), "term": g1.headers.get("Termination")},
            "g2": {"white": w2, "black": b2, "result": g2.headers.get("Result"), "term": g2.headers.get("Termination")},
            "pair_score_a": pair_score
        })
        
        for s in (s1, s2):
            if s == 1.0: wins_a += 1
            elif s == 0.5: draws += 1
            elif s == 0.0: losses_a += 1

    # Pentanomial calculation
    pent = {"WW": 0, "WD": 0, "DD_WL": 0, "LD": 0, "LL": 0}
    pair_scores_list = []
    for p in pairs:
        ps = p["pair_score_a"]
        pair_scores_list.append(ps)
        if ps == 2.0: pent["WW"] += 1
        elif ps == 1.5: pent["WD"] += 1
        elif ps == 1.0: pent["DD_WL"] += 1
        elif ps == 0.5: pent["LD"] += 1
        elif ps == 0.0: pent["LL"] += 1

    num_pairs = len(pairs)
    pts_a = wins_a + 0.5 * draws
    score_pct = pts_a / len(games)
    wilson_low, wilson_high = calc_wilson(pts_a, len(games))
    
    # Paired opening awareness:
    # Pair scores are random variables in [0, 2], mean = score_pct * 2
    pair_mean = sum(pair_scores_list) / num_pairs
    pair_var = sum((x - pair_mean)**2 for x in pair_scores_list) / (num_pairs - 1) if num_pairs > 1 else 0.0
    pair_sem = math.sqrt(pair_var / num_pairs)
    # Paired 95% CI on single-game percentage (pair_mean / 2):
    pair_pct_mean = pair_mean / 2.0
    pair_pct_sem = pair_sem / 2.0
    pair_ci_low = max(0.0, pair_pct_mean - 1.96 * pair_pct_sem)
    pair_ci_high = min(1.0, pair_pct_mean + 1.96 * pair_pct_sem)
    
    elo = calc_elo(score_pct)
    elo_pair_low = calc_elo(pair_ci_low) if pair_ci_low > 0 else -float('inf')
    elo_pair_high = calc_elo(pair_ci_high) if pair_ci_high < 1 else float('inf')

    return {
        "match": pgn_path.stem,
        "eng_a": eng_a,
        "eng_b": eng_b,
        "games": len(games),
        "pairs": num_pairs,
        "wins_a": wins_a,
        "draws": draws,
        "losses_a": losses_a,
        "pts_a": pts_a,
        "score_pct": score_pct * 100.0,
        "wilson_ci": (wilson_low * 100.0, wilson_high * 100.0),
        "paired_ci": (pair_ci_low * 100.0, pair_ci_high * 100.0),
        "elo": elo,
        "elo_paired_ci": (elo_pair_low, elo_pair_high),
        "pentanomial": pent,
        "crashes": crashes,
        "time_forfeits": time_forfeits,
        "illegal_moves": illegal_moves,
        "pair_details": pairs
    }

def audit_stockfish4_victory():
    pgn_path = P113_PGN_DIR / "x18_1t_vs_sf4_1t.pgn"
    with open(pgn_path, "r", encoding="utf-8") as f:
        idx = 0
        while True:
            g = chess.pgn.read_game(f)
            if not g: break
            idx += 1
            if idx == 25:
                # Inspect game 25
                board = g.board()
                moves = list(g.mainline_moves())
                for m in moves:
                    board.push(m)
                return {
                    "round": g.headers.get("Round"),
                    "white": g.headers.get("White"),
                    "black": g.headers.get("Black"),
                    "result": g.headers.get("Result"),
                    "termination": g.headers.get("Termination"),
                    "eco": g.headers.get("ECO"),
                    "opening": g.headers.get("Opening"),
                    "plies": len(moves),
                    "final_fen": board.fen(),
                    "is_legal": board.is_valid(),
                    "final_is_game_over": board.is_game_over()
                }

def main():
    tourn_results = []
    total_tourn_games = 0
    for mname, ea, eb, count in TOURNAMENT_MATCHES:
        p = P113_PGN_DIR / f"{mname}.pgn"
        res = parse_pgn_file(p, ea, eb, count)
        tourn_results.append(res)
        total_tourn_games += res["games"]
        
    calib_results = []
    total_calib_games = 0
    for mname, ea, eb, count in CALIBRATION_MATCHES:
        p = P113_PGN_DIR / f"{mname}.pgn"
        res = parse_pgn_file(p, ea, eb, count)
        calib_results.append(res)
        total_calib_games += res["games"]

    sf4_win_audit = audit_stockfish4_victory()

    out_data = {
        "tournament_games_count": total_tourn_games,
        "calibration_games_count": total_calib_games,
        "grand_total_unique_games": total_tourn_games + total_calib_games,
        "tournaments": tourn_results,
        "calibrations": calib_results,
        "sf4_victory_audit": sf4_win_audit
    }

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Reconciled {total_tourn_games} tournament games + {total_calib_games} calibration games = {total_tourn_games + total_calib_games} unique games.")
    print("Stockfish 4 win audit:", sf4_win_audit)

if __name__ == "__main__":
    main()
