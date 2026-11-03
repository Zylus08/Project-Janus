"""Project Janus v0.32 - Fixed-Time Playing-Strength Match Harness.

Executes controlled, colour-balanced, paired matches between:
- Baseline: Janus v0.27 (commit 851afc7)
- Candidate: Janus v0.30 (commit 05de411)
under fixed movetime budgets (e.g. 1000ms, 500ms, 250ms).
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

    cand_depths = []
    base_depths = []
    cand_move_times = []
    base_move_times = []

    for r in rows:
        pair_num = r["pair"]
        if pair_num not in pairs_dict:
            pairs_dict[pair_num] = []
        pairs_dict[pair_num].append(r)

        cand_color = r["candidate_color"]
        result = r["result"]

        if "avg_cand_depth" in r and r["avg_cand_depth"]:
            cand_depths.append(r["avg_cand_depth"])
        if "avg_base_depth" in r and r["avg_base_depth"]:
            base_depths.append(r["avg_base_depth"])
        if "avg_cand_move_time" in r and r["avg_cand_move_time"]:
            cand_move_times.append(r["avg_cand_move_time"])
        if "avg_base_move_time" in r and r["avg_base_move_time"]:
            base_move_times.append(r["avg_base_move_time"])

        if result == "*":
            unfinished += 1
            continue

        c_stat = by_color[cand_color]
        c_stat["games"] += 1

        if result == "1/2-1/2":
            cand_draws += 1
            c_stat["draws"] += 1
            c_stat["score_pts"] += 0.5
        elif (result == "1-0" and cand_color == "white") or (result == "0-1" and cand_color == "black"):
            cand_wins += 1
            c_stat["wins"] += 1
            c_stat["score_pts"] += 1.0
        else:
            cand_losses += 1
            c_stat["losses"] += 1

    completed = cand_wins + cand_draws + cand_losses
    points = cand_wins + 0.5 * cand_draws
    score_pct = (points / completed * 100.0) if completed > 0 else 0.0

    # Calculate standard error and 95% Wald CI for score percentage
    score_se = 0.0
    score_ci_95 = [0.0, 0.0]
    if completed > 1:
        p = points / completed
        var = (cand_wins * (1.0 - p) ** 2 + cand_draws * (0.5 - p) ** 2 + cand_losses * (0.0 - p) ** 2) / (completed - 1)
        se = math.sqrt(var / completed)
        score_se = round(se * 100.0, 2)
        score_ci_95 = [
            max(0.0, round((p - 1.96 * se) * 100.0, 2)),
            min(100.0, round((p + 1.96 * se) * 100.0, 2)),
        ]

    # Relative Elo estimate (descriptive)
    delta_elo = None
    if completed > 0 and 0 < points < completed:
        p = points / completed
        delta_elo = round(-400.0 * math.log10((1.0 / p) - 1.0), 1)

    # Opening-pair analysis (accounting for colour reversal)
    pairs_completed = 0
    pairs_won = 0
    pairs_drawn = 0
    pairs_lost = 0
    pair_diffs: list[float] = []

    for p_num, p_games in pairs_dict.items():
        if len(p_games) == 2 and p_games[0]["result"] != "*" and p_games[1]["result"] != "*":
            pairs_completed += 1
            # Calculate candidate net points in this pair:
            g1_pts = p_games[0]["candidate_score"]
            g2_pts = p_games[1]["candidate_score"]
            pair_cand_pts = g1_pts + g2_pts  # out of 2.0
            diff = pair_cand_pts - 1.0  # +1.0 = swept pair, 0.0 = tied, -1.0 = lost pair
            pair_diffs.append(diff)
            if pair_cand_pts > 1.0:
                pairs_won += 1
            elif pair_cand_pts == 1.0:
                pairs_drawn += 1
            else:
                pairs_lost += 1

    # Pair-level bootstrap 95% CI on score
    pair_ci_95 = None
    if pairs_completed >= 4:
        rng = random.Random(42)
        boot_means = []
        for _ in range(2000):
            sample = [rng.choice(pair_diffs) for _ in range(pairs_completed)]
            # mean diff in [-1, +1] -> mean score fraction = (mean_diff + 1) / 2
            boot_score_pct = (sum(sample) / len(sample) + 1.0) / 2.0 * 100.0
            boot_means.append(boot_score_pct)
        boot_means.sort()
        pair_ci_95 = [round(boot_means[50], 2), round(boot_means[1950], 2)]

    return {
        "games_total": len(rows),
        "completed_games": completed,
        "unfinished_games": unfinished,
        "candidate_wins": cand_wins,
        "draws": cand_draws,
        "candidate_losses": cand_losses,
        "candidate_points": points,
        "candidate_score_pct": round(score_pct, 2),
        "score_se_pct": score_se,
        "score_ci_95_wald": score_ci_95,
        "delta_elo": delta_elo,
        "pairs_total": len(pairs_dict),
        "pairs_completed": pairs_completed,
        "pairs_won": pairs_won,
        "pairs_drawn": pairs_drawn,
        "pairs_lost": pairs_lost,
        "pair_bootstrap_ci_95": pair_ci_95,
        "by_color": {
            "white": {
                **by_color["white"],
                "score_pct": round(by_color["white"]["score_pts"] / by_color["white"]["games"] * 100.0, 2)
                if by_color["white"]["games"] > 0 else 0.0,
            },
            "black": {
                **by_color["black"],
                "score_pct": round(by_color["black"]["score_pts"] / by_color["black"]["games"] * 100.0, 2)
                if by_color["black"]["games"] > 0 else 0.0,
            },
        },
        "search_stats": {
            "candidate_avg_depth": round(sum(cand_depths) / len(cand_depths), 2) if cand_depths else None,
            "baseline_avg_depth": round(sum(base_depths) / len(base_depths), 2) if base_depths else None,
            "candidate_avg_move_time_s": round(sum(cand_move_times) / len(cand_move_times), 4) if cand_move_times else None,
            "baseline_avg_move_time_s": round(sum(base_move_times) / len(base_move_times), 4) if base_move_times else None,
        },
    }


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

    white_name = "Janus-v0.30" if cand_color == chess.WHITE else "Janus-v0.27"
    black_name = "Janus-v0.27" if cand_color == chess.WHITE else "Janus-v0.30"

    game.headers["Event"] = "Project Janus v0.32 Playing-Strength Match"
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
        curr_name = "Janus-v0.30" if is_cand_turn else "Janus-v0.27"

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
                "engine": curr_name,
                "move": res.move.uci(),
                "time_s": round(elapsed_move, 4),
                "depth": depth_reached,
                "nodes": nodes_searched,
                "score": str(info.get("score")),
            })

            node = node.add_variation(res.move)
            board.push(res.move)

        except Exception as exc:
            result_string = "0-1" if board.turn == chess.WHITE else "1-0"
            termination_reason = f"crash/timeout by {curr_name}: {exc}"
            break

    if termination_reason is None:
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result_string = outcome.result()
            termination_reason = outcome.termination.name.lower().replace("_", " ")
        elif board.ply() >= max_plies:
            result_string = "1/2-1/2"
            termination_reason = "move limit"
        else:
            result_string = "*"
            termination_reason = "unfinished"

    game.headers["Result"] = result_string
    game.headers["Termination"] = termination_reason

    # Calculate candidate score
    cand_score = 0.5
    if result_string == "1-0":
        cand_score = 1.0 if cand_color == chess.WHITE else 0.0
    elif result_string == "0-1":
        cand_score = 0.0 if cand_color == chess.WHITE else 1.0

    duration = round(time.monotonic() - game_start, 3)

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
        "move_log": move_log,
    }

    return game, row


def write_reports(
    json_path: Path,
    csv_path: Path,
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    elapsed: float,
) -> None:
    summary = summarize_match(rows)
    report = {
        "metadata": metadata,
        "summary": summary,
        "elapsed_seconds": round(elapsed, 3),
        "games": rows,
    }
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if rows:
        fieldnames = [
            "game", "pair", "opening_id", "opening_name", "candidate_color",
            "white", "black", "result", "candidate_score", "termination",
            "plies", "duration_seconds", "movetime_ms", "avg_cand_depth",
            "avg_base_depth", "avg_cand_move_time", "avg_base_move_time",
            "avg_cand_nodes", "avg_base_nodes", "start_fen",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def run_match(
    games: int = 4,
    movetime_ms: int = 1000,
    max_plies: int = 200,
    seed: int = 42,
    out_dir: Path = ROOT / "analysis" / "v0.32" / "match",
    match_name: str = "v032_match",
    resume: bool = True,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{match_name}.json"
    csv_path = out_dir / f"{match_name}.csv"
    pgn_path = out_dir / f"{match_name}.pgn"

    base_dir = os.path.abspath(".worktree_v027")
    cand_dir = os.path.abspath(".")

    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"v0.27 worktree not found at {base_dir}")

    pairs_count = games // 2
    openings = load_openings(ROOT / "benchmarks" / "openings.json", count=pairs_count, seed=seed)

    rows: list[dict[str, Any]] = []
    start_index = 0

    if resume and json_path.is_file():
        try:
            prev = json.loads(json_path.read_text(encoding="utf-8"))
            existing = prev.get("games", [])
            if existing:
                rows = existing
                start_index = len(rows)
                print(f"Resuming match: found {start_index} existing games in {json_path}")
        except Exception as exc:
            print(f"Could not load resume data: {exc}")

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "851afc7",
        "baseline_name": "Janus-v0.27",
        "candidate_commit": "05de411",
        "candidate_name": "Janus-v0.30",
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

    base_cmd = [sys.executable, "-m", "janus.uci", "--name", "Janus-v0.27"]
    cand_cmd = [sys.executable, "-m", "janus.uci", "--name", "Janus-v0.30"]

    print(f"Launching match: {games} games ({pairs_count} pairs) at {movetime_ms}ms movetime...")

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
                # Alternate candidate color: Game 1 of pair = White, Game 2 of pair = Black
                cand_color = chess.WHITE if (i % 2 == 0) else chess.BLACK

                # Clean state before each game
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
                    f"Game {row['game']:03d}/{games:03d} (Pair {row['pair']:02d}): "
                    f"Cand ({row['candidate_color']}) {row['result']} | "
                    f"{row['plies']} plies, {row['duration_seconds']}s | "
                    f"D: Cand {row['avg_cand_depth']} vs Base {row['avg_base_depth']} | "
                    f"Term: {row['termination']}"
                )

    total_elapsed = time.monotonic() - start_time
    write_reports(json_path, csv_path, rows, metadata, total_elapsed)
    summary = summarize_match(rows)

    print("\n" + "=" * 80)
    print("MATCH COMPLETE")
    print(f"Games: {summary['completed_games']}/{summary['games_total']}")
    print(f"Candidate (v0.30) W-D-L: {summary['candidate_wins']}-{summary['draws']}-{summary['candidate_losses']}")
    print(f"Score: {summary['candidate_points']}/{summary['completed_games']} ({summary['candidate_score_pct']}%)")
    if summary.get("delta_elo") is not None:
        print(f"Estimated Delta Elo: {summary['delta_elo']:+0.1f}")
    print(f"Pairs: Won={summary['pairs_won']}, Drawn={summary['pairs_drawn']}, Lost={summary['pairs_lost']}")
    print(f"Average Depth: v0.30={summary['search_stats']['candidate_avg_depth']} vs v0.27={summary['search_stats']['baseline_avg_depth']}")
    print(f"Elapsed: {total_elapsed:.1f}s")
    print("=" * 80)

    return {
        "metadata": metadata,
        "summary": summary,
        "elapsed_seconds": total_elapsed,
        "games": rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Run v0.27 vs v0.30 match")
    parser.add_argument("--games", type=int, default=4, help="Total games (even number)")
    parser.add_argument("--movetime", type=int, default=1000, help="Movetime per move in ms")
    parser.add_argument("--max-plies", type=int, default=200, help="Max plies per game")
    parser.add_argument("--seed", type=int, default=42, help="Opening randomization seed")
    parser.add_argument("--match-name", default="v032_match", help="Base filename")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume existing match")
    args = parser.parse_args()

    run_match(
        games=args.games,
        movetime_ms=args.movetime,
        max_plies=args.max_plies,
        seed=args.seed,
        match_name=args.match_name,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
