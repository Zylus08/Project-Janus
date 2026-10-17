"""Run controlled Janus-vs-Stockfish games and save PGN/CSV/JSON reports."""
from __future__ import annotations
import argparse, csv, json, platform, random, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

def load_openings(openings_path: Path | None, count: int, seed: int = 42) -> list[dict[str, Any]]:
    """Load and deterministically select opening positions for paired matches."""
    if openings_path and openings_path.is_file():
        raw = json.loads(openings_path.read_text(encoding="utf-8"))
        if not raw:
            return [{"id": "startpos", "name": "Standard startpos", "fen": chess.STARTING_FEN}] * count
        rng = random.Random(seed)
        indices = list(range(len(raw)))
        rng.shuffle(indices)
        if count <= len(raw):
            return [raw[i] for i in indices[:count]]
        # If more pairs requested than available openings, cycle deterministically
        selected = [raw[i] for i in indices]
        while len(selected) < count:
            selected.extend(raw)
        return selected[:count]
    return [{"id": "startpos", "name": "Standard startpos", "fen": chess.STARTING_FEN}] * count

def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    wins = draws = losses = unfinished = 0
    by_color = {
        "white": {"wins": 0, "draws": 0, "losses": 0, "unfinished": 0, "games": 0},
        "black": {"wins": 0, "draws": 0, "losses": 0, "unfinished": 0, "games": 0},
    }
    for row in rows:
        result, color = row["result"], row["janus_color"]
        c_stats = by_color.setdefault(color, {"wins": 0, "draws": 0, "losses": 0, "unfinished": 0, "games": 0})
        c_stats["games"] += 1
        if result == "*":
            unfinished += 1
            c_stats["unfinished"] += 1
        elif result == "1/2-1/2":
            draws += 1
            c_stats["draws"] += 1
        elif (result == "1-0" and color == "white") or (result == "0-1" and color == "black"):
            wins += 1
            c_stats["wins"] += 1
        else:
            losses += 1
            c_stats["losses"] += 1
    completed = wins + draws + losses
    points = wins + 0.5 * draws
    score_pct = round(100 * points / completed, 2) if completed else None

    # Calculate standard error and 95% confidence interval for score percentage
    score_se = None
    score_ci_95 = None
    if completed > 1 and score_pct is not None:
        import math
        p = points / completed
        # Variance of chess game outcomes: sum((x_i - p)^2) / (N - 1)
        var = (wins * (1.0 - p) ** 2 + draws * (0.5 - p) ** 2 + losses * (0.0 - p) ** 2) / (completed - 1)
        se = math.sqrt(var / completed)
        score_se = round(se, 4)
        ci_low = max(0.0, round(100 * (p - 1.96 * se), 2))
        ci_high = min(100.0, round(100 * (p + 1.96 * se), 2))
        score_ci_95 = [ci_low, ci_high]

    return {
        "games": len(rows), "completed_games": completed, "unfinished_games": unfinished,
        "janus_wins": wins, "draws": draws, "janus_losses": losses,
        "janus_score_points": points,
        "janus_score_percentage": score_pct,
        "score_se": score_se,
        "score_ci_95": score_ci_95,
        "by_color": by_color,
    }

def play_one_game(engine1, engine2, game_number: int, engine1_color: chess.Color,
                  depth: int, max_plies: int, start_fen: str | None = None,
                  opening_id: str = "startpos", pair_number: int = 1,
                  engine1_name: str = "Janus", engine2_name: str = "Stockfish"):
    game_start = time.monotonic()
    board = chess.Board(start_fen) if start_fen else chess.Board()
    game = chess.pgn.Game()
    if start_fen and start_fen != chess.STARTING_FEN:
        game.setup(board)
    game.headers["Event"] = f"{engine1_name} vs {engine2_name} controlled match"
    game.headers["Site"] = "Local"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    white_name = engine1_name if engine1_color == chess.WHITE else engine2_name
    black_name = engine2_name if engine1_color == chess.WHITE else engine1_name
    game.headers["White"] = white_name
    game.headers["Black"] = black_name
    game.headers["TimeControl"] = f"depth {depth}"
    game.headers["Opening"] = opening_id
    node = game

    result_string = None
    termination_reason = None

    for _ in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break
        curr_is_engine1 = (board.turn == engine1_color)
        current_engine = engine1 if curr_is_engine1 else engine2
        curr_name = engine1_name if curr_is_engine1 else engine2_name

        try:
            result = current_engine.play(board, chess.engine.Limit(depth=depth), game=game_number)
            if result.move is None or result.move not in board.legal_moves:
                result_string = "0-1" if board.turn == chess.WHITE else "1-0"
                termination_reason = f"illegal move by {curr_name}"
                break
            node = node.add_variation(result.move)
            board.push(result.move)
        except Exception as exc:
            result_string = "0-1" if board.turn == chess.WHITE else "1-0"
            termination_reason = f"crash/error by {curr_name}: {exc}"
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

    game.headers["Termination"] = termination_reason
    game.headers["Result"] = result_string
    game_duration = round(time.monotonic() - game_start, 3)
    row = {
        "game": game_number, "pair": pair_number, "opening_id": opening_id,
        "janus_color": "white" if engine1_color == chess.WHITE else "black",
        "engine1_color": "white" if engine1_color == chess.WHITE else "black",
        "white": white_name, "black": black_name,
        "result": result_string, "termination": termination_reason,
        "plies": board.ply(), "depth": depth, "duration_seconds": game_duration,
        "start_fen": start_fen or chess.STARTING_FEN,
    }
    return game, row

def write_reports(json_path: Path, csv_path: Path, rows: list[dict[str, Any]],
                  metadata: dict[str, Any], elapsed: float) -> None:
    summary = summarize(rows)
    report = {
        "metadata": metadata,
        "summary": summary,
        "elapsed_seconds": round(elapsed, 3),
        "games": rows,
    }
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        fieldnames = ["game", "pair", "opening_id", "janus_color", "engine1_color", "white", "black",
                      "result", "termination", "plies", "depth", "duration_seconds", "start_fen"]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stockfish", default=None, help="Full path to stockfish.exe")
    parser.add_argument("--candidate-see", action="store_true",
                        help="Run Janus baseline (SEE OFF) vs Janus candidate (SEE ON)")
    parser.add_argument("--engine1-name", default=None, help="Name of Engine 1 (Janus perspective)")
    parser.add_argument("--engine1-cmd", nargs="+", default=None, help="Command line for Engine 1")
    parser.add_argument("--engine2-name", default=None, help="Name of Engine 2")
    parser.add_argument("--engine2-cmd", nargs="+", default=None, help="Command line for Engine 2")
    parser.add_argument("--games", type=int, default=2, help="Total number of games (even number for paired matches)")
    parser.add_argument("--depth", type=int, default=3, help="Fixed search depth for both engines")
    parser.add_argument("--max-plies", type=int, default=240, help="Hard cap per game")
    parser.add_argument("--openings", type=Path, default=ROOT / "benchmarks" / "openings.json",
                        help="Path to opening positions JSON file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic opening sampling")
    parser.add_argument("--stockfish-threads", type=int, default=1, help="Stockfish UCI Threads option")
    parser.add_argument("--stockfish-hash", type=int, default=128, help="Stockfish UCI Hash (MB) option")
    parser.add_argument("--stockfish-skill", type=int, default=None, help="Stockfish UCI Skill Level option (0-20)")
    parser.add_argument("--stockfish-elo", type=int, default=None, help="Stockfish UCI_Elo limit (1320-3190)")
    parser.add_argument("--out", type=Path, default=ROOT / "match-results")
    args = parser.parse_args()

    if args.games < 2: parser.error("--games must be >= 2")
    if args.games % 2 != 0: parser.error("--games must be an even number for paired opening evaluation")
    if args.depth < 1: parser.error("--depth must be >= 1")
    if args.max_plies < 1: parser.error("--max-plies must be >= 1")

    # Determine engine commands and display names
    if args.candidate_see:
        engine1_name = args.engine1_name or "Janus-Baseline"
        engine1_command = args.engine1_cmd or [sys.executable, "-m", "janus.uci", "--name", engine1_name]
        engine2_name = args.engine2_name or "Janus-SEE"
        engine2_command = args.engine2_cmd or [sys.executable, "-m", "janus.uci", "--see", "--name", engine2_name]
        is_stockfish_e2 = False
    elif args.stockfish:
        engine1_name = args.engine1_name or "Janus"
        engine1_command = args.engine1_cmd or [sys.executable, "-m", "janus.uci"]
        engine2_name = args.engine2_name or "Stockfish"
        engine2_command = [args.stockfish]
        is_stockfish_e2 = True
    elif args.engine2_cmd:
        engine1_name = args.engine1_name or "Janus-1"
        engine1_command = args.engine1_cmd or [sys.executable, "-m", "janus.uci"]
        engine2_name = args.engine2_name or "Janus-2"
        engine2_command = args.engine2_cmd
        is_stockfish_e2 = False
    else:
        parser.error("Must provide --stockfish, --candidate-see, or custom --engine2-cmd")

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = "janus-see" if args.candidate_see else f"{engine1_name.lower()}-{engine2_name.lower()}"
    pgn_path = args.out / f"{prefix}-{stamp}.pgn"
    csv_path = args.out / f"{prefix}-{stamp}.csv"
    json_path = args.out / f"{prefix}-{stamp}.json"
    rows: list[dict[str, Any]] = []

    pairs_count = args.games // 2
    openings = load_openings(args.openings, count=pairs_count, seed=args.seed)

    metadata: dict[str, Any] = {
        "engine1_name": engine1_name,
        "engine1_command": engine1_command,
        "engine2_name": engine2_name,
        "engine2_command": engine2_command,
        "janus_command": engine1_command,
        "stockfish_command": engine2_command if is_stockfish_e2 else None,
        "stockfish_threads": args.stockfish_threads if is_stockfish_e2 else None,
        "stockfish_hash_mb": args.stockfish_hash if is_stockfish_e2 else None,
        "stockfish_skill": args.stockfish_skill if is_stockfish_e2 else None,
        "stockfish_elo": args.stockfish_elo if is_stockfish_e2 else None,
        "depth_each_move": args.depth,
        "max_plies_per_game": args.max_plies,
        "openings_path": str(args.openings) if args.openings else None,
        "seed": args.seed,
        "pairs_count": pairs_count,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "method": "paired opening positions with alternating colours; fixed depth per move",
    }
    start = time.monotonic()
    match_failed = False

    try:
        with (
            chess.engine.SimpleEngine.popen_uci(engine1_command, cwd=str(ROOT)) as e1,
            chess.engine.SimpleEngine.popen_uci(engine2_command, cwd=str(ROOT)) as e2,
        ):
            if is_stockfish_e2:
                config: dict[str, Any] = {}
                if "Threads" in e2.options: config["Threads"] = args.stockfish_threads
                if "Hash" in e2.options: config["Hash"] = args.stockfish_hash
                if args.stockfish_skill is not None and "Skill Level" in e2.options:
                    config["Skill Level"] = args.stockfish_skill
                if args.stockfish_elo is not None:
                    if "UCI_LimitStrength" in e2.options: config["UCI_LimitStrength"] = True
                    if "UCI_Elo" in e2.options: config["UCI_Elo"] = args.stockfish_elo
                if config: e2.configure(config)

            with pgn_path.open("w", encoding="utf-8") as pgn_file:
                for i in range(args.games):
                    pair_index = i // 2
                    opening = openings[pair_index]
                    color = chess.WHITE if i % 2 == 0 else chess.BLACK
                    game, row = play_one_game(
                        e1, e2, i + 1, color, args.depth, args.max_plies,
                        start_fen=opening.get("fen"), opening_id=opening.get("id", "startpos"),
                        pair_number=pair_index + 1,
                        engine1_name=engine1_name, engine2_name=engine2_name,
                    )
                    pgn_file.write(str(game) + "\n\n")
                    pgn_file.flush()
                    rows.append(row)
                    elapsed_so_far = time.monotonic() - start
                    # Save progress after every game to ensure partial persistence
                    write_reports(json_path, csv_path, rows, metadata, elapsed_so_far)

                    print(f"Game {row['game']} (Pair {row['pair']}, {row['opening_id']}): "
                          f"{engine1_name} ({row['janus_color']}) {row['result']} {engine2_name}, "
                          f"{row['plies']} plies, {row['duration_seconds']}s, termination={row['termination']}")
    except (OSError, chess.engine.EngineError, RuntimeError) as exc:
        print(f"Match failed: {exc}", file=sys.stderr)
        match_failed = True

    elapsed = time.monotonic() - start
    write_reports(json_path, csv_path, rows, metadata, elapsed)
    summary = summarize(rows)

    print(f"\nMatch summary ({engine1_name} perspective)")
    print(f"Games: {summary['games']} (completed: {summary['completed_games']})")
    print(f"W-D-L: {summary['janus_wins']}-{summary['draws']}-{summary['janus_losses']}")
    if "by_color" in summary:
        w = summary["by_color"].get("white", {})
        b = summary["by_color"].get("black", {})
        print(f"  As White: {w.get('wins', 0)}W-{w.get('draws', 0)}D-{w.get('losses', 0)}L")
        print(f"  As Black: {b.get('wins', 0)}W-{b.get('draws', 0)}D-{b.get('losses', 0)}L")
    if summary["completed_games"]:
        score_line = f"Score: {summary['janus_score_points']}/{summary['completed_games']} ({summary['janus_score_percentage']}%)"
        if summary.get("score_ci_95"):
            score_line += f" [95% CI: {summary['score_ci_95'][0]}% - {summary['score_ci_95'][1]}%]"
        print(score_line)
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"PGN:  {pgn_path}\nCSV:  {csv_path}\nJSON: {json_path}")
    return 2 if match_failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
