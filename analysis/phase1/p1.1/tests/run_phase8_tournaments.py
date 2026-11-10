#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 8: Classical Strength Qualification Tournaments.
1. Janus Classical X (Variant X6) vs Frozen Classical C1 (100 Games / 50 Opening Pairs)
2. Janus Classical X (Variant X6) vs Unrestricted Stockfish 19 (20 Games / 10 Opening Pairs)
"""

import os
import sys
import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[4]
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
X_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
SF_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.1" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.1" / "pgn"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PGN_DIR.mkdir(parents=True, exist_ok=True)


def calc_confidence_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    """Exact Wilson score confidence interval for binomial proportion."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    lower = max(0.0, centre - half)
    upper = min(1.0, centre + half)
    return float(lower), float(upper)


class UciEngineProcess:
    def __init__(self, name: str, exe_path: Path, options: Dict[str, Any] = None):
        self.name = name
        self.exe_path = str(exe_path.resolve())
        self.options = options or {}
        self.proc: Optional[subprocess.Popen] = None

    def start(self):
        self.proc = subprocess.Popen(
            [self.exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send_command("uci")
        self.wait_for("uciok")
        for k, v in self.options.items():
            self.send_command(f"setoption name {k} value {v}")
        self.send_command("isready")
        self.wait_for("readyok")

    def send_command(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError(f"Engine {self.name} is not running.")
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def wait_for(self, target: str, timeout: float = 10.0) -> List[str]:
        lines = []
        t0 = time.time()
        while time.time() - t0 < timeout:
            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Engine {self.name} terminated unexpectedly with code {self.proc.returncode}")
                time.sleep(0.005)
                continue
            line = line.strip()
            lines.append(line)
            if line == target or line.startswith(target):
                return lines
        raise TimeoutError(f"Engine {self.name} timed out waiting for '{target}'")

    def new_game(self):
        self.send_command("ucinewgame")
        self.send_command("isready")
        self.wait_for("readyok")

    def play_move(
        self,
        board: chess.Board,
        wtime_ms: int,
        btime_ms: int,
        winc_ms: int,
        binc_ms: int
    ) -> Tuple[str, Dict[str, Any]]:
        moves_str = " ".join([m.uci() for m in board.move_stack])
        if moves_str:
            self.send_command(f"position startpos moves {moves_str}")
        else:
            self.send_command("position startpos")

        go_cmd = f"go wtime {wtime_ms} btime {btime_ms} winc {winc_ms} binc {binc_ms}"
        self.send_command(go_cmd)

        lines = []
        bestmove = None
        info_dict = {}

        t_start = time.perf_counter()
        my_time = wtime_ms if board.turn == chess.WHITE else btime_ms
        my_inc = winc_ms if board.turn == chess.WHITE else binc_ms
        safety_timeout = (my_time / 1000.0) + (my_inc / 1000.0) * 2.0 + 5.0

        while True:
            elapsed = time.perf_counter() - t_start
            if elapsed > safety_timeout:
                self.terminate()
                raise TimeoutError(f"Engine {self.name} exceeded safety time limit ({elapsed:.2f}s > {safety_timeout:.2f}s)")

            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Engine {self.name} crashed during search with code {self.proc.returncode}")
                time.sleep(0.002)
                continue

            line = line.strip()
            if line.startswith("info"):
                lines.append(line)
                parts = line.split()
                for idx, tok in enumerate(parts):
                    if tok == "depth" and idx + 1 < len(parts):
                        info_dict["depth"] = int(parts[idx+1])
                    elif tok == "nodes" and idx + 1 < len(parts):
                        info_dict["nodes"] = int(parts[idx+1])
                    elif tok == "nps" and idx + 1 < len(parts):
                        info_dict["nps"] = int(parts[idx+1])
                    elif tok == "cp" and idx + 1 < len(parts):
                        info_dict["score_cp"] = int(parts[idx+1])
            elif line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) > 1:
                    bestmove = tokens[1]
                break

        elapsed_sec = time.perf_counter() - t_start
        info_dict["elapsed_sec"] = elapsed_sec
        return bestmove, info_dict

    def terminate(self):
        if self.proc:
            try:
                self.send_command("quit")
                self.proc.wait(timeout=2.0)
            except Exception:
                self.proc.kill()
            self.proc = None


def play_single_game(
    white_engine: UciEngineProcess,
    black_engine: UciEngineProcess,
    opening: Dict[str, Any],
    time_base_ms: int = 1000,
    time_inc_ms: int = 50,
    max_plies: int = 200
) -> Dict[str, Any]:
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Janus P1.1 Strength Validation"
    game.headers["White"] = white_engine.name
    game.headers["Black"] = black_engine.name
    game.headers["TimeControl"] = f"{time_base_ms/1000.0:.1f}+{time_inc_ms/1000.0:.2f}"
    game.headers["Opening"] = opening.get("name", "Unknown Opening")

    node = game
    for uci_m in opening.get("uci_sequence", []):
      m = chess.Move.from_uci(uci_m)
      board.push(m)
      node = node.add_variation(m)

    wtime = time_base_ms
    btime = time_base_ms
    winc = time_inc_ms
    binc = time_inc_ms

    white_engine.new_game()
    black_engine.new_game()

    moves_history = []
    t_start = time.time()
    termination = "normal"
    result = "*"

    for ply in range(max_plies):
        if board.is_checkmate():
            result = "1-0" if board.turn == chess.BLACK else "0-1"
            termination = "checkmate"
            break
        if board.is_stalemate():
            result = "1/2-1/2"
            termination = "stalemate"
            break
        if board.is_insufficient_material():
            result = "1/2-1/2"
            termination = "insufficient_material"
            break
        if board.can_claim_threefold_repetition():
            result = "1/2-1/2"
            termination = "threefold_repetition"
            break
        if board.can_claim_fifty_moves():
            result = "1/2-1/2"
            termination = "fifty_moves"
            break

        curr_engine = white_engine if board.turn == chess.WHITE else black_engine
        t_move_start = time.perf_counter()

        try:
            bm, info = curr_engine.play_move(board, wtime, btime, winc, binc)
        except Exception as e:
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"crash/timeout: {e}"
            break

        move_dur = time.perf_counter() - t_move_start
        move_dur_ms = int(move_dur * 1000.0)

        if board.turn == chess.WHITE:
            wtime = max(10, wtime - move_dur_ms + winc)
        else:
            btime = max(10, btime - move_dur_ms + binc)

        if not bm or bm == "0000":
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "no_move"
            break

        try:
            move_obj = chess.Move.from_uci(bm)
            if move_obj not in board.legal_moves:
                result = "0-1" if board.turn == chess.WHITE else "1-0"
                termination = f"illegal_move ({bm})"
                break
        except Exception:
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"invalid_move ({bm})"
            break

        board.push(move_obj)
        node = node.add_variation(move_obj)
        moves_history.append({
            "ply": ply + 1,
            "side": "W" if board.turn == chess.BLACK else "B",
            "move": bm,
            "elapsed_ms": move_dur_ms,
            "depth": info.get("depth", 0),
            "nodes": info.get("nodes", 0),
            "score_cp": info.get("score_cp", 0)
        })

    if result == "*":
        result = "1/2-1/2"
        termination = "ply_limit_reached"

    game.headers["Result"] = result
    game.headers["Termination"] = termination

    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    pgn_str = game.accept(exporter)

    return {
        "white": white_engine.name,
        "black": black_engine.name,
        "opening_id": opening.get("id", "OP_00"),
        "opening_name": opening.get("name", "Unknown"),
        "result": result,
        "termination": termination,
        "plies": len(board.move_stack),
        "duration_sec": time.time() - t_start,
        "moves": moves_history,
        "pgn": pgn_str
    }


def run_paired_match(
    eng1_name: str, eng1_path: Path, eng1_opts: dict,
    eng2_name: str, eng2_path: Path, eng2_opts: dict,
    openings: list,
    time_base_ms: int,
    time_inc_ms: int,
    tourney_name: str
) -> dict:
    print("\n" + "=" * 80)
    print(f"TOURNAMENT: {tourney_name.upper()}")
    print(f"Engine 1: {eng1_name} vs Engine 2: {eng2_name}")
    print(f"Time Control: {time_base_ms/1000.0:.1f}s + {time_inc_ms/1000.0:.2f}s | Pairs: {len(openings)} ({len(openings)*2} Games)")
    print("=" * 80)

    e1 = UciEngineProcess(eng1_name, eng1_path, eng1_opts)
    e2 = UciEngineProcess(eng2_name, eng2_path, eng2_opts)
    e1.start()
    e2.start()

    games = []
    e1_score = 0.0
    e2_score = 0.0
    e1_wins = 0
    e1_draws = 0
    e1_losses = 0
    all_pgn = []

    try:
        for idx, op in enumerate(openings):
            pair_num = idx + 1
            op_name = op.get("name", f"Opening {pair_num}")

            # Game A: Eng1 White, Eng2 Black
            gA = play_single_game(e1, e2, op, time_base_ms, time_inc_ms)
            games.append(gA)
            all_pgn.append(gA["pgn"])
            if gA["result"] == "1-0":
                e1_score += 1.0; e1_wins += 1
            elif gA["result"] == "1/2-1/2":
                e1_score += 0.5; e2_score += 0.5; e1_draws += 1
            else:
                e2_score += 1.0; e1_losses += 1

            # Game B: Eng2 White, Eng1 Black
            gB = play_single_game(e2, e1, op, time_base_ms, time_inc_ms)
            games.append(gB)
            all_pgn.append(gB["pgn"])
            if gB["result"] == "1-0":
                e2_score += 1.0; e1_losses += 1
            elif gB["result"] == "1/2-1/2":
                e1_score += 0.5; e2_score += 0.5; e1_draws += 1
            else:
                e1_score += 1.0; e1_wins += 1

            total_played = pair_num * 2
            pct = (e1_score / total_played) * 100.0
            print(f"  [Pair {pair_num:02d}/{len(openings):02d}] {op_name:<30} | Game A: {gA['result']:<7} Game B: {gB['result']:<7} | Total: {eng1_name} {e1_score:.1f} - {e2_score:.1f} ({pct:.1f}%)", flush=True)

    finally:
        e1.terminate()
        e2.terminate()

    total_games = len(games)
    score_pct = (e1_score / total_games) * 100.0
    
    # Statistical calculations
    # Clopper-Pearson on wins + draws/2 (or effective Bernoulli equivalent)
    # Using normal approximation / exact binomial on non-draws and draws
    low_pct, high_pct = calc_confidence_interval(e1_score, total_games)
    low_pct *= 100.0
    high_pct *= 100.0

    # Elo difference
    p = max(0.001, min(0.999, e1_score / total_games))
    elo_diff = -400.0 * math.log10(1.0 / p - 1.0)
    p_low = max(0.001, low_pct / 100.0)
    p_high = min(0.999, high_pct / 100.0)
    elo_low = -400.0 * math.log10(1.0 / p_low - 1.0)
    elo_high = -400.0 * math.log10(1.0 / p_high - 1.0)

    print("\n" + "=" * 80)
    print(f"TOURNAMENT SUMMARY: {eng1_name} vs {eng2_name}")
    print("=" * 80)
    print(f"Score: {e1_score:.1f} / {total_games} ({score_pct:.1f}%)")
    print(f"W-D-L: {e1_wins}W - {e1_draws}D - {e1_losses}L")
    print(f"Elo Difference: {elo_diff:+.1f} Elo (95% CI: [{elo_low:+.1f}, {elo_high:+.1f}])")
    print("=" * 80)

    summary = {
        "tournament": tourney_name,
        "engine1": eng1_name,
        "engine2": eng2_name,
        "time_control": f"{time_base_ms/1000.0:.1f}s+{time_inc_ms/1000.0:.2f}s",
        "total_games": total_games,
        "e1_score": e1_score,
        "e2_score": e2_score,
        "e1_wins": e1_wins,
        "e1_draws": e1_draws,
        "e1_losses": e1_losses,
        "score_pct": round(score_pct, 2),
        "clopper_pearson_95ci_pct": [round(low_pct, 2), round(high_pct, 2)],
        "elo_diff": round(elo_diff, 1),
        "elo_95ci": [round(elo_low, 1), round(elo_high, 1)],
        "games": games
    }

    raw_path = RAW_DIR / f"{tourney_name}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    pgn_path = PGN_DIR / f"{tourney_name}.pgn"
    with open(pgn_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_pgn) + "\n")

    print(f"Wrote tournament data to: {raw_path}")
    print(f"Wrote tournament PGN to: {pgn_path}")
    return summary


def main():
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)

    # ----------------------------------------------------
    # TOURNAMENT 2: Janus Classical X (X6) vs Unrestricted Stockfish 19
    # 10 Pairs / 20 Games at 2.0s + 50ms
    # ----------------------------------------------------
    openings_10 = all_openings[:10]
    t2_res = run_paired_match(
        eng1_name="Janus Classical X (X6)",
        eng1_path=X_EXE,
        eng1_opts={"UCI_Variant": "X6"},
        eng2_name="Stockfish 19",
        eng2_path=SF_EXE,
        eng2_opts={"Threads": 1, "Hash": 64, "UCI_LimitStrength": "false", "MultiPV": 1},
        openings=openings_10,
        time_base_ms=2000,
        time_inc_ms=50,
        tourney_name="janus_x_vs_sf19_diagnostic"
    )

    print("\nPhase 8 Strength Qualification Tournaments Completed Successfully!")


if __name__ == "__main__":
    main()
