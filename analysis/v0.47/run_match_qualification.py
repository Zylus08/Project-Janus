"""Project Janus v0.47 - Controlled Head-to-Head Match Qualification.

Executes colour-balanced, paired head-to-head match between:
- Engine A: Janus-K0 (Baseline: eager sorting, enable_lazy_move_selection=False)
- Engine B: Janus-L1 (Candidate: lazy move selection, enable_lazy_move_selection=True)

Played across 25 standardized opening pairs (50 games total).
For each opening pair:
  Game 1: K0 as White, L1 as Black
  Game 2: L1 as White, K0 as Black
Time control: 1000ms + 50ms increment per move.
Preserves full PGNs, move telemetry, and paired statistical attribution.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from janus.engine_session import SupervisedEngineSession
from janus.time_manager import TimeManager, TimeManagerConfig


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def play_game(
    white_session: SupervisedEngineSession,
    black_session: SupervisedEngineSession,
    white_name: str,
    black_name: str,
    base_time_ms: int,
    inc_time_ms: int,
    game_number: int,
    pair_number: int,
    max_plies: int,
    start_fen: str,
    opening_id: str,
    opening_name: str,
) -> tuple[chess.pgn.Game, dict[str, Any], list[dict[str, Any]]]:
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen and start_fen != chess.STARTING_FEN else chess.Board()

    game = chess.pgn.Game()
    game.headers["Event"] = "Janus v0.47 Qualification - K0 vs L1"
    game.headers["Site"] = "Local Subprocess Session"
    game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = white_name
    game.headers["Black"] = black_name
    game.headers["TimeControl"] = f"{base_time_ms / 1000.0}+{inc_time_ms / 1000.0}"

    if start_fen and start_fen != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = start_fen

    node = game
    wtime_ms = float(base_time_ms)
    btime_ms = float(base_time_ms)

    white_depths: list[int] = []
    black_depths: list[int] = []
    white_times: list[float] = []
    black_times: list[float] = []
    move_telemetry_rows: list[dict[str, Any]] = []

    result_string = "*"
    termination_reason = "unknown"

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

        is_white = (board.turn == chess.WHITE)
        current_sess = white_session if is_white else black_session
        curr_name = white_name if is_white else black_name
        current_clock = wtime_ms if is_white else btime_ms

        try:
            move_res = current_sess.play_move(
                board=board,
                wtime=max(10, int(wtime_ms)),
                btime=max(10, int(btime_ms)),
                winc=inc_time_ms,
                binc=inc_time_ms,
            )
        except Exception as err:
            result_string = "0-1" if is_white else "1-0"
            termination_reason = f"engine_error_{curr_name}"
            break

        elapsed_ms = move_res.time_s * 1000.0

        if is_white:
            wtime_ms = max(0.0, wtime_ms - elapsed_ms + inc_time_ms)
            white_depths.append(move_res.depth or 0)
            white_times.append(elapsed_ms)
        else:
            btime_ms = max(0.0, btime_ms - elapsed_ms + inc_time_ms)
            black_depths.append(move_res.depth or 0)
            black_times.append(elapsed_ms)

        if move_res.move is None or move_res.move not in board.legal_moves:
            result_string = "0-1" if is_white else "1-0"
            termination_reason = f"illegal_move_{curr_name}"
            break

        move_telemetry_rows.append({
            "game": game_number,
            "pair": pair_number,
            "opening_id": opening_id,
            "ply": ply + 1,
            "player": curr_name,
            "color": "white" if is_white else "black",
            "move": move_res.move.uci(),
            "actual_time_ms": round(elapsed_ms, 1),
            "clock_after_ms": round(wtime_ms if is_white else btime_ms, 1),
            "depth": move_res.depth or 0,
            "nodes": move_res.nodes or 0,
            "nps": int(move_res.nodes / move_res.time_s) if move_res.time_s > 0 else 0,
        })

        node = node.add_variation(move_res.move)
        board.push(move_res.move)

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

    game_duration = time.monotonic() - game_start

    # Determine points for K0 and L1
    if white_name == "Janus-K0":
        if result_string == "1-0":
            k0_pts, l1_pts = 1.0, 0.0
        elif result_string == "0-1":
            k0_pts, l1_pts = 0.0, 1.0
        else:
            k0_pts, l1_pts = 0.5, 0.5
    else:  # white is L1
        if result_string == "1-0":
            k0_pts, l1_pts = 0.0, 1.0
        elif result_string == "0-1":
            k0_pts, l1_pts = 1.0, 0.0
        else:
            k0_pts, l1_pts = 0.5, 0.5

    record = {
        "game": game_number,
        "pair": pair_number,
        "white": white_name,
        "black": black_name,
        "result": result_string,
        "termination_reason": termination_reason,
        "plies": len(board.move_stack),
        "k0_points": k0_pts,
        "l1_points": l1_pts,
        "opening_id": opening_id,
        "opening_name": opening_name,
        "duration_seconds": round(game_duration, 2),
        "mean_white_depth": round(sum(white_depths) / len(white_depths), 2) if white_depths else 0.0,
        "mean_black_depth": round(sum(black_depths) / len(black_depths), 2) if black_depths else 0.0,
    }

    return game, record, move_telemetry_rows


def run_match(
    openings_path: Path,
    output_dir: Path,
    n_pairs: int = 25,
    base_time_ms: int = 1000,
    inc_time_ms: int = 50,
    max_plies: int = 160,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    openings = json.loads(openings_path.read_text(encoding="utf-8"))
    openings_to_play = openings[:n_pairs]

    k0_cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m", "janus.uci",
        "--name", "Janus-K0",
        "--eval-all",
    ]

    l1_cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m", "janus.uci",
        "--name", "Janus-L1",
        "--eval-all",
        "--enable-lazy-move-selection",
    ]

    pgn_path = output_dir / "match_results.pgn"
    results_json_path = output_dir / "match_results.json"
    results_csv_path = output_dir / "match_results.csv"
    moves_csv_path = output_dir / "match_moves.csv"

    print("=" * 70, flush=True)
    print(f"PROJECT JANUS v0.47 HEAD-TO-HEAD MATCH: K0 vs L1", flush=True)
    print(f"Openings: {openings_path.name} ({len(openings_to_play)} pairs, {len(openings_to_play)*2} games)", flush=True)
    print(f"Time control: {base_time_ms}ms + {inc_time_ms}ms", flush=True)
    print("=" * 70, flush=True)

    games_records = []
    game_num = 0

    with open(pgn_path, "w", encoding="utf-8") as pgn_file, \
         open(moves_csv_path, "w", newline="", encoding="utf-8") as moves_f:

        move_fields = ["game", "pair", "opening_id", "ply", "player", "color", "move", "actual_time_ms", "clock_after_ms", "depth", "nodes", "nps"]
        moves_writer = csv.DictWriter(moves_f, fieldnames=move_fields)
        moves_writer.writeheader()

        for p_idx, op in enumerate(openings_to_play, 1):
            op_id = op["id"]
            op_name = op["name"]
            op_fen = op["fen"]

            # Game 1: K0 White vs L1 Black
            game_num += 1
            with SupervisedEngineSession(cmd=k0_cmd, name="Janus-K0", cwd=ROOT) as sess_k0, \
                 SupervisedEngineSession(cmd=l1_cmd, name="Janus-L1", cwd=ROOT) as sess_l1:
                g1_pgn, g1_rec, g1_moves = play_game(
                    white_session=sess_k0, black_session=sess_l1,
                    white_name="Janus-K0", black_name="Janus-L1",
                    base_time_ms=base_time_ms, inc_time_ms=inc_time_ms,
                    game_number=game_num, pair_number=p_idx, max_plies=max_plies,
                    start_fen=op_fen, opening_id=op_id, opening_name=op_name,
                )
                print(g1_pgn, file=pgn_file, end="\n\n")
                pgn_file.flush()
                for m in g1_moves:
                    moves_writer.writerow(m)
                moves_f.flush()
                games_records.append(g1_rec)
                print(f"Game {game_num:2d} (Pair {p_idx:2d}A): {g1_rec['white']} vs {g1_rec['black']} -> {g1_rec['result']} ({g1_rec['termination_reason']}, {g1_rec['plies']} plies, {g1_rec['duration_seconds']}s)", flush=True)

            # Game 2: L1 White vs K0 Black
            game_num += 1
            with SupervisedEngineSession(cmd=l1_cmd, name="Janus-L1", cwd=ROOT) as sess_l1, \
                 SupervisedEngineSession(cmd=k0_cmd, name="Janus-K0", cwd=ROOT) as sess_k0:
                g2_pgn, g2_rec, g2_moves = play_game(
                    white_session=sess_l1, black_session=sess_k0,
                    white_name="Janus-L1", black_name="Janus-K0",
                    base_time_ms=base_time_ms, inc_time_ms=inc_time_ms,
                    game_number=game_num, pair_number=p_idx, max_plies=max_plies,
                    start_fen=op_fen, opening_id=op_id, opening_name=op_name,
                )
                print(g2_pgn, file=pgn_file, end="\n\n")
                pgn_file.flush()
                for m in g2_moves:
                    moves_writer.writerow(m)
                moves_f.flush()
                games_records.append(g2_rec)
                print(f"Game {game_num:2d} (Pair {p_idx:2d}B): {g2_rec['white']} vs {g2_rec['black']} -> {g2_rec['result']} ({g2_rec['termination_reason']}, {g2_rec['plies']} plies, {g2_rec['duration_seconds']}s)", flush=True)

    # Save summary
    k0_total = sum(r["k0_points"] for r in games_records)
    l1_total = sum(r["l1_points"] for r in games_records)
    k0_wins = sum(1 for r in games_records if r["k0_points"] == 1.0)
    l1_wins = sum(1 for r in games_records if r["l1_points"] == 1.0)
    draws = sum(1 for r in games_records if r["k0_points"] == 0.5)

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_games": len(games_records),
        "pairs": n_pairs,
        "k0_points": k0_total,
        "l1_points": l1_total,
        "k0_wins": k0_wins,
        "l1_wins": l1_wins,
        "draws": draws,
        "k0_win_rate": k0_total / len(games_records),
        "l1_win_rate": l1_total / len(games_records),
    }

    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "games": games_records}, f, indent=2)

    with open(results_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(games_records[0].keys()))
        writer.writeheader()
        writer.writerows(games_records)

    print("\n" + "=" * 70, flush=True)
    print("MATCH COMPLETE", flush=True)
    print(f"K0 Score: {k0_total} / {len(games_records)} ({k0_total/len(games_records):.1%}) [+{k0_wins} ={draws} -{l1_wins}]", flush=True)
    print(f"L1 Score: {l1_total} / {len(games_records)} ({l1_total/len(games_records):.1%}) [+{l1_wins} ={draws} -{k0_wins}]", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openings", default=str(ROOT / "analysis" / "v0.43" / "openings_v043_100.json"))
    parser.add_argument("--pairs", type=int, default=25)
    parser.add_argument("--output-dir", default=str(ROOT / "analysis" / "v0.47" / "matches"))
    parser.add_argument("--time-ms", type=int, default=1000)
    parser.add_argument("--inc-ms", type=int, default=50)
    args = parser.parse_args()

    run_match(
        openings_path=Path(args.openings),
        output_dir=Path(args.output_dir),
        n_pairs=args.pairs,
        base_time_ms=args.time_ms,
        inc_time_ms=args.inc_ms,
    )

