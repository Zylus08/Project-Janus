"""Project Janus v0.38 - External Engine Benchmark Runner and Telemetry Collector.

Executes controlled, colour-balanced, paired matches between Project Janus
and external chess engines (specifically Stockfish 19).

Supports three benchmark experiments:
1. Primary Benchmark ('primary_fischer'):
   Janus Adaptive vs Stockfish 19 unconstrained under 3000ms + 100ms Fischer increment (100 games / 50 pairs).
2. Historical Comparison Benchmark ('historical_depth3'):
   Janus vs Stockfish 19 at fixed search depth 3 (50 games / 25 pairs), directly reproducing v0.5 baseline.
3. Calibrated Opponent Benchmark ('calibrated_elo'):
   Janus Adaptive vs Stockfish 19 calibrated to Elo 1320 (50 games / 25 pairs).
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

STOCKFISH_PATH = r"E:\ChessXML\tools\stockfish\stockfish.exe"

BENCHMARK_MODES = {
    "primary_fischer": {
        "id": "primary_fischer",
        "title": "Primary Benchmark: Janus Adaptive vs Stockfish 19 (Fischer 3000ms+100ms)",
        "janus_policy": "arm_c",
        "stockfish_options": {"Threads": 1, "Hash": 64},
        "time_mode": "fischer_increment",
        "base_time_ms": 3000,
        "inc_time_ms": 100,
        "fixed_depth": None,
        "default_games": 100,
        "default_dir": "analysis/v0.38/primary_fischer",
    },
    "historical_depth3": {
        "id": "historical_depth3",
        "title": "Historical Comparison Benchmark: Janus vs Stockfish 19 (Fixed Depth 3)",
        "janus_policy": "reference",
        "stockfish_options": {"Threads": 1, "Hash": 64},
        "time_mode": "fixed_depth",
        "base_time_ms": 3000,
        "inc_time_ms": 0,
        "fixed_depth": 3,
        "default_games": 50,
        "default_dir": "analysis/v0.38/historical_depth3",
    },
    "calibrated_elo": {
        "id": "calibrated_elo",
        "title": "Calibrated Opponent Benchmark: Janus Adaptive vs Stockfish 19 (Elo 1320)",
        "janus_policy": "arm_c",
        "stockfish_options": {"Threads": 1, "Hash": 64, "UCI_LimitStrength": True, "UCI_Elo": 1320},
        "time_mode": "fischer_increment",
        "base_time_ms": 3000,
        "inc_time_ms": 100,
        "fixed_depth": None,
        "default_games": 50,
        "default_dir": "analysis/v0.38/calibrated_elo",
    },
}


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


def play_supervised_external_game(
    janus_session: SupervisedEngineSession,
    sf_session: SupervisedEngineSession,
    janus_tm: TimeManager,
    mode_id: str,
    time_mode: str,
    base_time_ms: int,
    inc_time_ms: int,
    fixed_depth: Optional[int],
    game_number: int,
    pair_number: int,
    attempt_number: int,
    janus_color: chess.Color,
    max_plies: int,
    start_fen: str | None,
    opening_id: str,
    opening_name: str,
) -> tuple[Optional[chess.pgn.Game], dict[str, Any], list[dict[str, Any]]]:
    """Play a single game between Janus and Stockfish 19 with fine-grained move telemetry."""
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen else chess.Board()

    white_is_janus = (janus_color == chess.WHITE)
    white_session = janus_session if white_is_janus else sf_session
    black_session = sf_session if white_is_janus else janus_session

    game = chess.pgn.Game()
    game.headers["Event"] = f"Janus v0.38 External Benchmark - {mode_id}"
    game.headers["Site"] = "Local Subprocess Session"
    game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = janus_session.name if white_is_janus else sf_session.name
    game.headers["Black"] = sf_session.name if white_is_janus else janus_session.name
    if time_mode == "fixed_depth":
        game.headers["TimeControl"] = f"depth {fixed_depth}"
    elif time_mode == "fischer_increment":
        game.headers["TimeControl"] = f"{base_time_ms / 1000.0}+{inc_time_ms / 1000.0}"
    else:
        game.headers["TimeControl"] = f"{base_time_ms / 1000.0}"

    if start_fen and start_fen != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = start_fen

    node = game

    # Clocks in milliseconds
    wtime_ms = float(base_time_ms)
    btime_ms = float(base_time_ms)

    janus_depths: list[int] = []
    sf_depths: list[int] = []
    janus_times: list[float] = []
    sf_times: list[float] = []
    move_telemetry_rows: list[dict[str, Any]] = []

    result_string = "*"
    termination_reason = "unknown"
    infrastructure_error: Optional[dict[str, Any]] = None

    for ply in range(max_plies):
        if board.is_game_over():
            outcome = board.outcome(claim_draw=True)
            if outcome is not None:
                result_string = outcome.result()
                if outcome.winner == chess.WHITE:
                    termination_reason = "checkmate_white_wins"
                elif outcome.winner == chess.BLACK:
                    termination_reason = "checkmate_black_wins"
                else:
                    termination_reason = f"draw_{outcome.termination.name.lower()}"
            break

        is_janus_turn = (board.turn == janus_color)
        current_session = janus_session if is_janus_turn else sf_session
        curr_name = janus_session.name if is_janus_turn else sf_session.name
        active_color = "white" if board.turn == chess.WHITE else "black"

        clock_before = wtime_ms if board.turn == chess.WHITE else btime_ms

        # Compute pre-move target allocation for Janus
        if is_janus_turn and time_mode == "fischer_increment":
            target_alloc_s = janus_tm.allocate_time(
                board.turn,
                wtime=int(wtime_ms),
                btime=int(btime_ms),
                winc=inc_time_ms,
                binc=inc_time_ms,
            )
            target_alloc_ms = (target_alloc_s * 1000.0) if target_alloc_s is not None else 0.0
            is_emergency = (clock_before <= janus_tm.config.safety_reserve_ms)
        else:
            target_alloc_ms = 0.0
            is_emergency = False

        try:
            if time_mode == "fixed_depth":
                m_res = current_session.play_move(board, depth=fixed_depth)
            else:
                m_res = current_session.play_move(
                    board,
                    wtime=int(wtime_ms),
                    btime=int(btime_ms),
                    winc=inc_time_ms,
                    binc=inc_time_ms,
                )
        except Exception as exc:
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
        overshoot_ms = max(0.0, actual_time_ms - target_alloc_ms) if is_janus_turn else 0.0

        # Update clocks
        if time_mode == "fischer_increment":
            if board.turn == chess.WHITE:
                wtime_ms = max(0.0, wtime_ms - actual_time_ms) + inc_time_ms
                clock_after = wtime_ms
                if wtime_ms <= 0.0:
                    result_string = "0-1"
                    termination_reason = "white_flagged"
            else:
                btime_ms = max(0.0, btime_ms - actual_time_ms) + inc_time_ms
                clock_after = btime_ms
                if btime_ms <= 0.0:
                    result_string = "1-0"
                    termination_reason = "black_flagged"
        else:
            clock_after = 0.0

        if is_janus_turn:
            janus_depths.append(m_res.depth)
            janus_times.append(m_res.time_s)
        else:
            sf_depths.append(m_res.depth)
            sf_times.append(m_res.time_s)

        nps = int(m_res.nodes / max(0.001, m_res.time_s))

        m_row = {
            "mode": mode_id,
            "game": game_number,
            "pair": pair_number,
            "opening_id": opening_id,
            "ply": ply + 1,
            "player": curr_name,
            "is_janus": is_janus_turn,
            "color": active_color,
            "move": m_res.move.uci(),
            "clock_before_ms": round(clock_before, 1),
            "inc_ms": inc_time_ms,
            "target_alloc_ms": round(target_alloc_ms, 1),
            "actual_time_ms": round(actual_time_ms, 1),
            "overshoot_ms": round(overshoot_ms, 1),
            "clock_after_ms": round(clock_after, 1),
            "depth": m_res.depth,
            "nodes": m_res.nodes,
            "nps": nps,
            "is_emergency": is_emergency,
        }
        move_telemetry_rows.append(m_row)

        node = node.add_variation(m_res.move)
        board.push(m_res.move)

        if termination_reason in ("white_flagged", "black_flagged"):
            break

    # Adjudication if game reached max plies
    if result_string == "*" and infrastructure_error is None:
        if board.is_game_over():
            outcome = board.outcome(claim_draw=True)
            result_string = outcome.result() if outcome else "1/2-1/2"
            termination_reason = "game_over_at_limit"
        else:
            result_string = "1/2-1/2"
            termination_reason = "max_plies_adjudication_draw"

    game_duration = time.monotonic() - game_start
    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    # Score calculation from Janus perspective
    if result_string == "1-0":
        janus_points = 1.0 if white_is_janus else 0.0
        janus_won = white_is_janus
    elif result_string == "0-1":
        janus_points = 0.0 if white_is_janus else 1.0
        janus_won = not white_is_janus
    elif result_string == "1/2-1/2":
        janus_points = 0.5
        janus_won = False
    else:
        janus_points = 0.0
        janus_won = False

    attempt_rec = {
        "mode": mode_id,
        "game": game_number,
        "pair": pair_number,
        "attempt_number": attempt_number,
        "status": "completed" if infrastructure_error is None else "infrastructure_failure",
        "result": result_string if infrastructure_error is None else "NONE",
        "termination_reason": termination_reason if infrastructure_error is None else "engine_error",
        "plies": len(board.move_stack),
        "janus_color": "white" if white_is_janus else "black",
        "janus_won": janus_won,
        "janus_points": janus_points,
        "opening_id": opening_id,
        "opening_name": opening_name,
        "start_fen": start_fen or chess.STARTING_FEN,
        "final_fen": board.fen(),
        "duration_seconds": round(game_duration, 2),
        "mean_janus_depth": round(sum(janus_depths) / max(1, len(janus_depths)), 2),
        "mean_sf_depth": round(sum(sf_depths) / max(1, len(sf_depths)), 2),
        "mean_janus_time": round(sum(janus_times) / max(1, len(janus_times)), 3),
        "mean_sf_time": round(sum(sf_times) / max(1, len(sf_times)), 3),
        "infrastructure_error": infrastructure_error,
        "move_log": [m.uci() for m in board.move_stack],
    }

    if infrastructure_error is not None:
        return None, attempt_rec, []

    return game, attempt_rec, move_telemetry_rows


def run_external_benchmark(
    mode_key: str,
    output_dir_path: str | Path,
    games: Optional[int] = None,
    max_plies: int = 200,
    max_attempts_per_slot: int = 3,
    openings_file: str = "benchmarks/openings.json",
    seed: int = 42,
    stockfish_path: str = STOCKFISH_PATH,
) -> dict[str, Any]:
    """Execute paired benchmark match between Janus and Stockfish 19."""
    if mode_key not in BENCHMARK_MODES:
        raise ValueError(f"Unknown benchmark mode: {mode_key}. Choices: {list(BENCHMARK_MODES.keys())}")

    mode_cfg = BENCHMARK_MODES[mode_key]
    n_games = games or mode_cfg["default_games"]

    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "match_results.json"
    pgn_path = output_dir / "match_results.pgn"
    csv_path = output_dir / "match_results.csv"
    moves_csv_path = output_dir / "match_moves.csv"
    attempts_path = output_dir / "attempt_log.json"

    valid_games: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []

    pairs_count = max(1, math.ceil(n_games / 2.0))
    openings_path = ROOT / openings_file
    openings = load_openings(openings_path, count=pairs_count, seed=seed)

    janus_cmd = [
        sys.executable, "-m", "janus.uci",
        "--name", "Janus-v0.38-Adaptive",
        "--eval-all",
        "--time-policy", mode_cfg["janus_policy"],
    ]
    sf_cmd = [stockfish_path]

    janus_tm = TimeManager(
        config=TimeManagerConfig.arm_c_adaptive()
        if mode_cfg["janus_policy"] == "arm_c"
        else TimeManagerConfig.reference_baseline()
    )

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode_id": mode_key,
        "title": mode_cfg["title"],
        "janus_cmd": janus_cmd,
        "janus_policy": mode_cfg["janus_policy"],
        "stockfish_path": stockfish_path,
        "stockfish_options": mode_cfg["stockfish_options"],
        "time_mode": mode_cfg["time_mode"],
        "base_time_ms": mode_cfg["base_time_ms"],
        "inc_time_ms": mode_cfg["inc_time_ms"],
        "fixed_depth": mode_cfg["fixed_depth"],
        "max_plies": max_plies,
        "total_games_requested": n_games,
        "pairs_requested": pairs_count,
        "seed": seed,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    move_fields = [
        "mode", "game", "pair", "opening_id", "ply", "player", "is_janus", "color", "move",
        "clock_before_ms", "inc_ms", "target_alloc_ms", "actual_time_ms", "overshoot_ms",
        "clock_after_ms", "depth", "nodes", "nps", "is_emergency"
    ]

    print("\n" + "=" * 65)
    print(f"STARTING V0.38 EXTERNAL BENCHMARK: {mode_cfg['title']}")
    print(f"Janus Command: {' '.join(janus_cmd)}")
    print(f"Stockfish Options: {mode_cfg['stockfish_options']}")
    print(f"Time Control: {mode_cfg['time_mode']} ({mode_cfg['base_time_ms']}ms + {mode_cfg['inc_time_ms']}ms)")
    print(f"Target: {n_games} games ({pairs_count} colour-reversed pairs)")
    print(f"Output Directory: {output_dir}")
    print("=" * 65 + "\n")

    with open(pgn_path, "w", encoding="utf-8") as pgn_file, \
         open(moves_csv_path, "w", newline="", encoding="utf-8") as moves_f:

        moves_writer = csv.DictWriter(moves_f, fieldnames=move_fields)
        moves_writer.writeheader()

        for slot in range(n_games):
            pair_idx = slot // 2
            is_game_1 = (slot % 2 == 0)
            janus_color = chess.WHITE if is_game_1 else chess.BLACK
            color_label = "W" if janus_color == chess.WHITE else "B"

            opening_info = openings[pair_idx % len(openings)]
            op_id = opening_info.get("id", f"op_{pair_idx}")
            op_name = opening_info.get("name", "Opening")
            op_fen = opening_info.get("fen", chess.STARTING_FEN)

            slot_completed = False
            for attempt_num in range(1, max_attempts_per_slot + 1):
                try:
                    with SupervisedEngineSession(cmd=janus_cmd, name="Janus-v0.38", cwd=ROOT) as janus_sess, \
                         SupervisedEngineSession(cmd=sf_cmd, name="Stockfish-19", cwd=ROOT) as sf_sess:
                        sf_sess.configure(mode_cfg["stockfish_options"])
                        game_pgn, att_rec, move_rows = play_supervised_external_game(
                            janus_session=janus_sess,
                            sf_session=sf_sess,
                            janus_tm=janus_tm,
                            mode_id=mode_key,
                            time_mode=mode_cfg["time_mode"],
                            base_time_ms=mode_cfg["base_time_ms"],
                            inc_time_ms=mode_cfg["inc_time_ms"],
                            fixed_depth=mode_cfg["fixed_depth"],
                            game_number=slot + 1,
                            pair_number=pair_idx + 1,
                            attempt_number=attempt_num,
                            janus_color=janus_color,
                            max_plies=max_plies,
                            start_fen=op_fen,
                            opening_id=op_id,
                            opening_name=op_name,
                        )
                except Exception as exc:
                    att_rec = {
                        "mode": mode_key,
                        "game": slot + 1,
                        "pair": pair_idx + 1,
                        "attempt_number": attempt_num,
                        "status": "infrastructure_failure",
                        "failure_category": type(exc).__name__,
                        "message": str(exc),
                    }
                    game_pgn = None
                    move_rows = []

                attempts.append(att_rec)

                if game_pgn is not None and att_rec.get("status") == "completed":
                    valid_games.append(att_rec)
                    pgn_file.write(str(game_pgn) + "\n\n")
                    pgn_file.flush()

                    for r in move_rows:
                        moves_writer.writerow(r)
                    moves_f.flush()

                    pts = att_rec['janus_points']
                    res = att_rec['result']
                    pl = att_rec['plies']
                    dur = att_rec['duration_seconds']
                    jd = att_rec['mean_janus_depth']
                    sfd = att_rec['mean_sf_depth']
                    print(
                        f"[{mode_key}] Game {slot+1:3d}/{n_games} [Pair {pair_idx+1:2d} | {color_label}] (Att {attempt_num}): "
                        f"Result: {res:<7} ({pts:3.1f}) | Plies: {pl:3d} | {dur:5.1f}s | "
                        f"JanusDepth: {jd:4.1f} | SFDepth: {sfd:4.1f}",
                        flush=True,
                    )
                    slot_completed = True
                    break
                else:
                    err_msg = att_rec.get("infrastructure_error", {}).get("message") or att_rec.get("message", "Unknown error")
                    print(f"[{mode_key}] Game {slot+1} Attempt {attempt_num} FAILED: {err_msg}. Retrying...", flush=True)
                    time.sleep(0.1)

            if not slot_completed:
                print(f"[{mode_key}] Game slot {slot+1} could not be completed. Aborting.")
                break

    # Summary CSV
    csv_fields = [
        "mode", "game", "pair", "attempt_number", "status", "result", "termination_reason",
        "plies", "janus_color", "janus_won", "janus_points", "opening_id", "opening_name",
        "duration_seconds", "mean_janus_depth", "mean_sf_depth", "mean_janus_time", "mean_sf_time"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for g in valid_games:
            writer.writerow({k: g.get(k, "") for k in csv_fields})

    n_valid = len(valid_games)
    janus_wins = sum(1 for g in valid_games if g["result"] == ("1-0" if g["janus_color"] == "white" else "0-1"))
    sf_wins = sum(1 for g in valid_games if g["result"] == ("0-1" if g["janus_color"] == "white" else "1-0"))
    draws = sum(1 for g in valid_games if g["result"] == "1/2-1/2")
    janus_points = sum(g["janus_points"] for g in valid_games)
    score_pct = (janus_points / n_valid * 100.0) if n_valid > 0 else 0.0

    complete_pairs = n_valid // 2
    infr_failures = sum(1 for a in attempts if a["status"] != "completed")

    match_summary = {
        "valid_games": n_valid,
        "complete_pairs": complete_pairs,
        "total_attempts": len(attempts),
        "infrastructure_failures": infr_failures,
        "janus_wins": janus_wins,
        "draws": draws,
        "stockfish_wins": sf_wins,
        "janus_points": janus_points,
        "janus_score_pct": round(score_pct, 2),
    }

    full_output = {
        "metadata": metadata,
        "match_summary": match_summary,
        "valid_games": valid_games,
        "attempts": attempts,
    }
    json_path.write_text(json.dumps(full_output, indent=2), encoding="utf-8")
    attempts_path.write_text(json.dumps(attempts, indent=2), encoding="utf-8")

    print("\n" + "=" * 65)
    print(f"BENCHMARK FINISHED: {n_valid}/{n_games} valid games, {len(attempts)} attempts")
    print(f"Infrastructure Failures: {infr_failures}")
    print(f"Janus: {janus_wins}W / {draws}D / {sf_wins}L ({score_pct:.1f}%)")
    print(f"Valid Complete Pairs: {complete_pairs}/{pairs_count}")
    print("=" * 65 + "\n")

    return full_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Project Janus v0.38 External Engine Benchmark.")
    parser.add_argument("--mode", type=str, default="primary_fischer", choices=["primary_fischer", "historical_depth3", "calibrated_elo", "all"],
                        help="Benchmark mode to run")
    parser.add_argument("--games", type=int, default=None, help="Number of games to run (overrides mode default)")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Opening RNG seed")
    parser.add_argument("--parallel", action="store_true", help="Run modes concurrently if mode=all")
    args = parser.parse_args()

    modes_to_run = ["primary_fischer", "historical_depth3", "calibrated_elo"] if args.mode == "all" else [args.mode]

    if args.parallel and len(modes_to_run) > 1:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(modes_to_run)) as executor:
            futures = [
                executor.submit(
                    run_external_benchmark,
                    mode_key=m,
                    output_dir_path=args.out_dir or BENCHMARK_MODES[m]["default_dir"],
                    games=args.games,
                    seed=args.seed,
                )
                for m in modes_to_run
            ]
            for f in concurrent.futures.as_completed(futures):
                f.result()
    else:
        for m in modes_to_run:
            target_dir = args.out_dir or BENCHMARK_MODES[m]["default_dir"]
            run_external_benchmark(
                mode_key=m,
                output_dir_path=target_dir,
                games=args.games,
                seed=args.seed,
            )
