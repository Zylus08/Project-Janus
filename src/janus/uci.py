"""UCI interface for Project Janus with interruptible background search."""
from __future__ import annotations

import argparse
import sys
import threading
import chess

from .search import JanusSearch, MATE_SCORE, MATE_THRESHOLD


def _score_to_uci(score: int) -> str:
    """Convert internal centipawn/mate-distance score to UCI notation."""
    if score >= MATE_THRESHOLD:
        plies = MATE_SCORE - score
        moves = max(1, (plies + 1) // 2)
        return f"mate {moves}"
    if score <= -MATE_THRESHOLD:
        plies = MATE_SCORE + score
        moves = max(1, (plies + 1) // 2)
        return f"mate -{moves}"
    return f"cp {score}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Janus UCI Engine")
    parser.add_argument("--name", type=str, default="Janus 0.2.3")
    parser.add_argument("--see", action="store_true", help="Enable both SEE ordering and SEE pruning")
    parser.add_argument("--see-ordering", action="store_true", help="Enable SEE capture ordering")
    parser.add_argument("--see-pruning", action="store_true", help="Enable SEE quiescence pruning")
    parser.add_argument("--check-extensions", type=str, default="disabled",
                        choices=["disabled", "single_reply", "bounded_all_checks"])
    parser.add_argument("--tt-policy", type=str, default="always_replace",
                        choices=["always_replace", "depth_preferred", "two_tier"])
    parser.add_argument("--tt-max-entries", type=int, default=200_000)
    args = parser.parse_args()

    engine_name = args.name
    see_ordering = args.see or args.see_ordering
    see_pruning = args.see or args.see_pruning

    board = chess.Board()
    engine = JanusSearch(
        tt_max_entries=args.tt_max_entries,
        enable_see_ordering=see_ordering,
        enable_see_pruning=see_pruning,
        check_extension_policy=args.check_extensions,
        tt_replacement_policy=args.tt_policy,
    )
    search_thread: threading.Thread | None = None
    stop_event: threading.Event | None = None
    output_lock = threading.Lock()

    def emit(message: str) -> None:
        with output_lock:
            print(message, flush=True)

    def stop_search() -> None:
        nonlocal search_thread, stop_event
        if stop_event is not None:
            stop_event.set()
        if search_thread is not None and search_thread.is_alive():
            search_thread.join()
        search_thread = None
        stop_event = None

    def start_search(position: chess.Board, depth: int, time_limit: float | None) -> None:
        nonlocal search_thread, stop_event
        stop_search()
        search_board = position.copy(stack=True)
        local_stop = threading.Event()
        stop_event = local_stop

        def worker() -> None:
            result = engine.search(
                search_board,
                max_depth=depth,
                time_limit=time_limit,
                stop_event=local_stop,
            )
            pv_text = " ".join(move.uci() for move in result.pv)
            emit(
                f"info depth {result.depth} score {_score_to_uci(result.score)} "
                f"nodes {result.nodes} time {int(result.elapsed * 1000)} pv {pv_text}".rstrip()
            )
            emit(f"bestmove {result.best_move.uci() if result.best_move else '0000'}")

        search_thread = threading.Thread(target=worker, daemon=True)
        search_thread.start()

    emit("info string Project Janus baseline starting")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        command = parts[0]

        if command == "uci":
            emit(f"id name {engine_name}")
            emit("id author Project Janus")
            emit("option name Hash type spin default 16 min 1 max 1024")
            emit(f"option name SEE_Ordering type check default {'true' if engine.enable_see_ordering else 'false'}")
            emit(f"option name SEE_Pruning type check default {'true' if engine.enable_see_pruning else 'false'}")
            emit(f"option name CheckExtensions type combo default {engine.check_extension_policy} var disabled var single_reply var bounded_all_checks")
            emit(f"option name TT_Policy type combo default {engine.tt_replacement_policy} var always_replace var depth_preferred var two_tier")
            emit("uciok")

        elif command == "setoption":
            try:
                name_idx = parts.index("name") + 1
                if "value" in parts:
                    val_idx = parts.index("value")
                    opt_name = " ".join(parts[name_idx:val_idx]).lower()
                    opt_val = " ".join(parts[val_idx + 1:])
                else:
                    opt_name = " ".join(parts[name_idx:]).lower()
                    opt_val = ""

                if opt_name in ("see_ordering", "see ordering"):
                    engine.enable_see_ordering = (opt_val.lower() == "true")
                elif opt_name in ("see_pruning", "see pruning"):
                    engine.enable_see_pruning = (opt_val.lower() == "true")
                elif opt_name == "see":
                    val_bool = (opt_val.lower() == "true")
                    engine.enable_see_ordering = val_bool
                    engine.enable_see_pruning = val_bool
                elif opt_name in ("checkextensions", "check extensions"):
                    if opt_val.lower() in ("disabled", "single_reply", "bounded_all_checks"):
                        engine.check_extension_policy = opt_val.lower()
                elif opt_name in ("tt_policy", "tt policy"):
                    if opt_val.lower() in ("always_replace", "depth_preferred", "two_tier"):
                        engine.tt_replacement_policy = opt_val.lower()
                elif opt_name == "hash":
                    try:
                        mb = max(1, int(opt_val))
                        engine.tt_max_entries = mb * 16384
                    except ValueError:
                        pass
            except (ValueError, IndexError):
                pass

        elif command == "isready":
            emit("readyok")

        elif command == "ucinewgame":
            stop_search()
            board = chess.Board()
            engine.tt.clear()
            engine.killers = [[None, None] for _ in range(engine.max_killers_ply)]
            engine.history = [[0] * 64 for _ in range(64)]

        elif command == "position":
            stop_search()
            try:
                if len(parts) >= 2 and parts[1] == "startpos":
                    board = chess.Board()
                    move_start = 2
                elif len(parts) >= 2 and parts[1] == "fen":
                    try:
                        move_start = parts.index("moves", 2)
                        fen_parts = parts[2:move_start]
                    except ValueError:
                        fen_parts = parts[2:]
                        move_start = len(parts)
                    board = chess.Board(" ".join(fen_parts))
                else:
                    emit("info string unsupported position command")
                    continue

                if move_start < len(parts) and parts[move_start] == "moves":
                    for uci_move in parts[move_start + 1:]:
                        board.push_uci(uci_move)
            except (ValueError, IndexError) as exc:
                emit(f"info string invalid position: {exc}")

        elif command == "go":
            depth = 5
            time_limit = None
            if "depth" in parts:
                try:
                    depth = max(1, int(parts[parts.index("depth") + 1]))
                except (ValueError, IndexError):
                    depth = 5
            if "movetime" in parts:
                try:
                    time_limit = max(1, int(parts[parts.index("movetime") + 1])) / 1000.0
                    depth = 64
                except (ValueError, IndexError):
                    time_limit = 1.0
                    depth = 64
            start_search(board, depth, time_limit)

        elif command == "stop":
            stop_search()

        elif command == "quit":
            stop_search()
            sys.exit(0)

        elif command == "debug":
            continue


if __name__ == "__main__":
    main()
