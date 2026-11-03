"""Reproducible Time Management Benchmark for Project Janus v0.35.

Evaluates and measures:
1. Fixed movetime allocations (e.g. 100ms, 250ms, 500ms)
2. Clock-only allocations (e.g. 6s, 30s, 60s without increment)
3. Fischer increment allocations (e.g. 3s+100ms, 10s+200ms, 60s+100ms, 500ms+50ms)

Distinguishes:
- Pure allocation calculation overhead (microseconds)
- Actual search duration vs allocated budget
- Deadline overshoot distribution
- Nodes, depth, and NPS
- Termination reason
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from janus import evaluation
from janus.search import JanusSearch
from janus.time_manager import TimeManager, TimeManagerConfig


def run_benchmark(
    positions: list[dict[str, str]],
    trials: int = 3,
    output_path: Optional[Path] = None,
) -> dict[str, Any]:
    # Configure Janus v0.34 tapered evaluation (--eval-all)
    evaluation.set_evaluation_features(
        pawn_structure=True,
        rook_files=True,
        king_safety=True,
        tapered_eval=True,
    )

    tm = TimeManager()
    engine = JanusSearch(tt_max_entries=50_000, time_manager=tm)

    # Time control test profiles
    test_profiles = [
        # Mode A: Fixed Movetime
        {
            "mode": "fixed_movetime",
            "name": "movetime_100ms",
            "kwargs": {"movetime": 100},
        },
        {
            "mode": "fixed_movetime",
            "name": "movetime_250ms",
            "kwargs": {"movetime": 250},
        },
        {
            "mode": "fixed_movetime",
            "name": "movetime_500ms",
            "kwargs": {"movetime": 500},
        },
        # Mode B: Clock-only (no increment)
        {
            "mode": "clock_only",
            "name": "clock_6s_sudden_death",
            "kwargs": {"wtime": 6000, "btime": 6000},
        },
        {
            "mode": "clock_only",
            "name": "clock_30s_sudden_death",
            "kwargs": {"wtime": 30000, "btime": 30000},
        },
        {
            "mode": "clock_only",
            "name": "clock_60s_sudden_death",
            "kwargs": {"wtime": 60000, "btime": 60000},
        },
        # Mode C: Fischer Increment
        {
            "mode": "fischer_increment",
            "name": "fischer_3s_plus_100ms",
            "kwargs": {"wtime": 3000, "btime": 3000, "winc": 100, "binc": 100},
        },
        {
            "mode": "fischer_increment",
            "name": "fischer_10s_plus_200ms",
            "kwargs": {"wtime": 10000, "btime": 10000, "winc": 200, "binc": 200},
        },
        {
            "mode": "fischer_increment",
            "name": "fischer_60s_plus_100ms",
            "kwargs": {"wtime": 60000, "btime": 60000, "winc": 100, "binc": 100},
        },
        {
            "mode": "fischer_increment",
            "name": "fischer_low_clock_500ms_plus_50ms",
            "kwargs": {"wtime": 500, "btime": 500, "winc": 50, "binc": 50},
        },
    ]

    all_results = []
    summary_by_profile = {}

    for profile in test_profiles:
        p_mode = profile["mode"]
        p_name = profile["name"]
        kwargs = profile["kwargs"]

        profile_overshoots = []
        profile_durations = []
        profile_budgets = []
        profile_alloc_latencies_us = []
        profile_nodes = []
        profile_depths = []

        print(f"Benchmarking {p_name} ({p_mode})...")

        for pos in positions:
            pos_id = pos["id"]
            fen = pos["fen"]
            board = chess.Board(fen)

            for trial in range(1, trials + 1):
                # Clear transposition table and history for repeatability
                engine.tt.clear()
                engine.history = [[0] * 64 for _ in range(64)]
                engine.killers = [[None, None] for _ in range(engine.max_killers_ply)]

                # Measure pure allocation calculation latency
                t_alloc_start = time.perf_counter()
                budget_s = tm.allocate_time(board.turn, **kwargs)
                t_alloc_end = time.perf_counter()
                alloc_latency_us = (t_alloc_end - t_alloc_start) * 1_000_000.0
                profile_alloc_latencies_us.append(alloc_latency_us)

                budget_ms = budget_s * 1000.0 if budget_s is not None else 0.0
                profile_budgets.append(budget_ms)

                # Execute search
                t_search_start = time.monotonic()
                res = engine.search(board, max_depth=64, time_limit=budget_s)
                t_search_end = time.monotonic()

                actual_duration_ms = (t_search_end - t_search_start) * 1000.0
                overshoot_ms = max(0.0, actual_duration_ms - budget_ms)

                profile_overshoots.append(overshoot_ms)
                profile_durations.append(actual_duration_ms)
                profile_nodes.append(res.nodes)
                profile_depths.append(res.depth)

                termination = "depth_reached" if res.depth >= 64 else "deadline_reached"
                nps = int(res.nodes / max(0.001, res.elapsed))

                record = {
                    "profile": p_name,
                    "mode": p_mode,
                    "position_id": pos_id,
                    "trial": trial,
                    "budget_ms": round(budget_ms, 2),
                    "actual_ms": round(actual_duration_ms, 2),
                    "overshoot_ms": round(overshoot_ms, 2),
                    "alloc_latency_us": round(alloc_latency_us, 3),
                    "depth": res.depth,
                    "nodes": res.nodes,
                    "nps": nps,
                    "best_move": res.best_move.uci() if res.best_move else "0000",
                    "termination": termination,
                }
                all_results.append(record)

        summary_by_profile[p_name] = {
            "mode": p_mode,
            "median_budget_ms": round(statistics.median(profile_budgets), 2),
            "median_actual_ms": round(statistics.median(profile_durations), 2),
            "median_overshoot_ms": round(statistics.median(profile_overshoots), 2),
            "max_overshoot_ms": round(max(profile_overshoots), 2),
            "mean_overshoot_ms": round(statistics.mean(profile_overshoots), 2),
            "median_alloc_latency_us": round(statistics.median(profile_alloc_latencies_us), 2),
            "median_depth": statistics.median(profile_depths),
            "median_nodes": int(statistics.median(profile_nodes)),
        }

    dataset = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary_by_profile,
        "raw_trials": all_results,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
        print(f"Results written to {output_path}")

    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Janus v0.35 Time Management Benchmark")
    parser.add_argument("--trials", type=int, default=3, help="Trials per position/profile")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "v0.35" / "benchmark_time_management.json",
        help="Destination JSON path",
    )
    args = parser.parse_args()

    pos_file = ROOT / "benchmarks" / "positions.json"
    raw_pos = json.loads(pos_file.read_text(encoding="utf-8"))
    # Select non-terminal active positions
    positions = [p for p in raw_pos if p.get("category") != "terminal"][:3]

    run_benchmark(positions, trials=args.trials, output_path=args.output)


if __name__ == "__main__":
    main()
