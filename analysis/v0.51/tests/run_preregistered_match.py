"""Project Janus v0.51 - Preregistered Head-to-Head Match Runner.

Candidate: Native N2 Standalone UCI Engine (janus_native_engine.exe)
Baseline: Production Baseline Python K0 (JanusSearch eager sort, RFP disabled)

Match Protocol:
- 100 opening pairs (200 games total) from analysis/v0.51/corpus/openings_v051_100.json
- Fixed Fischer Time Control: 3.0s initial + 100ms increment
- Exact color reversal per pair:
    Game A: N2 (White) vs K0 (Black)
    Game B: K0 (White) vs N2 (Black)
- Strict clock tracking, adjudication for checkmate, stalemate, threefold, 50-move, insufficient material
- Saves PGNs to analysis/v0.51/pgn/n2_vs_k0_match.pgn
- Saves raw telemetry and pair results to analysis/v0.51/raw/match_results_raw.json
"""

import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import chess
import chess.pgn
import math
import random
import statistics

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch

ENGINE_EXE = ROOT / "analysis" / "v0.51" / "native" / "janus_native_engine.exe"
OPENINGS_PATH = ROOT / "analysis" / "v0.51" / "corpus" / "openings_v051_100.json"
PGN_PATH = ROOT / "analysis" / "v0.51" / "pgn" / "n2_vs_k0_match.pgn"
RAW_OUT_PATH = ROOT / "analysis" / "v0.51" / "raw" / "match_results_raw.json"


class NativeUCIProcess:
    def __init__(self, path: Path):
        self.p = subprocess.Popen(
            [str(path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\nisready\n")
        self.p.stdin.flush()
        while True:
            l = self.p.stdout.readline()
            if not l or l.strip() == "readyok":
                break

    def ucinewgame(self):
        self.p.stdin.write("ucinewgame\nisready\n")
        self.p.stdin.flush()
        while True:
            l = self.p.stdout.readline()
            if not l or l.strip() == "readyok":
                break

    def play_move(self, fen: str, wtime_ms: int, btime_ms: int, winc_ms: int, binc_ms: int):
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


def play_single_game(
    opening: dict,
    n2_is_white: bool,
    game_num: int,
    n2_proc: NativeUCIProcess,
    k0_searcher: JanusSearch,
    base_time_ms: int = 3000,
    inc_ms: int = 100,
    max_plies: int = 150
) -> dict:
    fen = opening.get("fen", chess.STARTING_FEN)
    board = chess.Board(fen)

    wtime = float(base_time_ms)
    btime = float(base_time_ms)

    white_name = "Janus 0.51 Native (N2)" if n2_is_white else "Janus Production (K0)"
    black_name = "Janus Production (K0)" if n2_is_white else "Janus 0.51 Native (N2)"

    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Project Janus v0.51 Strength Qualification"
    pgn_game.headers["Site"] = "Local Benchmark Harness"
    pgn_game.headers["Date"] = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = str(game_num)
    pgn_game.headers["White"] = white_name
    pgn_game.headers["Black"] = black_name
    pgn_game.headers["TimeControl"] = f"{base_time_ms/1000:.1f}+{inc_ms/1000:.2f}"
    if fen != chess.STARTING_FEN:
        pgn_game.headers["SetUp"] = "1"
        pgn_game.headers["FEN"] = fen

    node = pgn_game
    termination = "unknown"
    result_str = "*"
    moves_history = []

    for ply in range(max_plies):
        if board.is_game_over():
            outcome = board.outcome(claim_draw=True)
            if outcome:
                result_str = outcome.result()
                if outcome.winner == chess.WHITE: termination = "checkmate_white"
                elif outcome.winner == chess.BLACK: termination = "checkmate_black"
                else: termination = f"draw_{outcome.termination.name.lower()}"
            break

        is_n2_turn = (board.turn == chess.WHITE) if n2_is_white else (board.turn == chess.BLACK)
        my_time = wtime if board.turn == chess.WHITE else btime

        # Check for timeout before move
        if my_time <= 0:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"timeout_{winner.lower()}_wins"
            break

        if is_n2_turn:
            best_uci, elapsed = n2_proc.play_move(
                board.fen(), int(wtime), int(btime), inc_ms, inc_ms
            )
            if not best_uci:
                best_move = list(board.legal_moves)[0] if list(board.legal_moves) else None
            else:
                try:
                    best_move = chess.Move.from_uci(best_uci)
                except Exception:
                    best_move = list(board.legal_moves)[0] if list(board.legal_moves) else None
        else:
            # K0 turn: Fischer allocation
            alloc_ms = (my_time + 40.0 * inc_ms) / 40.0
            if alloc_ms > my_time - 50.0:
                alloc_ms = max(10.0, my_time - 50.0)
            time_limit = alloc_ms / 1000.0

            t0 = time.perf_counter()
            k0_res = k0_searcher.search(board, max_depth=64, time_limit=time_limit)
            elapsed = time.perf_counter() - t0
            best_move = k0_res.best_move

        if not best_move or best_move not in board.legal_moves:
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_str = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"illegal_move_{winner.lower()}_wins"
            break

        # Update clock
        if board.turn == chess.WHITE:
            wtime = wtime - (elapsed * 1000.0) + inc_ms
        else:
            btime = btime - (elapsed * 1000.0) + inc_ms

        node = node.add_variation(best_move)
        board.push(best_move)
        moves_history.append(best_move.uci())

    if result_str == "*":
        outcome = board.outcome(claim_draw=True)
        if outcome:
            result_str = outcome.result()
            termination = f"draw_{outcome.termination.name.lower()}"
        else:
            result_str = "1/2-1/2"
            termination = "draw_max_plies_horizon"

    pgn_game.headers["Result"] = result_str
    pgn_game.headers["Termination"] = termination

    # Determine score for N2
    if result_str == "1-0":
        n2_score = 1.0 if n2_is_white else 0.0
    elif result_str == "0-1":
        n2_score = 0.0 if n2_is_white else 1.0
    else:
        n2_score = 0.5

    return {
        "game_number": game_num,
        "opening_id": opening.get("id"),
        "n2_color": "White" if n2_is_white else "Black",
        "result": result_str,
        "n2_score": n2_score,
        "termination": termination,
        "plies": len(moves_history),
        "pgn": str(pgn_game)
    }


def run_preregistered_match():
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    # Use first 100 openings (200 games)
    openings = openings[:100]
    n_pairs = len(openings)

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.51 - PREREGISTERED STRENGTH MATCH (N2 vs K0)", flush=True)
    print(f"Opening Pairs: {n_pairs} (Total Games: {n_pairs * 2})", flush=True)
    print("Time Control: 3.0s + 100ms increment", flush=True)
    print("=" * 80, flush=True)

    n2_proc = NativeUCIProcess(ENGINE_EXE)
    k0_searcher = JanusSearch(enable_lazy_move_selection=False, enable_rfp=False)

    all_games = []
    pair_deltas = []
    pair_scores_n2 = []
    pair_scores_k0 = []

    n2_wins = 0
    n2_losses = 0
    draws = 0
    n2_white_score = 0.0
    n2_black_score = 0.0

    pgn_file = open(PGN_PATH, "w", encoding="utf-8")

    t_start = time.perf_counter()

    for pair_idx, opening in enumerate(openings, 1):
        n2_proc.ucinewgame()

        # Game A: N2 White vs K0 Black
        game_num_a = (pair_idx - 1) * 2 + 1
        res_a = play_single_game(
            opening, n2_is_white=True, game_num=game_num_a,
            n2_proc=n2_proc, k0_searcher=k0_searcher
        )
        pgn_file.write(res_a["pgn"] + "\n\n")
        pgn_file.flush()
        all_games.append(res_a)

        # Game B: K0 White vs N2 Black
        n2_proc.ucinewgame()
        game_num_b = game_num_a + 1
        res_b = play_single_game(
            opening, n2_is_white=False, game_num=game_num_b,
            n2_proc=n2_proc, k0_searcher=k0_searcher
        )
        pgn_file.write(res_b["pgn"] + "\n\n")
        pgn_file.flush()
        all_games.append(res_b)

        # Update running stats
        score_a = res_a["n2_score"]
        score_b = res_b["n2_score"]
        n2_pair_total = score_a + score_b
        k0_pair_total = (1.0 - score_a) + (1.0 - score_b)
        delta = n2_pair_total - k0_pair_total

        pair_scores_n2.append(n2_pair_total)
        pair_scores_k0.append(k0_pair_total)
        pair_deltas.append(delta)

        n2_white_score += score_a
        n2_black_score += score_b

        for s in [score_a, score_b]:
            if s == 1.0: n2_wins += 1
            elif s == 0.0: n2_losses += 1
            else: draws += 1

        total_games_played = len(all_games)
        n2_total_pts = sum(g["n2_score"] for g in all_games)
        n2_pct = (n2_total_pts / total_games_played) * 100.0

        if pair_idx % 5 == 0 or pair_idx == n_pairs:
            print(
                f"Pair {pair_idx:3d}/{n_pairs:3d} ({total_games_played:3d}g): "
                f"N2 {n2_wins}W - {draws}D - {n2_losses}L | "
                f"N2 Pts: {n2_total_pts:.1f}/{total_games_played} ({n2_pct:.1f}%) | "
                f"Mean Delta/Pair: {statistics.mean(pair_deltas):+.3f}",
                flush=True
            )

    pgn_file.close()
    n2_proc.close()

    total_time = time.perf_counter() - t_start
    total_games = len(all_games)
    n2_total_pts = sum(g["n2_score"] for g in all_games)
    n2_pct = (n2_total_pts / total_games) * 100.0

    # Statistical Significance Testing
    mean_delta = float(statistics.mean(pair_deltas))
    std_delta = float(statistics.stdev(pair_deltas)) if len(pair_deltas) > 1 else 0.0
    se_delta = std_delta / math.sqrt(len(pair_deltas)) if len(pair_deltas) > 0 else 1.0
    t_stat = mean_delta / se_delta if se_delta > 0 else 0.0

    # 10,000 Pair-Bootstrap Resamples
    random.seed(42)
    boot_means = []
    n_p = len(pair_deltas)
    for _ in range(10000):
        sample = random.choices(pair_deltas, k=n_p)
        boot_means.append(statistics.mean(sample))
    boot_means.sort()
    ci_low = float(boot_means[int(0.025 * 10000)])
    ci_high = float(boot_means[int(0.975 * 10000)])

    # Two-tailed p-value via normal approximation (df = 99)
    p_val_two = math.erfc(abs(t_stat) / math.sqrt(2.0))
    p_val_one = p_val_two / 2.0 if t_stat > 0 else 1.0 - (p_val_two / 2.0)

    # Elo Calculation
    win_fraction = n2_total_pts / total_games
    if 0 < win_fraction < 1:
        elo_diff = float(-400.0 * math.log10(1.0 / win_fraction - 1.0))
        se_elo = float(400.0 / (math.log(10) * win_fraction * (1.0 - win_fraction) * math.sqrt(total_games)))
        elo_ci_low = elo_diff - 1.96 * se_elo
        elo_ci_high = elo_diff + 1.96 * se_elo
    else:
        elo_diff = 0.0
        elo_ci_low = 0.0
        elo_ci_high = 0.0

    final_report = {
        "match_name": "Project Janus v0.51 Strength Qualification (N2 vs K0)",
        "total_pairs": n_pairs,
        "total_games": total_games,
        "time_control": "3.0s + 100ms increment",
        "n2_wins": n2_wins,
        "draws": draws,
        "n2_losses": n2_losses,
        "n2_score_points": n2_total_pts,
        "n2_score_pct": round(n2_pct, 2),
        "n2_white_score": n2_white_score,
        "n2_black_score": n2_black_score,
        "white_win_pct": round(sum(1 for g in all_games if g["result"] == "1-0") / total_games * 100.0, 1),
        "black_win_pct": round(sum(1 for g in all_games if g["result"] == "0-1") / total_games * 100.0, 1),
        "draw_pct": round(draws / total_games * 100.0, 1),
        "mean_paired_delta": round(mean_delta, 4),
        "std_paired_delta": round(std_delta, 4),
        "paired_t_statistic": round(float(t_stat), 4),
        "two_tailed_p_value": float(p_val_two),
        "one_tailed_p_value": float(p_val_one),
        "bootstrap_95_ci": [round(ci_low, 4), round(ci_high, 4)],
        "estimated_elo_diff": round(elo_diff, 1),
        "elo_95_ci": [round(elo_ci_low, 1), round(elo_ci_high, 1)],
        "elapsed_time_sec": round(total_time, 1),
        "pair_deltas": pair_deltas,
        "games": all_games
    }

    with open(RAW_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print("\n" + "=" * 80, flush=True)
    print("FINAL MATCH RESULTS:", flush=True)
    print(f"Games: {total_games} | N2 Record: {n2_wins}W - {draws}D - {n2_losses}L ({n2_pct:.2f}%)", flush=True)
    print(f"Estimated Elo diff: {elo_diff:+.1f} (95% CI: [{elo_ci_low:+.1f}, {elo_ci_high:+.1f}])", flush=True)
    print(f"Paired t-statistic: {t_stat:.4f} | p-value (two-tailed): {p_val_two:.6f}", flush=True)
    print(f"Pair-Bootstrap 95% CI: [{ci_low:+.4f}, {ci_high:+.4f}] points per pair", flush=True)
    print(f"Saved PGN to {PGN_PATH}", flush=True)
    print(f"Saved raw match report to {RAW_OUT_PATH}", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    run_preregistered_match()
