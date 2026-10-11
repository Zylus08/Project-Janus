"""Minimal synchronous UCI interface for Project Janus."""
from __future__ import annotations

import sys
import chess

from .search import JanusSearch


def _score_to_uci(score: int) -> str:
    # Mate scores are left as centipawns in this starter version. A later
    # protocol-hardening pass will convert forced mates to UCI mate scores.
    return f"cp {score}"


def main() -> None:
    board = chess.Board()
    engine = JanusSearch()
    print("info string Project Janus baseline starting", flush=True)

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        command = parts[0]

        if command == "uci":
            print("id name Janus 0.1.0", flush=True)
            print("id author Project Janus", flush=True)
            print("uciok", flush=True)

        elif command == "isready":
            print("readyok", flush=True)

        elif command == "ucinewgame":
            board = chess.Board()
            engine.tt.clear()

        elif command == "position":
            try:
                if len(parts) >= 2 and parts[1] == "startpos":
                    board = chess.Board()
                    move_start = 2
                elif len(parts) >= 2 and parts[1] == "fen":
                    # FEN consists of six fields, followed optionally by "moves".
                    fen_start = 2
                    try:
                        move_start = parts.index("moves", fen_start)
                        fen_parts = parts[fen_start:move_start]
                    except ValueError:
                        fen_parts = parts[fen_start:]
                        move_start = len(parts)
                    board = chess.Board(" ".join(fen_parts))
                else:
                    print("info string unsupported position command", flush=True)
                    continue

                if move_start < len(parts) and parts[move_start] == "moves":
                    for uci_move in parts[move_start + 1:]:
                        board.push_uci(uci_move)
            except (ValueError, IndexError) as exc:
                print(f"info string invalid position: {exc}", flush=True)

        elif command == "go":
            depth = 5
            time_limit = None
            if "depth" in parts:
                try:
                    depth = max(1, int(parts[parts.index("depth") + 1]))
                except (ValueError, IndexError):
                    pass
            if "movetime" in parts:
                try:
                    time_limit = max(1, int(parts[parts.index("movetime") + 1])) / 1000.0
                    depth = 64
                except (ValueError, IndexError):
                    pass

            result = engine.search(board, max_depth=depth, time_limit=time_limit)
            pv_text = " ".join(move.uci() for move in result.pv)
            print(
                f"info depth {result.depth} score {_score_to_uci(result.score)} "
                f"nodes {result.nodes} time {int(result.elapsed * 1000)} pv {pv_text}".rstrip(),
                flush=True,
            )
            print(f"bestmove {result.best_move.uci() if result.best_move else '0000'}", flush=True)

        elif command == "stop":
            # Search is synchronous; stop is handled in a future UCI-hardening pass.
            print("info string stop received; synchronous search cannot be interrupted yet", flush=True)

        elif command == "quit":
            break

        elif command == "debug":
            continue

        else:
            # Ignore unknown UCI commands for forward compatibility.
            continue


if __name__ == "__main__":
    main()
