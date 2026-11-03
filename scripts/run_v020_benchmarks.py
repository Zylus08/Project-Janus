"""Controlled paired benchmark runner for Milestone v0.20: Check Extensions.

Compares:
- Baseline: LMR on, NMP on, check extensions off.
- Candidate: LMR on, NMP on, check extensions on.

Across the 6 standard benchmark positions at depths 3, 4, 5 with 5 interleaved paired repetitions.
Also includes a 4-way ablation of LMR/NMP with and without check extensions at depth 4.
Outputs results to analysis/v0.20/search_benchmarks.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any
import chess

from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]
POSITIONS_PATH = ROOT / "benchmarks" / "positions.json"
OUT_FILE = ROOT / "analysis" / "v0.20" / "search_benchmarks.json"


def compute_stats(values: list[float]) -> dict[str, float]:
    n = len(values)
    if not values:
        return {}
    mean_val = sum(values) / n
    sorted_v = sorted(values)
    min_val = sorted_v[0]
    max_val = sorted_v[-1]
    if n % 2 == 1:
        med = sorted_v[n // 2]
    else:
        med = (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0
    q1 = sorted_v[1] if n == 5 else sorted_v[n // 4]
    q3 = sorted_v[3] if n == 5 else sorted_v[(3 * n) // 4]
    iqr = round(q3 - q1, 6)
    variance = sum((x - mean_val) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
    stdev = round(variance ** 0.5, 6)
    return {
        "median": round(med, 4),
        "mean": round(mean_val, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "iqr": iqr,
        "stdev": stdev,
    }


def validate_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    v = board.copy()
    for m in pv:
        if m not in v.legal_moves:
            return False
        v.push(m)
    return True


def run_benchmark_pass(
    positions: list[dict[str, Any]],
    depth: int,
    enable_check_extensions: bool,
    enable_lmr: bool = True,
    enable_nmp: bool = True,
) -> dict[str, Any]:
    engine = JanusSearch(
        enable_lmr=enable_lmr,
        enable_nmp=enable_nmp,
        enable_check_extensions=enable_check_extensions,
    )
    total_nodes = 0
    total_time = 0.0
    telemetry_totals = {
        "check_extensions_eligible": 0,
        "check_extensions_applied": 0,
        "check_extension_plies": 0,
        "check_extensions_suppressed": 0,
        "check_extensions_terminal_mates": 0,
        "nmp_considered": 0,
        "nmp_attempts": 0,
        "nmp_fail_highs": 0,
        "nmp_fail_lows": 0,
        "nmp_verifications": 0,
        "nmp_verification_failures": 0,
        "nmp_cutoffs": 0,
        "lmr_considered": 0,
        "lmr_reduced_searches": 0,
        "lmr_reduced_plies": 0,
        "lmr_researches": 0,
        "lmr_fail_lows": 0,
        "lmr_fail_highs": 0,
        "lmr_cutoffs": 0,
        "scout_searches": 0,
        "scout_fail_highs": 0,
        "researches": 0,
        "beta_cutoffs": 0,
        "aspiration_iterations": 0,
        "aspiration_fail_lows": 0,
        "aspiration_fail_highs": 0,
        "aspiration_researches": 0,
        "aspiration_fallbacks": 0,
    }

    per_pos = []

    for p in positions:
        board = chess.Board(p["fen"])
        engine.tt.clear()
        t0 = time.perf_counter()
        res = engine.search(board, max_depth=depth)
        elapsed = time.perf_counter() - t0

        total_nodes += res.nodes
        total_time += elapsed

        for k in telemetry_totals:
            telemetry_totals[k] += getattr(res, k, 0)

        pv_valid = validate_pv(board, res.pv)
        per_pos.append({
            "id": p["id"],
            "category": p["category"],
            "fen": p["fen"],
            "depth": depth,
            "nodes": res.nodes,
            "score": res.score,
            "best_move": res.best_move.uci() if res.best_move else None,
            "pv": [m.uci() for m in res.pv],
            "pv_valid": pv_valid,
            "elapsed": round(elapsed, 4),
            "telemetry": {k: getattr(res, k, 0) for k in telemetry_totals},
        })

    return {
        "total_nodes": total_nodes,
        "total_time": round(total_time, 4),
        "telemetry_totals": telemetry_totals,
        "positions": per_pos,
    }


def main():
    print("Loading benchmark positions...")
    positions = json.loads(POSITIONS_PATH.read_text(encoding="utf-8"))
    depths = [3, 4, 5]
    repetitions = 5

    results: dict[str, Any] = {
        "metadata": {
            "title": "Project Janus v0.20 Controlled Benchmark: Check Extensions",
            "date": time.strftime("%Y-%m-%d"),
            "base_commit": "8936c7559aad8b4a5233ba9437505c56062045c1",
            "positions_count": len(positions),
            "depths": depths,
            "repetitions": repetitions,
            "methodology": "Paired interleaved execution with strictly alternating order",
        },
        "paired_benchmarks": {},
        "ablation_depth_4": {},
    }

    for depth in depths:
        print(f"\n--- Running Depth {depth} Paired Benchmark ({repetitions} interleaved reps) ---")
        base_runs = []
        cand_runs = []
        base_times = []
        cand_times = []

        for rep in range(repetitions):
            # Alternating execution order
            if rep % 2 == 0:
                print(f"  Rep {rep+1}: Baseline -> Candidate")
                b_run = run_benchmark_pass(positions, depth, enable_check_extensions=False)
                c_run = run_benchmark_pass(positions, depth, enable_check_extensions=True)
            else:
                print(f"  Rep {rep+1}: Candidate -> Baseline")
                c_run = run_benchmark_pass(positions, depth, enable_check_extensions=True)
                b_run = run_benchmark_pass(positions, depth, enable_check_extensions=False)

            base_runs.append(b_run)
            cand_runs.append(c_run)
            base_times.append(b_run["total_time"])
            cand_times.append(c_run["total_time"])

        base_nodes = base_runs[0]["total_nodes"]
        cand_nodes = cand_runs[0]["total_nodes"]
        node_delta = cand_nodes - base_nodes
        node_pct = round((node_delta / base_nodes) * 100, 2) if base_nodes > 0 else 0.0

        base_stats = compute_stats(base_times)
        cand_stats = compute_stats(cand_times)
        time_delta = round(cand_stats["median"] - base_stats["median"], 4)
        time_pct = round((time_delta / base_stats["median"]) * 100, 2) if base_stats["median"] > 0 else 0.0

        # Detailed per-position comparison from the first rep
        per_pos_comparison = []
        for b_pos, c_pos in zip(base_runs[0]["positions"], cand_runs[0]["positions"]):
            pos_node_delta = c_pos["nodes"] - b_pos["nodes"]
            pos_node_pct = round((pos_node_delta / b_pos["nodes"]) * 100, 2) if b_pos["nodes"] > 0 else 0.0
            per_pos_comparison.append({
                "id": b_pos["id"],
                "category": b_pos["category"],
                "fen": b_pos["fen"],
                "depth": depth,
                "baseline_nodes": b_pos["nodes"],
                "candidate_nodes": c_pos["nodes"],
                "node_delta": pos_node_delta,
                "node_percentage_delta": pos_node_pct,
                "baseline_score": b_pos["score"],
                "candidate_score": c_pos["score"],
                "baseline_best_move": b_pos["best_move"],
                "candidate_best_move": c_pos["best_move"],
                "baseline_pv": b_pos["pv"],
                "candidate_pv": c_pos["pv"],
                "pv_valid": c_pos["pv_valid"],
                "candidate_telemetry": c_pos["telemetry"],
            })

        results["paired_benchmarks"][f"depth_{depth}"] = {
            "depth": depth,
            "baseline_nodes": base_nodes,
            "candidate_nodes": cand_nodes,
            "node_delta": node_delta,
            "node_percentage_delta": node_pct,
            "baseline_time_stats": base_stats,
            "candidate_time_stats": cand_stats,
            "median_time_delta_seconds": time_delta,
            "median_time_percentage_delta": time_pct,
            "candidate_totals": cand_runs[0]["telemetry_totals"],
            "per_position": per_pos_comparison,
            "raw_runs": {
                "baseline_times": base_times,
                "candidate_times": cand_times,
            },
        }

        print(f"  Depth {depth} summary: Nodes {base_nodes:,} -> {cand_nodes:,} ({node_pct:+0.2f}%)")
        print(f"  Depth {depth} time: {base_stats['median']:.3f}s -> {cand_stats['median']:.3f}s ({time_pct:+0.2f}%)")

    # Ablation across 4 LMR/NMP configurations with check extensions on/off at depth 4
    print("\n--- Running Depth 4 Ablation Suite (4 LMR/NMP configs x check extensions on/off) ---")
    ablation_configs = [
        ("pure_pvs", False, False),
        ("lmr_only", True, False),
        ("nmp_only", False, True),
        ("lmr_and_nmp", True, True),
    ]

    for cfg_name, lmr, nmp in ablation_configs:
        off_run = run_benchmark_pass(positions, 4, enable_check_extensions=False, enable_lmr=lmr, enable_nmp=nmp)
        on_run = run_benchmark_pass(positions, 4, enable_check_extensions=True, enable_lmr=lmr, enable_nmp=nmp)
        n_delta = on_run["total_nodes"] - off_run["total_nodes"]
        n_pct = round((n_delta / off_run["total_nodes"]) * 100, 2)
        results["ablation_depth_4"][cfg_name] = {
            "enable_lmr": lmr,
            "enable_nmp": nmp,
            "check_ext_off_nodes": off_run["total_nodes"],
            "check_ext_on_nodes": on_run["total_nodes"],
            "node_delta": n_delta,
            "node_percentage_delta": n_pct,
            "check_ext_off_time": off_run["total_time"],
            "check_ext_on_time": on_run["total_time"],
            "check_extensions_applied": on_run["telemetry_totals"]["check_extensions_applied"],
        }
        print(f"  {cfg_name:<12}: Ext OFF={off_run['total_nodes']:,} -> Ext ON={on_run['total_nodes']:,} ({n_pct:+0.2f}%) [applied: {on_run['telemetry_totals']['check_extensions_applied']}]")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nAll benchmark results saved to {OUT_FILE}")


if __name__ == "__main__":
    main()
