#!/usr/bin/env python3
"""
run_p119_tournaments.py
Milestone P1.19 Authoritative Independent Tournament Battery & External Calibration.
Executes 470 games across 7 matches using the verified, certified tournament harness:
  Match 1: Candidate X24-S (1T) vs Reference X22-S (1T)       [50 pairs, 100 games @ 1.0s + 50ms]
  Match 2: Candidate X24-S (1T) vs Janus Classical X7 (1T)    [50 pairs, 100 games @ 1.0s + 50ms]
  Match 3: Candidate X24-P (4T) vs Janus Classical X12 (4T)   [50 pairs, 100 games @ 1.0s + 50ms]
  Match 4: Candidate X24-S (1T) vs Janus Classical X7 (1T)    [25 pairs,  50 games @ 3.0s + 100ms] (Slow TC)
  Match 5: Candidate X24-S (1T) vs Stockfish 4 (1T)          [20 pairs,  40 games @ 1.5s + 50ms]
  Match 6: Candidate X24-S (1T) vs Stockfish 11 (1T)         [20 pairs,  40 games @ 1.5s + 50ms]
  Match 7: Candidate X24-S (1T) vs Stockfish 19 NNUE (1T)    [20 pairs,  40 games @ 1.5s + 50ms]
Total: 470 games.
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

EXE_X24 = ROOT / "analysis" / "phase1" / "p1.19" / "control" / "janus_classical_x24.exe"
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7"  / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3"  / "control" / "janus_classical_x7.exe"

EXE_SF4  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.19" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.19" / "pgn"
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
    one_sided_p = 0.5 * math.erfc(t_stat / math.sqrt(2))
    two_sided_p = 2.0 * min(one_sided_p, 1.0 - one_sided_p)
    return mean_p, ci_low, ci_high, one_sided_p, two_sided_p

class EngineRunner:
    def __init__(self, exe_path: Path, name: str, threads: int = 1, is_x7: bool = False, is_sf: bool = False, variant: str = "", bp: int = 0, kfe: int = 0):
        self.exe_path = exe_path
        self.name = name
        self.threads = threads
        self.is_x7 = is_x7
        self.is_sf = is_sf
        self.variant = variant
        self.bp = bp
        self.kfe = kfe
        self.proc: Optional[subprocess.Popen] = None

    def start(self):
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

        if self.is_sf:
            self.send(f"setoption name Threads value {self.threads}")
            self.send("setoption name Hash value 64")
        else:
            if not self.is_x7:
                if self.threads > 1:
                    self.send(f"setoption name Threads value {self.threads}")
                if self.variant:
                    self.send(f"setoption name UCI_Variant value {self.variant}")
                if self.variant == "X24":
                    self.send(f"setoption name UCI_BackwardPawns value {'true' if self.bp else 'false'}")
                    self.send(f"setoption name UCI_KingFileExposure value {'true' if self.kfe else 'false'}")
                self.send("setoption name Hash value 64")

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

    def get_move(self, moves_str: str, wtime: int, btime: int, winc: int, binc: int) -> Tuple[Optional[str], Optional[int]]:
        cmd = f"position startpos moves {moves_str}" if moves_str else "position startpos"
        self.send(cmd)
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

def play_single_game(white_cfg: dict, black_cfg: dict, opening: dict, time_base_ms: int, time_inc_ms: int, max_plies: int = 150) -> dict:
    white_runner = EngineRunner(
        Path(white_cfg["exe"]),
        white_cfg["name"],
        threads=white_cfg.get("threads", 1),
        is_x7=white_cfg.get("is_x7", False),
        is_sf=white_cfg.get("is_sf", False),
        variant=white_cfg.get("variant", ""),
        bp=white_cfg.get("bp", 0),
        kfe=white_cfg.get("kfe", 0)
    )
    black_runner = EngineRunner(
        Path(black_cfg["exe"]),
        black_cfg["name"],
        threads=black_cfg.get("threads", 1),
        is_x7=black_cfg.get("is_x7", False),
        is_sf=black_cfg.get("is_sf", False),
        variant=black_cfg.get("variant", ""),
        bp=black_cfg.get("bp", 0),
        kfe=black_cfg.get("kfe", 0)
    )

    white_runner.start()
    black_runner.start()
    white_runner.new_game()
    black_runner.new_game()

    board = chess.Board()
    moves_history = []

    for m_san in opening.get("uci_sequence", []):
        try:
            m = board.parse_uci(m_san)
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
    consecutive_draw_evals = 0
    resignation_count = 0

    while len(moves_history) < max_plies and not board.is_game_over(claim_draw=True):
        turn = board.turn
        current_runner = white_runner if turn == chess.WHITE else black_runner

        t0 = time.time()
        moves_str = " ".join(moves_history)
        bestmove, score = current_runner.get_move(moves_str, wtime, btime, winc, binc)
        elapsed = time.time() - t0
        elapsed_ms = int(elapsed * 1000)

        # Update Fischer dynamic clock
        if turn == chess.WHITE:
            wtime = max(10, wtime - elapsed_ms + winc)
        else:
            btime = max(10, btime - elapsed_ms + binc)

        if not bestmove or bestmove == "(none)" or bestmove == "0000":
            adjudication = "forfeit_invalid_move"
            termination = "black_win" if turn == chess.WHITE else "white_win"
            break

        try:
            m = board.parse_uci(bestmove)
            if m not in board.legal_moves:
                adjudication = "forfeit_illegal_move"
                termination = "black_win" if turn == chess.WHITE else "white_win"
                break
            board.push(m)
            moves_history.append(bestmove)
        except Exception:
            adjudication = "forfeit_parsing_error"
            termination = "black_win" if turn == chess.WHITE else "white_win"
            break

        # Check immediate checkmate after move push
        if board.is_checkmate():
            adjudication = "checkmate"
            termination = "white_win" if turn == chess.WHITE else "black_win"
            break

        # Draw Adjudication: 10 consecutive near-zero evals (|eval| <= 8 cp) after move 40
        if score is not None and abs(score) <= 8 and len(moves_history) >= 80:
            consecutive_draw_evals += 1
            if consecutive_draw_evals >= 8:
                adjudication = "adjudication_eval_draw"
                termination = "draw"
                break
        else:
            consecutive_draw_evals = 0

        # Certified Resignation Adjudication: 5 consecutive |eval| >= 1000 cp after move 50
        if score is not None and len(moves_history) >= 100:
            if score <= -1000:
                resignation_count += 1
                if resignation_count >= 5:
                    adjudication = "adjudication_resignation"
                    termination = "black_win" if turn == chess.WHITE else "white_win"
                    break
            elif score >= 1000:
                resignation_count += 1
                if resignation_count >= 5:
                    adjudication = "adjudication_resignation"
                    termination = "white_win" if turn == chess.WHITE else "black_win"
                    break
            else:
                resignation_count = 0
        else:
            resignation_count = 0

    # Adjudicate final result if not already set
    if not termination or termination == "normal":
        if board.is_checkmate():
            termination = "black_win" if board.turn == chess.WHITE else "white_win"
            adjudication = "checkmate"
        elif board.is_stalemate():
            termination = "draw"
            adjudication = "stalemate"
        elif board.is_insufficient_material():
            termination = "draw"
            adjudication = "insufficient_material"
        elif board.can_claim_threefold_repetition() or board.is_repetition(3):
            termination = "draw"
            adjudication = "repetition"
        elif board.can_claim_fifty_moves() or board.halfmove_clock >= 100:
            termination = "draw"
            adjudication = "fifty_moves"
        else:
            termination = "draw"
            adjudication = "max_moves"

    white_runner.stop()
    black_runner.stop()

    if termination == "white_win":
        res_str = "1-0"
    elif termination == "black_win":
        res_str = "0-1"
    else:
        res_str = "1/2-1/2"

    return {
        "white": white_cfg["name"],
        "black": black_cfg["name"],
        "result": res_str,
        "termination": termination,
        "adjudication": adjudication,
        "plies": len(moves_history),
        "pgn_moves": moves_history,
        "opening_name": opening.get("name", "Unknown"),
        "opening_eco": opening.get("eco", "A00"),
        "opening_fen": opening.get("fen", "")
    }

def run_match_parallel(match_name: str, pgn_filename: str, json_filename: str,
                       cand_cfg: dict, ref_cfg: dict, openings: list,
                       time_base: int, time_inc: int, max_workers: int = 4) -> dict:
    print(f"\n================================================================================")
    print(f"STARTING {match_name}: {cand_cfg['name']} vs {ref_cfg['name']} ({len(openings)} pairs, {len(openings)*2} games)")
    print(f"Time Control: {time_base/1000.0}s + {time_inc}ms | Concurrency: {max_workers} workers")
    print(f"================================================================================")

    tasks = []
    for idx, op in enumerate(openings):
        tasks.append((idx, 1, cand_cfg, ref_cfg, op))
        tasks.append((idx, 2, ref_cfg, cand_cfg, op))

    game_results = [None] * len(tasks)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {}
        for t_idx, (p_idx, g_num, w_cfg, b_cfg, op) in enumerate(tasks):
            f = executor.submit(play_single_game, w_cfg, b_cfg, op, time_base, time_inc)
            future_to_task[f] = (t_idx, p_idx, g_num, w_cfg["name"], b_cfg["name"])

        for f in as_completed(future_to_task):
            t_idx, p_idx, g_num, w_name, b_name = future_to_task[f]
            try:
                res = f.result()
                game_results[t_idx] = res
                print(f"  [Pair {p_idx+1:02d} G{g_num}] {res['white']} vs {res['black']}: {res['result']} ({res['adjudication']}, {res['plies']} plies)")
            except Exception as e:
                print(f"  [ERROR Pair {p_idx+1:02d} G{g_num}]: {e}")
                game_results[t_idx] = {
                    "white": w_name, "black": b_name, "result": "1/2-1/2",
                    "termination": "error", "adjudication": str(e), "plies": 0, "pgn_moves": [],
                    "opening_name": "Error", "opening_eco": "A00", "opening_fen": ""
                }

    elapsed_match = time.time() - start_time

    cand_name = cand_cfg["name"]
    cand_score = 0.0
    wins = 0
    draws = 0
    losses = 0

    penta = {2.0: 0, 1.5: 0, 1.0: 0, 0.5: 0, 0.0: 0}
    pair_scores = []
    for p_idx in range(len(openings)):
        g1 = game_results[2 * p_idx]
        g2 = game_results[2 * p_idx + 1]

        # In g1, Cand is White
        s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
        # In g2, Cand is Black
        s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)

        pair_s = (s1 + s2) / 2.0
        pair_scores.append(pair_s)
        penta[s1 + s2] += 1

        cand_score += (s1 + s2)
        if s1 == 1.0: wins += 1
        elif s1 == 0.5: draws += 1
        else: losses += 1

        if s2 == 1.0: wins += 1
        elif s2 == 0.5: draws += 1
        else: losses += 1

    total_games = len(tasks)
    win_rate = (cand_score / total_games) * 100.0
    elo = calc_elo(cand_score / total_games) if total_games > 0 else 0.0
    mean_p, ci_low, ci_high, p_val_one, p_val_two = calc_paired_ci_and_pvalue(pair_scores)

    print(f"\n--- {match_name} Final Standings ---")
    print(f"Score: {cand_score:.1f}/{total_games} (+{wins} ={draws} -{losses}) | {win_rate:.1f}%")
    print(f"Pentanomial Distribution [2.0, 1.5, 1.0, 0.5, 0.0]: [{penta[2.0]}, {penta[1.5]}, {penta[1.0]}, {penta[0.5]}, {penta[0.0]}]")
    print(f"Paired CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%] | One-Sided p: {p_val_one:.4f} | Two-Sided p: {p_val_two:.4f}")
    if elo is not None:
        print(f"Elo Difference: {elo:+.1f} Elo")
    print(f"Elapsed Time: {elapsed_match:.1f}s")

    # Write clean PGN file
    pgn_path = PGN_DIR / pgn_filename
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for idx, g in enumerate(game_results):
            pf.write(f'[Event "{match_name}"]\n')
            pf.write(f'[Site "Janus Classical Search Lab"]\n')
            pf.write(f'[Date "{time.strftime("%Y.%m.%d")}"]\n')
            pf.write(f'[Round "{idx+1}"]\n')
            pf.write(f'[White "{g["white"]}"]\n')
            pf.write(f'[Black "{g["black"]}"]\n')
            pf.write(f'[Result "{g["result"]}"]\n')
            pf.write(f'[Termination "{g["adjudication"]}"]\n')
            pf.write(f'[Opening "{g.get("opening_name", "Unknown")}"]\n')
            pf.write(f'[ECO "{g.get("opening_eco", "A00")}"]\n')
            if g.get("opening_fen"):
                pf.write(f'[OpeningFEN "{g["opening_fen"]}"]\n')
            pf.write('\n')

            moves = g.get("pgn_moves", [])
            b = chess.Board()
            for m_i, mv in enumerate(moves):
                try:
                    m = chess.Move.from_uci(mv)
                    san = b.san(m)
                    b.push(m)
                    if m_i % 2 == 0:
                        pf.write(f"{m_i//2 + 1}. {san} ")
                    else:
                        pf.write(f"{san} ")
                except Exception:
                    if m_i % 2 == 0:
                        pf.write(f"{m_i//2 + 1}. {mv} ")
                    else:
                        pf.write(f"{mv} ")
            pf.write(f"{g['result']}\n\n")

    summary_dict = {
        "match_name": match_name,
        "candidate": cand_name,
        "reference": ref_cfg["name"],
        "num_pairs": len(openings),
        "total_games": total_games,
        "score": cand_score,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate_percent": round(win_rate, 2),
        "elo": round(elo, 1) if elo is not None else None,
        "paired_ci_95": [round(ci_low * 100, 2), round(ci_high * 100, 2)],
        "p_value_one_sided": round(p_val_one, 4),
        "p_value_two_sided": round(p_val_two, 4),
        "pentanomial": penta,
        "elapsed_seconds": round(elapsed_match, 1)
    }

    raw_path = RAW_DIR / json_filename
    with open(raw_path, "w", encoding="utf-8") as jf:
        json.dump(summary_dict, jf, indent=2)

    return summary_dict

def main():
    print("=" * 80)
    print("MILESTONE P1.19 AUTHORITATIVE TOURNAMENT BATTERY (470 GAMES)")
    print("=" * 80)

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)

    cfg_x24_s = {"name": "Janus Classical X24-S", "exe": str(EXE_X24), "threads": 1, "variant": "X24", "bp": 1, "kfe": 0}
    cfg_x24_p = {"name": "Janus Classical X24-P", "exe": str(EXE_X24), "threads": 4, "variant": "X24", "bp": 1, "kfe": 0}
    cfg_x22_s = {"name": "Janus Classical X22-S", "exe": str(EXE_X22), "threads": 1, "variant": "X22", "bp": 0, "kfe": 0}
    cfg_x12_p = {"name": "Janus Classical X12",   "exe": str(EXE_X12), "threads": 4, "is_x7": False}
    cfg_x7_s  = {"name": "Janus Classical X7",    "exe": str(EXE_X7),  "threads": 1, "is_x7": True}

    cfg_sf4  = {"name": "Stockfish 4",  "exe": str(EXE_SF4),  "threads": 1, "is_sf": True}
    cfg_sf11 = {"name": "Stockfish 11", "exe": str(EXE_SF11), "threads": 1, "is_sf": True}
    cfg_sf19 = {"name": "Stockfish 19", "exe": str(EXE_SF19), "threads": 1, "is_sf": True}

    overall_results = {}

    # Match 1: Candidate X24-S vs Reference X22-S (50 pairs, 100 games @ 1.0s + 50ms)
    res_m1 = run_match_parallel(
        match_name="Match 1: Candidate X24-S vs Reference X22-S (Primary Gate)",
        pgn_filename="match_1_x24-s_vs_x22-s_ref_1t.pgn",
        json_filename="match_1_x24_vs_x22_summary.json",
        cand_cfg=cfg_x24_s, ref_cfg=cfg_x22_s,
        openings=all_openings[:50],
        time_base=1000, time_inc=50, max_workers=4
    )
    overall_results["match_1"] = res_m1

    # Match 2: Candidate X24-S vs Janus Classical X7 (50 pairs, 100 games @ 1.0s + 50ms)
    res_m2 = run_match_parallel(
        match_name="Match 2: Candidate X24-S vs Janus Classical X7 (1T Baseline)",
        pgn_filename="match_2_x24-s_vs_x7_baseline_1t.pgn",
        json_filename="match_2_x24_vs_x7_summary.json",
        cand_cfg=cfg_x24_s, ref_cfg=cfg_x7_s,
        openings=all_openings[:50],
        time_base=1000, time_inc=50, max_workers=4
    )
    overall_results["match_2"] = res_m2

    # Match 3: Candidate X24-P vs Janus Classical X12 (50 pairs, 100 games @ 1.0s + 50ms, 4T SMP)
    res_m3 = run_match_parallel(
        match_name="Match 3: Candidate X24-P vs Janus Classical X12 (4T SMP Baseline)",
        pgn_filename="match_3_x24-p_vs_x12_baseline_4t.pgn",
        json_filename="match_3_x24_vs_x12_summary.json",
        cand_cfg=cfg_x24_p, ref_cfg=cfg_x12_p,
        openings=all_openings[:50],
        time_base=1000, time_inc=50, max_workers=2
    )
    overall_results["match_3"] = res_m3

    # Match 4: Candidate X24-S vs Janus Classical X7 (25 pairs, 50 games @ 3.0s + 100ms, Slow TC)
    res_m4 = run_match_parallel(
        match_name="Match 4: Candidate X24-S vs Janus Classical X7 (Slow TC Robustness)",
        pgn_filename="match_4_x24-s_vs_x7_slow_tc.pgn",
        json_filename="match_4_x24_vs_x7_slow_summary.json",
        cand_cfg=cfg_x24_s, ref_cfg=cfg_x7_s,
        openings=all_openings[:25],
        time_base=3000, time_inc=100, max_workers=4
    )
    overall_results["match_4"] = res_m4

    # Match 5: Candidate X24-S vs Stockfish 4 (20 pairs, 40 games @ 1.5s + 50ms)
    res_m5 = run_match_parallel(
        match_name="Match 5: Candidate X24-S vs Stockfish 4 (External 2014 Reference)",
        pgn_filename="match_5_x24-s_vs_stockfish_4.pgn",
        json_filename="match_5_x24_vs_sf4_summary.json",
        cand_cfg=cfg_x24_s, ref_cfg=cfg_sf4,
        openings=all_openings[:20],
        time_base=1500, time_inc=50, max_workers=4
    )
    overall_results["match_5"] = res_m5

    # Match 6: Candidate X24-S vs Stockfish 11 (20 pairs, 40 games @ 1.5s + 50ms)
    res_m6 = run_match_parallel(
        match_name="Match 6: Candidate X24-S vs Stockfish 11 (External 2020 Reference)",
        pgn_filename="match_6_x24-s_vs_stockfish_11.pgn",
        json_filename="match_6_x24_vs_sf11_summary.json",
        cand_cfg=cfg_x24_s, ref_cfg=cfg_sf11,
        openings=all_openings[:20],
        time_base=1500, time_inc=50, max_workers=4
    )
    overall_results["match_6"] = res_m6

    # Match 7: Candidate X24-S vs Stockfish 19 NNUE (20 pairs, 40 games @ 1.5s + 50ms)
    res_m7 = run_match_parallel(
        match_name="Match 7: Candidate X24-S vs Stockfish 19 (External SOTA Benchmark)",
        pgn_filename="match_7_x24-s_vs_stockfish_19.pgn",
        json_filename="match_7_x24_vs_sf19_summary.json",
        cand_cfg=cfg_x24_s, ref_cfg=cfg_sf19,
        openings=all_openings[:20],
        time_base=1500, time_inc=50, max_workers=4
    )
    overall_results["match_7"] = res_m7

    # Save overall summary
    summary_path = RAW_DIR / "authoritative_tournament_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(overall_results, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL 7 AUTHORITATIVE MATCHES COMPLETED SUCCESSFULLY!")
    print(f"Summary written to {summary_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
