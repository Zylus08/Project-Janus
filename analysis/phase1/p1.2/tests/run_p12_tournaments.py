#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.2
Phase 7 & Phase 8 Tournament Suite:
1. Janus Classical X7 (Candidate) vs Janus Classical X6 (Frozen Control)
   - 100 Games (50 Balanced Opening Pairs) at 1.0s + 50ms Fischer increment
2. Janus Classical X7 vs Unrestricted Stockfish 19 (Reference Engine)
   - 20 Games (10 Balanced Opening Pairs) at 2.0s + 50ms Fischer increment
"""

import os
import sys
import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import chess
import chess.pgn

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
X7_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
X6_EXE = ROOT / "analysis" / "phase1" / "p1.2" / "control" / "janus_classical_x6.exe"
C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
SF_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.2" / "raw"
PGN_DIR = ROOT / "analysis" / "phase1" / "p1.2" / "pgn"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PGN_DIR.mkdir(parents=True, exist_ok=True)


def calc_confidence_interval(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    """Exact Wilson score confidence interval."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    lower = max(0.0, centre - half)
    upper = min(1.0, centre + half)
    return float(lower), float(upper)


def calc_elo(p: float) -> float:
    if p <= 0.001:
        return -800.0
    if p >= 0.999:
        return 800.0
    return -400.0 * math.log10(1.0 / p - 1.0)


class UciEngineProcess:
    def __init__(self, name: str, exe_path: Path, options: Dict[str, Any] = None):
        self.name = name
        self.exe_path = str(exe_path.resolve())
        self.options = options or {}
        self.proc: Optional[subprocess.Popen] = None

    def start(self):
        self.proc = subprocess.Popen(
            [self.exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send_command("uci")
        self.wait_for("uciok")
        for k, v in self.options.items():
            self.send_command(f"setoption name {k} value {v}")
        self.send_command("isready")
        self.wait_for("readyok")

    def send_command(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError(f"Engine {self.name} is not running.")
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def wait_for(self, target: str, timeout: float = 10.0) -> List[str]:
        lines = []
        t0 = time.time()
        while time.time() - t0 < timeout:
            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Engine {self.name} terminated unexpectedly with code {self.proc.returncode}")
                time.sleep(0.005)
                continue
            line = line.strip()
            lines.append(line)
            if line == target or line.startswith(target):
                return lines
        raise TimeoutError(f"Engine {self.name} timed out waiting for '{target}'")

    def new_game(self):
        self.send_command("ucinewgame")
        self.send_command("isready")
        self.wait_for("readyok")

    def play_move(
        self,
        board: chess.Board,
        wtime_ms: int,
        btime_ms: int,
        winc_ms: int,
        binc_ms: int
    ) -> Tuple[str, Dict[str, Any]]:
        moves_str = " ".join([m.uci() for m in board.move_stack])
        if moves_str:
            self.send_command(f"position startpos moves {moves_str}")
        else:
            self.send_command("position startpos")

        go_cmd = f"go wtime {wtime_ms} btime {btime_ms} winc {winc_ms} binc {binc_ms}"
        self.send_command(go_cmd)

        lines = []
        bestmove = None
        info_dict = {}

        t_start = time.perf_counter()
        my_time = wtime_ms if board.turn == chess.WHITE else btime_ms
        my_inc = winc_ms if board.turn == chess.WHITE else binc_ms
        safety_timeout = (my_time / 1000.0) + (my_inc / 1000.0) * 2.0 + 5.0

        while True:
            elapsed = time.perf_counter() - t_start
            if elapsed > safety_timeout:
                self.terminate()
                raise TimeoutError(f"Engine {self.name} exceeded safety time limit ({elapsed:.2f}s > {safety_timeout:.2f}s)")

            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Engine {self.name} crashed during search with code {self.proc.returncode}")
                time.sleep(0.002)
                continue

            line = line.strip()
            if line.startswith("info"):
                lines.append(line)
                parts = line.split()
                for idx, tok in enumerate(parts):
                    if tok == "depth" and idx + 1 < len(parts):
                        info_dict["depth"] = int(parts[idx+1])
                    elif tok == "nodes" and idx + 1 < len(parts):
                        info_dict["nodes"] = int(parts[idx+1])
                    elif tok == "nps" and idx + 1 < len(parts):
                        info_dict["nps"] = int(parts[idx+1])
                    elif tok == "cp" and idx + 1 < len(parts):
                        info_dict["score_cp"] = int(parts[idx+1])
            elif line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) > 1:
                    bestmove = tokens[1]
                break

        elapsed_sec = time.perf_counter() - t_start
        info_dict["elapsed_sec"] = elapsed_sec
        return bestmove, info_dict

    def terminate(self):
        if self.proc:
            try:
                self.send_command("quit")
                self.proc.wait(timeout=2.0)
            except Exception:
                self.proc.kill()
            self.proc = None


def play_single_game(
    white_engine: UciEngineProcess,
    black_engine: UciEngineProcess,
    opening: Dict[str, Any],
    time_base_ms: int = 1000,
    time_inc_ms: int = 50,
    max_plies: int = 200
) -> Dict[str, Any]:
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Janus P1.2 Strength Validation"
    game.headers["White"] = white_engine.name
    game.headers["Black"] = black_engine.name
    game.headers["TimeControl"] = f"{time_base_ms/1000.0:.1f}+{time_inc_ms/1000.0:.2f}"
    game.headers["Opening"] = opening.get("name", "Unknown Opening")

    node = game
    for uci_m in opening.get("uci_sequence", []):
        m = chess.Move.from_uci(uci_m)
        board.push(m)
        node = node.add_variation(m)

    wtime = time_base_ms
    btime = time_base_ms
    winc = time_inc_ms
    binc = time_inc_ms

    white_engine.new_game()
    black_engine.new_game()

    moves_history = []
    t_start = time.time()
    termination = "normal"
    result = "*"

    for ply in range(max_plies):
        if board.is_checkmate():
            result = "1-0" if board.turn == chess.BLACK else "0-1"
            termination = "checkmate"
            break
        if board.is_stalemate():
            result = "1/2-1/2"
            termination = "stalemate"
            break
        if board.is_insufficient_material():
            result = "1/2-1/2"
            termination = "insufficient_material"
            break
        if board.can_claim_threefold_repetition():
            result = "1/2-1/2"
            termination = "threefold_repetition"
            break
        if board.can_claim_fifty_moves():
            result = "1/2-1/2"
            termination = "fifty_moves"
            break

        curr_engine = white_engine if board.turn == chess.WHITE else black_engine
        t_move_start = time.perf_counter()

        try:
            bm, info = curr_engine.play_move(board, wtime, btime, winc, binc)
        except Exception as e:
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"crash/timeout: {e}"
            break

        move_dur = time.perf_counter() - t_move_start
        move_dur_ms = int(move_dur * 1000.0)

        if board.turn == chess.WHITE:
            wtime = max(10, wtime - move_dur_ms + winc)
        else:
            btime = max(10, btime - move_dur_ms + binc)

        if not bm or bm == "0000":
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "no_move"
            break

        try:
            move_obj = chess.Move.from_uci(bm)
            if move_obj not in board.legal_moves:
                result = "0-1" if board.turn == chess.WHITE else "1-0"
                termination = f"illegal_move_{bm}"
                break
        except Exception:
            result = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = f"invalid_uci_{bm}"
            break

        board.push(move_obj)
        node = node.add_variation(move_obj)
        if "score_cp" in info:
            node.comment = f"eval={info['score_cp']/100.0:+.2f} d={info.get('depth',0)} n={info.get('nodes',0)}"

        moves_history.append({
            "ply": ply + 1,
            "turn": "W" if board.turn == chess.BLACK else "B",
            "move": bm,
            "duration_sec": move_dur,
            "info": info
        })

    if result == "*":
        result = "1/2-1/2"
        termination = "max_plies_adjudication"

    game.headers["Result"] = result
    game.headers["Termination"] = termination

    return {
        "white": white_engine.name,
        "black": black_engine.name,
        "result": result,
        "termination": termination,
        "plies": len(moves_history),
        "duration_sec": time.time() - t_start,
        "moves": moves_history,
        "pgn": str(game)
    }


def run_tournament(
    engine_a: UciEngineProcess,
    engine_b: UciEngineProcess,
    openings: List[Dict[str, Any]],
    num_pairs: int,
    time_base_ms: int,
    time_inc_ms: int,
    pgn_path: Path
) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f"Starting Match: {engine_a.name} vs {engine_b.name}")
    print(f"Pairs: {num_pairs} ({num_pairs * 2} games), Time Control: {time_base_ms/1000.0}s+{time_inc_ms/1000.0}s")
    print(f"=======================================================")

    engine_a.start()
    engine_b.start()

    games = []
    pair_results = []
    a_wins = 0
    b_wins = 0
    draws = 0

    pgn_file = open(pgn_path, "w", encoding="utf-8")

    t_tourn_start = time.time()

    try:
        for pair_idx in range(num_pairs):
            opening = openings[pair_idx % len(openings)]
            op_name = opening.get("name", f"Opening {pair_idx+1}")

            # Game 1: A as White, B as Black
            g1 = play_single_game(engine_a, engine_b, opening, time_base_ms, time_inc_ms)
            pgn_file.write(g1["pgn"] + "\n\n")
            pgn_file.flush()

            r1 = g1["result"]
            if r1 == "1-0":
                a_wins += 1
                s1_a = 1.0
            elif r1 == "0-1":
                b_wins += 1
                s1_a = 0.0
            else:
                draws += 1
                s1_a = 0.5

            # Game 2: B as White, A as Black
            g2 = play_single_game(engine_b, engine_a, opening, time_base_ms, time_inc_ms)
            pgn_file.write(g2["pgn"] + "\n\n")
            pgn_file.flush()

            r2 = g2["result"]
            if r2 == "1-0":
                b_wins += 1
                s2_a = 0.0
            elif r2 == "0-1":
                a_wins += 1
                s2_a = 1.0
            else:
                draws += 1
                s2_a = 0.5

            pair_score_a = s1_a + s2_a
            pair_results.append({
                "pair_idx": pair_idx + 1,
                "opening": op_name,
                "g1_result": r1,
                "g2_result": r2,
                "a_score": pair_score_a
            })
            games.extend([g1, g2])

            curr_n = len(games)
            curr_pts = a_wins + 0.5 * draws
            curr_pct = (curr_pts / curr_n) * 100.0
            print(f"Pair {pair_idx+1:2d}/{num_pairs:2d} | {op_name[:28]:28s} | G1:{r1:7s} G2:{r2:7s} | Pair:{pair_score_a:.1f}-{(2.0-pair_score_a):.1f} | Tot: +{a_wins}={draws}-{b_wins} ({curr_pct:.1f}%)")

    finally:
        engine_a.terminate()
        engine_b.terminate()
        pgn_file.close()

    total_games = len(games)
    a_points = a_wins + 0.5 * draws
    score_pct = a_points / total_games if total_games > 0 else 0.0
    ci_low, ci_high = calc_confidence_interval(a_points, total_games)
    elo = calc_elo(score_pct)
    elo_low = calc_elo(ci_low)
    elo_high = calc_elo(ci_high)

    # Clustered opening pair statistics
    pair_scores = [pr["a_score"] for pr in pair_results]
    n_pairs = len(pair_scores)
    mean_pair = sum(pair_scores) / n_pairs if n_pairs > 0 else 0.0
    var_pair = sum((x - mean_pair)**2 for x in pair_scores) / (n_pairs - 1) if n_pairs > 1 else 0.0
    se_pair = math.sqrt(var_pair / n_pairs) if n_pairs > 0 else 0.0
    # Clustered score proportion = mean_pair / 2.0
    cluster_score_pct = mean_pair / 2.0
    cluster_ci_low = max(0.0, (mean_pair - 1.96 * se_pair) / 2.0)
    cluster_ci_high = min(1.0, (mean_pair + 1.96 * se_pair) / 2.0)
    cluster_elo = calc_elo(cluster_score_pct)
    cluster_elo_low = calc_elo(cluster_ci_low)
    cluster_elo_high = calc_elo(cluster_ci_high)

    duration = time.time() - t_tourn_start

    print(f"\n--- Match Summary: {engine_a.name} vs {engine_b.name} ---")
    print(f"Total Games: {total_games} ({n_pairs} opening pairs)")
    print(f"Score: +{a_wins} ={draws} -{b_wins} -> {a_points:.1f}/{total_games} ({score_pct*100.0:.2f}%)")
    print(f"Binomial 95% CI: [{ci_low*100.0:.2f}%, {ci_high*100.0:.2f}%] -> Elo: {elo:+.1f} [{elo_low:+.1f}, {elo_high:+.1f}]")
    print(f"Clustered 95% CI: [{cluster_ci_low*100.0:.2f}%, {cluster_ci_high*100.0:.2f}%] -> Elo: {cluster_elo:+.1f} [{cluster_elo_low:+.1f}, {cluster_elo_high:+.1f}]")
    print(f"Duration: {duration:.1f}s\n")

    return {
        "engine_a": engine_a.name,
        "engine_b": engine_b.name,
        "total_games": total_games,
        "pairs_count": n_pairs,
        "a_wins": a_wins,
        "draws": draws,
        "b_wins": b_wins,
        "a_points": a_points,
        "score_pct": score_pct,
        "ci_95": [ci_low, ci_high],
        "elo": elo,
        "elo_95": [elo_low, elo_high],
        "clustered_score_pct": cluster_score_pct,
        "clustered_ci_95": [cluster_ci_low, cluster_ci_high],
        "clustered_elo": cluster_elo,
        "clustered_elo_95": [cluster_elo_low, cluster_elo_high],
        "duration_sec": duration,
        "pair_results": pair_results,
        "pgn_path": str(pgn_path)
    }


def main():
    print(f"=== Project Janus P1.2 — Phase 7 & 8 Tournament Execution ===")
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings_data = json.load(f)
    openings = openings_data if isinstance(openings_data, list) else openings_data.get("openings", [])
    print(f"Loaded {len(openings)} openings from {OPENINGS_PATH}")

    # =========================================================================
    # TOURNAMENT 1: Janus Classical X7 vs Janus Classical X6
    # 100 Games (50 Pairs) at 1.0s + 50ms Fischer increment
    # =========================================================================
    eng_x7 = UciEngineProcess(
        name="Janus_Classical_X7",
        exe_path=X7_EXE,
        options={
            "UCI_Variant": "X7",
            "UCI_ContinuationHistory": "H3",
            "UCI_DynamicLMR": "L3",
            "UCI_ClassicalEval": "E5"
        }
    )
    eng_x6 = UciEngineProcess(
        name="Janus_Classical_X6",
        exe_path=X6_EXE,
        options={
            "UCI_Variant": "X6"
        }
    )

    t1_res = run_tournament(
        engine_a=eng_x7,
        engine_b=eng_x6,
        openings=openings,
        num_pairs=50,
        time_base_ms=1000,
        time_inc_ms=50,
        pgn_path=PGN_DIR / "x7_vs_x6.pgn"
    )

    with open(RAW_DIR / "x7_vs_x6_tournament_raw.json", "w", encoding="utf-8") as f:
        json.dump(t1_res, f, indent=2)
    print(f"Saved Tournament 1 raw data to {RAW_DIR / 'x7_vs_x6_tournament_raw.json'}")

    # =========================================================================
    # TOURNAMENT 2: Janus Classical X7 vs Unrestricted Stockfish 19
    # 20 Games (10 Pairs) at 2.0s + 50ms Fischer increment
    # =========================================================================
    eng_x7_sf = UciEngineProcess(
        name="Janus_Classical_X7",
        exe_path=X7_EXE,
        options={
            "UCI_Variant": "X7",
            "UCI_ContinuationHistory": "H3",
            "UCI_DynamicLMR": "L3",
            "UCI_ClassicalEval": "E5"
        }
    )
    eng_sf19 = UciEngineProcess(
        name="Stockfish_19",
        exe_path=SF_EXE,
        options={
            "Threads": 1,
            "Hash": 16
        }
    )

    t2_res = run_tournament(
        engine_a=eng_x7_sf,
        engine_b=eng_sf19,
        openings=openings,
        num_pairs=10,
        time_base_ms=2000,
        time_inc_ms=50,
        pgn_path=PGN_DIR / "matched_sf19_progress.pgn"
    )

    with open(RAW_DIR / "matched_sf19_progress_raw.json", "w", encoding="utf-8") as f:
        json.dump(t2_res, f, indent=2)
    print(f"Saved Tournament 2 raw data to {RAW_DIR / 'matched_sf19_progress_raw.json'}")

if __name__ == "__main__":
    main()

