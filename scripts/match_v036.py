"""Project Janus v0.36 - Extended Fischer Match Harness and Diagnostics Collector.

Executes controlled, colour-balanced, paired matches between:
- Candidate: Janus v0.36 (Adaptive policy: inc_weight=0.85, reserve=50ms, mtg=30)
- Reference: Janus v0.36 (Reference policy: inc_weight=0.00, reserve=0ms, mtg=40)
under 3000 ms + 100 ms Fischer increment time control.

Collects comprehensive move-level diagnostics including target allocations,
actual durations, deadline overshoots, remaining clocks, depth, nodes, and NPS.
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
from typing import Any, Optional

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
from janus.time_manager import TimeManager, TimeManagerConfig  # noqa: E402


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


def play_supervised_game_v036(
    base_session: SupervisedEngineSession,
    cand_session: SupervisedEngineSession,
    cand_tm: TimeManager,
    base_tm: TimeManager,
    game_number: int,
    pair_number: int,
    attempt_number: int,
    cand_color: chess.Color,
    time_mode: str,
    base_time_ms: int,
    inc_time_ms: int,
    max_plies: int,
    start_fen: str | None,
    opening_id: str,
    opening_name: str,
) -> tuple[Optional[chess.pgn.Game], dict[str, Any], list[dict[str, Any]]]:
    """Play a single game between two SupervisedEngineSessions with fine-grained move telemetry.

    Returns:
        (game_pgn, attempt_record, move_records)
    """
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen else chess.Board()

    white_is_cand = (cand_color == chess.WHITE)
    white_session = cand_session if white_is_cand else base_session
    black_session = base_session if white_is_cand else cand_session

    game = chess.pgn.Game()
    game.headers["Event"] = f"Janus v0.36 Match - {time_mode}"
    game.headers["Site"] = "Local Subprocess Session"
    game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = cand_session.name if white_is_cand else base_session.name
    game.headers["Black"] = base_session.name if white_is_cand else cand_session.name
    game.headers["TimeControl"] = (
        f"{base_time_ms / 1000.0}+{inc_time_ms / 1000.0}"
        if time_mode == "fischer_increment"
        else f"{base_time_ms / 1000.0}"
    )
    if start_fen and start_fen != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = start_fen

    node = game

    result_string = None
    termination_reason = None
    infrastructure_error: Optional[dict[str, Any]] = None

    move_log: list[dict[str, Any]] = []
    move_telemetry_rows: list[dict[str, Any]] = []
    cand_depths = []
    base_depths = []
    cand_times = []
    base_times = []

    # Initialize clocks
    wtime_ms = float(base_time_ms)
    btime_ms = float(base_time_ms)

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
            "opening_name": opening_name,
            "start_fen": start_fen or chess.STARTING_FEN,
            "candidate_color": "white" if cand_color == chess.WHITE else "black",
            "duration_seconds": round(time.monotonic() - game_start, 3),
        }, []

    for ply in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break

        is_cand_turn = (board.turn == cand_color)
        current_session = cand_session if is_cand_turn else base_session
        current_tm = cand_tm if is_cand_turn else base_tm
        curr_name = "Adaptive" if is_cand_turn else "Reference"
        policy_label = "adaptive" if is_cand_turn else "reference"
        active_color = "white" if board.turn == chess.WHITE else "black"

        clock_before = wtime_ms if board.turn == chess.WHITE else btime_ms

        # Compute pre-move target allocation from the engine's active TimeManager policy
        target_alloc_s = current_tm.allocate_time(
            board.turn,
            wtime=int(wtime_ms),
            btime=int(btime_ms),
            winc=inc_time_ms if time_mode == "fischer_increment" else 0,
            binc=inc_time_ms if time_mode == "fischer_increment" else 0,
        )
        target_alloc_ms = (target_alloc_s * 1000.0) if target_alloc_s is not None else 0.0
        is_emergency = (clock_before <= current_tm.config.safety_reserve_ms)

        try:
            if time_mode == "fixed_movetime":
                m_res: MoveResult = current_session.play_move(board, movetime_ms=base_time_ms)
            else:
                m_res: MoveResult = current_session.play_move(
                    board,
                    wtime=int(wtime_ms),
                    btime=int(btime_ms),
                    winc=inc_time_ms if time_mode == "fischer_increment" else 0,
                    binc=inc_time_ms if time_mode == "fischer_increment" else 0,
                )
        except EngineError as exc:
            infrastructure_error = {
                "category": type(exc).__name__,
                "engine": curr_name,
                "message": str(exc),
                "ply": ply + 1,
                "exit_code": current_session.process.poll() if current_session.process else -1,
                "stderr_snippet": current_session.get_stderr_snippet(),
            }
            break

        actual_time_ms = m_res.time_s * 1000.0
        overshoot_ms = max(0.0, actual_time_ms - target_alloc_ms)
        is_deadline_stop = (actual_time_ms >= (target_alloc_ms - 2.0)) and (m_res.depth < 64)
        fallback_used = (m_res.depth == 0)

        # Update clocks
        if board.turn == chess.WHITE:
            wtime_ms = max(0.0, wtime_ms - actual_time_ms)
            if time_mode == "fischer_increment":
                wtime_ms += inc_time_ms
            clock_after = wtime_ms
            if wtime_ms <= 0.0 and time_mode != "fixed_movetime":
                result_string = "0-1"
                termination_reason = "white_flagged"
        else:
            btime_ms = max(0.0, btime_ms - actual_time_ms)
            if time_mode == "fischer_increment":
                btime_ms += inc_time_ms
            clock_after = btime_ms
            if btime_ms <= 0.0 and time_mode != "fixed_movetime":
                result_string = "1-0"
                termination_reason = "black_flagged"

        if is_cand_turn:
            cand_depths.append(m_res.depth)
            cand_times.append(m_res.time_s)
        else:
            base_depths.append(m_res.depth)
            base_times.append(m_res.time_s)

        nps = int(m_res.nodes / max(0.001, m_res.time_s))

        # Move telemetry row
        m_row = {
            "game": game_number,
            "pair": pair_number,
            "opening_id": opening_id,
            "ply": ply + 1,
            "player": curr_name,
            "policy": policy_label,
            "color": active_color,
            "move": m_res.move.uci(),
            "clock_before_ms": round(clock_before, 1),
            "inc_ms": inc_time_ms if time_mode == "fischer_increment" else 0,
            "target_alloc_ms": round(target_alloc_ms, 1),
            "actual_time_ms": round(actual_time_ms, 1),
            "overshoot_ms": round(overshoot_ms, 1),
            "clock_after_ms": round(clock_after, 1),
            "depth": m_res.depth,
            "nodes": m_res.nodes,
            "nps": nps,
            "is_emergency": is_emergency,
            "is_deadline_stop": is_deadline_stop,
            "fallback_move_required": fallback_used,
            "error_or_timeout": False,
        }
        move_telemetry_rows.append(m_row)

        move_log.append({
            "ply": ply + 1,
            "player": curr_name,
            "policy": policy_label,
            "color": active_color,
            "move": m_res.move.uci(),
            "time_s": round(m_res.time_s, 3),
            "wtime_left_ms": round(wtime_ms, 1),
            "btime_left_ms": round(btime_ms, 1),
            "depth": m_res.depth,
            "nodes": m_res.nodes,
            "nps": nps,
        })

        node = node.add_variation(m_res.move)
        board.push(m_res.move)

        if result_string is not None:
            break

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
            "opening_name": opening_name,
            "start_fen": start_fen or chess.STARTING_FEN,
            "candidate_color": "white" if cand_color == chess.WHITE else "black",
            "duration_seconds": duration,
        }, move_telemetry_rows

    # Evaluate chess termination if not already flagged
    if result_string is None:
        if board.is_checkmate():
            result_string = "0-1" if board.turn == chess.WHITE else "1-0"
            termination_reason = "checkmate"
        elif board.is_stalemate():
            result_string = "1/2-1/2"
            termination_reason = "stalemate"
        elif board.is_insufficient_material():
            result_string = "1/2-1/2"
            termination_reason = "insufficient_material"
        elif board.can_claim_threefold_repetition():
            result_string = "1/2-1/2"
            termination_reason = "threefold_repetition"
        elif board.can_claim_fifty_moves():
            result_string = "1/2-1/2"
            termination_reason = "fifty_moves"
        elif len(move_log) >= max_plies:
            result_string = "1/2-1/2"
            termination_reason = "max_plies_reached"
        else:
            result_string = "1/2-1/2"
            termination_reason = "adjudicated_draw"

    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    cand_won = (
        (result_string == "1-0" and cand_color == chess.WHITE)
        or (result_string == "0-1" and cand_color == chess.BLACK)
    )
    cand_pts = 1.0 if cand_won else (0.5 if result_string == "1/2-1/2" else 0.0)

    attempt_record = {
        "game": game_number,
        "pair": pair_number,
        "attempt_number": attempt_number,
        "status": "completed",
        "result": result_string,
        "termination_reason": termination_reason,
        "plies": len(move_log),
        "candidate_color": "white" if cand_color == chess.WHITE else "black",
        "candidate_won": cand_won,
        "candidate_points": cand_pts,
        "opening_id": opening_id,
        "opening_name": opening_name,
        "start_fen": start_fen or chess.STARTING_FEN,
        "final_fen": board.fen(),
        "duration_seconds": duration,
        "mean_cand_depth": round(sum(cand_depths) / len(cand_depths), 1) if cand_depths else 0.0,
        "mean_base_depth": round(sum(base_depths) / len(base_depths), 1) if base_depths else 0.0,
        "mean_cand_time": round(sum(cand_times) / len(cand_times), 3) if cand_times else 0.0,
        "mean_base_time": round(sum(base_times) / len(base_times), 3) if base_times else 0.0,
        "move_log": move_log,
    }

    return game, attempt_record, move_telemetry_rows


def summarize_match_v036(
    valid_games: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    planned_games: int,
    planned_pairs: int,
) -> dict[str, Any]:
    """Calculate summary statistics from valid games."""
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
            else:
                cand_losses += 1
                by_color["black"]["losses"] += 1
        elif res == "0-1":
            if color == "black":
                cand_wins += 1
                by_color["black"]["wins"] += 1
            else:
                cand_losses += 1
                by_color["white"]["losses"] += 1
        elif res == "1/2-1/2":
            cand_draws += 1
            if color == "white":
                by_color["white"]["draws"] += 1
            else:
                by_color["black"]["draws"] += 1

        if color in by_color:
            by_color[color]["games"] += 1
            by_color[color]["score_pts"] = (
                by_color[color]["wins"] + 0.5 * by_color[color]["draws"]
            )

    total_valid = len(valid_games)
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_valid * 100.0) if total_valid > 0 else 0.0

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

    decisive_pairs = pair_outcomes["won"] + pair_outcomes["lost"]
    sign_test_p = None
    if decisive_pairs > 0:
        k = min(pair_outcomes["won"], pair_outcomes["lost"])
        sign_test_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        sign_test_p = min(1.0, sign_test_p)

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


def run_clean_match_v036(
    games: int = 100,
    time_mode: str = "fischer_increment",
    base_time_ms: int = 3000,
    inc_time_ms: int = 100,
    max_plies: int = 100,
    seed: int = 42,
    openings_file: str = "benchmarks/openings.json",
    output_dir_path: Path = ROOT / "analysis" / "v0.36" / "match",
    match_name: str = "fischer_100_match",
    max_attempts_per_slot: int = 3,
    custom_base_cmd: Optional[list[str]] = None,
    custom_cand_cmd: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Execute paired match using supervised per-game process lifecycles and record telemetry."""
    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{match_name}.json"
    pgn_path = output_dir / f"{match_name}.pgn"
    csv_path = output_dir / f"{match_name}.csv"
    moves_csv_path = output_dir / f"{match_name}_moves.csv"
    attempts_path = output_dir / f"{match_name}_attempts.json"

    valid_games: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    all_move_records: list[dict[str, Any]] = []

    pairs_count = max(1, math.ceil(games / 2.0))
    openings_path = ROOT / openings_file
    openings = load_openings(openings_path, count=pairs_count, seed=seed)

    base_cmd = custom_base_cmd or [
        sys.executable, "-m", "janus.uci", "--name", "Janus-v0.36-Reference", "--eval-all", "--time-policy", "reference"
    ]
    cand_cmd = custom_cand_cmd or [
        sys.executable, "-m", "janus.uci", "--name", "Janus-v0.36-Adaptive", "--eval-all", "--time-policy", "adaptive"
    ]

    cand_tm = TimeManager(config=TimeManagerConfig())
    base_tm = TimeManager(config=TimeManagerConfig.reference_baseline())

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_name": "Janus-v0.36-Adaptive",
        "candidate_config": "CONFIG_V034_TAPERED + Adaptive TimeManager (weight=0.85, reserve=50ms, mtg=30)",
        "candidate_cmd": cand_cmd,
        "reference_name": "Janus-v0.36-Reference",
        "reference_config": "CONFIG_V034_TAPERED + Reference TimeManager (weight=0.00, reserve=0ms, mtg=40)",
        "reference_cmd": base_cmd,
        "time_mode": time_mode,
        "base_time_ms": base_time_ms,
        "inc_time_ms": inc_time_ms,
        "max_plies": max_plies,
        "total_games_requested": games,
        "pairs_requested": pairs_count,
        "seed": seed,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    # Open PGN and moves CSV streams
    move_fields = [
        "game", "pair", "opening_id", "ply", "player", "policy", "color", "move",
        "clock_before_ms", "inc_ms", "target_alloc_ms", "actual_time_ms", "overshoot_ms",
        "clock_after_ms", "depth", "nodes", "nps", "is_emergency", "is_deadline_stop",
        "fallback_move_required", "error_or_timeout"
    ]

    with open(pgn_path, "w", encoding="utf-8") as pgn_file, \
         open(moves_csv_path, "w", newline="", encoding="utf-8") as moves_f:

        moves_writer = csv.DictWriter(moves_f, fieldnames=move_fields)
        moves_writer.writeheader()

        for slot in range(games):
            pair_idx = slot // 2
            is_game_1 = (slot % 2 == 0)
            cand_color = chess.WHITE if is_game_1 else chess.BLACK
            color_label = "W" if cand_color == chess.WHITE else "B"

            opening_info = openings[pair_idx % len(openings)]
            op_id = opening_info.get("id", f"op_{pair_idx}")
            op_name = opening_info.get("name", "Opening")
            op_fen = opening_info.get("fen", chess.STARTING_FEN)

            slot_completed = False
            for attempt_num in range(1, max_attempts_per_slot + 1):
                try:
                    with SupervisedEngineSession(cmd=base_cmd, name="Reference", cwd=ROOT) as base_sess, \
                         SupervisedEngineSession(cmd=cand_cmd, name="Candidate", cwd=ROOT) as cand_sess:
                        game_pgn, att_rec, move_rows = play_supervised_game_v036(
                            base_session=base_sess,
                            cand_session=cand_sess,
                            cand_tm=cand_tm,
                            base_tm=base_tm,
                            game_number=slot + 1,
                            pair_number=pair_idx + 1,
                            attempt_number=attempt_num,
                            cand_color=cand_color,
                            time_mode=time_mode,
                            base_time_ms=base_time_ms,
                            inc_time_ms=inc_time_ms,
                            max_plies=max_plies,
                            start_fen=op_fen,
                            opening_id=op_id,
                            opening_name=op_name,
                        )
                except Exception as exc:
                    att_rec = {
                        "game": slot + 1,
                        "pair": pair_idx + 1,
                        "attempt_number": attempt_num,
                        "status": "infrastructure_failure",
                        "failure_category": type(exc).__name__,
                        "error_message": str(exc),
                        "opening_id": op_id,
                        "opening_name": op_name,
                        "start_fen": op_fen,
                        "candidate_color": "white" if cand_color == chess.WHITE else "black",
                        "duration_seconds": 0.0,
                    }
                    game_pgn = None
                    move_rows = []

                attempts.append(att_rec)

                if att_rec.get("status") == "completed" and game_pgn is not None:
                    valid_games.append(att_rec)
                    all_move_records.extend(move_rows)
                    pgn_file.write(str(game_pgn) + "\n\n")
                    pgn_file.flush()

                    for m_row in move_rows:
                        moves_writer.writerow(m_row)
                    moves_f.flush()

                    print(
                        f"Game {slot + 1:3d}/{games} [Pair {pair_idx + 1:2d} | {color_label}] "
                        f"(Attempt {attempt_num}): Result: {att_rec['result']} ({att_rec['candidate_points']}) | "
                        f"Plies: {att_rec['plies']:3d} | {att_rec['duration_seconds']:5.1f}s | "
                        f"CandDepth: {att_rec['mean_cand_depth']:.1f} | BaseDepth: {att_rec['mean_base_depth']:.1f}"
                    )
                    slot_completed = True
                    break
                else:
                    print(
                        f"Game {slot + 1:3d} Attempt {attempt_num} FAILED: "
                        f"{att_rec.get('failure_category')}: {att_rec.get('error_message')}"
                    )

            if not slot_completed:
                print(f"Game slot {slot + 1} could not be completed after {max_attempts_per_slot} attempts. Aborting match loop.")
                break

    match_summary = summarize_match_v036(
        valid_games=valid_games,
        attempts=attempts,
        planned_games=games,
        planned_pairs=pairs_count,
    )

    full_dataset = {
        "metadata": metadata,
        "match_summary": match_summary,
        "valid_games": valid_games,
        "attempts": attempts,
    }

    json_path.write_text(json.dumps(full_dataset, indent=2), encoding="utf-8")
    attempts_path.write_text(json.dumps(attempts, indent=2), encoding="utf-8")

    # Write per-game summary CSV
    if valid_games:
        game_fields = [
            "game", "pair", "attempt_number", "result", "candidate_color", "candidate_points",
            "plies", "duration_seconds", "mean_cand_depth", "mean_base_depth",
            "opening_id", "opening_name", "start_fen", "final_fen"
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=game_fields, extrasaction="ignore")
            writer.writeheader()
            for g in valid_games:
                writer.writerow(g)

    print("\n" + "=" * 65)
    print(
        f"MATCH FINISHED: {len(valid_games)}/{games} valid games, {len(attempts)} attempts\n"
        f"Candidate: {match_summary['candidate_wins']}W / {match_summary['candidate_draws']}D / {match_summary['candidate_losses']}L "
        f"({match_summary['candidate_score_pct']}%)\n"
        f"Valid Complete Pairs: {match_summary['complete_valid_pairs']}/{pairs_count}\n"
        f"Estimated Elo diff: {match_summary['estimated_elo_diff']} (95% CI: {match_summary['elo_95_ci']})\n"
        f"Target Met: {match_summary['target_met']}"
    )
    print("=" * 65)

    return full_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Janus v0.36 Match Harness")
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    parser.add_argument("--time-mode", type=str, default="fischer_increment",
                        choices=["fixed_movetime", "clock_only", "fischer_increment"])
    parser.add_argument("--base-time-ms", type=int, default=3000, help="Base time in ms")
    parser.add_argument("--inc-time-ms", type=int, default=100, help="Increment per move in ms")
    parser.add_argument("--max-plies", type=int, default=100, help="Max plies before draw")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--output-dir", type=str, default="analysis/v0.36/match")
    parser.add_argument("--match-name", type=str, default="fischer_100_match")
    args = parser.parse_args()

    run_clean_match_v036(
        games=args.games,
        time_mode=args.time_mode,
        base_time_ms=args.base_time_ms,
        inc_time_ms=args.inc_time_ms,
        max_plies=args.max_plies,
        seed=args.seed,
        output_dir_path=Path(args.output_dir),
        match_name=args.match_name,
    )


if __name__ == "__main__":
    main()
