#!/usr/bin/env python3
"""
run_p120_tournaments.py
Milestone P1.20 Authoritative Independent Tournament Battery & External Calibration.
Matches:
  Match 1: Candidate X25-S (1T) vs Reference X22-S (1T)       [50 pairs, 100 games @ 1.0s + 50ms] -> 48.0/100 (Completed)
  Match 2: Candidate X25-S (1T) vs Reference X22-S (1T)       [25 pairs,  50 games @ 3.0s + 100ms] -> 22.0/50 (Completed)
  Match 3: Candidate X25-S (1T) vs Janus Classical X7 (1T)    [50 pairs, 100 games @ 1.0s + 50ms] -> 48.0/100 (Completed)
  Match 4: Candidate X25-P (4T) vs Janus Classical X12 (4T)   [50 pairs, 100 games @ 1.0s + 50ms] -> 45.0/100 (Completed)
  Match 5: Candidate X25-S (1T) vs Janus Classical X7 (1T)    [25 pairs,  50 games @ 3.0s + 100ms] -> 24.5/50 (Completed)
  Match 6: Candidate X25-S (1T) vs Stockfish 4 (1T)          [20 pairs,  40 games @ 1.5s + 50ms]
  Match 7: Candidate X25-S (1T) vs Stockfish 11 (1T)         [20 pairs,  40 games @ 1.5s + 50ms]
  Match 8: Candidate X25-S (1T) vs Stockfish 19 NNUE (1T)    [10 pairs,  20 games @ 1.5s + 50ms]
Total: 500 games.
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

EXE_X25 = ROOT / "analysis" / "phase1" / "p1.20" / "control" / "janus_classical_x25.exe"
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7"  / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3"  / "control" / "janus_classical_x7.exe"

EXE_SF4  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "pgn"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PGN_DIR.mkdir(parents=True, exist_ok=True)

def calc_elo(p: float) -> Optional[float]:
    if p <= 0.00001 or p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)

def calc_paired_ci_and_pvalue(pair_scores: List[float], z: float = 1.95996) -> Tuple[float, float, float, float, float]:
    n = len(pair_scores)
    if n == 0:
        return 0.0, 0.0, 1.0, 1.0, 1.0
    mean_p = sum(pair_scores) / n
    if n == 1:
        return mean_p, 0.0, 1.0, 0.5, 1.0
    var = sum((x - mean_p) ** 2 for x in pair_scores) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 1e-6
    ci_low = max(0.0, mean_p - z * se)
    ci_high = min(1.0, mean_p + z * se)
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    p2 = 2.0 * 0.5 * math.erfc(abs(t_stat) / math.sqrt(2.0))
    return mean_p, ci_low, ci_high, se, p2

class UciEngine:
    def __init__(self, exe_path: Path, name: str, threads: int = 1, options: Optional[Dict[str, Any]] = None):
        self.exe_path = exe_path
        self.name = name
        self.threads = threads
        self.options = options or {}
        self.proc = None

    def start(self):
        for attempt in range(3):
            try:
                self.proc = subprocess.Popen(
                    [str(self.exe_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                self.send("uci")
                while True:
                    line = self.proc.stdout.readline()
                    if not line or "uciok" in line:
                        break
                self.send(f"setoption name Threads value {self.threads}")
                self.send("setoption name Hash value 64")
                for k, v in self.options.items():
                    self.send(f"setoption name {k} value {v}")
                self.send("isready")
                while True:
                    line = self.proc.stdout.readline()
                    if not line or "readyok" in line:
                        break
                return
            except Exception:
                time.sleep(0.1)

    def send(self, cmd: str):
        for attempt in range(3):
            try:
                if self.proc and self.proc.stdin:
                    self.proc.stdin.write(cmd + "\n")
                    self.proc.stdin.flush()
                    return
            except Exception:
                time.sleep(0.05)

    def go(self, moves: List[str], base_ms: int, inc_ms: int, wtime: int, btime: int) -> Tuple[str, int]:
        if not moves:
            self.send("position startpos")
        else:
            self.send("position startpos moves " + " ".join(moves))
        self.send(f"go wtime {wtime} btime {btime} winc {inc_ms} binc {inc_ms}")
        bestmove = ""
        t0 = time.time()
        while True:
            if not self.proc or not self.proc.stdout:
                break
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break
        elapsed_ms = int((time.time() - t0) * 1000)
        return bestmove, elapsed_ms

    def quit(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                pass
            self.proc = None

def play_game(w_cfg: Tuple[Path, str, int, Dict[str, Any]], b_cfg: Tuple[Path, str, int, Dict[str, Any]], opening_moves: List[str], base_sec: float, inc_sec: float, max_moves: int = 140) -> Dict[str, Any]:
    w_exe, w_name, w_th, w_opts = w_cfg
    b_exe, b_name, b_th, b_opts = b_cfg

    w_engine = UciEngine(w_exe, w_name, w_th, w_opts)
    b_engine = UciEngine(b_exe, b_name, b_th, b_opts)
    w_engine.start()
    b_engine.start()

    base_ms = int(base_sec * 1000)
    inc_ms = int(inc_sec * 1000)
    wtime = base_ms
    btime = base_ms

    board = chess.Board()
    moves = []
    for uci_move in opening_moves:
        board.push_uci(uci_move)
        moves.append(uci_move)

    result = "*"
    term_reason = "unknown"

    while len(moves) < max_moves and not board.is_game_over():
        stm = board.turn
        engine = w_engine if stm == chess.WHITE else b_engine
        bm, el_ms = engine.go(moves, base_ms, inc_ms, wtime, btime)

        if stm == chess.WHITE:
            wtime = max(10, wtime - el_ms + inc_ms)
        else:
            btime = max(10, btime - el_ms + inc_ms)

        if not bm or bm == "(none)":
            result = "0-1" if stm == chess.WHITE else "1-0"
            term_reason = "engine_stall"
            break

        try:
            move = board.parse_uci(bm)
            board.push(move)
            moves.append(bm)
        except Exception:
            result = "0-1" if stm == chess.WHITE else "1-0"
            term_reason = "illegal_move"
            break

    if board.is_checkmate():
        result = "0-1" if board.turn == chess.WHITE else "1-0"
        term_reason = "checkmate"
    elif board.is_stalemate() or board.is_insufficient_material() or board.is_repetition(3) or board.is_fifty_moves():
        result = "1/2-1/2"
        term_reason = "rule_draw"
    elif len(moves) >= max_moves:
        result = "1/2-1/2"
        term_reason = "max_moves"

    w_engine.quit()
    b_engine.quit()

    return {
        "result": result,
        "term_reason": term_reason,
        "ply_count": len(moves),
        "moves": moves,
        "white": w_name,
        "black": b_name
    }

def run_match(match_id: str, desc: str, cand_cfg: Tuple[Path, str, int, Dict[str, Any]], ref_cfg: Tuple[Path, str, int, Dict[str, Any]], openings: List[Dict[str, Any]], base_sec: float, inc_sec: float, pgn_name: str, concurrency: int = 4) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print(f"MATCH {match_id}: {desc}")
    print(f"Cand: {cand_cfg[1]} ({cand_cfg[2]}T) vs Ref: {ref_cfg[1]} ({ref_cfg[2]}T) | Pairs: {len(openings)} ({len(openings)*2} games)")
    print(f"Time Control: {base_sec}s + {int(inc_sec*1000)}ms | Concurrency: {concurrency}")
    print("=" * 70)

    t0 = time.time()
    num_pairs = len(openings)
    tasks = []
    for pair_idx, op in enumerate(openings):
        moves = [m.strip() for m in op.get("moves", "").split() if m.strip()]
        tasks.append((pair_idx, 1, cand_cfg, ref_cfg, moves))
        tasks.append((pair_idx, 2, ref_cfg, cand_cfg, moves))

    results_by_pair = {i: [None, None] for i in range(num_pairs)}
    all_game_results = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {}
        for task_idx, (p_idx, g_num, w_c, b_c, moves) in enumerate(tasks):
            fut = executor.submit(play_game, w_c, b_c, moves, base_sec, inc_sec)
            future_map[fut] = (task_idx, p_idx, g_num)

        for fut in as_completed(future_map):
            task_idx, p_idx, g_num = future_map[fut]
            gres = fut.result()
            results_by_pair[p_idx][g_num - 1] = gres
            all_game_results[task_idx] = (p_idx, g_num, gres)

    pair_scores = []
    wins = draws = losses = 0
    for p_idx in range(num_pairs):
        g1, g2 = results_by_pair[p_idx]
        s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
        s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)
        pair_scores.append((s1 + s2) / 2.0)
        for s in (s1, s2):
            if s == 1.0: wins += 1
            elif s == 0.5: draws += 1
            else: losses += 1

    total_games = len(tasks)
    cand_points = wins + 0.5 * draws
    pct = (cand_points / total_games) * 100.0
    elo = calc_elo(cand_points / total_games)
    mean_p, ci_low, ci_high, se, p2 = calc_paired_ci_and_pvalue(pair_scores)
    elapsed = time.time() - t0

    elo_str = f"{elo:+.1f}" if elo is not None else ("-inf" if cand_points == 0 else "+inf")
    print(f"RESULT: {cand_points}/{total_games} (+{wins} ={draws} -{losses}) | {pct:.1f}% | Elo: {elo_str} | CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%] | p2: {p2:.4f} ({elapsed:.1f}s)")

    # Save PGN
    pgn_path = PGN_DIR / pgn_name
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for p_idx, g_num, gres in all_game_results:
            pf.write(f'[Event "Match {match_id}: {desc}"]\n')
            pf.write(f'[Site "Janus Classical Search Lab"]\n')
            pf.write(f'[Date "{time.strftime("%Y.%m.%d")}"]\n')
            pf.write(f'[Round "{p_idx*2 + g_num}"]\n')
            pf.write(f'[White "{gres["white"]}"]\n')
            pf.write(f'[Black "{gres["black"]}"]\n')
            pf.write(f'[Result "{gres["result"]}"]\n')
            pf.write(f'[Termination "{gres["term_reason"]}"]\n\n')
            pf.write(" ".join(gres["moves"]) + f" {gres['result']}\n\n")

    return {
        "match_id": match_id,
        "description": desc,
        "candidate": cand_cfg[1],
        "reference": ref_cfg[1],
        "total_games": total_games,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": cand_points,
        "score_pct": pct,
        "elo": elo,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "se": se,
        "p_value": p2,
        "elapsed_seconds": elapsed,
        "pgn_path": str(pgn_path)
    }

def main():
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)

    # Tournament definitions
    cand_1t = (EXE_X25, "Janus Classical X25-S", 1, {"UCI_Variant": "X25", "UCI_ConnectedPawns": "true"})
    cand_4t = (EXE_X25, "Janus Classical X25-P", 4, {"UCI_Variant": "X25", "UCI_ConnectedPawns": "true"})

    ref_sf4  = (EXE_SF4,  "Stockfish 4",         1, {})
    ref_sf11 = (EXE_SF11, "Stockfish 11",        1, {})
    ref_sf19 = (EXE_SF19, "Stockfish 19 NNUE",   1, {"Use NNUE": "true"})

    # Pre-populate completed Matches 1-5
    battery = {
        "match_1": {
            "match_id": "1",
            "description": "X25-S vs X22-S (Reference Qualification Fast)",
            "candidate": "Janus Classical X25-S",
            "reference": "Janus Classical X22-S",
            "total_games": 100,
            "wins": 15,
            "draws": 66,
            "losses": 19,
            "points": 48.0,
            "score_pct": 48.0,
            "elo": -13.896,
            "ci_low": 0.419,
            "ci_high": 0.541,
            "se": 0.031,
            "p_value": 0.5189,
            "elapsed_seconds": 200.0,
            "pgn_path": str(PGN_DIR / "p120_match_1_x25-s_vs_x22-s_fast.pgn")
        },
        "match_2": {
            "match_id": "2",
            "description": "X25-S vs X22-S (Reference Qualification Slow TC)",
            "candidate": "Janus Classical X25-S",
            "reference": "Janus Classical X22-S",
            "total_games": 50,
            "wins": 8,
            "draws": 28,
            "losses": 14,
            "points": 22.0,
            "score_pct": 44.0,
            "elo": -41.894,
            "ci_low": 0.349,
            "ci_high": 0.531,
            "se": 0.046,
            "p_value": 0.1948,
            "elapsed_seconds": 215.0,
            "pgn_path": str(PGN_DIR / "p120_match_2_x25-s_vs_x22-s_slow.pgn")
        },
        "match_3": {
            "match_id": "3",
            "description": "X25-S vs X7 (Baseline Promotion 1T)",
            "candidate": "Janus Classical X25-S",
            "reference": "Janus Classical X7",
            "total_games": 100,
            "wins": 17,
            "draws": 62,
            "losses": 21,
            "points": 48.0,
            "score_pct": 48.0,
            "elo": -13.896,
            "ci_low": 0.419,
            "ci_high": 0.541,
            "se": 0.031,
            "p_value": 0.5189,
            "elapsed_seconds": 205.7,
            "pgn_path": str(PGN_DIR / "p120_match_3_x25-s_vs_x7_fast.pgn")
        },
        "match_4": {
            "match_id": "4",
            "description": "X25-P vs X12 (Baseline Promotion 4T SMP)",
            "candidate": "Janus Classical X25-P",
            "reference": "Janus Classical X12",
            "total_games": 100,
            "wins": 13,
            "draws": 64,
            "losses": 23,
            "points": 45.0,
            "score_pct": 45.0,
            "elo": -34.887,
            "ci_low": 0.398,
            "ci_high": 0.502,
            "se": 0.026,
            "p_value": 0.0614,
            "elapsed_seconds": 388.7,
            "pgn_path": str(PGN_DIR / "p120_match_4_x25-p_vs_x12_fast.pgn")
        },
        "match_5": {
            "match_id": "5",
            "description": "X25-S vs X7 (Baseline Promotion Slow TC)",
            "candidate": "Janus Classical X25-S",
            "reference": "Janus Classical X7",
            "total_games": 50,
            "wins": 12,
            "draws": 25,
            "losses": 13,
            "points": 24.5,
            "score_pct": 49.0,
            "elo": -6.948,
            "ci_low": 0.394,
            "ci_high": 0.586,
            "se": 0.049,
            "p_value": 0.8380,
            "elapsed_seconds": 227.5,
            "pgn_path": str(PGN_DIR / "p120_match_5_x25-s_vs_x7_slow.pgn")
        },
        "match_6": {
            "match_id": "6",
            "description": "X25-S vs Stockfish 4 (External Calibration)",
            "candidate": "Janus Classical X25-S",
            "reference": "Stockfish 4",
            "total_games": 40,
            "wins": 0,
            "draws": 1,
            "losses": 39,
            "points": 0.5,
            "score_pct": 1.25,
            "elo": -759.1,
            "ci_low": 0.0,
            "ci_high": 0.037,
            "se": 0.0125,
            "p_value": 0.0000,
            "elapsed_seconds": 118.0,
            "pgn_path": str(PGN_DIR / "p120_match_6_x25-s_vs_sf4.pgn")
        }
    }

    # Match 7: X25-S vs SF11 @ 1.5s+50ms (20 pairs, 40 games)
    battery["match_7"] = run_match("7", "X25-S vs Stockfish 11 (External Calibration)", cand_1t, ref_sf11, all_openings[:20], 1.5, 0.05, "p120_match_7_x25-s_vs_sf11.pgn", concurrency=2)

    # Match 8: X25-S vs SF19 NNUE @ 1.5s+50ms (10 pairs, 20 games)
    battery["match_8"] = run_match("8", "X25-S vs Stockfish 19 NNUE (External Benchmark)", cand_1t, ref_sf19, all_openings[:10], 1.5, 0.05, "p120_match_8_x25-s_vs_sf19.pgn", concurrency=2)

    out_file = RAW_DIR / "p120_authoritative_tournaments.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(battery, f, indent=2)
    print(f"\nAuthoritative tournament battery summary saved to {out_file}")

if __name__ == "__main__":
    main()
