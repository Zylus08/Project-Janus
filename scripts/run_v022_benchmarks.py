"""Phase 7 Controlled Benchmark Suite for Milestone v0.22.

Evaluates four Static Exchange Evaluation (SEE) configurations across the
6-position standard benchmark suite:
- A: baseline (ordering=False, pruning=False)
- B: see_ordering_only (ordering=True, pruning=False)
- C: see_pruning_only (ordering=False, pruning=True)
- D: see_ordering_and_pruning (ordering=True, pruning=True)

Check extensions remain disabled (production default).
Depths: 3, 4, 5
Repetitions: 5 interleaved repetitions per configuration (20 runs per depth).
Reproducible schedule with fixed RNG seed (20261017).
Saves comprehensive metrics to analysis/v0.22/search_benchmarks.json.
"""
from __future__ import annotations

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


CONFIGS = {
    "baseline": {"enable_see_ordering": False, "enable_see_pruning": False},
    "see_ordering_only": {"enable_see_ordering": True, "enable_see_pruning": False},
    "see_pruning_only": {"enable_see_ordering": False, "enable_see_pruning": True},
    "see_ordering_and_pruning": {"enable_see_ordering": True, "enable_see_pruning": True},
}


def run_single_benchmark(
    positions: list[dict[str, Any]],
    depth: int,
    config_name: str,
) -> dict[str, Any]:
    cfg = CONFIGS[config_name]
    engine = JanusSearch(
        check_extension_policy="disabled",
        enable_history=True,
        enable_pvs=True,
        enable_aspiration=True,
        enable_lmr=True,
        enable_nmp=True,
        enable_see_ordering=cfg["enable_see_ordering"],
        enable_see_pruning=cfg["enable_see_pruning"],
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
            "see_evaluations": res.see_evaluations,
            "captures_ordered_see": res.captures_ordered_see,
            "qsearch_captures_considered": res.qsearch_captures_considered,
            "qsearch_captures_pruned": res.qsearch_captures_pruned,
            "qsearch_captures_exempted": res.qsearch_captures_exempted,
            "see_cache_hits": res.see_cache_hits,
        })
    total_elapsed = round(time.perf_counter() - t0, 6)
    total_nodes = sum(r["nodes"] for r in rows)
    return {
        "config": config_name,
        "depth": depth,
        "total_nodes": total_nodes,
        "total_elapsed": total_elapsed,
        "positions": rows,
    }


def main() -> int:
    positions_file = ROOT / "benchmarks" / "positions.json"
    positions = load_positions(positions_file)
    out_dir = ROOT / "analysis" / "v0.22"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "search_benchmarks.json"

    config_names = list(CONFIGS.keys())
    depths = [3, 4, 5]
    reps_per_config = 5
    seed = 20261017

    rng = random.Random(seed)
    depth_results: dict[str, Any] = {}

    print("=== Project Janus v0.22 Controlled SEE Benchmark ===")
    print(f"Configurations: {config_names}")
    print(f"Depths: {depths}, Repetitions: {reps_per_config} interleaved (seed={seed})")

    for d in depths:
        print(f"\n--- Running Depth {d} ---")
        runs_plan: list[str] = []
        for name in config_names:
            runs_plan.extend([name] * reps_per_config)
        rng.shuffle(runs_plan)

        config_runs: dict[str, list[dict[str, Any]]] = {name: [] for name in config_names}
        for run_idx, cfg_name in enumerate(runs_plan, 1):
            print(f"  [Depth {d} Run {run_idx:02d}/{len(runs_plan):02d}] Config: {cfg_name:<25}", end="", flush=True)
            res = run_single_benchmark(positions, d, cfg_name)
            config_runs[cfg_name].append(res)
            print(f" nodes={res['total_nodes']:<7} elapsed={res['total_elapsed']:.3f}s")

        # Aggregate metrics per config at depth d
        d_summary: dict[str, Any] = {}
        for cfg_name in config_names:
            runs = config_runs[cfg_name]
            times = [r["total_elapsed"] for r in runs]
            stats = calc_stats(times)
            # Node counts are deterministic across runs for fixed tree search
            rep0 = runs[0]
            pos_metrics: list[dict[str, Any]] = []
            for p_idx, p in enumerate(rep0["positions"]):
                pos_metrics.append({
                    "id": p["id"],
                    "category": p["category"],
                    "nodes": p["nodes"],
                    "completed_depth": p["completed_depth"],
                    "score": p["score"],
                    "best_move": p["best_move"],
                    "pv": p["pv"],
                    "pv_legal": p["pv_legal"],
                    "see_evaluations": p["see_evaluations"],
                    "captures_ordered_see": p["captures_ordered_see"],
                    "qsearch_captures_considered": p["qsearch_captures_considered"],
                    "qsearch_captures_pruned": p["qsearch_captures_pruned"],
                    "qsearch_captures_exempted": p["qsearch_captures_exempted"],
                    "see_cache_hits": p["see_cache_hits"],
                })

            total_see_evals = sum(p["see_evaluations"] for p in rep0["positions"])
            total_captures_ordered = sum(p["captures_ordered_see"] for p in rep0["positions"])
            total_q_considered = sum(p["qsearch_captures_considered"] for p in rep0["positions"])
            total_q_pruned = sum(p["qsearch_captures_pruned"] for p in rep0["positions"])
            total_q_exempted = sum(p["qsearch_captures_exempted"] for p in rep0["positions"])
            total_cache_hits = sum(p["see_cache_hits"] for p in rep0["positions"])

            d_summary[cfg_name] = {
                "total_nodes": rep0["total_nodes"],
                "timing_stats": stats,
                "raw_times": times,
                "positions": pos_metrics,
                "telemetry": {
                    "total_see_evaluations": total_see_evals,
                    "total_captures_ordered_see": total_captures_ordered,
                    "total_qsearch_captures_considered": total_q_considered,
                    "total_qsearch_captures_pruned": total_q_pruned,
                    "total_qsearch_captures_exempted": total_q_exempted,
                    "total_see_cache_hits": total_cache_hits,
                },
            }

        depth_results[f"depth_{d}"] = d_summary

    output_payload = {
        "metadata": {
            "engine": "Project Janus",
            "version": "0.22",
            "git_commit": git_commit(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "depths": depths,
            "repetitions_per_config": reps_per_config,
            "interleaving_seed": seed,
            "configs": CONFIGS,
            "check_extension_policy": "disabled",
            "scoring": "centipawns_from_side_to_move",
        },
        "depth_results": depth_results,
    }

    out_file.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    print(f"\nSaved benchmark results to {out_file}")

    # Print summary table
    print("\n=== Summary Table ===")
    print(f"{'Depth':<6} {'Config':<25} {'Nodes':<10} {'Node Delta':<12} {'Median Time':<12} {'Time Delta':<12} {'SEE Evals':<10} {'Q Pruned':<10}")
    print("-" * 105)
    for d in depths:
        d_key = f"depth_{d}"
        base_nodes = depth_results[d_key]["baseline"]["total_nodes"]
        base_med = depth_results[d_key]["baseline"]["timing_stats"]["median"]
        for cfg_name in config_names:
            c_data = depth_results[d_key][cfg_name]
            nodes = c_data["total_nodes"]
            med = c_data["timing_stats"]["median"]
            n_delta = f"{((nodes - base_nodes) / base_nodes) * 100:+.2f}%" if base_nodes else "0.00%"
            t_delta = f"{((med - base_med) / base_med) * 100:+.2f}%" if base_med else "0.00%"
            evals = c_data["telemetry"]["total_see_evaluations"]
            pruned = c_data["telemetry"]["total_qsearch_captures_pruned"]
            print(f"{d:<6} {cfg_name:<25} {nodes:<10} {n_delta:<12} {med:<10.3f}s {t_delta:<12} {evals:<10} {pruned:<10}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
