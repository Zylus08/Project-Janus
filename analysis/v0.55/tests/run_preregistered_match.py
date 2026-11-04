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


def play_single_game(
    game_id: int,
    pair_id: int,
    cand_is_white: bool,
    opening_fen: str,
    opening_name: str,
    cand_opts: dict,
    base_opts: dict,
    base_time_sec: float = 3.0,
    inc_sec: float = 0.1,
    max_plies: int = 300
) -> dict:
    """Plays a single game between Candidate and Baseline processes with unbuffered I/O."""
    p_cand = NativeUCIEngineProcess(EXE_PATH, options=cand_opts)
    p_base = NativeUCIEngineProcess(EXE_PATH, options=base_opts)

    cand_name = "Candidate"
    base_name = "Baseline"

    white_proc = p_cand if cand_is_white else p_base
    black_proc = p_base if cand_is_white else p_cand

    white_name = cand_name if cand_is_white else base_name
    black_name = base_name if cand_is_white else cand_name

    board = chess.Board(opening_fen)
    moves_played = []

    white_clock = base_time_sec
    black_clock = base_time_sec

    termination = ""
    result_str = "*"
    cand_points = 0.5

    t_start = time.perf_counter()

    try:
        while len(moves_played) < max_plies:
            active_proc = white_proc if board.turn == chess.WHITE else black_proc
            active_clock = white_clock if board.turn == chess.WHITE else black_clock

            wtime_ms = int(max(0.01, white_clock) * 1000)
            btime_ms = int(max(0.01, black_clock) * 1000)
            winc_ms = int(inc_sec * 1000)
            binc_ms = int(inc_sec * 1000)

            t0 = time.perf_counter()
            bestmove = active_proc.get_best_move(
                board.fen(),
                wtime=wtime_ms,
                btime=btime_ms,
                winc=winc_ms,
                binc=binc_ms,
                timeout=max(2.0, active_clock + 5.0)
            )
            elapsed = time.perf_counter() - t0

            if board.turn == chess.WHITE:
                white_clock = white_clock - elapsed + inc_sec
                if white_clock <= 0:
                    termination = "time_forfeit_white"
                    result_str = "0-1"
                    cand_points = 0.0 if cand_is_white else 1.0
                    break
            else:
                black_clock = black_clock - elapsed + inc_sec
                if black_clock <= 0:
                    termination = "time_forfeit_black"
                    result_str = "1-0"
                    cand_points = 1.0 if cand_is_white else 0.0
                    break

            if not bestmove:
                termination = "engine_crash_no_move"
                if board.turn == chess.WHITE:
                    result_str = "0-1"
                    cand_points = 0.0 if cand_is_white else 1.0
                else:
                    result_str = "1-0"
                    cand_points = 1.0 if cand_is_white else 0.0
                break

            try:
                move = chess.Move.from_uci(bestmove)
                if move not in board.legal_moves:
                    termination = "illegal_move"
                    if board.turn == chess.WHITE:
                        result_str = "0-1"
                        cand_points = 0.0 if cand_is_white else 1.0
                    else:
                        result_str = "1-0"
                        cand_points = 1.0 if cand_is_white else 0.0
                    break
            except Exception:
                termination = "parse_move_error"
                break

            board.push(move)
            moves_played.append(bestmove)

            # Adjudicate via strict FIDE rules
            is_term, term_code, term_res = adjudicate_board(board)
            if is_term:
                termination = term_code
                result_str = term_res
                if result_str == "1-0":
                    cand_points = 1.0 if cand_is_white else 0.0
                elif result_str == "0-1":
                    cand_points = 0.0 if cand_is_white else 1.0
                else:
                    cand_points = 0.5
                break

        if not termination and len(moves_played) >= max_plies:
            termination = "safety_limit_300_plies"
            result_str = "1/2-1/2"
            cand_points = 0.5

    finally:
        p_cand.close()
        p_base.close()

    duration = time.perf_counter() - t_start

    return {
        "game_id": game_id,
        "pair_id": pair_id,
        "cand_is_white": cand_is_white,
        "white_name": white_name,
        "black_name": black_name,
        "result_str": result_str,
        "cand_points": cand_points,
        "termination": termination,
        "plies": len(moves_played),
        "duration_sec": duration,
        "opening_name": opening_name,
        "opening_fen": opening_fen,
        "moves": moves_played,
    }


def run_match(match_id: str):
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    if match_id == "n6_vs_n5":
        cand_label = "Janus 0.55 N6 (Killer+History+PVS)"
        base_label = "Janus 0.55 N5 (Killer+History)"
        cand_opts = {"UseKillerOrdering": "true", "UseHistoryOrdering": "true", "UsePVS": "true", "UseLMR": "true"}
        base_opts = {"UseKillerOrdering": "true", "UseHistoryOrdering": "true", "UsePVS": "false", "UseLMR": "true"}
    elif match_id == "n5_vs_n3":
        cand_label = "Janus 0.55 N5 (Killer+History)"
        base_label = "Janus 0.55 N3 (Control)"
        cand_opts = {"UseKillerOrdering": "true", "UseHistoryOrdering": "true", "UsePVS": "false", "UseLMR": "true"}
        base_opts = {"UseKillerOrdering": "false", "UseHistoryOrdering": "false", "UsePVS": "false", "UseLMR": "true"}
    else:
        raise ValueError(f"Unknown match ID: {match_id}")

    print("=================================================================")
    print(f"Launching Preregistered Tournament: {match_id.upper()}")
    print(f"Candidate : {cand_label}")
    print(f"Baseline  : {base_label}")
    print(f"Corpus    : {len(openings)} Opening Pairs ({len(openings)*2} Games)")
    print(f"Control   : Fischer 3.0s + 100ms | 8 Parallel Workers")
    print(f"Binary    : {EXE_PATH}")
    print("=================================================================")

    # Schedule 200 games (100 pairs)
    tasks = []
    game_id = 1
    for pair_idx, op in enumerate(openings):
        pair_id = pair_idx + 1
        fen = op["fen"]
        name = op["name"]
        # Game 1: Cand is White
        tasks.append((game_id, pair_id, True, fen, name, cand_opts, base_opts))
        game_id += 1
        # Game 2: Cand is Black
        tasks.append((game_id, pair_id, False, fen, name, cand_opts, base_opts))
        game_id += 1

    t_tourn_start = time.perf_counter()
    completed_games = []

    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(play_single_game, *t): t for t in tasks}
        count = 0
        cand_score_acc = 0.0

        for fut in as_completed(futures):
            res = fut.result()
            completed_games.append(res)
            count += 1
            cand_score_acc += res["cand_points"]
            if count % 20 == 0 or count == len(tasks):
                pct = (cand_score_acc / count) * 100
                print(f"  Completed {count}/{len(tasks)} games | Candidate score: {cand_score_acc}/{count} ({pct:.2f}%)")

    tourn_duration = time.perf_counter() - t_tourn_start
    print(f"\nTournament completed in {tourn_duration:.2f} seconds ({tourn_duration/60:.2f} mins).")

    # Sort completed games by game_id
    completed_games.sort(key=lambda g: g["game_id"])

    # Aggregate by opening pair
    pairs = {}
    for g in completed_games:
        pid = g["pair_id"]
        if pid not in pairs:
            pairs[pid] = []
        pairs[pid].append(g)

    pair_diffs = []
    cand_white_score = 0.0
    cand_black_score = 0.0
    cand_w, cand_d, cand_l = 0, 0, 0
    terminations = {}

    for pid in sorted(pairs.keys()):
        pgames = pairs[pid]
        assert len(pgames) == 2, f"Pair {pid} does not have 2 games!"
        cand_pair_pts = 0.0
        for g in pgames:
            pts = g["cand_points"]
            cand_pair_pts += pts
            if g["cand_is_white"]:
                cand_white_score += pts
            else:
                cand_black_score += pts

            if pts == 1.0:
                cand_w += 1
            elif pts == 0.5:
                cand_d += 1
            else:
                cand_l += 1

            term = g["termination"]
            terminations[term] = terminations.get(term, 0) + 1

        base_pair_pts = 2.0 - cand_pair_pts
        pair_diff = (cand_pair_pts - base_pair_pts) / 2.0  # Delta score per game
        pair_diffs.append(pair_diff)

    N_pairs = len(pair_diffs)
    mean_diff = sum(pair_diffs) / N_pairs
    sq_errs = sum((d - mean_diff) ** 2 for d in pair_diffs)
    std_diff = math.sqrt(sq_errs / (N_pairs - 1)) if N_pairs > 1 else 0.0
    se_diff = std_diff / math.sqrt(N_pairs)
    t_stat = mean_diff / se_diff if se_diff > 0 else 0.0
    df = N_pairs - 1
    p_val = student_t_two_sided_p(abs(t_stat), df)

    # 10,000 paired bootstrap resamples
    random.seed(42)
    boot_diffs = []
    for _ in range(10000):
        sample = [random.choice(pair_diffs) for _ in range(N_pairs)]
        boot_diffs.append(sum(sample) / N_pairs)
    boot_diffs.sort()
    ci_diff_lower = boot_diffs[int(0.025 * 10000)]
    ci_diff_upper = boot_diffs[int(0.975 * 10000)]

    def diff_to_elo(d):
        s = (d + 1.0) / 2.0
        s = max(0.001, min(0.999, s))
        return -400.0 * math.log10((1.0 - s) / s)

    elo_diff = diff_to_elo(mean_diff)
    elo_ci_lower = diff_to_elo(ci_diff_lower)
    elo_ci_upper = diff_to_elo(ci_diff_upper)

    cand_pts = cand_w + 0.5 * cand_d
    cand_pct = (cand_pts / len(completed_games)) * 100

    print("\n=================================================================")
    print(f"FINAL TOURNAMENT RESULTS: {match_id.upper()}")
    print("=================================================================")
    print(f"Candidate : {cand_pts} / {len(completed_games)} ({cand_pct:.2f}%)  [+{cand_w} ={cand_d} -{cand_l}]")
    print(f"Baseline  : {len(completed_games) - cand_pts} / {len(completed_games)} ({100 - cand_pct:.2f}%)")
    print(f"Net Score : {cand_pts - (len(completed_games) - cand_pts):+.1f} points")
    print(f"Estimated Elo Advantage: {elo_diff:+.2f} Elo")
    print(f"Bootstrap 95% Elo CI   : [{elo_ci_lower:+.2f}, {elo_ci_upper:+.2f}] Elo")
    print(f"Paired Difference (d)  : {mean_diff:+.4f} +/- {std_diff:.4f} (SE={se_diff:.4f})")
    print(f"Student's t-statistic  : t = {t_stat:.4f} (df={df})")
    print(f"Two-Sided p-value      : p = {p_val:.5f}")
    print(f"White Score: {cand_white_score}/{N_pairs} ({cand_white_score/N_pairs*100:.1f}%) | Black Score: {cand_black_score}/{N_pairs} ({cand_black_score/N_pairs*100:.1f}%)")
    print(f"Terminations: {terminations}")
    print("=================================================================")

    # Write PGN file
    pgn_path = PGN_DIR / f"{match_id}.pgn"
    with open(pgn_path, "w", encoding="utf-8") as f_pgn:
        for g in completed_games:
            pgn_game = chess.pgn.Game()
            pgn_game.headers["Event"] = f"Project Janus v0.55 Match - {match_id}"
            pgn_game.headers["Site"] = "Antigravity Research Sandbox"
            pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
            pgn_game.headers["Round"] = str(g["game_id"])
            pgn_game.headers["White"] = g["white_name"]
            pgn_game.headers["Black"] = g["black_name"]
            pgn_game.headers["Result"] = g["result_str"]
            pgn_game.headers["Termination"] = g["termination"]
            pgn_game.headers["TimeControl"] = "3.0+0.1"
            pgn_game.headers["FEN"] = g["opening_fen"]
            pgn_game.headers["Opening"] = g["opening_name"]

            b = chess.Board(g["opening_fen"])
            node = pgn_game
            for m_str in g["moves"]:
                m = chess.Move.from_uci(m_str)
                node = node.add_variation(m)

            f_pgn.write(str(pgn_game) + "\n\n")

    print(f"Saved complete PGN to {pgn_path}")

    # Write Raw JSON
    raw_path = RAW_DIR / f"{match_id}_raw.json"
    summary_data = {
        "match_id": match_id,
        "candidate": cand_label,
        "control": base_label,
        "total_pairs": N_pairs,
        "total_games": len(completed_games),
        "time_control": "3.0s + 100ms",
        "total_duration_sec": tourn_duration,
        "cand_wins": cand_w,
        "cand_draws": cand_d,
        "cand_losses": cand_l,
        "cand_points": cand_pts,
        "cand_score_pct": cand_pct,
        "cand_white_score": cand_white_score,
        "cand_black_score": cand_black_score,
        "paired_diff_mean": mean_diff,
        "paired_diff_std": std_diff,
        "paired_diff_se": se_diff,
        "t_statistic": t_stat,
        "degrees_of_freedom": df,
        "two_sided_p_value": p_val,
        "bootstrap_ci_95_diff": [ci_diff_lower, ci_diff_upper],
        "elo_difference": elo_diff,
        "bootstrap_ci_95_elo": [elo_ci_lower, elo_ci_upper],
        "average_game_plies": sum(g["plies"] for g in completed_games) / len(completed_games),
        "terminations": terminations,
    }

    full_output = {
        "summary": summary_data,
        "pair_differences": pair_diffs,
        "games": completed_games
    }

    with open(raw_path, "w", encoding="utf-8") as f_json:
        json.dump(full_output, f_json, indent=2)

    print(f"Saved complete raw JSON data to {raw_path}")
    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", choices=["n6_vs_n5", "n5_vs_n3"], required=True)
    args = parser.parse_args()
    run_match(args.match)

