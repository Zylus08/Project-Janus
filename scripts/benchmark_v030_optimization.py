"""Project Janus v0.30 - Interleaved Baseline vs Candidate Benchmark Harness.

Performs 5 interleaved repetitions across all 6 standard benchmark positions at
depths 4 and 5, comparing the v0.29 quiescence baseline (redundant legal move generation
on root entry) against the v0.30 quiescence candidate (lazy/bypassed root stalemate check).
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
OUTPUT_DIR = os.path.join("analysis", "v0.30", "benchmarks")


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
# Construct Baseline and Candidate _negamax implementations
# ---------------------------------------------------------------------------
with open("src/janus/search.py", "r", encoding="utf-8") as f:
    src_code = f.read()

target_cand = "return self._quiescence(board, alpha, beta, ply, check_stalemate=False), []"
replacement_base = "return self._quiescence(board, alpha, beta, ply, check_stalemate=True), []"

assert target_cand in src_code, "Target candidate block not found in src/janus/search.py"
src_base = src_code.replace(target_cand, replacement_base)

base_ns = {"__name__": "janus.search", "__file__": "src/janus/search.py"}
exec(src_base, base_ns)
_negamax_baseline = base_ns["JanusSearch"]._negamax

_negamax_candidate = JanusSearch._negamax


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
        "baseline_commit": "b5a3f84",
    }

    # 1. Warm-up run
    print("Executing warm-up run...")
    for _ in range(2):
        JanusSearch._negamax = _negamax_baseline
        s_warm = JanusSearch()
        s_warm.search(chess.Board(), max_depth=3)
        JanusSearch._negamax = _negamax_candidate
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

                # 1. Baseline Run (Redundant check_stalemate=True)
                JanusSearch._negamax = _negamax_baseline
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
                })

                # 2. Candidate Run (Optimized check_stalemate=False)
                JanusSearch._negamax = _negamax_candidate
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
    JanusSearch._negamax = _negamax_candidate

    output_data = {
        "metadata": metadata,
        "runs": raw_runs,
    }

    out_file = os.path.join(OUTPUT_DIR, "v030_interleaved_benchmark.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved raw benchmark data to {out_file}")

    return output_data


if __name__ == "__main__":
    run_benchmark(reps=5, depths=[4, 5])
