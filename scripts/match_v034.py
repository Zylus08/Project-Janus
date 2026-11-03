"""Project Janus v0.34 - Fixed-Time Playing-Strength Match Harness.

Executes controlled, colour-balanced, paired matches between:
- Reference: Janus v0.30 (commit 05de411) from .worktree_v030
- Candidate: Janus v0.34 (tapered evaluation + evaluation features) with --eval-all
under fixed movetime budgets (e.g. 500ms).
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
from typing import Any

import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]


def load_openings(openings_path: Path, count: int, seed: int = 42) -> list[dict[str, Any]]:
    """Load and deterministically select opening positions for paired matches."""
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


def summarize_match(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate and pair-level statistics from completed games."""
    cand_wins = 0
    cand_draws = 0
    cand_losses = 0
    unfinished = 0

    by_color = {
        "white": {"wins": 0, "draws": 0, "losses": 0, "games": 0, "score_pts": 0.0},
        "black": {"wins": 0, "draws": 0, "losses": 0, "games": 0, "score_pts": 0.0},
    }

    pairs_dict: dict[int, list[dict[str, Any]]] = {}

    for row in rows:
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
        else:
            unfinished += 1

        by_color[color]["games"] += 1

    total_completed = cand_wins + cand_draws + cand_losses
    cand_score = cand_wins + 0.5 * cand_draws
    cand_score_pct = (cand_score / total_completed * 100.0) if total_completed > 0 else 0.0

    # Pair outcomes
    pair_outcomes = {"won": 0, "drawn": 0, "lost": 0, "incomplete": 0}
    pair_diffs: list[float] = []

    for p_num, p_rows in pairs_dict.items():
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
    if total_completed > 0:
        p_hat = cand_score / total_completed
        if 0 < p_hat < 1:
            elo_diff = -400.0 * math.log10((1.0 - p_hat) / p_hat)
            var_p = (p_hat * (1.0 - p_hat)) / total_completed
            se_p = math.sqrt(var_p)
            se_elo = (400.0 / (math.log(10) * p_hat * (1.0 - p_hat))) * se_p
            elo_ci = [round(elo_diff - 1.96 * se_elo, 1), round(elo_diff + 1.96 * se_elo, 1)]

    # Paired sign test
    decisive_pairs = pair_outcomes["won"] + pair_outcomes["lost"]
    sign_test_p = None
    if decisive_pairs > 0:
        from math import comb
        k = min(pair_outcomes["won"], pair_outcomes["lost"])
        sign_test_p = sum(comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        sign_test_p = min(1.0, sign_test_p)

    return {
        "total_completed": total_completed,
        "unfinished": unfinished,
        "candidate_wins": cand_wins,
        "candidate_draws": cand_draws,
        "candidate_losses": cand_losses,
        "candidate_score": cand_score,
        "candidate_score_pct": round(cand_score_pct, 2),
        "estimated_elo_diff": round(elo_diff, 1) if elo_diff is not None else None,
        "elo_95_ci": elo_ci,
        "by_color": by_color,
        "pairs_summary": {
            "total_pairs": len(pairs_dict),
            "completed_pairs": len(pair_diffs),
            "pairs_won": pair_outcomes["won"],
            "pairs_drawn": pair_outcomes["drawn"],
            "pairs_lost": pair_outcomes["lost"],
            "decisive_pairs": decisive_pairs,
            "sign_test_p_value": round(sign_test_p, 4) if sign_test_p is not None else None,
        },
    }


def write_reports(
    json_path: Path,
    csv_path: Path,
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    elapsed_so_far: float,
) -> None:
    """Safely write JSON, CSV, and summary reports atomically."""
    summary = summarize_match(rows)

    full_payload = {
        "metadata": {
            **metadata,
            "elapsed_seconds": round(elapsed_so_far, 1),
            "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        },
        "summary": summary,
        "games": rows,
    }

    # Write JSON atomically
    tmp_json = json_path.with_suffix(".tmp.json")
    with tmp_json.open("w", encoding="utf-8") as f:
        json.dump(full_payload, f, indent=2)
    tmp_json.replace(json_path)

    # Write summary-only JSON
    summary_path = json_path.parent / json_path.name.replace(".json", "_summary.json")
    tmp_sum = summary_path.with_suffix(".tmp.json")
    with tmp_sum.open("w", encoding="utf-8") as f:
        json.dump({"metadata": full_payload["metadata"], "summary": summary}, f, indent=2)
    tmp_sum.replace(summary_path)

    # Write CSV atomically
    if rows:
        tmp_csv = csv_path.with_suffix(".tmp.csv")
        fieldnames = [
            "game", "pair", "opening_id", "opening_name", "candidate_color",
            "white", "black", "result", "candidate_score", "termination",
            "plies", "duration_seconds", "movetime_ms", "start_fen",
            "avg_cand_depth", "avg_base_depth", "avg_cand_move_time",
            "avg_base_move_time", "avg_cand_nodes", "avg_base_nodes"
        ]
        with tmp_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp_csv.replace(csv_path)


def play_one_game(
    base_engine: chess.engine.SimpleEngine,
    cand_engine: chess.engine.SimpleEngine,
    game_number: int,
    pair_number: int,
    cand_color: chess.Color,
    movetime_s: float,
    max_plies: int,
    start_fen: str | None,
    opening_id: str,
    opening_name: str,
) -> tuple[chess.pgn.Game, dict[str, Any]]:
    """Play one game with fixed per-move time control and track search statistics."""
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen else chess.Board()

    game = chess.pgn.Game()
    if start_fen and start_fen != chess.STARTING_FEN:
        game.setup(board)

    white_name = "Janus-v0.34" if cand_color == chess.WHITE else "Janus-v0.30"
    black_name = "Janus-v0.30" if cand_color == chess.WHITE else "Janus-v0.34"

    game.headers["Event"] = "Project Janus v0.34 Playing-Strength Match"
    game.headers["Site"] = "Local"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = white_name
    game.headers["Black"] = black_name
    game.headers["TimeControl"] = f"movetime {int(movetime_s * 1000)}ms"
    game.headers["Opening"] = f"{opening_id} ({opening_name})"

    node = game
    result_string = None
    termination_reason = None

    move_log: list[dict[str, Any]] = []
    cand_depths = []
    base_depths = []
    cand_times = []
    base_times = []
    cand_nodes_list = []
    base_nodes_list = []

    limit = chess.engine.Limit(time=movetime_s)

    for ply in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break

        is_cand_turn = (board.turn == cand_color)
        current_engine = cand_engine if is_cand_turn else base_engine
        curr_name = "Janus-v0.34" if is_cand_turn else "Janus-v0.30"

        t0 = time.monotonic()
        try:
            res = current_engine.play(board, limit, info=chess.engine.INFO_ALL)
            elapsed_move = time.monotonic() - t0

            if res.move is None or res.move not in board.legal_moves:
                result_string = "0-1" if board.turn == chess.WHITE else "1-0"
                termination_reason = f"illegal move by {curr_name}"
                break

            info = res.info or {}
            depth_reached = info.get("depth", 0)
            nodes_searched = info.get("nodes", 0)

            if is_cand_turn:
                cand_depths.append(depth_reached)
                cand_times.append(elapsed_move)
                cand_nodes_list.append(nodes_searched)
            else:
                base_depths.append(depth_reached)
                base_times.append(elapsed_move)
                base_nodes_list.append(nodes_searched)

            move_log.append({
                "ply": ply + 1,
                "player": curr_name,
                "color": "white" if board.turn == chess.WHITE else "black",
                "move": res.move.uci(),
                "time_s": round(elapsed_move, 3),
                "depth": depth_reached,
                "nodes": nodes_searched,
            })

            node = node.add_variation(res.move)
            board.push(res.move)

        except Exception as exc:
            result_string = "0-1" if board.turn == chess.WHITE else "1-0"
            termination_reason = f"engine crash ({curr_name}): {exc}"
            break

    duration = round(time.monotonic() - game_start, 2)

    if result_string is None:
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
            termination_reason = "unknown draw"

    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    cand_score = 0.5
    if result_string == "1-0":
        cand_score = 1.0 if cand_color == chess.WHITE else 0.0
    elif result_string == "0-1":
        cand_score = 0.0 if cand_color == chess.WHITE else 1.0

    row = {
        "game": game_number,
        "pair": pair_number,
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
        "movetime_ms": int(movetime_s * 1000),
        "start_fen": start_fen or chess.STARTING_FEN,
        "avg_cand_depth": round(sum(cand_depths) / len(cand_depths), 2) if cand_depths else None,
        "avg_base_depth": round(sum(base_depths) / len(base_depths), 2) if base_depths else None,
        "avg_cand_move_time": round(sum(cand_times) / len(cand_times), 4) if cand_times else None,
        "avg_base_move_time": round(sum(base_times) / len(base_times), 4) if base_times else None,
        "avg_cand_nodes": round(sum(cand_nodes_list) / len(cand_nodes_list), 0) if cand_nodes_list else None,
        "avg_base_nodes": round(sum(base_nodes_list) / len(base_nodes_list), 0) if base_nodes_list else None,
        "moves": move_log,
    }

    return game, row


def run_match(
    games: int = 100,
    movetime_ms: int = 500,
    max_plies: int = 200,
    seed: int = 42,
    match_name: str = "v034_match_500ms",
    openings_file: str = "benchmarks/openings.json",
    base_dir_path: str = ".worktree_v030",
    cand_dir_path: str = ".",
) -> dict[str, Any]:
    """Execute fixed-time paired match between v0.30 reference and v0.34 candidate."""
    base_dir = os.path.abspath(base_dir_path)
    cand_dir = os.path.abspath(cand_dir_path)

    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"Reference v0.30 worktree not found at {base_dir}")

    output_dir = ROOT / "analysis" / "v0.34" / "match"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{match_name}.json"
    csv_path = output_dir / f"{match_name}.csv"
    pgn_path = output_dir / f"{match_name}.pgn"

    rows: list[dict[str, Any]] = []
    start_index = 0
    if json_path.is_file():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
            rows = existing.get("games", [])
            start_index = len(rows)
            print(f"Resuming match from game {start_index + 1}/{games}...")
        except Exception:
            rows = []
            start_index = 0

    pairs_count = games // 2
    openings_path = ROOT / openings_file
    openings = load_openings(openings_path, count=pairs_count, seed=seed)

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "05de411",
        "baseline_name": "Janus-v0.30",
        "candidate_commit": "HEAD",
        "candidate_name": "Janus-v0.34",
        "time_control": f"fixed movetime {movetime_ms}ms",
        "movetime_ms": movetime_ms,
        "movetime_s": movetime_ms / 1000.0,
        "max_plies": max_plies,
        "total_games_requested": games,
        "pairs_requested": pairs_count,
        "seed": seed,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    start_time = time.monotonic()

    if start_index >= games:
        print(f"Match already complete ({start_index}/{games} games).")
        return json.loads(json_path.read_text(encoding="utf-8"))

    env_base = os.environ.copy()
    env_base["PYTHONPATH"] = os.path.join(base_dir, "src")

    base_cmd = [sys.executable, "-m", "janus.uci", "--name", "Janus-v0.30"]
    cand_cmd = [sys.executable, "-m", "janus.uci", "--name", "Janus-v0.34", "--eval-all"]

    print(f"Launching match: {games} games ({pairs_count} pairs) at {movetime_ms}ms movetime...")
    print(f"  Reference: {base_cmd} (in {base_dir})")
    print(f"  Candidate: {cand_cmd} (in {cand_dir})")

    with (
        chess.engine.SimpleEngine.popen_uci(base_cmd, cwd=base_dir, env=env_base) as base_eng,
        chess.engine.SimpleEngine.popen_uci(cand_cmd, cwd=cand_dir) as cand_eng,
    ):
        for eng in (base_eng, cand_eng):
            if "Hash" in eng.options:
                eng.configure({"Hash": 128})

        pgn_mode = "a" if (start_index > 0 and pgn_path.is_file()) else "w"
        with pgn_path.open(pgn_mode, encoding="utf-8") as pgn_file:
            for i in range(start_index, games):
                pair_idx = i // 2
                opening = openings[pair_idx]
                cand_color = chess.WHITE if (i % 2 == 0) else chess.BLACK

                try:
                    base_eng.protocol.send_line("ucinewgame")
                    cand_eng.protocol.send_line("ucinewgame")
                    base_eng.ping()
                    cand_eng.ping()
                except Exception:
                    pass

                game_obj, row = play_one_game(
                    base_engine=base_eng,
                    cand_engine=cand_eng,
                    game_number=i + 1,
                    pair_number=pair_idx + 1,
                    cand_color=cand_color,
                    movetime_s=movetime_ms / 1000.0,
                    max_plies=max_plies,
                    start_fen=opening.get("fen"),
                    opening_id=opening.get("id", "startpos"),
                    opening_name=opening.get("name", "Standard startpos"),
                )

                pgn_file.write(str(game_obj) + "\n\n")
                pgn_file.flush()
                rows.append(row)

                elapsed_so_far = time.monotonic() - start_time
                write_reports(json_path, csv_path, rows, metadata, elapsed_so_far)

                print(
                    f"Game {i+1:3d}/{games} [Pair {pair_idx+1:2d} | {'W' if cand_color == chess.WHITE else 'B'}]: "
                    f"Result: {row['result']:7s} ({row['candidate_score']:.1f}) | "
                    f"Plies: {row['plies']:3d} | {row['duration_seconds']:5.1f}s | "
                    f"CandDepth: {row['avg_cand_depth'] or 0:.1f} | BaseDepth: {row['avg_base_depth'] or 0:.1f} | "
                    f"CandTime: {row['avg_cand_move_time'] or 0:.3f}s | BaseTime: {row['avg_base_move_time'] or 0:.3f}s"
                )

    final_summary = summarize_match(rows)
    print("\n" + "=" * 60)
    print(f"MATCH COMPLETE: {len(rows)} games")
    print(f"Candidate: {final_summary['candidate_wins']}W / {final_summary['candidate_draws']}D / {final_summary['candidate_losses']}L ({final_summary['candidate_score_pct']}%)")
    print(f"Pairs: {final_summary['pairs_summary']['pairs_won']}W / {final_summary['pairs_summary']['pairs_drawn']}D / {final_summary['pairs_summary']['pairs_lost']}L")
    if final_summary['estimated_elo_diff'] is not None:
        print(f"Estimated Elo diff: {final_summary['estimated_elo_diff']:+.1f} (95% CI: {final_summary['elo_95_ci']})")
    print("=" * 60)

    return final_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Janus v0.34 Match Runner")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--movetime-ms", type=int, default=500)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--match-name", type=str, default="v034_match_500ms")
    parser.add_argument("--openings", type=str, default="benchmarks/openings.json")
    parser.add_argument("--base-dir", type=str, default=".worktree_v030")
    parser.add_argument("--pilot", action="store_true", help="Run 2-game pilot validation")
    args = parser.parse_args()

    games = 2 if args.pilot else args.games
    match_name = "v034_pilot_500ms" if args.pilot else args.match_name

    run_match(
        games=games,
        movetime_ms=args.movetime_ms,
        max_plies=args.max_plies,
        seed=args.seed,
        match_name=match_name,
        openings_file=args.openings,
        base_dir_path=args.base_dir,
    )


if __name__ == "__main__":
    main()
