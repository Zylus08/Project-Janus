#!/usr/bin/env python3
"""
run_dev_ablations.py
Milestone P1.18 Phase 10: Development Ablation Tournaments.
Executes 3 targeted ablation matches across 10 balanced opening pairs (20 games per match, 60 games total)
under the certified release tournament harness at 0.5s + 20ms:
  Match Dev-1: Candidate X23-S vs Reference X22-S (Joint: Track A + Track B)
  Match Dev-2: Track A Alone (BP=1, KFE=0) vs Reference X22-S
  Match Dev-3: Track B Alone (BP=0, KFE=1) vs Reference X22-S
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

EXE_X23 = ROOT / "analysis" / "phase1" / "p1.18" / "control" / "janus_classical_x23.exe"
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.18" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.18" / "pgn"
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

def calc_elo(p: float) -> Optional[float]:
    if p <= 0.00001 or p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)

def calc_paired_ci_and_pvalue(pair_scores: List[float], z: float = 1.95996) -> Tuple[float, float, float, float]:
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
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    p_value = 0.5 * math.erfc(t_stat / math.sqrt(2))
    return mean_p, ci_low, ci_high, p_value

class EngineRunner:
    def __init__(self, exe_path: Path, name: str, threads: int = 1, variant: str = "", bp: int = 0, kfe: int = 0):
        self.exe_path = exe_path
        self.name = name
        self.threads = threads
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

        if self.threads > 1:
            self.send(f"setoption name Threads value {self.threads}")
        if self.variant:
            self.send(f"setoption name UCI_Variant value {self.variant}")
        self.send(f"setoption name UCI_BackwardPawns value {'true' if self.bp else 'false'}")
        self.send(f"setoption name UCI_KingFileExposure value {'true' if self.kfe else 'false'}")

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

def play_single_game(white_cfg: dict, black_cfg: dict, opening: dict, time_base_ms: int, time_inc_ms: int, max_plies: int = 140) -> dict:
    white_runner = EngineRunner(
        Path(white_cfg["exe"]),
        white_cfg["name"],
        threads=white_cfg.get("threads", 1),
        variant=white_cfg.get("variant", ""),
        bp=white_cfg.get("bp", 0),
        kfe=white_cfg.get("kfe", 0)
    )
    black_runner = EngineRunner(
        Path(black_cfg["exe"]),
        black_cfg["name"],
        threads=black_cfg.get("threads", 1),
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

        if not bestmove or bestmove == "(none)":
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

        # Draw Adjudication: 10 consecutive near-zero evals (|eval| <= 5 cp) after move 35
        if score is not None and abs(score) <= 5 and len(moves_history) >= 70:
            consecutive_draw_evals += 1
            if consecutive_draw_evals >= 10:
                adjudication = "adjudication_eval_draw"
                termination = "draw"
                break
        else:
            consecutive_draw_evals = 0

        # Certified Resignation Adjudication:
        if score is not None and len(moves_history) >= 50:
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
        "pgn_moves": moves_history
    }

def run_match_parallel(match_name: str, cand_cfg: dict, ref_cfg: dict, openings: list, time_base: int, time_inc: int) -> dict:
    print(f"\n================================================================================")
    print(f"STARTING {match_name}: {cand_cfg['name']} vs {ref_cfg['name']} ({len(openings)} pairs, {len(openings)*2} games)")
    print(f"Time Control: {time_base/1000.0}s + {time_inc}ms")
    print(f"================================================================================")

    tasks = []
    # Generate paired games (each opening played twice: cand as White, cand as Black)
    for idx, op in enumerate(openings):
        tasks.append((idx, 1, cand_cfg, ref_cfg, op))
        tasks.append((idx, 2, ref_cfg, cand_cfg, op))

    game_results = [None] * len(tasks)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=4) as executor:
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
                    "termination": "error", "adjudication": str(e), "plies": 0, "pgn_moves": []
                }

    elapsed_match = time.time() - start_time

    # Tally results from candidate's perspective
    cand_name = cand_cfg["name"]
    cand_score = 0.0
    wins = 0
    draws = 0
    losses = 0

    pair_scores = []
    for p_idx in range(len(openings)):
        g1 = game_results[2 * p_idx]
        g2 = game_results[2 * p_idx + 1]

        # In g1, cand is White
        s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
        # In g2, cand is Black
        s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)

        pair_s = (s1 + s2) / 2.0
        pair_scores.append(pair_s)

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
    mean_p, ci_low, ci_high, p_val = calc_paired_ci_and_pvalue(pair_scores)

    print(f"\n--- {match_name} Final Standings ---")
    print(f"Score: {cand_score:.1f}/{total_games} (+{wins} ={draws} -{losses}) | {win_rate:.1f}%")
    print(f"Paired CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%] | p-value: {p_val:.4f}")
    if elo is not None:
        print(f"Elo Difference: {elo:+.1f} Elo")
    print(f"Elapsed Time: {elapsed_match:.1f}s")

    return {
        "match_name": match_name,
        "cand": cand_name,
        "ref": ref_cfg["name"],
        "total_games": total_games,
        "score": cand_score,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": win_rate,
        "elo": elo,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": p_val,
        "elapsed_seconds": elapsed_match,
        "games": game_results
    }

def main():
    with open(OPENINGS_PATH, "r") as f:
        all_openings = json.load(f)

    # Use first 10 openings (pairs 1..10) for development ablations
    dev_openings = all_openings[:10]

    cfg_x22 = {
        "name": "Janus Classical X22-S",
        "exe": str(EXE_X22),
        "threads": 1,
        "variant": "X22",
        "bp": 0,
        "kfe": 0
    }

    # Match Dev-1: Candidate X23-S (Joint BP=1, KFE=1) vs Reference X22-S
    cfg_x23 = {
        "name": "Janus Classical X23-S (Joint)",
        "exe": str(EXE_X23),
        "threads": 1,
        "variant": "X23",
        "bp": 1,
        "kfe": 1
    }
    m1 = run_match_parallel("Match Dev-1 (Joint X23 vs X22)", cfg_x23, cfg_x22, dev_openings, 500, 20)

    # Match Dev-2: Track A Alone (BP=1, KFE=0) vs Reference X22-S
    cfg_x23_tA = {
        "name": "Janus Classical X23 (Track A Alone)",
        "exe": str(EXE_X23),
        "threads": 1,
        "variant": "X23",
        "bp": 1,
        "kfe": 0
    }
    m2 = run_match_parallel("Match Dev-2 (Track A Alone vs X22)", cfg_x23_tA, cfg_x22, dev_openings, 500, 20)

    # Match Dev-3: Track B Alone (BP=0, KFE=1) vs Reference X22-S
    cfg_x23_tB = {
        "name": "Janus Classical X23 (Track B Alone)",
        "exe": str(EXE_X23),
        "threads": 1,
        "variant": "X23",
        "bp": 0,
        "kfe": 1
    }
    m3 = run_match_parallel("Match Dev-3 (Track B Alone vs X22)", cfg_x23_tB, cfg_x22, dev_openings, 500, 20)

    ablations_summary = {
        "match_dev1_joint": m1,
        "match_dev2_trackA": m2,
        "match_dev3_trackB": m3
    }

    out_file = RAW_DIR / "dev_ablations_raw.json"
    with open(out_file, "w") as f:
        json.dump(ablations_summary, f, indent=2)
    print(f"\n[OK] Development ablations written to {out_file}")

if __name__ == "__main__":
    main()
