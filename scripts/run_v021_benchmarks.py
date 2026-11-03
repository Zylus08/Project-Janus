"""Phase 5 Controlled Benchmark Suite for Milestone v0.21.

Evaluates three check extension policies across the 6-position standard benchmark suite:
- disabled
- bounded_all_checks
- single_reply

Depths: 3, 4, 5
Repetitions: 5 interleaved repetitions per policy (15 runs per depth).
Reproducible schedule with fixed RNG seed.
Saves comprehensive metrics to analysis/v0.21/search_benchmarks.json.
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


def run_single_benchmark(
    positions: list[dict[str, Any]],
    depth: int,
    policy: str,
) -> dict[str, Any]:
    engine = JanusSearch(
        check_extension_policy=policy,
        enable_history=True,
        enable_pvs=True,
        enable_aspiration=True,
        enable_lmr=True,
        enable_nmp=True,
        max_check_extensions=2,
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
            "check_extensions_eligible": res.check_extensions_eligible,
            "check_extensions_applied": res.check_extensions_applied,
            "check_extension_plies": res.check_extension_plies,
            "check_extensions_suppressed": res.check_extensions_suppressed,
            "check_extensions_multiple_replies": res.check_extensions_multiple_replies,
            "check_extensions_terminal_mates": res.check_extensions_terminal_mates,
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
    out_dir = ROOT / "analysis" / "v0.21"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "search_benchmarks.json"

    policies = ["disabled", "bounded_all_checks", "single_reply"]
    depths = [3, 4, 5]
    reps_per_policy = 5
    seed = 20261016

    # Generate reproducible interleaved schedule
    rng = random.Random(seed)
    depth_results: dict[str, Any] = {}

    print(f"=== Project Janus v0.21 Controlled Benchmark ===")
    print(f"Policies: {policies}")
    print(f"Depths: {depths}, Repetitions: {reps_per_policy} interleaved (seed={seed})")

    for d in depths:
        print(f"\n--- Running Depth {d} ---")
        # Build balanced sequence of runs
        runs_plan: list[str] = []
        for _ in range(reps_per_policy):
            cycle = list(policies)
            rng.shuffle(cycle)
            runs_plan.extend(cycle)

        policy_runs: dict[str, list[dict[str, Any]]] = {p: [] for p in policies}

        for idx, policy in enumerate(runs_plan):
            run_data = run_single_benchmark(positions, d, policy)
            policy_runs[policy].append(run_data)
            print(
                f"  [{idx+1:02d}/{len(runs_plan):02d}] Depth {d} | Policy: {policy:<18} | "
                f"Nodes: {run_data['total_nodes']:<7} | Time: {run_data['total_elapsed']:.3f}s"
            )

        # Aggregate stats per policy
        policy_aggregates: dict[str, Any] = {}
        for p in policies:
            runs = policy_runs[p]
            wall_times = [r["total_elapsed"] for r in runs]
            node_counts = [r["total_nodes"] for r in runs]
            # Since search is deterministic, node counts should be invariant across runs
            node_count = node_counts[0]
            assert all(n == node_count for n in node_counts), f"Non-deterministic node counts for {p} at depth {d}: {node_counts}"

            # Grab per-position baseline details from first run
            first_run = runs[0]
            per_pos = {
                r["id"]: {
                    "nodes": r["nodes"],
                    "score": r["score"],
                    "best_move": r["best_move"],
                    "pv": r["pv"],
                    "pv_legal": r["pv_legal"],
                    "check_extensions_eligible": r["check_extensions_eligible"],
                    "check_extensions_applied": r["check_extensions_applied"],
                    "check_extension_plies": r["check_extension_plies"],
                    "check_extensions_suppressed": r["check_extensions_suppressed"],
                    "check_extensions_multiple_replies": r["check_extensions_multiple_replies"],
                    "check_extensions_terminal_mates": r["check_extensions_terminal_mates"],
                }
                for r in first_run["positions"]
            }

            total_eligible = sum(r["check_extensions_eligible"] for r in first_run["positions"])
            total_applied = sum(r["check_extensions_applied"] for r in first_run["positions"])
            total_plies = sum(r["check_extension_plies"] for r in first_run["positions"])
            total_suppressed = sum(r["check_extensions_suppressed"] for r in first_run["positions"])
            total_multiple_replies = sum(r["check_extensions_multiple_replies"] for r in first_run["positions"])
            total_terminal_mates = sum(r["check_extensions_terminal_mates"] for r in first_run["positions"])

            policy_aggregates[p] = {
                "nodes": node_count,
                "reps": reps_per_policy,
                "raw_elapsed_times": wall_times,
                "timing": calc_stats(wall_times),
                "extension_telemetry": {
                    "eligible": total_eligible,
                    "applied": total_applied,
                    "plies": total_plies,
                    "suppressed": total_suppressed,
                    "multiple_replies": total_multiple_replies,
                    "terminal_mates": total_terminal_mates,
                },
                "positions": per_pos,
            }

        depth_results[f"depth_{d}"] = {
            "schedule": runs_plan,
            "policies": policy_aggregates,
        }

    report = {
        "metadata": {
            "milestone": "v0.21",
            "experiment": "selective_check_extensions_controlled_benchmark",
            "git_commit": git_commit(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "schedule_seed": seed,
            "repetitions_per_policy": reps_per_policy,
            "positions_count": len(positions),
        },
        "depths": depth_results,
    }

    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n[DONE] Saved benchmark artifacts to {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
