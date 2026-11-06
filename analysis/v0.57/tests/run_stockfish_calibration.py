"""Project Janus v0.57 - Reusable Stockfish 19 Calibration Match Runner.

Runs Janus Native N5 vs Stockfish 19 across 4 calibration tiers:
- SF19-A: UCI_LimitStrength=true, UCI_Elo=1320 (20 games: 10 opening pairs)
- SF19-B: UCI_LimitStrength=true, UCI_Elo=1600 (20 games: 10 opening pairs)
- SF19-C: UCI_LimitStrength=true, UCI_Elo=2000 (20 games: 10 opening pairs)
- SF19-D: UCI_LimitStrength=false (Unrestricted) (20 games: 10 opening pairs)

Total: 80 games under Fischer Blitz 3.0s base + 100ms increment.
Adjudication: Strict FIDE rules via python-chess + 300-ply non-FIDE safety horizon.
Outputs:
- PGN per tier and combined
- JSON raw telemetry per tier and combined
- CSV per-game summary
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[3]
V57_DIR = ROOT / "analysis" / "v0.57"
PGN_DIR = V57_DIR / "pgn"
RAW_DIR = V57_DIR / "raw"
CORPUS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
JANUS_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
STOCKFISH_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

PGN_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class UCIProcess:
    """Manages an external UCI chess engine process."""

    def __init__(self, exe_path: Path, options: Optional[Dict[str, Any]] = None):
        self.exe_path = exe_path
        self.options = options or {}
        self.p = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "uciok":
                break

        for opt_name, opt_val in self.options.items():
            if isinstance(opt_val, bool):
                val_str = "true" if opt_val else "false"
            else:
                val_str = str(opt_val)
            self.p.stdin.write(f"setoption name {opt_name} value {val_str}\n")

        self.p.stdin.write("isready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def ucinewgame(self):
        self.p.stdin.write("ucinewgame\nisready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def play_move(self, fen: str, wtime_ms: int, btime_ms: int, winc_ms: int, binc_ms: int) -> Tuple[Optional[str], float]:
        t0 = time.perf_counter()
        cmd = f"position fen {fen}\ngo wtime {wtime_ms} btime {btime_ms} winc {winc_ms} binc {binc_ms}\n"
        self.p.stdin.write(cmd)
        self.p.stdin.flush()
        bestmove = None
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) >= 2:
                    bestmove = tokens[1]
                break
        elapsed = time.perf_counter() - t0
        return bestmove, elapsed

    def close(self):
        try:
            if self.p.poll() is None:
                self.p.stdin.write("quit\n")
                self.p.stdin.flush()
                self.p.wait(timeout=2)
            if self.p.stdin and not self.p.stdin.closed:
                self.p.stdin.close()
            if self.p.stdout and not self.p.stdout.closed:
                self.p.stdout.close()
        except Exception:
            self.p.kill()


def adjudicate_board(board: chess.Board, ply_count: int, max_plies: int = 300) -> Tuple[bool, str, str]:
    """Strict FIDE adjudication via python-chess + safety horizon."""
    if board.is_checkmate():
        winner = "White" if board.turn == chess.BLACK else "Black"
        result_str = "1-0" if winner == "White" else "0-1"
        return True, result_str, f"checkmate_{winner.lower()}"

    if board.is_stalemate():
        return True, "1/2-1/2", "draw_stalemate"

    if board.is_insufficient_material():
        return True, "1/2-1/2", "draw_insufficient_material"

    if board.is_seventyfive_moves():
        return True, "1/2-1/2", "draw_seventyfive_moves"

    if board.is_fivefold_repetition():
        return True, "1/2-1/2", "draw_fivefold_repetition"

    if board.can_claim_threefold_repetition():
        return True, "1/2-1/2", "draw_threefold_repetition"

    if board.can_claim_fifty_moves():
        return True, "1/2-1/2", "draw_fifty_moves"

    if ply_count >= max_plies:
        return True, "1/2-1/2", "safety_limit_300_plies"

    return False, "*", "in_progress"


def play_single_game(
    white_proc: UCIProcess,
    black_proc: UCIProcess,
    white_name: str,
    black_name: str,
    opening_fen: str,
    round_num: int,
    base_time_ms: int = 3000,
    inc_ms: int = 100,
    max_plies: int = 300,
) -> Dict[str, Any]:
    white_proc.ucinewgame()
    black_proc.ucinewgame()

    board = chess.Board(opening_fen)
    wtime_ms = base_time_ms
    btime_ms = base_time_ms

    moves_played = []
    ply_count = 0
    t_start = time.perf_counter()

    while True:
        is_over, term_res, term_reason = adjudicate_board(board, ply_count, max_plies=max_plies)
        if is_over:
            break

        current_turn = board.turn
        current_proc = white_proc if current_turn == chess.WHITE else black_proc

        cur_fen = board.fen()
        bestmove_uci, elapsed_s = current_proc.play_move(
            cur_fen,
            wtime_ms=wtime_ms,
            btime_ms=btime_ms,
            winc_ms=inc_ms,
            binc_ms=inc_ms,
        )
        elapsed_ms = int(elapsed_s * 1000)

        if not bestmove_uci:
            term_res = "0-1" if current_turn == chess.WHITE else "1-0"
            term_reason = f"engine_stall_{'white' if current_turn == chess.WHITE else 'black'}"
            break

        try:
            move = chess.Move.from_uci(bestmove_uci)
        except Exception:
            term_res = "0-1" if current_turn == chess.WHITE else "1-0"
            term_reason = f"illegal_uci_{bestmove_uci}"
            break

        if not board.is_legal(move):
            term_res = "0-1" if current_turn == chess.WHITE else "1-0"
            term_reason = f"illegal_move_{bestmove_uci}"
            break

        if current_turn == chess.WHITE:
            wtime_ms = max(10, wtime_ms - elapsed_ms + inc_ms)
        else:
            btime_ms = max(10, btime_ms - elapsed_ms + inc_ms)

        board.push(move)
        moves_played.append(bestmove_uci)
        ply_count += 1

    duration = time.perf_counter() - t_start

    return {
        "round": round_num,
        "white": white_name,
        "black": black_name,
        "opening_fen": opening_fen,
        "moves": moves_played,
        "plies": ply_count,
        "result": term_res,
        "termination": term_reason,
        "duration_sec": duration,
        "final_fen": board.fen(),
    }


def worker_play_tier_pair(args: Tuple) -> Dict[str, Any]:
    tier_name, pair_data, janus_opts, sf_opts, janus_name, sf_name = args
    pair_id = pair_data["pair_id"]
    opening_fen = pair_data["fen"]

    p_janus = UCIProcess(JANUS_EXE, options=janus_opts)
    p_sf = UCIProcess(STOCKFISH_EXE, options=sf_opts)

    try:
        # Game 1: Janus is White
        g1 = play_single_game(
            white_proc=p_janus,
            black_proc=p_sf,
            white_name=janus_name,
            black_name=sf_name,
            opening_fen=opening_fen,
            round_num=2 * pair_id - 1,
        )

        # Game 2: Janus is Black
        g2 = play_single_game(
            white_proc=p_sf,
            black_proc=p_janus,
            white_name=sf_name,
            black_name=janus_name,
            opening_fen=opening_fen,
            round_num=2 * pair_id,
        )
    finally:
        p_janus.close()
        p_sf.close()

    def score_for_janus(res: str, janus_is_white: bool) -> float:
        if res == "1/2-1/2": return 0.5
        if res == "1-0": return 1.0 if janus_is_white else 0.0
        if res == "0-1": return 0.0 if janus_is_white else 1.0
        return 0.5

    s1 = score_for_janus(g1["result"], janus_is_white=True)
    s2 = score_for_janus(g2["result"], janus_is_white=False)

    return {
        "tier": tier_name,
        "pair_id": pair_id,
        "eco": pair_data["eco"],
        "name": pair_data["name"],
        "opening_fen": opening_fen,
        "game_1": g1,
        "game_2": g2,
        "janus_points": s1 + s2,
        "sf_points": (1.0 - s1) + (1.0 - s2),
        "diff": (s1 + s2) - ((1.0 - s1) + (1.0 - s2)),
    }


def run_calibration_ladder(num_workers: int = 4):
    print("=================================================================")
    print("PROJECT JANUS v0.57 — STOCKFISH 19 CALIBRATION MATCH RUNNER")
    print("=================================================================")

    janus_sha256 = compute_sha256(JANUS_EXE)
    sf_sha256 = compute_sha256(STOCKFISH_EXE)
    print(f"Janus N5 Executable:      {JANUS_EXE} (SHA-256: {janus_sha256[:16]}...)")
    print(f"Stockfish 19 Executable:  {STOCKFISH_EXE} (SHA-256: {sf_sha256[:16]}...)")

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)
    openings = all_openings[:10]  # First 10 balanced opening pairs
    print(f"Selected {len(openings)} opening pairs (20 games per tier).")

    janus_opts = {
        "UseKillerOrdering": "true",
        "UseHistoryOrdering": "true",
        "UsePVS": "false",
        "UseLMR": "true",
        "UseSEEOrdering": "false",
        "UseSEEInQuiescence": "false",
    }

    tiers = [
        {
            "id": "sf19_a_elo1320",
            "name": "SF19-A (Elo 1320)",
            "sf_name": "Stockfish 19 (Elo 1320)",
            "sf_opts": {"UCI_LimitStrength": "true", "UCI_Elo": 1320, "Threads": 1, "Hash": 16},
        },
        {
            "id": "sf19_b_elo1600",
            "name": "SF19-B (Elo 1600)",
            "sf_name": "Stockfish 19 (Elo 1600)",
            "sf_opts": {"UCI_LimitStrength": "true", "UCI_Elo": 1600, "Threads": 1, "Hash": 16},
        },
        {
            "id": "sf19_c_elo2000",
            "name": "SF19-C (Elo 2000)",
            "sf_name": "Stockfish 19 (Elo 2000)",
            "sf_opts": {"UCI_LimitStrength": "true", "UCI_Elo": 2000, "Threads": 1, "Hash": 16},
        },
        {
            "id": "sf19_d_unrestricted",
            "name": "SF19-D (Unrestricted)",
            "sf_name": "Stockfish 19 (Unrestricted)",
            "sf_opts": {"UCI_LimitStrength": "false", "Threads": 1, "Hash": 16},
        },
    ]

    all_tier_results = {}
    csv_rows = []
    combined_pgn_path = PGN_DIR / "stockfish_19_calibration_all.pgn"
    f_comb_pgn = open(combined_pgn_path, "w", encoding="utf-8")

    total_start = time.perf_counter()

    for tier in tiers:
        t_id = tier["id"]
        t_name = tier["name"]
        sf_name = tier["sf_name"]
        sf_opts = tier["sf_opts"]
        janus_name = "Janus 0.57 N5 (Production Baseline)"

        print(f"\n-------------------------------------------------------------")
        print(f"RUNNING CALIBRATION TIER: {t_name}")
        print(f"Stockfish Options: {sf_opts}")
        print(f"-------------------------------------------------------------")

        work_items = [
            (t_id, op, janus_opts, sf_opts, janus_name, sf_name)
            for op in openings
        ]

        pair_results = []
        tier_start = time.perf_counter()

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_play_tier_pair, item) for item in work_items]
            for fut in as_completed(futures):
                res = fut.result()
                pair_results.append(res)
                pts = sum(p["janus_points"] for p in pair_results)
                tot = len(pair_results) * 2
                print(f"  Tier {t_id} progress: {len(pair_results)}/10 pairs ({tot}/20 games) | Janus: {pts:.1f}/{tot} ({pts/tot*100:.1f}%)")

        tier_duration = time.perf_counter() - tier_start
        pair_results.sort(key=lambda x: x["pair_id"])

        # Aggregate tier
        janus_wins = 0
        janus_draws = 0
        janus_losses = 0
        janus_white_pts = 0.0
        janus_black_pts = 0.0
        terminations = {}
        tier_games = []

        tier_pgn_path = PGN_DIR / f"{t_id}.pgn"
        with open(tier_pgn_path, "w", encoding="utf-8") as f_tier_pgn:
            for p in pair_results:
                for g_idx, g in enumerate([p["game_1"], p["game_2"]]):
                    tier_games.append(g)
                    res = g["result"]
                    term = g["termination"]
                    terminations[term] = terminations.get(term, 0) + 1

                    janus_is_white = (g_idx == 0)
                    if res == "1/2-1/2":
                        janus_draws += 1
                        if janus_is_white: janus_white_pts += 0.5
                        else: janus_black_pts += 0.5
                    elif res == "1-0":
                        if janus_is_white:
                            janus_wins += 1
                            janus_white_pts += 1.0
                        else:
                            janus_losses += 1
                    elif res == "0-1":
                        if janus_is_white:
                            janus_losses += 1
                        else:
                            janus_wins += 1
                            janus_black_pts += 1.0

                    # Write PGN
                    pgn_game = chess.pgn.Game()
                    pgn_game.headers["Event"] = f"Project Janus v0.57 Calibration ({t_id})"
                    pgn_game.headers["Site"] = "Antigravity Research Sandbox"
                    pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
                    pgn_game.headers["Round"] = str(g["round"])
                    pgn_game.headers["White"] = g["white"]
                    pgn_game.headers["Black"] = g["black"]
                    pgn_game.headers["Result"] = g["result"]
                    pgn_game.headers["Termination"] = g["termination"]
                    pgn_game.headers["TimeControl"] = "3.0+0.1"
                    pgn_game.headers["ECO"] = p["eco"]
                    pgn_game.headers["Opening"] = p["name"]
                    pgn_game.headers["FEN"] = g["opening_fen"]

                    curr_node = pgn_game
                    for m_uci in g["moves"]:
                        m = chess.Move.from_uci(m_uci)
                        curr_node = curr_node.add_variation(m)

                    f_tier_pgn.write(str(pgn_game) + "\n\n")
                    f_comb_pgn.write(str(pgn_game) + "\n\n")

                    csv_rows.append({
                        "tier": t_id,
                        "round": g["round"],
                        "pair_id": p["pair_id"],
                        "eco": p["eco"],
                        "opening_name": p["name"],
                        "white": g["white"],
                        "black": g["black"],
                        "result": g["result"],
                        "janus_points": 1.0 if (janus_is_white and res == "1-0") or (not janus_is_white and res == "0-1") else (0.5 if res == "1/2-1/2" else 0.0),
                        "termination": g["termination"],
                        "plies": g["plies"],
                        "duration_sec": round(g["duration_sec"], 2),
                    })

        total_pts = janus_white_pts + janus_black_pts
        tot_g = len(tier_games)
        pct = (total_pts / tot_g) * 100.0 if tot_g > 0 else 0.0

        # Estimated Elo diff
        S = max(0.01, min(0.99, total_pts / tot_g))
        elo_diff = -400.0 * math.log10(1.0 / S - 1.0)

        tier_summary = {
            "tier_id": t_id,
            "tier_name": t_name,
            "sf_options": sf_opts,
            "total_games": tot_g,
            "total_pairs": len(pair_results),
            "janus_wins": janus_wins,
            "janus_draws": janus_draws,
            "janus_losses": janus_losses,
            "janus_points": total_pts,
            "janus_score_pct": pct,
            "janus_white_pts": janus_white_pts,
            "janus_black_pts": janus_black_pts,
            "estimated_elo_diff": elo_diff,
            "duration_sec": tier_duration,
            "average_plies": sum(g["plies"] for g in tier_games) / tot_g if tot_g > 0 else 0,
            "terminations": terminations,
        }

        all_tier_results[t_id] = {
            "summary": tier_summary,
            "pairs": pair_results,
        }

        tier_json_path = RAW_DIR / f"{t_id}_raw.json"
        with open(tier_json_path, "w", encoding="utf-8") as f_json:
            json.dump(all_tier_results[t_id], f_json, indent=2)

        print(f"Tier {t_name} Completed in {tier_duration:.1f}s:")
        print(f"  Score:       {total_pts:.1f}/{tot_g} ({pct:.1f}%) [+{janus_wins} ={janus_draws} -{janus_losses}]")
        print(f"  White Score: {janus_white_pts:.1f}/10 | Black Score: {janus_black_pts:.1f}/10")
        print(f"  Elo Diff:    {elo_diff:+.1f} vs opponent target")
        print(f"  Terminations: {terminations}")

    f_comb_pgn.close()

    # Save Combined JSON
    combined_summary = {
        "milestone": "v0.57",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_calibration_games": len(csv_rows),
        "janus_engine": {
            "name": "Janus 0.57 N5 Native",
            "path": str(JANUS_EXE),
            "sha256": janus_sha256,
            "options": janus_opts,
        },
        "stockfish_engine": {
            "name": "Stockfish 19 x64 AVX2",
            "path": str(STOCKFISH_EXE),
            "sha256": sf_sha256,
        },
        "tiers": {t_id: data["summary"] for t_id, data in all_tier_results.items()},
    }

    combined_json_path = RAW_DIR / "stockfish_19_calibration_raw.json"
    with open(combined_json_path, "w", encoding="utf-8") as f_comb_json:
        json.dump({"summary": combined_summary, "tier_data": all_tier_results}, f_comb_json, indent=2)

    # Save CSV
    csv_path = RAW_DIR / "stockfish_19_calibration_games.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f_csv:
        fieldnames = ["tier", "round", "pair_id", "eco", "opening_name", "white", "black", "result", "janus_points", "termination", "plies", "duration_sec"]
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\n=================================================================")
    print(f"ALL 4 CALIBRATION TIERS COMPLETED ({len(csv_rows)} total games)")
    print(f"Combined PGN: {combined_pgn_path}")
    print(f"Combined JSON: {combined_json_path}")
    print(f"Games CSV:    {csv_path}")
    print(f"Total Time:   {time.perf_counter() - total_start:.1f}s")
    print(f"=================================================================\n")

    return combined_summary


if __name__ == "__main__":
    run_calibration_ladder(num_workers=4)

