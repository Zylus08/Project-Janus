"""Milestone v0.24 Phase 2: Transposition Table Capacity Stress Testing.

Evaluates TT replacement policies (always_replace, depth_preferred, two_tier)
under 3 capacity budgets:
- Small: 1,000 entries
- Medium: 5,000 entries
- Standard: 200,000 entries

Across the 6 standard benchmark positions at depth 5 with 3 interleaved repetitions.
Also includes a cumulative multi-position test to stress capacity limits without clearing.
Saves machine-readable results to analysis/v0.24/tt_capacity/tt_capacity_results.json and .csv.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import sys
import time

import chess

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch


def load_positions(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    b = board.copy()
    for m in pv:
        if m not in b.legal_moves:
            return False
        b.push(m)
    return True


def main():
    positions = load_positions(ROOT / "benchmarks" / "positions.json")
    out_dir = ROOT / "analysis" / "v0.24" / "tt_capacity"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "tt_capacity_results.json"
    csv_path = out_dir / "tt_capacity_results.csv"

    capacities = {
        "small": 1_000,
        "medium": 5_000,
        "standard": 200_000,
    }
    policies = ["always_replace", "depth_preferred", "two_tier"]
    reps = 3
    depth = 5
    rng = random.Random(20261017)

    print("=== Phase 2: TT Capacity Stress Testing ===")
    print(f"Capacities: {capacities}")
    print(f"Policies: {policies}")
    print(f"Depth: {depth}, Repetitions: {reps}\n")

    all_results = {}
    csv_rows = []

    for cap_name, cap_size in capacities.items():
        print(f"\n--- Testing Capacity: {cap_name.upper()} ({cap_size:,} entries) ---")
        cap_results = {}

        # Plan interleaved runs
        runs_plan = []
        for pol in policies:
            runs_plan.extend([pol] * reps)
        rng.shuffle(runs_plan)

        policy_runs = {p: [] for p in policies}

        for run_idx, pol in enumerate(runs_plan, 1):
            engine = JanusSearch(
                tt_max_entries=cap_size,
                tt_replacement_policy=pol,
                enable_see_ordering=False,
                enable_see_pruning=False,
                check_extension_policy="disabled",
            )
            t0 = time.perf_counter()
            tot_nodes = 0
            pos_results = []

            for pos in positions:
                engine.tt.clear()
                board = chess.Board(pos["fen"])
                res = engine.search(board, max_depth=depth)
                tot_nodes += res.nodes
                pv_ok = verify_pv(board, res.pv)
                pos_results.append({
                    "id": pos["id"],
                    "nodes": res.nodes,
                    "score": res.score,
                    "best_move": res.best_move.uci() if res.best_move else None,
                    "pv_legal": pv_ok,
                    "tt_probes": res.tt_probes,
                    "tt_hits": res.tt_hits,
                    "tt_usable_hits": res.tt_usable_hits,
                    "tt_cutoffs": res.tt_cutoffs,
                    "tt_stores": res.tt_stores,
                    "tt_same_key_updates": res.tt_same_key_updates,
                    "tt_same_key_overwrites": res.tt_same_key_overwrites,
                    "tt_same_key_rejected": res.tt_same_key_rejected,
                    "tt_clears": res.tt_clears,
                    "retained_entries": len(engine.tt) + len(engine.tt_recent),
                })
            elapsed = time.perf_counter() - t0
            run_data = {
                "nodes": tot_nodes,
                "elapsed": elapsed,
                "positions": pos_results,
            }
            policy_runs[pol].append(run_data)
            print(f"  [{cap_name:<8} Run {run_idx:02d}/{len(runs_plan):02d}] {pol:<16} nodes={tot_nodes:<6} elapsed={elapsed:.3f}s")

        # Summarize across repetitions
        for pol in policies:
            runs = policy_runs[pol]
            times = sorted(r["elapsed"] for r in runs)
            med_time = times[len(times) // 2]
            p0 = runs[0]["positions"]
            tot_nodes = runs[0]["nodes"]
            tot_probes = sum(p["tt_probes"] for p in p0)
            tot_hits = sum(p["tt_hits"] for p in p0)
            tot_usable = sum(p["tt_usable_hits"] for p in p0)
            tot_cutoffs = sum(p["tt_cutoffs"] for p in p0)
            tot_stores = sum(p["tt_stores"] for p in p0)
            tot_same_key = sum(p["tt_same_key_updates"] for p in p0)
            tot_overwrites = sum(p["tt_same_key_overwrites"] for p in p0)
            tot_rejected = sum(p["tt_same_key_rejected"] for p in p0)
            tot_clears = sum(p["tt_clears"] for p in p0)
            max_retained = max(p["retained_entries"] for p in p0)

            hit_rate = round(100 * tot_hits / tot_probes, 2) if tot_probes else 0.0
            cutoff_rate = round(100 * tot_cutoffs / tot_probes, 2) if tot_probes else 0.0

            summary = {
                "capacity": cap_size,
                "policy": pol,
                "total_nodes": tot_nodes,
                "median_elapsed": round(med_time, 4),
                "min_elapsed": round(times[0], 4),
                "max_elapsed": round(times[-1], 4),
                "tt_probes": tot_probes,
                "tt_hits": tot_hits,
                "hit_rate_pct": hit_rate,
                "tt_usable_hits": tot_usable,
                "tt_cutoffs": tot_cutoffs,
                "cutoff_rate_pct": cutoff_rate,
                "tt_stores": tot_stores,
                "tt_same_key_updates": tot_same_key,
                "tt_same_key_overwrites": tot_overwrites,
                "tt_same_key_rejected": tot_rejected,
                "tt_clears": tot_clears,
                "max_retained_entries": max_retained,
            }
            cap_results[pol] = {
                "summary": summary,
                "positions": p0,
            }
            csv_rows.append(summary)

        all_results[cap_name] = cap_results

    # Continuous accumulation test (no clears between positions)
    print("\n--- Testing Cumulative Multi-Position Stress Test ---")
    cum_results = {}
    for cap_name, cap_size in [("small", 1_000), ("medium", 5_000)]:
        cum_results[cap_name] = {}
        for pol in policies:
            engine = JanusSearch(
                tt_max_entries=cap_size,
                tt_replacement_policy=pol,
                enable_see_ordering=False,
                enable_see_pruning=False,
                check_extension_policy="disabled",
            )
            # Do NOT clear TT between positions
            t0 = time.perf_counter()
            tot_nodes = 0
            for pos in positions:
                board = chess.Board(pos["fen"])
                res = engine.search(board, max_depth=depth)
                tot_nodes += res.nodes
            elapsed = time.perf_counter() - t0
            retained = len(engine.tt) + len(engine.tt_recent)
            cum_summary = {
                "capacity": cap_size,
                "policy": pol,
                "cumulative_nodes": tot_nodes,
                "elapsed": round(elapsed, 4),
                "final_retained_entries": retained,
                "total_clears": engine.tt_clears,
                "total_same_key_updates": engine.tt_same_key_updates,
                "total_same_key_overwrites": engine.tt_same_key_overwrites,
                "total_same_key_rejected": engine.tt_same_key_rejected,
            }
            cum_results[cap_name][pol] = cum_summary
            print(f"  [Cumulative {cap_name:<6}] {pol:<16} nodes={tot_nodes:<6} clears={engine.tt_clears:<3} retained={retained:<5} elapsed={elapsed:.3f}s")

    all_results["cumulative_stress"] = cum_results

    # Write JSON and CSV
    json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nSaved capacity stress results to {json_path} and {csv_path}")


if __name__ == "__main__":
    main()
