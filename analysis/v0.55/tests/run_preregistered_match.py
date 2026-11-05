"""Project Janus v0.55 - Preregistered Strength Match Runner.

Matches Supported:
1. Experiment A: n6_vs_n5 (Candidate N6 vs Production N5)
2. Experiment B: n5_vs_n3 (Candidate N5 vs Control N3 Replication)

Design:
- 100 opening pairs (200 games) from independent_openings_v055.json
- Time Control: 3.0s base + 100ms increment (Fischer 3+0.1)
- Concurrency: 8-Worker Parallel Process Pool
- Adjudication: Sound FIDE rules + 300-ply safety horizon via tournament_controller.py
- Statistics: Paired Student-t (df=99), 10,000 paired bootstrap resamples, empirical Elo confidence interval.
"""

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
sys.path.insert(0, str(ROOT / "analysis" / "v0.55" / "tests"))

from tournament_controller import NativeUCIEngineProcess, adjudicate_board

CORPUS_PATH = ROOT / "analysis" / "v0.55" / "corpus" / "independent_openings_v055.json"
PGN_DIR = ROOT / "analysis" / "v0.55" / "pgn"
RAW_DIR = ROOT / "analysis" / "v0.55" / "raw"
EXE_PATH = ROOT / "analysis" / "v0.55" / "native" / "janus_native_engine.exe"

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
        is_over, result_str, term_reason = adjudicate_board(board, ply_count, max_plies=300)
        if is_over:
            break

        current_turn = board.turn
        current_proc = white_proc if current_turn == chess.WHITE else black_proc

        cur_fen = board.fen()
        bestmove_uci, elapsed_sec = current_proc.play_move(
            cur_fen,
            wtime_ms=wtime_ms,
            btime_ms=btime_ms,
            winc_ms=inc_ms,
            binc_ms=inc_ms
        )

        elapsed_ms = int(elapsed_sec * 1000)

        if current_turn == chess.WHITE:
            wtime_ms = max(10, wtime_ms - elapsed_ms + inc_ms)
        else:
            btime_ms = max(10, btime_ms - elapsed_ms + inc_ms)

        if not bestmove_uci:
            loser = "white" if current_turn == chess.WHITE else "black"
            winner = "black" if current_turn == chess.WHITE else "white"
            result_str = "0-1" if winner == "black" else "1-0"
            term_reason = f"crash_forfeit_{loser}"
            break

        try:
            move = chess.Move.from_uci(bestmove_uci)
            if move not in board.legal_moves:
                loser = "white" if current_turn == chess.WHITE else "black"
                winner = "black" if current_turn == chess.WHITE else "white"
                result_str = "0-1" if winner == "black" else "1-0"
                term_reason = f"illegal_move_{loser}"
                break
        except Exception:
            loser = "white" if current_turn == chess.WHITE else "black"
            winner = "black" if current_turn == chess.WHITE else "white"
            result_str = "0-1" if winner == "black" else "1-0"
            term_reason = f"illegal_uci_string_{loser}"
            break

        board.push(move)
        moves_played.append(bestmove_uci)
        ply_count += 1

    total_game_time = time.perf_counter() - t_start

    return {
        "round": round_num,
        "white": white_name,
        "black": black_name,
        "result": result_str,
        "termination": term_reason,
        "plies": ply_count,
        "full_moves": len(moves_played) // 2,
        "duration_sec": total_game_time,
        "opening_fen": opening_fen,
        "moves": moves_played,
    }


def worker_play_pair(pair_args):
    pair_idx, op_fen, op_name, exe_path_str, cand_opts, ctrl_opts, cand_name, ctrl_name = pair_args
    pair_num = pair_idx + 1
    exe_p = Path(exe_path_str)

    cand_proc = NativeUCIEngineProcess(exe_p, options=cand_opts)
    ctrl_proc = NativeUCIEngineProcess(exe_p, options=ctrl_opts)

    try:
        # Game A: Candidate (White) vs Control (Black)
        round_a = pair_num * 2 - 1
        res_a = play_single_game_worker(
            white_proc=cand_proc,
            black_proc=ctrl_proc,
            white_name=cand_name,
            black_name=ctrl_name,
            opening_fen=op_fen,
            round_num=round_a,
        )

        # Game B: Control (White) vs Candidate (Black)
        round_b = pair_num * 2
        res_b = play_single_game_worker(
            white_proc=ctrl_proc,
            black_proc=cand_proc,
            white_name=ctrl_name,
            black_name=cand_name,
            opening_fen=op_fen,
            round_num=round_b,
        )
    finally:
        cand_proc.close()
        ctrl_proc.close()

    return pair_idx, res_a, res_b


def run_match(match_id: str, cand_name: str, ctrl_name: str, cand_opts: dict, ctrl_opts: dict):
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    n_pairs = len(openings)
    pgn_path = PGN_DIR / f"{match_id}.pgn"
    raw_path = RAW_DIR / f"{match_id}_raw.json"

    print(f"\n=======================================================")
    print(f"LAUNCHING MATCH: {match_id}")
    print(f"Candidate: {cand_name} (Opts: {cand_opts})")
    print(f"Control:   {ctrl_name} (Opts: {ctrl_opts})")
    print(f"Openings:  {n_pairs} pairs (200 games)")
    print(f"=======================================================")

    tasks = [
        (i, openings[i]["fen"], openings[i].get("name", f"Opening {i+1}"), str(EXE_PATH),
         cand_opts, ctrl_opts, cand_name, ctrl_name)
        for i in range(n_pairs)
    ]

    pair_results = [None] * n_pairs
    completed_pairs = 0
    t_start = time.perf_counter()

    with ProcessPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(worker_play_pair, task): task[0] for task in tasks}
        for future in as_completed(future_map):
            pair_idx, res_a, res_b = future.result()
            pair_results[pair_idx] = (res_a, res_b)
            completed_pairs += 1

            if completed_pairs % 10 == 0 or completed_pairs == n_pairs:
                elapsed = time.perf_counter() - t_start
                rate = completed_pairs / elapsed if elapsed > 0 else 0
                rem_sec = (n_pairs - completed_pairs) / rate if rate > 0 else 0
                print(f"  [Progress] {completed_pairs}/{n_pairs} pairs ({completed_pairs*2}/200 games) | Elapsed: {elapsed:.1f}s | Rem: {rem_sec:.1f}s")

    t_end = time.perf_counter()
    total_duration = t_end - t_start

    # Process all games
    all_games = []
    pair_differences = []

    cand_wins = 0
    cand_draws = 0
    cand_losses = 0
    cand_white_score = 0.0
    cand_black_score = 0.0

    terminations = {}

    for pair_idx in range(n_pairs):
        res_a, res_b = pair_results[pair_idx]
        all_games.append(res_a)
        all_games.append(res_b)

        # Game A: Candidate is White
        score_cand_a = 1.0 if res_a["result"] == "1-0" else (0.5 if res_a["result"] == "1/2-1/2" else 0.0)
        cand_white_score += score_cand_a
        if score_cand_a == 1.0: cand_wins += 1
        elif score_cand_a == 0.5: cand_draws += 1
        else: cand_losses += 1

        term_a = res_a["termination"]
        terminations[term_a] = terminations.get(term_a, 0) + 1

        # Game B: Candidate is Black
        score_cand_b = 1.0 if res_b["result"] == "0-1" else (0.5 if res_b["result"] == "1/2-1/2" else 0.0)
        cand_black_score += score_cand_b
        if score_cand_b == 1.0: cand_wins += 1
        elif score_cand_b == 0.5: cand_draws += 1
        else: cand_losses += 1

        term_b = res_b["termination"]
        terminations[term_b] = terminations.get(term_b, 0) + 1

        # Pair delta (cand_score - ctrl_score) / 2
        cand_pair_total = score_cand_a + score_cand_b
        ctrl_pair_total = (1.0 - score_cand_a) + (1.0 - score_cand_b)
        delta = (cand_pair_total - ctrl_pair_total) / 2.0
        pair_differences.append(delta)

    cand_total_points = cand_wins * 1.0 + cand_draws * 0.5
    total_games = n_pairs * 2
    cand_score_pct = (cand_total_points / total_games) * 100.0

    # Statistics
    mean_d = sum(pair_differences) / n_pairs
    sq_err = sum((d - mean_d) ** 2 for d in pair_differences)
    std_d = math.sqrt(sq_err / (n_pairs - 1)) if n_pairs > 1 else 0.0
    se_d = std_d / math.sqrt(n_pairs) if n_pairs > 0 else 0.0
    t_stat = mean_d / se_d if se_d > 0 else 0.0
    df = n_pairs - 1
    two_sided_p = student_t_two_sided_p(abs(t_stat), df)

    # 10,000 paired bootstrap resamples
    random.seed(42)
    boot_means = []
    for _ in range(10000):
        sample = [random.choice(pair_differences) for _ in range(n_pairs)]
        boot_means.append(sum(sample) / n_pairs)

    boot_means.sort()
    ci_lower_diff = boot_means[int(0.025 * 10000)]
    ci_upper_diff = boot_means[int(0.975 * 10000)]

    def diff_to_elo(d):
        p = (d + 1.0) / 2.0
        p = max(0.001, min(0.999, p))
        return -400.0 * math.log10((1.0 - p) / p)

    elo_diff = diff_to_elo(mean_d)
    elo_ci_lower = diff_to_elo(ci_lower_diff)
    elo_ci_upper = diff_to_elo(ci_upper_diff)

    summary = {
        "match_id": match_id,
        "candidate": cand_name,
        "control": ctrl_name,
        "total_pairs": n_pairs,
        "total_games": total_games,
        "time_control": "3.0s + 100ms",
        "total_duration_sec": total_duration,
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
            game.headers["Event"] = f"Project Janus v0.55 Match ({match_id})"
            game.headers["Site"] = "Antigravity Research Sandbox"
            game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
            game.headers["Round"] = str(g["round"])
            game.headers["White"] = g["white"]
            game.headers["Black"] = g["black"]
            game.headers["Result"] = g["result"]
            game.headers["Termination"] = g["termination"]
            game.headers["TimeControl"] = "3.0+0.1"
            game.headers["FEN"] = g["opening_fen"]

            b = chess.Board(g["opening_fen"])
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


def main():
    parser = argparse.ArgumentParser(description="Run Janus v0.55 Preregistered Matches")
    parser.add_argument("--match", choices=["n6_vs_n5", "n5_vs_n3"], required=True,
                        help="Match to run: 'n6_vs_n5' (Experiment A) or 'n5_vs_n3' (Experiment B)")
    args = parser.parse_args()

    if args.match == "n6_vs_n5":
        run_match(
            match_id="n6_vs_n5",
            cand_name="Janus 0.55 N6 (Killer+History+PVS)",
            ctrl_name="Janus 0.55 N5 (Killer+History)",
            cand_opts={"UseKillerOrdering": "true", "UseHistoryOrdering": "true", "UsePVS": "true", "UseLMR": "true"},
            ctrl_opts={"UseKillerOrdering": "true", "UseHistoryOrdering": "true", "UsePVS": "false", "UseLMR": "true"},
        )
    elif args.match == "n5_vs_n3":
        run_match(
            match_id="n5_vs_n3",
            cand_name="Janus 0.55 N5 (Killer+History)",
            ctrl_name="Janus 0.55 N3 (Control)",
            cand_opts={"UseKillerOrdering": "true", "UseHistoryOrdering": "true", "UsePVS": "false", "UseLMR": "true"},
            ctrl_opts={"UseKillerOrdering": "false", "UseHistoryOrdering": "false", "UsePVS": "false", "UseLMR": "true"},
        )


if __name__ == "__main__":
    main()
