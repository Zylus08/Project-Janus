"""Phase II: Controlled 4-arm factorial performance benchmark for Milestone v0.26.

Audits four factorial arms on 6 canonical standard positions:
- Arm A (Baseline): SEE ordering OFF, SEE pruning OFF
- Arm B (Ordering-only): SEE ordering ON, SEE pruning OFF
- Arm C (Pruning-only): SEE ordering OFF, SEE pruning ON
- Arm D (Combined): SEE ordering ON, SEE pruning ON

Evaluates depths 3, 4, and 5 with:
- 5 interleaved repetitions per arm and depth
- Rotated arm execution order between repetitions
- Detailed raw telemetry (nodes, time, score, best_move, pv, see_ordered, see_pruned, see_cache_hits)
- Factorial analysis of main effects and interaction effects (in nodes and runtime)
"""
from __future__ import annotations

import json
import math
import platform
import time
from pathlib import Path
from typing import Any
import chess

from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]
POSITIONS_FILE = ROOT / "benchmarks" / "positions.json"
OUT_RAW = ROOT / "analysis" / "v0.26" / "benchmarks" / "raw_factorial_benchmark.json"
OUT_SUMMARY = ROOT / "analysis" / "v0.26" / "benchmarks" / "summary_factorial_benchmark.json"

ARMS = [
    {"id": "Arm_A", "label": "Baseline", "ordering": False, "pruning": False},
    {"id": "Arm_B", "label": "Ordering-only", "ordering": True, "pruning": False},
    {"id": "Arm_C", "label": "Pruning-only", "ordering": False, "pruning": True},
    {"id": "Arm_D", "label": "Combined", "ordering": True, "pruning": True},
]

DEPTHS = [3, 4, 5]
REPETITIONS = 5


def percentile(data: list[float], p: float) -> float:
    """Compute percentile using linear interpolation."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def verify_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    b = board.copy()
    for m in pv:
        if not b.is_legal(m):
            return False
        b.push(m)
    return True


def run_benchmarks() -> dict[str, Any]:
    positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    raw_runs: list[dict[str, Any]] = []

    print("=" * 75)
    print("Project Janus v0.26 — Phase II Factorial Performance Benchmark")
    print(f"Arms: {len(ARMS)} | Depths: {DEPTHS} | Repetitions: {REPETITIONS} (Interleaved & Rotated)")
    print(f"Positions: {len(positions)} canonical positions from benchmarks/positions.json")
    print("=" * 75)

    total_runs = len(DEPTHS) * REPETITIONS * len(ARMS) * len(positions)
    run_counter = 0

    bench_start = time.monotonic()

    for depth in DEPTHS:
        print(f"\n>>> Running Depth {depth} across {REPETITIONS} interleaved repetitions...")
        for rep in range(1, REPETITIONS + 1):
            # Rotated arm order to prevent thermal / cache drift
            shift = (rep - 1) % len(ARMS)
            rotated_arms = ARMS[shift:] + ARMS[:shift]
            arm_order_str = ", ".join(a["id"] for a in rotated_arms)
            print(f"  Repetition {rep}/{REPETITIONS} (Arm order: {arm_order_str})")

            for arm in rotated_arms:
                arm_id = arm["id"]
                for pos in positions:
                    run_counter += 1
                    pos_id = pos["id"]
                    fen = pos["fen"]
                    board = chess.Board(fen)

                    engine = JanusSearch(
                        enable_see_ordering=arm["ordering"],
                        enable_see_pruning=arm["pruning"],
                    )

                    t0 = time.perf_counter()
                    res = engine.search(board, max_depth=depth)
                    elapsed = time.perf_counter() - t0

                    pv_valid = verify_pv(board, res.pv)
                    best_move_str = res.best_move.uci() if res.best_move else None

                    raw_runs.append({
                        "run_id": run_counter,
                        "depth": depth,
                        "repetition": rep,
                        "arm": arm_id,
                        "arm_label": arm["label"],
                        "ordering": arm["ordering"],
                        "pruning": arm["pruning"],
                        "position_id": pos_id,
                        "nodes": res.nodes,
                        "elapsed_s": round(elapsed, 6),
                        "score": res.score,
                        "best_move": best_move_str,
                        "pv": [m.uci() for m in res.pv],
                        "pv_valid": pv_valid,
                        "see_ordered": engine.captures_ordered_see,
                        "see_pruned": engine.qsearch_captures_pruned,
                        "see_cache_hits": engine.see_cache_hits,
                    })

    bench_duration = time.monotonic() - bench_start
    print(f"\nAll {total_runs} benchmark runs completed in {bench_duration:.2f}s.")

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with OUT_RAW.open("w", encoding="utf-8") as f:
        json.dump(raw_runs, f, indent=2)

    # -------------------------------------------------------------------------
    # Statistical Summarization & Factorial Effects Analysis
    # -------------------------------------------------------------------------
    summary: dict[str, Any] = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "depths": DEPTHS,
            "repetitions": REPETITIONS,
            "arms": {a["id"]: a for a in ARMS},
            "positions": [p["id"] for p in positions],
            "total_benchmark_time_s": round(bench_duration, 2),
        },
        "by_depth": {},
    }

    for depth in DEPTHS:
        depth_runs = [r for r in raw_runs if r["depth"] == depth]
        depth_summary: dict[str, Any] = {
            "per_arm": {},
            "per_position_per_arm": {},
            "factorial_effects": {},
        }

        # Aggregate per arm across all positions and reps
        for arm in ARMS:
            a_id = arm["id"]
            a_runs = [r for r in depth_runs if r["arm"] == a_id]

            # Sum of nodes per repetition across all 6 positions
            reps_nodes: list[int] = []
            reps_times: list[float] = []
            reps_ordered: list[int] = []
            reps_pruned: list[int] = []
            reps_cache: list[int] = []

            for rep in range(1, REPETITIONS + 1):
                rep_r = [r for r in a_runs if r["repetition"] == rep]
                reps_nodes.append(sum(r["nodes"] for r in rep_r))
                reps_times.append(sum(r["elapsed_s"] for r in rep_r))
                reps_ordered.append(sum(r["see_ordered"] for r in rep_r))
                reps_pruned.append(sum(r["see_pruned"] for r in rep_r))
                reps_cache.append(sum(r["see_cache_hits"] for r in rep_r))

            med_time = percentile(reps_times, 0.50)
            q25_time = percentile(reps_times, 0.25)
            q75_time = percentile(reps_times, 0.75)
            iqr_time = q75_time - q25_time

            med_nodes = percentile(reps_nodes, 0.50)
            q25_nodes = percentile(reps_nodes, 0.25)
            q75_nodes = percentile(reps_nodes, 0.75)
            iqr_nodes = q75_nodes - q25_nodes

            depth_summary["per_arm"][a_id] = {
                "label": arm["label"],
                "median_total_nodes": round(med_nodes, 1),
                "iqr_total_nodes": round(iqr_nodes, 1),
                "mean_total_nodes": round(sum(reps_nodes) / len(reps_nodes), 1),
                "median_total_time_s": round(med_time, 5),
                "iqr_total_time_s": round(iqr_time, 5),
                "mean_total_time_s": round(sum(reps_times) / len(reps_times), 5),
                "mean_see_ordered": round(sum(reps_ordered) / len(reps_ordered), 1),
                "mean_see_pruned": round(sum(reps_pruned) / len(reps_pruned), 1),
                "mean_see_cache_hits": round(sum(reps_cache) / len(reps_cache), 1),
            }

        # Baseline values (Arm A)
        base_nodes = depth_summary["per_arm"]["Arm_A"]["median_total_nodes"]
        base_time = depth_summary["per_arm"]["Arm_A"]["median_total_time_s"]

        for arm in ARMS:
            a_id = arm["id"]
            m_nodes = depth_summary["per_arm"][a_id]["median_total_nodes"]
            m_time = depth_summary["per_arm"][a_id]["median_total_time_s"]
            node_pct_change = round(100.0 * (m_nodes - base_nodes) / base_nodes, 2)
            time_pct_change = round(100.0 * (m_time - base_time) / base_time, 2)
            depth_summary["per_arm"][a_id]["node_change_pct_vs_baseline"] = node_pct_change
            depth_summary["per_arm"][a_id]["time_change_pct_vs_baseline"] = time_pct_change

        # ---------------------------------------------------------------------
        # Factorial Main Effects and Interaction
        # ---------------------------------------------------------------------
        # Arm A = Baseline (0, 0)
        # Arm B = Ordering-only (1, 0)
        # Arm C = Pruning-only (0, 1)
        # Arm D = Combined (1, 1)
        nodes_A = depth_summary["per_arm"]["Arm_A"]["median_total_nodes"]
        nodes_B = depth_summary["per_arm"]["Arm_B"]["median_total_nodes"]
        nodes_C = depth_summary["per_arm"]["Arm_C"]["median_total_nodes"]
        nodes_D = depth_summary["per_arm"]["Arm_D"]["median_total_nodes"]

        time_A = depth_summary["per_arm"]["Arm_A"]["median_total_time_s"]
        time_B = depth_summary["per_arm"]["Arm_B"]["median_total_time_s"]
        time_C = depth_summary["per_arm"]["Arm_C"]["median_total_time_s"]
        time_D = depth_summary["per_arm"]["Arm_D"]["median_total_time_s"]

        # Ordering effect w/ pruning OFF: B - A
        ord_off_nodes = nodes_B - nodes_A
        ord_off_time = time_B - time_A
        # Ordering effect w/ pruning ON: D - C
        ord_on_nodes = nodes_D - nodes_C
        ord_on_time = time_D - time_C
        # Pruning effect w/ ordering OFF: C - A
        prun_off_nodes = nodes_C - nodes_A
        prun_off_time = time_C - time_A
        # Pruning effect w/ ordering ON: D - B
        prun_on_nodes = nodes_D - nodes_B
        prun_on_time = time_D - time_B
        # Combined effect: D - A
        comb_nodes = nodes_D - nodes_A
        comb_time = time_D - time_A
        # Interaction: D - B - C + A
        inter_nodes = (nodes_D - nodes_A) - ((nodes_B - nodes_A) + (nodes_C - nodes_A))
        inter_time = (time_D - time_A) - ((time_B - time_A) + (time_C - time_A))

        depth_summary["factorial_effects"] = {
            "ordering_effect_pruning_off": {
                "nodes": round(ord_off_nodes, 1),
                "nodes_pct": round(100.0 * ord_off_nodes / nodes_A, 2),
                "time_s": round(ord_off_time, 5),
                "time_pct": round(100.0 * ord_off_time / time_A, 2),
            },
            "ordering_effect_pruning_on": {
                "nodes": round(ord_on_nodes, 1),
                "nodes_pct": round(100.0 * ord_on_nodes / nodes_C, 2),
                "time_s": round(ord_on_time, 5),
                "time_pct": round(100.0 * ord_on_time / time_C, 2),
            },
            "pruning_effect_ordering_off": {
                "nodes": round(prun_off_nodes, 1),
                "nodes_pct": round(100.0 * prun_off_nodes / nodes_A, 2),
                "time_s": round(prun_off_time, 5),
                "time_pct": round(100.0 * prun_off_time / time_A, 2),
            },
            "pruning_effect_ordering_on": {
                "nodes": round(prun_on_nodes, 1),
                "nodes_pct": round(100.0 * prun_on_nodes / nodes_B, 2),
                "time_s": round(prun_on_time, 5),
                "time_pct": round(100.0 * prun_on_time / time_B, 2),
            },
            "combined_effect": {
                "nodes": round(comb_nodes, 1),
                "nodes_pct": round(100.0 * comb_nodes / nodes_A, 2),
                "time_s": round(comb_time, 5),
                "time_pct": round(100.0 * comb_time / time_A, 2),
            },
            "interaction_effect": {
                "nodes": round(inter_nodes, 1),
                "nodes_pct_of_baseline": round(100.0 * inter_nodes / nodes_A, 2),
                "time_s": round(inter_time, 5),
                "time_pct_of_baseline": round(100.0 * inter_time / time_A, 2),
            },
        }

        # Per position breakdown
        for pos in positions:
            p_id = pos["id"]
            p_runs = [r for r in depth_runs if r["position_id"] == p_id]
            depth_summary["per_position_per_arm"][p_id] = {}
            for arm in ARMS:
                a_id = arm["id"]
                ap_runs = [r for r in p_runs if r["arm"] == a_id]
                times = [r["elapsed_s"] for r in ap_runs]
                nodes = [r["nodes"] for r in ap_runs]
                ordered = [r["see_ordered"] for r in ap_runs]
                pruned = [r["see_pruned"] for r in ap_runs]
                cache = [r["see_cache_hits"] for r in ap_runs]
                depth_summary["per_position_per_arm"][p_id][a_id] = {
                    "median_nodes": round(percentile(nodes, 0.50), 1),
                    "median_time_s": round(percentile(times, 0.50), 5),
                    "best_move": ap_runs[0]["best_move"],
                    "score": ap_runs[0]["score"],
                    "mean_see_ordered": round(sum(ordered) / len(ordered), 1),
                    "mean_see_pruned": round(sum(pruned) / len(pruned), 1),
                    "mean_see_cache_hits": round(sum(cache) / len(cache), 1),
                }

        summary["by_depth"][str(depth)] = depth_summary

    with OUT_SUMMARY.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 75)
    print("PHASE II FACTORIAL BENCHMARK SUMMARY TABLE:")
    print("=" * 75)
    for depth in DEPTHS:
        print(f"\n--- Depth {depth} ---")
        ds = summary["by_depth"][str(depth)]
        print(f"{'Arm':<18} | {'Median Nodes':<12} | {'Node Delta %':<12} | {'Median Time (s)':<16} | {'Time Delta %':<12} | {'SEE Ordered':<11} | {'SEE Pruned':<10}")
        print("-" * 105)
        for arm in ARMS:
            a_id = arm["id"]
            pa = ds["per_arm"][a_id]
            print(f"{arm['label']:<18} | {pa['median_total_nodes']:<12.1f} | {pa['node_change_pct_vs_baseline']:>+10.2f}% | {pa['median_total_time_s']:<16.5f} | {pa['time_change_pct_vs_baseline']:>+10.2f}% | {pa['mean_see_ordered']:<11.1f} | {pa['mean_see_pruned']:<10.1f}")

        fe = ds["factorial_effects"]
        print("\nFactorial Decomposition:")
        print(f"  Ordering Effect (Pruning OFF): {fe['ordering_effect_pruning_off']['nodes_pct']:>+6.2f}% nodes, {fe['ordering_effect_pruning_off']['time_pct']:>+6.2f}% time")
        print(f"  Ordering Effect (Pruning ON) : {fe['ordering_effect_pruning_on']['nodes_pct']:>+6.2f}% nodes, {fe['ordering_effect_pruning_on']['time_pct']:>+6.2f}% time")
        print(f"  Pruning Effect (Ordering OFF): {fe['pruning_effect_ordering_off']['nodes_pct']:>+6.2f}% nodes, {fe['pruning_effect_ordering_off']['time_pct']:>+6.2f}% time")
        print(f"  Pruning Effect (Ordering ON) : {fe['pruning_effect_ordering_on']['nodes_pct']:>+6.2f}% nodes, {fe['pruning_effect_ordering_on']['time_pct']:>+6.2f}% time")
        print(f"  Combined Effect (D vs A)     : {fe['combined_effect']['nodes_pct']:>+6.2f}% nodes, {fe['combined_effect']['time_pct']:>+6.2f}% time")
        print(f"  Interaction Effect           : {fe['interaction_effect']['nodes_pct_of_baseline']:>+6.2f}% nodes, {fe['interaction_effect']['time_pct_of_baseline']:>+6.2f}% time")

    print("\nSummary written to: " + str(OUT_SUMMARY))
    print("=" * 75)
    return summary


if __name__ == "__main__":
    run_benchmarks()
