"""Project Janus v0.31 - Matched Cumulative Benchmark: v0.27 vs v0.30.

Performs 5 interleaved repetitions across all 6 standard benchmark positions at
depths 4 and 5, comparing the historical pre-optimisation v0.27 baseline (commit 851afc7)
against the current v0.30 candidate (commit 05de411).
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
import time
import types
from datetime import datetime, timezone
from typing import Any

import chess

POSITIONS_PATH = os.path.join("benchmarks", "positions.json")
OUTPUT_DIR = os.path.join("analysis", "v0.31", "benchmarks")


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


def load_package(pkg_name: str, pkg_dir: str) -> types.ModuleType:
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [pkg_dir]
    pkg.__file__ = os.path.join(pkg_dir, "__init__.py")
    sys.modules[pkg_name] = pkg

    for mod_name in ["evaluation", "search", "uci"]:
        file_path = os.path.join(pkg_dir, f"{mod_name}.py")
        if os.path.exists(file_path):
            full_name = f"{pkg_name}.{mod_name}"
            spec = importlib.util.spec_from_file_location(full_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[full_name] = mod
            setattr(pkg, mod_name, mod)
            spec.loader.exec_module(mod)
    return pkg


def run_benchmark(
    reps: int = 5,
    depths: list[int] = [4, 5],
) -> dict[str, Any]:
    base_dir = os.path.abspath(".worktree_v027/src/janus")
    cand_dir = os.path.abspath("src/janus")

    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"v0.27 worktree not found at {base_dir}")

    pkg_base = load_package("janus_v027", base_dir)
    pkg_cand = load_package("janus_v030", cand_dir)

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
        "baseline_commit": "851afc7",
        "candidate_commit": "05de411",
        "description": "Cumulative matched comparison: pre-optimisation v0.27 vs v0.30",
    }

    # 1. Warm-up run
    print("Executing warm-up run (2 reps at depth 3)...")
    for _ in range(2):
        s_warm_base = pkg_base.search.JanusSearch()
        s_warm_base.search(chess.Board(), max_depth=3)
        s_warm_cand = pkg_cand.search.JanusSearch()
        s_warm_cand.search(chess.Board(), max_depth=3)

    raw_runs: list[dict[str, Any]] = []

    print(f"Starting {reps} interleaved benchmark repetitions for depths {depths}...")

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        for depth in depths:
            for p in positions:
                pid = p["id"]
                fen = p["fen"]

                # 1. Baseline Run (v0.27)
                b_base = chess.Board(fen)
                s_base = pkg_base.search.JanusSearch()
                t0 = time.perf_counter()
                res_base = s_base.search(b_base.copy(), max_depth=depth)
                elapsed_base = time.perf_counter() - t0
                pv_base_legal = verify_pv_legality(b_base, res_base.pv)

                raw_runs.append({
                    "rep": rep,
                    "depth": depth,
                    "position_id": pid,
                    "arm": "baseline",
                    "commit": "851afc7",
                    "elapsed_s": elapsed_base,
                    "nodes": res_base.nodes,
                    "nps": res_base.nodes / elapsed_base if elapsed_base > 0 else 0,
                    "best_move": str(res_base.best_move),
                    "score": res_base.score,
                    "pv": [str(m) for m in res_base.pv],
                    "pv_legal": pv_base_legal,
                })

                # 2. Candidate Run (v0.30)
                b_cand = chess.Board(fen)
                s_cand = pkg_cand.search.JanusSearch()
                t0 = time.perf_counter()
                res_cand = s_cand.search(b_cand.copy(), max_depth=depth)
                elapsed_cand = time.perf_counter() - t0
                pv_cand_legal = verify_pv_legality(b_cand, res_cand.pv)

                raw_runs.append({
                    "rep": rep,
                    "depth": depth,
                    "position_id": pid,
                    "arm": "candidate",
                    "commit": "05de411",
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
                    f"v0.27: {elapsed_base:.3f}s ({res_base.nodes}n) | "
                    f"v0.30: {elapsed_cand:.3f}s ({res_cand.nodes}n) | "
                    f"Speedup: {speedup:+.1f}%"
                )

    output_data = {
        "metadata": metadata,
        "runs": raw_runs,
    }

    out_file = os.path.join(OUTPUT_DIR, "v031_cumulative_benchmark.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved raw cumulative benchmark data to {out_file}")

    return output_data


if __name__ == "__main__":
    run_benchmark(reps=5, depths=[4, 5])
