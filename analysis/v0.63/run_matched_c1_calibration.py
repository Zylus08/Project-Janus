"""Project Janus v0.63 - Matched C1 Calibration vs Stockfish 1600.

Runs Classical Baseline C1 against Stockfish 19 (UCI_Elo=1600) across the exact same
10 opening pairs from independent_openings_v062.json used by N1 in v0.62.
"""

import json
import time
import math
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import chess
import chess.pgn
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "v0.56" / "tests"))
from tournament_controller import adjudicate_board

CORPUS_PATH = ROOT / "analysis" / "v0.62" / "corpus" / "independent_openings_v062.json"
C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
STOCKFISH_EXE = Path(r"E:\ChessXML\tools\stockfish\stockfish.exe")
OUT_DIR = ROOT / "analysis" / "v0.63"


class UCIEngineProcess:
    def __init__(self, exe_path: Path, options=None, cwd=None):
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(cwd) if cwd else None,
        )
        self.options = options or {}
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() in ("uciok", "readyok"):
                break
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
                self.p.wait(timeout=2.0)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


def play_game(game_id, pair_id, opening_name, moves, white_is_c1):
    c1_opts = {
        "UseKillerOrdering": True,
        "UseHistoryOrdering": True,
        "UseLMR": True,
        "UsePVS": False,
        "UseSEEOrdering": False,
        "UseSEEInQuiescence": False,
    }
    sf_opts = {
        "UCI_LimitStrength": True,
        "UCI_Elo": 1600,
        "Threads": 1,
        "Hash": 16,
    }

    if white_is_c1:
        white_eng = UCIEngineProcess(C1_EXE, c1_opts, cwd=ROOT)
        black_eng = UCIEngineProcess(STOCKFISH_EXE, sf_opts)
    else:
        white_eng = UCIEngineProcess(STOCKFISH_EXE, sf_opts)
        black_eng = UCIEngineProcess(C1_EXE, c1_opts, cwd=ROOT)

    board = chess.Board()
    for m in moves:
        board.push(chess.Move.from_uci(m))

    wtime = 3000
    btime = 3000
    winc = 100
    binc = 100

    white_eng.ucinewgame()
    black_eng.ucinewgame()

    moves_played = list(moves)
    game_over, result_str, termination = adjudicate_board(board, len(moves_played), 300)

    while not game_over and len(moves_played) < 300:
        active = white_eng if board.turn == chess.WHITE else black_eng
        bm, el = active.play_move(board.fen(), wtime, btime, winc, binc)
        el_ms = int(el * 1000)

        if board.turn == chess.WHITE:
            wtime = max(10, wtime - el_ms + winc)
        else:
            btime = max(10, btime - el_ms + binc)

        if not bm:
            result_str = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "forfeit_no_move"
            break

        try:
            m = chess.Move.from_uci(bm)
            if m not in board.legal_moves:
                result_str = "0-1" if board.turn == chess.WHITE else "1-0"
                termination = f"illegal_move_{bm}"
                break
            board.push(m)
            moves_played.append(bm)
        except Exception:
            result_str = "0-1" if board.turn == chess.WHITE else "1-0"
            termination = "parse_error"
            break

        game_over, result_str, termination = adjudicate_board(board, len(moves_played), 300)

    white_eng.close()
    black_eng.close()

    if result_str == "1-0":
        c1_pts = 1.0 if white_is_c1 else 0.0
    elif result_str == "0-1":
        c1_pts = 0.0 if white_is_c1 else 1.0
    else:
        c1_pts = 0.5

    return {
        "game_id": game_id,
        "pair_id": pair_id,
        "white_is_c1": white_is_c1,
        "result": result_str,
        "c1_points": c1_pts,
        "termination": termination,
        "plies": len(moves_played),
    }


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.63 — MATCHED EXTERNAL CALIBRATION")
    print("Classical Baseline C1 vs Stockfish 19 (UCI_Elo=1600)")
    print("Corpus: First 10 opening pairs of independent_openings_v062.json (20 games)")
    print("=" * 80, flush=True)

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)[:10]

    tasks = []
    gid = 1
    for pid, op in enumerate(openings):
        moves = op.get("uci_sequence", [])
        name = op.get("name", "")
        tasks.append((gid, pid, name, moves, True))
        gid += 1
        tasks.append((gid, pid, name, moves, False))
        gid += 1

    results = []
    t_start = time.time()
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(play_game, *t): t[0] for t in tasks}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            print(f"[{len(results)}/20] Game {res['game_id']} finished: {res['result']} (C1 pts: {res['c1_points']})", flush=True)

    wins = sum(1 for r in results if r["c1_points"] == 1.0)
    draws = sum(1 for r in results if r["c1_points"] == 0.5)
    losses = sum(1 for r in results if r["c1_points"] == 0.0)
    pts = wins + 0.5 * draws
    pct = (pts / len(results)) * 100.0
    p_clamped = max(0.001, min(0.999, pct / 100.0))
    elo_d = -400.0 * math.log10(1.0 / p_clamped - 1.0)
    implied_elo = round(1600 + elo_d)

    print("\n--- Classical C1 Matched Calibration Results ---")
    print(f"Score: {wins}W - {draws}D - {losses}L ({pts:.1f}/20, {pct:.1f}%)")
    print(f"Estimated Elo Delta: {elo_d:+.1f} | Implied Elo: ~{implied_elo}")
    print(f"Elapsed Time: {time.time() - t_start:.1f}s")

    out_file = OUT_DIR / "matched_c1_vs_sf1600.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summary": {"wins": wins, "draws": draws, "losses": losses, "points": pts, "pct": pct, "elo_delta": elo_d, "implied_elo": implied_elo}, "games": results}, f, indent=2)
    print(f"Saved matched calibration to {out_file}")


if __name__ == "__main__":
    main()
