"""Independent statistical replication and audit of Project Janus Milestone v0.32 match data."""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from pathlib import Path

import chess
import chess.pgn


def audit_v032_data(
    json_path: Path,
    csv_path: Path,
    pgn_path: Path,
    summary_path: Path,
) -> dict:
    report = {}

    # 1. Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    meta = json_data.get("metadata", {})
    summary = json_data.get("summary", {})
    games = json_data.get("games", [])

    report["metadata_check"] = {
        "candidate_name": meta.get("candidate_name"),
        "candidate_commit": meta.get("candidate_commit"),
        "baseline_name": meta.get("baseline_name"),
        "baseline_commit": meta.get("baseline_commit"),
        "time_control": meta.get("time_control"),
        "movetime_ms": meta.get("movetime_ms"),
        "seed": meta.get("seed"),
        "total_games_requested": meta.get("total_games_requested"),
    }

    # 2. Check games integrity in JSON
    num_games = len(games)
    report["num_games_json"] = num_games

    # Check game IDs sequence
    game_ids = [g["game"] for g in games]
    report["game_ids_contiguous"] = (game_ids == list(range(1, num_games + 1)))

    # Check pair numbers and color reversal
    pairs: dict[int, list[dict]] = {}
    for g in games:
        p = g["pair"]
        pairs.setdefault(p, []).append(g)

    report["pairs_count"] = len(pairs)
    pair_integrity_errors = []

    cand_wins = 0
    cand_draws = 0
    cand_losses = 0
    cand_points = 0.0

    by_color = {
        "white": {"wins": 0, "draws": 0, "losses": 0, "points": 0.0, "games": 0},
        "black": {"wins": 0, "draws": 0, "losses": 0, "points": 0.0, "games": 0},
    }

    pair_outcomes = {"won": 0, "drawn": 0, "lost": 0}
    pair_diffs = []
    pair_scores = []

    for p_id in sorted(pairs.keys()):
        p_games = pairs[p_id]
        if len(p_games) != 2:
            pair_integrity_errors.append(f"Pair {p_id} has {len(p_games)} games (expected 2)")
            continue

        g1, g2 = p_games[0], p_games[1]
        # Check start FEN / opening
        if g1.get("start_fen") != g2.get("start_fen"):
            pair_integrity_errors.append(f"Pair {p_id} start FEN mismatch: {g1.get('start_fen')} vs {g2.get('start_fen')}")
        if g1.get("opening_id") != g2.get("opening_id"):
            pair_integrity_errors.append(f"Pair {p_id} opening ID mismatch")

        # Check color reversal: g1 should be White, g2 Black (or opposite)
        colors = {g1["candidate_color"], g2["candidate_color"]}
        if colors != {"white", "black"}:
            pair_integrity_errors.append(f"Pair {p_id} colors are {colors}, expected {{white, black}}")

        # Sum pair score
        p_cand_pts = g1["candidate_score"] + g2["candidate_score"]
        pair_scores.append(p_cand_pts)
        diff = p_cand_pts - 1.0
        pair_diffs.append(diff)
        if p_cand_pts > 1.0:
            pair_outcomes["won"] += 1
        elif p_cand_pts == 1.0:
            pair_outcomes["drawn"] += 1
        else:
            pair_outcomes["lost"] += 1

    report["pair_integrity_errors"] = pair_integrity_errors
    report["pair_outcomes_calculated"] = pair_outcomes

    # Game-level tallies
    terminations = {}
    for g in games:
        res = g["result"]
        c_col = g["candidate_color"]
        c_score = g["candidate_score"]
        term = g["termination"]
        terminations[term] = terminations.get(term, 0) + 1

        # Check result / score consistency
        expected_score = 0.5 if res == "1/2-1/2" else (1.0 if (res == "1-0" and c_col == "white") or (res == "0-1" and c_col == "black") else 0.0)
        if c_score != expected_score:
            pair_integrity_errors.append(f"Game {g['game']}: candidate_score {c_score} != expected {expected_score}")

        cand_points += c_score
        by_color[c_col]["games"] += 1
        by_color[c_col]["points"] += c_score

        if c_score == 1.0:
            cand_wins += 1
            by_color[c_col]["wins"] += 1
        elif c_score == 0.5:
            cand_draws += 1
            by_color[c_col]["draws"] += 1
        else:
            cand_losses += 1
            by_color[c_col]["losses"] += 1

    by_color["white"]["score_pct"] = round(by_color["white"]["points"] / by_color["white"]["games"] * 100.0, 2) if by_color["white"]["games"] else 0.0
    by_color["black"]["score_pct"] = round(by_color["black"]["points"] / by_color["black"]["games"] * 100.0, 2) if by_color["black"]["games"] else 0.0

    report["tallies_calculated"] = {
        "candidate_wins": cand_wins,
        "draws": cand_draws,
        "candidate_losses": cand_losses,
        "candidate_points": cand_points,
        "candidate_score_pct": cand_points / num_games * 100.0,
        "by_color": by_color,
        "terminations": terminations,
    }

    # 3. Check CSV agreement
    csv_rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_rows.append(row)

    report["num_games_csv"] = len(csv_rows)
    csv_mismatches = []
    if len(csv_rows) != num_games:
        csv_mismatches.append(f"CSV row count {len(csv_rows)} != JSON count {num_games}")
    else:
        for i in range(num_games):
            jg = games[i]
            cr = csv_rows[i]
            if int(cr["game"]) != jg["game"]:
                csv_mismatches.append(f"Game {i+1} ID mismatch: CSV {cr['game']} vs JSON {jg['game']}")
            if cr["result"] != jg["result"]:
                csv_mismatches.append(f"Game {i+1} result mismatch: CSV {cr['result']} vs JSON {jg['result']}")
            if float(cr["candidate_score"]) != jg["candidate_score"]:
                csv_mismatches.append(f"Game {i+1} score mismatch: CSV {cr['candidate_score']} vs JSON {jg['candidate_score']}")
            if cr["termination"] != jg["termination"]:
                csv_mismatches.append(f"Game {i+1} term mismatch: CSV {cr['termination']} vs JSON {jg['termination']}")
    report["csv_mismatches"] = csv_mismatches

    # 4. Check PGN agreement and move legality
    pgn_games = []
    pgn_mismatches = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            pgn_games.append(game)

    report["num_games_pgn"] = len(pgn_games)
    if len(pgn_games) != num_games:
        pgn_mismatches.append(f"PGN count {len(pgn_games)} != JSON count {num_games}")
    else:
        for i in range(num_games):
            jg = games[i]
            pg = pgn_games[i]
            pgn_res = pg.headers.get("Result")
            if pgn_res != jg["result"]:
                pgn_mismatches.append(f"Game {i+1} PGN result {pgn_res} != JSON {jg['result']}")

            # Verify move legality by playing through board
            b = pg.board()
            start_ply = b.ply()
            moves_played = 0
            for move in pg.mainline_moves():
                if move not in b.legal_moves:
                    pgn_mismatches.append(f"Game {i+1} illegal move {move} at move {moves_played}")
                    break
                b.push(move)
                moves_played += 1

            total_game_plies = start_ply + moves_played
            if total_game_plies != jg["plies"]:
                pgn_mismatches.append(f"Game {i+1} plies mismatch: FEN ({start_ply}) + PGN ({moves_played}) = {total_game_plies} vs JSON {jg['plies']}")

    report["pgn_mismatches"] = pgn_mismatches

    # 5. Statistical Recomputations
    N = num_games
    S = cand_points / N
    # Game-level variance & Wald CI
    game_scores = [g["candidate_score"] for g in games]
    sample_var = sum((s - S) ** 2 for s in game_scores) / (N - 1)
    se_game = math.sqrt(sample_var / N)
    wald_ci_lower = max(0.0, (S - 1.96 * se_game) * 100.0)
    wald_ci_upper = min(100.0, (S + 1.96 * se_game) * 100.0)

    # Conventional Elo-equivalent
    delta_elo = -400.0 * math.log10((1.0 / S) - 1.0)
    # Delta method standard error for Elo: d(Delta E)/dS = 400 / (ln(10) * S * (1 - S))
    d_elo_ds = 400.0 / (math.log(10) * S * (1.0 - S))
    elo_se = d_elo_ds * se_game

    # Paired design statistics (Pairs are the unit of observation)
    M = len(pair_scores) # 50 pairs
    # Each pair score is out of 2.0. Let pair fraction z_i = pair_score / 2.0
    z_scores = [ps / 2.0 for ps in pair_scores]
    mean_z = sum(z_scores) / M
    pair_var = sum((z - mean_z) ** 2 for z in z_scores) / (M - 1)
    se_paired = math.sqrt(pair_var / M)
    paired_t_stat = (mean_z - 0.5) / se_paired if se_paired > 0 else 0.0

    # Paired bootstrap CI (exact 2000 replicates with seed 42 as in match_v032)
    rng = random.Random(42)
    boot_means = []
    for _ in range(2000):
        sample = [rng.choice(pair_diffs) for _ in range(M)]
        boot_pct = (sum(sample) / len(sample) + 1.0) / 2.0 * 100.0
        boot_means.append(boot_pct)
    boot_means.sort()
    boot_ci_42 = [round(boot_means[50], 2), round(boot_means[1950], 2)]

    # Extended bootstrap (100,000 replicates for ultra-precise CI)
    rng100k = random.Random(12345)
    boot_means_100k = []
    for _ in range(100000):
        sample = [rng100k.choice(pair_diffs) for _ in range(M)]
        boot_pct = (sum(sample) / len(sample) + 1.0) / 2.0 * 100.0
        boot_means_100k.append(boot_pct)
    boot_means_100k.sort()
    boot_ci_100k = [round(boot_means_100k[2500], 2), round(boot_means_100k[97500], 2)]

    # Paired Wilcoxon signed-rank test on (g1_cand_score - g1_base_score) vs (g2_cand_score - g2_base_score)
    # pair diff = pair_cand_pts - 1.0 in {-1.0, -0.5, 0.0, +0.5, +1.0}
    # Non-zero differences:
    non_zero_diffs = [d for d in pair_diffs if d != 0.0]
    n_won_pairs = pair_outcomes["won"]
    n_lost_pairs = pair_outcomes["lost"]
    n_drawn_pairs = pair_outcomes["drawn"]

    # Sign test on decisive pairs:
    # Under H0 (p=0.5): won_pairs ~ Binomial(n_decisive, 0.5)
    n_decisive = n_won_pairs + n_lost_pairs
    # Binomial p-value (two-tailed) for 15 wins out of 34 decisive pairs
    # P(X <= 15 or X >= 19) where X ~ Bin(34, 0.5)
    def binom_pmf(k, n, p=0.5):
        return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))

    p_val_sign_test = 2.0 * sum(binom_pmf(k, n_decisive, 0.5) for k in range(0, n_won_pairs + 1))

    report["statistical_recomputation"] = {
        "observed_score_pct": S * 100.0,
        "game_standard_error_pct": round(se_game * 100.0, 4),
        "wald_ci_95": [round(wald_ci_lower, 2), round(wald_ci_upper, 2)],
        "delta_elo": round(delta_elo, 2),
        "elo_standard_error": round(elo_se, 2),
        "elo_ci_95": [round(delta_elo - 1.96 * elo_se, 1), round(delta_elo + 1.96 * elo_se, 1)],
        "paired_standard_error_pct": round(se_paired * 100.0, 4),
        "paired_t_statistic": round(paired_t_stat, 4),
        "pair_bootstrap_ci_95_seed42_2k": boot_ci_42,
        "pair_bootstrap_ci_95_100k": boot_ci_100k,
        "decisive_pairs": n_decisive,
        "sign_test_two_tailed_p_value": round(p_val_sign_test, 4),
    }

    # Compare with reported summary
    rep_summary = summary
    discrepancies = []
    if rep_summary.get("candidate_wins") != cand_wins:
        discrepancies.append(f"Wins: reported {rep_summary.get('candidate_wins')} vs calculated {cand_wins}")
    if rep_summary.get("draws") != cand_draws:
        discrepancies.append(f"Draws: reported {rep_summary.get('draws')} vs calculated {cand_draws}")
    if rep_summary.get("candidate_losses") != cand_losses:
        discrepancies.append(f"Losses: reported {rep_summary.get('candidate_losses')} vs calculated {cand_losses}")
    if rep_summary.get("candidate_score_pct") != round(S * 100.0, 2):
        discrepancies.append(f"Score %: reported {rep_summary.get('candidate_score_pct')} vs calculated {round(S * 100.0, 2)}")
    if rep_summary.get("delta_elo") != round(delta_elo, 1):
        discrepancies.append(f"Delta Elo: reported {rep_summary.get('delta_elo')} vs calculated {round(delta_elo, 1)}")
    if rep_summary.get("pairs_won") != pair_outcomes["won"]:
        discrepancies.append(f"Pairs won: reported {rep_summary.get('pairs_won')} vs calculated {pair_outcomes['won']}")
    if rep_summary.get("pairs_drawn") != pair_outcomes["drawn"]:
        discrepancies.append(f"Pairs drawn: reported {rep_summary.get('pairs_drawn')} vs calculated {pair_outcomes['drawn']}")
    if rep_summary.get("pairs_lost") != pair_outcomes["lost"]:
        discrepancies.append(f"Pairs lost: reported {rep_summary.get('pairs_lost')} vs calculated {pair_outcomes['lost']}")

    report["discrepancies_with_reported_summary"] = discrepancies

    return report


if __name__ == "__main__":
    base = Path("E:/ChessXML/project-janus")
    json_path = base / "analysis/v0.32/match/v032_match_500ms.json"
    csv_path = base / "analysis/v0.32/match/v032_match_500ms.csv"
    pgn_path = base / "analysis/v0.32/match/v032_match_500ms.pgn"
    summary_path = base / "analysis/v0.32/match/v032_match_summary.json"

    res = audit_v032_data(json_path, csv_path, pgn_path, summary_path)
    print(json.dumps(res, indent=2))
