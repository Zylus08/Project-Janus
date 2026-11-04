"""Project Janus v0.52 - Corrected Tournament Controller & Adjudication Engine.

Remediates the v0.51.1 audit findings:
1. Eliminates the artificial 150-ply draw horizon.
2. Implements standard FIDE tournament adjudications:
   - Checkmate (Article 1.2)
   - Stalemate (Article 5.2.1)
   - Insufficient Material (Article 5.2.2 / 9.6)
   - Threefold Repetition Claim (Article 9.2)
   - Fivefold Repetition Automatic Draw (Article 9.6.1)
   - 50-Move Rule Claim (Article 9.3)
   - 75-Move Rule Automatic Draw (Article 9.6.2)
3. Emergency Circuit-Breaker: Games are allowed to run up to 300 plies (150 full moves).
   If reached, it is explicitly classified as 'safety_limit_300_plies' and never mislabeled
   as a FIDE draw.
"""

import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import chess
import chess.pgn


class NativeUCIEngineProcess:
    """Manages an external UCI chess engine subprocess with unbuffered I/O."""

    def __init__(self, exe_path: Path, options: Optional[Dict[str, Any]] = None):
        self.exe_path = exe_path
        self.options = options or {}
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\n")
        self.p.stdin.flush()
        # Set options before isready
        for opt_name, opt_val in self.options.items():
            if isinstance(opt_val, bool):
                val_str = "true" if opt_val else "false"
            else:
                val_str = str(opt_val)
            self.p.stdin.write(f"setoption name {opt_name} value {val_str}\n")
        self.p.stdin.write("isready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def set_option(self, name: str, value: Any):
        self.options[name] = value
        val_str = "true" if value is True else ("false" if value is False else str(value))
        self.p.stdin.write(f"setoption name {name} value {val_str}\nisready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def ucinewgame(self):
        self.p.stdin.write("ucinewgame\nisready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def play_move(self, fen: str, wtime_ms: int, btime_ms: int, winc_ms: int, binc_ms: int) -> Tuple[Optional[str], float]:
        t0 = time.perf_counter()
        cmd = f"position fen {fen}\ngo wtime {wtime_ms} btime {btime_ms} winc {winc_ms} binc {binc_ms}\n"
        self.p.stdin.write(cmd)
        self.p.stdin.flush()
        bestmove = None
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) >= 2:
                    bestmove = tokens[1]
                break
        elapsed = time.perf_counter() - t0
        return bestmove, elapsed

    def close(self):
        try:
            if self.p.poll() is None:
                self.p.stdin.write("quit\n")
                self.p.stdin.flush()
                self.p.wait(timeout=2)
            if self.p.stdin and not self.p.stdin.closed:
                self.p.stdin.close()
            if self.p.stdout and not self.p.stdout.closed:
                self.p.stdout.close()
        except Exception:
            self.p.kill()


def adjudicate_board(board: chess.Board, ply_count: int, max_plies: int = 300) -> Tuple[bool, str, str]:
    """Evaluates the board state and returns (is_game_over, result_str, termination_reason).

    Distinguishes exact FIDE rules from emergency safety limits.
    """
    # 1. On-the-board checkmate
    if board.is_checkmate():
        winner = "White" if board.turn == chess.BLACK else "Black"
        result_str = "1-0" if winner == "White" else "0-1"
        return True, result_str, f"checkmate_{winner.lower()}"

    # 2. Stalemate
    if board.is_stalemate():
        return True, "1/2-1/2", "draw_stalemate"

    # 3. Insufficient material
    if board.is_insufficient_material():
        return True, "1/2-1/2", "draw_insufficient_material"

    # 4. Mandatory 75-move rule (FIDE 9.6.2)
    if board.is_seventyfive_moves():
        return True, "1/2-1/2", "draw_seventyfive_moves"

    # 5. Mandatory Fivefold Repetition (FIDE 9.6.1)
    if board.is_fivefold_repetition():
        return True, "1/2-1/2", "draw_fivefold_repetition"

    # 6. Claimable Threefold Repetition (Tournament Controller Policy: automatic adjudication on 3-fold)
    if board.can_claim_threefold_repetition():
        return True, "1/2-1/2", "draw_threefold_repetition"

    # 7. Claimable 50-Move Rule (Tournament Controller Policy: automatic adjudication on 100 halfmoves)
    if board.can_claim_fifty_moves():
        return True, "1/2-1/2", "draw_fifty_moves"

    # 8. Emergency Safety Limit (Non-FIDE Circuit Breaker)
    if ply_count >= max_plies:
        return True, "1/2-1/2", "safety_limit_300_plies"

    return False, "*", "in_progress"


def play_tournament_game(
    opening: Dict[str, Any],
    white_engine: NativeUCIEngineProcess,
    black_engine: NativeUCIEngineProcess,
    white_name: str,
    black_name: str,
    game_num: int,
    base_time_ms: int = 3000,
    inc_ms: int = 100,
    max_plies: int = 300
) -> Dict[str, Any]:
    """Executes a single tournament game under Fischer clocks with rigorous adjudication."""
    fen = opening.get("fen", chess.STARTING_FEN)
    board = chess.Board(fen)

    wtime = float(base_time_ms)
    btime = float(base_time_ms)

    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Project Janus v0.52 Controlled Tournament"
    pgn_game.headers["Site"] = "Local Benchmark Harness"
    pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = str(game_num)
    pgn_game.headers["White"] = white_name
    pgn_game.headers["Black"] = black_name
    pgn_game.headers["TimeControl"] = f"{base_time_ms/1000:.1f}+{inc_ms/1000:.2f}"
    if fen != chess.STARTING_FEN:
        pgn_game.headers["SetUp"] = "1"
        pgn_game.headers["FEN"] = fen

    node = pgn_game
    termination = "unknown"
    result_str = "*"
    moves_history = []

    for ply in range(max_plies):
        # Adjudicate before move
        is_over, res, term = adjudicate_board(board, ply, max_plies)
        if is_over:
            result_str = res
            termination = term
            break

        # Clock check before move
        my_time = wtime if board.turn == chess.WHITE else btime
        if my_time <= 0:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"timeout_{winner.lower()}_wins"
            break

        current_engine = white_engine if board.turn == chess.WHITE else black_engine
        best_uci, elapsed = current_engine.play_move(
            board.fen(), int(wtime), int(btime), inc_ms, inc_ms
        )

        if not best_uci:
            legal_list = list(board.legal_moves)
            best_move = legal_list[0] if legal_list else None
        else:
            try:
                best_move = chess.Move.from_uci(best_uci)
            except Exception:
                legal_list = list(board.legal_moves)
                best_move = legal_list[0] if legal_list else None

        # Illegal move forfeiture
        if not best_move or best_move not in board.legal_moves:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"illegal_move_{winner.lower()}_wins"
            break

        # Update clock
        if board.turn == chess.WHITE:
            wtime = wtime - (elapsed * 1000.0) + inc_ms
        else:
            btime = btime - (elapsed * 1000.0) + inc_ms

        node = node.add_variation(best_move)
        board.push(best_move)
        moves_history.append(best_move.uci())

    # Final post-loop adjudication if not already terminal
    if result_str == "*":
        is_over, res, term = adjudicate_board(board, len(moves_history), max_plies)
        result_str = res if is_over else "1/2-1/2"
        termination = term if is_over else "safety_limit_300_plies"

    pgn_game.headers["Result"] = result_str
    pgn_game.headers["Termination"] = termination

    return {
        "game_number": game_num,
        "opening_id": opening.get("id"),
        "result": result_str,
        "termination": termination,
        "plies": len(moves_history),
        "final_fen": board.fen(),
        "final_halfmove_clock": board.halfmove_clock,
        "pgn": str(pgn_game)
    }

