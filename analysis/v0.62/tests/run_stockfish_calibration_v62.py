"""Project Janus v0.62 - External Stockfish 19 Calibration Match Runner.

Evaluates Janus Neural Value V2 (Hybrid 50/50, AVX2) against Stockfish 19 across 3 calibrated tiers:
- SF19-A: UCI_LimitStrength=true, UCI_Elo=1320 (20 games: 10 opening pairs)
- SF19-B: UCI_LimitStrength=true, UCI_Elo=1600 (20 games: 10 opening pairs)
- SF19-C: UCI_LimitStrength=true, UCI_Elo=2000 (20 games: 10 opening pairs)

Matches are contested under Fischer 3.0s base + 100ms increment using the first 10 opening pairs
from the independent opening suite (independent_openings_v062.json).
"""

from __future__ import annotations

import json
import sys
import time
import math
import random
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional, Dict, Any, Tuple
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.56" / "tests"))

from tournament_controller import adjudicate_board

CORPUS_PATH = ROOT / "analysis" / "v0.62" / "corpus" / "independent_openings_v062.json"
PGN_DIR = ROOT / "analysis" / "v0.62" / "pgn"
RAW_DIR = ROOT / "analysis" / "v0.62" / "raw"
CANDIDATE_EXE = ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe"
STOCKFISH_EXE = Path(r"E:\ChessXML\tools\stockfish\stockfish.exe")
MODEL_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"

PGN_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


class UCIEngineProcess:
    def __init__(self, exe_path: Path, options: Optional[Dict[str, Any]] = None, cwd: Optional[Path] = None):
        self.exe_path = exe_path
        self.options = options or {}
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(cwd) if cwd else None,
        )
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() in ("uciok", "readyok"):
                break
        for opt_name, opt_val in self.options.items():
            val_str = "true" if opt_val is True else ("false" if opt_val is False else str(opt_val))
            self.p.stdin.write(f"setoption name {opt_name} value {val_str}\n")
        self.p.stdin.write("isready\n")
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
                self.p.wait(timeout=2.0)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


def play_sf_game(
    tier_id: str,
    target_elo: int,
    game_id: int,
    pair_id: int,
    opening_name: str,
    opening_moves: list[str],
    white_is_janus: bool,
    base_time_sec: float = 3.0,
    inc_sec: float = 0.1,
    max_plies: int = 300,
) -> dict:
    janus_opts = {
        "NeuralValueModelPath": str(MODEL_PATH.resolve()),
        "UseNeuralValue": True,
        "NeuralValueBlend": 50,
        "NeuralValueUseAVX2": True,
        "UseKillerOrdering": True,
        "UseHistoryOrdering": True,
        "UseLMR": True,
        "UsePVS": False,
        "UseSEEOrdering": False,
        "UseSEEInQuiescence": False,
    }

    sf_opts = {
        "UCI_LimitStrength": True,
        "UCI_Elo": target_elo,
        "Threads": 1,
        "Hash": 16,
    }

    if white_is_janus:
        white_engine = UCIEngineProcess(CANDIDATE_EXE, janus_opts, cwd=ROOT)
        black_engine = UCIEngineProcess(STOCKFISH_EXE, sf_opts)
        white_name = "Janus Neural Value V2 (Hybrid)"
        black_name = f"Stockfish 19 (Elo {target_elo})"
    else:
        white_engine = UCIEngineProcess(STOCKFISH_EXE, sf_opts)
        black_engine = UCIEngineProcess(CANDIDATE_EXE, janus_opts, cwd=ROOT)
        white_name = f"Stockfish 19 (Elo {target_elo})"
        black_name = "Janus Neural Value V2 (Hybrid)"

    board = chess.Board()
    for m_uci in opening_moves:
        board.push(chess.Move.from_uci(m_uci))

    wtime_ms = int(base_time_sec * 1000)
    btime_ms = int(base_time_sec * 1000)
    winc_ms = int(inc_sec * 1000)
    binc_ms = int(inc_sec * 1000)

    white_engine.ucinewgame()
    black_engine.ucinewgame()

    moves_played = list(opening_moves)
    move_times = []
    t_start = time.time()

    game_over, result_str, termination = adjudicate_board(board, len(moves_played), max_plies)

    while not game_over and len(moves_played) < max_plies:
        active = white_engine if board.turn == chess.WHITE else black_engine
        bm_uci, elapsed = active.play_move(board.fen(), wtime_ms, btime_ms, winc_ms, binc_ms)
        elapsed_ms = int(elapsed * 1000)
        move_times.append(elapsed_ms)

        if board.turn == chess.WHITE:
            wtime_ms = max(10, wtime_ms - elapsed_ms + winc_ms)
        else:
            btime_ms = max(10, btime_ms - elapsed_ms + binc_ms)

        if not bm_uci:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if winner == "Black" else "1-0"
            termination = f"forfeit_no_move_{board.turn}"
            game_over = True
            break

        try:
            m = chess.Move.from_uci(bm_uci)
            if m not in board.legal_moves:
                winner = "Black" if board.turn == chess.WHITE else "White"
                result_str = "0-1" if winner == "Black" else "1-0"
                termination = f"illegal_move_{bm_uci}"
                game_over = True
                break
            board.push(m)
            moves_played.append(bm_uci)
        except Exception as e:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if winner == "Black" else "1-0"
            termination = f"move_parse_error_{e}"
            game_over = True
            break

        game_over, result_str, termination = adjudicate_board(board, len(moves_played), max_plies)

    white_engine.close()
    black_engine.close()
    total_time = time.time() - t_start

    if result_str == "1-0":
        janus_pts = 1.0 if white_is_janus else 0.0
    elif result_str == "0-1":
        janus_pts = 0.0 if white_is_janus else 1.0
    else:
        janus_pts = 0.5

    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = f"Stockfish 19 Calibration ({tier_id})"
    pgn_game.headers["Site"] = "Janus Research Lab"
    pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = str(game_id)
    pgn_game.headers["White"] = white_name
    pgn_game.headers["Black"] = black_name
    pgn_game.headers["Result"] = result_str
    pgn_game.headers["Opening"] = opening_name
    pgn_game.headers["Termination"] = termination
    pgn_game.headers["TimeControl"] = f"{base_time_sec}+{inc_sec}"

    node = pgn_game
    replay_board = chess.Board()
    for m_uci in moves_played:
        mv = chess.Move.from_uci(m_uci)
        node = node.add_variation(mv)
        replay_board.push(mv)

    return {
        "tier": tier_id,
        "target_elo": target_elo,
        "game_id": game_id,
        "pair_id": pair_id,
        "white_is_janus": white_is_janus,
        "result": result_str,
        "janus_points": janus_pts,
        "termination": termination,
        "ply_count": len(moves_played),
        "game_duration_sec": round(total_time, 2),
        "pgn": str(pgn_game),
    }


def run_sf_calibration(max_workers: int = 8):
    print("=" * 80)
    print("PROJECT JANUS v0.62 — EXTERNAL STOCKFISH 19 CALIBRATION")
    print("Candidate: Janus Neural Value V2 (Hybrid 50/50, AVX2)")
    print("Opponent:  Stockfish 19 x64 AVX2 (UCI_LimitStrength=true)")
    print("Tiers:     SF19-A (1320 Elo), SF19-B (1600 Elo), SF19-C (2000 Elo)")
    print("Games:     20 games per tier (10 opening pairs) = 60 total games")
    print("=" * 80, flush=True)

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    # Use first 10 opening pairs
    openings_10 = openings[:10]

    tiers = [
        {"id": "SF19-A", "elo": 1320},
        {"id": "SF19-B", "elo": 1600},
        {"id": "SF19-C", "elo": 2000},
    ]

    all_tasks = []
    game_counter = 1

    for tier in tiers:
        for pid, op in enumerate(openings_10):
            moves = op.get("uci_sequence", [])
            name = op.get("name", f"Opening_{pid+1}")

            all_tasks.append((tier["id"], tier["elo"], game_counter, pid, name, moves, True))
            game_counter += 1

            all_tasks.append((tier["id"], tier["elo"], game_counter, pid, name, moves, False))
            game_counter += 1

    print(f"Prepared {len(all_tasks)} calibration games across {len(tiers)} tiers.", flush=True)

    results = []
    t_start = time.time()
    pgn_path = PGN_DIR / "v062_stockfish_calibration.pgn"
    pgn_file = open(pgn_path, "w", encoding="utf-8")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                play_sf_game,
                t_id,
                t_elo,
                gid,
                pid,
                name,
                moves,
                w_janus,
            ): gid
            for t_id, t_elo, gid, pid, name, moves, w_janus in all_tasks
        }

        completed = 0
        for fut in as_completed(futures):
            gid = futures[fut]
            try:
                gres = fut.result()
                results.append(gres)
                completed += 1
                pgn_file.write(gres["pgn"] + "\n\n")
                pgn_file.flush()

                if completed % 10 == 0 or completed == len(all_tasks):
                    elapsed = time.time() - t_start
                    print(f"[{completed:2d}/{len(all_tasks)}] Calibration games finished | Elapsed: {elapsed:.1f}s", flush=True)
            except Exception as e:
                print(f"Error in game {gid}: {e}", flush=True)

    pgn_file.close()

    # Tier statistics
    tier_summary = {}
    for tier in tiers:
        t_id = tier["id"]
        t_games = [r for r in results if r["tier"] == t_id]
        t_wins = sum(1 for r in t_games if r["janus_points"] == 1.0)
        t_draws = sum(1 for r in t_games if r["janus_points"] == 0.5)
        t_losses = sum(1 for r in t_games if r["janus_points"] == 0.0)
        t_pts = t_wins + 0.5 * t_draws
        t_pct = (t_pts / len(t_games)) * 100.0 if t_games else 0.0

        p_b = max(0.001, min(0.999, t_pts / len(t_games)))
        elo_d = -400.0 * math.log10(1.0 / p_b - 1.0)
        implied_elo = round(tier["elo"] + elo_d)

        tier_summary[t_id] = {
            "target_elo": tier["elo"],
            "games": len(t_games),
            "wins": t_wins,
            "draws": t_draws,
            "losses": t_losses,
            "points": t_pts,
            "score_pct": round(t_pct, 2),
            "elo_delta": round(elo_d, 1),
            "implied_elo": implied_elo,
        }

        print(f"\n{t_id} (Target Elo: {tier['elo']}):")
        print(f"  Score: {t_wins}W - {t_draws}D - {t_losses}L ({t_pts:.1f}/{len(t_games)}, {t_pct:.1f}%)")
        print(f"  Estimated Elo Delta: {elo_d:+.1f} | Implied Janus Elo: ~{implied_elo}")

    out_file = RAW_DIR / "stockfish_19_calibration_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summary": tier_summary, "games": results}, f, indent=2)

    print(f"\nSaved calibration raw results to {out_file}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    run_sf_calibration(max_workers=args.workers)
