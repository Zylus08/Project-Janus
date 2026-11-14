#!/usr/bin/env python3
"""
run_dev_tournaments.py
Milestone P1.19 Phase 8: Track A Development Strength Battery.
Executes an independent 50-pair (100-game) development match between:
  Candidate X24-S (Track A Isolated: BP=1, KFE=0, E5, Q1, PawnHash=1)
  vs
  Reference X22-S (Control: BP=0, KFE=0, E5, Q1, PawnHash=1)
Time Control: 0.5s + 20ms Fischer increment.
Adjudication: Standard Project Janus certified release rules (draws at move 40+ with |eval| < 8 cp for 8 half-moves; resignation at move 50+ with |eval| > 1000 cp for 5 half-moves).
Computes exact pentanomial distribution, paired CI, p-values, and Elo delta.
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

EXE_X24 = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"

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

    def set_position(self, fen: str, moves: List[str]):
        if moves:
            mv_str = " ".join(moves)
            self.send(f"position fen {fen} moves {mv_str}")
        else:
            self.send(f"position fen {fen}")

    def go(self, wtime: int, btime: int, winc: int, binc: int) -> Tuple[str, Optional[int]]:
        self.send(f"go wtime {wtime} btime {btime} winc {winc} binc {binc}")
        bestmove = ""
        score = None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if "score cp" in line_str:
                parts = line_str.split()
                try:
                    cp_idx = parts.index("cp")
                    score = int(parts[cp_idx + 1])
                except (ValueError, IndexError):
                    pass
            elif "score mate" in line_str:
                parts = line_str.split()
                try:
                    mate_idx = parts.index("mate")
                    mate_plies = int(parts[mate_idx + 1])
                    score = 30000 if mate_plies > 0 else -30000
                except (ValueError, IndexError):
                    pass
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break
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

def play_game(
    game_id: int,
    opening_info: Dict[str, Any],
    white_cfg: Dict[str, Any],
    black_cfg: Dict[str, Any],
    base_time_ms: int = 500,
    inc_ms: int = 20
) -> Dict[str, Any]:
    white_runner = EngineRunner(
        white_cfg["exe"], white_cfg["name"],
        threads=white_cfg.get("threads", 1),
        variant=white_cfg.get("variant", ""),
        bp=white_cfg.get("bp", 0),
        kfe=white_cfg.get("kfe", 0)
    )
    black_runner = EngineRunner(
        black_cfg["exe"], black_cfg["name"],
        threads=black_cfg.get("threads", 1),
        variant=black_cfg.get("variant", ""),
        bp=black_cfg.get("bp", 0),
        kfe=black_cfg.get("kfe", 0)
    )

    white_runner.start()
    black_runner.start()
    white_runner.new_game()
    black_runner.new_game()

    board = chess.Board(opening_info["fen"])
    moves_history: List[str] = list(opening_info.get("uci_sequence", []))

    wtime = base_time_ms
    btime = base_time_ms
    consecutive_draw_evals = 0
    resignation_count = 0
    adjudication = None
    termination = None

    for ply in range(len(moves_history), 250):
        turn = board.turn
        current_runner = white_runner if turn == chess.WHITE else black_runner

        current_runner.set_position(chess.STARTING_FEN, moves_history)
        t_start = time.perf_counter()
        bestmove, score = current_runner.go(wtime, btime, inc_ms, inc_ms)
        t_elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        if turn == chess.WHITE:
            wtime = max(10, wtime - t_elapsed_ms + inc_ms)
        else:
            btime = max(10, btime - t_elapsed_ms + inc_ms)

        if not bestmove or bestmove == "0000" or bestmove == "(none)":
            adjudication = "no_move"
            termination = "black_win" if turn == chess.WHITE else "white_win"
            break

        move_obj = chess.Move.from_uci(bestmove)
        if move_obj not in board.legal_moves:
            adjudication = "illegal_move"
            termination = "black_win" if turn == chess.WHITE else "white_win"
            break

        board.push(move_obj)
        moves_history.append(bestmove)

        if board.is_checkmate():
            adjudication = "checkmate"
            termination = "white_win" if turn == chess.WHITE else "black_win"
            break
        if board.is_stalemate():
            adjudication = "stalemate"
            termination = "draw"
            break
        if board.is_insufficient_material():
            adjudication = "insufficient_material"
            termination = "draw"
            break
        if board.can_claim_threefold_repetition() or board.is_repetition(3):
            adjudication = "repetition"
            termination = "draw"
            break
        if board.can_claim_fifty_moves() or board.halfmove_clock >= 100:
            adjudication = "fifty_moves"
            termination = "draw"
            break

        # Certified Draw Adjudication: Move 40+ with |score| <= 8 cp for 8 half-moves
        if score is not None and len(moves_history) >= 80:
            if abs(score) <= 8:
                consecutive_draw_evals += 1
            else:
                consecutive_draw_evals = 0
            if consecutive_draw_evals >= 8:
                adjudication = "adjudication_eval_draw"
                termination = "draw"
                break
        else:
            consecutive_draw_evals = 0

        # Certified Resignation Adjudication: Move 50+ with |score| >= 1000 cp for 5 half-moves
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

    if not termination:
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
        "game_id": game_id,
        "opening": opening_info.get("name", "Unknown"),
        "eco": opening_info.get("eco", "A00"),
        "fen": opening_info["fen"],
        "white": white_cfg["name"],
        "black": black_cfg["name"],
        "result": res_str,
        "adjudication": adjudication,
        "ply_count": len(moves_history),
        "moves": moves_history
    }

def run_development_match():
    print("=" * 80)
    print("MILESTONE P1.19 PHASE 8: TRACK A INDEPENDENT DEVELOPMENT TOURNAMENT")
    print("=" * 80)

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)

    # Use first 50 openings (50 opening pairs = 100 games)
    NUM_PAIRS = 50
    dev_openings = all_openings[:NUM_PAIRS]

    cfg_x24 = {
        "name": "Janus Classical X24-S",
        "exe": EXE_X24,
        "threads": 1,
        "variant": "X24",
        "bp": 1,
        "kfe": 0
    }
    cfg_x22 = {
        "name": "Janus Classical X22-S",
        "exe": EXE_X22,
        "threads": 1,
        "variant": "X22",
        "bp": 0,
        "kfe": 0
    }

    match_name = "Match Dev: Candidate X24-S vs Reference X22-S"
    print(f"\nStarting {match_name} ({NUM_PAIRS} Opening Pairs / 100 Games @ 0.5s + 20ms)...")

    tasks = []
    for p_idx, op in enumerate(dev_openings):
        # Game 1: X24 White, X22 Black
        tasks.append((2 * p_idx + 1, op, cfg_x24, cfg_x22))
        # Game 2: X22 White, X24 Black
        tasks.append((2 * p_idx + 2, op, cfg_x22, cfg_x24))

    start_time = time.time()
    game_results = [None] * len(tasks)

    # Execute with max_workers=4 concurrent games
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_task = {
            executor.submit(play_game, gid, op, w_cfg, b_cfg, 500, 20): (gid, w_cfg["name"], b_cfg["name"])
            for (gid, op, w_cfg, b_cfg) in tasks
        }
        completed = 0
        for future in as_completed(future_to_task):
            gid, w_name, b_name = future_to_task[future]
            try:
                res = future.result()
                game_results[gid - 1] = res
                completed += 1
                if completed % 10 == 0 or completed == len(tasks):
                    print(f"[{completed:3d}/{len(tasks):3d}] Game {gid:3d} finished: {res['white']} vs {res['black']} -> {res['result']} ({res['adjudication']})")
            except Exception as e:
                print(f"ERROR in game {gid}: {e}")

    elapsed_match = time.time() - start_time

    # Tally results from Candidate X24 perspective
    cand_score = 0.0
    wins = 0
    draws = 0
    losses = 0

    penta = {2.0: 0, 1.5: 0, 1.0: 0, 0.5: 0, 0.0: 0}
    pair_scores = []

    for p_idx in range(len(dev_openings)):
        g1 = game_results[2 * p_idx]
        g2 = game_results[2 * p_idx + 1]

        # In g1, X24 is White
        s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
        # In g2, X24 is Black
        s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)

        pair_sum = s1 + s2
        penta[pair_sum] += 1
        pair_scores.append(pair_sum / 2.0)

        cand_score += pair_sum
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

    print("\n" + "=" * 80)
    print(f"--- {match_name} Final Standings ---")
    print(f"Score: {cand_score:.1f}/{total_games} (+{wins} ={draws} -{losses}) | {win_rate:.1f}%")
    print(f"Pentanomial Distribution [2.0, 1.5, 1.0, 0.5, 0.0]: [{penta[2.0]}, {penta[1.5]}, {penta[1.0]}, {penta[0.5]}, {penta[0.0]}]")
    print(f"Paired CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%] | One-Sided p: {p_val_one:.4f} | Two-Sided p: {p_val_two:.4f}")
    if elo is not None:
        print(f"Elo Difference: {elo:+.1f} Elo")
    print(f"Elapsed Time: {elapsed_match:.1f}s")
    print("=" * 80)

    # Save PGN
    pgn_file = PGN_DIR / "match_dev_x24_vs_x22.pgn"
    with open(pgn_file, "w", encoding="utf-8") as f_pgn:
        for g_data in game_results:
            game = chess.pgn.Game()
            game.headers["Event"] = match_name
            game.headers["Site"] = "Project Janus Classical Search Lab"
            game.headers["Date"] = time.strftime("%Y.%m.%d")
            game.headers["Round"] = str(g_data["game_id"])
            game.headers["White"] = g_data["white"]
            game.headers["Black"] = g_data["black"]
            game.headers["Result"] = g_data["result"]
            game.headers["Termination"] = g_data["adjudication"]
            game.headers["Opening"] = g_data["opening"]
            game.headers["ECO"] = g_data["eco"]
            game.headers["OpeningFEN"] = g_data["fen"]

            node = game
            for mv in g_data["moves"]:
                try:
                    m = chess.Move.from_uci(mv)
                    node = node.add_variation(m)
                except Exception as ex:
                    print(f"Error parsing move {mv} in game {g_data['game_id']}: {ex}")
            print(game, file=f_pgn, end="\n\n")

    print(f"PGN saved to: {pgn_file}")

    # Save Raw Summary
    summary_data = {
        "match_name": match_name,
        "candidate": cfg_x24["name"],
        "reference": cfg_x22["name"],
        "num_pairs": NUM_PAIRS,
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
        "elapsed_seconds": round(elapsed_match, 1),
        "games": game_results
    }

    out_file = RAW_DIR / "track_a_dev_strength.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Raw results saved to: {out_file}")

if __name__ == "__main__":
    run_development_match()
