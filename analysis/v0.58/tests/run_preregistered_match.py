"""Project Janus v0.58 - Preregistered Strength Match Runner (N8-A vs C1).

Match: n8_vs_c1 (Candidate Neural N8-A vs Frozen Classical Baseline C1)
Candidate N8-A: Janus Native v0.58 (UseNeuralPolicyOrdering=true, MaxPly=0, MinDepth=4, ScoreWeight=50000)
Baseline C1:    Janus Native v0.56 / v0.57 Frozen (UseKiller=true, UseHistory=true, UseLMR=true, UsePVS=false, UseSEE=false)

Design:
- 100 opening pairs (200 games) from independent_openings_v056.json
- Time Control: 3.0s base + 100ms increment (Fischer 3+0.1)
- Concurrency: 8-Worker Parallel Process Pool
- Adjudication: Strict FIDE referee rules via python-chess (threefold repetition,
  50-move rule, checkmate, stalemate, insufficient material) + 300-ply safety limit.
- Statistics: Paired Student-t (df=99), 10,000 paired bootstrap resamples,
  empirical Elo confidence interval.
"""

from __future__ import annotations

import json
import time
import math
import random
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.56" / "tests"))

from tournament_controller import NativeUCIEngineProcess, adjudicate_board

CORPUS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
PGN_DIR = ROOT / "analysis" / "v0.58" / "pgn"
RAW_DIR = ROOT / "analysis" / "v0.58" / "raw"
CANDIDATE_EXE = ROOT / "analysis" / "v0.58" / "native" / "janus_native_engine.exe"
BASELINE_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"

PGN_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


# Exact Student-t p-value calculation via regularized incomplete beta function
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
    if x < 0.0 or x > 1.0:
        raise ValueError("x out of range in betai")
    if x == 0.0 or x == 1.0:
        return x
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def student_t_two_tailed_p(t_val: float, df: int) -> float:
    t2 = t_val * t_val
    x = df / (df + t2)
    return betai(0.5 * df, 0.5, x)


def play_single_game(
    game_id: int,
    pair_id: int,
    opening_name: str,
    opening_moves: list[str],
    white_is_candidate: bool,
    base_time_sec: float = 3.0,
    inc_sec: float = 0.1,
    max_plies: int = 300,
) -> dict:
    """Executes a single game between N8-A and C1."""
    candidate_opts = {
        "UseNeuralPolicyOrdering": True,
        "NeuralPolicyModelPath": "analysis/v0.58/models/janus_policy_v1.bin",
        "NeuralPolicyMaxPly": 0,
        "NeuralPolicyMinDepth": 4,
        "NeuralPolicyScoreWeight": 50000,
        "UseKillerOrdering": True,
        "UseHistoryOrdering": True,
        "UseLMR": True,
        "UsePVS": False,
        "UseSEEOrdering": False,
        "UseSEEInQuiescence": False,
    }
    baseline_opts = {
        "UseKillerOrdering": True,
        "UseHistoryOrdering": True,
        "UseLMR": True,
        "UsePVS": False,
        "UseSEEOrdering": False,
        "UseSEEInQuiescence": False,
    }

    if white_is_candidate:
        white_engine = NativeUCIEngineProcess(CANDIDATE_EXE, candidate_opts)
        black_engine = NativeUCIEngineProcess(BASELINE_EXE, baseline_opts)
        white_name = "Janus Neural N8-A"
        black_name = "Janus Classical Baseline C1"
    else:
        white_engine = NativeUCIEngineProcess(BASELINE_EXE, baseline_opts)
        black_engine = NativeUCIEngineProcess(CANDIDATE_EXE, candidate_opts)
        white_name = "Janus Classical Baseline C1"
        black_name = "Janus Neural N8-A"

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
    t_start = time.time()

    game_over = False
    result_str = "*"
    termination = "unknown"

    # Adjudicate opening if applicable
    game_over, result_str, termination = adjudicate_board(board, len(moves_played), max_plies)

    while not game_over and len(moves_played) < max_plies:
        active_engine = white_engine if board.turn == chess.WHITE else black_engine

        bestmove_uci, elapsed = active_engine.play_move(board.fen(), wtime_ms, btime_ms, winc_ms, binc_ms)
        elapsed_ms = int(elapsed * 1000)
        move_times.append(elapsed_ms)

        if board.turn == chess.WHITE:
            wtime_ms = max(10, wtime_ms - elapsed_ms + winc_ms)
        else:
            btime_ms = max(10, btime_ms - elapsed_ms + binc_ms)

        if not bestmove_uci:
            # Engine failure / forfeited
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

    white_engine.close()
    black_engine.close()

    total_game_time = time.time() - t_start

    # Determine points from candidate perspective
    if result_str == "1-0":
        cand_points = 1.0 if white_is_candidate else 0.0
    elif result_str == "0-1":
        cand_points = 0.0 if white_is_candidate else 1.0
    elif result_str == "1/2-1/2":
        cand_points = 0.5
    else:
        cand_points = 0.5

    # Build PGN Game object
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Project Janus v0.58 Preregistered Match"
    pgn_game.headers["Site"] = "Antigravity Research Environment"
    pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = str(game_id)
    pgn_game.headers["White"] = white_name
    pgn_game.headers["Black"] = black_name
    pgn_game.headers["Result"] = result_str
    pgn_game.headers["Opening"] = opening_name
    pgn_game.headers["Termination"] = termination
    pgn_game.headers["TimeControl"] = f"{base_time_sec}+{inc_sec}"

    node = pgn_game
    replay_board = chess.Board()
    for m_uci in moves_played:
        m = chess.Move.from_uci(m_uci)
        node = node.add_variation(m)
        replay_board.push(m)

    return {
        "game_id": game_id,
        "pair_id": pair_id,
        "opening": opening_name,
        "white_is_candidate": white_is_candidate,
        "white_name": white_name,
        "black_name": black_name,
        "result": result_str,
        "termination": termination,
        "candidate_points": cand_points,
        "plies": len(moves_played),
        "game_duration_sec": round(total_game_time, 2),
        "pgn": str(pgn_game),
        "moves": moves_played,
    }


def run_preregistered_match(max_workers: int = 8):
    print("=" * 80)
    print("PROJECT JANUS v0.58: PREREGISTERED STRENGTH TOURNAMENT")
    print("Candidate: Janus Neural N8-A vs Control: Janus Classical Baseline C1")
    print(f"Time Control: Fischer 3.0s + 100ms | Concurrency: {max_workers} Workers")
    print("=" * 80)

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    num_pairs = len(openings) # 100
    total_games = num_pairs * 2 # 200

    print(f"Loaded {num_pairs} balanced opening pairs ({total_games} total games).")

    # Build task list: 2 games per pair
    tasks = []
    game_id = 1
    for p_idx, op in enumerate(openings, 1):
        op_name = op.get("name", f"Opening_{p_idx}")
        op_moves = op.get("uci_sequence", op.get("moves", []))

        # Game 1: N8-A is White, C1 is Black
        tasks.append((game_id, p_idx, op_name, op_moves, True))
        game_id += 1

        # Game 2: C1 is White, N8-A is Black
        tasks.append((game_id, p_idx, op_name, op_moves, False))
        game_id += 1

    results = []
    t_match_start = time.time()

    pgn_path = PGN_DIR / "n8_vs_c1_200games.pgn"
    pgn_file = open(pgn_path, "w", encoding="utf-8")

    print(f"\nLaunching {total_games} games across {max_workers} processes...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                play_single_game,
                gid, pid, name, moves, w_cand
            ): (gid, pid)
            for gid, pid, name, moves, w_cand in tasks
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

                # Write to PGN stream
                pgn_file.write(gres["pgn"] + "\n\n")
                pgn_file.flush()

                if completed % 10 == 0 or completed == total_games:
                    win_pct = (cand_total_points / completed) * 100.0
                    elapsed = time.time() - t_match_start
                    print(f"[{completed:3d}/{total_games}] Games done | N8-A Score: {cand_total_points:.1f}/{completed} ({win_pct:.2f}%) | Elapsed: {elapsed:.1f}s")

            except Exception as e:
                print(f"Error in game {gid}: {e}")

    pgn_file.close()
    total_match_duration = time.time() - t_match_start

    # Sort results by game_id
    results.sort(key=lambda x: x["game_id"])

    # Aggregate statistics
    wins = sum(1 for r in results if (r["white_is_candidate"] and r["result"] == "1-0") or (not r["white_is_candidate"] and r["result"] == "0-1"))
    losses = sum(1 for r in results if (r["white_is_candidate"] and r["result"] == "0-1") or (not r["white_is_candidate"] and r["result"] == "1-0"))
    draws = sum(1 for r in results if r["result"] == "1/2-1/2")

    total_score = wins + 0.5 * draws
    score_pct = (total_score / total_games) * 100.0

    # Paired Opening Analysis
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
        p_cand_w = pairs_data[pid].get("cand_white", 0.5)
        p_cand_b = pairs_data[pid].get("cand_black", 0.5)
        cand_pair_score = p_cand_w + p_cand_b # out of 2.0
        base_pair_score = 2.0 - cand_pair_score
        diff = cand_pair_score - base_pair_score # in [-2, +2]
        pair_diffs.append(diff)

    n_pairs = len(pair_diffs) # 100
    mean_diff = sum(pair_diffs) / n_pairs
    variance = sum((d - mean_diff) ** 2 for d in pair_diffs) / (n_pairs - 1) if n_pairs > 1 else 0.0
    std_dev = math.sqrt(variance)
    std_err = std_dev / math.sqrt(n_pairs)

    t_stat = (mean_diff / std_err) if std_err > 0 else 0.0
    df = n_pairs - 1 # 99
    p_val = student_t_two_tailed_p(abs(t_stat), df) if t_stat != 0 else 1.0

    # 10,000 paired bootstrap resamples
    random.seed(42)
    B = 10000
    boot_means = []
    for _ in range(B):
        sample = [random.choice(pair_diffs) for _ in range(n_pairs)]
        boot_means.append(sum(sample) / n_pairs)
    boot_means.sort()
    ci_lower = boot_means[int(0.025 * B)]
    ci_upper = boot_means[int(0.975 * B)]

    # Elo calculation
    # P = score_pct / 100.0
    p_bounded = max(0.001, min(0.999, total_score / total_games))
    elo_diff = -400.0 * math.log10(1.0 / p_bounded - 1.0)

    # Elo bootstrap CI
    boot_elo = []
    for bm in boot_means:
        # bm is mean difference per pair in [-2, 2].
        # Cand score per pair = (bm + 2) / 2 = bm/2 + 1. Out of 2 games: cand_p = cand_score / 2 = bm/4 + 0.5
        cand_p = bm / 4.0 + 0.5
        cand_p_b = max(0.001, min(0.999, cand_p))
        boot_elo.append(-400.0 * math.log10(1.0 / cand_p_b - 1.0))
    boot_elo.sort()
    elo_ci_lower = boot_elo[int(0.025 * B)]
    elo_ci_upper = boot_elo[int(0.975 * B)]

    # Termination breakdown
    terminations = {}
    for r in results:
        term = r["termination"]
        terminations[term] = terminations.get(term, 0) + 1

    print("\n" + "=" * 80)
    print("FINAL MATCH RESULTS: JANUS NEURAL N8-A vs CLASSICAL BASELINE C1")
    print("=" * 80)
    print(f"Total Games: {total_games}")
    print(f"Score: N8-A: {wins} wins, {draws} draws, {losses} losses")
    print(f"Total Points: {total_score:.1f} / {total_games} ({score_pct:.2f}%)")
    print(f"Estimated Elo Advantage: {elo_diff:+.1f} Elo (95% CI: [{elo_ci_lower:+.1f}, {elo_ci_upper:+.1f}])")
    print(f"Paired Difference / Pair: {mean_diff:+.3f} (95% CI: [{ci_lower:+.3f}, {ci_upper:+.3f}])")
    print(f"Paired Student-t: t = {t_stat:+.4f}, p = {p_val:.4e} (df = {df})")
    print(f"Statistically Significant (p < 0.05): {'YES' if p_val < 0.05 else 'NO'}")
    print(f"Total Match Duration: {total_match_duration:.1f}s")
    print("\nTermination Breakdown:")
    for term, cnt in sorted(terminations.items(), key=lambda x: -x[1]):
        print(f"  {term:35s}: {cnt:3d} ({cnt/total_games*100.1:.1f}%)")

    # Save raw json
    match_payload = {
        "match_id": "v058_n8a_vs_c1",
        "candidate": "Janus Neural N8-A",
        "control": "Janus Classical Baseline C1",
        "time_control": "Fischer 3.0s+100ms",
        "total_games": total_games,
        "total_pairs": n_pairs,
        "score": {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "points": total_score,
            "percentage": round(score_pct, 2),
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
        "terminations": terminations,
        "duration_seconds": round(total_match_duration, 2),
        "games": results,
    }

    raw_path = RAW_DIR / "n8_vs_c1_match_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(match_payload, f, indent=2)
    print(f"\nSaved raw match telemetry to {raw_path}")
    print(f"Saved PGN to {pgn_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel worker processes")
    args = parser.parse_args()
    run_preregistered_match(max_workers=args.workers)
