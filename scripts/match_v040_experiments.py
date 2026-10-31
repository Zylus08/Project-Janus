"""Project Janus v0.40 - Controlled Experiment Match Runner.

Executes controlled, colour-balanced, paired matches against Stockfish 19 Elo 1320.
Supports candidates:
- 'k0': Current baseline (Q0 + K0 enabled)
- 'k1': King-safety ablation (uncastled king safety disabled)
- 'ord1': Quiet move ordering enhancements (history & countermove heuristics)
- 'rfp': Reverse futility pruning (experimental selective search)
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


def play_supervised_match_game(
    janus_session: SupervisedEngineSession,
    sf_session: SupervisedEngineSession,
    janus_tm: TimeManager,
    candidate_id: str,
    base_time_ms: int,
    inc_time_ms: int,
    game_number: int,
    pair_number: int,
    attempt_number: int,
    janus_color: chess.Color,
    max_plies: int,
    start_fen: str | None,
    opening_id: str,
    opening_name: str,
) -> tuple[Optional[chess.pgn.Game], dict[str, Any], list[dict[str, Any]]]:
    """Play a single game between Janus Candidate and Stockfish 19."""
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen else chess.Board()

    white_is_janus = (janus_color == chess.WHITE)
    white_session = janus_session if white_is_janus else sf_session
    black_session = sf_session if white_is_janus else janus_session

    game = chess.pgn.Game()
    game.headers["Event"] = f"Janus v0.40 Controlled Experiment - {candidate_id.upper()}"
    game.headers["Site"] = "Local Subprocess Session"
    game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = janus_session.name if white_is_janus else sf_session.name
    game.headers["Black"] = sf_session.name if white_is_janus else janus_session.name
    game.headers["TimeControl"] = f"{base_time_ms / 1000.0}+{inc_time_ms / 1000.0}"

    if start_fen and start_fen != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = start_fen

    node = game

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

        if is_janus_turn:
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
            move_res: MoveResult = current_session.play_move(
                board=board,
                wtime=int(wtime_ms),
                btime=int(btime_ms),
                winc=inc_time_ms,
                binc=inc_time_ms,
            )
        except (EngineTimeoutError, EngineProtocolError, EngineProcessError, EngineError) as err:
            infrastructure_error = {
                "failed_session": curr_name,
                "error_type": type(err).__name__,
                "message": str(err),
                "ply": ply + 1,
            }
            termination_reason = f"infrastructure_{type(err).__name__.lower()}"
            break

        actual_time_ms = move_res.time_s * 1000.0
        overshoot_ms = max(0.0, actual_time_ms - target_alloc_ms) if is_janus_turn else 0.0

        if board.turn == chess.WHITE:
            wtime_ms = max(0.0, wtime_ms - actual_time_ms) + inc_time_ms
            clock_after = wtime_ms
            if wtime_ms <= 0.0:
                result_string = "0-1"
                termination_reason = "white_flagged"
                break
        else:
            btime_ms = max(0.0, btime_ms - actual_time_ms) + inc_time_ms
            clock_after = btime_ms
            if btime_ms <= 0.0:
                result_string = "1-0"
                termination_reason = "black_flagged"
                break

        if is_janus_turn:
            janus_depths.append(move_res.depth)
            janus_times.append(move_res.time_s)
        else:
            sf_depths.append(move_res.depth)
            sf_times.append(move_res.time_s)

        nps = int(move_res.nodes / max(0.001, move_res.time_s))

        move_telemetry_rows.append({
            "candidate": candidate_id,
            "game": game_number,
            "pair": pair_number,
            "opening_id": opening_id,
            "ply": ply + 1,
            "player": curr_name,
            "is_janus": is_janus_turn,
            "color": active_color,
            "move": move_res.move.uci(),
            "clock_before_ms": round(clock_before, 1),
            "inc_ms": inc_time_ms,
            "target_alloc_ms": round(target_alloc_ms, 1),
            "actual_time_ms": round(actual_time_ms, 1),
            "overshoot_ms": round(overshoot_ms, 1),
            "clock_after_ms": round(clock_after, 1),
            "depth": move_res.depth,
            "nodes": move_res.nodes,
            "nps": nps,
            "is_emergency": is_emergency,
        })

        node = node.add_variation(move_res.move)
        board.push(move_res.move)

    if board.is_game_over() and termination_reason == "unknown":
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result_string = outcome.result()
            if outcome.winner == chess.WHITE:
                termination_reason = "checkmate_white_wins"
            elif outcome.winner == chess.BLACK:
                termination_reason = "checkmate_black_wins"
            else:
                termination_reason = f"draw_{outcome.termination.name.lower()}"
    elif termination_reason == "unknown":
        termination_reason = "max_plies_reached"
        result_string = "1/2-1/2"

    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    duration = time.monotonic() - game_start

    janus_won = False
    janus_points = 0.5
    if result_string == "1-0":
        janus_won = white_is_janus
        janus_points = 1.0 if white_is_janus else 0.0
    elif result_string == "0-1":
        janus_won = not white_is_janus
        janus_points = 0.0 if white_is_janus else 1.0

    attempt_record = {
        "candidate": candidate_id,
        "game": game_number,
        "pair": pair_number,
        "attempt_number": attempt_number,
        "status": "completed" if infrastructure_error is None else "infrastructure_failure",
        "result": result_string,
        "termination_reason": termination_reason,
        "plies": len(board.move_stack),
        "janus_color": "white" if white_is_janus else "black",
        "janus_won": janus_won,
        "janus_points": janus_points,
        "opening_id": opening_id,
        "opening_name": opening_name,
        "duration_seconds": round(duration, 2),
        "mean_janus_depth": round(sum(janus_depths) / len(janus_depths), 2) if janus_depths else 0.0,
        "mean_sf_depth": round(sum(sf_depths) / len(sf_depths), 2) if sf_depths else 0.0,
        "mean_janus_time": round(sum(janus_times) / len(janus_times), 3) if janus_times else 0.0,
        "mean_sf_time": round(sum(sf_times) / len(sf_times), 3) if sf_times else 0.0,
        "infrastructure_error": infrastructure_error,
    }

    if infrastructure_error is not None:
        return None, attempt_record, []

    return game, attempt_record, move_telemetry_rows


def run_experiment_match(
    candidate_id: str,
    n_games: int = 50,
    base_time_ms: int = 3000,
    inc_time_ms: int = 100,
    stockfish_path: str = STOCKFISH_PATH,
    openings_file: str = "benchmarks/openings.json",
    seed: int = 42,
    max_plies: int = 200,
    output_dir: Optional[Path] = None,
    max_attempts_per_slot: int = 3,
) -> dict[str, Any]:
    """Execute candidate match against Stockfish 19 Elo 1320."""
    if output_dir is None:
        output_dir = ROOT / "analysis" / "v0.40" / f"match_{candidate_id}"
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

    # Configure Candidate Janus Command
    janus_cmd = [
        sys.executable, "-m", "janus.uci",
        "--name", f"Janus-v0.40-{candidate_id.upper()}",
        "--eval-all",
        "--time-policy", "arm_c",
    ]

    if candidate_id == "k1":
        janus_cmd.append("--disable-uncastled-king-safety")
    elif candidate_id == "ord1":
        janus_cmd.append("--enable-ord1")
    elif candidate_id == "rfp":
        janus_cmd.append("--enable-rfp")

    sf_cmd = [stockfish_path]
    sf_options = {"Threads": 1, "Hash": 64, "UCI_LimitStrength": True, "UCI_Elo": 1320}

    janus_tm = TimeManager(config=TimeManagerConfig.arm_c_adaptive())

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": candidate_id,
        "title": f"Janus v0.40 Candidate {candidate_id.upper()} vs Stockfish 19 Elo 1320",
        "janus_cmd": janus_cmd,
        "stockfish_path": stockfish_path,
        "stockfish_options": sf_options,
        "time_mode": "fischer_increment",
        "base_time_ms": base_time_ms,
        "inc_time_ms": inc_time_ms,
        "max_plies": max_plies,
        "total_games_requested": n_games,
        "pairs_requested": pairs_count,
        "seed": seed,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    move_fields = [
        "candidate", "game", "pair", "opening_id", "ply", "player", "is_janus", "color", "move",
        "clock_before_ms", "inc_ms", "target_alloc_ms", "actual_time_ms", "overshoot_ms",
        "clock_after_ms", "depth", "nodes", "nps", "is_emergency"
    ]

    print("\n" + "=" * 65)
    print(f"STARTING V0.40 CONTROLLED EXPERIMENT: {candidate_id.upper()}")
    print(f"Janus Command: {' '.join(janus_cmd)}")
    print(f"Stockfish Options: {sf_options}")
    print(f"Time Control: {base_time_ms}ms + {inc_time_ms}ms Fischer increment")
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
                    with SupervisedEngineSession(cmd=janus_cmd, name=f"Janus-v0.40-{candidate_id.upper()}", cwd=ROOT) as janus_sess, \
                         SupervisedEngineSession(cmd=sf_cmd, name="Stockfish-19-Elo1320", cwd=ROOT) as sf_sess:
                        sf_sess.configure(sf_options)
                        game_pgn, att_rec, move_rows = play_supervised_match_game(
                            janus_session=janus_sess,
                            sf_session=sf_sess,
                            janus_tm=janus_tm,
                            candidate_id=candidate_id,
                            base_time_ms=base_time_ms,
                            inc_time_ms=inc_time_ms,
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
                        "candidate": candidate_id,
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
                    attempts_path.write_text(json.dumps(attempts, indent=2), encoding="utf-8")

                    pts = att_rec['janus_points']
                    res = att_rec['result']
                    pl = att_rec['plies']
                    dur = att_rec['duration_seconds']
                    jd = att_rec['mean_janus_depth']
                    sfd = att_rec['mean_sf_depth']
                    print(
                        f"[{candidate_id.upper()}] Game {slot+1:2d}/{n_games} [Pair {pair_idx+1:2d} | {color_label}] (Att {attempt_num}): "
                        f"Result: {res:<7} ({pts:3.1f}) | Plies: {pl:3d} | {dur:5.1f}s | "
                        f"JanusDepth: {jd:4.1f} | SFDepth: {sfd:4.1f}",
                        flush=True,
                    )
                    slot_completed = True
                    break
                else:
                    err_msg = att_rec.get("infrastructure_error", {}).get("message") or att_rec.get("message", "Unknown error")
                    print(f"[{candidate_id.upper()}] Game {slot+1} Attempt {attempt_num} FAILED: {err_msg}. Retrying...", flush=True)
                    time.sleep(0.1)

            if not slot_completed:
                print(f"[{candidate_id.upper()}] Game slot {slot+1} could not be completed. Aborting.")
                break

    # Summary CSV
    csv_fields = [
        "candidate", "game", "pair", "attempt_number", "status", "result", "termination_reason",
        "plies", "janus_color", "janus_won", "janus_points", "opening_id", "opening_name",
        "duration_seconds", "mean_janus_depth", "mean_sf_depth", "mean_janus_time", "mean_sf_time"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for g in valid_games:
            row = {k: g.get(k) for k in csv_fields}
            writer.writerow(row)

    attempts_path.write_text(json.dumps(attempts, indent=2), encoding="utf-8")

    janus_wins = sum(1 for g in valid_games if g.get("janus_points") == 1.0)
    draws = sum(1 for g in valid_games if g.get("janus_points") == 0.5)
    sf_wins = sum(1 for g in valid_games if g.get("janus_points") == 0.0)
    total_pts = sum(g.get("janus_points", 0.0) for g in valid_games)
    score_pct = (total_pts / len(valid_games) * 100.0) if valid_games else 0.0

    match_summary = {
        "valid_games": len(valid_games),
        "complete_pairs": len(valid_games) // 2,
        "total_attempts": len(attempts),
        "infrastructure_failures": len(attempts) - len(valid_games),
        "janus_wins": janus_wins,
        "draws": draws,
        "stockfish_wins": sf_wins,
        "janus_points": total_pts,
        "janus_score_pct": round(score_pct, 2),
    }

    full_output = {
        "metadata": metadata,
        "match_summary": match_summary,
        "valid_games": valid_games,
    }
    json_path.write_text(json.dumps(full_output, indent=2), encoding="utf-8")

    print("\n" + "=" * 65)
    print(f"MATCH COMPLETE: {candidate_id.upper()}")
    print(f"Valid Games: {len(valid_games)} / {n_games}")
    print(f"Score: {janus_wins}W - {draws}D - {sf_wins}L => {total_pts}/{len(valid_games)} ({score_pct:.1f}%)")
    print(f"Output saved to: {output_dir}")
    print("=" * 65 + "\n")

    return full_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run v0.40 controlled candidate match.")
    parser.add_argument("--candidate", type=str, required=True, choices=["k0", "k1", "ord1", "rfp"])
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--base-time", type=int, default=3000)
    parser.add_argument("--inc-time", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stockfish", type=str, default=STOCKFISH_PATH)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    run_experiment_match(
        candidate_id=args.candidate,
        n_games=args.games,
        base_time_ms=args.base_time,
        inc_time_ms=args.inc_time,
        stockfish_path=args.stockfish,
        seed=args.seed,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )

