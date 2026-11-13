#!/usr/bin/env python3
"""
run_p115_tournaments.py
Milestone P1.15 Independent Strength Qualification & Competitive Calibration.
Executes:
  Match 1: X20-S (1T) vs Janus Classical X7 (1T Baseline)    [50 pairs, 100 games @ 1.0s + 50ms]
  Match 2: X20-S (1T) vs Janus Classical X7 (1T Baseline)    [25 pairs,  50 games @ 2.5s + 100ms] (Slow TC)
  Match 3: X20-P (4T) vs Janus Classical X12 (4T Baseline)   [50 pairs, 100 games @ 1.0s + 50ms]
  Match 4: X20-S (1T) vs Janus Classical X19-S (1T Baseline) [25 pairs,  50 games @ 1.0s + 50ms]
  Match 5: X20-S (1T) vs Stockfish 4 (1T)                   [20 pairs,  40 games @ 1.5s + 50ms]
  Match 6: X20-S (1T) vs Stockfish 11 (1T)                  [20 pairs,  40 games @ 1.5s + 50ms]
  Match 7: X20-S (1T) vs Stockfish 19 (1T)                  [20 pairs,  40 games @ 1.5s + 50ms]
Total: 420 games.
"""

import os
import sys
import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

EXE_X20 = ROOT / "analysis" / "phase1" / "p1.15" / "control" / "janus_classical_x20.exe"
EXE_X19 = ROOT / "analysis" / "phase1" / "p1.14" / "control" / "janus_classical_x19.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"

EXE_SF4  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.15" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.15" / "pgn"
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
    if p <= 0.00001 or p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)

def calc_paired_ci_and_pvalue(pair_scores: List[float], z: float = 1.95996) -> Tuple[float, float, float, float]:
    """
    Calculates 95% paired confidence interval and 1-sided p-value against H0: mu <= 0.5.
    pair_scores is list of normalized pair scores in [0.0, 1.0] (pair_pts / 2.0).
    Returns (mean_p, ci_low, ci_high, p_value).
    """
    n = len(pair_scores)
    if n == 0:
        return 0.0, 0.0, 1.0, 1.0
    mean_p = sum(pair_scores) / n
    if n == 1:
        return mean_p, 0.0, 1.0, 0.5
    var = sum((x - mean_p) ** 2 for x in pair_scores) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 1e-6
    ci_low = max(0.0, mean_p - z * se)
    ci_high = min(1.0, mean_p + z * se)

    # 1-sided z-test / t-test approximation
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    # Normal CDF approximation
    p_value = 0.5 * math.erfc(t_stat / math.sqrt(2))
    return mean_p, ci_low, ci_high, p_value

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
            elif "X20" in self.name:
                self.send("setoption name UCI_Variant value X20")
            elif "X19" in self.name:
                self.send("setoption name UCI_Variant value X19")
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
        Path(white_cfg["exe"]),
        white_cfg["name"],
        threads=white_cfg.get("threads", 1),
        is_x7=white_cfg.get("is_x7", False),
        is_sf=white_cfg.get("is_sf", False),
        variant=white_cfg.get("variant", "")
    )
    black_runner = EngineRunner(
        Path(black_cfg["exe"]),
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
    moves_history = []

    # Load opening moves
    for m_san in opening.get("moves", []):
        try:
            m = board.parse_san(m_san)
            board.push(m)
            moves_history.append(m.uci())
        except Exception:
            break

    wtime = time_base_ms
    btime = time_base_ms
    winc = time_inc_ms
    binc = time_inc_ms

    adjudication = None
    termination = "normal"
    draw_claim_moves = 0
    consecutive_draw_evals = 0

    while len(moves_history) < max_plies and not board.is_game_over(claim_draw=True):
        turn = board.turn
        current_runner = white_runner if turn == chess.WHITE else black_runner
        cur_time = wtime if turn == chess.WHITE else btime
        cur_inc = winc if turn == chess.WHITE else binc

        t0 = time.time()
        moves_str = " ".join(moves_history)
        bm_uci, eval_cp = current_runner.get_move(moves_str, cur_time, btime if turn == chess.WHITE else wtime, cur_inc, binc if turn == chess.WHITE else winc)
        elapsed_ms = int((time.time() - t0) * 1000)

        # Update clock with 10ms safety floor against pipe jitter
        if turn == chess.WHITE:
            wtime = max(10, wtime - elapsed_ms + winc)
        else:
            btime = max(10, btime - elapsed_ms + binc)

        if not bm_uci:
            termination = "no_move"
            adjudication = "0-1" if turn == chess.WHITE else "1-0"
            break

        try:
            move = chess.Move.from_uci(bm_uci)
            if move not in board.legal_moves:
                termination = f"illegal_move_{bm_uci}"
                adjudication = "0-1" if turn == chess.WHITE else "1-0"
                break
        except Exception:
            termination = f"corrupt_move_{bm_uci}"
            adjudication = "0-1" if turn == chess.WHITE else "1-0"
            break

        board.push(move)
        moves_history.append(bm_uci)

        # Adjudication checks (eval stability)
        if eval_cp is not None and abs(eval_cp) <= 10 and len(moves_history) >= 60:
            consecutive_draw_evals += 1
            if consecutive_draw_evals >= 10:
                termination = "eval_draw_adjudication"
                adjudication = "1/2-1/2"
                break
        else:
            consecutive_draw_evals = 0

        if eval_cp is not None and abs(eval_cp) >= 1000 and len(moves_history) >= 50:
            draw_claim_moves += 1
            if draw_claim_moves >= 6:
                termination = "eval_resignation_adjudication"
                if eval_cp > 0:
                    adjudication = "1-0" if turn == chess.WHITE else "0-1"
                else:
                    adjudication = "0-1" if turn == chess.WHITE else "1-0"
                break
        else:
            draw_claim_moves = 0

    white_runner.stop()
    black_runner.stop()

    if not adjudication:
        if board.is_checkmate():
            adjudication = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "checkmate"
        elif board.is_stalemate():
            adjudication = "1/2-1/2"
            termination = "stalemate"
        elif board.is_insufficient_material():
            adjudication = "1/2-1/2"
            termination = "insufficient_material"
        elif board.can_claim_threefold_repetition():
            adjudication = "1/2-1/2"
            termination = "threefold_repetition"
        elif board.can_claim_fifty_moves():
            adjudication = "1/2-1/2"
            termination = "fifty_moves"
        else:
            adjudication = "1/2-1/2"
            termination = "max_plies_drawn"

    return {
        "white": white_cfg["name"],
        "black": black_cfg["name"],
        "result": adjudication,
        "termination": termination,
        "plies": len(moves_history),
        "moves": moves_history,
        "eco": opening.get("eco", ""),
        "opening_name": opening.get("name", ""),
        "fen": opening.get("fen", chess.STARTING_FEN)
    }

def run_match_task(args):
    game_idx, w_cfg, b_cfg, op, tb, ti = args
    res = play_single_game(w_cfg, b_cfg, op, tb, ti)
    return game_idx, res

def execute_match(match_name: str, eng_a: dict, eng_b: dict, openings: list, num_pairs: int, time_base: int, time_inc: int, max_workers: int = 8) -> dict:
    pgn_path = PGN_DIR / f"{match_name}.pgn"
    game_count = num_pairs * 2

    print(f"\n================================================================================")
    print(f"STARTING MATCH: {match_name} ({game_count} games @ {time_base}ms + {time_inc}ms)")
    print(f"================================================================================")

    tasks = []
    for pair_idx in range(num_pairs):
        op = openings[pair_idx % len(openings)]
        # Game 1: A is White, B is Black
        tasks.append((pair_idx * 2, eng_a, eng_b, op, time_base, time_inc))
        # Game 2: B is White, A is Black
        tasks.append((pair_idx * 2 + 1, eng_b, eng_a, op, time_base, time_inc))

    results = [None] * game_count
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_match_task, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            g_idx, res = fut.result()
            results[g_idx] = res
            print(f"[{match_name}] Game {g_idx+1:2d}/{game_count}: {res['white']} vs {res['black']} -> {res['result']} ({res['termination']}, {res['plies']} plies)", flush=True)

    # Save PGN
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for idx, g in enumerate(results):
            pgn_game = chess.pgn.Game()
            pgn_game.headers["Event"] = f"P1.15 Tournament: {match_name}"
            pgn_game.headers["Round"] = str(idx + 1)
            pgn_game.headers["White"] = g["white"]
            pgn_game.headers["Black"] = g["black"]
            pgn_game.headers["Result"] = g["result"]
            pgn_game.headers["Termination"] = g["termination"]
            pgn_game.headers["ECO"] = g["eco"]
            pgn_game.headers["Opening"] = g["opening_name"]

            node = pgn_game
            b = chess.Board()
            for m_uci in g["moves"]:
                m = chess.Move.from_uci(m_uci)
                node = node.add_variation(m)
                b.push(m)
            pf.write(str(pgn_game) + "\n\n")

    # Analyze from perspective of eng_a
    wins_a = 0
    draws = 0
    losses_a = 0
    time_forfeits = 0
    illegal_moves = 0

    for g in results:
        is_a_white = g["white"] == eng_a["name"]
        res = g["result"]
        if res == "1-0":
            if is_a_white: wins_a += 1
            else: losses_a += 1
        elif res == "0-1":
            if is_a_white: losses_a += 1
            else: wins_a += 1
        else:
            draws += 1

        if "no_move" in g["termination"]: time_forfeits += 1
        if "illegal" in g["termination"] or "corrupt" in g["termination"]: illegal_moves += 1

    pts_a = wins_a + 0.5 * draws
    score_pct = (pts_a / game_count) * 100.0
    w_low, w_high = calc_confidence_interval(pts_a, game_count)
    elo = calc_elo(pts_a / game_count)

    # Pentanomial distribution & paired stats
    pentanomial = {"WW": 0, "WD": 0, "DD_WL": 0, "LD": 0, "LL": 0}
    pair_normalized_scores = []
    for p in range(num_pairs):
        g1 = results[2 * p]
        g2 = results[2 * p + 1]

        def get_g_pts(g, name):
            if g["result"] == "1/2-1/2": return 0.5
            if g["result"] == "1-0": return 1.0 if g["white"] == name else 0.0
            if g["result"] == "0-1": return 1.0 if g["black"] == name else 0.0
            return 0.5

        p_pts = get_g_pts(g1, eng_a["name"]) + get_g_pts(g2, eng_a["name"])
        pair_normalized_scores.append(p_pts / 2.0)

        if p_pts == 2.0: pentanomial["WW"] += 1
        elif p_pts == 1.5: pentanomial["WD"] += 1
        elif p_pts == 1.0: pentanomial["DD_WL"] += 1
        elif p_pts == 0.5: pentanomial["LD"] += 1
        else: pentanomial["LL"] += 1

    p_mean, p_low, p_high, p_val = calc_paired_ci_and_pvalue(pair_normalized_scores)

    summary = {
        "match": match_name,
        "engine_a": eng_a["name"],
        "engine_b": eng_b["name"],
        "total_games": game_count,
        "pairs": num_pairs,
        "time_control": f"{time_base/1000}s + {time_inc/1000}s",
        "wins": wins_a,
        "draws": draws,
        "losses": losses_a,
        "points": pts_a,
        "score_pct": round(score_pct, 2),
        "elo": round(elo, 1) if elo is not None else None,
        "wilson_ci_95": [round(w_low * 100.0, 2), round(w_high * 100.0, 2)],
        "paired_ci_95": [round(p_low * 100.0, 2), round(p_high * 100.0, 2)],
        "p_value_onesided": round(p_val, 5),
        "statistically_superior": (p_low > 0.50 and p_val < 0.05),
        "pentanomial": pentanomial,
        "technical_incidents": {
            "time_forfeits": time_forfeits,
            "illegal_moves": illegal_moves
        }
    }

    print(f"\nMATCH {match_name} COMPLETE:")
    print(f"  Score: {wins_a}W - {draws}D - {losses_a}L ({pts_a}/{game_count} = {score_pct:.2f}%)")
    print(f"  Elo: {elo} | Paired 95% CI: [{summary['paired_ci_95'][0]}%, {summary['paired_ci_95'][1]}%] | p-value: {p_val:.4f}")
    print(f"  Pentanomial: {pentanomial}")
    print(f"  Statistically Superior: {summary['statistically_superior']}")

    return summary

def main():
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    cfg_x20_1t = {"exe": str(EXE_X20), "name": "Janus Classical X20-S (1T)", "threads": 1, "variant": "X20"}
    cfg_x20_4t = {"exe": str(EXE_X20), "name": "Janus Classical X20-P (4T)", "threads": 4, "variant": "X20"}
    cfg_x7_1t  = {"exe": str(EXE_X7),  "name": "Janus Classical X7 (1T)",   "threads": 1, "is_x7": True}
    cfg_x12_4t = {"exe": str(EXE_X12), "name": "Janus Classical X12 (4T)",  "threads": 4, "variant": "X12"}
    cfg_x19_1t = {"exe": str(EXE_X19), "name": "Janus Classical X19-S (1T)", "threads": 1, "variant": "X19"}

    cfg_sf4_1t  = {"exe": str(EXE_SF4),  "name": "Stockfish 4 (1T)",  "threads": 1, "is_sf": True}
    cfg_sf11_1t = {"exe": str(EXE_SF11), "name": "Stockfish 11 (1T)", "threads": 1, "is_sf": True}
    cfg_sf19_1t = {"exe": str(EXE_SF19), "name": "Stockfish 19 (1T)", "threads": 1, "is_sf": True}

    matches_summary = {}

    # Match 1: X20-S (1T) vs X7 Baseline (1T) @ 1.0s + 50ms (50 pairs = 100 games)
    matches_summary["match1_x20s_vs_x7_fast"] = execute_match(
        "x20_1t_vs_x7_1t", cfg_x20_1t, cfg_x7_1t, openings, num_pairs=50, time_base=1000, time_inc=50, max_workers=8
    )

    # Match 2: X20-S (1T) vs X7 Baseline (1T) @ 2.5s + 100ms (25 pairs = 50 games)
    matches_summary["match2_x20s_vs_x7_slow"] = execute_match(
        "x20_1t_vs_x7_1t_slow", cfg_x20_1t, cfg_x7_1t, openings, num_pairs=25, time_base=2500, time_inc=100, max_workers=8
    )

    # Match 3: X20-P (4T) vs X12 Baseline (4T) @ 1.0s + 50ms (50 pairs = 100 games)
    matches_summary["match3_x20p_vs_x12_fast"] = execute_match(
        "x20_4t_vs_x12_4t", cfg_x20_4t, cfg_x12_4t, openings, num_pairs=50, time_base=1000, time_inc=50, max_workers=8
    )

    # Match 4: X20-S (1T) vs X19-S Baseline (1T) @ 1.0s + 50ms (25 pairs = 50 games)
    matches_summary["match4_x20s_vs_x19s_fast"] = execute_match(
        "x20_1t_vs_x19_1t", cfg_x20_1t, cfg_x19_1t, openings, num_pairs=25, time_base=1000, time_inc=50, max_workers=8
    )

    # Match 5: X20-S (1T) vs Stockfish 4 (1T) @ 1.5s + 50ms (20 pairs = 40 games)
    matches_summary["match5_x20s_vs_sf4"] = execute_match(
        "x20_1t_vs_sf4_1t", cfg_x20_1t, cfg_sf4_1t, openings, num_pairs=20, time_base=1500, time_inc=50, max_workers=8
    )

    # Match 6: X20-S (1T) vs Stockfish 11 (1T) @ 1.5s + 50ms (20 pairs = 40 games)
    matches_summary["match6_x20s_vs_sf11"] = execute_match(
        "x20_1t_vs_sf11_1t", cfg_x20_1t, cfg_sf11_1t, openings, num_pairs=20, time_base=1500, time_inc=50, max_workers=8
    )

    # Match 7: X20-S (1T) vs Stockfish 19 (1T) @ 1.5s + 50ms (20 pairs = 40 games)
    matches_summary["match7_x20s_vs_sf19"] = execute_match(
        "x20_1t_vs_sf19_1t", cfg_x20_1t, cfg_sf19_1t, openings, num_pairs=20, time_base=1500, time_inc=50, max_workers=8
    )

    raw_out_path = RAW_DIR / "p115_tournaments_raw.json"
    with open(raw_out_path, "w", encoding="utf-8") as f:
        json.dump(matches_summary, f, indent=2)

    print(f"\n================================================================================")
    print(f"ALL 420 TOURNAMENT GAMES COMPLETED SUCCESSFULLY. RAW DATA SAVED TO {raw_out_path}")
    print(f"================================================================================")

if __name__ == "__main__":
    main()

