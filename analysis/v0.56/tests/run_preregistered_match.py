"""Project Janus v0.56 - Preregistered Strength Match Runner.

Match: n7_vs_n5 (Candidate N7 vs Baseline N5)
Candidate: Janus N7 (UseSEEOrdering=true, UseSEEInQuiescence=true)
Baseline:  Janus N5 (UseSEEOrdering=false, UseSEEInQuiescence=false)

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
PGN_DIR = ROOT / "analysis" / "v0.56" / "pgn"
RAW_DIR = ROOT / "analysis" / "v0.56" / "raw"
EXE_PATH = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"

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


def student_t_two_sided_p(t_stat: float, df: int) -> float:
    if df <= 0:
        return 1.0
    x = df / (df + t_stat * t_stat)
    p = betai(0.5 * df, 0.5, x)
    return max(0.0, min(1.0, p))


def play_single_game_worker(
    white_proc: NativeUCIEngineProcess,
    black_proc: NativeUCIEngineProcess,
    white_name: str,
    black_name: str,
    opening_fen: str,
    round_num: int,
) -> dict:
    white_proc.ucinewgame()
    black_proc.ucinewgame()

    board = chess.Board(opening_fen)

    wtime_ms = 3000
    btime_ms = 3000
    inc_ms = 100

    moves_played = []
    ply_count = 0
    t_start = time.perf_counter()

    while True:
        is_over, term_res, term_reason = adjudicate_board(board, ply_count, max_plies=300)
        if is_over:
            break

        current_turn = board.turn
        current_proc = white_proc if current_turn == chess.WHITE else black_proc

        cur_fen = board.fen()
        move_uci, elapsed_s = current_proc.play_move(
            cur_fen,
            wtime_ms=wtime_ms,
            btime_ms=btime_ms,
            winc_ms=inc_ms,
            binc_ms=inc_ms,
        )
        elapsed_ms = int(elapsed_s * 1000)

        if not move_uci:
            term_res = "0-1" if current_turn == chess.WHITE else "1-0"
            term_reason = "engine_stall"
            break

        try:
            move = chess.Move.from_uci(move_uci)
        except Exception:
            term_res = "0-1" if current_turn == chess.WHITE else "1-0"
            term_reason = f"illegal_uci_{move_uci}"
            break

        if not board.is_legal(move):
            term_res = "0-1" if current_turn == chess.WHITE else "1-0"
            term_reason = f"illegal_move_{move_uci}"
            break

        if current_turn == chess.WHITE:
            wtime_ms = max(10, wtime_ms - elapsed_ms + inc_ms)
        else:
            btime_ms = max(10, btime_ms - elapsed_ms + inc_ms)

        board.push(move)
        moves_played.append(move_uci)
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


def worker_play_pair(pair_data: dict, cand_opts: dict, ctrl_opts: dict, cand_name: str, ctrl_name: str) -> dict:
    pair_id = pair_data["pair_id"]
    opening_fen = pair_data["fen"]

    p_cand = NativeUCIEngineProcess(EXE_PATH, options=cand_opts)
    p_ctrl = NativeUCIEngineProcess(EXE_PATH, options=ctrl_opts)

    try:
        # Game 1: Candidate is White
        g1 = play_single_game_worker(
            white_proc=p_cand,
            black_proc=p_ctrl,
            white_name=cand_name,
            black_name=ctrl_name,
            opening_fen=opening_fen,
            round_num=2 * pair_id - 1,
        )

        # Game 2: Candidate is Black
        g2 = play_single_game_worker(
            white_proc=p_ctrl,
            black_proc=p_cand,
            white_name=ctrl_name,
            black_name=cand_name,
            opening_fen=opening_fen,
            round_num=2 * pair_id,
        )
    finally:
        p_cand.close()
        p_ctrl.close()

    def score_for_cand(res: str, cand_is_white: bool) -> float:
        if res == "1/2-1/2": return 0.5
        if res == "1-0": return 1.0 if cand_is_white else 0.0
        if res == "0-1": return 0.0 if cand_is_white else 1.0
        return 0.5

    s1 = score_for_cand(g1["result"], cand_is_white=True)
    s2 = score_for_cand(g2["result"], cand_is_white=False)

    cand_pair_points = s1 + s2
    ctrl_pair_points = (1.0 - s1) + (1.0 - s2)
    diff = cand_pair_points - ctrl_pair_points

    return {
        "pair_id": pair_id,
        "eco": pair_data["eco"],
        "name": pair_data["name"],
        "opening_fen": opening_fen,
        "game_1": g1,
        "game_2": g2,
        "cand_points": cand_pair_points,
        "ctrl_points": ctrl_pair_points,
        "diff": diff,
    }


def run_match():
    match_id = "n7_vs_n5"
    cand_name = "Janus 0.56 N7 (Combined SEE)"
    ctrl_name = "Janus 0.56 N5 (Baseline)"
    cand_opts = {
        "UseKillerOrdering": "true",
        "UseHistoryOrdering": "true",
        "UsePVS": "false",
        "UseLMR": "true",
        "UseSEEOrdering": "true",
        "UseSEEInQuiescence": "true",
    }
    ctrl_opts = {
        "UseKillerOrdering": "true",
        "UseHistoryOrdering": "true",
        "UsePVS": "false",
        "UseLMR": "true",
        "UseSEEOrdering": "false",
        "UseSEEInQuiescence": "false",
    }

    pgn_path = PGN_DIR / f"{match_id}.pgn"
    raw_path = RAW_DIR / f"{match_id}_raw.json"

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    total_pairs = len(openings)
    total_games = total_pairs * 2

    print(f"\n=======================================================")
    print(f"LAUNCHING JANUS v0.56 PREREGISTERED MATCH: {match_id}")
    print(f"Candidate: {cand_name}")
    print(f"Baseline:  {ctrl_name}")
    print(f"Time Control: Fischer 3.0s + 100ms increment")
    print(f"Total Games: {total_games} ({total_pairs} paired openings)")
    print(f"Corpus: {CORPUS_PATH.name}")
    print(f"Process Concurrency: 8 workers")
    print(f"=======================================================\n")

    t_start = time.perf_counter()
    pair_results = []
    completed_pairs = 0

    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(worker_play_pair, op, cand_opts, ctrl_opts, cand_name, ctrl_name): op["pair_id"]
            for op in openings
        }

        for fut in as_completed(futures):
            res = fut.result()
            pair_results.append(res)
            completed_pairs += 1
            if completed_pairs % 10 == 0 or completed_pairs == total_pairs:
                cand_pts = sum(p["cand_points"] for p in pair_results)
                tot_g = completed_pairs * 2
                pct = (cand_pts / tot_g) * 100.0
                print(f"Progress: {completed_pairs}/{total_pairs} pairs ({tot_g}/{total_games} games) | Cand: {cand_pts:.1f}/{tot_g} ({pct:.2f}%)")

    total_duration = time.perf_counter() - t_start

    # Sort pairs by pair_id
    pair_results.sort(key=lambda x: x["pair_id"])

    # Flatten games
    all_games = []
    pair_differences = []
    cand_white_score = 0.0
    cand_black_score = 0.0
    cand_wins = 0
    cand_draws = 0
    cand_losses = 0
    terminations = {}

    for p in pair_results:
        pair_differences.append(p["diff"])
        all_games.append(p["game_1"])
        all_games.append(p["game_2"])

        # Game 1: Cand is White
        g1_res = p["game_1"]["result"]
        t1 = p["game_1"]["termination"]
        terminations[t1] = terminations.get(t1, 0) + 1
        if g1_res == "1-0":
            cand_white_score += 1.0
            cand_wins += 1
        elif g1_res == "1/2-1/2":
            cand_white_score += 0.5
            cand_draws += 1
        else:
            cand_losses += 1

        # Game 2: Cand is Black
        g2_res = p["game_2"]["result"]
        t2 = p["game_2"]["termination"]
        terminations[t2] = terminations.get(t2, 0) + 1
        if g2_res == "0-1":
            cand_black_score += 1.0
            cand_wins += 1
        elif g2_res == "1/2-1/2":
            cand_black_score += 0.5
            cand_draws += 1
        else:
            cand_losses += 1

    cand_total_points = cand_white_score + cand_black_score
    cand_score_pct = (cand_total_points / total_games) * 100.0

    # Paired Statistics
    n_pairs = len(pair_differences)
    mean_d = sum(pair_differences) / n_pairs
    variance_d = sum((d - mean_d) ** 2 for d in pair_differences) / (n_pairs - 1) if n_pairs > 1 else 0.0
    std_d = math.sqrt(variance_d)
    se_d = std_d / math.sqrt(n_pairs) if n_pairs > 0 else 0.0

    t_stat = (mean_d / se_d) if se_d > 0 else 0.0
    df = n_pairs - 1
    two_sided_p = student_t_two_sided_p(t_stat, df)

    # 10,000 paired bootstrap resamples
    random.seed(42)
    B = 10000
    boot_means = []
    for _ in range(B):
        sample = [random.choice(pair_differences) for _ in range(n_pairs)]
        boot_means.append(sum(sample) / n_pairs)
    boot_means.sort()

    ci_lower_diff = boot_means[int(0.025 * B)]
    ci_upper_diff = boot_means[int(0.975 * B)]

    # Elo conversion
    S = max(0.001, min(0.999, cand_total_points / total_games))
    elo_diff = -400.0 * math.log10(1.0 / S - 1.0)

    def elo_from_diff_mean(m_diff):
        cand_p = (m_diff + 2.0) / 4.0
        cand_p = max(0.001, min(0.999, cand_p))
        return -400.0 * math.log10(1.0 / cand_p - 1.0)

    elo_ci_lower = elo_from_diff_mean(ci_lower_diff)
    elo_ci_upper = elo_from_diff_mean(ci_upper_diff)

    summary = {
        "match_id": match_id,
        "candidate": cand_name,
        "baseline": ctrl_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_games": total_games,
        "total_pairs": total_pairs,
        "duration_sec": total_duration,
        "cand_wins": cand_wins,
        "cand_draws": cand_draws,
        "cand_losses": cand_losses,
        "cand_points": cand_total_points,
        "cand_score_pct": cand_score_pct,
        "cand_white_score": cand_white_score,
        "cand_black_score": cand_black_score,
        "paired_diff_mean": mean_d,
        "paired_diff_std": std_d,
        "paired_diff_se": se_d,
        "t_statistic": t_stat,
        "degrees_of_freedom": df,
        "two_sided_p_value": two_sided_p,
        "bootstrap_ci_95_diff": [ci_lower_diff, ci_upper_diff],
        "elo_difference": elo_diff,
        "bootstrap_ci_95_elo": [elo_ci_lower, elo_ci_upper],
        "average_game_plies": sum(g["plies"] for g in all_games) / len(all_games) if all_games else 0,
        "terminations": terminations,
    }

    # Save PGN
    with open(pgn_path, "w", encoding="utf-8") as f_pgn:
        for g in all_games:
            game = chess.pgn.Game()
            game.headers["Event"] = f"Project Janus v0.56 Match ({match_id})"
            game.headers["Site"] = "Antigravity Research Sandbox"
            game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
            game.headers["Round"] = str(g["round"])
            game.headers["White"] = g["white"]
            game.headers["Black"] = g["black"]
            game.headers["Result"] = g["result"]
            game.headers["Termination"] = g["termination"]
            game.headers["TimeControl"] = "3.0+0.1"
            game.headers["FEN"] = g["opening_fen"]

            curr_node = game
            for m_uci in g["moves"]:
                m = chess.Move.from_uci(m_uci)
                curr_node = curr_node.add_variation(m)

            f_pgn.write(str(game) + "\n\n")

    # Save Raw JSON
    raw_output = {
        "summary": summary,
        "pair_differences": pair_differences,
        "games": all_games,
    }
    with open(raw_path, "w", encoding="utf-8") as f_raw:
        json.dump(raw_output, f_raw, indent=2)

    print(f"\n=======================================================")
    print(f"MATCH FINISHED: {match_id}")
    print(f"Score:       {cand_total_points}/{total_games} ({cand_score_pct:.2f}%)  [+{cand_wins} ={cand_draws} -{cand_losses}]")
    print(f"Net Margin:  {cand_total_points - (total_games - cand_total_points):+.1f} points")
    print(f"Elo Diff:    {elo_diff:+.2f} Elo [95% CI: {elo_ci_lower:+.2f}, {elo_ci_upper:+.2f}]")
    print(f"Student-t:   t = {t_stat:.4f} (df={df}), p = {two_sided_p:.5f}")
    print(f"Terminations: {terminations}")
    print(f"Saved PGN to {pgn_path}")
    print(f"Saved Raw to {raw_path}")
    print(f"=======================================================")

    return summary


if __name__ == "__main__":
    run_match()
