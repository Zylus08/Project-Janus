#!/usr/bin/env python3
"""
run_p121_tournaments.py
Milestone P1.21 Authoritative Independent Tournament Battery & External Calibration.

Authoritative Battery (Phase 13):
  Match 1: Candidate X26-S (1T) vs Reference X22-S (1T)       [50 pairs, 100 games @ 1.0s + 50ms]
  Match 2: Candidate X26-S (1T) vs Reference X22-S (1T)       [25 pairs,  50 games @ 3.0s + 100ms]
  Match 3: Candidate X26-S (1T) vs Janus Classical X7 (1T)    [50 pairs, 100 games @ 1.0s + 50ms]
  Match 4: Candidate X26-S (1T) vs Janus Classical X7 (1T)    [25 pairs,  50 games @ 3.0s + 100ms]
  Match 5: Candidate X26-P (4T) vs Janus Classical X12 (4T)   [50 pairs, 100 games @ 1.0s + 50ms]

External Calibration (Phase 14):
  Match 6: Candidate X26-S (1T) vs Stockfish 4 (1T)          [20 pairs,  40 games @ 1.5s + 50ms]
  Match 7: Candidate X26-S (1T) vs Stockfish 11 (1T)         [20 pairs,  40 games @ 1.5s + 50ms]
  Match 8: Candidate X26-S (1T) vs Stockfish 19 NNUE (1T)    [10 pairs,  20 games @ 1.5s + 50ms]

Total: 500 authoritative games.
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

EXE_X26 = ROOT / "analysis" / "phase1" / "p1.21" / "control" / "janus_classical_x26.exe"
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7"  / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3"  / "control" / "janus_classical_x7.exe"

EXE_SF4  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.21" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.21" / "pgn"
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

def calc_pentanomial(pair_scores: List[float]) -> List[int]:
    penta = [0, 0, 0, 0, 0] # 0.0, 0.5, 1.0, 1.5, 2.0 (total points in pair)
    for s in pair_scores:
        tot = round(s * 2.0)
        if 0 <= tot <= 4:
            penta[tot] += 1
    return penta

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
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(0.1)

    def send(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def set_position(self, moves: List[str]):
        if moves:
            self.send(f"position startpos moves {' '.join(moves)}")
        else:
            self.send("position startpos")

    def go(self, wtime_ms: int, btime_ms: int, winc_ms: int, binc_ms: int) -> str:
        self.send(f"go wtime {wtime_ms} btime {btime_ms} winc {winc_ms} binc {binc_ms}")
        bestmove = ""
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break
        return bestmove

    def quit(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.wait(timeout=0.5)
            except Exception:
                self.proc.kill()
            self.proc = None

def play_game(w_cfg: Tuple[Path, str, int, Dict[str, Any]], b_cfg: Tuple[Path, str, int, Dict[str, Any]], opening_moves: List[str], base_sec: float, inc_sec: float, max_moves: int = 150) -> Dict[str, Any]:
    w_exe, w_name, w_th, w_opt = w_cfg
    b_exe, b_name, b_th, b_opt = b_cfg

    w_engine = UciEngine(w_exe, w_name, w_th, w_opt)
    b_engine = UciEngine(b_exe, b_name, b_th, b_opt)
    w_engine.start()
    b_engine.start()

    board = chess.Board()
    moves = []
    for m_str in opening_moves:
        mv = chess.Move.from_uci(m_str)
        if mv in board.legal_moves:
            board.push(mv)
            moves.append(m_str)
        else:
            break

    w_time = int(base_sec * 1000)
    b_time = int(base_sec * 1000)
    w_inc = int(inc_sec * 1000)
    b_inc = int(inc_sec * 1000)

    result = "*"
    term_reason = ""

    while not board.is_game_over(claim_draw=True) and len(moves) < max_moves:
        is_white = (board.turn == chess.WHITE)
        eng = w_engine if is_white else b_engine

        eng.set_position(moves)
        t_start = time.perf_counter()
        bm = eng.go(w_time, b_time, w_inc, b_inc)
        t_elapsed = time.perf_counter() - t_start
        elapsed_ms = int(t_elapsed * 1000)

        if is_white:
            w_time = max(1, w_time - elapsed_ms + w_inc)
        else:
            b_time = max(1, b_time - elapsed_ms + b_inc)

        if not bm or bm == "(none)":
            result = "0-1" if is_white else "1-0"
            term_reason = "engine_stall_or_null"
            break

        try:
            mv = chess.Move.from_uci(bm)
        except Exception:
            result = "0-1" if is_white else "1-0"
            term_reason = "illegal_uci_format"
            break

        if mv not in board.legal_moves:
            result = "0-1" if is_white else "1-0"
            term_reason = f"illegal_move_{bm}"
            break

        board.push(mv)
        moves.append(bm)

    if result == "*":
        if board.is_checkmate():
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            term_reason = "checkmate"
        elif board.is_stalemate():
            result = "1/2-1/2"
            term_reason = "stalemate"
        elif board.is_insufficient_material():
            result = "1/2-1/2"
            term_reason = "insufficient_material"
        elif board.is_fifty_moves():
            result = "1/2-1/2"
            term_reason = "fifty_moves"
        elif board.is_repetition(3):
            result = "1/2-1/2"
            term_reason = "threefold_repetition"
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

def run_match(match_id: str, desc: str, cand_cfg: Tuple[Path, str, int, Dict[str, Any]], ref_cfg: Tuple[Path, str, int, Dict[str, Any]], openings: List[Dict[str, Any]], base_sec: float, inc_sec: float, pgn_name: str, concurrency: int = 8) -> Dict[str, Any]:
    print("\n" + "=" * 75)
    print(f"MATCH {match_id}: {desc}")
    print(f"Cand: {cand_cfg[1]} ({cand_cfg[2]}T) vs Ref: {ref_cfg[1]} ({ref_cfg[2]}T) | Pairs: {len(openings)} ({len(openings)*2} games)")
    print(f"Time Control: {base_sec}s + {int(inc_sec*1000)}ms | Concurrency: {concurrency}")
    print("=" * 75)

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
    pentanomial = calc_pentanomial(pair_scores)
    elapsed = time.time() - t0

    elo_str = f"{elo:+.1f}" if elo is not None else ("-inf" if cand_points == 0 else "+inf")
    print(f"RESULT: {cand_points}/{total_games} (+{wins} ={draws} -{losses}) | {pct:.1f}% | Elo: {elo_str} | CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%] | Pentanomial: {pentanomial} | p2: {p2:.4f} ({elapsed:.1f}s)")

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
        "pentanomial": pentanomial,
        "elapsed_seconds": elapsed,
        "pgn_path": str(pgn_path)
    }

def main():
    print("==========================================================================")
    print("PROJECT JANUS — MILESTONE P1.21 AUTHORITATIVE TOURNAMENT BATTERY (500 GMS)")
    print("Candidate: Janus Classical X26 (Option A RFP Correctness Repair)")
    print("==========================================================================")

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings_pool = json.load(f)

    # Prepare opening slices
    pool_50 = openings_pool[:50]
    pool_25 = openings_pool[:25]
    pool_20 = openings_pool[:20]
    pool_10 = openings_pool[:10]

    # Engine configs
    cfg_x26_s = (EXE_X26, "Janus_Classical_X26_S", 1, {"UCI_Variant": "X26", "UCI_RfpRepair": "true"})
    cfg_x26_p = (EXE_X26, "Janus_Classical_X26_P", 4, {"UCI_Variant": "X26", "UCI_RfpRepair": "true"})

    cfg_x22_s = (EXE_X22, "Janus_Classical_X22_S", 1, {"UCI_Variant": "X22"})
    cfg_x7_s  = (EXE_X7,  "Janus_Classical_X7",    1, {})
    cfg_x12_p = (EXE_X12, "Janus_Classical_X12",   4, {})

    cfg_sf4   = (EXE_SF4,  "Stockfish_4",           1, {})
    cfg_sf11  = (EXE_SF11, "Stockfish_11",          1, {})
    cfg_sf19  = (EXE_SF19, "Stockfish_19_NNUE",     1, {})

    all_matches = []

    # -------------------------------------------------------------------------
    # PHASE 13: INDEPENDENT COMPETITIVE QUALIFICATION (400 Games)
    # -------------------------------------------------------------------------
    # Match 1: X26-S vs X22-S Fast TC (100 games)
    m1 = run_match("M1", "X26-S vs Reference X22-S Fast TC", cfg_x26_s, cfg_x22_s, pool_50, 1.0, 0.05, "match1_x26s_vs_x22s_fast.pgn", concurrency=8)
    all_matches.append(m1)

    # Match 2: X26-S vs Reference X22-S Slow TC (50 games)
    m2 = run_match("M2", "X26-S vs Reference X22-S Slow TC", cfg_x26_s, cfg_x22_s, pool_25, 3.0, 0.10, "match2_x26s_vs_x22s_slow.pgn", concurrency=8)
    all_matches.append(m2)

    # Match 3: X26-S vs Baseline X7 Fast TC (100 games)
    m3 = run_match("M3", "X26-S vs Baseline X7 Fast TC", cfg_x26_s, cfg_x7_s, pool_50, 1.0, 0.05, "match3_x26s_vs_x7_fast.pgn", concurrency=8)
    all_matches.append(m3)

    # Match 4: X26-S vs Baseline X7 Slow TC (50 games)
    m4 = run_match("M4", "X26-S vs Baseline X7 Slow TC", cfg_x26_s, cfg_x7_s, pool_25, 3.0, 0.10, "match4_x26s_vs_x7_slow.pgn", concurrency=8)
    all_matches.append(m4)

    # Match 5: X26-P (4T) vs Baseline X12 (4T) Fast TC (100 games)
    m5 = run_match("M5", "X26-P vs Baseline X12 Fast TC", cfg_x26_p, cfg_x12_p, pool_50, 1.0, 0.05, "match5_x26p_vs_x12_fast.pgn", concurrency=4)
    all_matches.append(m5)

    # -------------------------------------------------------------------------
    # PHASE 14: EXTERNAL CALIBRATION (100 Games)
    # -------------------------------------------------------------------------
    # Match 6: X26-S vs Stockfish 4 Blitz (40 games)
    m6 = run_match("M6", "X26-S vs Stockfish 4 Blitz", cfg_x26_s, cfg_sf4, pool_20, 1.5, 0.05, "match6_x26s_vs_sf4_blitz.pgn", concurrency=8)
    all_matches.append(m6)

    # Match 7: X26-S vs Stockfish 11 Blitz (40 games)
    m7 = run_match("M7", "X26-S vs Stockfish 11 Blitz", cfg_x26_s, cfg_sf11, pool_20, 1.5, 0.05, "match7_x26s_vs_sf11_blitz.pgn", concurrency=8)
    all_matches.append(m7)

    # Match 8: X26-S vs Stockfish 19 NNUE Blitz (20 games)
    m8 = run_match("M8", "X26-S vs Stockfish 19 NNUE Blitz", cfg_x26_s, cfg_sf19, pool_10, 1.5, 0.05, "match8_x26s_vs_sf19_blitz.pgn", concurrency=8)
    all_matches.append(m8)

    # Write raw output
    out_file = RAW_DIR / "independent_strength_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_matches, f, indent=2)

    print("\n" + "=" * 75)
    print("ALL 500 TOURNAMENT GAMES COMPLETED SUCCESSFULLY!")
    print(f"Data saved to: {out_file}")
    print(f"PGNs saved to: {PGN_DIR}")
    print("=" * 75)

if __name__ == "__main__":
    main()
