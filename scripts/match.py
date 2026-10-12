"""Run controlled Janus-vs-Stockfish games and save PGN/CSV/JSON reports."""
from __future__ import annotations
import argparse, csv, json, platform, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

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
    return {
        "games": len(rows), "completed_games": completed, "unfinished_games": unfinished,
        "janus_wins": wins, "draws": draws, "janus_losses": losses,
        "janus_score_points": wins + 0.5 * draws,
        "janus_score_percentage": round(100 * (wins + 0.5 * draws) / completed, 2) if completed else None,
        "by_color": by_color,
    }

def play_one_game(janus, stockfish, game_number: int, janus_color: chess.Color,
                  depth: int, max_plies: int):
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Project Janus vs Stockfish controlled match"
    game.headers["Site"] = "Local"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = "Janus" if janus_color == chess.WHITE else "Stockfish"
    game.headers["Black"] = "Stockfish" if janus_color == chess.WHITE else "Janus"
    game.headers["TimeControl"] = f"depth {depth}"
    node = game
    for _ in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break
        engine = janus if board.turn == janus_color else stockfish
        result = engine.play(board, chess.engine.Limit(depth=depth), game=game_number)
        if result.move is None or result.move not in board.legal_moves:
            who = "Janus" if engine is janus else "Stockfish"
            raise RuntimeError(f"{who} returned no legal move at ply {board.ply()}")
        node = node.add_variation(result.move)
        board.push(result.move)

    outcome = board.outcome(claim_draw=True)
    if outcome is not None:
        result_string = outcome.result()
        game.headers["Termination"] = outcome.termination.name.lower().replace("_", " ")
    elif board.ply() >= max_plies:
        result_string = "1/2-1/2"
        game.headers["Termination"] = "move limit"
    else:
        result_string = "*"
        game.headers["Termination"] = "unfinished"
    game.headers["Result"] = result_string
    row = {
        "game": game_number, "janus_color": "white" if janus_color == chess.WHITE else "black",
        "white": game.headers["White"], "black": game.headers["Black"],
        "result": result_string, "termination": game.headers["Termination"],
        "plies": board.ply(), "depth": depth,
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
        fieldnames = ["game", "janus_color", "white", "black", "result", "termination", "plies", "depth"]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stockfish", required=True, help="Full path to stockfish.exe")
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--depth", type=int, default=3, help="Fixed search depth for both engines")
    parser.add_argument("--max-plies", type=int, default=240, help="Hard cap per game")
    parser.add_argument("--out", type=Path, default=ROOT / "match-results")
    args = parser.parse_args()
    if args.games < 1: parser.error("--games must be >= 1")
    if args.depth < 1: parser.error("--depth must be >= 1")
    if args.max_plies < 1: parser.error("--max-plies must be >= 1")

    janus_command = [sys.executable, "-m", "janus.uci"]
    stockfish_command = [args.stockfish]
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pgn_path = args.out / f"janus-stockfish-{stamp}.pgn"
    csv_path = args.out / f"janus-stockfish-{stamp}.csv"
    json_path = args.out / f"janus-stockfish-{stamp}.json"
    rows = []
    metadata = {
        "janus_command": janus_command, "stockfish_command": stockfish_command,
        "stockfish_threads": 1, "stockfish_hash_mb": 128,
        "depth_each_move": args.depth, "max_plies_per_game": args.max_plies,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "method": "alternating Janus colours; fixed depth per move; one Stockfish thread",
    }
    start = time.monotonic()
    match_failed = False
    try:
        with (
            chess.engine.SimpleEngine.popen_uci(janus_command, cwd=str(ROOT)) as janus,
            chess.engine.SimpleEngine.popen_uci(stockfish_command, cwd=str(ROOT)) as stockfish,
        ):
            config = {}
            if "Threads" in stockfish.options: config["Threads"] = 1
            if "Hash" in stockfish.options: config["Hash"] = 128
            if config: stockfish.configure(config)
            with pgn_path.open("w", encoding="utf-8") as pgn_file:
                for i in range(args.games):
                    color = chess.WHITE if i % 2 == 0 else chess.BLACK
                    game, row = play_one_game(janus, stockfish, i + 1, color, args.depth, args.max_plies)
                    pgn_file.write(str(game) + "\n\n")
                    pgn_file.flush()
                    rows.append(row)
                    print(f"Game {row['game']}: Janus {row['janus_color']}, {row['result']}, "
                          f"{row['plies']} plies, termination={row['termination']}")
    except (OSError, chess.engine.EngineError, RuntimeError) as exc:
        print(f"Match failed: {exc}", file=sys.stderr)
        print("Check executable paths and the Janus UCI smoke test.", file=sys.stderr)
        match_failed = True

    elapsed = time.monotonic() - start
    write_reports(json_path, csv_path, rows, metadata, elapsed)
    summary = summarize(rows)

    print("\nMatch summary (Janus perspective)")
    print(f"Games: {summary['games']} (completed: {summary['completed_games']})")
    print(f"W-D-L: {summary['janus_wins']}-{summary['draws']}-{summary['janus_losses']}")
    if "by_color" in summary:
        w = summary["by_color"].get("white", {})
        b = summary["by_color"].get("black", {})
        print(f"  As White: {w.get('wins', 0)}W-{w.get('draws', 0)}D-{w.get('losses', 0)}L")
        print(f"  As Black: {b.get('wins', 0)}W-{b.get('draws', 0)}D-{b.get('losses', 0)}L")
    if summary["completed_games"]:
        print(f"Score: {summary['janus_score_points']}/{summary['completed_games']} "
              f"({summary['janus_score_percentage']}%)")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"PGN:  {pgn_path}\nCSV:  {csv_path}\nJSON: {json_path}")
    return 2 if match_failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
