#!/usr/bin/env python3
"""
audit_p121_tournament_reconciliation.py
Milestone P1.22 Phase 0: Forensic Audit and Statistical Reconciliation of P1.21 Tournament Battery.

Authoritative re-scoring and pentanomial audit of all 8 matches (500 games) from P1.21.
Identifies and resolves:
1. PGN result parser defect where games terminating via can_claim_threefold_repetition() had Result '*'.
2. P1.21 harness tabulation defect where '*' was scored as 0.0 (candidate loss), artificially depressing candidate score.
3. P1.21 pentanomial calculation defect where round(pair_scores * 2.0) was called on normalized scores in [0, 1],
   collapsing buckets into indices 0, 1, 2 and leaving indices 3 and 4 permanently zero.

Computes exact pair categories (LL, LD, DD, WL, WD, WW), validated pentanomials, paired statistics, and
mathematical identity invariants.
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.21" / "pgn"
OUT_JSON = ROOT / "analysis" / "phase1" / "p1.22" / "raw" / "p121_tournament_reconciliation.json"
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

MATCH_FILES = [
    ("M1", "X26-S vs Reference X22-S Fast TC", "match1_x26s_vs_x22s_fast.pgn", "Janus_Classical_X26_S", 50),
    ("M2", "X26-S vs Reference X22-S Slow TC", "match2_x26s_vs_x22s_slow.pgn", "Janus_Classical_X26_S", 25),
    ("M3", "X26-S vs Baseline X7 Fast TC", "match3_x26s_vs_x7_fast.pgn", "Janus_Classical_X26_S", 50),
    ("M4", "X26-S vs Baseline X7 Slow TC", "match4_x26s_vs_x7_slow.pgn", "Janus_Classical_X26_S", 25),
    ("M5", "X26-P vs Baseline X12 Fast TC", "match5_x26p_vs_x12_fast.pgn", "Janus_Classical_X26_P", 50),
    ("M6", "X26-S vs Stockfish 4 Blitz", "match6_x26s_vs_sf4_blitz.pgn", "Janus_Classical_X26_S", 20),
    ("M7", "X26-S vs Stockfish 11 Blitz", "match7_x26s_vs_sf11_blitz.pgn", "Janus_Classical_X26_S", 20),
    ("M8", "X26-S vs Stockfish 19 NNUE Blitz", "match8_x26s_vs_sf19_blitz.pgn", "Janus_Classical_X26_S", 10),
]

def wilson_score_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    spread = (z / denom) * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4 * (n**2)))
    return max(0.0, center - spread), min(1.0, center + spread)

def calc_paired_stats(pair_scores_normalized: List[float], z: float = 1.95996):
    # pair_scores_normalized are in [0, 1] (i.e. pair_points / 2.0)
    n = len(pair_scores_normalized)
    if n == 0:
        return 0.0, 0.0, 1.0, 1.0, 1.0
    mean_p = sum(pair_scores_normalized) / n
    if n == 1:
        return mean_p, 0.0, 1.0, 0.5, 1.0
    var = sum((x - mean_p) ** 2 for x in pair_scores_normalized) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 1e-6
    ci_low = max(0.0, mean_p - z * se)
    ci_high = min(1.0, mean_p + z * se)
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    p2 = 2.0 * 0.5 * math.erfc(abs(t_stat) / math.sqrt(2.0))
    return mean_p, ci_low, ci_high, se, p2

def adjudicate_game(game: chess.pgn.Game) -> Tuple[str, str]:
    """Returns (result, adjudication_note)"""
    res = game.headers.get("Result", "*")
    if res in ("1-0", "0-1", "1/2-1/2"):
        return res, "pgn_header"

    # Replay moves
    b = game.board()
    moves = list(game.mainline_moves())
    for m in moves:
        b.push(m)

    if b.is_checkmate():
        return ("0-1" if b.turn == chess.WHITE else "1-0"), "checkmate_verified"
    elif b.can_claim_threefold_repetition():
        return "1/2-1/2", "threefold_repetition"
    elif b.is_stalemate():
        return "1/2-1/2", "stalemate"
    elif b.is_insufficient_material():
        return "1/2-1/2", "insufficient_material"
    elif b.is_fifty_moves():
        return "1/2-1/2", "fifty_moves"
    elif len(moves) >= 150:
        return "1/2-1/2", "max_moves"
    else:
        raise ValueError(f"Unresolved game termination at ply {len(moves)}: fen {b.fen()}")

def audit_pgn(match_id: str, desc: str, pgn_filename: str, cand_name: str, expected_pairs: int) -> Dict[str, Any]:
    pgn_path = PGN_DIR / pgn_filename
    if not pgn_path.exists():
        raise FileNotFoundError(f"Missing PGN: {pgn_path}")

    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)

    total_games = len(games)
    assert total_games == expected_pairs * 2, f"Expected {expected_pairs*2} games in {pgn_filename}, found {total_games}"

    pairs_data = []
    w_count = d_count = l_count = 0
    subcat_counts = {"LL": 0, "LD": 0, "DD": 0, "WL": 0, "WD": 0, "WW": 0}
    pair_points_list = []

    # Also track what P1.21 originally tabulated (where '*' was scored as 0.0)
    p121_w = p121_d = p121_l = 0
    p121_pair_scores_norm = []
    repaired_star_count = 0

    for p_idx in range(expected_pairs):
        g1 = games[2 * p_idx]
        g2 = games[2 * p_idx + 1]

        g1_white = g1.headers.get("White", "")
        g1_black = g1.headers.get("Black", "")
        g1_raw_res = g1.headers.get("Result", "*")

        g2_white = g2.headers.get("White", "")
        g2_black = g2.headers.get("Black", "")
        g2_raw_res = g2.headers.get("Result", "*")

        assert g1_white == cand_name, f"Expected candidate as White in game {2*p_idx+1}, got {g1_white}"
        assert g2_black == cand_name, f"Expected candidate as Black in game {2*p_idx+2}, got {g2_black}"

        # Authoritative adjudication
        g1_res, g1_note = adjudicate_game(g1)
        g2_res, g2_note = adjudicate_game(g2)

        if g1_raw_res == "*":
            repaired_star_count += 1
        if g2_raw_res == "*":
            repaired_star_count += 1

        # Candidate points in g1 (as White)
        s1 = 1.0 if g1_res == "1-0" else (0.5 if g1_res == "1/2-1/2" else 0.0)
        # Candidate points in g2 (as Black)
        s2 = 1.0 if g2_res == "0-1" else (0.5 if g2_res == "1/2-1/2" else 0.0)

        # Track P1.21 buggy scoring:
        p121_s1 = 1.0 if g1_raw_res == "1-0" else (0.5 if g1_raw_res == "1/2-1/2" else 0.0)
        p121_s2 = 1.0 if g2_raw_res == "0-1" else (0.5 if g2_raw_res == "1/2-1/2" else 0.0)
        p121_pair_scores_norm.append((p121_s1 + p121_s2) / 2.0)
        for s in (p121_s1, p121_s2):
            if s == 1.0: p121_w += 1
            elif s == 0.5: p121_d += 1
            else: p121_l += 1

        for s in (s1, s2):
            if s == 1.0: w_count += 1
            elif s == 0.5: d_count += 1
            else: l_count += 1

        pair_pts = s1 + s2
        pair_points_list.append(pair_pts)

        if pair_pts == 0.0:
            cat = "LL"
        elif pair_pts == 0.5:
            cat = "LD"
        elif pair_pts == 1.0:
            cat = "DD" if (s1 == 0.5 and s2 == 0.5) else "WL"
        elif pair_pts == 1.5:
            cat = "WD"
        elif pair_pts == 2.0:
            cat = "WW"
        else:
            raise ValueError(f"Invalid pair points: {pair_pts}")

        subcat_counts[cat] += 1

        pairs_data.append({
            "pair_index": p_idx,
            "game1_white": g1_white,
            "game1_black": g1_black,
            "game1_raw_result": g1_raw_res,
            "game1_adjudicated_result": g1_res,
            "game1_cand_score": s1,
            "game2_white": g2_white,
            "game2_black": g2_black,
            "game2_raw_result": g2_raw_res,
            "game2_adjudicated_result": g2_res,
            "game2_cand_score": s2,
            "cand_pair_points": pair_pts,
            "pair_category": cat
        })

    # Verifications & Invariants
    total_pairs_subcat = sum(subcat_counts.values())
    assert total_pairs_subcat == expected_pairs, f"Subcat sum {total_pairs_subcat} != {expected_pairs}"

    cand_total_points = w_count + 0.5 * d_count
    pair_sum_points = sum(pair_points_list)
    assert abs(cand_total_points - pair_sum_points) < 1e-6, f"Points mismatch: {cand_total_points} vs {pair_sum_points}"

    w_decomposed = 2 * subcat_counts["WW"] + subcat_counts["WD"] + subcat_counts["WL"]
    d_decomposed = 2 * subcat_counts["DD"] + subcat_counts["WD"] + subcat_counts["LD"]
    l_decomposed = 2 * subcat_counts["LL"] + subcat_counts["LD"] + subcat_counts["WL"]
    assert w_count == w_decomposed, f"Wins mismatch: {w_count} vs {w_decomposed}"
    assert d_count == d_decomposed, f"Draws mismatch: {d_count} vs {d_decomposed}"
    assert l_count == l_decomposed, f"Losses mismatch: {l_count} vs {l_decomposed}"

    # Authoritative Pentanomial distributions:
    # Ascending [LL(0.0), LD(0.5), DD+WL(1.0), WD(1.5), WW(2.0)]
    penta_ascending = [
        subcat_counts["LL"],
        subcat_counts["LD"],
        subcat_counts["DD"] + subcat_counts["WL"],
        subcat_counts["WD"],
        subcat_counts["WW"]
    ]
    # Descending [WW(2.0), WD(1.5), DD+WL(1.0), LD(0.5), LL(0.0)]
    penta_descending = [
        subcat_counts["WW"],
        subcat_counts["WD"],
        subcat_counts["DD"] + subcat_counts["WL"],
        subcat_counts["LD"],
        subcat_counts["LL"]
    ]

    score_pct = (cand_total_points / total_games) * 100.0
    elo = -400.0 * math.log10(1.0 / (cand_total_points / total_games) - 1.0) if 0 < cand_total_points < total_games else None

    # Paired stats on true normalized pair scores
    pair_scores_norm = [pts / 2.0 for pts in pair_points_list]
    mean_p, ci_low, ci_high, se, p2 = calc_paired_stats(pair_scores_norm)
    wilson_low, wilson_high = wilson_score_interval(cand_total_points, total_games)

    # Reconstruct the P1.21 buggy pentanomial:
    # In P1.21: calc_pentanomial used round(s * 2.0) where s was in [0, 1]
    p121_corrupted_penta = [0, 0, 0, 0, 0]
    for s in p121_pair_scores_norm:
        idx = int(round(s * 2.0))
        p121_corrupted_penta[idx] += 1

    return {
        "match_id": match_id,
        "description": desc,
        "candidate": cand_name,
        "total_games": total_games,
        "total_pairs": expected_pairs,
        "repaired_threefold_star_games": repaired_star_count,
        "p121_as_reported": {
            "wins": p121_w,
            "draws": p121_d,
            "losses": p121_l,
            "points": p121_w + 0.5 * p121_d,
            "score_pct": round(((p121_w + 0.5 * p121_d) / total_games) * 100.0, 2),
            "corrupted_pentanomial_raw": p121_corrupted_penta
        },
        "authoritative_reconciled": {
            "wins": w_count,
            "draws": d_count,
            "losses": l_count,
            "points": cand_total_points,
            "score_pct": round(score_pct, 2),
            "elo": round(elo, 2) if elo is not None else None,
            "subcategories": subcat_counts,
            "pentanomial_ascending_LL_to_WW": penta_ascending,
            "pentanomial_descending_WW_to_LL": penta_descending,
            "paired_ci_95": [round(ci_low * 100.0, 2), round(ci_high * 100.0, 2)],
            "paired_se": round(se, 5),
            "paired_p_value": round(p2, 5),
            "wilson_ci_95": [round(wilson_low * 100.0, 2), round(wilson_high * 100.0, 2)]
        },
        "pairs": pairs_data
    }

def main():
    print("=" * 85)
    print("PHASE 0: FORENSIC AUDIT & STATISTICAL RECONCILIATION OF P1.21 TOURNAMENTS")
    print("=" * 85)

    reconciled_matches = []

    for mid, desc, fname, cand, n_pairs in MATCH_FILES:
        res = audit_pgn(mid, desc, fname, cand, n_pairs)
        reconciled_matches.append(res)

        rep = res["p121_as_reported"]
        auth = res["authoritative_reconciled"]

        print(f"\n[{mid}] {desc}")
        print(f"  Games: {res['total_games']} (Pairs: {res['total_pairs']}) | Repaired Threefold '*' Games: {res['repaired_threefold_star_games']}")
        print(f"  P1.21 As-Reported (Buggy):  W-D-L: {rep['wins']}-{rep['draws']}-{rep['losses']} | Pts: {rep['points']}/{res['total_games']} ({rep['score_pct']}%)")
        print(f"    Corrupted Pentanomial:     {rep['corrupted_pentanomial_raw']}  [round(s*2.0) on s in [0,1]]")
        print(f"  Authoritative Reconciled:   W-D-L: {auth['wins']}-{auth['draws']}-{auth['losses']} | Pts: {auth['points']}/{res['total_games']} ({auth['score_pct']}%) | Elo: {auth['elo']}")
        print(f"    Subcategories:            LL={auth['subcategories']['LL']}, LD={auth['subcategories']['LD']}, DD={auth['subcategories']['DD']}, WL={auth['subcategories']['WL']}, WD={auth['subcategories']['WD']}, WW={auth['subcategories']['WW']}")
        print(f"    Pentanomial [0.0..2.0]:   {auth['pentanomial_ascending_LL_to_WW']}  (LL, LD, 1.0, WD, WW)")
        print(f"    Pentanomial [2.0..0.0]:   {auth['pentanomial_descending_WW_to_LL']}  (WW, WD, 1.0, LD, LL)")
        print(f"    Paired 95% CI:            [{auth['paired_ci_95'][0]}%, {auth['paired_ci_95'][1]}%] | SE: {auth['paired_se']} | p-value: {auth['paired_p_value']}")
        print(f"    Wilson Score 95% CI:      [{auth['wilson_ci_95'][0]}%, {auth['wilson_ci_95'][1]}%]")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(reconciled_matches, f, indent=2)

    print(f"\n" + "=" * 85)
    print(f"Authoritative reconciliation JSON saved to:\n  {OUT_JSON}")
    print("=" * 85)

if __name__ == "__main__":
    main()
