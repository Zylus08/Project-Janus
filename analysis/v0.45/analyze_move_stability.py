"""Evaluate move stability and decision quality against Stockfish 19 reference oracle."""
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
import chess

from janus.search import JanusSearch

STOCKFISH_PATH = r"E:\ChessXML\tools\stockfish\stockfish.exe"

class StockfishOracle:
    def __init__(self, depth: int = 12):
        self.depth = depth
        self.process = subprocess.Popen(
            [STOCKFISH_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._send("uci")
        self._read_until("uciok")
        self._send("setoption name Threads value 1")
        self._send("setoption name Hash value 64")
        self._send("isready")
        self._read_until("readyok")

    def _send(self, cmd: str) -> None:
        if self.process and self.process.stdin:
            self.process.stdin.write(f"{cmd}\n")
            self.process.stdin.flush()

    def _read_until(self, target: str) -> list[str]:
        lines = []
        if not self.process or not self.process.stdout:
            return lines
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            lines.append(line_str)
            if line_str == target or line_str.startswith(target):
                break
        return lines

    def eval_position(self, fen: str) -> Tuple[int, Optional[str]]:
        self._send(f"position fen {fen}")
        self._send(f"go depth {self.depth}")
        score_side = 0
        best_move = None
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if "score cp" in line_str:
                parts = line_str.split()
                try:
                    idx = parts.index("cp")
                    score_side = int(parts[idx + 1])
                except (ValueError, IndexError):
                    pass
            elif "score mate" in line_str:
                parts = line_str.split()
                try:
                    idx = parts.index("mate")
                    mate_plies = int(parts[idx + 1])
                    score_side = 30000 if mate_plies > 0 else -30000
                except (ValueError, IndexError):
                    pass
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    best_move = parts[1]
                break
        return score_side, best_move

    def close(self):
        try:
            self._send("quit")
            self.process.terminate()
            self.process.wait(timeout=1.0)
        except Exception:
            pass

def run():
    corpus_path = Path("analysis/v0.45/diagnostic_positions/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # 1. Load fixed_depth and fixed_time data
    with open("analysis/v0.45/fixed_depth/fixed_depth_ladder_raw.json", "r", encoding="utf-8") as f:
        fixed_depth_data = json.load(f)

    with open("analysis/v0.45/fixed_time/fixed_time_ladder_raw.json", "r", encoding="utf-8") as f:
        fixed_time_data = json.load(f)

    # Move stability analysis across fixed depths 2 -> 3 -> 4 -> 5
    # For each position, count how many times the best move flips between consecutive depths
    by_pos_depth = {}
    for r in fixed_depth_data["results"]:
        pid = r["position_id"]
        d = r["target_depth"]
        if pid not in by_pos_depth: by_pos_depth[pid] = {}
        by_pos_depth[pid][d] = r

    k0_flips = 0
    rfp_flips = 0
    total_transitions = 0

    for pid, d_map in by_pos_depth.items():
        for d in [2, 3, 4]:
            if d in d_map and (d + 1) in d_map:
                total_transitions += 1
                if d_map[d]["k0"]["move"] != d_map[d + 1]["k0"]["move"]:
                    k0_flips += 1
                if d_map[d]["rfp"]["move"] != d_map[d + 1]["rfp"]["move"]:
                    rfp_flips += 1

    print(f"Move Flips across Depth transitions (2->3, 3->4, 4->5):")
    print(f"  Total Transitions: {total_transitions}")
    print(f"  K0 Move Flips: {k0_flips} ({k0_flips/total_transitions*100:.1f}%)")
    print(f"  RFP Move Flips: {rfp_flips} ({rfp_flips/total_transitions*100:.1f}%)")

    # 2. Reference evaluation using Stockfish 19 (depth 12)
    oracle = StockfishOracle(depth=12)
    reference_records = []

    print(f"\nEvaluating {len(corpus)} positions with Stockfish 19 (depth 12)...")
    for idx, pos in enumerate(corpus, 1):
        fen = pos["fen"]
        sf_score, sf_best_mv = oracle.eval_position(fen)
        reference_records.append({
            "position_id": pos["id"],
            "fen": fen,
            "stockfish_depth": 12,
            "stockfish_score_cp": sf_score,
            "stockfish_best_move": sf_best_mv,
        })

    oracle.close()

    out_ref = Path("analysis/v0.45/reference/stockfish_reference.json")
    with open(out_ref, "w", encoding="utf-8") as f:
        json.dump(reference_records, f, indent=2)
    print(f"Saved reference analysis to {out_ref}")

    # 3. Decision quality comparison at match budget (180 ms)
    ref_by_id = {r["position_id"]: r for r in reference_records}
    results_180ms = [r for r in fixed_time_data["results"] if r["budget_ms"] == 180]

    k0_agree_sf = 0
    rfp_agree_sf = 0

    for r in results_180ms:
        pid = r["position_id"]
        sf_mv = ref_by_id[pid]["stockfish_best_move"]
        if r["k0"]["move"] == sf_mv: k0_agree_sf += 1
        if r["rfp"]["move"] == sf_mv: rfp_agree_sf += 1

    print(f"\nDecision Quality at Match Time Budget (180ms):")
    print(f"  K0 Agreement with Stockfish:  {k0_agree_sf}/{len(results_180ms)} ({k0_agree_sf/len(results_180ms)*100:.1f}%)")
    print(f"  RFP Agreement with Stockfish: {rfp_agree_sf}/{len(results_180ms)} ({rfp_agree_sf/len(results_180ms)*100:.1f}%)")

    stability_report = {
        "move_transitions_total": total_transitions,
        "k0_depth_flips": k0_flips,
        "rfp_depth_flips": rfp_flips,
        "k0_flip_rate_pct": (k0_flips / total_transitions) * 100.0 if total_transitions else 0,
        "rfp_flip_rate_pct": (rfp_flips / total_transitions) * 100.0 if total_transitions else 0,
        "stockfish_agreement_180ms": {
            "total_positions": len(results_180ms),
            "k0_agreements": k0_agree_sf,
            "rfp_agreements": rfp_agree_sf,
            "k0_agreement_pct": (k0_agree_sf / len(results_180ms)) * 100.0 if results_180ms else 0,
            "rfp_agreement_pct": (rfp_agree_sf / len(results_180ms)) * 100.0 if results_180ms else 0,
        }
    }

    with open("analysis/v0.45/reports/move_stability_summary.json", "w", encoding="utf-8") as f:
        json.dump(stability_report, f, indent=2)

if __name__ == "__main__":
    run()

