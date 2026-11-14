#!/usr/bin/env python3
"""
run_p120_dev_ablations.py
Milestone P1.20 Phase 9: Development Ablations Battery for Candidate X25.
Ablation Configurations:
  B0: Baseline Architecture (Option B Connected Pawns DISABLED, Backward Pawns DISABLED) -> X22 equivalent
  B1: Candidate X25 (Option B Connected Pawns ENABLED, Backward Pawns DISABLED)
  B2: Counter-Ablation (Option B Connected Pawns ENABLED, Backward Pawns ENABLED)

Matches:
  Dev Match 1: B1 vs B0 @ 1.0s + 50ms (25 pairs, 50 games) - Primary Option B single-thread gain
  Dev Match 2: B1 vs B0 @ 3.0s + 100ms (25 pairs, 50 games) - Slow-TC non-regression verification
  Dev Match 3: B1 vs B2 @ 1.0s + 50ms (25 pairs, 50 games) - Backward pawn negative interaction check
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
ENGINE_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"

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
    def __init__(self, exe_path: Path, options: Dict[str, Any]):
        self.exe_path = exe_path
        self.options = options
        self.proc = None

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
        for opt, val in self.options.items():
            self.send(f"setoption name {opt} value {val}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def go(self, moves: List[str], base_ms: int, inc_ms: int, wtime: int, btime: int) -> Tuple[str, int]:
        if not moves:
            self.send("position startpos")
        else:
            self.send("position startpos moves " + " ".join(moves))
        self.send(f"go wtime {wtime} btime {btime} winc {inc_ms} binc {inc_ms}")
        bestmove = ""
        score = 0
        t0 = time.time()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "score cp" in line:
                parts = line.split()
                try:
                    idx = parts.index("cp")
                    score = int(parts[idx + 1])
                except (ValueError, IndexError):
                    pass
            elif "score mate" in line:
                parts = line.split()
                try:
                    idx = parts.index("mate")
                    score = 10000 if int(parts[idx + 1]) > 0 else -10000
                except (ValueError, IndexError):
                    pass
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

def play_game(w_opts: Dict[str, Any], b_opts: Dict[str, Any], opening_moves: List[str], base_sec: float, inc_sec: float, max_moves: int = 120) -> Dict[str, Any]:
    w_engine = UciEngine(ENGINE_EXE, w_opts)
    b_engine = UciEngine(ENGINE_EXE, b_opts)
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

    eval_history = []
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
        "moves": moves
    }

def run_single_match(match_id: str, desc: str, cand_opts: Dict[str, Any], ref_opts: Dict[str, Any], openings: List[Dict[str, Any]], base_sec: float, inc_sec: float, pgn_name: str, concurrency: int = 4) -> Dict[str, Any]:
    print("\n" + "-" * 70)
    print(f"RUNNING: {match_id} — {desc}")
    print(f"Time Control: {base_sec}s + {int(inc_sec*1000)}ms | Concurrency: {concurrency}")
    print("-" * 70)

    t0 = time.time()
    num_pairs = len(openings)
    tasks = []
    for pair_idx, op in enumerate(openings):
        moves = [m.strip() for m in op.get("moves", "").split() if m.strip()]
        tasks.append((pair_idx, 1, cand_opts, ref_opts, moves))
        tasks.append((pair_idx, 2, ref_opts, cand_opts, moves))

    results_by_pair = {i: [None, None] for i in range(num_pairs)}
    all_game_results = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {}
        for task_idx, (p_idx, g_num, w_opts, b_opts, moves) in enumerate(tasks):
            fut = executor.submit(play_game, w_opts, b_opts, moves, base_sec, inc_sec)
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

    print(f"RESULT: {cand_points}/{total_games} (+{wins} ={draws} -{losses}) | {pct:.1f}% | Elo: {elo:+.1f} | CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%] | p2: {p2:.4f} ({elapsed:.1f}s)")

    # Save PGN
    pgn_path = PGN_DIR / pgn_name
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for p_idx, g_num, gres in all_game_results:
            cand_white = (g_num == 1)
            w_name = "Candidate B1 (Option B)" if cand_white else "Reference/Ablation"
            b_name = "Reference/Ablation" if cand_white else "Candidate B1 (Option B)"
            pf.write(f'[Event "{match_id}: {desc}"]\n')
            pf.write(f'[Site "Janus Classical Search Lab"]\n')
            pf.write(f'[Date "{time.strftime("%Y.%m.%d")}"]\n')
            pf.write(f'[White "{w_name}"]\n')
            pf.write(f'[Black "{b_name}"]\n')
            pf.write(f'[Result "{gres["result"]}"]\n')
            pf.write(f'[Termination "{gres["term_reason"]}"]\n\n')
            pf.write(" ".join(gres["moves"]) + f" {gres['result']}\n\n")

    return {
        "match_id": match_id,
        "description": desc,
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
    test_openings = all_openings[:25]

    b0_opts = {"UCI_Variant": "X25", "UCI_ConnectedPawns": "false", "UCI_BackwardPawns": "false", "Hash": "64"}
    b1_opts = {"UCI_Variant": "X25", "UCI_ConnectedPawns": "true",  "UCI_BackwardPawns": "false", "Hash": "64"}
    b2_opts = {"UCI_Variant": "X25", "UCI_ConnectedPawns": "true",  "UCI_BackwardPawns": "true",  "Hash": "64"}

    results = {}
    # Dev Match 1: B1 vs B0 @ 1.0s+50ms
    results["dev_match_1"] = run_single_match(
        "DEV_1_FAST", "B1 (Option B) vs B0 (Baseline) @ 1.0s+50ms",
        b1_opts, b0_opts, test_openings, 1.0, 0.05, "p120_dev_m1_b1_vs_b0_fast.pgn"
    )
    # Dev Match 2: B1 vs B0 @ 3.0s+100ms
    results["dev_match_2"] = run_single_match(
        "DEV_2_SLOW", "B1 (Option B) vs B0 (Baseline) @ 3.0s+100ms",
        b1_opts, b0_opts, test_openings, 3.0, 0.10, "p120_dev_m2_b1_vs_b0_slow.pgn"
    )
    # Dev Match 3: B1 vs B2 @ 1.0s+50ms
    results["dev_match_3"] = run_single_match(
        "DEV_3_BP", "B1 (Option B) vs B2 (Option B + Backward Pawns) @ 1.0s+50ms",
        b1_opts, b2_opts, test_openings, 1.0, 0.05, "p120_dev_m3_b1_vs_b2_fast.pgn"
    )

    out_file = RAW_DIR / "p120_dev_ablations.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nDev ablations summary written to {out_file}")

if __name__ == "__main__":
    main()
