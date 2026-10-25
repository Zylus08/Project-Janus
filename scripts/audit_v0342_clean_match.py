"""Project Janus v0.34.2 - Independent Clean Match Result Auditor.

Independently inspects and validates the raw match artifacts produced by scripts/match_v0342.py:
- Verifies exactly the planned valid games and complete colour-reversed pairs.
- Validates that every recorded move is strictly legal from the opening position.
- Verifies opening FENs and colour balance match benchmarks/openings.json.
- Checks that infrastructure failures and retries are accounted for and excluded from chess statistics.
- Cross-reconciles JSON, CSV, consolidated PGN, and per-game PGN files.
- Computes W-D-L, score percentage, score by color, pair outcomes, Elo point estimate.
- Performs pair-level bootstrap confidence interval (10,000 resamples) and paired hypothesis test.
- Outputs independent_audit.json and returns nonzero exit code on audit failure.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.match_v0342 import load_openings  # noqa: E402


def paired_bootstrap_ci(
    pair_scores: list[float],
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """Calculate pair-level bootstrap confidence interval for candidate score and Elo."""
    n_pairs = len(pair_scores)
    if n_pairs == 0:
        return {"cand_score_pct_ci": [0.0, 0.0], "elo_ci": [0.0, 0.0]}

    rng = random.Random(seed)
    bootstrap_score_pcts = []
    bootstrap_elos = []

    for _ in range(n_resamples):
        sample = [rng.choice(pair_scores) for _ in range(n_pairs)]
        total_pts = sum(sample)
        total_games = n_pairs * 2
        p_hat = total_pts / total_games
        pct = p_hat * 100.0
        bootstrap_score_pcts.append(pct)

        if 0 < p_hat < 1:
            elo = -400.0 * math.log10((1.0 - p_hat) / p_hat)
            bootstrap_elos.append(elo)

    bootstrap_score_pcts.sort()
    lower_idx = int((alpha / 2.0) * len(bootstrap_score_pcts))
    upper_idx = int((1.0 - alpha / 2.0) * len(bootstrap_score_pcts))
    score_pct_ci = [
        round(bootstrap_score_pcts[lower_idx], 2),
        round(bootstrap_score_pcts[upper_idx], 2),
    ]

    elo_ci = [None, None]
    if bootstrap_elos:
        bootstrap_elos.sort()
        e_lower = int((alpha / 2.0) * len(bootstrap_elos))
        e_upper = int((1.0 - alpha / 2.0) * len(bootstrap_elos))
        elo_ci = [round(bootstrap_elos[e_lower], 1), round(bootstrap_elos[e_upper], 1)]

    return {
        "n_resamples": n_resamples,
        "score_pct_95_ci": score_pct_ci,
        "elo_95_ci": elo_ci,
    }


def audit_match_directory(
    match_dir: Path,
    expected_games: int = 100,
    expected_pairs: int = 50,
    openings_file: str = "benchmarks/openings.json",
    seed: int = 42,
) -> dict[str, Any]:
    """Independently audit match artifacts and verify match integrity."""
    audit_start = datetime.now(timezone.utc).isoformat()
    findings: list[str] = []
    errors: list[str] = []

    json_path = match_dir / "clean_match_500ms.json"
    if not json_path.is_file():
        # Check smoke match or generic json
        json_candidates = list(match_dir.glob("*.json"))
        # Exclude independent_audit.json, attempts.json, manifest.json, *_summary.json
        main_candidates = [
            p for p in json_candidates
            if not p.name.endswith("_summary.json")
            and p.name not in ("attempts.json", "manifest.json", "independent_audit.json")
        ]
        if not main_candidates:
            errors.append(f"No match JSON found in {match_dir}")
            return {"audit_passed": False, "errors": errors}
        json_path = main_candidates[0]

    match_base_name = json_path.stem
    csv_path = match_dir / f"{match_base_name}.csv"
    pgn_path = match_dir / f"{match_base_name}.pgn"
    summary_path = match_dir / f"{match_base_name}_summary.json"
    manifest_path = match_dir / "manifest.json"
    attempts_path = match_dir / "attempts.json"
    per_game_dir = match_dir / "per_game_pgn"

    # Check presence of required artifacts
    for required_file in [csv_path, pgn_path, summary_path, manifest_path, attempts_path]:
        if not required_file.is_file():
            errors.append(f"Missing required artifact: {required_file.name}")

    if not per_game_dir.is_dir():
        errors.append("Missing per_game_pgn directory")

    if errors:
        return {"audit_passed": False, "errors": errors}

    # Load artifacts
    raw_json = json.loads(json_path.read_text(encoding="utf-8"))
    valid_games = raw_json.get("valid_games", [])
    raw_attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Load CSV
    csv_rows = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    # 1. Verify game and pair counts
    findings.append(f"Found {len(valid_games)} valid games in JSON, {len(csv_rows)} in CSV, {len(raw_attempts)} attempts in attempts.json.")
    if len(valid_games) != expected_games:
        errors.append(f"Expected {expected_games} valid games, found {len(valid_games)}.")

    if len(csv_rows) != len(valid_games):
        errors.append(f"Row count mismatch between JSON ({len(valid_games)}) and CSV ({len(csv_rows)}).")

    # 2. Verify opening positions against predefined benchmark suite
    expected_openings = load_openings(ROOT / openings_file, count=expected_pairs, seed=seed)
    pairs_in_games: dict[int, list[dict[str, Any]]] = {}

    for g_idx, g in enumerate(valid_games):
        g_num = g.get("game")
        p_num = g.get("pair")
        cand_col = g.get("candidate_color")
        start_fen = g.get("start_fen")

        if p_num is None or g_num is None:
            errors.append(f"Game {g_idx+1} missing game or pair number.")
            continue

        pairs_in_games.setdefault(p_num, []).append(g)

        # Expected opening for pair
        expected_op = expected_openings[p_num - 1]
        expected_fen = expected_op.get("fen", chess.STARTING_FEN)
        if start_fen != expected_fen:
            errors.append(f"Game {g_num} (Pair {p_num}) FEN mismatch! Found {start_fen}, expected {expected_fen}")

        # Expected candidate color: even index -> White, odd index -> Black
        expected_color = "white" if (g_num % 2 == 1) else "black"
        if cand_col != expected_color:
            errors.append(f"Game {g_num} color mismatch! Found {cand_col}, expected {expected_color}")

    # 3. Verify complete colour-reversed pairs
    complete_pairs = 0
    incomplete_pairs = 0
    pair_scores: list[float] = []
    pair_results: list[dict[str, Any]] = []

    for p_num in range(1, expected_pairs + 1):
        p_games = pairs_in_games.get(p_num, [])
        if len(p_games) != 2:
            errors.append(f"Pair {p_num} is incomplete! Contains {len(p_games)} valid games instead of 2.")
            incomplete_pairs += 1
            continue

        colors = {p_games[0].get("candidate_color"), p_games[1].get("candidate_color")}
        if colors != {"white", "black"}:
            errors.append(f"Pair {p_num} is not properly colour-reversed! Colors: {colors}")

        p_score = 0.0
        for pg in p_games:
            res = pg.get("result")
            col = pg.get("candidate_color")
            if res == "1/2-1/2":
                p_score += 0.5
            elif (res == "1-0" and col == "white") or (res == "0-1" and col == "black"):
                p_score += 1.0

        pair_scores.append(p_score)
        complete_pairs += 1

        outcome = "drawn"
        if p_score > 1.0:
            outcome = "won"
        elif p_score < 1.0:
            outcome = "lost"

        pair_results.append({
            "pair": p_num,
            "score": p_score,
            "outcome": outcome,
            "opening_id": p_games[0].get("opening_id"),
        })

    if complete_pairs != expected_pairs:
        errors.append(f"Expected {expected_pairs} complete valid pairs, found {complete_pairs}.")

    # 4. Move legality validation
    illegal_moves_found = 0
    for g in valid_games:
        g_num = g.get("game")
        start_fen = g.get("start_fen", chess.STARTING_FEN)
        board = chess.Board(start_fen)

        moves = g.get("moves", [])
        for m_dict in moves:
            uci_str = m_dict.get("move")
            try:
                move_obj = chess.Move.from_uci(uci_str)
                if move_obj not in board.legal_moves:
                    errors.append(f"Illegal move {uci_str} in game {g_num} at ply {board.ply() + 1}")
                    illegal_moves_found += 1
                    break
                board.push(move_obj)
            except Exception as exc:
                errors.append(f"Malformed move {uci_str} in game {g_num}: {exc}")
                illegal_moves_found += 1
                break

    if illegal_moves_found == 0:
        findings.append("All moves across all valid games verified strictly legal from their starting positions.")

    # 5. PGN reconciliation
    consolidated_pgn_games = 0
    with pgn_path.open(encoding="utf-8") as f:
        while True:
            pgn_g = chess.pgn.read_game(f)
            if pgn_g is None:
                break
            consolidated_pgn_games += 1

    if consolidated_pgn_games != len(valid_games):
        errors.append(f"Consolidated PGN contains {consolidated_pgn_games} games, expected {len(valid_games)}.")
    else:
        findings.append(f"Consolidated PGN matches valid games count ({consolidated_pgn_games}).")

    # Check per-game PGN directory
    per_game_files = list(per_game_dir.glob("game_*.pgn"))
    if len(per_game_files) != len(valid_games):
        errors.append(f"Per-game PGN directory contains {len(per_game_files)} files, expected {len(valid_games)}.")
    else:
        findings.append(f"Per-game PGN directory contains exactly {len(per_game_files)} individual PGN files.")

    # 6. Reconcile attempts and check for untracked failures
    infra_failures = [a for a in raw_attempts if a.get("status") == "infrastructure_failure"]
    valid_attempts = [a for a in raw_attempts if a.get("status") == "valid_chess"]

    findings.append(f"Total attempts: {len(raw_attempts)} (Valid: {len(valid_attempts)}, Infrastructure Failures: {len(infra_failures)}).")

    # Verify no infrastructure failure was recorded as a chess result in valid_games
    for vg in valid_games:
        if vg.get("status") != "valid_chess":
            errors.append(f"Game {vg.get('game')} in valid_games has status '{vg.get('status')}', not 'valid_chess'!")

    # 7. Independent calculation of candidate statistics
    cand_wins = 0
    cand_draws = 0
    cand_losses = 0
    by_color = {
        "white": {"wins": 0, "draws": 0, "losses": 0, "score": 0.0, "games": 0},
        "black": {"wins": 0, "draws": 0, "losses": 0, "score": 0.0, "games": 0},
    }

    cand_depths = []
    base_depths = []
    cand_times = []
    base_times = []
    cand_nodes = []
    base_nodes = []

    for vg in valid_games:
        res = vg.get("result")
        col = vg.get("candidate_color")
        by_color[col]["games"] += 1

        if res == "1-0":
            if col == "white":
                cand_wins += 1
                by_color["white"]["wins"] += 1
                by_color["white"]["score"] += 1.0
            else:
                cand_losses += 1
                by_color["black"]["losses"] += 1
        elif res == "0-1":
            if col == "white":
                cand_losses += 1
                by_color["white"]["losses"] += 1
            else:
                cand_wins += 1
                by_color["black"]["wins"] += 1
                by_color["black"]["score"] += 1.0
        elif res == "1/2-1/2":
            cand_draws += 1
            by_color[col]["draws"] += 1
            by_color[col]["score"] += 0.5

        if vg.get("avg_cand_depth") is not None:
            cand_depths.append(vg["avg_cand_depth"])
        if vg.get("avg_base_depth") is not None:
            base_depths.append(vg["avg_base_depth"])
        if vg.get("avg_cand_move_time") is not None:
            cand_times.append(vg["avg_cand_move_time"])
        if vg.get("avg_base_move_time") is not None:
            base_times.append(vg["avg_base_move_time"])
        if vg.get("avg_cand_nodes") is not None:
            cand_nodes.append(vg["avg_cand_nodes"])
        if vg.get("avg_base_nodes") is not None:
            base_nodes.append(vg["avg_base_nodes"])

    total_valid = len(valid_games)
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_valid * 100.0) if total_valid > 0 else 0.0

    # Elo difference point estimate
    elo_diff = None
    elo_analytical_ci = None
    if total_valid > 0:
        p_hat = cand_score / total_valid
        if 0 < p_hat < 1:
            elo_diff = -400.0 * math.log10((1.0 - p_hat) / p_hat)
            var_p = (p_hat * (1.0 - p_hat)) / total_valid
            se_p = math.sqrt(var_p)
            se_elo = (400.0 / (math.log(10) * p_hat * (1.0 - p_hat))) * se_p
            elo_analytical_ci = [round(elo_diff - 1.96 * se_elo, 1), round(elo_diff + 1.96 * se_elo, 1)]

    # Pair statistics
    pairs_won = sum(1 for pr in pair_results if pr["outcome"] == "won")
    pairs_drawn = sum(1 for pr in pair_results if pr["outcome"] == "drawn")
    pairs_lost = sum(1 for pr in pair_results if pr["outcome"] == "lost")
    decisive_pairs = pairs_won + pairs_lost

    # Paired sign test
    sign_test_p = None
    if decisive_pairs > 0:
        k = min(pairs_won, pairs_lost)
        sign_test_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        sign_test_p = min(1.0, sign_test_p)

    # Paired t-test on pair score differences
    # Pair difference: candidate score in pair - 1.0 (since reference score is 2.0 - pair score)
    # pair diff ranges from -1.0 to +1.0
    pair_diffs = [s - 1.0 for s in pair_scores]
    t_test_p = None
    t_stat = None
    if len(pair_diffs) > 1:
        mean_diff = sum(pair_diffs) / len(pair_diffs)
        var_diff = sum((d - mean_diff) ** 2 for d in pair_diffs) / (len(pair_diffs) - 1)
        se_diff = math.sqrt(var_diff / len(pair_diffs)) if var_diff > 0 else 0.0
        if se_diff > 0:
            t_stat = mean_diff / se_diff
            # Approximate two-tailed p-value using normal distribution for n=50
            z = abs(t_stat)
            t_test_p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))

    # Bootstrap CI
    bootstrap = paired_bootstrap_ci(pair_scores, n_resamples=10000, seed=seed)

    audit_passed = len(errors) == 0

    audit_report = {
        "audit_timestamp_utc": audit_start,
        "audit_passed": audit_passed,
        "errors": errors,
        "findings": findings,
        "counts": {
            "expected_games": expected_games,
            "expected_pairs": expected_pairs,
            "valid_completed_games": total_valid,
            "total_attempts": len(raw_attempts),
            "infrastructure_failures": len(infra_failures),
            "complete_valid_pairs": complete_pairs,
            "incomplete_pairs": incomplete_pairs,
        },
        "playing_strength": {
            "candidate_wins": cand_wins,
            "candidate_draws": cand_draws,
            "candidate_losses": cand_losses,
            "candidate_score": cand_score,
            "candidate_score_pct": round(cand_score_pct, 2),
            "estimated_elo_diff": round(elo_diff, 1) if elo_diff is not None else None,
            "elo_analytical_95_ci": elo_analytical_ci,
            "elo_bootstrap_95_ci": bootstrap["elo_95_ci"],
            "score_pct_bootstrap_95_ci": bootstrap["score_pct_95_ci"],
            "by_color": {
                "white": {
                    "wins": by_color["white"]["wins"],
                    "draws": by_color["white"]["draws"],
                    "losses": by_color["white"]["losses"],
                    "score_pts": by_color["white"]["score"],
                    "score_pct": round(by_color["white"]["score"] / by_color["white"]["games"] * 100.0, 2) if by_color["white"]["games"] > 0 else 0.0,
                    "games": by_color["white"]["games"],
                },
                "black": {
                    "wins": by_color["black"]["wins"],
                    "draws": by_color["black"]["draws"],
                    "losses": by_color["black"]["losses"],
                    "score_pts": by_color["black"]["score"],
                    "score_pct": round(by_color["black"]["score"] / by_color["black"]["games"] * 100.0, 2) if by_color["black"]["games"] > 0 else 0.0,
                    "games": by_color["black"]["games"],
                },
            },
        },
        "paired_analysis": {
            "total_pairs": len(pair_scores),
            "pairs_won": pairs_won,
            "pairs_drawn": pairs_drawn,
            "pairs_lost": pairs_lost,
            "decisive_pairs": decisive_pairs,
            "paired_sign_test_p": round(sign_test_p, 4) if sign_test_p is not None else None,
            "paired_t_stat": round(t_stat, 3) if t_stat is not None else None,
            "paired_t_test_p": round(t_test_p, 4) if t_test_p is not None else None,
            "pair_results": pair_results,
        },
        "performance_telemetry": {
            "avg_candidate_depth": round(sum(cand_depths) / len(cand_depths), 2) if cand_depths else None,
            "avg_reference_depth": round(sum(base_depths) / len(base_depths), 2) if base_depths else None,
            "avg_candidate_movetime_s": round(sum(cand_times) / len(cand_times), 4) if cand_times else None,
            "avg_reference_movetime_s": round(sum(base_times) / len(base_times), 4) if base_times else None,
            "avg_candidate_nodes": round(sum(cand_nodes) / len(cand_nodes), 0) if cand_nodes else None,
            "avg_reference_nodes": round(sum(base_nodes) / len(base_nodes), 0) if base_nodes else None,
        },
        "infrastructure_audit": {
            "failure_count": len(infra_failures),
            "failures": infra_failures,
        },
    }

    # Save audit report to json
    audit_out_path = match_dir / "independent_audit.json"
    audit_out_path.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    print(f"Independent audit report written to: {audit_out_path}")

    return audit_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Janus v0.34.2 Independent Match Auditor")
    parser.add_argument("--match-dir", type=str, default="analysis/v0.34_2/clean_match")
    parser.add_argument("--expected-games", type=int, default=100)
    parser.add_argument("--expected-pairs", type=int, default=50)
    parser.add_argument("--openings", type=str, default="benchmarks/openings.json")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    match_dir = ROOT / args.match_dir
    report = audit_match_directory(
        match_dir=match_dir,
        expected_games=args.expected_games,
        expected_pairs=args.expected_pairs,
        openings_file=args.openings,
        seed=args.seed,
    )

    print("\n" + "=" * 65)
    print("INDEPENDENT AUDIT VERDICT")
    print("=" * 65)
    print(f"Passed: {report['audit_passed']}")
    if report.get("errors"):
        print("\nERRORS DETECTED:")
        for err in report["errors"]:
            print(f"  [ERROR] {err}")
    if report.get("findings"):
        print("\nFINDINGS:")
        for f in report["findings"]:
            print(f"  [OK] {f}")

    if report.get("audit_passed"):
        ps = report["playing_strength"]
        pa = report["paired_analysis"]
        print(f"\nCandidate Score: {ps['candidate_wins']}W / {ps['candidate_draws']}D / {ps['candidate_losses']}L ({ps['candidate_score_pct']}%)")
        elo_str = f"{ps['estimated_elo_diff']:+.1f}" if ps['estimated_elo_diff'] is not None else "N/A (unbounded)"
        print(f"Estimated Elo diff: {elo_str} (Bootstrap 95% CI: {ps['elo_bootstrap_95_ci']})")
        print(f"Pairs: {pa['pairs_won']}W / {pa['pairs_drawn']}D / {pa['pairs_lost']}L (Sign test p={pa['paired_sign_test_p']})")
        print(f"Color: White {ps['by_color']['white']['score_pct']}% vs Black {ps['by_color']['black']['score_pct']}%")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
