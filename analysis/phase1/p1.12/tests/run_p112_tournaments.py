#!/usr/bin/env python3
"""
Project Janus — Milestone P1.12
Tournament Harness & Statistical Analysis Pipeline (JCTS v2 Standard)

Matches:
  Match 1: Janus Classical X17-S (1T) vs Janus Classical X7 (1T)   [50 pairs, 100 games @ 1.0s + 50ms]
  Match 2: Janus Classical X17-S (1T) vs Janus Classical X7 (1T)   [25 pairs,  50 games @ 2.5s + 100ms] (Slower TC)
  Match 3: Janus Classical X17-P (4T) vs Janus Classical X12 (4T)  [50 pairs, 100 games @ 1.0s + 50ms]
  Match 4: Janus Classical X17-S (1T) vs Stockfish 11 (1T)         [20 pairs,  40 games @ 1.5s + 50ms]  (Tier 2 Benchmark 1T)
  Match 5: Janus Classical X17-P (4T) vs Stockfish 11 (4T)         [20 pairs,  40 games @ 1.5s + 50ms]  (Tier 2 Benchmark 4T)
  Match 6: Janus Classical X17-S (1T) vs Stockfish 19 (1T)         [20 pairs,  40 games @ 1.5s + 50ms]  (Tier 3 Benchmark 1T)
  Match 7: Janus Classical X17-P (4T) vs Stockfish 19 (4T)         [20 pairs,  40 games @ 1.5s + 50ms]  (Tier 3 Benchmark 4T)
"""

import os
import sys
import json
import time
import math
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

EXE_X17 = ROOT / "analysis" / "phase1" / "p1.12" / "control" / "janus_classical_x17.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.12" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.12" / "pgn"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PGN_DIR.mkdir(parents=True, exist_ok=True)


def calc_confidence_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    """Wilson score confidence interval for score percentage."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def calc_elo(p: float) -> Optional[float]:
    """Logistic Elo difference from score proportion."""
    if p <= 0.00001:
        return None
    if p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)


class EngineRunner:
    def __init__(self, exe_path: Path, name: str, threads: int = 1, is_x7: bool = False, is_sf: bool = False, variant: str = ""):
        self.exe_path = exe_path
        self.name = name
        self.threads = threads
        self.is_x7 = is_x7
        self.is_sf = is_sf
        self.variant = variant
        self.proc: Optional[subprocess.Popen] = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break

        if self.is_sf:
            self.send(f"setoption name Threads value {self.threads}")
            self.send("setoption name Hash value 32")
        elif self.is_x7:
            self.send("setoption name Threads value 1")
            self.send("setoption name UCI_Variant value X7")
        else:
            self.send(f"setoption name Threads value {self.threads}")
            if self.variant:
                self.send(f"setoption name UCI_Variant value {self.variant}")
            elif "X17" in self.name:
                self.send("setoption name UCI_Variant value X17")
            elif "X12" in self.name:
                self.send("setoption name UCI_Variant value X12")

        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass

    def new_game(self):
        self.send("ucinewgame")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def get_move(self, moves_str: str, wtime: int, btime: int, winc: int, binc: int) -> Tuple[str, Optional[int]]:
        if moves_str:
            self.send(f"position startpos moves {moves_str}")
        else:
            self.send("position startpos")

        self.send(f"go wtime {wtime} btime {btime} winc {winc} binc {binc}")
        bestmove = None
        score = None

        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break
            elif "score cp" in line:
                parts = line.split()
                try:
                    score = int(parts[parts.index("cp") + 1])
                except (ValueError, IndexError):
                    pass
            elif "score mate" in line:
                parts = line.split()
                try:
                    mate_plies = int(parts[parts.index("mate") + 1])
                    score = 30000 - abs(mate_plies) if mate_plies > 0 else -30000 + abs(mate_plies)
                except (ValueError, IndexError):
                    pass

        return bestmove, score

    def stop(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None


def play_single_game(white_cfg: dict, black_cfg: dict, opening: dict, time_base_ms: int, time_inc_ms: int, max_plies: int = 160) -> dict:
    white_runner = EngineRunner(
        white_cfg["exe"],
        white_cfg["name"],
        threads=white_cfg.get("threads", 1),
        is_x7=white_cfg.get("is_x7", False),
        is_sf=white_cfg.get("is_sf", False),
        variant=white_cfg.get("variant", "")
    )
    black_runner = EngineRunner(
        black_cfg["exe"],
        black_cfg["name"],
        threads=black_cfg.get("threads", 1),
        is_x7=black_cfg.get("is_x7", False),
        is_sf=black_cfg.get("is_sf", False),
        variant=black_cfg.get("variant", "")
    )

    white_runner.start()
    black_runner.start()
    white_runner.new_game()
    black_runner.new_game()

    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Janus P1.12 Qualification Match"
    game.headers["White"] = white_cfg["name"]
    game.headers["Black"] = black_cfg["name"]
    game.headers["TimeControl"] = f"{time_base_ms/1000.0:.1f}+{time_inc_ms/1000.0:.2f}"
    game.headers["Opening"] = opening.get("name", "Unknown Opening")

    node = game
    moves_history = []
    for uci_m in opening.get("uci_sequence", []):
        m = chess.Move.from_uci(uci_m)
        board.push(m)
        node = node.add_variation(m)
        moves_history.append(uci_m)

    wtime = time_base_ms
    btime = time_base_ms
    winc = time_inc_ms
    binc = time_inc_ms

    t_start = time.time()
    result = "*"
    termination = "normal"

    consec_high_score = 0
    consec_draw_score = 0
    resign_side = None

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

        moves_str = " ".join(moves_history)
        active_runner = white_runner if board.turn == chess.WHITE else black_runner

        t0 = time.time()
        best_uci, score = active_runner.get_move(moves_str, wtime, btime, winc, binc)
        elapsed_move_ms = int((time.time() - t0) * 1000)

        if board.turn == chess.WHITE:
            wtime = max(10, wtime - elapsed_move_ms + winc)
        else:
            btime = max(10, btime - elapsed_move_ms + binc)

        if not best_uci or best_uci == "0000":
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "illegal_move"
            break

        try:
            m = chess.Move.from_uci(best_uci)
            if m not in board.legal_moves:
                result = "0-1" if board.turn == chess.WHITE else "1-0"
                termination = "illegal_move"
                break
            board.push(m)
            node = node.add_variation(m)
            moves_history.append(best_uci)
        except Exception:
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "move_parse_error"
            break

        # JCTS v2 Section 4.2 Adjudications
        if score is not None:
            # Resignation adjudication: mover is down by >= 600 cp for 4 consecutive half-moves
            if score <= -600 and ply >= 40:
                if resign_side == board.turn:
                    consec_high_score += 1
                else:
                    resign_side = board.turn
                    consec_high_score = 1
                if consec_high_score >= 4:
                    result = "0-1" if resign_side == chess.WHITE else "1-0"
                    termination = "adjudication_resignation"
                    break
            else:
                consec_high_score = 0
                resign_side = None

            # Draw adjudication: both engines agree within [-15, +15] cp for 8 consecutive half-moves
            if abs(score) <= 15 and ply >= 80 and len(board.piece_map()) <= 12:
                consec_draw_score += 1
                if consec_draw_score >= 8:
                    result = "1/2-1/2"
                    termination = "adjudication_draw"
                    break
            else:
                consec_draw_score = 0

    if result == "*":
        result = "1/2-1/2"
        termination = "max_plies_adjudication"

    game.headers["Result"] = result
    game.headers["Termination"] = termination

    white_runner.stop()
    black_runner.stop()

    return {
        "white": white_cfg["name"],
        "black": black_cfg["name"],
        "result": result,
        "termination": termination,
        "plies": len(moves_history),
        "duration_sec": round(time.time() - t_start, 2),
        "pgn_text": str(game)
    }


def play_game_pair(pair_idx: int, a_cfg: dict, b_cfg: dict, opening: dict, time_base_ms: int, time_inc_ms: int) -> dict:
    # Game 1: A as White, B as Black
    g1 = play_single_game(a_cfg, b_cfg, opening, time_base_ms, time_inc_ms)
    # Game 2: B as White, A as Black
    g2 = play_single_game(b_cfg, a_cfg, opening, time_base_ms, time_inc_ms)

    # Score from A's perspective
    pts_g1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
    pts_g2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)
    total_pts_a = pts_g1 + pts_g2

    return {
        "pair_idx": pair_idx,
        "opening_id": opening.get("id", str(pair_idx)),
        "opening_name": opening.get("name", "Unknown"),
        "points_a": total_pts_a,
        "game1": g1,
        "game2": g2
    }


def run_tournament(a_cfg: dict, b_cfg: dict, openings: list, num_pairs: int, t_base: int, t_inc: int, pgn_path: Path, workers: int = 8) -> dict:
    print(f"\n=======================================================", flush=True)
    print(f">>> STARTING MATCH: {a_cfg['name']} vs {b_cfg['name']}", flush=True)
    print(f"    Pairs: {num_pairs} ({num_pairs * 2} games) @ {t_base/1000:.1f}s+{t_inc/1000:.2f}s | Workers: {workers}", flush=True)
    print(f"=======================================================", flush=True)

    t_start = time.time()
    selected_openings = openings[:num_pairs] if len(openings) >= num_pairs else (openings * (num_pairs // len(openings) + 1))[:num_pairs]

    pair_results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(play_game_pair, idx, a_cfg, b_cfg, selected_openings[idx], t_base, t_inc): idx
            for idx in range(num_pairs)
        }
        for future in as_completed(futures):
            res = future.result()
            pair_results.append(res)
            done = len(pair_results)
            pts_so_far = sum(p["points_a"] for p in pair_results)
            games_so_far = done * 2
            score_pct = (pts_so_far / games_so_far) * 100
            if done % 5 == 0 or done == num_pairs:
                print(f"    [Progress: {done}/{num_pairs} pairs ({games_so_far} games)] {a_cfg['name']}: {pts_so_far:.1f}/{games_so_far} ({score_pct:.1f}%)", flush=True)

    pair_results.sort(key=lambda x: x["pair_idx"])
    total_duration = time.time() - t_start

    # Combine PGN
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for p in pair_results:
            pf.write(p["game1"]["pgn_text"] + "\n\n")
            pf.write(p["game2"]["pgn_text"] + "\n\n")

    # Statistics
    total_games = num_pairs * 2
    points_a = sum(p["points_a"] for p in pair_results)
    score_pct = (points_a / total_games) * 100.0

    a_wins = 0
    b_wins = 0
    draws = 0
    for p in pair_results:
        for g in [p["game1"], p["game2"]]:
            r = g["result"]
            if g["white"] == a_cfg["name"]:
                if r == "1-0": a_wins += 1
                elif r == "0-1": b_wins += 1
                else: draws += 1
            else:
                if r == "0-1": a_wins += 1
                elif r == "1-0": b_wins += 1
                else: draws += 1

    ci_low, ci_high = calc_confidence_interval(points_a, total_games)
    elo_delta = calc_elo(points_a / total_games)
    elo_low = calc_elo(ci_low)
    elo_high = calc_elo(ci_high)

    summary = {
        "engine_a": a_cfg["name"],
        "engine_b": b_cfg["name"],
        "total_pairs": num_pairs,
        "total_games": total_games,
        "points_a": points_a,
        "score_pct": round(score_pct, 2),
        "wins_a": a_wins,
        "draws": draws,
        "wins_b": b_wins,
        "elo_delta": round(elo_delta, 1) if elo_delta is not None else None,
        "elo_ci_95": [round(elo_low, 1) if elo_low is not None else -9999.0,
                      round(elo_high, 1) if elo_high is not None else 9999.0],
        "duration_seconds": round(total_duration, 2),
        "pgn_file": str(pgn_path)
    }

    print(f"\n--- MATCH COMPLETED: {a_cfg['name']} vs {b_cfg['name']} ---", flush=True)
    print(f"Result: {a_wins}W - {draws}D - {b_wins}L ({points_a}/{total_games}, {score_pct:.2f}%)", flush=True)
    if elo_delta is not None:
        print(f"Elo Delta: {elo_delta:+.1f} [{elo_low:+.1f}, {elo_high:+.1f}]", flush=True)
    print(f"Duration: {total_duration:.1f}s | PGN: {pgn_path}", flush=True)

    return summary


def main():
    parser = argparse.ArgumentParser(description="JCTS v2 Tournament Suite")
    parser.add_argument("--matches", choices=["internal", "external", "all", "1", "2", "3", "4", "5", "6", "7"], default="all")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    cfg_x17_1t = {"exe": EXE_X17, "name": "Janus Classical X17-S (1T)", "threads": 1, "variant": "X17"}
    cfg_x17_4t = {"exe": EXE_X17, "name": "Janus Classical X17-P (4T)", "threads": 4, "variant": "X17"}
    cfg_x7_1t  = {"exe": EXE_X7,  "name": "Janus Classical X7 (1T)",     "threads": 1, "is_x7": True, "variant": "X7"}
    cfg_x12_4t = {"exe": EXE_X12, "name": "Janus Classical X12 (4T)",    "threads": 4, "variant": "X12"}
    cfg_sf11_1t = {"exe": EXE_SF11, "name": "Stockfish 11 (1T)",         "threads": 1, "is_sf": True}
    cfg_sf11_4t = {"exe": EXE_SF11, "name": "Stockfish 11 (4T)",         "threads": 4, "is_sf": True}
    cfg_sf19_1t = {"exe": EXE_SF19, "name": "Stockfish 19 (1T)",         "threads": 1, "is_sf": True}
    cfg_sf19_4t = {"exe": EXE_SF19, "name": "Stockfish 19 (4T)",         "threads": 4, "is_sf": True}

    out_internal = RAW_DIR / "x17_internal_strength_raw.json"
    internal_data = {}
    if out_internal.exists():
        try:
            with open(out_internal, "r", encoding="utf-8") as f:
                internal_data = json.load(f)
        except Exception:
            internal_data = {}

    out_calibration = RAW_DIR / "x17_external_calibration_raw.json"
    calib_data = {}
    if out_calibration.exists():
        try:
            with open(out_calibration, "r", encoding="utf-8") as f:
                calib_data = json.load(f)
        except Exception:
            calib_data = {}

    # Match 1: X17-S 1T vs X7 1T (100 games @ 1.0s + 50ms)
    if args.matches in ["internal", "all", "1"]:
        res = run_tournament(
            cfg_x17_1t, cfg_x7_1t, openings,
            num_pairs=50, t_base=1000, t_inc=50,
            pgn_path=PGN_DIR / "x17_1t_vs_x7_1t.pgn",
            workers=args.workers
        )
        internal_data["match1_x17_vs_x7_1t"] = res
        with open(out_internal, "w", encoding="utf-8") as f:
            json.dump(internal_data, f, indent=2)

    # Match 2: X17-S 1T vs X7 1T Slow TC (50 games @ 2.5s + 100ms)
    if args.matches in ["internal", "all", "2"]:
        res = run_tournament(
            cfg_x17_1t, cfg_x7_1t, openings,
            num_pairs=25, t_base=2500, t_inc=100,
            pgn_path=PGN_DIR / "x17_1t_vs_x7_1t_slow.pgn",
            workers=args.workers
        )
        internal_data["match2_x17_vs_x7_1t_slow"] = res
        with open(out_internal, "w", encoding="utf-8") as f:
            json.dump(internal_data, f, indent=2)

    # Match 3: X17-P 4T vs X12 4T (100 games @ 1.0s + 50ms)
    if args.matches in ["internal", "all", "3"]:
        res = run_tournament(
            cfg_x17_4t, cfg_x12_4t, openings,
            num_pairs=50, t_base=1000, t_inc=50,
            pgn_path=PGN_DIR / "x17_4t_vs_x12_4t.pgn",
            workers=args.workers
        )
        internal_data["match3_x17_vs_x12_4t"] = res
        with open(out_internal, "w", encoding="utf-8") as f:
            json.dump(internal_data, f, indent=2)

    # Match 4: X17-S 1T vs Stockfish 11 1T (40 games @ 1.5s + 50ms)
    if args.matches in ["external", "all", "4"]:
        res = run_tournament(
            cfg_x17_1t, cfg_sf11_1t, openings,
            num_pairs=20, t_base=1500, t_inc=50,
            pgn_path=PGN_DIR / "x17_1t_vs_sf11_1t.pgn",
            workers=args.workers
        )
        calib_data["match4_x17_vs_sf11_1t"] = res
        with open(out_calibration, "w", encoding="utf-8") as f:
            json.dump(calib_data, f, indent=2)

    # Match 5: X17-P 4T vs Stockfish 11 4T (40 games @ 1.5s + 50ms)
    if args.matches in ["external", "all", "5"]:
        res = run_tournament(
            cfg_x17_4t, cfg_sf11_4t, openings,
            num_pairs=20, t_base=1500, t_inc=50,
            pgn_path=PGN_DIR / "x17_4t_vs_sf11_4t.pgn",
            workers=args.workers
        )
        calib_data["match5_x17_vs_sf11_4t"] = res
        with open(out_calibration, "w", encoding="utf-8") as f:
            json.dump(calib_data, f, indent=2)

    # Match 6: X17-S 1T vs Stockfish 19 1T (40 games @ 1.5s + 50ms)
    if args.matches in ["external", "all", "6"]:
        res = run_tournament(
            cfg_x17_1t, cfg_sf19_1t, openings,
            num_pairs=20, t_base=1500, t_inc=50,
            pgn_path=PGN_DIR / "x17_1t_vs_sf19_1t.pgn",
            workers=args.workers
        )
        calib_data["match6_x17_vs_sf19_1t"] = res
        with open(out_calibration, "w", encoding="utf-8") as f:
            json.dump(calib_data, f, indent=2)

    # Match 7: X17-P 4T vs Stockfish 19 4T (40 games @ 1.5s + 50ms)
    if args.matches in ["external", "all", "7"]:
        res = run_tournament(
            cfg_x17_4t, cfg_sf19_4t, openings,
            num_pairs=20, t_base=1500, t_inc=50,
            pgn_path=PGN_DIR / "x17_4t_vs_sf19_4t.pgn",
            workers=args.workers
        )
        calib_data["match7_x17_vs_sf19_4t"] = res
        with open(out_calibration, "w", encoding="utf-8") as f:
            json.dump(calib_data, f, indent=2)

    print("\n=======================================================", flush=True)
    print("TOURNAMENT SUITE RUN COMPLETED!", flush=True)
    print(f"Internal results: {out_internal}", flush=True)
    print(f"External calibration: {out_calibration}", flush=True)
    print("=======================================================", flush=True)


if __name__ == "__main__":
    main()
