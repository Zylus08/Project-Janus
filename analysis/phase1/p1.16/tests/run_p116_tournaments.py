#!/usr/bin/env python3
"""
run_p116_tournaments.py
Milestone P1.16 Independent Competitive Strength Qualification & External Calibration.
Executes 420 tournament games across 7 matches:
  Match 1: Candidate X21-S (1T) vs Janus Classical X7 (1T Baseline)    [50 pairs, 100 games @ 1.0s + 50ms]
  Match 2: Candidate X21-S (1T) vs Janus Classical X7 (1T Baseline)    [25 pairs,  50 games @ 2.5s + 100ms] (Slow TC)
  Match 3: Candidate X21-P (4T) vs Janus Classical X12 (4T Baseline)   [50 pairs, 100 games @ 1.0s + 50ms]
  Match 4: Candidate X21-S (1T) vs Janus Classical X19 / X20 (1T Refs) [25 pairs,  50 games @ 1.0s + 50ms]
  Match 5: Candidate X21-S (1T) vs Stockfish 4 (1T)                   [20 pairs,  40 games @ 1.5s + 50ms]
  Match 6: Candidate X21-S (1T) vs Stockfish 11 (1T)                  [20 pairs,  40 games @ 1.5s + 50ms]
  Match 7: Candidate X21-S (1T) vs Stockfish 19 NNUE (1T)             [20 pairs,  40 games @ 1.5s + 50ms]
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

EXE_X21 = ROOT / "analysis" / "phase1" / "p1.16" / "control" / "janus_classical_x21.exe"
EXE_X20 = ROOT / "analysis" / "phase1" / "p1.15" / "control" / "janus_classical_x20.exe"
EXE_X19 = ROOT / "analysis" / "phase1" / "p1.14" / "control" / "janus_classical_x19.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"

EXE_SF4  = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.16" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.16" / "pgn"
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
            elif "X21" in self.name:
                self.send("setoption name UCI_Variant value X21")
                self.send("setoption name UCI_QuiescenceMode value Q1")
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

        # Draw Adjudication: 5 consecutive near-zero evals (|eval| <= 5 cp) after move 35
        if score is not None and abs(score) <= 5 and len(moves_history) >= 70:
            consecutive_draw_evals += 1
            if consecutive_draw_evals >= 10:
                adjudication = "adjudication_eval_draw"
                termination = "draw"
                break
        else:
            consecutive_draw_evals = 0

        # Resignation Adjudication: |eval| >= 1000 cp for 4 plies after move 30
        if score is not None and abs(score) >= 1000 and len(moves_history) >= 60:
            draw_claim_moves += 1
            if draw_claim_moves >= 6:
                adjudication = "adjudication_resignation"
                termination = "white_win" if score > 0 else "black_win"
                break
        else:
            draw_claim_moves = 0

    # Adjudicate final result
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
        elif len(moves_history) >= max_plies:
            termination = "draw"
            adjudication = "max_plies_reached"
        else:
            termination = "draw"
            adjudication = "adjudication_draw"

    white_runner.stop()
    black_runner.stop()

    if termination == "white_win":
        res_str = "1-0"
        cand_score = 1.0 if "X21" in white_cfg["name"] else 0.0
    elif termination == "black_win":
        res_str = "0-1"
        cand_score = 1.0 if "X21" in black_cfg["name"] else 0.0
    else:
        res_str = "1/2-1/2"
        cand_score = 0.5

    # Build PGN game
    game = chess.pgn.Game()
    game.headers["Event"] = f"Milestone P1.16 Tournament: {white_cfg['name']} vs {black_cfg['name']}"
    game.headers["White"] = white_cfg["name"]
    game.headers["Black"] = black_cfg["name"]
    game.headers["Result"] = res_str
    game.headers["TimeControl"] = f"{time_base_ms//1000}+{time_inc_ms/1000}"
    game.headers["Termination"] = f"{adjudication or termination}"
    game.headers["Opening"] = opening.get("name", "Unknown Opening")

    node = game
    replay_b = chess.Board()
    for uci_m in moves_history:
        m = chess.Move.from_uci(uci_m)
        node = node.add_variation(m)
        replay_b.push(m)

    return {
        "white": white_cfg["name"],
        "black": black_cfg["name"],
        "result": res_str,
        "termination": termination,
        "adjudication": adjudication,
        "plies": len(moves_history),
        "cand_score": cand_score,
        "opening": opening.get("name", ""),
        "pgn_text": str(game)
    }

def run_match(match_id: str, cand_cfg: dict, opp_cfg: dict, n_pairs: int, time_base: int, time_inc: int, max_workers: int = 6) -> dict:
    with open(OPENINGS_PATH, "r") as f:
        all_openings = json.load(f)

    openings = all_openings[:n_pairs]
    print(f"\n================================================================================")
    print(f"RUNNING MATCH {match_id}: {cand_cfg['name']} vs {opp_cfg['name']}")
    print(f"Games: {n_pairs * 2} ({n_pairs} paired openings) | TC: {time_base/1000}s + {time_inc/1000}s | Workers: {max_workers}")
    print(f"================================================================================")

    games_data = []
    pair_scores = []
    pgn_lines = []

    t_start = time.time()

    # Schedule paired games (White and Black for each opening)
    pair_tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pair = {}
        for p_idx, op in enumerate(openings):
            f_w = executor.submit(play_single_game, cand_cfg, opp_cfg, op, time_base, time_inc)
            f_b = executor.submit(play_single_game, opp_cfg, cand_cfg, op, time_base, time_inc)
            future_to_pair[p_idx] = (f_w, f_b, op)

        for p_idx, (f_w, f_b, op) in future_to_pair.items():
            res_w = f_w.result()
            res_b = f_b.result()

            p_cand_pts = res_w["cand_score"] + res_b["cand_score"]
            norm_pair_score = p_cand_pts / 2.0
            pair_scores.append(norm_pair_score)

            games_data.append(res_w)
            games_data.append(res_b)

            pgn_lines.append(res_w["pgn_text"] + "\n\n")
            pgn_lines.append(res_b["pgn_text"] + "\n\n")

            curr_total = sum(g["cand_score"] for g in games_data)
            n_played = len(games_data)
            print(f"  [Pair {p_idx+1:>2}/{n_pairs}] Cand: {p_cand_pts:.1f}/2.0 | Match: {curr_total:.1f}/{n_played} ({curr_total/n_played*100:5.1f}%) | Op: {op['name'][:25]}")

    elapsed_sec = time.time() - t_start

    # Statistical Evaluation
    total_cand = sum(g["cand_score"] for g in games_data)
    n_games = len(games_data)
    score_pct = total_cand / n_games
    mean_p, ci_low, ci_high, p_value = calc_paired_ci_and_pvalue(pair_scores)
    elo_diff = calc_elo(score_pct)

    cand_wins = sum(1 for g in games_data if g["cand_score"] == 1.0)
    draws = sum(1 for g in games_data if g["cand_score"] == 0.5)
    cand_losses = sum(1 for g in games_data if g["cand_score"] == 0.0)

    # Save PGN
    pgn_path = PGN_DIR / f"{match_id.lower()}.pgn"
    with open(pgn_path, "w") as f:
        f.writelines(pgn_lines)

    summary = {
        "match_id": match_id,
        "candidate": cand_cfg["name"],
        "opponent": opp_cfg["name"],
        "games_played": n_games,
        "pairs_played": n_pairs,
        "time_control": f"{time_base/1000}s+{time_inc/1000}s",
        "cand_wins": cand_wins,
        "draws": draws,
        "cand_losses": cand_losses,
        "cand_points": total_cand,
        "cand_score_pct": score_pct,
        "elo_difference": elo_diff,
        "paired_ci_95": [ci_low, ci_high],
        "one_sided_p_value": p_value,
        "elapsed_seconds": elapsed_sec,
        "pgn_file": str(pgn_path),
        "games": games_data
    }

    print(f"\n--- MATCH {match_id} COMPLETED in {elapsed_sec:.1f}s ---")
    print(f"  Result: {total_cand:.1f}/{n_games} ({score_pct*100:.2f}%) | +{cand_wins} ={draws} -{cand_losses}")
    print(f"  Elo Diff: {f'{elo_diff:+.1f}' if elo_diff is not None else 'N/A'}")
    print(f"  95% Paired CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]")
    print(f"  1-Sided p-value: {p_value:.6f}")
    print(f"  PGN saved to {pgn_path}")

    return summary

def main():
    print("================================================================================")
    print("PROJECT JANUS — PHASE 11 & 12: TOURNAMENT PROGRAM (420 GAMES)")
    print("================================================================================")

    CAND_X21S = {"name": "Janus Classical X21-S", "exe": str(EXE_X21), "threads": 1, "variant": "X21"}
    CAND_X21P = {"name": "Janus Classical X21-P", "exe": str(EXE_X21), "threads": 4, "variant": "X21"}

    OPP_X7  = {"name": "Janus Classical X7 (Baseline 1T)", "exe": str(EXE_X7), "threads": 1, "is_x7": True}
    OPP_X12 = {"name": "Janus Classical X12 (Baseline 4T)", "exe": str(EXE_X12), "threads": 4, "variant": "X12"}
    OPP_X19 = {"name": "Janus Classical X19 (Ref 1T)", "exe": str(EXE_X19), "threads": 1, "variant": "X19"}
    OPP_X20 = {"name": "Janus Classical X20 (Ref 1T)", "exe": str(EXE_X20), "threads": 1, "variant": "X20"}

    OPP_SF4  = {"name": "Stockfish 4 (Classical Ref 1)", "exe": str(EXE_SF4), "threads": 1, "is_sf": True}
    OPP_SF11 = {"name": "Stockfish 11 (Classical Ref 2)", "exe": str(EXE_SF11), "threads": 1, "is_sf": True}
    OPP_SF19 = {"name": "Stockfish 19 (Ultimate NNUE)", "exe": str(EXE_SF19), "threads": 1, "is_sf": True}

    matches_out = {}

    # Match 1: X21-S (1T) vs X7 (1T Baseline) [100 games @ 1.0s + 50ms]
    matches_out["Match_1"] = run_match("match1_x21s_vs_x7", CAND_X21S, OPP_X7, 50, 1000, 50, max_workers=6)

    # Match 2: X21-S (1T) vs X7 (1T Baseline) [50 games @ 2.5s + 100ms] (Slower TC)
    matches_out["Match_2"] = run_match("match2_x21s_vs_x7_slow", CAND_X21S, OPP_X7, 25, 2500, 100, max_workers=6)

    # Match 3: X21-P (4T) vs X12 (4T Baseline) [100 games @ 1.0s + 50ms] (4T SMP)
    matches_out["Match_3"] = run_match("match3_x21p_vs_x12", CAND_X21P, OPP_X12, 50, 1000, 50, max_workers=2)

    # Match 4: X21-S (1T) vs References (25 vs X19, 25 vs X20) [50 games @ 1.0s + 50ms]
    # We run 25 games (12 pairs = 24 games + 1) vs X19 and X20
    m4_x19 = run_match("match4_part1_vs_x19", CAND_X21S, OPP_X19, 13, 1000, 50, max_workers=6)
    m4_x20 = run_match("match4_part2_vs_x20", CAND_X21S, OPP_X20, 12, 1000, 50, max_workers=6)

    # Merge Match 4 results
    m4_games = m4_x19["games"] + m4_x20["games"]
    m4_total_cand = sum(g["cand_score"] for g in m4_games)
    m4_n = len(m4_games)
    m4_p = m4_total_cand / m4_n
    m4_ci = calc_confidence_interval(m4_total_cand, m4_n)
    matches_out["Match_4"] = {
        "match_id": "match4_x21s_vs_references",
        "candidate": "Janus Classical X21-S",
        "opponent": "Janus Classical X19 / X20",
        "games_played": m4_n,
        "cand_points": m4_total_cand,
        "cand_score_pct": m4_p,
        "elo_difference": calc_elo(m4_p),
        "ci_95": m4_ci,
        "cand_wins": sum(1 for g in m4_games if g["cand_score"] == 1.0),
        "draws": sum(1 for g in m4_games if g["cand_score"] == 0.5),
        "cand_losses": sum(1 for g in m4_games if g["cand_score"] == 0.0),
        "sub_matches": {"vs_x19": m4_x19, "vs_x20": m4_x20}
    }

    # Match 5: X21-S (1T) vs Stockfish 4 [40 games @ 1.5s + 50ms]
    matches_out["Match_5"] = run_match("match5_x21s_vs_sf4", CAND_X21S, OPP_SF4, 20, 1500, 50, max_workers=6)

    # Match 6: X21-S (1T) vs Stockfish 11 [40 games @ 1.5s + 50ms]
    matches_out["Match_6"] = run_match("match6_x21s_vs_sf11", CAND_X21S, OPP_SF11, 20, 1500, 50, max_workers=6)

    # Match 7: X21-S (1T) vs Stockfish 19 [40 games @ 1.5s + 50ms]
    matches_out["Match_7"] = run_match("match7_x21s_vs_sf19", CAND_X21S, OPP_SF19, 20, 1500, 50, max_workers=6)

    # Summary File Output
    out_file = RAW_DIR / "p116_tournaments_raw.json"
    with open(out_file, "w") as f:
        json.dump(matches_out, f, indent=2)

    print("\n================================================================================")
    print("ALL 7 TOURNAMENT MATCHES COMPLETED SUCCESSFULLY (420 GAMES)")
    print(f"Raw results written to {out_file}")
    print("================================================================================")

if __name__ == "__main__":
    main()
