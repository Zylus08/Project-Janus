#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.6
Tournaments Suite:
1. Tournament 1 (Phase 9): Primary Qualification — Janus Classical X11 (1T) vs Janus Classical X7 (1T)
   - 200 Games (100 Balanced Opening Pairs) at 1.0s + 50ms
2. Tournament 2 (Phase 10A): Multithread Scaling Match — Janus Classical X11 (4T) vs Janus Classical X7 (1T)
   - 40 Games (20 Balanced Opening Pairs) at 1.0s + 50ms
3. Tournament 3 (Phase 10B1): Matched External Benchmark — Janus Classical X11 (1T) vs Stockfish 19 (1T)
   - 40 Games (20 Balanced Opening Pairs) at 2.0s + 50ms
4. Tournament 4 (Phase 10B2): Multithreaded External Benchmark — Janus Classical X11 (4T) vs Stockfish 19 (4T)
   - 40 Games (20 Balanced Opening Pairs) at 2.0s + 50ms
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

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
X11_EXE = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
X7_EXE = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
SF_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.6" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.6" / "pgn"
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
    if p <= 0.001:
        return -800.0
    if p >= 0.999:
        return 800.0
    return -400.0 * math.log10(1.0 / p - 1.0)


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
            if "uciok" in line:
                break

        if self.is_sf:
            self.send(f"setoption name Threads value {self.threads}")
        elif self.is_x7:
            self.send("setoption name Threads value 1")
            self.send("setoption name UCI_Variant value X7")
            self.send("setoption name UCI_DynamicTime value false")
        else:
            # Candidate X11
            self.send(f"setoption name Threads value {self.threads}")
            self.send("setoption name UCI_Variant value X11")
            self.send("setoption name UCI_LMP value L1")
            self.send("setoption name UCI_DynamicTime value true")

        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if "readyok" in line:
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
            if "readyok" in line:
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
    game.headers["Event"] = "Janus P1.6 Match"
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


def run_parallel_tournament(a_cfg, b_cfg, openings, num_pairs, t_base, t_inc, pgn_path, workers=4):
    print(f"\n=======================================================")
    print(f"Tournament: {a_cfg['name']} vs {b_cfg['name']}")
    print(f"Pairs: {num_pairs} ({num_pairs * 2} games), Time: {t_base/1000.0}s+{t_inc/1000.0}s, Workers: {workers}")
    print(f"=======================================================")

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
            if completed % 10 == 0 or completed == num_pairs:
                print(f"Completed {completed}/{num_pairs} pairs ({completed*2}/{num_pairs*2} games) [{(time.time()-t0):.1f}s]")

    total_duration = time.time() - t0

    # Collect in order
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

            r1 = g1["result"]
            r2 = g2["result"]
            if r1 == "1-0":
                a_wins += 1
            elif r1 == "0-1":
                b_wins += 1
            else:
                draws += 1

            if r2 == "0-1":
                a_wins += 1
            elif r2 == "1-0":
                b_wins += 1
            else:
                draws += 1

            s_b = 2.0 - s_a
            pair_diffs.append(s_a - s_b)
            pair_results.append({
                "pair_idx": pidx,
                "opening": op.get("name", f"Pair {pidx}"),
                "g1_result": r1,
                "g2_result": r2,
                "a_score": s_a
            })

    total_games = num_pairs * 2
    a_points = a_wins + 0.5 * draws
    score_pct = a_points / total_games

    # Paired t-test
    n_pairs = len(pair_diffs)
    mean_d = sum(pair_diffs) / n_pairs
    var_d = sum((d - mean_d) ** 2 for d in pair_diffs) / (n_pairs - 1) if n_pairs > 1 else 1e-9
    se_d = math.sqrt(var_d / n_pairs) if var_d > 0 else 1e-9
    t_stat = mean_d / se_d

    # Two-tailed p-value via normal approximation
    p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t_stat) / math.sqrt(2.0))))

    # Clustered CI
    ci_score_low = score_pct - 1.96 * (se_d / 2.0)
    ci_score_high = score_pct + 1.96 * (se_d / 2.0)

    elo_diff = calc_elo(score_pct)
    elo_low = calc_elo(max(0.001, ci_score_low))
    elo_high = calc_elo(min(0.999, ci_score_high))

    summary = {
        "engine_a": a_cfg["name"],
        "engine_b": b_cfg["name"],
        "games": total_games,
        "pairs": num_pairs,
        "time_control": f"{t_base/1000.0}s+{t_inc/1000.0}s",
        "duration_sec": round(total_duration, 1),
        "a_wins": a_wins,
        "b_wins": b_wins,
        "draws": draws,
        "a_points": a_points,
        "score_pct": round(score_pct * 100.0, 2),
        "elo_diff": round(elo_diff, 1),
        "ci_95": [round(elo_low, 1), round(elo_high, 1)],
        "t_stat": round(t_stat, 4),
        "p_val": round(p_val, 4),
        "significant": bool(p_val < 0.05),
        "pair_results": pair_results
    }

    print("\n--- Match Results Summary ---")
    print(f"{a_cfg['name']} vs {b_cfg['name']}: {a_wins}W - {draws}D - {b_wins}L")
    print(f"Score: {a_points}/{total_games} ({summary['score_pct']}%)")
    print(f"Elo Diff: {elo_diff:+.1f} [95% CI: {elo_low:+.1f}, {elo_high:+.1f}]")
    print(f"Paired t-test: t = {t_stat:.4f}, p = {p_val:.4f} (Significant: {summary['significant']})")
    print(f"PGN saved: {pgn_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Janus P1.6 Tournaments Suite")
    parser.add_argument("--match", choices=["t1", "t2", "t3", "t4", "all"], default="all",
                        help="Which tournament to run (t1=X11_1T vs X7_1T, t2=X11_4T vs X7_1T, t3=X11_1T vs SF19_1T, t4=X11_4T vs SF19_4T, all=all 4)")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel worker processes")
    args = parser.parse_args()

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    cfg_x11_1t = {"exe": X11_EXE, "name": "Janus Classical X11 (1T)", "threads": 1, "is_x7": False, "is_sf": False}
    cfg_x11_4t = {"exe": X11_EXE, "name": "Janus Classical X11 (4T)", "threads": 4, "is_x7": False, "is_sf": False}
    cfg_x7_1t  = {"exe": X7_EXE,  "name": "Janus Classical X7 (1T)",  "threads": 1, "is_x7": True,  "is_sf": False}
    cfg_sf19_1t = {"exe": SF_EXE, "name": "Stockfish 19 (1T)",         "threads": 1, "is_x7": False, "is_sf": True}
    cfg_sf19_4t = {"exe": SF_EXE, "name": "Stockfish 19 (4T)",         "threads": 4, "is_x7": False, "is_sf": True}

    if args.match in ["t1", "all"]:
        # Match 1: X11 (1T) vs X7 (1T) — 200 games (100 pairs) at 1.0s + 50ms
        pgn_file = PGN_DIR / "x11_1t_vs_x7.pgn"
        res_t1 = run_parallel_tournament(cfg_x11_1t, cfg_x7_1t, openings, 100, 1000, 50, pgn_file, workers=args.workers)
        with open(RAW_DIR / "x11_1t_vs_x7_tournament_raw.json", "w", encoding="utf-8") as f:
            json.dump(res_t1, f, indent=2)

    if args.match in ["t2", "all"]:
        # Match 2: X11 (4T) vs X7 (1T) — 40 games (20 pairs) at 1.0s + 50ms
        pgn_file = PGN_DIR / "x11_4t_vs_x7_1t.pgn"
        # 4T uses more threads, so use workers=2
        workers_t2 = min(args.workers, 2)
        res_t2 = run_parallel_tournament(cfg_x11_4t, cfg_x7_1t, openings, 20, 1000, 50, pgn_file, workers=workers_t2)
        with open(RAW_DIR / "x11_4t_vs_x7_1t_raw.json", "w", encoding="utf-8") as f:
            json.dump(res_t2, f, indent=2)

    if args.match in ["t3", "all"]:
        # Match 3: X11 (1T) vs Stockfish 19 (1T) — 40 games (20 pairs) at 2.0s + 50ms
        pgn_file = PGN_DIR / "x11_1t_vs_sf19.pgn"
        res_t3 = run_parallel_tournament(cfg_x11_1t, cfg_sf19_1t, openings, 20, 2000, 50, pgn_file, workers=args.workers)
        with open(RAW_DIR / "x11_1t_vs_sf19_raw.json", "w", encoding="utf-8") as f:
            json.dump(res_t3, f, indent=2)

    if args.match in ["t4", "all"]:
        # Match 4: X11 (4T) vs Stockfish 19 (4T) — 40 games (20 pairs) at 2.0s + 50ms
        pgn_file = PGN_DIR / "x11_4t_vs_sf19_4t.pgn"
        # 4T vs 4T uses 8 threads per game, so use workers=2 on 16-core CPU
        workers_t4 = min(args.workers, 2)
        res_t4 = run_parallel_tournament(cfg_x11_4t, cfg_sf19_4t, openings, 20, 2000, 50, pgn_file, workers=workers_t4)
        with open(RAW_DIR / "x11_4t_vs_sf19_4t_raw.json", "w", encoding="utf-8") as f:
            json.dump(res_t4, f, indent=2)

    print("\n[ALL TOURNAMENTS COMPLETED]")

if __name__ == "__main__":
    main()

