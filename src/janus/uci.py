"""UCI interface for Project Janus with interruptible background search."""
from __future__ import annotations

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
    board = chess.Board()
    engine = JanusSearch()
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
            emit("id name Janus 0.2.3")
            emit("id author Project Janus")
            emit("uciok")

        elif command == "isready":
            emit("readyok")

        elif command == "ucinewgame":
            stop_search()
            board = chess.Board()
            engine.tt.clear()

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
            break

        elif command == "debug":
            continue


if __name__ == "__main__":
    main()
