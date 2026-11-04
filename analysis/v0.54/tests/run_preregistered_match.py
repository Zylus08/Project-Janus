"""Project Janus v0.54 - Preregistered Strength Match Runner.

Controlled Strength Ablation:
- Primary Match: Candidate C3 (UseKiller=true, UseHistory=true) vs Control C0 (UseKiller=false, UseHistory=false)
- Secondary Matches (Exploratory):
  - C1 (Killer Only) vs C0
  - C2 (History Only) vs C0
- Corpus: 100 opening pairs (200 games) from openings_v052_100.json
- Time Control: 3.0s base + 100ms increment (Fischer 3+0.1)
- Adjudication: Sound FIDE adjudications + 300-ply non-FIDE safety horizon via tournament_controller.py
- Architecture: 8-Worker Parallel Process Pool (utilizing AMD64 16-core CPU)
- Statistics: Exact Student-t (df=99), 100,000 paired bootstrap resamples, empirical Elo confidence interval.
"""

import json
import time
import math
import random
import sys
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.54" / "tests"))

from tournament_controller import NativeUCIEngineProcess, adjudicate_board

CORPUS_PATH = ROOT / "analysis" / "v0.54" / "corpus" / "openings_v052_100.json"
PGN_DIR = ROOT / "analysis" / "v0.54" / "pgn"
RAW_DIR = ROOT / "analysis" / "v0.54" / "raw"
EXE_PATH = ROOT / "analysis" / "v0.54" / "native" / "janus_native_engine.exe"

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


def ibeta(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * betacf(a, b, x) / a
    else:
        return 1.0 - front * betacf(b, a, 1.0 - x) / b


def student_t_pvalue(t_val, df):
    if df <= 0: return 1.0
    x = df / (df + t_val * t_val)
    return ibeta(df / 2.0, 0.5, x)


def compute_elo_diff(score_frac):
    if score_frac <= 0.001: return -800.0
    if score_frac >= 0.999: return +800.0
    return -400.0 * math.log10(1.0 / score_frac - 1.0)


def play_single_game_worker(white_proc, black_proc, white_name, black_name, opening_fen, round_num):
    board = chess.Board(opening_fen)
    white_proc.ucinewgame()
    black_proc.ucinewgame()

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
                rate = completed_pairs / elapsed
                rem = (n_pairs - completed_pairs) / rate if rate > 0 else 0
                print(f"[{match_id}] Progress: {completed_pairs:3d}/{n_pairs} pairs ({completed_pairs*2:3d}/200 games) | Elapsed: {elapsed:.1f}s | Est. Remaining: {rem:.1f}s")

    total_match_sec = time.perf_counter() - t_start

    # Assemble ordered games and export PGN
    games_data = []
    pair_differences = []
    cand_wins = 0
    cand_draws = 0
    cand_losses = 0
    cand_white_score = 0.0
    cand_black_score = 0.0
    terminations_count = {}

    with open(pgn_path, "w", encoding="utf-8") as pgn_file:
        for pair_idx, (res_a, res_b) in enumerate(pair_results):
            for res, is_game_a in [(res_a, True), (res_b, False)]:
                game = chess.pgn.Game()
                game.headers["Event"] = f"Project Janus v0.54 {match_id}"
                game.headers["Site"] = "Localhost AMD64"
                game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
                game.headers["Round"] = str(res["round"])
                game.headers["White"] = res["white"]
                game.headers["Black"] = res["black"]
                game.headers["Result"] = res["result"]
                game.headers["Termination"] = res["termination"]
                if res["opening_fen"] != chess.STARTING_FEN:
                    game.headers["SetUp"] = "1"
                    game.headers["FEN"] = res["opening_fen"]

                b = chess.Board(res["opening_fen"])
                node = game
                for m_str in res["moves"]:
                    mv = chess.Move.from_uci(m_str)
                    node = node.add_variation(mv)
                    b.push(mv)

                exporter = chess.pgn.FileExporter(pgn_file)
                game.accept(exporter)

                terminations_count[res["termination"]] = terminations_count.get(res["termination"], 0) + 1
                games_data.append({
                    "round": res["round"],
                    "white": res["white"],
                    "black": res["black"],
                    "result": res["result"],
                    "termination": res["termination"],
                    "plies": res["plies"],
                    "full_moves": res["full_moves"],
                    "duration_sec": res["duration_sec"],
                    "opening_fen": res["opening_fen"],
                })

            # Calculate paired score for Candidate
            if res_a["result"] == "1-0":
                sc_a = 1.0
                cand_wins += 1
            elif res_a["result"] == "0-1":
                sc_a = 0.0
                cand_losses += 1
            else:
                sc_a = 0.5
                cand_draws += 1
            cand_white_score += sc_a

            if res_b["result"] == "0-1":
                sc_b = 1.0
                cand_wins += 1
            elif res_b["result"] == "1-0":
                sc_b = 0.0
                cand_losses += 1
            else:
                sc_b = 0.5
                cand_draws += 1
            cand_black_score += sc_b

            pair_net = (sc_a + sc_b) - 1.0
            pair_differences.append(pair_net)

    # Statistical Evaluation
    total_games = len(games_data)
    cand_total_pts = cand_wins + 0.5 * cand_draws
    score_frac = cand_total_pts / total_games
    score_pct = score_frac * 100.0

    mean_d = sum(pair_differences) / n_pairs
    variance_d = sum((d - mean_d) ** 2 for d in pair_differences) / (n_pairs - 1)
    std_d = math.sqrt(variance_d)
    se_d = std_d / math.sqrt(n_pairs)

    t_stat = (mean_d / se_d) if se_d > 0 else 0.0
    p_val = student_t_pvalue(t_stat, df=n_pairs - 1)

    random.seed(42)
    B = 100_000
    boot_means = []
    for _ in range(B):
        sample = [random.choice(pair_differences) for _ in range(n_pairs)]
        boot_means.append(sum(sample) / n_pairs)
    boot_means.sort()
    ci_lower_d = boot_means[int(0.025 * B)]
    ci_upper_d = boot_means[int(0.975 * B)]

    elo_diff = compute_elo_diff(score_frac)
    elo_samples = [compute_elo_diff((m + 1.0) / 2.0) for m in boot_means]
    elo_samples.sort()
    ci_lower_elo = elo_samples[int(0.025 * B)]
    ci_upper_elo = elo_samples[int(0.975 * B)]

    avg_plies = sum(g["plies"] for g in games_data) / total_games

    summary = {
        "match_id": match_id,
        "candidate": cand_name,
        "control": ctrl_name,
        "total_pairs": n_pairs,
        "total_games": total_games,
        "time_control": "3.0s + 100ms",
        "total_duration_sec": total_match_sec,
        "cand_wins": cand_wins,
        "cand_draws": cand_draws,
        "cand_losses": cand_losses,
        "cand_points": cand_total_pts,
        "cand_score_pct": score_pct,
        "cand_white_score": cand_white_score,
        "cand_black_score": cand_black_score,
        "paired_diff_mean": mean_d,
        "paired_diff_std": std_d,
        "paired_diff_se": se_d,
        "t_statistic": t_stat,
        "degrees_of_freedom": n_pairs - 1,
        "two_sided_p_value": p_val,
        "bootstrap_ci_95_diff": [ci_lower_d, ci_upper_d],
        "elo_difference": elo_diff,
        "bootstrap_ci_95_elo": [ci_lower_elo, ci_upper_elo],
        "average_game_plies": avg_plies,
        "terminations": terminations_count,
    }

    full_output = {
        "summary": summary,
        "pair_differences": pair_differences,
        "games": games_data,
    }

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print(f"\n[{match_id}] COMPLETED in {total_match_sec:.1f}s")
    print(f"Score: +{cand_wins} ={cand_draws} -{cand_losses} -> {cand_total_pts}/{total_games} ({score_pct:.2f}%)")
    print(f"Elo Advantage: {elo_diff:+.1f} [95% CI: {ci_lower_elo:+.1f}, {ci_upper_elo:+.1f}]")
    print(f"Paired Student-t: t = {t_stat:.4f}, df = {n_pairs - 1}, p = {p_val:.4e}")
    print(f"PGN written to: {pgn_path}")

    return summary


def main():
    # Primary Preregistered Match: C3 (Combined N5) vs C0 (Control N3)
    c0_opts = {"UseKillerOrdering": False, "UseHistoryOrdering": False, "UseLMR": True, "UsePVS": False}
    c3_opts = {"UseKillerOrdering": True, "UseHistoryOrdering": True, "UseLMR": True, "UsePVS": False}

    run_match(
        match_id="c3_vs_c0_primary",
        cand_name="Janus 0.54 N5 C3 (Killer+History)",
        ctrl_name="Janus 0.54 N3 C0 (Control)",
        cand_opts=c3_opts,
        ctrl_opts=c0_opts,
    )


if __name__ == "__main__":
    main()

