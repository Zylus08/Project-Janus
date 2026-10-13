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
    return {
        "games": len(rows), "completed_games": completed, "unfinished_games": unfinished,
        "janus_wins": wins, "draws": draws, "janus_losses": losses,
        "janus_score_points": wins + 0.5 * draws,
        "janus_score_percentage": round(100 * (wins + 0.5 * draws) / completed, 2) if completed else None,
        "by_color": by_color,
    }

def play_one_game(janus, stockfish, game_number: int, janus_color: chess.Color,
                  depth: int, max_plies: int, start_fen: str | None = None,
                  opening_id: str = "startpos", pair_number: int = 1):
    board = chess.Board(start_fen) if start_fen else chess.Board()
    game = chess.pgn.Game()
    if start_fen and start_fen != chess.STARTING_FEN:
        game.setup(board)
    game.headers["Event"] = "Project Janus vs Stockfish controlled match"
    game.headers["Site"] = "Local"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_number)
    game.headers["White"] = "Janus" if janus_color == chess.WHITE else "Stockfish"
    game.headers["Black"] = "Stockfish" if janus_color == chess.WHITE else "Janus"
    game.headers["TimeControl"] = f"depth {depth}"
    game.headers["Opening"] = opening_id
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
        "game": game_number, "pair": pair_number, "opening_id": opening_id,
        "janus_color": "white" if janus_color == chess.WHITE else "black",
        "white": game.headers["White"], "black": game.headers["Black"],
        "result": result_string, "termination": game.headers["Termination"],
        "plies": board.ply(), "depth": depth, "start_fen": start_fen or chess.STARTING_FEN,
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
        fieldnames = ["game", "pair", "opening_id", "janus_color", "white", "black",
                      "result", "termination", "plies", "depth", "start_fen"]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stockfish", required=True, help="Full path to stockfish.exe")
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

    janus_command = [sys.executable, "-m", "janus.uci"]
    stockfish_command = [args.stockfish]
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pgn_path = args.out / f"janus-stockfish-{stamp}.pgn"
    csv_path = args.out / f"janus-stockfish-{stamp}.csv"
    json_path = args.out / f"janus-stockfish-{stamp}.json"
    rows = []

    pairs_count = args.games // 2
    openings = load_openings(args.openings, count=pairs_count, seed=args.seed)

    metadata = {
        "janus_command": janus_command, "stockfish_command": stockfish_command,
        "stockfish_threads": args.stockfish_threads, "stockfish_hash_mb": args.stockfish_hash,
        "stockfish_skill": args.stockfish_skill, "stockfish_elo": args.stockfish_elo,
        "depth_each_move": args.depth, "max_plies_per_game": args.max_plies,
        "openings_path": str(args.openings) if args.openings else None,
        "seed": args.seed, "pairs_count": pairs_count,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "method": "paired opening positions with alternating colours; fixed depth per move",
    }
    start = time.monotonic()
    match_failed = False
    try:
        with (
            chess.engine.SimpleEngine.popen_uci(janus_command, cwd=str(ROOT)) as janus,
            chess.engine.SimpleEngine.popen_uci(stockfish_command, cwd=str(ROOT)) as stockfish,
        ):
            config: dict[str, Any] = {}
            if "Threads" in stockfish.options: config["Threads"] = args.stockfish_threads
            if "Hash" in stockfish.options: config["Hash"] = args.stockfish_hash
            if args.stockfish_skill is not None and "Skill Level" in stockfish.options:
                config["Skill Level"] = args.stockfish_skill
            if args.stockfish_elo is not None:
                if "UCI_LimitStrength" in stockfish.options: config["UCI_LimitStrength"] = True
                if "UCI_Elo" in stockfish.options: config["UCI_Elo"] = args.stockfish_elo
            if config: stockfish.configure(config)

            with pgn_path.open("w", encoding="utf-8") as pgn_file:
                for i in range(args.games):
                    pair_index = i // 2
                    opening = openings[pair_index]
                    color = chess.WHITE if i % 2 == 0 else chess.BLACK
                    game, row = play_one_game(
                        janus, stockfish, i + 1, color, args.depth, args.max_plies,
                        start_fen=opening.get("fen"), opening_id=opening.get("id", "startpos"),
                        pair_number=pair_index + 1
                    )
                    pgn_file.write(str(game) + "\n\n")
                    pgn_file.flush()
                    rows.append(row)
                    print(f"Game {row['game']} (Pair {row['pair']}, {row['opening_id']}): "
                          f"Janus {row['janus_color']}, {row['result']}, "
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
