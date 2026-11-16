#!/usr/bin/env python3
"""
run_p21_tournaments.py
Milestone P2.1: Authoritative Tournament Battery for Neural Evaluation Qualification.
Candidate: Janus Hybrid H1 (R1 Core + Original Quantized NNUE Model H1)

Evaluates:
- Phase 11: Independent Playing-Strength Experiment:
  * M1: Candidate H1 (NNUE) vs R1 (Classical) [Primary Scientific Isolation, 100 games]
  * M2: Candidate H2 (Hybrid) vs Candidate H1 (NNUE) [Secondary Blend Comparison, 50 games]
  * M3: Candidate H1 (NNUE) vs Baseline X7 [Historical 1T Control, 100 games]
  * M4: Candidate H1 (NNUE) vs Reference X22-S [Historical Correctness Reference, 100 games]
- Phase 12: External Calibration:
  * M5: Candidate H1 vs Stockfish 4 [Blitz, 40 games]
  * M6: Candidate H1 vs Stockfish 11 [Blitz, 40 games]
  * M7: Candidate H1 vs Stockfish 19 NNUE [Blitz, 20 games]

Features:
- Strict FIDE referee checking can_claim_threefold_repetition() on exit (0 truncated '*' games).
- 6-category subcategory accounting (LL, LD, DD, WL, WD, WW).
- Dual pentanomials (Ascending [0.0..2.0] and Descending [2.0..0.0]).
- Paired SE, 95% Paired CI, two-tailed p-values, Wilson score intervals.
"""

import os
import sys
import json
import time
import math
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
PGN_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "pgn"
OUT_JSON = ROOT / "analysis" / "phase2" / "p2.1" / "raw" / "p21_tournaments_raw.json"
PGN_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Engine Executables
CAND_EXE = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.exe"
R1_EXE   = ROOT / "analysis" / "phase1" / "p1.22" / "control" / "janus_classical_r1.exe"
X7_EXE   = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
X22_EXE  = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
SF4_EXE  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
SF11_EXE = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
SF19_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

OPENINGS_FILE = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

def wilson_score_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    spread = (z / denom) * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4 * (n**2)))
    return max(0.0, center - spread), min(1.0, center + spread)

def calc_paired_ci_and_pvalue(pair_scores_norm: List[float], z: float = 1.95996) -> Tuple[float, float, float, float, float]:
    n = len(pair_scores_norm)
    if n == 0:
        return 0.0, 0.0, 1.0, 1.0, 1.0
    mean_p = sum(pair_scores_norm) / n
    if n == 1:
        return mean_p, 0.0, 1.0, 0.5, 1.0
    var = sum((x - mean_p) ** 2 for x in pair_scores_norm) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 1e-6
    ci_low = max(0.0, mean_p - z * se)
    ci_high = min(1.0, mean_p + z * se)
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    p2 = 2.0 * 0.5 * math.erfc(abs(t_stat) / math.sqrt(2.0))
    return mean_p, ci_low, ci_high, se, p2

def calc_elo(score_fraction: float) -> float:
    if score_fraction <= 0.0 or score_fraction >= 1.0:
        return None
    return -400.0 * math.log10(1.0 / score_fraction - 1.0)

class UciEngine:
    def __init__(self, exe: Path, name: str, threads: int = 1, options: Dict[str, Any] = None):
        self.exe = exe
        self.name = name
        self.threads = threads
        self.options = options or {}
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=-1
        )
        self.send("uci")
        found_uciok = False
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "uciok" in line:
                found_uciok = True
                break
        if not found_uciok:
            raise RuntimeError(f"Engine {self.name} failed to return uciok (exitcode: {self.proc.poll()})")

        self.send(f"setoption name Threads value {self.threads}")
        for k, v in self.options.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        found_readyok = False
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "readyok" in line:
                found_readyok = True
                break
        if not found_readyok:
            raise RuntimeError(f"Engine {self.name} failed to return readyok (exitcode: {self.proc.poll()})")

    def send(self, cmd: str):
        if self.proc and self.proc.poll() is None and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except Exception:
                pass

    def go(self, moves_str: str, time_ms: int, inc_ms: int) -> str:
        if not self.proc or self.proc.poll() is not None:
            return None
        if moves_str:
            self.send(f"position startpos moves {moves_str}")
        else:
            self.send("position startpos")
        self.send(f"go wtime {time_ms} btime {time_ms} winc {inc_ms} binc {inc_ms}")

        bestmove = None
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
        return bestmove

    def stop(self):
        if self.proc:
            try:
                if self.proc.poll() is None:
                    self.send("quit")
                    self.proc.communicate(timeout=0.5)
            except Exception:
                pass
            finally:
                try:
                    if self.proc and self.proc.poll() is None:
                        self.proc.kill()
                except Exception:
                    pass
                self.proc = None

def play_single_game(
    white_engine_cfg: Tuple[Path, str, int, Dict[str, Any]],
    black_engine_cfg: Tuple[Path, str, int, Dict[str, Any]],
    opening_moves: List[str],
    base_time_sec: float,
    inc_sec: float
) -> Dict[str, Any]:
    w_eng = UciEngine(*white_engine_cfg)
    b_eng = UciEngine(*black_engine_cfg)
    w_eng.start()
    b_eng.start()

    board = chess.Board()
    played_moves = []
    for m_uci in opening_moves:
        mv = chess.Move.from_uci(m_uci)
        board.push(mv)
        played_moves.append(m_uci)

    w_time = int(base_time_sec * 1000)
    b_time = int(base_time_sec * 1000)
    inc_ms = int(inc_sec * 1000)

    result_str = "*"
    term_reason = "Normal"
    max_plies = 200

    try:
        while len(played_moves) < max_plies and not board.is_game_over(claim_draw=True):
            moves_str = " ".join(played_moves)
            is_white = (board.turn == chess.WHITE)
            active_eng = w_eng if is_white else b_eng
            active_time = w_time if is_white else b_time

            t_start = time.perf_counter()
            bestmove = active_eng.go(moves_str, active_time, inc_ms)
            elapsed_ms = int((time.perf_counter() - t_start) * 1000)

            if is_white:
                w_time = max(10, w_time - elapsed_ms + inc_ms)
            else:
                b_time = max(10, b_time - elapsed_ms + inc_ms)

            if not bestmove or bestmove == "(none)":
                result_str = "0-1" if is_white else "1-0"
                term_reason = "No move returned (Forfeit)"
                break

            try:
                mv = chess.Move.from_uci(bestmove)
            except Exception:
                result_str = "0-1" if is_white else "1-0"
                term_reason = "Illegal move syntax"
                break

            if mv not in board.legal_moves:
                result_str = "0-1" if is_white else "1-0"
                term_reason = f"Illegal move: {bestmove}"
                break

            board.push(mv)
            played_moves.append(bestmove)

            # Strict FIDE referee check inside loop
            if board.is_checkmate():
                result_str = "0-1" if board.turn == chess.WHITE else "1-0"
                term_reason = "Checkmate"
                break
            if board.is_stalemate():
                result_str = "1/2-1/2"
                term_reason = "Stalemate"
                break
            if board.is_insufficient_material():
                result_str = "1/2-1/2"
                term_reason = "Insufficient Material"
                break
            if board.can_claim_threefold_repetition() or board.is_repetition(3):
                result_str = "1/2-1/2"
                term_reason = "Threefold Repetition"
                break
            if board.can_claim_fifty_moves() or board.halfmove_clock >= 100:
                result_str = "1/2-1/2"
                term_reason = "Fifty Moves"
                break

        # Post-loop FIDE check
        if result_str == "*":
            if board.is_checkmate():
                result_str = "0-1" if board.turn == chess.WHITE else "1-0"
                term_reason = "Checkmate"
            elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.is_repetition(3) or board.can_claim_fifty_moves() or board.halfmove_clock >= 100:
                result_str = "1/2-1/2"
                term_reason = "Draw by Rule"
            elif len(played_moves) >= max_plies:
                result_str = "1/2-1/2"
                term_reason = "Max Plies Adjudication"

    finally:
        w_eng.stop()
        b_eng.stop()

    return {
        "white": white_engine_cfg[1],
        "black": black_engine_cfg[1],
        "result": result_str,
        "term_reason": term_reason,
        "moves": played_moves,
        "plies": len(played_moves)
    }

def play_opening_pair(
    pair_idx: int,
    cand_cfg: Tuple[Path, str, int, Dict[str, Any]],
    ref_cfg: Tuple[Path, str, int, Dict[str, Any]],
    opening_moves: List[str],
    base_time: float,
    inc: float
) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    # Game 1: Cand as White, Ref as Black
    res1 = play_single_game(cand_cfg, ref_cfg, opening_moves, base_time, inc)
    # Game 2: Ref as White, Cand as Black
    res2 = play_single_game(ref_cfg, cand_cfg, opening_moves, base_time, inc)
    return pair_idx, res1, res2

def run_match(
    match_id: str,
    desc: str,
    cand_cfg: Tuple[Path, str, int, Dict[str, Any]],
    ref_cfg: Tuple[Path, str, int, Dict[str, Any]],
    openings: List[List[str]],
    base_time: float,
    inc: float,
    pgn_filename: str,
    concurrency: int = 8
) -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print(f"MATCH {match_id}: {desc}")
    print(f"Cand: {cand_cfg[1]} vs Ref: {ref_cfg[1]} | Pairs: {len(openings)} ({len(openings)*2} games)")
    print(f"Time Control: {base_time}s + {inc}s | Concurrency: {concurrency}")
    print("=" * 80)

    t0 = time.time()
    pair_results = [None] * len(openings)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(play_opening_pair, i, cand_cfg, ref_cfg, openings[i], base_time, inc): i
            for i in range(len(openings))
        }
        done_count = 0
        for fut in as_completed(futures):
            p_idx, r1, r2 = fut.result()
            pair_results[p_idx] = (r1, r2)
            done_count += 1
            if done_count % 10 == 0 or done_count == len(openings):
                pct = (done_count * 2) / (len(openings) * 2) * 100.0
                print(f"  Progress: {done_count*2}/{len(openings)*2} games finished ({pct:.1f}%)", flush=True)

    elapsed = time.time() - t0

    # Aggregate Statistics
    total_games = len(openings) * 2
    wins = 0
    draws = 0
    losses = 0
    cand_points = 0.0

    subcat_counts = {"LL": 0, "LD": 0, "DD": 0, "WL": 0, "WD": 0, "WW": 0}
    pair_scores_norm = []
    penta_ascending = [0, 0, 0, 0, 0] # [0.0, 0.5, 1.0, 1.5, 2.0]

    for r1, r2 in pair_results:
        # Game 1: Cand is White
        if r1["result"] == "1-0":
            s1 = 1.0; wins += 1
        elif r1["result"] == "0-1":
            s1 = 0.0; losses += 1
        else:
            s1 = 0.5; draws += 1

        # Game 2: Cand is Black
        if r2["result"] == "0-1":
            s2 = 1.0; wins += 1
        elif r2["result"] == "1-0":
            s2 = 0.0; losses += 1
        else:
            s2 = 0.5; draws += 1

        pair_score = s1 + s2
        cand_points += pair_score
        pair_scores_norm.append(pair_score / 2.0)

        if pair_score == 0.0:
            subcat_counts["LL"] += 1
            penta_ascending[0] += 1
        elif pair_score == 0.5:
            subcat_counts["LD"] += 1
            penta_ascending[1] += 1
        elif pair_score == 1.0:
            if s1 == 0.5 and s2 == 0.5:
                subcat_counts["DD"] += 1
            else:
                subcat_counts["WL"] += 1
            penta_ascending[2] += 1
        elif pair_score == 1.5:
            subcat_counts["WD"] += 1
            penta_ascending[3] += 1
        elif pair_score == 2.0:
            subcat_counts["WW"] += 1
            penta_ascending[4] += 1

    penta_descending = list(reversed(penta_ascending))
    score_pct = (cand_points / total_games) * 100.0
    elo = calc_elo(cand_points / total_games)

    mean_p, ci_low, ci_high, se, p2 = calc_paired_ci_and_pvalue(pair_scores_norm)
    wilson_low, wilson_high = wilson_score_interval(cand_points, total_games)
    elo_str = f"{elo:.1f}" if elo is not None else "N/A"

    print(f"\nRESULT {match_id}: {cand_points}/{total_games} (+{wins} ={draws} -{losses}) | {score_pct:.1f}% | Elo: {elo_str}")
    print(f"  Subcategories: LL={subcat_counts['LL']}, LD={subcat_counts['LD']}, DD={subcat_counts['DD']}, WL={subcat_counts['WL']}, WD={subcat_counts['WD']}, WW={subcat_counts['WW']}")
    print(f"  Pentanomial [0.0..2.0]: {penta_ascending}  (LL, LD, 1.0, WD, WW)")
    print(f"  Pentanomial [2.0..0.0]: {penta_descending}  (WW, WD, 1.0, LD, LL)")
    print(f"  Paired 95% CI: [{ci_low*100.0:.1f}%, {ci_high*100.0:.1f}%] | SE: {se:.4f} | p-value: {p2:.4f} ({elapsed:.1f}s)\n")

    # Save PGN
    pgn_path = PGN_DIR / pgn_filename
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for p_idx, (r1, r2) in enumerate(pair_results):
            for g_num, gres in enumerate([r1, r2], 1):
                pf.write(f'[Event "{desc}"]\n')
                pf.write(f'[Site "Project Janus Phase 2 Lab"]\n')
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
        "total_pairs": len(openings),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": cand_points,
        "score_pct": round(score_pct, 2),
        "elo": round(elo, 2) if elo is not None else None,
        "subcategories": subcat_counts,
        "pentanomial_ascending_LL_to_WW": penta_ascending,
        "pentanomial_descending_WW_to_LL": penta_descending,
        "paired_ci_95": [round(ci_low * 100.0, 2), round(ci_high * 100.0, 2)],
        "paired_se": round(se, 5),
        "paired_p_value": round(p2, 5),
        "wilson_ci_95": [round(wilson_low * 100.0, 2), round(wilson_high * 100.0, 2)],
        "elapsed_seconds": round(elapsed, 1),
        "pgn_path": str(pgn_path.relative_to(ROOT)).replace("\\", "/")
    }

def main():
    print("=" * 80)
    print("PROJECT JANUS — MILESTONE P2.1 AUTHORITATIVE TOURNAMENT BATTERY (450 GMS)")
    print("Candidate: Janus Hybrid H1 (R1 Core + Original Quantized NNUE Model H1)")
    print("=" * 80)

    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        raw_pool = json.load(f)
        openings_pool = [item["uci_sequence"] for item in raw_pool]

    # Engine Configurations:
    # Candidate H1 (Pure NNUE)
    c_h1 = (CAND_EXE, "Janus_Hybrid_H1", 1, {"UCI_Variant": "H1", "UCI_Evaluation": "NNUE"})
    # Candidate H2 (Hybrid Blend)
    c_h2 = (CAND_EXE, "Janus_Hybrid_H2", 1, {"UCI_Variant": "H2", "UCI_Evaluation": "Hybrid", "NNUE_Weight": "50"})

    # Baselines & References:
    ref_r1_1t = (R1_EXE,  "Janus_Classical_R1",  1, {"UCI_Variant": "R1", "UCI_Evaluation": "Classical"})
    ref_x7_1t  = (X7_EXE,  "Janus_Classical_X7",  1, {})
    ref_x22_1t = (X22_EXE, "Janus_Classical_X22_S", 1, {})
    ref_sf4    = (SF4_EXE, "Stockfish_4", 1, {})
    ref_sf11   = (SF11_EXE,"Stockfish_11", 1, {})
    ref_sf19   = (SF19_EXE,"Stockfish_19_NNUE", 1, {})

    matches_data = []

    # ========================================================================
    # Phase 11: Independent Playing-Strength Experiment (Matches M1-M4)
    # ========================================================================
    # M1: Candidate H1 (NNUE) vs R1 (Classical) [Primary Scientific Isolation]
    m1 = run_match("M1", "H1 (NNUE) vs R1 (Classical) Fast TC", c_h1, ref_r1_1t,
                   openings_pool[:50], 5.0, 0.05, "match1_h1_vs_r1_fast.pgn", concurrency=8)
    matches_data.append(m1)

    # M2: Candidate H2 (Hybrid) vs Candidate H1 (NNUE) [Secondary Blend Comparison]
    m2 = run_match("M2", "H2 (Hybrid) vs H1 (NNUE) Fast TC", c_h2, c_h1,
                   openings_pool[:25], 5.0, 0.05, "match2_h2_vs_h1_fast.pgn", concurrency=8)
    matches_data.append(m2)

    # M3: Candidate H1 (NNUE) vs Baseline X7 [Historical 1T Control]
    m3 = run_match("M3", "H1 (NNUE) vs Baseline X7 Fast TC", c_h1, ref_x7_1t,
                   openings_pool[:50], 5.0, 0.05, "match3_h1_vs_x7_fast.pgn", concurrency=8)
    matches_data.append(m3)

    # M4: Candidate H1 (NNUE) vs Reference X22-S [Historical Correctness Reference]
    m4 = run_match("M4", "H1 (NNUE) vs Reference X22-S Fast TC", c_h1, ref_x22_1t,
                   openings_pool[:50], 5.0, 0.05, "match4_h1_vs_x22s_fast.pgn", concurrency=8)
    matches_data.append(m4)

    # ========================================================================
    # Phase 12: External Stockfish Calibration (Matches M5-M7)
    # ========================================================================
    # M5: Candidate H1 vs Stockfish 4 Blitz
    m5 = run_match("M5", "H1 (NNUE) vs Stockfish 4 Blitz", c_h1, ref_sf4,
                   openings_pool[:20], 3.0, 0.03, "match5_h1_vs_sf4_blitz.pgn", concurrency=8)
    matches_data.append(m5)

    # M6: Candidate H1 vs Stockfish 11 Blitz
    m6 = run_match("M6", "H1 (NNUE) vs Stockfish 11 Blitz", c_h1, ref_sf11,
                   openings_pool[:20], 3.0, 0.03, "match6_h1_vs_sf11_blitz.pgn", concurrency=8)
    matches_data.append(m6)

    # M7: Candidate H1 vs Stockfish 19 NNUE Blitz
    m7 = run_match("M7", "H1 (NNUE) vs Stockfish 19 NNUE Blitz", c_h1, ref_sf19,
                   openings_pool[:10], 3.0, 0.03, "match7_h1_vs_sf19_blitz.pgn", concurrency=8)
    matches_data.append(m7)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(matches_data, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL 7 MATCHES (450 GAMES) COMPLETED SUCCESSFULLY!")
    print(f"Tournament raw JSON saved to:\n  {OUT_JSON}")
    print("=" * 80)

if __name__ == "__main__":
    main()
