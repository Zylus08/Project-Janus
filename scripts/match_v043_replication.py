"""Project Janus v0.43 - Independent Strength Replication Harness.

Executes colour-balanced, counterbalanced, paired ablation matches comparing
Baseline K0 against Candidate RFP against Stockfish 19 Elo 1320.

For each opening position:
- Both K0 and RFP play the position as White and as Black against Stockfish 19.
- Order is counterbalanced:
  Even pair indices: K0(W), K0(B), RFP(W), RFP(B)
  Odd pair indices:  RFP(W), RFP(B), K0(W), K0(B)
- Full move telemetry, clock compliance, and PGN preservation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
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


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def play_game(
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
    start_fen: str,
    opening_id: str,
    opening_name: str,
) -> tuple[Optional[chess.pgn.Game], dict[str, Any], list[dict[str, Any]]]:
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen and start_fen != chess.STARTING_FEN else chess.Board()

    white_is_janus = (janus_color == chess.WHITE)
    white_session = janus_session if white_is_janus else sf_session
    black_session = sf_session if white_is_janus else janus_session

    game = chess.pgn.Game()
    game.headers["Event"] = f"Janus v0.43 Replication - {candidate_id.upper()}"
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
            }
            break

        actual_time_ms = move_res.time_s * 1000.0
        nps = int(move_res.nodes / move_res.time_s) if move_res.time_s > 0 else 0
        if is_janus_turn:
            janus_depths.append(move_res.depth)
            janus_times.append(actual_time_ms)
        else:
            sf_depths.append(move_res.depth)
            sf_times.append(actual_time_ms)

        overshoot_ms = max(0.0, actual_time_ms - target_alloc_ms) if is_janus_turn else 0.0
        clock_after = max(0.0, clock_before - actual_time_ms + inc_time_ms)

        if board.turn == chess.WHITE:
            wtime_ms = clock_after
        else:
            btime_ms = clock_after

        move_telemetry_rows.append({
            "candidate": candidate_id,
            "game": game_number,
            "pair": pair_number,
            "opening_id": opening_id,
            "ply": ply + 1,
            "player": "janus" if is_janus_turn else "stockfish",
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

        if move_res.move not in board.legal_moves:
            infrastructure_error = {
                "failed_session": curr_name,
                "error_type": "IllegalMoveError",
                "message": f"Illegal move played: {move_res.move.uci()} in fen {board.fen()}",
            }
            break

        node = node.add_variation(move_res.move)
        board.push(move_res.move)

    game_duration = time.monotonic() - game_start

    if infrastructure_error is not None:
        return None, {
            "candidate": candidate_id,
            "game": game_number,
            "pair": pair_number,
            "attempt_number": attempt_number,
            "status": "infrastructure_failure",
            "failure_category": infrastructure_error["error_type"],
            "infrastructure_error": infrastructure_error,
            "duration_seconds": round(game_duration, 2),
        }, move_telemetry_rows

    if result_string == "*":
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result_string = outcome.result()
            termination_reason = f"adjudicated_{outcome.termination.name.lower()}"
        else:
            result_string = "1/2-1/2"
            termination_reason = "max_plies_draw"

    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    # Compute Janus points
    if result_string == "1/2-1/2":
        janus_pts = 0.5
        janus_won = False
    elif result_string == "1-0":
        janus_pts = 1.0 if white_is_janus else 0.0
        janus_won = white_is_janus
    elif result_string == "0-1":
        janus_pts = 0.0 if white_is_janus else 1.0
        janus_won = not white_is_janus
    else:
        janus_pts = 0.5
        janus_won = False

    mean_jd = sum(janus_depths) / len(janus_depths) if janus_depths else 0.0
    mean_sfd = sum(sf_depths) / len(sf_depths) if sf_depths else 0.0
    mean_jt = sum(janus_times) / len(janus_times) if janus_times else 0.0
    mean_sft = sum(sf_times) / len(sf_times) if sf_times else 0.0

    attempt_record = {
        "candidate": candidate_id,
        "game": game_number,
        "pair": pair_number,
        "attempt_number": attempt_number,
        "status": "completed",
        "result": result_string,
        "termination_reason": termination_reason,
        "plies": len(board.move_stack),
        "janus_color": "white" if white_is_janus else "black",
        "janus_won": janus_won,
        "janus_points": janus_pts,
        "opening_id": opening_id,
        "opening_name": opening_name,
        "duration_seconds": round(game_duration, 2),
        "mean_janus_depth": round(mean_jd, 2),
        "mean_sf_depth": round(mean_sfd, 2),
        "mean_janus_time": round(mean_jt, 2),
        "mean_sf_time": round(mean_sft, 2),
    }

    return game, attempt_record, move_telemetry_rows


def run_replication(
    openings_path: Path,
    output_dir: Path,
    n_pairs: int = 100,
    base_time_ms: int = 3000,
    inc_time_ms: int = 100,
    max_plies: int = 200,
    max_attempts_per_slot: int = 3,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    openings = json.loads(openings_path.read_text(encoding="utf-8"))
    openings_hash = compute_file_sha256(openings_path)

    openings_to_play = openings[:n_pairs]

    sf_cmd = [STOCKFISH_PATH]
    sf_options = {
        "Threads": 1,
        "Hash": 64,
        "UCI_LimitStrength": True,
        "UCI_Elo": 1320,
    }

    k0_cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m", "janus.uci",
        "--name", "Janus-K0",
        "--eval-all",
        "--time-policy", "arm_c",
    ]

    rfp_cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m", "janus.uci",
        "--name", "Janus-RFP",
        "--eval-all",
        "--time-policy", "arm_c",
        "--enable-rfp",
    ]

    janus_tm = TimeManager(TimeManagerConfig())

    pgn_path = output_dir / "match_results.pgn"
    moves_csv_path = output_dir / "match_moves.csv"
    results_csv_path = output_dir / "match_results.csv"
    attempts_path = output_dir / "attempt_log.json"
    results_json_path = output_dir / "match_results.json"

    attempts: list[dict[str, Any]] = []
    valid_games: list[dict[str, Any]] = []

    move_fields = [
        "candidate", "game", "pair", "opening_id", "ply", "player", "is_janus", "color", "move",
        "clock_before_ms", "inc_ms", "target_alloc_ms", "actual_time_ms", "overshoot_ms",
        "clock_after_ms", "depth", "nodes", "nps", "is_emergency"
    ]

    print("\n" + "=" * 80)
    print("PROJECT JANUS v0.43 INDEPENDENT REPLICATION HARNESS")
    print(f"Openings: {openings_path.name} (SHA-256: {openings_hash[:16]}...)")
    print(f"Pairs Planned: {len(openings_to_play)} | Total Games: {len(openings_to_play) * 4}")
    print(f"Time Control: {base_time_ms}ms + {inc_time_ms}ms Fischer")
    print(f"Output Directory: {output_dir}")
    print("=" * 80 + "\n")

    game_counter = 0

    with open(pgn_path, "w", encoding="utf-8") as pgn_file, \
         open(moves_csv_path, "w", newline="", encoding="utf-8") as moves_f:

        moves_writer = csv.DictWriter(moves_f, fieldnames=move_fields)
        moves_writer.writeheader()

        for pair_idx, op_info in enumerate(openings_to_play):
            pair_num = pair_idx + 1
            op_id = op_info["id"]
            op_name = op_info["name"]
            op_fen = op_info["fen"]

            # Counterbalance order
            if pair_idx % 2 == 0:
                engine_schedule = [("k0", chess.WHITE), ("k0", chess.BLACK), ("rfp", chess.WHITE), ("rfp", chess.BLACK)]
            else:
                engine_schedule = [("rfp", chess.WHITE), ("rfp", chess.BLACK), ("k0", chess.WHITE), ("k0", chess.BLACK)]

            for cand_id, color in engine_schedule:
                game_counter += 1
                cmd = rfp_cmd if cand_id == "rfp" else k0_cmd
                color_label = "W" if color == chess.WHITE else "B"

                completed_game = False
                for attempt_num in range(1, max_attempts_per_slot + 1):
                    try:
                        with SupervisedEngineSession(cmd=cmd, name=f"Janus-{cand_id.upper()}", cwd=ROOT) as janus_sess, \
                             SupervisedEngineSession(cmd=sf_cmd, name="Stockfish-19-Elo1320", cwd=ROOT) as sf_sess:
                            sf_sess.configure(sf_options)
                            game_pgn, att_rec, move_rows = play_game(
                                janus_session=janus_sess,
                                sf_session=sf_sess,
                                janus_tm=janus_tm,
                                candidate_id=cand_id,
                                base_time_ms=base_time_ms,
                                inc_time_ms=inc_time_ms,
                                game_number=game_counter,
                                pair_number=pair_num,
                                attempt_number=attempt_num,
                                janus_color=color,
                                max_plies=max_plies,
                                start_fen=op_fen,
                                opening_id=op_id,
                                opening_name=op_name,
                            )
                    except Exception as exc:
                        att_rec = {
                            "candidate": cand_id,
                            "game": game_counter,
                            "pair": pair_num,
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

                        # Write attempt log dynamically
                        attempts_path.write_text(json.dumps(attempts, indent=2), encoding="utf-8")

                        pts = att_rec["janus_points"]
                        res = att_rec["result"]
                        plies = att_rec["plies"]
                        dur = att_rec["duration_seconds"]
                        jd = att_rec["mean_janus_depth"]
                        print(
                            f"Pair {pair_num:3d}/100 | Game {game_counter:3d} | [{cand_id.upper()} {color_label}] "
                            f"Result: {res:<7} ({pts:3.1f}) | Plies: {plies:3d} | {dur:4.1f}s | Depth: {jd:4.1f}",
                            flush=True,
                        )
                        completed_game = True
                        break
                    else:
                        print(f"FAILED attempt {attempt_num} on game {game_counter}. Retrying...", flush=True)
                        time.sleep(0.1)

                if not completed_game:
                    print(f"CRITICAL: Game {game_counter} failed all attempts.")

    # Results CSV
    csv_fields = [
        "candidate", "game", "pair", "attempt_number", "status", "result", "termination_reason",
        "plies", "janus_color", "janus_won", "janus_points", "opening_id", "opening_name",
        "duration_seconds", "mean_janus_depth", "mean_sf_depth", "mean_janus_time", "mean_sf_time"
    ]
    with open(results_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for g in valid_games:
            writer.writerow({k: g.get(k) for k in csv_fields})

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "openings_manifest": str(openings_path),
        "openings_hash": openings_hash,
        "pairs_completed": len(valid_games) // 4,
        "total_valid_games": len(valid_games),
        "total_attempts": len(attempts),
        "k0_points": sum(g["janus_points"] for g in valid_games if g["candidate"] == "k0"),
        "rfp_points": sum(g["janus_points"] for g in valid_games if g["candidate"] == "rfp"),
    }
    results_json_path.write_text(json.dumps({"summary": summary, "games": valid_games}, indent=2), encoding="utf-8")
    print(f"\nReplication complete. Valid games: {len(valid_games)}.")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run v0.43 replication match.")
    parser.add_argument("--openings", type=str, default=str(ROOT / "analysis" / "v0.43" / "openings_v043_100.json"))
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "analysis" / "v0.43" / "match_replication"))
    args = parser.parse_args()

    run_replication(
        openings_path=Path(args.openings),
        output_dir=Path(args.output_dir),
        n_pairs=args.pairs,
    )
