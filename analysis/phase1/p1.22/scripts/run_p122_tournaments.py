#!/usr/bin/env python3
"""
run_p122_tournaments.py
Milestone P1.22: Authoritative 500-Game Tournament Battery.
Candidate: Janus Classical R1.0 (Clean-Sheet Search Core Reboot)

Evaluates:
- Phase 11: Single-Thread Research Qualification (vs Reference X22-S and Baseline X7-S at Fast and Slow TC)
- Phase 12: Four-Thread Parallel Architecture Decision (vs Baseline X12 at Fast TC)
- Phase 13: External Calibration (vs Stockfish 4, Stockfish 11, and Stockfish 19 NNUE)

Integrates:
1. Strict FIDE referee repair (checks can_claim_threefold_repetition() on loop exit; 0 '*' results).
2. Authoritative 6-category pair outcomes (LL, LD, DD, WL, WD, WW).
3. Verified pentanomials (both ascending [0.0..2.0] and descending [2.0..0.0]).
4. Paired standard errors, 95% paired CI, two-tailed p-values, and Wilson score intervals.
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
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.22" / "pgn"
OUT_JSON = ROOT / "analysis" / "phase1" / "p1.22" / "raw" / "p122_tournaments_raw.json"
PGN_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Engine Executables
R1_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
X7_EXE = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
X12_EXE = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
X22_EXE = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
SF4_EXE = Path("E:/ChessXML/tools/stockfish_4/stockfish_4.exe")
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
    if score_fraction <= 0.0:
        return None
    if score_fraction >= 1.0:
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
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        self.send(f"setoption name Threads value {self.threads}")
        for k, v in self.options.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def set_position(self, moves: List[str]):
        if moves:
            self.send(f"position startpos moves {' '.join(moves)}")
        else:
            self.send("position startpos")

    def go(self, wtime: int, btime: int, winc: int, binc: int) -> str:
        self.send(f"go wtime {wtime} btime {btime} winc {winc} binc {binc}")
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if line.startswith("bestmove"):
                parts = line.split()
                return parts[1] if len(parts) > 1 else None

    def quit(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()
            self.proc = None

def play_game(w_cfg: Tuple[Path, str, int, Dict[str, Any]],
              b_cfg: Tuple[Path, str, int, Dict[str, Any]],
              opening_moves: List[str], base_sec: float, inc_sec: float,
              max_moves: int = 150) -> Dict[str, Any]:
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

    # Authoritative FIDE Referee Logic (Fixed threefold repetition detection)
    if result == "*":
        if board.is_checkmate():
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            term_reason = "checkmate"
        elif board.can_claim_threefold_repetition() or board.is_repetition(3):
            result = "1/2-1/2"
            term_reason = "threefold_repetition"
        elif board.is_stalemate():
            result = "1/2-1/2"
            term_reason = "stalemate"
        elif board.is_insufficient_material():
            result = "1/2-1/2"
            term_reason = "insufficient_material"
        elif board.is_fifty_moves():
            result = "1/2-1/2"
            term_reason = "fifty_moves"
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

def run_match(match_id: str, desc: str,
              cand_cfg: Tuple[Path, str, int, Dict[str, Any]],
              ref_cfg: Tuple[Path, str, int, Dict[str, Any]],
              openings: List[Dict[str, Any]], base_sec: float, inc_sec: float,
              pgn_name: str, concurrency: int = 8) -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print(f"MATCH {match_id}: {desc}")
    print(f"Cand: {cand_cfg[1]} ({cand_cfg[2]}T) vs Ref: {ref_cfg[1]} ({ref_cfg[2]}T) | Pairs: {len(openings)} ({len(openings)*2} games)")
    print(f"Time Control: {base_sec}s + {inc_sec}s | Concurrency: {concurrency}")
    print("=" * 80)

    tasks = []
    for p_idx, op in enumerate(openings):
        mvs = op.get("moves", [])
        # Game 1: Cand as White
        tasks.append((p_idx, 1, cand_cfg, ref_cfg, mvs, base_sec, inc_sec))
        # Game 2: Cand as Black
        tasks.append((p_idx, 2, ref_cfg, cand_cfg, mvs, base_sec, inc_sec))

    all_game_results = [None] * len(tasks)
    results_by_pair = {i: [None, None] for i in range(len(openings))}

    t0 = time.time()
    completed = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {
            executor.submit(play_game, w, b, mvs, bs, inc): (p_idx, g_num)
            for (p_idx, g_num, w, b, mvs, bs, inc) in tasks
        }

        for future in as_completed(future_map):
            p_idx, g_num = future_map[future]
            try:
                gres = future.result()
            except Exception as e:
                gres = {"result": "0-1" if g_num == 1 else "1-0", "term_reason": f"exception_{e}", "ply_count": 0, "moves": [], "white": cand_cfg[1] if g_num == 1 else ref_cfg[1], "black": ref_cfg[1] if g_num == 1 else cand_cfg[1]}

            task_idx = p_idx * 2 + (g_num - 1)
            all_game_results[task_idx] = (p_idx, g_num, gres)
            results_by_pair[p_idx][g_num - 1] = gres
            completed += 1

            if completed % 10 == 0 or completed == len(tasks):
                print(f"  Progress: {completed}/{len(tasks)} games finished ({(completed/len(tasks))*100:.1f}%)")

    # Authoritative Tabulation
    wins = draws = losses = 0
    subcat_counts = {"LL": 0, "LD": 0, "DD": 0, "WL": 0, "WD": 0, "WW": 0}
    pair_points_list = []

    for p_idx in range(len(openings)):
        g1, g2 = results_by_pair[p_idx]
        s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
        s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)

        for s in (s1, s2):
            if s == 1.0: wins += 1
            elif s == 0.5: draws += 1
            else: losses += 1

        pair_pts = s1 + s2
        pair_points_list.append(pair_pts)

        if pair_pts == 0.0: cat = "LL"
        elif pair_pts == 0.5: cat = "LD"
        elif pair_pts == 1.0: cat = "DD" if (s1 == 0.5 and s2 == 0.5) else "WL"
        elif pair_pts == 1.5: cat = "WD"
        elif pair_pts == 2.0: cat = "WW"
        subcat_counts[cat] += 1

    total_games = len(tasks)
    cand_points = wins + 0.5 * draws
    score_pct = (cand_points / total_games) * 100.0
    elo = calc_elo(cand_points / total_games)

    pair_scores_norm = [pts / 2.0 for pts in pair_points_list]
    mean_p, ci_low, ci_high, se, p2 = calc_paired_ci_and_pvalue(pair_scores_norm)
    wilson_low, wilson_high = wilson_score_interval(cand_points, total_games)

    penta_ascending = [
        subcat_counts["LL"],
        subcat_counts["LD"],
        subcat_counts["DD"] + subcat_counts["WL"],
        subcat_counts["WD"],
        subcat_counts["WW"]
    ]
    penta_descending = [
        subcat_counts["WW"],
        subcat_counts["WD"],
        subcat_counts["DD"] + subcat_counts["WL"],
        subcat_counts["LD"],
        subcat_counts["LL"]
    ]

    elapsed = time.time() - t0
    elo_str = f"{elo:+.1f}" if elo is not None else ("-inf" if cand_points == 0 else "+inf")

    print(f"\nRESULT {match_id}: {cand_points}/{total_games} (+{wins} ={draws} -{losses}) | {score_pct:.1f}% | Elo: {elo_str}")
    print(f"  Subcategories: LL={subcat_counts['LL']}, LD={subcat_counts['LD']}, DD={subcat_counts['DD']}, WL={subcat_counts['WL']}, WD={subcat_counts['WD']}, WW={subcat_counts['WW']}")
    print(f"  Pentanomial [0.0..2.0]: {penta_ascending}  (LL, LD, 1.0, WD, WW)")
    print(f"  Pentanomial [2.0..0.0]: {penta_descending}  (WW, WD, 1.0, LD, LL)")
    print(f"  Paired 95% CI: [{ci_low*100.0:.1f}%, {ci_high*100.0:.1f}%] | SE: {se:.4f} | p-value: {p2:.4f} ({elapsed:.1f}s)")

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
        "pgn_path": str(pgn_path)
    }

def main():
    print("=" * 80)
    print("PROJECT JANUS — MILESTONE P1.22 AUTHORITATIVE TOURNAMENT BATTERY (500 GMS)")
    print("Candidate: Janus Classical R1.0 (Clean-Sheet Search Core Reboot)")
    print("=" * 80)

    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        openings_pool = json.load(f)

    # Engine Configurations
    # 1. Candidate R1 (1T)
    c_r1_1t = (R1_EXE, "Janus_Classical_R1_0", 1, {"UCI_Variant": "R1"})
    # 2. Candidate R1 (4T)
    c_r1_4t = (R1_EXE, "Janus_Classical_R1_4T", 4, {"UCI_Variant": "R1"})

    # Controls
    ref_x22_1t = (X22_EXE, "Janus_Classical_X22_S", 1, {})
    ref_x7_1t  = (X7_EXE,  "Janus_Classical_X7",    1, {})
    ref_x12_4t = (X12_EXE, "Janus_Classical_X12",   4, {})
    ref_sf4    = (SF4_EXE, "Stockfish_4",           1, {})
    ref_sf11   = (SF11_EXE,"Stockfish_11",          1, {})
    ref_sf19   = (SF19_EXE,"Stockfish_19_NNUE",     1, {})

    matches_data = []

    # ========================================================================
    # Phase 11: Single-Thread Research Qualification (Matches M1-M4)
    # ========================================================================
    # M1: R1 vs Reference X22-S Fast TC (5s+0.05s) - 50 pairs (100 games)
    m1 = run_match("M1", "R1 vs Reference X22-S Fast TC", c_r1_1t, ref_x22_1t,
                   openings_pool[:50], 5.0, 0.05, "match1_r1_vs_x22s_fast.pgn", concurrency=10)
    matches_data.append(m1)

    # M2: R1 vs Reference X22-S Slow TC (15s+0.15s) - 25 pairs (50 games)
    m2 = run_match("M2", "R1 vs Reference X22-S Slow TC", c_r1_1t, ref_x22_1t,
                   openings_pool[:25], 15.0, 0.15, "match2_r1_vs_x22s_slow.pgn", concurrency=10)
    matches_data.append(m2)

    # M3: R1 vs Baseline X7 Fast TC (5s+0.05s) - 50 pairs (100 games)
    m3 = run_match("M3", "R1 vs Baseline X7 Fast TC", c_r1_1t, ref_x7_1t,
                   openings_pool[:50], 5.0, 0.05, "match3_r1_vs_x7_fast.pgn", concurrency=10)
    matches_data.append(m3)

    # M4: R1 vs Baseline X7 Slow TC (15s+0.15s) - 25 pairs (50 games)
    m4 = run_match("M4", "R1 vs Baseline X7 Slow TC", c_r1_1t, ref_x7_1t,
                   openings_pool[:25], 15.0, 0.15, "match4_r1_vs_x7_slow.pgn", concurrency=10)
    matches_data.append(m4)

    # ========================================================================
    # Phase 12: Four-Thread Parallel Architecture Decision (Match M5)
    # ========================================================================
    # M5: R1-4T vs Baseline X12 Fast TC (5s+0.05s) - 50 pairs (100 games)
    m5 = run_match("M5", "R1-4T vs Baseline X12 Fast TC (4T SMP)", c_r1_4t, ref_x12_4t,
                   openings_pool[:50], 5.0, 0.05, "match5_r1_4t_vs_x12_fast.pgn", concurrency=2)
    matches_data.append(m5)

    # ========================================================================
    # Phase 13: External Calibration (Matches M6-M8)
    # ========================================================================
    # M6: R1 vs Stockfish 4 Blitz (3s+0.03s) - 20 pairs (40 games)
    m6 = run_match("M6", "R1 vs Stockfish 4 Blitz", c_r1_1t, ref_sf4,
                   openings_pool[:20], 3.0, 0.03, "match6_r1_vs_sf4_blitz.pgn", concurrency=10)
    matches_data.append(m6)

    # M7: R1 vs Stockfish 11 Blitz (3s+0.03s) - 20 pairs (40 games)
    m7 = run_match("M7", "R1 vs Stockfish 11 Blitz", c_r1_1t, ref_sf11,
                   openings_pool[:20], 3.0, 0.03, "match7_r1_vs_sf11_blitz.pgn", concurrency=10)
    matches_data.append(m7)

    # M8: R1 vs Stockfish 19 NNUE Blitz (3s+0.03s) - 10 pairs (20 games)
    m8 = run_match("M8", "R1 vs Stockfish 19 NNUE Blitz", c_r1_1t, ref_sf19,
                   openings_pool[:10], 3.0, 0.03, "match8_r1_vs_sf19_blitz.pgn", concurrency=10)
    matches_data.append(m8)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(matches_data, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL 8 MATCHES (500 GAMES) COMPLETED SUCCESSFULLY!")
    print(f"Authoritative tournament raw JSON saved to:\n  {OUT_JSON}")
    print("=" * 80)

if __name__ == "__main__":
    main()
