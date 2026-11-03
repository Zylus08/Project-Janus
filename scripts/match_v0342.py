"""Project Janus v0.34.2 - Robust Fixed-Time Match Harness with Supervised Engine Lifecycle.

Executes controlled, colour-balanced, paired matches between:
- Reference: Janus v0.30 (commit 05de411) from .worktree_v030
- Candidate: Janus v0.34 (tapered evaluation + evaluation features) with --eval-all
under fixed movetime budgets (e.g. 500ms).

Key reliability enhancements in v0.34.2:
1. Fresh SupervisedEngineSession spawned and closed per game.
2. Explicit failure detection: startup crash, move timeout, protocol error, process termination.
3. Strict separation of chess results from infrastructure failures.
4. Preserved audit log of every attempt and retry.
5. Incomplete pairs excluded from paired analysis.
6. Nonzero exit code if requested valid games/pairs target is not met.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from janus.engine_session import (  # noqa: E402
    EngineError,
    EngineInitializationError,
    EngineProcessError,
    EngineProtocolError,
    EngineTimeoutError,
    MoveResult,
    SupervisedEngineSession,
)


def load_openings(openings_path: Path, count: int, seed: int = 42) -> list[dict[str, Any]]:
    """Load and deterministically select opening positions for paired matches."""
    count = max(1, count)
    if openings_path.is_file():
        raw = json.loads(openings_path.read_text(encoding="utf-8"))
        if not raw:
            return [{"id": "startpos", "name": "Standard startpos", "fen": chess.STARTING_FEN}] * count
        rng = random.Random(seed)
        indices = list(range(len(raw)))
        rng.shuffle(indices)
        if count <= len(raw):
            return [raw[i] for i in indices[:count]]
        selected = [raw[i] for i in indices]
        while len(selected) < count:
            selected.extend(raw)
        return selected[:count]
    return [{"id": "startpos", "name": "Standard startpos", "fen": chess.STARTING_FEN}] * count


def summarize_match(
    valid_games: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    planned_games: int,
    planned_pairs: int,
) -> dict[str, Any]:
    """Calculate aggregate and pair-level statistics from valid games only.

    Infrastructure failures and retried attempts are counted in attempt telemetry
    but strictly excluded from chess playing-strength ratings.
    """
    cand_wins = 0
    cand_draws = 0
    cand_losses = 0

    by_color = {
        "white": {"wins": 0, "draws": 0, "losses": 0, "games": 0, "score_pts": 0.0},
        "black": {"wins": 0, "draws": 0, "losses": 0, "games": 0, "score_pts": 0.0},
    }

    pairs_dict: dict[int, list[dict[str, Any]]] = {}

    for row in valid_games:
        color = row.get("candidate_color", "white")
        res = row.get("result")
        p_num = row.get("pair")

        if p_num is not None:
            pairs_dict.setdefault(p_num, []).append(row)

        if res == "1-0":
            if color == "white":
                cand_wins += 1
                by_color["white"]["wins"] += 1
                by_color["white"]["score_pts"] += 1.0
            else:
                cand_losses += 1
                by_color["black"]["losses"] += 1
        elif res == "0-1":
            if color == "white":
                cand_losses += 1
                by_color["white"]["losses"] += 1
            else:
                cand_wins += 1
                by_color["black"]["wins"] += 1
                by_color["black"]["score_pts"] += 1.0
        elif res == "1/2-1/2":
            cand_draws += 1
            by_color[color]["draws"] += 1
            by_color[color]["score_pts"] += 0.5

        by_color[color]["games"] += 1

    total_valid = cand_wins + cand_draws + cand_losses
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_valid * 100.0) if total_valid > 0 else 0.0

    # Pair outcomes - only pairs with exactly 2 valid games count
    pair_outcomes = {"won": 0, "drawn": 0, "lost": 0, "incomplete": 0}
    pair_diffs: list[float] = []

    for p_num in range(1, planned_pairs + 1):
        p_rows = pairs_dict.get(p_num, [])
        if len(p_rows) == 2:
            p_score = 0.0
            for r in p_rows:
                res = r.get("result")
                c = r.get("candidate_color")
                if res == "1/2-1/2":
                    p_score += 0.5
                elif (res == "1-0" and c == "white") or (res == "0-1" and c == "black"):
                    p_score += 1.0

            if p_score > 1.0:
                pair_outcomes["won"] += 1
                pair_diffs.append(+1.0)
            elif p_score < 1.0:
                pair_outcomes["lost"] += 1
                pair_diffs.append(-1.0)
            else:
                pair_outcomes["drawn"] += 1
                pair_diffs.append(0.0)
        else:
            pair_outcomes["incomplete"] += 1

    # Statistical estimates
    elo_diff = None
    elo_ci = None
    if total_valid > 0:
        p_hat = cand_score / total_valid
        if 0 < p_hat < 1:
            elo_diff = -400.0 * math.log10((1.0 - p_hat) / p_hat)
            var_p = (p_hat * (1.0 - p_hat)) / total_valid
            se_p = math.sqrt(var_p)
            se_elo = (400.0 / (math.log(10) * p_hat * (1.0 - p_hat))) * se_p
            elo_ci = [round(elo_diff - 1.96 * se_elo, 1), round(elo_diff + 1.96 * se_elo, 1)]

    # Paired sign test
    decisive_pairs = pair_outcomes["won"] + pair_outcomes["lost"]
    sign_test_p = None
    if decisive_pairs > 0:
        k = min(pair_outcomes["won"], pair_outcomes["lost"])
        sign_test_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        sign_test_p = min(1.0, sign_test_p)

    # Attempt counts
    infra_failures = [a for a in attempts if a.get("status") == "infrastructure_failure"]
    retried_attempts = [a for a in attempts if a.get("attempt_number", 1) > 1]

    return {
        "planned_games": planned_games,
        "planned_pairs": planned_pairs,
        "attempted_games": len(attempts),
        "valid_completed_games": total_valid,
        "infrastructure_failures": len(infra_failures),
        "retried_attempts": len(retried_attempts),
        "complete_valid_pairs": len(pair_diffs),
        "incomplete_pairs": pair_outcomes["incomplete"],
        "target_met": (total_valid == planned_games and len(pair_diffs) == planned_pairs),
        "candidate_wins": cand_wins,
        "candidate_draws": cand_draws,
        "candidate_losses": cand_losses,
        "candidate_score": cand_score,
        "candidate_score_pct": round(cand_score_pct, 2),
        "estimated_elo_diff": round(elo_diff, 1) if elo_diff is not None else None,
        "elo_95_ci": elo_ci,
        "by_color": by_color,
        "pairs_summary": {
            "total_planned_pairs": planned_pairs,
            "completed_valid_pairs": len(pair_diffs),
            "pairs_won": pair_outcomes["won"],
            "pairs_drawn": pair_outcomes["drawn"],
            "pairs_lost": pair_outcomes["lost"],
            "decisive_pairs": decisive_pairs,
            "sign_test_p_value": round(sign_test_p, 4) if sign_test_p is not None else None,
        },
    }


def play_supervised_game(
    base_session: SupervisedEngineSession,
    cand_session: SupervisedEngineSession,
    game_number: int,
    pair_number: int,
    attempt_number: int,
    cand_color: chess.Color,
    movetime_ms: int,
    max_plies: int,
    start_fen: str | None,
    opening_id: str,
    opening_name: str,
) -> tuple[Optional[chess.pgn.Game], dict[str, Any]]:
    """Play a single game between two SupervisedEngineSessions.

    Returns:
        (game_pgn, attempt_record)
        If an infrastructure error occurs, game_pgn is None and attempt_record
        has status="infrastructure_failure" with detailed diagnostic fields.
    """
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen else chess.Board()

    white_is_cand = (cand_color == chess.WHITE)
    white_session = cand_session if white_is_cand else base_session
    black_session = base_session if white_is_cand else cand_session

    white_name = cand_session.name if white_is_cand else base_session.name
    black_name = base_session.name if white_is_cand else cand_session.name

    game = chess.pgn.Game()
    if start_fen and start_fen != chess.STARTING_FEN:
        game.setup(board)

    game.headers["Event"] = "Project Janus v0.34.2 Supervised Playing-Strength Match"
    game.headers["Site"] = "Local"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = f"{game_number}.{attempt_number}"
    game.headers["White"] = white_name
    game.headers["Black"] = black_name
    game.headers["TimeControl"] = f"movetime {movetime_ms}ms"
    game.headers["Opening"] = f"{opening_id} ({opening_name})"

    node = game
    result_string = None
    termination_reason = None
    infrastructure_error: Optional[dict[str, Any]] = None

    move_log: list[dict[str, Any]] = []
    cand_depths = []
    base_depths = []
    cand_times = []
    base_times = []
    cand_nodes_list = []
    base_nodes_list = []

    # Send ucinewgame to both sessions
    try:
        white_session.ucinewgame()
        black_session.ucinewgame()
    except EngineError as exc:
        failed_session = white_session if not white_session.is_alive() else black_session
        return None, {
            "game": game_number,
            "pair": pair_number,
            "attempt_number": attempt_number,
            "status": "infrastructure_failure",
            "failure_category": type(exc).__name__,
            "failed_engine": failed_session.name,
            "error_message": str(exc),
            "exit_code": failed_session.process.poll() if failed_session.process else -1,
            "stderr_snippet": failed_session.get_stderr_snippet(),
            "opening_id": opening_id,
            "candidate_color": "white" if cand_color == chess.WHITE else "black",
            "start_fen": start_fen or chess.STARTING_FEN,
            "duration_seconds": round(time.monotonic() - game_start, 3),
        }

    for ply in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break

        is_cand_turn = (board.turn == cand_color)
        current_session = cand_session if is_cand_turn else base_session
        curr_name = current_session.name

        try:
            m_res: MoveResult = current_session.play_move(board, movetime_ms=movetime_ms)
        except EngineError as exc:
            # Infrastructure failure!
            infrastructure_error = {
                "category": type(exc).__name__,
                "engine": curr_name,
                "message": str(exc),
                "ply": ply + 1,
                "exit_code": current_session.process.poll() if current_session.process else -1,
                "stderr_snippet": current_session.get_stderr_snippet(),
            }
            break

        if is_cand_turn:
            cand_depths.append(m_res.depth)
            cand_times.append(m_res.time_s)
            cand_nodes_list.append(m_res.nodes)
        else:
            base_depths.append(m_res.depth)
            base_times.append(m_res.time_s)
            base_nodes_list.append(m_res.nodes)

        move_log.append({
            "ply": ply + 1,
            "player": curr_name,
            "color": "white" if board.turn == chess.WHITE else "black",
            "move": m_res.move.uci(),
            "time_s": round(m_res.time_s, 3),
            "depth": m_res.depth,
            "nodes": m_res.nodes,
        })

        node = node.add_variation(m_res.move)
        board.push(m_res.move)

    duration = round(time.monotonic() - game_start, 2)

    if infrastructure_error is not None:
        return None, {
            "game": game_number,
            "pair": pair_number,
            "attempt_number": attempt_number,
            "status": "infrastructure_failure",
            "failure_category": infrastructure_error["category"],
            "failed_engine": infrastructure_error["engine"],
            "error_message": infrastructure_error["message"],
            "failed_ply": infrastructure_error["ply"],
            "exit_code": infrastructure_error["exit_code"],
            "stderr_snippet": infrastructure_error["stderr_snippet"],
            "opening_id": opening_id,
            "candidate_color": "white" if cand_color == chess.WHITE else "black",
            "start_fen": start_fen or chess.STARTING_FEN,
            "duration_seconds": duration,
        }

    # Evaluate chess termination
    if board.is_checkmate():
        result_string = "0-1" if board.turn == chess.WHITE else "1-0"
        termination_reason = "checkmate"
    elif board.is_stalemate():
        result_string = "1/2-1/2"
        termination_reason = "stalemate"
    elif board.is_insufficient_material():
        result_string = "1/2-1/2"
        termination_reason = "insufficient material"
    elif board.is_fifty_moves():
        result_string = "1/2-1/2"
        termination_reason = "fifty moves rule"
    elif board.is_repetition(3):
        result_string = "1/2-1/2"
        termination_reason = "threefold repetition"
    elif board.ply() >= max_plies:
        result_string = "1/2-1/2"
        termination_reason = f"max plies reached ({max_plies})"
    else:
        result_string = "1/2-1/2"
        termination_reason = "draw by agreement/claim"

    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    cand_score = 0.5
    if result_string == "1-0":
        cand_score = 1.0 if cand_color == chess.WHITE else 0.0
    elif result_string == "0-1":
        cand_score = 0.0 if cand_color == chess.WHITE else 1.0

    record = {
        "game": game_number,
        "pair": pair_number,
        "attempt_number": attempt_number,
        "status": "valid_chess",
        "opening_id": opening_id,
        "opening_name": opening_name,
        "candidate_color": "white" if cand_color == chess.WHITE else "black",
        "white": white_name,
        "black": black_name,
        "result": result_string,
        "candidate_score": cand_score,
        "termination": termination_reason,
        "plies": board.ply(),
        "duration_seconds": duration,
        "movetime_ms": movetime_ms,
        "start_fen": start_fen or chess.STARTING_FEN,
        "avg_cand_depth": round(sum(cand_depths) / len(cand_depths), 2) if cand_depths else None,
        "avg_base_depth": round(sum(base_depths) / len(base_depths), 2) if base_depths else None,
        "avg_cand_move_time": round(sum(cand_times) / len(cand_times), 4) if cand_times else None,
        "avg_base_move_time": round(sum(base_times) / len(base_times), 4) if base_times else None,
        "avg_cand_nodes": round(sum(cand_nodes_list) / len(cand_nodes_list), 0) if cand_nodes_list else None,
        "avg_base_nodes": round(sum(base_nodes_list) / len(base_nodes_list), 0) if base_nodes_list else None,
        "moves": move_log,
    }

    return game, record


def write_clean_match_reports(
    output_dir: Path,
    match_name: str,
    valid_games: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    metadata: dict[str, Any],
    elapsed_so_far: float,
    planned_games: int,
    planned_pairs: int,
) -> dict[str, Any]:
    """Safely and atomically write JSON, CSV, summary, manifest, and attempts."""
    summary = summarize_match(
        valid_games=valid_games,
        attempts=attempts,
        planned_games=planned_games,
        planned_pairs=planned_pairs,
    )

    full_payload = {
        "metadata": {
            **metadata,
            "elapsed_seconds": round(elapsed_so_far, 1),
            "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        },
        "summary": summary,
        "valid_games": valid_games,
        "attempts": attempts,
    }

    json_path = output_dir / f"{match_name}.json"
    csv_path = output_dir / f"{match_name}.csv"
    summary_path = output_dir / f"{match_name}_summary.json"
    manifest_path = output_dir / "manifest.json"
    attempts_path = output_dir / "attempts.json"

    # Write full JSON atomically
    tmp_json = json_path.with_suffix(".tmp.json")
    with tmp_json.open("w", encoding="utf-8") as f:
        json.dump(full_payload, f, indent=2)
    tmp_json.replace(json_path)

    # Write summary JSON atomically
    tmp_sum = summary_path.with_suffix(".tmp.json")
    with tmp_sum.open("w", encoding="utf-8") as f:
        json.dump({"metadata": full_payload["metadata"], "summary": summary}, f, indent=2)
    tmp_sum.replace(summary_path)

    # Write manifest JSON atomically
    tmp_man = manifest_path.with_suffix(".tmp.json")
    with tmp_man.open("w", encoding="utf-8") as f:
        json.dump(full_payload["metadata"], f, indent=2)
    tmp_man.replace(manifest_path)

    # Write attempts JSON atomically
    tmp_att = attempts_path.with_suffix(".tmp.json")
    with tmp_att.open("w", encoding="utf-8") as f:
        json.dump(attempts, f, indent=2)
    tmp_att.replace(attempts_path)

    # Write valid games CSV atomically
    if valid_games:
        tmp_csv = csv_path.with_suffix(".tmp.csv")
        fieldnames = [
            "game", "pair", "attempt_number", "status", "opening_id", "opening_name",
            "candidate_color", "white", "black", "result", "candidate_score",
            "termination", "plies", "duration_seconds", "movetime_ms", "start_fen",
            "avg_cand_depth", "avg_base_depth", "avg_cand_move_time",
            "avg_base_move_time", "avg_cand_nodes", "avg_base_nodes"
        ]
        with tmp_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(valid_games)
        tmp_csv.replace(csv_path)

    return summary


def run_clean_match(
    games: int = 100,
    movetime_ms: int = 500,
    max_plies: int = 200,
    seed: int = 42,
    match_name: str = "clean_match_500ms",
    openings_file: str = "benchmarks/openings.json",
    base_dir_path: str = ".worktree_v030",
    cand_dir_path: str = ".",
    output_dir_path: str = "analysis/v0.34_2/clean_match",
    max_retries_per_slot: int = 2,
    max_match_failures: int = 5,
    session_factory: Optional[Callable[..., SupervisedEngineSession]] = None,
    custom_base_cmd: Optional[list[str]] = None,
    custom_cand_cmd: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Execute fixed-time paired match using supervised per-game process lifecycles.

    Guarantees:
    - Never overwrites historical match datasets.
    - Spawns fresh engine processes per game.
    - Cleans up failed processes immediately.
    - Records all attempts in attempts.json.
    - Excludes infrastructure failures from chess statistics.
    - Exits nonzero if the valid game target is not met.
    """
    base_dir = os.path.abspath(base_dir_path)
    cand_dir = os.path.abspath(cand_dir_path)
    output_dir = ROOT / output_dir_path
    output_dir.mkdir(parents=True, exist_ok=True)

    per_game_pgn_dir = output_dir / "per_game_pgn"
    per_game_pgn_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.isdir(base_dir) and session_factory is None:
        raise FileNotFoundError(f"Reference v0.30 worktree not found at {base_dir}")

    json_path = output_dir / f"{match_name}.json"
    pgn_path = output_dir / f"{match_name}.pgn"

    valid_games: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []

    # Resume support if clean_match.json already exists
    if json_path.is_file():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
            valid_games = existing.get("valid_games", [])
            attempts = existing.get("attempts", [])
            print(f"Resuming clean match: {len(valid_games)} valid games already recorded...")
        except Exception:
            valid_games = []
            attempts = []

    pairs_count = max(1, math.ceil(games / 2.0))
    openings_path = ROOT / openings_file
    openings = load_openings(openings_path, count=pairs_count, seed=seed)

    env_base = os.environ.copy()
    env_base["PYTHONPATH"] = os.path.join(base_dir, "src")

    base_cmd = custom_base_cmd or [sys.executable, "-m", "janus.uci", "--name", "Janus-v0.30"]
    cand_cmd = custom_cand_cmd or [sys.executable, "-m", "janus.uci", "--name", "Janus-v0.34", "--eval-all"]

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "05de4112c27ec6b2f36a9c3be29b47a993a0a7dc",
        "baseline_name": "Janus-v0.30",
        "candidate_commit": "f2e47be",
        "candidate_name": "Janus-v0.34",
        "candidate_config": "CONFIG_V034_TAPERED",
        "time_control": f"fixed movetime {movetime_ms}ms",
        "movetime_ms": movetime_ms,
        "max_plies": max_plies,
        "total_games_requested": games,
        "pairs_requested": pairs_count,
        "seed": seed,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "output_directory": str(output_dir),
    }

    start_time = time.monotonic()
    total_failures_encountered = sum(1 for a in attempts if a.get("status") == "infrastructure_failure")

    make_session = session_factory or (
        lambda cmd, cwd, env, name: SupervisedEngineSession(cmd=cmd, cwd=cwd, env=env, name=name)
    )

    completed_game_indices = {g["game"] - 1 for g in valid_games}

    # Consolidated PGN mode
    pgn_mode = "a" if (valid_games and pgn_path.is_file()) else "w"
    pgn_file = pgn_path.open(pgn_mode, encoding="utf-8")

    try:
        for i in range(games):
            if i in completed_game_indices:
                continue

            pair_idx = i // 2
            opening = openings[pair_idx]
            cand_color = chess.WHITE if (i % 2 == 0) else chess.BLACK
            game_number = i + 1
            pair_number = pair_idx + 1

            slot_success = False
            for attempt_idx in range(1, max_retries_per_slot + 2):
                if total_failures_encountered >= max_match_failures:
                    print(f"ABORTING MATCH: Cumulative infrastructure failures ({total_failures_encountered}) reached limit ({max_match_failures}).")
                    break

                # Spawn fresh engines for this attempt
                base_sess = make_session(cmd=base_cmd, cwd=base_dir, env=env_base, name="Janus-v0.30")
                cand_sess = make_session(cmd=cand_cmd, cwd=cand_dir, env=None, name="Janus-v0.34")

                try:
                    base_sess.start()
                    cand_sess.start()
                    base_sess.configure({"Hash": 128})
                    cand_sess.configure({"Hash": 128})
                except EngineError as init_exc:
                    total_failures_encountered += 1
                    failed_sess = base_sess if not base_sess.is_alive() else cand_sess
                    fail_rec = {
                        "game": game_number,
                        "pair": pair_number,
                        "attempt_number": attempt_idx,
                        "status": "infrastructure_failure",
                        "failure_category": type(init_exc).__name__,
                        "failed_engine": failed_sess.name,
                        "error_message": str(init_exc),
                        "exit_code": failed_sess.process.poll() if failed_sess.process else -1,
                        "stderr_snippet": failed_sess.get_stderr_snippet(),
                        "opening_id": opening.get("id", "startpos"),
                        "candidate_color": "white" if cand_color == chess.WHITE else "black",
                        "start_fen": opening.get("fen", chess.STARTING_FEN),
                        "duration_seconds": 0.0,
                    }
                    attempts.append(fail_rec)
                    print(f"Game {game_number:3d} Attempt {attempt_idx} FAILED during init: {init_exc}", flush=True)
                    base_sess.close()
                    cand_sess.close()
                    continue

                game_obj, rec = play_supervised_game(
                    base_session=base_sess,
                    cand_session=cand_sess,
                    game_number=game_number,
                    pair_number=pair_number,
                    attempt_number=attempt_idx,
                    cand_color=cand_color,
                    movetime_ms=movetime_ms,
                    max_plies=max_plies,
                    start_fen=opening.get("fen"),
                    opening_id=opening.get("id", "startpos"),
                    opening_name=opening.get("name", "Standard startpos"),
                )

                # Clean up processes immediately
                base_sess.close()
                cand_sess.close()

                attempts.append(rec)

                if rec["status"] == "valid_chess" and game_obj is not None:
                    valid_games.append(rec)
                    slot_success = True

                    # Write per-game PGN
                    single_pgn_path = per_game_pgn_dir / f"game_{game_number:03d}.pgn"
                    single_pgn_path.write_text(str(game_obj) + "\n\n", encoding="utf-8")

                    # Append to consolidated PGN
                    pgn_file.write(str(game_obj) + "\n\n")
                    pgn_file.flush()

                    elapsed_so_far = time.monotonic() - start_time
                    write_clean_match_reports(
                        output_dir=output_dir,
                        match_name=match_name,
                        valid_games=valid_games,
                        attempts=attempts,
                        metadata=metadata,
                        elapsed_so_far=elapsed_so_far,
                        planned_games=games,
                        planned_pairs=pairs_count,
                    )

                    print(
                        f"Game {game_number:3d}/{games} [Pair {pair_number:2d} | {'W' if cand_color == chess.WHITE else 'B'}] "
                        f"(Attempt {attempt_idx}): "
                        f"Result: {rec['result']:7s} ({rec['candidate_score']:.1f}) | "
                        f"Plies: {rec['plies']:3d} | {rec['duration_seconds']:5.1f}s | "
                        f"CandDepth: {rec['avg_cand_depth'] or 0:.1f} | BaseDepth: {rec['avg_base_depth'] or 0:.1f}",
                        flush=True,
                    )
                    break
                else:
                    total_failures_encountered += 1
                    print(
                        f"Game {game_number:3d} Attempt {attempt_idx} FAILED mid-game: "
                        f"{rec.get('failure_category')}: {rec.get('error_message')}",
                        flush=True,
                    )

            if not slot_success:
                print(f"Game slot {game_number} could not be completed after attempts. Aborting match loop.", flush=True)
                break

    finally:
        pgn_file.close()

    elapsed_so_far = time.monotonic() - start_time
    final_summary = write_clean_match_reports(
        output_dir=output_dir,
        match_name=match_name,
        valid_games=valid_games,
        attempts=attempts,
        metadata=metadata,
        elapsed_so_far=elapsed_so_far,
        planned_games=games,
        planned_pairs=pairs_count,
    )

    print("\n" + "=" * 65, flush=True)
    print(f"MATCH FINISHED: {len(valid_games)}/{games} valid games, {len(attempts)} attempts", flush=True)
    print(f"Infrastructure Failures: {final_summary['infrastructure_failures']}", flush=True)
    print(f"Candidate: {final_summary['candidate_wins']}W / {final_summary['candidate_draws']}D / {final_summary['candidate_losses']}L ({final_summary['candidate_score_pct']}%)", flush=True)
    print(f"Valid Complete Pairs: {final_summary['pairs_summary']['completed_valid_pairs']}/{pairs_count}", flush=True)
    if final_summary["estimated_elo_diff"] is not None:
        print(f"Estimated Elo diff: {final_summary['estimated_elo_diff']:+.1f} (95% CI: {final_summary['elo_95_ci']})", flush=True)
    print(f"Target Met: {final_summary['target_met']}", flush=True)
    print("=" * 65, flush=True)

    return final_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Janus v0.34.2 Supervised Match Runner")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--movetime-ms", type=int, default=500)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--match-name", type=str, default="clean_match_500ms")
    parser.add_argument("--openings", type=str, default="benchmarks/openings.json")
    parser.add_argument("--base-dir", type=str, default=".worktree_v030")
    parser.add_argument("--cand-dir", type=str, default=".")
    parser.add_argument("--output-dir", type=str, default="analysis/v0.34_2/clean_match")
    parser.add_argument("--smoke", action="store_true", help="Run 4-game smoke match qualification")
    args = parser.parse_args()

    games = 4 if args.smoke else args.games
    match_name = "smoke_match_500ms" if args.smoke else args.match_name
    output_dir = "analysis/v0.34_2/smoke_match" if args.smoke else args.output_dir

    summary = run_clean_match(
        games=games,
        movetime_ms=args.movetime_ms,
        max_plies=args.max_plies,
        seed=args.seed,
        match_name=match_name,
        openings_file=args.openings,
        base_dir_path=args.base_dir,
        cand_dir_path=args.cand_dir,
        output_dir_path=output_dir,
    )

    if not summary.get("target_met", False):
        print("\nERROR: Match failed to achieve planned valid games or complete pairs target.")
        sys.exit(1)


if __name__ == "__main__":
    main()
