"""Stockfish reference generation script using direct subprocess protocol (Windows-safe)."""

import sys
import os
import json
import subprocess
import time
from pathlib import Path

STOCKFISH_PATH = r"E:\ChessXML\tools\stockfish\stockfish.exe"


class StockfishDriver:
    def __init__(self, path: str):
        self.p = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._send("uci")
        while True:
            line = self.p.stdout.readline()
            if line.strip() == "uciok":
                break
        self._send("isready")
        while True:
            line = self.p.stdout.readline()
            if line.strip() == "readyok":
                break

    def _send(self, cmd: str):
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def evaluate(self, fen: str, depth: int) -> dict:
        self._send(f"position fen {fen}")
        self._send(f"go depth {depth}")

        best_move = None
        score_cp = 0
        nodes = 0

        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("info") and f"depth {depth}" in line_str:
                parts = line_str.split()
                if "score" in parts:
                    idx = parts.index("score")
                    score_type = parts[idx + 1]
                    val = int(parts[idx + 2])
                    if score_type == "cp":
                        score_cp = val
                    elif score_type == "mate":
                        score_cp = 10000 if val > 0 else -10000
                if "nodes" in parts:
                    nodes = int(parts[parts.index("nodes") + 1])
                if "pv" in parts:
                    best_move = parts[parts.index("pv") + 1]
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if not best_move and len(parts) > 1:
                    best_move = parts[1]
                break

        return {"depth": depth, "best_move": best_move, "score_cp": score_cp, "nodes": nodes}

    def close(self):
        try:
            self._send("quit")
            self.p.wait(timeout=2)
        except Exception:
            self.p.kill()


def main():
    corpus_path = Path("analysis/v0.46/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        positions = json.load(f)

    depths = [8, 10, 12, 14]
    results = {}

    print(f"Launching Stockfish driver at {STOCKFISH_PATH}...")
    sf = StockfishDriver(STOCKFISH_PATH)

    try:
        for idx, pos in enumerate(positions, 1):
            pos_id = pos["id"]
            fen = pos["fen"]

            pos_records = {}
            for d in depths:
                eval_data = sf.evaluate(fen, d)
                pos_records[str(d)] = eval_data

            stable_12_14 = (pos_records["12"]["best_move"] == pos_records["14"]["best_move"])
            stable_10_12 = (pos_records["10"]["best_move"] == pos_records["12"]["best_move"])

            results[pos_id] = {
                "id": pos_id,
                "fen": fen,
                "depth_evals": pos_records,
                "reference_move_d12": pos_records["12"]["best_move"],
                "reference_score_d12": pos_records["12"]["score_cp"],
                "reference_move_d14": pos_records["14"]["best_move"],
                "reference_score_d14": pos_records["14"]["score_cp"],
                "stable_12_14": stable_12_14,
                "stable_10_12": stable_10_12,
            }
            print(f"[{idx}/{len(positions)}] {pos_id}: d12={pos_records['12']['best_move']} ({pos_records['12']['score_cp']}cp), d14={pos_records['14']['best_move']} ({pos_records['14']['score_cp']}cp), stable={stable_12_14}")

    finally:
        sf.close()

    out_file = Path("analysis/v0.46/reference/stockfish_reference_ladder.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nStockfish reference ladder saved to {out_file}")


if __name__ == "__main__":
    main()
