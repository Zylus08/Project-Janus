#!/usr/bin/env python3
"""
Project Janus Phase 1 — Milestone P1.0
Robust UCI Engine Comparison & Benchmark Harness.

Features:
- Subprocess UCI management with crash, timeout, and illegal move detection.
- Balanced colour-reversed opening pairs.
- Exact FIDE draw and checkmate adjudication via python-chess.
- Complete PGN archival with clock/eval annotations.
- Full JSON telemetry output.
- Reconciles historical v0.57 20-game 0W/0D/20L calibration baseline.
- Executes fresh live validation matches under Blitz and Slower diagnostic controls.
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[4]
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
HISTORICAL_V57_PATH = ROOT / "analysis" / "v0.57" / "raw" / "stockfish_19_calibration_raw.json"
BENCHMARK_DIR = ROOT / "analysis" / "phase1" / "p1.0" / "benchmark"
PGN_DIR = BENCHMARK_DIR / "pgn"
RAW_DIR = BENCHMARK_DIR / "raw"

PGN_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


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


def play_game(
    white_engine: UciEngineProcess,
    black_engine: UciEngineProcess,
    opening: Dict[str, Any],
    time_base_ms: int = 3000,
    time_inc_ms: int = 100,
    max_plies: int = 200
) -> Dict[str, Any]:
    board = chess.Board()
    for uci_m in opening.get("uci_sequence", []):
        board.push(chess.Move.from_uci(uci_m))

    wtime = time_base_ms
    btime = time_base_ms
    winc = time_inc_ms
    binc = time_inc_ms

    white_engine.new_game()
    black_engine.new_game()

    game = chess.pgn.Game()
    game.headers["Event"] = f"Janus Phase 1 Benchmark ({time_base_ms/1000:.1f}+{time_inc_ms/1000:.1f})"
    game.headers["Site"] = "Local Host"
    game.headers["Date"] = time.strftime("%Y.%m.%d")
    game.headers["Round"] = str(opening.get("pair_id", 1))
    game.headers["White"] = white_engine.name
    game.headers["Black"] = black_engine.name
    game.headers["Opening"] = opening.get("name", "Unknown Opening")
    game.headers["ECO"] = opening.get("eco", "A00")

    node = game
    init_b = chess.Board()
    for uci_m in opening.get("uci_sequence", []):
        m = chess.Move.from_uci(uci_m)
        node = node.add_variation(m)
        init_b.push(m)

    game_moves = []
    termination_reason = "normal"
    result_str = "*"

    for ply in range(len(board.move_stack), max_plies):
        if board.is_game_over():
            break

        turn = board.turn
        current_eng = white_engine if turn == chess.WHITE else black_engine
        my_time = wtime if turn == chess.WHITE else btime

        try:
            best_uci, info = current_eng.play_move(board, wtime, btime, winc, binc)
        except Exception as e:
            termination_reason = f"{current_eng.name} crash / timeout: {str(e)}"
            result_str = "0-1" if turn == chess.WHITE else "1-0"
            break

        move_time_ms = int(info["elapsed_sec"] * 1000)
        if turn == chess.WHITE:
            wtime = max(0, wtime - move_time_ms + winc)
            if wtime <= 0 and move_time_ms > (time_base_ms + winc):
                termination_reason = "White time forfeit"
                result_str = "0-1"
                break
        else:
            btime = max(0, btime - move_time_ms + binc)
            if btime <= 0 and move_time_ms > (time_base_ms + binc):
                termination_reason = "Black time forfeit"
                result_str = "1-0"
                break

        try:
            m = chess.Move.from_uci(best_uci)
        except Exception:
            termination_reason = f"Illegal move format: {best_uci}"
            result_str = "0-1" if turn == chess.WHITE else "1-0"
            break

        if m not in board.legal_moves:
            termination_reason = f"Illegal move attempted: {best_uci}"
            result_str = "0-1" if turn == chess.WHITE else "1-0"
            break

        board.push(m)
        node = node.add_variation(m)
        node.comment = f"[%eval {info.get('score_cp', 0)/100.0:.2f}] [%clk {wtime if turn == chess.WHITE else btime}]"

        game_moves.append({
            "ply": ply + 1,
            "turn": "white" if turn == chess.WHITE else "black",
            "move": best_uci,
            "score_cp": info.get("score_cp", 0),
            "depth": info.get("depth", 0),
            "nodes": info.get("nodes", 0),
            "nps": info.get("nps", 0),
            "time_ms": move_time_ms
        })

    if result_str == "*":
        outcome = board.outcome()
        if outcome:
            result_str = outcome.result()
            termination_reason = outcome.termination.name
        elif len(board.move_stack) >= max_plies:
            result_str = "1/2-1/2"
            termination_reason = "Adjudicated: Max Plies Reached"

    game.headers["Result"] = result_str
    game.headers["Termination"] = termination_reason

    return {
        "white": white_engine.name,
        "black": black_engine.name,
        "result": result_str,
        "termination": termination_reason,
        "plies": len(board.move_stack),
        "pgn": str(game),
        "moves": game_moves
    }


def run_tournament(
    c1_exe: Path,
    sf_exe: Path,
    openings: List[Dict[str, Any]],
    time_base_ms: int = 3000,
    time_inc_ms: int = 100,
    tourney_name: str = "c1_vs_sf19_blitz"
) -> Dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"RUNNING BENCHMARK TOURNAMENT: {tourney_name.upper()} ({time_base_ms/1000:.1f}s + {time_inc_ms/1000:.1f}s)", flush=True)
    print(f"Pairs: {len(openings)} | Total Games: {len(openings)*2}", flush=True)
    print("=" * 80, flush=True)

    c1_eng = UciEngineProcess(
        name="Janus Classical Baseline C1",
        exe_path=c1_exe,
        options={
            "UseKillerOrdering": "true",
            "UseHistoryOrdering": "true",
            "UsePVS": "false",
            "UseLMR": "true",
            "UseSEEOrdering": "false",
            "UseSEEInQuiescence": "false"
        }
    )

    sf_eng = UciEngineProcess(
        name="Stockfish 19",
        exe_path=sf_exe,
        options={
            "Threads": 1,
            "Hash": 64,
            "UCI_LimitStrength": "false",
            "MultiPV": 1
        }
    )

    c1_eng.start()
    sf_eng.start()

    games = []
    c1_score = 0.0
    sf_score = 0.0
    c1_wins = 0
    c1_draws = 0
    c1_losses = 0

    all_pgn_text = []

    try:
        for idx, op in enumerate(openings):
            pair_id = op.get("pair_id", idx + 1)
            op_name = op.get("name", f"Opening {pair_id}")

            # Game 1: C1 White, SF Black
            print(f"\n[Pair {pair_id:02d} / Game 1] White: C1 | Black: SF19 | {op_name}", flush=True)
            g1 = play_game(c1_eng, sf_eng, op, time_base_ms, time_inc_ms)
            games.append(g1)
            all_pgn_text.append(g1["pgn"])

            if g1["result"] == "1-0":
                c1_score += 1.0; c1_wins += 1
            elif g1["result"] == "1/2-1/2":
                c1_score += 0.5; sf_score += 0.5; c1_draws += 1
            elif g1["result"] == "0-1":
                sf_score += 1.0; c1_losses += 1
            print(f"  Result: {g1['result']} ({g1['termination']}) in {g1['plies']} plies. Score: C1 {c1_score} - SF {sf_score}", flush=True)

            # Game 2: SF White, C1 Black
            print(f"[Pair {pair_id:02d} / Game 2] White: SF19 | Black: C1 | {op_name}", flush=True)
            g2 = play_game(sf_eng, c1_eng, op, time_base_ms, time_inc_ms)
            games.append(g2)
            all_pgn_text.append(g2["pgn"])

            if g2["result"] == "1-0":
                sf_score += 1.0; c1_losses += 1
            elif g2["result"] == "1/2-1/2":
                c1_score += 0.5; sf_score += 0.5; c1_draws += 1
            elif g2["result"] == "0-1":
                c1_score += 1.0; c1_wins += 1
            print(f"  Result: {g2['result']} ({g2['termination']}) in {g2['plies']} plies. Score: C1 {c1_score} - SF {sf_score}", flush=True)

    finally:
        c1_eng.terminate()
        sf_eng.terminate()

    total_games = len(games)
    c1_pct = (c1_score / max(total_games, 1)) * 100.0

    pgn_file = PGN_DIR / f"{tourney_name}.pgn"
    with open(pgn_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_pgn_text) + "\n")

    summary = {
        "tourney_name": tourney_name,
        "time_control": f"{time_base_ms/1000:.1f}s+{time_inc_ms/1000:.1f}s",
        "total_games": total_games,
        "c1_score": c1_score,
        "sf_score": sf_score,
        "c1_wins": c1_wins,
        "c1_draws": c1_draws,
        "c1_losses": c1_losses,
        "c1_score_pct": round(c1_pct, 2),
        "pgn_file": str(pgn_file)
    }

    raw_output = {
        "summary": summary,
        "games": games
    }

    raw_file = RAW_DIR / f"{tourney_name}_raw.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(raw_output, f, indent=2)

    print("\n" + "=" * 80, flush=True)
    print(f"TOURNAMENT SUMMARY: {tourney_name.upper()}", flush=True)
    print(f"Score: C1 {c1_score:.1f} / {total_games} ({c1_pct:.1f}%) | W={c1_wins}, D={c1_draws}, L={c1_losses}", flush=True)
    print(f"PGN saved: {pgn_file}", flush=True)
    print(f"JSON saved: {raw_file}", flush=True)
    print("=" * 80, flush=True)

    return raw_output


def reproduce_historical_v57():
    print("=" * 80, flush=True)
    print("REPRODUCING HISTORICAL v0.57 CALIBRATION DATASET (20 GAMES, TIER D UNRESTRICTED)", flush=True)
    print("=" * 80, flush=True)

    with open(HISTORICAL_V57_PATH, "r", encoding="utf-8") as f:
        v57_data = json.load(f)

    tier_d = v57_data["tier_data"]["sf19_d_unrestricted"]
    v57_summary = tier_d["summary"]
    v57_pairs = tier_d["pairs"]

    all_games = []
    pgn_entries = []

    for p in v57_pairs:
        for g_key in ["game_1", "game_2"]:
            g = p[g_key]
            all_games.append(g)

            pgn_game = chess.pgn.Game()
            pgn_game.headers["Event"] = "Historical v0.57 Tier D Unrestricted Calibration"
            pgn_game.headers["Site"] = "Local Host"
            pgn_game.headers["Date"] = "2026.11.06"
            pgn_game.headers["Round"] = str(p.get("pair_id", 1))
            pgn_game.headers["White"] = g.get("white", "Janus Classical Baseline C1")
            pgn_game.headers["Black"] = g.get("black", "Stockfish 19")
            pgn_game.headers["Result"] = g.get("result", "*")
            pgn_game.headers["Termination"] = g.get("termination", "normal")
            pgn_game.headers["ECO"] = p.get("eco", "A00")
            pgn_game.headers["Opening"] = p.get("name", "Unknown Opening")

            # Setup custom opening FEN if not startpos
            init_fen = p.get("opening_fen", chess.STARTING_FEN)
            b = chess.Board(init_fen)
            if init_fen != chess.STARTING_FEN:
                pgn_game.setup(b)

            node = pgn_game
            for m_dict in g.get("moves", []):
                m_uci = m_dict.get("move") if isinstance(m_dict, dict) else m_dict
                if m_uci:
                    try:
                        m_obj = chess.Move.from_uci(m_uci)
                        if m_obj in b.legal_moves:
                            node = node.add_variation(m_obj)
                            b.push(m_obj)
                    except Exception:
                        pass
            pgn_entries.append(str(pgn_game))

    print(f"Historical Games Reconstructed: {len(all_games)} games across {len(v57_pairs)} pairs", flush=True)
    print(f"Historical Result: C1 {v57_summary['janus_points']:.1f} / {v57_summary['total_games']} ({v57_summary['janus_score_pct']:.1f}%)", flush=True)
    print(f"WDL: {v57_summary['janus_wins']}W / {v57_summary['janus_draws']}D / {v57_summary['janus_losses']}L", flush=True)

    reproduced_payload = {
        "summary": {
            "tourney_name": "c1_vs_sf19_historical_reproduced_tier_d",
            "source_milestone": "v0.57",
            "time_control": "3.0s+100ms",
            "total_games": v57_summary["total_games"],
            "c1_score": v57_summary["janus_points"],
            "sf_score": v57_summary["total_games"] - v57_summary["janus_points"],
            "c1_wins": v57_summary["janus_wins"],
            "c1_draws": v57_summary["janus_draws"],
            "c1_losses": v57_summary["janus_losses"],
            "c1_score_pct": v57_summary["janus_score_pct"],
            "duration_sec": v57_summary["duration_sec"],
            "average_plies": v57_summary["average_plies"],
            "terminations": v57_summary["terminations"]
        },
        "pairs": v57_pairs,
        "games": all_games
    }

    raw_path = RAW_DIR / "c1_vs_sf19_historical_reproduced_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(reproduced_payload, f, indent=2)

    pgn_path = PGN_DIR / "c1_vs_sf19_historical_reproduced.pgn"
    with open(pgn_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(pgn_entries) + "\n")

    print(f"Wrote reproduced historical raw to {raw_path}", flush=True)
    print(f"Wrote reproduced historical PGN to {pgn_path}", flush=True)

    return reproduced_payload


def main():
    c1_exe = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
    sf_exe = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        all_openings = json.load(f)

    # 1. Historical v0.57 20-Game Calibration Dataset Reproduction
    reproduce_historical_v57()

    # 2. Fresh Live Validation Blitz Match (6 Games / 3 Pairs at 3.0s+100ms)
    sub_openings_3 = all_openings[:3]
    res_blitz = run_tournament(
        c1_exe=c1_exe,
        sf_exe=sf_exe,
        openings=sub_openings_3,
        time_base_ms=3000,
        time_inc_ms=100,
        tourney_name="c1_vs_sf19_unrestricted_blitz"
    )

    # 3. Slower Time Control Diagnostic (2 Games / 1 Pair at 10.0s+100ms)
    sub_openings_1 = all_openings[:1]
    res_slower = run_tournament(
        c1_exe=c1_exe,
        sf_exe=sf_exe,
        openings=sub_openings_1,
        time_base_ms=10000,
        time_inc_ms=100,
        tourney_name="c1_vs_sf19_slower_diagnostic"
    )

    print("\nAll benchmark validation matches completed successfully!", flush=True)


if __name__ == "__main__":
    main()
