"""Project Janus v0.64 - Secondary Match: Candidate NNUE-V3 vs Neural Baseline N1.

Match: v064_secondary_v3_vs_n1
Candidate: Janus Neural Value V3 (SEF + Phase-Tapered Adaptive Blend 50%, AVX2)
Control:   Janus Neural Baseline N1 (NNUE-V2 Small, Fixed 50/50 Hybrid, AVX2)
Suite:     analysis/v0.64/corpus/independent_openings_v064.json (first 50 pairs = 100 games)
Time:      Fischer 3.0s base + 100ms increment
"""

from __future__ import annotations

import json
import time
import math
import random
import sys
import atexit
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional, Dict, Any, Tuple
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.56" / "tests"))

from tournament_controller import adjudicate_board

CORPUS_PATH = ROOT / "analysis" / "v0.64" / "corpus" / "independent_openings_v064.json"
PGN_DIR = ROOT / "analysis" / "v0.64" / "pgn"
RAW_DIR = ROOT / "analysis" / "v0.64" / "raw"

CANDIDATE_EXE = ROOT / "analysis" / "v0.64" / "native" / "janus_native_engine.exe"
CANDIDATE_MODEL = ROOT / "analysis" / "v0.64" / "models" / "janus_nnue_v3.jnnue"

N1_EXE = ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe"
N1_MODEL = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"

PGN_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


class V64EngineProcess:
    def __init__(self, exe_path: Path, options: Optional[Dict[str, Any]] = None):
        self.exe_path = exe_path
        self.options = options or {}
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(ROOT),
        )
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\n")
        self.p.stdin.flush()
        for opt_name, opt_val in self.options.items():
            val_str = "true" if opt_val is True else ("false" if opt_val is False else str(opt_val))
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
                self.p.wait(timeout=2.0)
            if self.p.stdin and not self.p.stdin.closed:
                self.p.stdin.close()
            if self.p.stdout and not self.p.stdout.closed:
                self.p.stdout.close()
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


# Worker globals
cand_engine: Optional[V64EngineProcess] = None
n1_engine: Optional[V64EngineProcess] = None


def cleanup_worker():
    global cand_engine, n1_engine
    if cand_engine is not None:
        cand_engine.close()
        cand_engine = None
    if n1_engine is not None:
        n1_engine.close()
        n1_engine = None


def init_worker():
    global cand_engine, n1_engine
    cand_opts = {
        "NeuralValueModelPath": str(CANDIDATE_MODEL.resolve()),
        "UseNeuralValue": True,
        "NeuralValueBlend": 50,
        "NeuralValueAdaptiveBlend": True,
        "NeuralValueUseAVX2": True,
        "UseKillerOrdering": True,
        "UseHistoryOrdering": True,
        "UseLMR": True,
        "UsePVS": False,
        "UseSEEOrdering": False,
        "UseSEEInQuiescence": False,
    }
    n1_opts = {
        "NeuralValueModelPath": str(N1_MODEL.resolve()),
        "UseNeuralValue": True,
        "NeuralValueBlend": 50,
        "NeuralValueUseAVX2": True,
        "UseKillerOrdering": True,
        "UseHistoryOrdering": True,
        "UseLMR": True,
        "UsePVS": False,
        "UseSEEOrdering": False,
        "UseSEEInQuiescence": False,
    }
    cand_engine = V64EngineProcess(CANDIDATE_EXE, cand_opts)
    n1_engine = V64EngineProcess(N1_EXE, n1_opts)
    atexit.register(cleanup_worker)


def betacf(a, b, x):
    MAXIT = 200
    EPS = 3.0e-14
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30: d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        del_val = d * c
        h *= del_val
        if abs(del_val - 1.0) < EPS:
            break
    return h


def betai(a, b, x):
    if x < 0.0 or x > 1.0: raise ValueError("x out of range in betai")
    if x == 0.0 or x == 1.0: return x
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def student_t_two_tailed_p(t_val: float, df: int) -> float:
    t2 = t_val * t_val
    x = df / (df + t2)
    return betai(0.5 * df, 0.5, x)


def compute_board_phase(board: chess.Board) -> int:
    phase = 0
    phase += len(board.pieces(chess.KNIGHT, chess.WHITE)) * 1
    phase += len(board.pieces(chess.KNIGHT, chess.BLACK)) * 1
    phase += len(board.pieces(chess.BISHOP, chess.WHITE)) * 1
    phase += len(board.pieces(chess.BISHOP, chess.BLACK)) * 1
    phase += len(board.pieces(chess.ROOK, chess.WHITE)) * 2
    phase += len(board.pieces(chess.ROOK, chess.BLACK)) * 2
    phase += len(board.pieces(chess.QUEEN, chess.WHITE)) * 4
    phase += len(board.pieces(chess.QUEEN, chess.BLACK)) * 4
    return min(24, phase)


def play_single_game(
    game_id: int,
    pair_id: int,
    opening_name: str,
    opening_volume: str,
    opening_eco: str,
    opening_moves: list[str],
    white_is_candidate: bool,
    base_time_sec: float = 3.0,
    inc_sec: float = 0.1,
    max_plies: int = 300,
) -> dict:
    global cand_engine, n1_engine
    assert cand_engine is not None and n1_engine is not None

    if white_is_candidate:
        white_engine = cand_engine
        black_engine = n1_engine
        white_name = "Janus Neural Value V3 (Adaptive)"
        black_name = "Janus Neural Baseline N1 (V2 Fixed)"
    else:
        white_engine = n1_engine
        black_engine = cand_engine
        white_name = "Janus Neural Baseline N1 (V2 Fixed)"
        black_name = "Janus Neural Value V3 (Adaptive)"

    board = chess.Board()
    for m_uci in opening_moves:
        board.push(chess.Move.from_uci(m_uci))

    wtime_ms = int(base_time_sec * 1000)
    btime_ms = int(base_time_sec * 1000)
    winc_ms = int(inc_sec * 1000)
    binc_ms = int(inc_sec * 1000)

    white_engine.ucinewgame()
    black_engine.ucinewgame()

    moves_played = list(opening_moves)
    move_times = []
    min_phase_reached = 24
    t_start = time.time()

    game_over, result_str, termination = adjudicate_board(board, len(moves_played), max_plies)

    while not game_over and len(moves_played) < max_plies:
        cur_phase = compute_board_phase(board)
        if cur_phase < min_phase_reached:
            min_phase_reached = cur_phase

        active_engine = white_engine if board.turn == chess.WHITE else black_engine

        bestmove_uci, elapsed = active_engine.play_move(board.fen(), wtime_ms, btime_ms, winc_ms, binc_ms)
        elapsed_ms = int(elapsed * 1000)
        move_times.append(elapsed_ms)

        if board.turn == chess.WHITE:
            wtime_ms = max(10, wtime_ms - elapsed_ms + winc_ms)
        else:
            btime_ms = max(10, btime_ms - elapsed_ms + binc_ms)

        if not bestmove_uci:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if winner == "Black" else "1-0"
            termination = f"forfeit_no_move_{board.turn}"
            game_over = True
            break

        try:
            m = chess.Move.from_uci(bestmove_uci)
            if m not in board.legal_moves:
                winner = "Black" if board.turn == chess.WHITE else "White"
                result_str = "0-1" if winner == "Black" else "1-0"
                termination = f"illegal_move_{bestmove_uci}"
                game_over = True
                break
            board.push(m)
            moves_played.append(bestmove_uci)
        except Exception as e:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if winner == "Black" else "1-0"
            termination = f"move_parse_error_{e}"
            game_over = True
            break

        game_over, result_str, termination = adjudicate_board(board, len(moves_played), max_plies)

    total_game_time = time.time() - t_start

    if result_str == "1-0":
        cand_points = 1.0 if white_is_candidate else 0.0
    elif result_str == "0-1":
        cand_points = 0.0 if white_is_candidate else 1.0
    elif result_str == "1/2-1/2":
        cand_points = 0.5
    else:
        cand_points = 0.5

    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Project Janus v0.64 Secondary Match: V3 vs N1"
    pgn_game.headers["Site"] = "Janus Research Lab"
    pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = str(game_id)
    pgn_game.headers["White"] = white_name
    pgn_game.headers["Black"] = black_name
    pgn_game.headers["Result"] = result_str
    pgn_game.headers["ECO"] = opening_eco
    pgn_game.headers["Opening"] = opening_name
    pgn_game.headers["Volume"] = opening_volume
    pgn_game.headers["MinPhase"] = str(min_phase_reached)
    pgn_game.headers["Termination"] = termination
    pgn_game.headers["TimeControl"] = f"{base_time_sec}+{inc_sec}"

    node = pgn_game
    replay_board = chess.Board()
    for m_uci in moves_played:
        mv = chess.Move.from_uci(m_uci)
        node = node.add_variation(mv)
        replay_board.push(mv)

    return {
        "game_id": game_id,
        "pair_id": pair_id,
        "opening_name": opening_name,
        "opening_volume": opening_volume,
        "opening_eco": opening_eco,
        "white": white_name,
        "black": black_name,
        "white_is_candidate": white_is_candidate,
        "result": result_str,
        "candidate_points": cand_points,
        "termination": termination,
        "min_phase": min_phase_reached,
        "ply_count": len(moves_played),
        "game_duration_sec": round(total_game_time, 2),
        "avg_move_time_ms": round(sum(move_times) / len(move_times), 1) if move_times else 0,
        "pgn": str(pgn_game),
    }


def run_secondary_tournament(max_workers: int = 4, num_pairs: int = 50):
    print("=" * 80)
    print("PROJECT JANUS v0.64 — SECONDARY MATCH: CANDIDATE NNUE-V3 vs NEURAL N1")
    print("Candidate: Janus Neural Value V3 (SEF + Phase-Tapered Adaptive Blend 50%, AVX2)")
    print("Control:   Janus Neural Baseline N1 (NNUE-V2 Small, Fixed 50/50 Hybrid, AVX2)")
    print(f"Corpus:    analysis/v0.64/corpus/independent_openings_v064.json ({num_pairs} pairs = {num_pairs * 2} games)")
    print("Time:      Fischer 3.0s + 100ms")
    print("=" * 80)

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)

    openings = all_openings[:num_pairs]

    tasks = []
    game_counter = 1
    for pair_idx, op in enumerate(openings):
        name = op.get("name", f"Opening_{pair_idx+1}")
        volume = op.get("volume", "A")
        eco = op.get("eco", "A00")
        moves = op.get("uci_sequence", [])

        # Game A: Candidate is White
        tasks.append((game_counter, pair_idx, name, volume, eco, moves, True))
        game_counter += 1

        # Game B: Candidate is Black
        tasks.append((game_counter, pair_idx, name, volume, eco, moves, False))
        game_counter += 1

    total_games = len(tasks)
    print(f"Loaded {len(openings)} openings. Total games: {total_games}", flush=True)
    print(f"Executing tournament across {max_workers} persistent worker processes...\n", flush=True)

    results = []
    t_match_start = time.time()

    pgn_path = PGN_DIR / "v064_secondary_v3_vs_n1.pgn"
    pgn_file = open(pgn_path, "w", encoding="utf-8")

    with ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
        futures = {
            executor.submit(
                play_single_game,
                gid,
                pid,
                name,
                volume,
                eco,
                moves,
                w_cand,
            ): (gid, pid)
            for gid, pid, name, volume, eco, moves, w_cand in tasks
        }

        completed = 0
        cand_total_points = 0.0

        for fut in as_completed(futures):
            gid, pid = futures[fut]
            try:
                gres = fut.result()
                results.append(gres)
                cand_total_points += gres["candidate_points"]
                completed += 1

                pgn_file.write(gres["pgn"] + "\n\n")
                pgn_file.flush()

                if completed % 10 == 0 or completed == total_games:
                    win_pct = (cand_total_points / completed) * 100.0
                    elapsed = time.time() - t_match_start
                    print(f"[{completed:3d}/{total_games}] Games done | V3 Score: {cand_total_points:.1f}/{completed} ({win_pct:.2f}%) | Elapsed: {elapsed:.1f}s", flush=True)

            except Exception as e:
                print(f"Error in game {gid}: {e}")

    pgn_file.close()
    total_match_duration = time.time() - t_match_start

    results.sort(key=lambda x: x["game_id"])

    wins = sum(1 for r in results if (r["white_is_candidate"] and r["result"] == "1-0") or (not r["white_is_candidate"] and r["result"] == "0-1"))
    losses = sum(1 for r in results if (r["white_is_candidate"] and r["result"] == "0-1") or (not r["white_is_candidate"] and r["result"] == "1-0"))
    draws = sum(1 for r in results if r["result"] == "1/2-1/2")

    total_score = wins + 0.5 * draws
    score_pct = (total_score / total_games) * 100.0

    # Color breakdown
    white_games = [r for r in results if r["white_is_candidate"]]
    black_games = [r for r in results if not r["white_is_candidate"]]

    w_pts = sum(r["candidate_points"] for r in white_games)
    b_pts = sum(r["candidate_points"] for r in black_games)

    # Volume breakdown
    vol_stats = {}
    for r in results:
        vol = r["opening_volume"]
        if vol not in vol_stats:
            vol_stats[vol] = {"games": 0, "points": 0.0, "wins": 0, "draws": 0, "losses": 0}
        vol_stats[vol]["games"] += 1
        vol_stats[vol]["points"] += r["candidate_points"]
        if (r["white_is_candidate"] and r["result"] == "1-0") or (not r["white_is_candidate"] and r["result"] == "0-1"):
            vol_stats[vol]["wins"] += 1
        elif r["result"] == "1/2-1/2":
            vol_stats[vol]["draws"] += 1
        else:
            vol_stats[vol]["losses"] += 1

    # Endgame phase breakdown
    endgame_games = [r for r in results if r["min_phase"] <= 16]
    eg_pts = sum(r["candidate_points"] for r in endgame_games) if endgame_games else 0.0
    eg_wins = sum(1 for r in endgame_games if (r["white_is_candidate"] and r["result"] == "1-0") or (not r["white_is_candidate"] and r["result"] == "0-1"))
    eg_losses = sum(1 for r in endgame_games if (r["white_is_candidate"] and r["result"] == "0-1") or (not r["white_is_candidate"] and r["result"] == "1-0"))
    eg_draws = sum(1 for r in endgame_games if r["result"] == "1/2-1/2")

    # Paired analysis
    pair_diffs = []
    pairs_data = {}
    for r in results:
        pid = r["pair_id"]
        if pid not in pairs_data:
            pairs_data[pid] = {}
        if r["white_is_candidate"]:
            pairs_data[pid]["cand_white"] = r["candidate_points"]
        else:
            pairs_data[pid]["cand_black"] = r["candidate_points"]

    for pid in sorted(pairs_data.keys()):
        cand_pair_score = pairs_data[pid].get("cand_white", 0.5) + pairs_data[pid].get("cand_black", 0.5)
        base_pair_score = 2.0 - cand_pair_score
        pair_diffs.append(cand_pair_score - base_pair_score)

    n_pairs = len(pair_diffs)
    mean_diff = sum(pair_diffs) / n_pairs
    variance = sum((d - mean_diff) ** 2 for d in pair_diffs) / (n_pairs - 1) if n_pairs > 1 else 0.0
    std_dev = math.sqrt(variance)
    std_err = std_dev / math.sqrt(n_pairs)

    t_stat = (mean_diff / std_err) if std_err > 0 else 0.0
    df = n_pairs - 1
    p_val = student_t_two_tailed_p(abs(t_stat), df) if t_stat != 0 else 1.0

    random.seed(42)
    B = 10000
    boot_means = []
    for _ in range(B):
        sample = [random.choice(pair_diffs) for _ in range(n_pairs)]
        boot_means.append(sum(sample) / n_pairs)
    boot_means.sort()
    ci_lower = boot_means[int(0.025 * B)]
    ci_upper = boot_means[int(0.975 * B)]

    p_bounded = max(0.001, min(0.999, total_score / total_games))
    elo_diff = -400.0 * math.log10(1.0 / p_bounded - 1.0)

    boot_elo = []
    for bm in boot_means:
        cand_p = max(0.001, min(0.999, bm / 4.0 + 0.5))
        boot_elo.append(-400.0 * math.log10(1.0 / cand_p - 1.0))
    boot_elo.sort()
    elo_ci_lower = boot_elo[int(0.025 * B)]
    elo_ci_upper = boot_elo[int(0.975 * B)]

    print("\n" + "=" * 80)
    print("SECONDARY COMPARISON RESULTS: CANDIDATE NNUE-V3 vs NEURAL N1 (v0.64)")
    print("=" * 80)
    print(f"Total Games: {total_games} ({n_pairs} opening pairs)")
    print(f"Score: NNUE-V3: {wins} wins, {draws} draws, {losses} losses")
    print(f"Total Points: {total_score:.1f} / {total_games} ({score_pct:.2f}%)")
    print(f"Estimated Elo Advantage: {elo_diff:+.1f} Elo (95% CI: [{elo_ci_lower:+.1f}, {elo_ci_upper:+.1f}])")
    print(f"Paired Difference / Pair: {mean_diff:+.3f} (95% CI: [{ci_lower:+.3f}, {ci_upper:+.3f}])")
    print(f"Paired Student-t: t = {t_stat:+.4f}, p = {p_val:.4e} (df = {df})")
    print(f"Statistically Significant (p < 0.05): {'YES' if p_val < 0.05 else 'NO'}")
    print(f"White Score: {w_pts:.1f} / {len(white_games)} ({w_pts/len(white_games)*100:.1f}%)")
    print(f"Black Score: {b_pts:.1f} / {len(black_games)} ({b_pts/len(black_games)*100:.1f}%)")
    print(f"Endgame Reached (Phase <= 16): {len(endgame_games)} games | Score: {eg_pts:.1f}/{len(endgame_games)} ({eg_wins}W / {eg_draws}D / {eg_losses}L)")
    print(f"Total Match Duration: {total_match_duration:.1f}s")

    match_payload = {
        "match_id": "v064_secondary_v3_vs_n1",
        "candidate": "Janus Neural Value V3 (Adaptive Blend 50%, AVX2, SEF)",
        "control": "Janus Neural Baseline N1 (NNUE-V2 Small Hybrid 50/50)",
        "time_control": "Fischer 3.0s+100ms",
        "opening_suite": "analysis/v0.64/corpus/independent_openings_v064.json",
        "total_games": total_games,
        "total_pairs": n_pairs,
        "score": {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "points": total_score,
            "percentage": round(score_pct, 2),
        },
        "color_performance": {
            "white_points": w_pts,
            "white_games": len(white_games),
            "white_pct": round(w_pts / len(white_games) * 100.0, 2),
            "black_points": b_pts,
            "black_games": len(black_games),
            "black_pct": round(b_pts / len(black_games) * 100.0, 2),
        },
        "volume_performance": vol_stats,
        "endgame_performance": {
            "games_with_phase_le_16": len(endgame_games),
            "points": eg_pts,
            "wins": eg_wins,
            "draws": eg_draws,
            "losses": eg_losses,
            "percentage": round(eg_pts / len(endgame_games) * 100.0, 2) if endgame_games else 0.0,
        },
        "paired_statistics": {
            "mean_pair_difference": round(mean_diff, 4),
            "std_err": round(std_err, 4),
            "t_statistic": round(t_stat, 4),
            "degrees_of_freedom": df,
            "p_value": float(f"{p_val:.4e}"),
            "statistically_significant": (p_val < 0.05),
            "bootstrap_mean_ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
        },
        "elo": {
            "delta_elo": round(elo_diff, 1),
            "bootstrap_elo_ci_95": [round(elo_ci_lower, 1), round(elo_ci_upper, 1)],
        },
        "duration_seconds": round(total_match_duration, 2),
        "games": results,
    }

    raw_path = RAW_DIR / "v064_secondary_v3_vs_n1_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(match_payload, f, indent=2)
    print(f"\nSaved secondary telemetry to {raw_path}")
    print(f"Saved secondary PGN to {pgn_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel worker processes")
    parser.add_argument("--pairs", type=int, default=50, help="Number of opening pairs")
    args = parser.parse_args()
    run_secondary_tournament(max_workers=args.workers, num_pairs=args.pairs)

