#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Independent Strength Qualification & Stockfish 19 Multicore Benchmark
Matches:
  Match A: Janus Classical X12 (4T) vs Janus Classical X11 (4T) [100 pairs, 200 games @ 1.0s+50ms]
  Match B: Janus Classical X12 (4T) vs Janus Classical X7 (1T)  [20 pairs,  40 games @ 1.0s+50ms]
  Match C: Janus Classical X12 (1T) vs Janus Classical X7 (1T)  [20 pairs,  40 games @ 1.0s+50ms]
  Match SF: Janus Classical X12 (4T) vs Stockfish 19 (4T)       [20 pairs,  40 games @ 2.0s+50ms]
"""

import os
import sys
import json
import time
import math
import argparse
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X11 = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_SF  = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "pgn"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PGN_DIR.mkdir(parents=True, exist_ok=True)


def calc_confidence_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def calc_elo(p: float) -> float:
    if p <= 0.0001:
        return -800.0
    if p >= 0.9999:
        return 800.0
    return -400.0 * math.log10(1.0 / p - 1.0)


def student_t_pvalue(t_val: float, df: int) -> float:
    """Exact two-tailed p-value for Student's t distribution with df degrees of freedom."""
    if df <= 0:
        return 1.0
    t = abs(t_val)
    x = df / (df + t * t)
    # Regularized incomplete beta function I_x(a, b) where a = df/2, b = 0.5
    a = df / 2.0
    b = 0.5
    n_steps = 1000
    h = x / n_steps
    def integrand(u):
        if u <= 0.0 or u >= 1.0:
            return 0.0
        return (u ** (a - 1.0)) * ((1.0 - u) ** (b - 1.0))
    
    integral = integrand(0.0) + integrand(x)
    for i in range(1, n_steps):
        u = i * h
        weight = 4.0 if (i % 2 == 1) else 2.0
        integral += weight * integrand(u)
    integral *= (h / 3.0)
    
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    beta_val = math.exp(log_beta)
    cdf = integral / beta_val
    return max(0.0, min(1.0, cdf))


class EngineRunner:
    def __init__(self, exe_path: Path, name: str, threads: int = 1, is_x7: bool = False, is_sf: bool = False):
        self.exe_path = exe_path
        self.name = name
        self.threads = threads
        self.is_x7 = is_x7
        self.is_sf = is_sf
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
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
            self.send("setoption name UCI_DynamicTime value false")
        else:
            self.send(f"setoption name Threads value {self.threads}")
            if "X12" in self.name:
                self.send("setoption name UCI_Variant value X12")
            elif "X11" in self.name:
                self.send("setoption name UCI_Variant value X11")
                self.send("setoption name UCI_LMP value L1")
            self.send("setoption name UCI_DynamicTime value true")

        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

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
                m_score = re.search(r'score cp (-?\d+)', line)
                if m_score:
                    score = int(m_score.group(1))
            elif "score mate" in line:
                m_mate = re.search(r'score mate (-?\d+)', line)
                if m_mate:
                    score = 10000 if int(m_mate.group(1)) > 0 else -10000

        return bestmove, score

    def stop(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()
            self.proc = None


def play_game_worker(white_cfg, black_cfg, opening, time_base_ms, time_inc_ms, max_plies=200):
    white_runner = EngineRunner(
        white_cfg["exe"],
        white_cfg["name"],
        threads=white_cfg.get("threads", 1),
        is_x7=white_cfg.get("is_x7", False),
        is_sf=white_cfg.get("is_sf", False)
    )
    black_runner = EngineRunner(
        black_cfg["exe"],
        black_cfg["name"],
        threads=black_cfg.get("threads", 1),
        is_x7=black_cfg.get("is_x7", False),
        is_sf=black_cfg.get("is_sf", False)
    )
    white_runner.start()
    black_runner.start()
    white_runner.new_game()
    black_runner.new_game()

    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Janus P1.7 Match"
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
        curr_time = wtime if board.turn == chess.WHITE else btime
        curr_inc = winc if board.turn == chess.WHITE else binc

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

    if result == "*":
        result = "1/2-1/2"
        termination = "max_plies_adjudication"

    game.headers["Result"] = result
    game.headers["Termination"] = termination

    white_runner.stop()
    black_runner.stop()

    return {
        "result": result,
        "termination": termination,
        "plies": len(moves_history),
        "duration_sec": time.time() - t_start,
        "pgn": str(game)
    }


def play_pair_worker(pair_args):
    pair_idx, op, a_cfg, b_cfg, t_base, t_inc = pair_args
    # Game 1: A as White, B as Black
    g1 = play_game_worker(a_cfg, b_cfg, op, t_base, t_inc)
    # Game 2: B as White, A as Black
    g2 = play_game_worker(b_cfg, a_cfg, op, t_base, t_inc)

    # Score from engine A's perspective
    r1 = g1["result"]
    s1 = 1.0 if r1 == "1-0" else (0.5 if r1 == "1/2-1/2" else 0.0)

    r2 = g2["result"]
    s2 = 1.0 if r2 == "0-1" else (0.5 if r2 == "1/2-1/2" else 0.0)

    pair_score_a = s1 + s2
    return pair_idx, op, g1, g2, pair_score_a


def run_tournament(a_cfg, b_cfg, openings, num_pairs, t_base, t_inc, pgn_path, workers=4) -> Dict[str, Any]:
    print(f"\n================================================================================", flush=True)
    print(f"Tournament: {a_cfg['name']} vs {b_cfg['name']}", flush=True)
    print(f"Pairs: {num_pairs} ({num_pairs * 2} games), Time: {t_base/1000.0}s+{t_inc/1000.0}s, Workers: {workers}", flush=True)
    print(f"================================================================================", flush=True)

    pair_args_list = []
    for i in range(num_pairs):
        op = openings[i % len(openings)]
        pair_args_list.append((i + 1, op, a_cfg, b_cfg, t_base, t_inc))

    results_by_pair = {}
    t0 = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(play_pair_worker, args): args[0] for args in pair_args_list}
        completed = 0
        for fut in as_completed(futures):
            pidx, op, g1, g2, s_a = fut.result()
            results_by_pair[pidx] = (op, g1, g2, s_a)
            completed += 1
            if completed % 5 == 0 or completed == num_pairs:
                print(f"  Completed {completed}/{num_pairs} pairs ({completed*2}/{num_pairs*2} games) [{(time.time()-t0):.1f}s]", flush=True)

    total_duration = time.time() - t0

    # Collect results
    a_wins = 0
    b_wins = 0
    draws = 0
    pair_diffs = []
    pair_results = []

    with open(pgn_path, "w", encoding="utf-8") as f_pgn:
        for pidx in sorted(results_by_pair.keys()):
            op, g1, g2, s_a = results_by_pair[pidx]
            f_pgn.write(g1["pgn"] + "\n\n")
            f_pgn.write(g2["pgn"] + "\n\n")

            # Game 1
            if g1["result"] == "1-0": a_wins += 1
            elif g1["result"] == "0-1": b_wins += 1
            else: draws += 1

            # Game 2
            if g2["result"] == "0-1": a_wins += 1
            elif g2["result"] == "1-0": b_wins += 1
            else: draws += 1

            d_i = s_a - 1.0 # Pair diff relative to even (0.0 = even, +1.0 = 2-0, -1.0 = 0-2)
            pair_diffs.append(d_i)
            pair_results.append({
                "pair_idx": pidx,
                "opening": op.get("name", "Unknown"),
                "game1_result": g1["result"],
                "game2_result": g2["result"],
                "score_a": s_a,
                "pair_diff": d_i
            })

    total_games = num_pairs * 2
    points_a = a_wins + 0.5 * draws
    score_pct = points_a / total_games
    elo_delta = calc_elo(score_pct)
    ci_low_p, ci_high_p = calc_confidence_interval(points_a, total_games)
    ci_low_elo = calc_elo(ci_low_p)
    ci_high_elo = calc_elo(ci_high_p)

    # Paired Student's t test
    mean_d = sum(pair_diffs) / num_pairs
    variance_d = sum((x - mean_d) ** 2 for x in pair_diffs) / (num_pairs - 1) if num_pairs > 1 else 0.0
    se_d = math.sqrt(variance_d / num_pairs) if num_pairs > 0 else 0.0
    t_stat = (mean_d / se_d) if se_d > 0 else 0.0
    df = num_pairs - 1
    p_val = student_t_pvalue(t_stat, df)

    summary = {
        "engine_a": a_cfg["name"],
        "engine_b": b_cfg["name"],
        "num_pairs": num_pairs,
        "total_games": total_games,
        "wins_a": a_wins,
        "draws": draws,
        "wins_b": b_wins,
        "points_a": points_a,
        "score_pct": round(score_pct * 100.0, 2),
        "elo_delta": round(elo_delta, 1),
        "elo_ci_95": [round(ci_low_elo, 1), round(ci_high_elo, 1)],
        "paired_t_statistic": round(t_stat, 4),
        "degrees_of_freedom": df,
        "p_value": round(p_val, 6),
        "statistically_significant": bool(p_val < 0.05),
        "duration_seconds": round(total_duration, 2),
        "pgn_file": str(pgn_path),
        "pairs": pair_results
    }

    print(f"\n--- MATCH RESULT: {a_cfg['name']} vs {b_cfg['name']} ---", flush=True)
    print(f"Score: {a_wins}W - {draws}D - {b_wins}L = {points_a}/{total_games} ({summary['score_pct']}%)", flush=True)
    print(f"Elo Delta: {summary['elo_delta']} [{summary['elo_ci_95'][0]}, {summary['elo_ci_95'][1]}]", flush=True)
    print(f"Paired t-stat: {summary['paired_t_statistic']} (df={df}), p-value: {summary['p_value']}", flush=True)
    print(f"Significant (p < 0.05): {summary['statistically_significant']}", flush=True)
    print(f"PGN written to: {pgn_path}", flush=True)
    print(f"Total Match Time: {summary['duration_seconds']}s", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description="P1.7 Tournament Suite")
    parser.add_argument("--match", choices=["A", "B", "C", "SF", "all"], default="all", help="Which match to run")
    parser.add_argument("--workers", type=int, default=4, help="Process pool workers")
    args = parser.parse_args()

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    cfg_x12_4t = {"exe": EXE_X12, "name": "Janus Classical X12 (4T)", "threads": 4}
    cfg_x12_1t = {"exe": EXE_X12, "name": "Janus Classical X12 (1T)", "threads": 1}
    cfg_x11_4t = {"exe": EXE_X11, "name": "Janus Classical X11 (4T)", "threads": 4}
    cfg_x7_1t  = {"exe": EXE_X7,  "name": "Janus Classical X7 (1T)",  "threads": 1, "is_x7": True}
    cfg_sf_4t  = {"exe": EXE_SF,  "name": "Stockfish 19 (4T)",        "threads": 4, "is_sf": True}

    internal_json = RAW_DIR / "x12_internal_strength_raw.json"
    internal_results = {}
    if internal_json.exists():
        try:
            with open(internal_json, "r", encoding="utf-8") as f:
                internal_results = json.load(f)
        except Exception:
            internal_results = {}

    # Match A: X12 4T vs X11 4T (200 games / 100 pairs)
    if args.match in ["A", "all"]:
        res_a = run_tournament(
            cfg_x12_4t, cfg_x11_4t, openings,
            num_pairs=100, t_base=1000, t_inc=50,
            pgn_path=PGN_DIR / "x12_4t_vs_x11_4t.pgn",
            workers=args.workers
        )
        internal_results["match_a_x12_4t_vs_x11_4t"] = res_a
        with open(internal_json, "w", encoding="utf-8") as f:
            json.dump(internal_results, f, indent=2)

    # Match B: X12 4T vs X7 1T (40 games / 20 pairs)
    if args.match in ["B", "all"]:
        res_b = run_tournament(
            cfg_x12_4t, cfg_x7_1t, openings,
            num_pairs=20, t_base=1000, t_inc=50,
            pgn_path=PGN_DIR / "x12_4t_vs_x7_1t.pgn",
            workers=args.workers
        )
        internal_results["match_b_x12_4t_vs_x7_1t"] = res_b
        with open(internal_json, "w", encoding="utf-8") as f:
            json.dump(internal_results, f, indent=2)

    # Match C: X12 1T vs X7 1T (40 games / 20 pairs)
    if args.match in ["C", "all"]:
        res_c = run_tournament(
            cfg_x12_1t, cfg_x7_1t, openings,
            num_pairs=20, t_base=1000, t_inc=50,
            pgn_path=PGN_DIR / "x12_1t_vs_x7_1t.pgn",
            workers=args.workers
        )
        internal_results["match_c_x12_1t_vs_x7_1t"] = res_c
        with open(internal_json, "w", encoding="utf-8") as f:
            json.dump(internal_results, f, indent=2)

    if internal_results:
        with open(internal_json, "w", encoding="utf-8") as f:
            json.dump(internal_results, f, indent=2)
        print(f"\n[DONE] Saved internal strength results to {internal_json}", flush=True)

    # Match SF: X12 4T vs SF19 4T (40 games / 20 pairs @ 2.0s+50ms)
    if args.match in ["SF", "all"]:
        res_sf = run_tournament(
            cfg_x12_4t, cfg_sf_4t, openings,
            num_pairs=20, t_base=2000, t_inc=50,
            pgn_path=PGN_DIR / "x12_4t_vs_sf19_4t.pgn",
            workers=args.workers
        )
        sf_json = RAW_DIR / "x12_vs_sf19_raw.json"
        with open(sf_json, "w", encoding="utf-8") as f:
            json.dump({"match_x12_4t_vs_sf19_4t": res_sf}, f, indent=2)
        print(f"\n[DONE] Saved Stockfish 19 benchmark results to {sf_json}", flush=True)


if __name__ == "__main__":
    main()
