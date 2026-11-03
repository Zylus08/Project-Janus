"""Phase 2 & 5 Controlled Transposition Table Benchmark Harness for Milestone v0.23.

Evaluates three Transposition Table replacement policies across the
6-position standard benchmark suite:
1. always_replace (Current baseline)
2. depth_preferred (Protects deeper entries, exact upgrade, preserves best moves)
3. two_tier (Two-slot partitioned: deep tier + recent tier)

Depths: 3, 4, 5
Repetitions: 5 interleaved repetitions per policy (15 runs per depth, 45 runs total).
Reproducible schedule with fixed RNG seed (20261017).
SEE ordering and pruning: OFF for primary experiment.
Check extensions: disabled.
Cold-start: TT cleared before each position.
Saves metrics to analysis/v0.23/tt_benchmarks.json and analysis/v0.23/tt_benchmarks.csv.
"""
from __future__ import annotations

import csv
import json
import math
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_positions(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    v = board.copy()
    for m in pv:
        if m not in v.legal_moves:
            return False
        v.push(m)
    return True


def calc_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    mean = sum(s) / n
    variance = sum((x - mean) ** 2 for x in s) / n if n > 1 else 0.0
    stdev = math.sqrt(variance)
    median = s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0
    q1 = s[n // 4]
    q3 = s[(3 * n) // 4]
    iqr = q3 - q1
    return {
        "min": round(min(s), 6),
        "max": round(max(s), 6),
        "mean": round(mean, 6),
        "median": round(median, 6),
        "iqr": round(iqr, 6),
        "stdev": round(stdev, 6),
    }


POLICIES = ["always_replace", "depth_preferred", "two_tier"]


def run_single_benchmark(
    positions: list[dict[str, Any]],
    depth: int,
    policy: str,
) -> dict[str, Any]:
    engine = JanusSearch(
        check_extension_policy="disabled",
        enable_history=True,
        enable_pvs=True,
        enable_aspiration=True,
        enable_lmr=True,
        enable_nmp=True,
        enable_see_ordering=False,
        enable_see_pruning=False,
        tt_replacement_policy=policy,
    )
    rows: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for pos in positions:
        board = chess.Board(pos["fen"])
        engine.tt.clear()
        res = engine.search(board, max_depth=depth)
        best_uci = res.best_move.uci() if res.best_move else ""
        pv_uci = [m.uci() for m in res.pv]
        rows.append({
            "id": pos["id"],
            "category": pos["category"],
            "completed_depth": res.depth,
            "score": res.score,
            "best_move": best_uci,
            "pv": pv_uci,
            "pv_legal": validate_pv(board, res.pv),
            "nodes": res.nodes,
            "elapsed": round(res.elapsed, 6),
            "tt_replacement_policy": res.tt_replacement_policy,
            "tt_probes": res.tt_probes,
            "tt_hits": res.tt_hits,
            "tt_usable_hits": res.tt_usable_hits,
            "tt_cutoffs": res.tt_cutoffs,
            "tt_stores": res.tt_stores,
            "tt_same_key_updates": res.tt_same_key_updates,
            "tt_same_key_overwrites": res.tt_same_key_overwrites,
            "tt_same_key_rejected": res.tt_same_key_rejected,
            "tt_clears": res.tt_clears,
        })
    total_elapsed = round(time.perf_counter() - t0, 6)
    total_nodes = sum(r["nodes"] for r in rows)
    return {
        "policy": policy,
        "depth": depth,
        "total_nodes": total_nodes,
        "total_elapsed": total_elapsed,
        "positions": rows,
    }


def main() -> int:
    positions_file = ROOT / "benchmarks" / "positions.json"
    positions = load_positions(positions_file)
    out_dir = ROOT / "analysis" / "v0.23"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_out_file = out_dir / "tt_benchmarks.json"
    csv_out_file = out_dir / "tt_benchmarks.csv"

    depths = [3, 4, 5]
    reps_per_policy = 5
    seed = 20261017

    rng = random.Random(seed)
    depth_results: dict[str, Any] = {}
    all_flat_rows: list[dict[str, Any]] = []

    print("=== Project Janus v0.23 Controlled TT Replacement Policy Benchmark ===")
    print(f"Policies: {POLICIES}")
    print(f"Depths: {depths}, Repetitions: {reps_per_policy} interleaved (seed={seed})")

    for d in depths:
        print(f"\n--- Running Depth {d} ---")
        runs_plan: list[str] = []
        for name in POLICIES:
            runs_plan.extend([name] * reps_per_policy)
        rng.shuffle(runs_plan)

        policy_runs: dict[str, list[dict[str, Any]]] = {name: [] for name in POLICIES}
        for run_idx, pol_name in enumerate(runs_plan, 1):
            print(f"  [Depth {d} Run {run_idx:02d}/{len(runs_plan):02d}] Policy: {pol_name:<18}", end="", flush=True)
            res = run_single_benchmark(positions, d, pol_name)
            policy_runs[pol_name].append(res)
            print(f" nodes={res['total_nodes']:<7} elapsed={res['total_elapsed']:.3f}s")

        # Aggregate metrics per policy at depth d
        d_summary: dict[str, Any] = {}
        for pol_name in POLICIES:
            runs = policy_runs[pol_name]
            times = [r["total_elapsed"] for r in runs]
            stats = calc_stats(times)
            rep0 = runs[0]

            pos_metrics: list[dict[str, Any]] = []
            for p in rep0["positions"]:
                pos_metrics.append({
                    "id": p["id"],
                    "category": p["category"],
                    "nodes": p["nodes"],
                    "completed_depth": p["completed_depth"],
                    "score": p["score"],
                    "best_move": p["best_move"],
                    "pv": p["pv"],
                    "pv_legal": p["pv_legal"],
                    "tt_probes": p["tt_probes"],
                    "tt_hits": p["tt_hits"],
                    "tt_usable_hits": p["tt_usable_hits"],
                    "tt_cutoffs": p["tt_cutoffs"],
                    "tt_stores": p["tt_stores"],
                    "tt_same_key_updates": p["tt_same_key_updates"],
                    "tt_same_key_overwrites": p["tt_same_key_overwrites"],
                    "tt_same_key_rejected": p["tt_same_key_rejected"],
                    "tt_clears": p["tt_clears"],
                })
                all_flat_rows.append({
                    "requested_depth": d,
                    "policy": pol_name,
                    "position_id": p["id"],
                    "category": p["category"],
                    "nodes": p["nodes"],
                    "score": p["score"],
                    "best_move": p["best_move"],
                    "pv_legal": p["pv_legal"],
                    "tt_probes": p["tt_probes"],
                    "tt_hits": p["tt_hits"],
                    "tt_usable_hits": p["tt_usable_hits"],
                    "tt_cutoffs": p["tt_cutoffs"],
                    "tt_stores": p["tt_stores"],
                    "tt_same_key_updates": p["tt_same_key_updates"],
                    "tt_same_key_overwrites": p["tt_same_key_overwrites"],
                    "tt_same_key_rejected": p["tt_same_key_rejected"],
                    "tt_clears": p["tt_clears"],
                })

            total_probes = sum(p["tt_probes"] for p in rep0["positions"])
            total_hits = sum(p["tt_hits"] for p in rep0["positions"])
            total_usable = sum(p["tt_usable_hits"] for p in rep0["positions"])
            total_cutoffs = sum(p["tt_cutoffs"] for p in rep0["positions"])
            total_stores = sum(p["tt_stores"] for p in rep0["positions"])
            total_updates = sum(p["tt_same_key_updates"] for p in rep0["positions"])
            total_overwrites = sum(p["tt_same_key_overwrites"] for p in rep0["positions"])
            total_rejected = sum(p["tt_same_key_rejected"] for p in rep0["positions"])
            total_clears = sum(p["tt_clears"] for p in rep0["positions"])

            hit_rate = round(total_hits / total_probes * 100, 2) if total_probes > 0 else 0.0
            cutoff_rate = round(total_cutoffs / total_probes * 100, 2) if total_probes > 0 else 0.0

            d_summary[pol_name] = {
                "total_nodes": rep0["total_nodes"],
                "timing_stats": stats,
                "raw_times": times,
                "telemetry": {
                    "total_tt_probes": total_probes,
                    "total_tt_hits": total_hits,
                    "hit_rate_pct": hit_rate,
                    "total_tt_usable_hits": total_usable,
                    "total_tt_cutoffs": total_cutoffs,
                    "cutoff_rate_pct": cutoff_rate,
                    "total_tt_stores": total_stores,
                    "total_tt_same_key_updates": total_updates,
                    "total_tt_same_key_overwrites": total_overwrites,
                    "total_tt_same_key_rejected": total_rejected,
                    "total_tt_clears": total_clears,
                },
                "positions": pos_metrics,
            }

        depth_results[f"depth_{d}"] = d_summary

    output_payload = {
        "metadata": {
            "engine": "Project Janus",
            "version": "0.23",
            "git_commit": git_commit(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "depths": depths,
            "repetitions_per_policy": reps_per_policy,
            "interleaving_seed": seed,
            "policies": POLICIES,
            "check_extension_policy": "disabled",
            "see_ordering_enabled": False,
            "see_pruning_enabled": False,
            "tt_max_entries": 200_000,
            "tt_mode": "cold_start_cleared_before_each_position",
        },
        "depth_results": depth_results,
    }

    json_out_file.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    print(f"\nSaved benchmark results to {json_out_file}")

    if all_flat_rows:
        with csv_out_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_flat_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_flat_rows)
        print(f"Saved CSV results to {csv_out_file}")

    # Print summary table
    print("\n=== Summary Table ===")
    print(f"{'Depth':<6} {'Policy':<18} {'Nodes':<10} {'Node Delta':<12} {'Median Time':<12} {'Time Delta':<12} {'Probes':<10} {'Hits':<10} {'Cutoffs':<10} {'Cutoff %':<10} {'Rejects':<10}")
    print("-" * 120)
    for d in depths:
        d_key = f"depth_{d}"
        base_nodes = depth_results[d_key]["always_replace"]["total_nodes"]
        base_med = depth_results[d_key]["always_replace"]["timing_stats"]["median"]
        for pol_name in POLICIES:
            p_data = depth_results[d_key][pol_name]
            nodes = p_data["total_nodes"]
            med = p_data["timing_stats"]["median"]
            n_delta = f"{((nodes - base_nodes) / base_nodes) * 100:+.2f}%" if base_nodes else "0.00%"
            t_delta = f"{((med - base_med) / base_med) * 100:+.2f}%" if base_med else "0.00%"
            probes = p_data["telemetry"]["total_tt_probes"]
            hits = p_data["telemetry"]["total_tt_hits"]
            cutoffs = p_data["telemetry"]["total_tt_cutoffs"]
            cutoff_pct = f"{p_data['telemetry']['cutoff_rate_pct']:.2f}%"
            rejects = p_data["telemetry"]["total_tt_same_key_rejected"]
            print(f"{d:<6} {pol_name:<18} {nodes:<10} {n_delta:<12} {med:<10.3f}s {t_delta:<12} {probes:<10} {hits:<10} {cutoffs:<10} {cutoff_pct:<10} {rejects:<10}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
