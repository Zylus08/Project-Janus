"""Project Janus v0.37 - Time-Management Ablation Match Harness and Telemetry Collector.

Executes controlled, colour-balanced, paired matches among three experimental arms:
- Arm A (Original Reference): inc_weight=0.00, reserve=0ms, mtg=40, max_ratio=0.20
- Arm B (Matched Reference):  inc_weight=0.00, reserve=50ms, mtg=30, max_ratio=0.20
- Arm C (Adaptive Candidate):  inc_weight=0.85, reserve=50ms, mtg=30, max_ratio=0.20

Supports three planned comparisons under 3000 ms + 100 ms Fischer increment:
1. Primary:   B versus C (isolates increment weight: 0.00 vs 0.85)
2. Secondary: A versus B (evaluates reserve + mtg change at 0.00 inc weight)
3. Context:   A versus C (reproduces v0.36 combined policy comparison)
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
from dataclasses import asdict
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


ARM_CONFIGS = {
    "arm_a": {
        "name": "Janus-v0.37-ArmA",
        "label": "Arm A (Original Reference)",
        "cmd_policy": "arm_a",
        "config": TimeManagerConfig.arm_a_original_reference(),
        "description": "Original Reference: reserve=0ms, mtg=40, inc_weight=0.00, max_ratio=0.20",
    },
    "arm_b": {
        "name": "Janus-v0.37-ArmB",
        "label": "Arm B (Matched Reference)",
        "cmd_policy": "arm_b",
        "config": TimeManagerConfig.arm_b_matched_reference(),
        "description": "Matched Reference: reserve=50ms, mtg=30, inc_weight=0.00, max_ratio=0.20",
    },
    "arm_c": {
        "name": "Janus-v0.37-ArmC",
        "label": "Arm C (Adaptive Candidate)",
        "cmd_policy": "arm_c",
        "config": TimeManagerConfig.arm_c_adaptive(),
        "description": "Adaptive Candidate: reserve=50ms, mtg=30, inc_weight=0.85, max_ratio=0.20",
    },
}

COMPARISONS = {
    "b_vs_c": {
        "id": "b_vs_c",
        "title": "Primary: Arm B vs Arm C (Increment Weight Isolation)",
        "cand_arm": "arm_c",
        "base_arm": "arm_b",
        "default_dir": "analysis/v0.37/match_b_vs_c",
    },
    "a_vs_b": {
        "id": "a_vs_b",
        "title": "Secondary: Arm A vs Arm B (Reserve & Horizon Combined)",
        "cand_arm": "arm_b",
        "base_arm": "arm_a",
        "default_dir": "analysis/v0.37/match_a_vs_b",
    },
    "a_vs_c": {
        "id": "a_vs_c",
        "title": "Contextual: Arm A vs Arm C (Combined Policy Reproduction)",
        "cand_arm": "arm_c",
        "base_arm": "arm_a",
        "default_dir": "analysis/v0.37/match_a_vs_c",
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


def play_supervised_game_v037(
    base_session: SupervisedEngineSession,
    cand_session: SupervisedEngineSession,
    cand_tm: TimeManager,
    base_tm: TimeManager,
    cand_arm_id: str,
    base_arm_id: str,
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
    comparison_id: str,
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
    game.headers["Event"] = f"Janus v0.37 Ablation - {comparison_id}"
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

    # Clocks in milliseconds
    wtime_ms = float(base_time_ms)
    btime_ms = float(base_time_ms)

    cand_depths: list[int] = []
    base_depths: list[int] = []
    cand_times: list[float] = []
    base_times: list[float] = []
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

        is_cand_turn = (board.turn == cand_color)
        current_session = cand_session if is_cand_turn else base_session
        current_tm = cand_tm if is_cand_turn else base_tm
        curr_arm = cand_arm_id if is_cand_turn else base_arm_id
        curr_name = ARM_CONFIGS[curr_arm]["name"]
        policy_label = current_tm.config.policy_name
        active_color = "white" if board.turn == chess.WHITE else "black"

        clock_before = wtime_ms if board.turn == chess.WHITE else btime_ms

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

        m_row = {
            "comparison": comparison_id,
            "game": game_number,
            "pair": pair_number,
            "opening_id": opening_id,
            "ply": ply + 1,
            "player": curr_name,
            "arm": curr_arm,
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

    # Score calculation from candidate perspective
    if result_string == "1-0":
        cand_points = 1.0 if white_is_cand else 0.0
        cand_won = white_is_cand
    elif result_string == "0-1":
        cand_points = 0.0 if white_is_cand else 1.0
        cand_won = not white_is_cand
    elif result_string == "1/2-1/2":
        cand_points = 0.5
        cand_won = False
    else:
        cand_points = 0.0
        cand_won = False

    attempt_rec = {
        "comparison": comparison_id,
        "game": game_number,
        "pair": pair_number,
        "attempt_number": attempt_number,
        "status": "completed" if infrastructure_error is None else "infrastructure_failure",
        "result": result_string if infrastructure_error is None else "NONE",
        "termination_reason": termination_reason if infrastructure_error is None else "engine_error",
        "plies": len(board.move_stack),
        "candidate_arm": cand_arm_id,
        "base_arm": base_arm_id,
        "candidate_color": "white" if white_is_cand else "black",
        "candidate_won": cand_won,
        "candidate_points": cand_points,
        "opening_id": opening_id,
        "opening_name": opening_name,
        "start_fen": start_fen or chess.STARTING_FEN,
        "final_fen": board.fen(),
        "duration_seconds": round(game_duration, 2),
        "mean_cand_depth": round(sum(cand_depths) / max(1, len(cand_depths)), 2),
        "mean_base_depth": round(sum(base_depths) / max(1, len(base_depths)), 2),
        "mean_cand_time": round(sum(cand_times) / max(1, len(cand_times)), 3),
        "mean_base_time": round(sum(base_times) / max(1, len(base_times)), 3),
        "infrastructure_error": infrastructure_error,
        "move_log": [m.uci() for m in board.move_stack],
    }

    if infrastructure_error is not None:
        return None, attempt_rec, []

    return game, attempt_rec, move_telemetry_rows


def run_paired_match_v037(
    comparison_key: str,
    output_dir_path: str | Path,
    games: int = 100,
    time_mode: str = "fischer_increment",
    base_time_ms: int = 3000,
    inc_time_ms: int = 100,
    max_plies: int = 200,
    max_attempts_per_slot: int = 3,
    openings_file: str = "benchmarks/openings.json",
    seed: int = 42,
    custom_cand_cmd: Optional[list[str]] = None,
    custom_base_cmd: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Execute paired match between specified arms using supervised process lifecycles."""
    if comparison_key not in COMPARISONS:
        raise ValueError(f"Unknown comparison: {comparison_key}. Choices: {list(COMPARISONS.keys())}")

    comp_info = COMPARISONS[comparison_key]
    cand_arm_id = comp_info["cand_arm"]
    base_arm_id = comp_info["base_arm"]

    cand_arm = ARM_CONFIGS[cand_arm_id]
    base_arm = ARM_CONFIGS[base_arm_id]

    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "match.json"
    pgn_path = output_dir / "match.pgn"
    csv_path = output_dir / "match.csv"
    moves_csv_path = output_dir / "match_moves.csv"
    attempts_path = output_dir / "match_attempts.json"

    valid_games: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []

    pairs_count = max(1, math.ceil(games / 2.0))
    openings_path = ROOT / openings_file
    openings = load_openings(openings_path, count=pairs_count, seed=seed)

    base_cmd = custom_base_cmd or [
        sys.executable, "-m", "janus.uci", "--name", base_arm["name"], "--eval-all", "--time-policy", base_arm["cmd_policy"]
    ]
    cand_cmd = custom_cand_cmd or [
        sys.executable, "-m", "janus.uci", "--name", cand_arm["name"], "--eval-all", "--time-policy", cand_arm["cmd_policy"]
    ]

    cand_tm = TimeManager(config=cand_arm["config"])
    base_tm = TimeManager(config=base_arm["config"])

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "comparison_id": comparison_key,
        "comparison_title": comp_info["title"],
        "candidate_arm": cand_arm_id,
        "candidate_name": cand_arm["name"],
        "candidate_config": asdict(cand_arm["config"]),
        "candidate_cmd": cand_cmd,
        "base_arm": base_arm_id,
        "base_name": base_arm["name"],
        "base_config": asdict(base_arm["config"]),
        "base_cmd": base_cmd,
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

    move_fields = [
        "comparison", "game", "pair", "opening_id", "ply", "player", "arm", "policy", "color", "move",
        "clock_before_ms", "inc_ms", "target_alloc_ms", "actual_time_ms", "overshoot_ms",
        "clock_after_ms", "depth", "nodes", "nps", "is_emergency", "is_deadline_stop",
        "fallback_move_required", "error_or_timeout"
    ]

    print(f"\n=================================================================")
    print(f"STARTING V0.37 ABLATION MATCH: {comp_info['title']}")
    print(f"Candidate: {cand_arm['name']} ({cand_arm['description']})")
    print(f"Reference: {base_arm['name']} ({base_arm['description']})")
    print(f"Time Control: {base_time_ms} ms + {inc_time_ms} ms Fischer increment")
    print(f"Target: {games} games ({pairs_count} colour-reversed pairs)")
    print(f"Output Directory: {output_dir}")
    print(f"=================================================================\n")

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
                    with SupervisedEngineSession(cmd=base_cmd, name=base_arm["name"], cwd=ROOT) as base_sess, \
                         SupervisedEngineSession(cmd=cand_cmd, name=cand_arm["name"], cwd=ROOT) as cand_sess:
                        game_pgn, att_rec, move_rows = play_supervised_game_v037(
                            base_session=base_sess,
                            cand_session=cand_sess,
                            cand_tm=cand_tm,
                            base_tm=base_tm,
                            cand_arm_id=cand_arm_id,
                            base_arm_id=base_arm_id,
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
                            comparison_id=comparison_key,
                        )
                except Exception as exc:
                    att_rec = {
                        "comparison": comparison_key,
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

                    pts = att_rec['candidate_points']
                    res = att_rec['result']
                    pl = att_rec['plies']
                    dur = att_rec['duration_seconds']
                    cd = att_rec['mean_cand_depth']
                    bd = att_rec['mean_base_depth']
                    print(
                        f"[{comparison_key}] Game {slot+1:3d}/{games} [Pair {pair_idx+1:2d} | {color_label}] (Att {attempt_num}): "
                        f"Result: {res:<7} ({pts:3.1f}) | Plies: {pl:3d} | {dur:5.1f}s | "
                        f"CandDepth: {cd:4.1f} | BaseDepth: {bd:4.1f}"
                    )
                    slot_completed = True
                    break
                else:
                    err_msg = att_rec.get("infrastructure_error", {}).get("message") or att_rec.get("message", "Unknown error")
                    print(f"[{comparison_key}] Game {slot+1} Attempt {attempt_num} FAILED: {err_msg}. Retrying...")
                    time.sleep(0.1)

            if not slot_completed:
                print(f"[{comparison_key}] Game slot {slot+1} could not be completed after {max_attempts_per_slot} attempts. Aborting.")
                break

    # Write summary CSV
    csv_fields = [
        "comparison", "game", "pair", "attempt_number", "status", "result", "termination_reason",
        "plies", "candidate_arm", "base_arm", "candidate_color", "candidate_won", "candidate_points",
        "opening_id", "opening_name", "duration_seconds", "mean_cand_depth", "mean_base_depth",
        "mean_cand_time", "mean_base_time"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for g in valid_games:
            writer.writerow({k: g.get(k, "") for k in csv_fields})

    # Summary metrics
    n_valid = len(valid_games)
    cand_wins = sum(1 for g in valid_games if g["result"] == ("1-0" if g["candidate_color"] == "white" else "0-1"))
    base_wins = sum(1 for g in valid_games if g["result"] == ("0-1" if g["candidate_color"] == "white" else "1-0"))
    draws = sum(1 for g in valid_games if g["result"] == "1/2-1/2")
    cand_points = sum(g["candidate_points"] for g in valid_games)
    score_pct = (cand_points / n_valid * 100.0) if n_valid > 0 else 0.0

    complete_pairs = n_valid // 2
    infr_failures = sum(1 for a in attempts if a["status"] != "completed")

    match_summary = {
        "valid_games": n_valid,
        "complete_pairs": complete_pairs,
        "total_attempts": len(attempts),
        "infrastructure_failures": infr_failures,
        "candidate_wins": cand_wins,
        "draws": draws,
        "reference_wins": base_wins,
        "candidate_points": cand_points,
        "candidate_score_pct": round(score_pct, 2),
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
    print(f"MATCH FINISHED: {n_valid}/{games} valid games, {len(attempts)} attempts")
    print(f"Infrastructure Failures: {infr_failures}")
    print(f"Candidate ({cand_arm['name']}): {cand_wins}W / {draws}D / {base_wins}L ({score_pct:.1f}%)")
    print(f"Valid Complete Pairs: {complete_pairs}/{pairs_count}")
    print("=" * 65 + "\n")

    return full_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Project Janus v0.37 ablation match.")
    parser.add_argument("--comparison", type=str, default="b_vs_c", choices=["b_vs_c", "a_vs_b", "a_vs_c", "all"],
                        help="Comparison to run: b_vs_c (primary), a_vs_b (secondary), a_vs_c (contextual), or all")
    parser.add_argument("--games", type=int, default=100, help="Number of games per comparison (default: 100)")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Opening RNG seed")
    parser.add_argument("--parallel", action="store_true", help="Run comparisons in parallel")
    args = parser.parse_args()

    comps_to_run = ["b_vs_c", "a_vs_b", "a_vs_c"] if args.comparison == "all" else [args.comparison]
    if args.parallel and len(comps_to_run) > 1:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(comps_to_run)) as executor:
            futures = [
                executor.submit(
                    run_paired_match_v037,
                    comparison_key=c_key,
                    output_dir_path=args.out_dir or COMPARISONS[c_key]["default_dir"],
                    games=args.games,
                    seed=args.seed,
                )
                for c_key in comps_to_run
            ]
            for f in concurrent.futures.as_completed(futures):
                f.result()
    else:
        for c_key in comps_to_run:
            target_dir = args.out_dir or COMPARISONS[c_key]["default_dir"]
            run_paired_match_v037(
                comparison_key=c_key,
                output_dir_path=target_dir,
                games=args.games,
                seed=args.seed,
            )
