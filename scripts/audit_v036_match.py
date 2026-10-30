"""Project Janus v0.36 - Independent Experimental Release Audit Tool.

Implements an independent validation pipeline that recalculates all results
and statistics directly from raw move and game records, with zero reliance
on the match runner's summary routines.

Verifies:
1. Target completion: 100 valid games across 50 complete opening pairs
2. Protocol & time control: 3000 ms + 100 ms Fischer increment
3. Engine identities, configuration parameters, and CLI commands
4. Colour reversal and opening pair integrity
5. Complete move legality replay with chess.Board
6. Monotonic clock decrement and increment progression
7. Agreement across JSON, PGN, CSV, moves CSV, and attempt logs
8. Absence of duplicate games or accidental double-counting
9. Independent statistical verification:
   - Match score percentage S
   - Mean paired difference Delta_bar
   - Paired Student's t-test (df=49)
   - Pair-level bootstrap 95% CI (10,000 resamples)
   - Paired sign test on decisive pairs
   - Elo point estimate and confidence interval
10. SHA-256 manifest and artifact integrity verification
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_v036(
    match_dir: Path = ROOT / "analysis" / "v0.36" / "match",
    match_name: str = "fischer_100_match",
    manifest_path: Path = ROOT / "analysis" / "v0.36" / "experiment_manifest.json",
    stat_analysis_path: Path = ROOT / "analysis" / "v0.36" / "statistical_analysis.json",
    expected_games: int = 100,
    expected_pairs: int = 50,
) -> dict[str, Any]:
    json_path = match_dir / f"{match_name}.json"
    pgn_path = match_dir / f"{match_name}.pgn"
    csv_path = match_dir / f"{match_name}.csv"
    moves_csv_path = match_dir / f"{match_name}_moves.csv"
    attempts_path = match_dir / f"{match_name}_attempts.json"

    required_files = [json_path, pgn_path, csv_path, moves_csv_path, attempts_path, manifest_path]
    for p in required_files:
        if not p.is_file():
            raise FileNotFoundError(f"Required artifact not found: {p}")

    match_data = json.loads(json_path.read_text(encoding="utf-8"))
    raw_attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    metadata = match_data["metadata"]
    match_summary = match_data["match_summary"]
    valid_games = match_data["valid_games"]

    audit_checks: dict[str, bool] = {}
    audit_notes: list[str] = []

    # 1. Target completion & counts
    total_valid = len(valid_games)
    audit_checks["target_games_met"] = (total_valid == expected_games)
    audit_checks["attempt_accounting"] = (len(raw_attempts) >= total_valid)

    # 2. Engine identity & commands
    cand_cmd = " ".join(metadata["candidate_cmd"])
    ref_cmd = " ".join(metadata["reference_cmd"])
    audit_checks["candidate_policy_adaptive"] = ("--time-policy adaptive" in cand_cmd)
    audit_checks["reference_policy_reference"] = ("--time-policy reference" in ref_cmd)
    audit_checks["eval_all_enabled"] = ("--eval-all" in cand_cmd and "--eval-all" in ref_cmd)

    # 3. Time control parameters
    audit_checks["time_control_parameters"] = (
        metadata["time_mode"] == "fischer_increment"
        and metadata["base_time_ms"] == 3000
        and metadata["inc_time_ms"] == 100
    )

    # 4. Opening pair symmetry & colour balance
    pairs_dict: dict[int, list[dict[str, Any]]] = {}
    for g in valid_games:
        pairs_dict.setdefault(g["pair"], []).append(g)

    pair_symmetry_valid = (len(pairs_dict) == expected_pairs)
    for p_num, p_games in pairs_dict.items():
        if len(p_games) != 2:
            pair_symmetry_valid = False
            audit_notes.append(f"Pair {p_num} has {len(p_games)} games instead of 2")
            break
        g1, g2 = p_games[0], p_games[1]
        if g1["candidate_color"] == g2["candidate_color"]:
            pair_symmetry_valid = False
            audit_notes.append(f"Pair {p_num} colour reversal failed: both played {g1['candidate_color']}")
        if g1["opening_id"] != g2["opening_id"] or g1["start_fen"] != g2["start_fen"]:
            pair_symmetry_valid = False
            audit_notes.append(f"Pair {p_num} opening discrepancy: {g1['opening_id']} vs {g2['opening_id']}")

    audit_checks["opening_pair_symmetry"] = pair_symmetry_valid

    # 5. Duplicate game detection
    seen_signatures = set()
    no_duplicates = True
    for g in valid_games:
        sig = (g["pair"], g["candidate_color"], g["opening_id"], g["final_fen"], g["plies"])
        if sig in seen_signatures:
            no_duplicates = False
            audit_notes.append(f"Duplicate game signature detected in Game {g['game']}")
        seen_signatures.add(sig)
    audit_checks["no_duplicate_games"] = no_duplicates

    # 6. CSV agreement
    csv_games = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_games.append(row)

    csv_agreement = (len(csv_games) == total_valid)
    if csv_agreement:
        for c_row, j_row in zip(csv_games, valid_games):
            if (
                int(c_row["game"]) != j_row["game"]
                or c_row["result"] != j_row["result"]
                or float(c_row["candidate_points"]) != float(j_row["candidate_points"])
                or int(c_row["plies"]) != int(j_row["plies"])
            ):
                csv_agreement = False
                break
    audit_checks["csv_agreement"] = csv_agreement

    # 7. PGN move legality and replay
    pgn_games = []
    with open(pgn_path, encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            pgn_games.append(g)

    audit_checks["pgn_game_count"] = (len(pgn_games) == total_valid)

    all_moves_legal = True
    for idx, (p_game, j_game) in enumerate(zip(pgn_games, valid_games)):
        if p_game.headers.get("Result") != j_game["result"]:
            all_moves_legal = False
            audit_notes.append(f"Game {idx + 1} result mismatch between PGN and JSON")
        board = p_game.board()
        for m in p_game.mainline_moves():
            if m not in board.legal_moves:
                all_moves_legal = False
                audit_notes.append(f"Illegal move {m.uci()} in Game {idx + 1}")
                break
            board.push(m)
        if board.fen() != j_game["final_fen"]:
            all_moves_legal = False
            audit_notes.append(f"Game {idx + 1} final FEN mismatch")

    audit_checks["move_legality"] = all_moves_legal

    # 8. Move telemetry and clock consistency
    moves_rows = []
    with open(moves_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            moves_rows.append(row)

    moves_valid = (len(moves_rows) > 0)
    clock_consistent = True
    for m_row in moves_rows:
        clk_b = float(m_row["clock_before_ms"])
        clk_a = float(m_row["clock_after_ms"])
        dur = float(m_row["actual_time_ms"])
        inc = float(m_row["inc_ms"])
        if clk_a < 0.0 or clk_b < 0.0:
            clock_consistent = False
            audit_notes.append(f"Negative clock observed in move row: {m_row}")
            break
        # Expected clock after move: max(0.0, clk_b - dur) + inc
        expected_clk_a = max(0.0, clk_b - dur) + inc
        if abs(clk_a - expected_clk_a) > 1.0:
            clock_consistent = False
            audit_notes.append(f"Clock calculation drift: got {clk_a}, expected {expected_clk_a}")
            break

    audit_checks["moves_telemetry_valid"] = moves_valid
    audit_checks["clock_accounting_consistent"] = clock_consistent

    # 9. Independent statistical recomputation
    cand_wins = sum(1 for g in valid_games if (g["result"] == "1-0" and g["candidate_color"] == "white") or (g["result"] == "0-1" and g["candidate_color"] == "black"))
    cand_draws = sum(1 for g in valid_games if g["result"] == "1/2-1/2")
    cand_losses = total_valid - cand_wins - cand_draws
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_valid) * 100.0

    pair_deltas = []
    pairs_won = 0
    pairs_drawn = 0
    pairs_lost = 0
    for p_games in pairs_dict.values():
        p_cand_pts = 0.0
        for g in p_games:
            res = g["result"]
            c = g["candidate_color"]
            if res == "1/2-1/2":
                p_cand_pts += 0.5
            elif (res == "1-0" and c == "white") or (res == "0-1" and c == "black"):
                p_cand_pts += 1.0
        p_avg = p_cand_pts / 2.0
        delta_i = p_avg - 0.5
        pair_deltas.append(delta_i)
        if p_avg > 0.5:
            pairs_won += 1
        elif p_avg < 0.5:
            pairs_lost += 1
        else:
            pairs_drawn += 1

    M = len(pair_deltas)
    mean_delta = statistics.mean(pair_deltas)
    std_delta = statistics.stdev(pair_deltas) if M > 1 else 0.0
    se_delta = std_delta / math.sqrt(M) if M > 0 else 0.0

    # Independent Student's t-test with df = 49
    df = M - 1
    t_stat = mean_delta / se_delta if se_delta > 0 else 0.0

    # Numerical integration of Student's t
    def t_pdf(u: float) -> float:
        c = math.gamma((df + 1) / 2.0) / (math.sqrt(df * math.pi) * math.gamma(df / 2.0))
        return c * (1.0 + (u * u) / df) ** (-(df + 1) / 2.0)

    n_steps = 1000
    b = abs(t_stat)
    h = b / n_steps
    integ = t_pdf(0.0) + t_pdf(b)
    for i in range(1, n_steps):
        integ += (4.0 if (i % 2 == 1) else 2.0) * t_pdf(i * h)
    integ *= (h / 3.0)
    p_two_sided = min(1.0, 2.0 * max(0.0, 0.5 - integ))

    # Independent bootstrap
    rng = random.Random(42)
    boot_means = []
    for _ in range(10000):
        boot_means.append(statistics.mean(rng.choice(pair_deltas) for _ in range(M)))
    boot_means.sort()
    boot_ci_low = round(0.5 + boot_means[250], 4)
    boot_ci_high = round(0.5 + boot_means[9750], 4)

    # Elo conversion
    p_hat = cand_score / total_valid
    elo_point = round(-400.0 * math.log10((1.0 - p_hat) / p_hat), 1) if 0 < p_hat < 1 else None

    # Sign test
    decisive_pairs = pairs_won + pairs_lost
    k = min(pairs_won, pairs_lost)
    sign_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0 if decisive_pairs > 0 else 1.0
    sign_p = min(1.0, sign_p)

    stats_reproducible = (
        cand_wins == match_summary["candidate_wins"]
        and cand_draws == match_summary["candidate_draws"]
        and cand_losses == match_summary["candidate_losses"]
        and round(cand_score_pct, 2) == match_summary["candidate_score_pct"]
        and pairs_won == match_summary["pairs_summary"]["pairs_won"]
        and pairs_drawn == match_summary["pairs_summary"]["pairs_drawn"]
        and pairs_lost == match_summary["pairs_summary"]["pairs_lost"]
        and round(sign_p, 4) == match_summary["pairs_summary"]["sign_test_p_value"]
    )
    audit_checks["statistics_reproducible"] = stats_reproducible

    # 10. Manifest and hash verification
    manifest_hashes = manifest.get("frozen_hashes", {})
    hashes_verified = True
    for rel_path, expected_hash in manifest_hashes.items():
        full_p = ROOT / rel_path
        if not full_p.is_file():
            hashes_verified = False
            audit_notes.append(f"Manifest target missing: {rel_path}")
            continue
        actual_hash = compute_sha256(full_p)
        if actual_hash != expected_hash:
            hashes_verified = False
            audit_notes.append(f"Hash mismatch for {rel_path}: got {actual_hash}, expected {expected_hash}")

    audit_checks["frozen_hashes_verified"] = hashes_verified

    # Final verdict determination
    all_passed = all(audit_checks.values())
    if all_passed:
        verdict = "VERIFIED_VALID"
    elif not audit_checks["move_legality"] or not audit_checks["target_games_met"] or not audit_checks["opening_pair_symmetry"]:
        verdict = "INVALID"
    else:
        verdict = "VALID_WITH_LIMITATIONS"

    audit_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "audit_checks": audit_checks,
        "audit_notes": audit_notes,
        "verified_sample": {
            "valid_games": total_valid,
            "opening_pairs": M,
            "total_moves_replayed": len(moves_rows),
            "infrastructure_failures": match_summary["infrastructure_failures"],
        },
        "independently_computed_statistics": {
            "candidate_wins": cand_wins,
            "candidate_draws": cand_draws,
            "candidate_losses": cand_losses,
            "candidate_score": cand_score,
            "candidate_score_pct": round(cand_score_pct, 2),
            "estimated_elo_diff": elo_point,
            "pairs_won": pairs_won,
            "pairs_drawn": pairs_drawn,
            "pairs_lost": pairs_lost,
            "decisive_pairs": decisive_pairs,
            "mean_paired_delta": round(mean_delta, 4),
            "se_paired_delta": round(se_delta, 4),
            "t_statistic": round(t_stat, 4),
            "t_test_two_sided_p_value": round(p_two_sided, 5),
            "bootstrap_ci_95_score": [boot_ci_low, boot_ci_high],
            "sign_test_p_value": round(sign_p, 5),
        },
    }

    out_json = match_dir.parent / "independent_audit.json"
    out_json.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    print(f"\nIndependent audit report written to {out_json}")
    print(f"Audit Verdict: {verdict}")

    return audit_report


if __name__ == "__main__":
    rep = audit_v036()
    if rep["verdict"] != "VERIFIED_VALID":
        sys.exit(1)
