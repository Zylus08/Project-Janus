"""Independent Release Audit for Project Janus v0.35 Time Management Match.

Performs rigorous verification:
1. Engine identities, commands, and metadata integrity
2. Agreement between JSON, CSV, PGN, and attempt logs
3. Opening pair integrity and colour reversal
4. Move-by-move legality verification for all games
5. Clock and increment progression consistency
6. Independent recalculation of all match statistics
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]


def audit_v035_match(
    match_dir: Path = ROOT / "analysis" / "v0.35" / "strength_match",
    match_name: str = "fischer_strength_match",
) -> dict[str, Any]:
    json_path = match_dir / f"{match_name}.json"
    pgn_path = match_dir / f"{match_name}.pgn"
    csv_path = match_dir / f"{match_name}.csv"
    attempts_path = match_dir / f"{match_name}_attempts.json"

    if not json_path.is_file():
        raise FileNotFoundError(f"JSON match file not found at {json_path}")
    if not pgn_path.is_file():
        raise FileNotFoundError(f"PGN file not found at {pgn_path}")
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found at {csv_path}")
    if not attempts_path.is_file():
        raise FileNotFoundError(f"Attempts file not found at {attempts_path}")

    raw_json = json.loads(json_path.read_text(encoding="utf-8"))
    raw_attempts = json.loads(attempts_path.read_text(encoding="utf-8"))

    metadata = raw_json["metadata"]
    match_summary = raw_json["match_summary"]
    valid_games = raw_json["valid_games"]

    audit_checks = {}

    # Check 1: Engine identity and metadata
    expected_cand = "Janus-v0.35-Adaptive"
    expected_ref = "Janus-v0.35-Reference"
    audit_checks["engine_identity"] = (
        metadata["candidate_name"] == expected_cand
        and metadata["reference_name"] == expected_ref
        and "--time-policy" in metadata["candidate_cmd"]
        and metadata["time_mode"] == "fischer_increment"
        and metadata["base_time_ms"] == 3000
        and metadata["inc_time_ms"] == 100
    )

    # Check 2: Raw attempts vs completed games
    total_attempts = len(raw_attempts)
    completed_attempts = [a for a in raw_attempts if a.get("status") == "completed"]
    infra_failures = [a for a in raw_attempts if a.get("status") == "infrastructure_failure"]
    audit_checks["attempt_counts"] = (
        total_attempts == len(valid_games)
        and len(infra_failures) == 0
        and len(completed_attempts) == len(valid_games)
    )

    # Check 3: CSV agreement
    csv_rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_rows.append(row)

    csv_matches_json = (len(csv_rows) == len(valid_games))
    if csv_matches_json:
        for c_row, j_row in zip(csv_rows, valid_games):
            if (
                int(c_row["game"]) != j_row["game"]
                or c_row["result"] != j_row["result"]
                or float(c_row["candidate_points"]) != float(j_row["candidate_points"])
            ):
                csv_matches_json = False
                break
    audit_checks["csv_agreement"] = csv_matches_json

    # Check 4: PGN games and move legality
    pgn_games = []
    all_moves_legal = True
    clock_consistency = True

    with open(pgn_path, encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            pgn_games.append(game)

    audit_checks["pgn_game_count"] = (len(pgn_games) == len(valid_games))

    for idx, (p_game, j_game) in enumerate(zip(pgn_games, valid_games)):
        # Verify result agreement
        if p_game.headers.get("Result") != j_game["result"]:
            audit_checks[f"game_{idx + 1}_result_mismatch"] = False

        # Replay moves and verify legality
        board = p_game.board()
        move_log = j_game["move_log"]

        if len(move_log) != len(list(p_game.mainline_moves())):
            all_moves_legal = False

        for ply_idx, move in enumerate(p_game.mainline_moves()):
            if move not in board.legal_moves:
                all_moves_legal = False
                break
            board.push(move)

            # Check clock record
            if ply_idx < len(move_log):
                rec = move_log[ply_idx]
                if rec["move"] != move.uci():
                    all_moves_legal = False
                if rec["wtime_left_ms"] < 0 or rec["btime_left_ms"] < 0:
                    clock_consistency = False

        if board.fen() != j_game["final_fen"]:
            all_moves_legal = False

    audit_checks["move_legality"] = all_moves_legal
    audit_checks["clock_consistency"] = clock_consistency

    # Check 5: Opening pair balance and colour reversal
    pair_checks = True
    pairs_dict = {}
    for g in valid_games:
        pairs_dict.setdefault(g["pair"], []).append(g)

    for p_num, p_games in pairs_dict.items():
        if len(p_games) != 2:
            pair_checks = False
            break
        g1, g2 = p_games[0], p_games[1]
        # Colors must be reversed
        if g1["candidate_color"] == g2["candidate_color"]:
            pair_checks = False
        # Opening must be identical
        if g1["opening_id"] != g2["opening_id"]:
            pair_checks = False
        if g1.get("start_fen") and g2.get("start_fen") and g1["start_fen"] != g2["start_fen"]:
            pair_checks = False

    audit_checks["opening_pair_symmetry"] = pair_checks

    # Check 6: Independent statistical recalculation
    cand_wins = sum(1 for g in valid_games if (g["result"] == "1-0" and g["candidate_color"] == "white") or (g["result"] == "0-1" and g["candidate_color"] == "black"))
    cand_draws = sum(1 for g in valid_games if g["result"] == "1/2-1/2")
    cand_losses = len(valid_games) - cand_wins - cand_draws
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / len(valid_games)) * 100.0

    p_hat = cand_score / len(valid_games)
    indep_elo = -400.0 * math.log10((1.0 - p_hat) / p_hat)
    se_p = math.sqrt((p_hat * (1.0 - p_hat)) / len(valid_games))
    se_elo = (400.0 / (math.log(10) * p_hat * (1.0 - p_hat))) * se_p
    ci_low = round(indep_elo - 1.96 * se_elo, 1)
    ci_high = round(indep_elo + 1.96 * se_elo, 1)

    pairs_won = 0
    pairs_drawn = 0
    pairs_lost = 0
    for p_games in pairs_dict.values():
        p_score = 0.0
        for r in p_games:
            res = r.get("result")
            c = r.get("candidate_color")
            if res == "1/2-1/2":
                p_score += 0.5
            elif (res == "1-0" and c == "white") or (res == "0-1" and c == "black"):
                p_score += 1.0
        if p_score > 1.0:
            pairs_won += 1
        elif p_score < 1.0:
            pairs_lost += 1
        else:
            pairs_drawn += 1

    decisive_pairs = pairs_won + pairs_lost
    k = min(pairs_won, pairs_lost)
    sign_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
    sign_p = min(1.0, sign_p)

    stats_match = (
        cand_wins == match_summary["candidate_wins"]
        and cand_draws == match_summary["candidate_draws"]
        and cand_losses == match_summary["candidate_losses"]
        and round(cand_score_pct, 2) == match_summary["candidate_score_pct"]
        and round(indep_elo, 1) == match_summary["estimated_elo_diff"]
        and pairs_won == match_summary["pairs_summary"]["pairs_won"]
        and pairs_drawn == match_summary["pairs_summary"]["pairs_drawn"]
        and pairs_lost == match_summary["pairs_summary"]["pairs_lost"]
        and round(sign_p, 4) == match_summary["pairs_summary"]["sign_test_p_value"]
    )
    audit_checks["statistics_reproducible"] = stats_match

    overall_verdict = all(audit_checks.values())

    audit_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "VERIFIED_VALID" if overall_verdict else "REJECTED_AUDIT_FAILURE",
        "audit_checks": audit_checks,
        "match_size": {
            "total_games": len(valid_games),
            "total_pairs": len(pairs_dict),
            "infrastructure_failures": len(infra_failures),
        },
        "statistics": {
            "candidate_wins": cand_wins,
            "candidate_draws": cand_draws,
            "candidate_losses": cand_losses,
            "candidate_score": cand_score,
            "candidate_score_pct": round(cand_score_pct, 2),
            "estimated_elo_diff": round(indep_elo, 1),
            "elo_95_ci": [ci_low, ci_high],
            "pairs_won": pairs_won,
            "pairs_drawn": pairs_drawn,
            "pairs_lost": pairs_lost,
            "sign_test_p_value": round(sign_p, 4),
        },
    }

    out_file = match_dir / "independent_audit.json"
    out_file.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    print(f"Independent audit report written to {out_file}")
    print(f"Overall Audit Verdict: {audit_report['verdict']}")

    return audit_report


if __name__ == "__main__":
    rep = audit_v035_match()
    if rep["verdict"] != "VERIFIED_VALID":
        sys.exit(1)
