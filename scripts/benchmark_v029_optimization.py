"""Project Janus v0.29 - Interleaved Baseline vs Candidate Benchmark Harness.

Performs 5 interleaved repetitions across all 6 standard benchmark positions at
depths 4 and 5, comparing the v0.28 eager-check baseline against the v0.29 lazy LMR candidate.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any

import chess
from janus.search import JanusSearch

POSITIONS_PATH = os.path.join("benchmarks", "positions.json")
OUTPUT_DIR = os.path.join("analysis", "v0.29", "benchmarks")


def load_positions() -> list[dict[str, Any]]:
    with open(POSITIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_pv_legality(board: chess.Board, pv: list[chess.Move]) -> bool:
    b = board.copy()
    for m in pv:
        if m not in b.legal_moves:
            return False
        b.push(m)
    return True


# ---------------------------------------------------------------------------
# Load exact v0.28 eager baseline _negamax
# ---------------------------------------------------------------------------
with open("src/janus/search.py", "r", encoding="utf-8") as f:
    src_code = f.read()

target_lazy = """        for move in moves:
            is_capture = board.is_capture(move)
            is_promotion = move.promotion is not None

            eligible_for_lmr = (
                self.enable_lmr
                and moves_searched >= 3
                and depth >= 3
                and ply > 0
                and not in_check
                and not is_capture
                and not is_promotion
                and (
                    ply >= len(self.killers)
                    or (move != self.killers[ply][0] and move != self.killers[ply][1])
                )
                and not board.gives_check(move)
            )"""

replacement_eager = """        for move in moves:
            is_capture = board.is_capture(move)
            is_promotion = move.promotion is not None
            gives_check = board.gives_check(move)

            eligible_for_lmr = (
                self.enable_lmr
                and moves_searched >= 3
                and depth >= 3
                and ply > 0
                and not in_check
                and not is_capture
                and not is_promotion
                and not gives_check
                and (
                    ply >= len(self.killers)
                    or (move != self.killers[ply][0] and move != self.killers[ply][1])
                )
            )"""

assert target_lazy in src_code, "Target lazy block not found in src/janus/search.py"
src_eager = src_code.replace(target_lazy, replacement_eager)

eager_ns = {"__name__": "janus.search", "__file__": "src/janus/search.py"}
exec(src_eager, eager_ns)
_negamax_eager_baseline = eager_ns["JanusSearch"]._negamax


def run_benchmark(
    reps: int = 5,
    depths: list[int] = [4, 5],
) -> dict[str, Any]:
    positions = load_positions()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "reps": reps,
        "depths": depths,
        "positions_count": len(positions),
        "baseline_commit": "5f76a62",
    }

    # Store candidate implementation
    cand_negamax = JanusSearch._negamax

    # 1. Warm-up run
    print("Executing warm-up run...")
    for _ in range(2):
        JanusSearch._negamax = _negamax_eager_baseline
        s_warm = JanusSearch()
        s_warm.search(chess.Board(), max_depth=3)
        JanusSearch._negamax = cand_negamax
        s_warm = JanusSearch()
        s_warm.search(chess.Board(), max_depth=3)

    raw_runs: list[dict[str, Any]] = []

    print(f"Starting {reps} interleaved benchmark repetitions for depths {depths}...")

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        for depth in depths:
            for p in positions:
                pid = p["id"]
                fen = p["fen"]

                # 1. Baseline Run (Eager)
                JanusSearch._negamax = _negamax_eager_baseline
                b_base = chess.Board(fen)
                s_base = JanusSearch()
                t0 = time.perf_counter()
                res_base = s_base.search(b_base, max_depth=depth)
                elapsed_base = time.perf_counter() - t0
                pv_base_legal = verify_pv_legality(b_base, res_base.pv)

                raw_runs.append({
                    "rep": rep,
                    "depth": depth,
                    "position_id": pid,
                    "arm": "baseline",
                    "elapsed_s": elapsed_base,
                    "nodes": res_base.nodes,
                    "nps": res_base.nodes / elapsed_base if elapsed_base > 0 else 0,
                    "best_move": str(res_base.best_move),
                    "score": res_base.score,
                    "pv": [str(m) for m in res_base.pv],
                    "pv_legal": pv_base_legal,
                    "lmr_considered": res_base.lmr_considered,
                    "lmr_reduced_searches": res_base.lmr_reduced_searches,
                })

                # 2. Candidate Run (Lazy)
                JanusSearch._negamax = cand_negamax
                b_cand = chess.Board(fen)
                s_cand = JanusSearch()
                t0 = time.perf_counter()
                res_cand = s_cand.search(b_cand, max_depth=depth)
                elapsed_cand = time.perf_counter() - t0
                pv_cand_legal = verify_pv_legality(b_cand, res_cand.pv)

                raw_runs.append({
                    "rep": rep,
                    "depth": depth,
                    "position_id": pid,
                    "arm": "candidate",
                    "elapsed_s": elapsed_cand,
                    "nodes": res_cand.nodes,
                    "nps": res_cand.nodes / elapsed_cand if elapsed_cand > 0 else 0,
                    "best_move": str(res_cand.best_move),
                    "score": res_cand.score,
                    "pv": [str(m) for m in res_cand.pv],
                    "pv_legal": pv_cand_legal,
                    "lmr_considered": res_cand.lmr_considered,
                    "lmr_reduced_searches": res_cand.lmr_reduced_searches,
                })

                speedup = (
                    (elapsed_base - elapsed_cand) / elapsed_base * 100
                    if elapsed_base > 0
                    else 0.0
                )
                print(
                    f"Rep {rep} | D{depth} | {pid:<18} | "
                    f"Base: {elapsed_base:.3f}s ({res_base.nodes}n) | "
                    f"Cand: {elapsed_cand:.3f}s ({res_cand.nodes}n) | "
                    f"Speedup: {speedup:+.1f}%"
                )

    # Restore candidate
    JanusSearch._negamax = cand_negamax

    output_data = {
        "metadata": metadata,
        "runs": raw_runs,
    }

    out_file = os.path.join(OUTPUT_DIR, "v029_interleaved_benchmark.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved raw benchmark data to {out_file}")

    return output_data


if __name__ == "__main__":
    run_benchmark(reps=5, depths=[4, 5])
