#!/usr/bin/env python3
"""
run_p113_tournaments.py
Milestone P1.13 Comprehensive Tournament Pipeline (JCTS v2 Standard)
Project Janus — Phase 1, Milestone P1.13

Tournaments Executed:
  Match 1: Janus Classical X18-S (1T) vs Janus Classical X7 (1T)   [50 pairs, 100 games @ 1.0s + 50ms]
  Match 2: Janus Classical X18-S (1T) vs Janus Classical X7 (1T)   [25 pairs,  50 games @ 2.5s + 100ms] (Slow TC)
  Match 3: Janus Classical X18-P (4T) vs Janus Classical X12 (4T)  [50 pairs, 100 games @ 1.0s + 50ms]
  Match 4: Janus Classical X18-S (1T) vs Stockfish 4 (1T)          [20 pairs,  40 games @ 1.5s + 50ms] (Ladder Step 1)
  Match 5: Janus Classical X18-S (1T) vs Stockfish 11 (1T)         [20 pairs,  40 games @ 1.5s + 50ms] (Peak Classical Ceiling)
  Match 6: Janus Classical X18-S (1T) vs Stockfish 19 (1T)         [20 pairs,  40 games @ 1.5s + 50ms] (Modern Ceiling 1T)
  Match 7: Janus Classical X18-P (4T) vs Stockfish 19 (4T)         [20 pairs,  40 games @ 1.5s + 50ms] (Modern Ceiling 4T)
Total games = 410
"""

import os
import sys
import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

EXE_X18 = ROOT / "analysis" / "phase1" / "p1.13" / "control" / "janus_classical_x18.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"

EXE_SF4  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.13" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.13" / "pgn"
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
            elif "X18" in self.name:
                self.send("setoption name UCI_Variant value X18")
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


def execute_match(match_name: str, eng_a: dict, eng_b: dict, openings: list, num_pairs: int, time_base: int, time_inc: int, max_workers: int = 4) -> dict:
    print(f"\n================================================================================")
    print(f"STARTING MATCH: {match_name} ({num_pairs * 2} games @ {time_base}ms + {time_inc}ms)")
    print(f"================================================================================")
    tasks = []
    game_count = num_pairs * 2
    for pair_idx in range(num_pairs):
        op = openings[pair_idx % len(openings)]
        # Game 1: A is White, B is Black
        tasks.append((pair_idx * 2, eng_a, eng_b, op, time_base, time_inc))
        # Game 2: B is White, A is Black
        tasks.append((pair_idx * 2 + 1, eng_b, eng_a, op, time_base, time_inc))

    results = [None] * game_count
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_match_task, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            g_idx, res = fut.result()
            results[g_idx] = res
            print(f"[{match_name}] Game {g_idx+1:2d}/{game_count}: {res['white']} vs {res['black']} -> {res['result']} ({res['termination']}, {res['plies']} plies)", flush=True)

    # Save PGN
    pgn_path = PGN_DIR / f"{match_name}.pgn"
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for idx, g in enumerate(results):
            pgn_game = chess.pgn.Game()
            pgn_game.headers["Event"] = f"P1.13 Tournament: {match_name}"
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

    pts_a = wins_a + 0.5 * draws
    score_pct = (pts_a / game_count) * 100.0
    ci_low, ci_high = calc_confidence_interval(pts_a, game_count)
    elo = calc_elo(pts_a / game_count)
    elo_low = calc_elo(ci_low) if ci_low > 0 else -float('inf')
    elo_high = calc_elo(ci_high) if ci_high < 1 else float('inf')

    # Pentanomial distribution
    pentanomial = {"WW": 0, "WD": 0, "DD_WL": 0, "LD": 0, "LL": 0}
    for p in range(num_pairs):
        g1 = results[2 * p]
        g2 = results[2 * p + 1]
        def pts_for_a(g):
            is_aw = g["white"] == eng_a["name"]
            if g["result"] == "1-0": return 1.0 if is_aw else 0.0
            if g["result"] == "0-1": return 0.0 if is_aw else 1.0
            return 0.5
        pair_pts = pts_for_a(g1) + pts_for_a(g2)
        if pair_pts == 2.0: pentanomial["WW"] += 1
        elif pair_pts == 1.5: pentanomial["WD"] += 1
        elif pair_pts == 1.0: pentanomial["DD_WL"] += 1
        elif pair_pts == 0.5: pentanomial["LD"] += 1
        elif pair_pts == 0.0: pentanomial["LL"] += 1

    summary = {
        "match_name": match_name,
        "eng_a": eng_a["name"],
        "eng_b": eng_b["name"],
        "games": game_count,
        "wins_a": wins_a,
        "draws": draws,
        "losses_a": losses_a,
        "pts_a": pts_a,
        "score_pct": score_pct,
        "ci_pct": (ci_low * 100.0, ci_high * 100.0),
        "elo": elo,
        "elo_ci": (elo_low, elo_high),
        "pentanomial": pentanomial
    }
    
    print(f"\n=== MATCH SUMMARY: {match_name} ===")
    print(f"Score for {eng_a['name']}: {wins_a}W - {draws}D - {losses_a}L ({pts_a}/{game_count} = {score_pct:.2f}%)")
    print(f"95% CI: [{ci_low*100:.2f}%, {ci_high*100:.2f}%]")
    if elo is not None:
        print(f"Elo Difference: {elo:+.1f} (95% CI: [{elo_low:+.1f}, {elo_high:+.1f}])")
    else:
        print("Elo Difference: Undefined (Zero score / Maximum score)")
    print(f"Pentanomial: {pentanomial}")
    return summary


def main():
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    # Engine configs
    cfg_x18_1t = {"exe": str(EXE_X18), "name": "Janus-X18-1T", "threads": 1, "is_x7": False, "is_sf": False, "variant": "X18"}
    cfg_x18_4t = {"exe": str(EXE_X18), "name": "Janus-X18-4T", "threads": 4, "is_x7": False, "is_sf": False, "variant": "X18"}
    
    cfg_x7_1t  = {"exe": str(EXE_X7), "name": "Janus-X7-1T", "threads": 1, "is_x7": True, "is_sf": False}
    cfg_x12_4t = {"exe": str(EXE_X12), "name": "Janus-X12-4T", "threads": 4, "is_x7": False, "is_sf": False, "variant": "X12"}

    cfg_sf4_1t  = {"exe": str(EXE_SF4), "name": "Stockfish-4-1T", "threads": 1, "is_x7": False, "is_sf": True}
    cfg_sf11_1t = {"exe": str(EXE_SF11), "name": "Stockfish-11-1T", "threads": 1, "is_x7": False, "is_sf": True}
    cfg_sf19_1t = {"exe": str(EXE_SF19), "name": "Stockfish-19-1T", "threads": 1, "is_x7": False, "is_sf": True}
    cfg_sf19_4t = {"exe": str(EXE_SF19), "name": "Stockfish-19-4T", "threads": 4, "is_x7": False, "is_sf": True}

    matches_to_run = [
        # Match 1: Single-thread qualification (50 pairs, 100 games @ 1.0s + 50ms)
        ("x18_1t_vs_x7_1t", cfg_x18_1t, cfg_x7_1t, 50, 1000, 50),
        
        # Match 2: Slower-time replication (25 pairs, 50 games @ 2.5s + 100ms)
        ("x18_1t_vs_x7_1t_slow", cfg_x18_1t, cfg_x7_1t, 25, 2500, 100),
        
        # Match 3: Four-thread qualification (50 pairs, 100 games @ 1.0s + 50ms)
        ("x18_4t_vs_x12_4t", cfg_x18_4t, cfg_x12_4t, 50, 1000, 50),
        
        # Match 4: Historical Classical Ladder Step 1 (20 pairs, 40 games @ 1.5s + 50ms)
        ("x18_1t_vs_sf4_1t", cfg_x18_1t, cfg_sf4_1t, 20, 1500, 50),
        
        # Match 5: Historical Classical Peak Ceiling (20 pairs, 40 games @ 1.5s + 50ms)
        ("x18_1t_vs_sf11_1t", cfg_x18_1t, cfg_sf11_1t, 20, 1500, 50),
        
        # Match 6: Unrestricted Stockfish 19 Benchmark 1T (20 pairs, 40 games @ 1.5s + 50ms)
        ("x18_1t_vs_sf19_1t", cfg_x18_1t, cfg_sf19_1t, 20, 1500, 50),
        
        # Match 7: Unrestricted Stockfish 19 Benchmark 4T (20 pairs, 40 games @ 1.5s + 50ms)
        ("x18_4t_vs_sf19_4t", cfg_x18_4t, cfg_sf19_4t, 20, 1500, 50),
    ]

    all_summaries = []
    total_games_played = 0
    for mname, ea, eb, npairs, tb, ti in matches_to_run:
        summary = execute_match(mname, ea, eb, openings, npairs, tb, ti, max_workers=4)
        all_summaries.append(summary)
        total_games_played += summary["games"]

    out_file = RAW_DIR / "p113_tournaments_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_tournaments": len(all_summaries),
            "total_games_played": total_games_played,
            "tournaments": all_summaries
        }, f, indent=2)
    print(f"\nAll {total_games_played} tournament games completed successfully. Summary saved to {out_file}")

if __name__ == "__main__":
    main()

