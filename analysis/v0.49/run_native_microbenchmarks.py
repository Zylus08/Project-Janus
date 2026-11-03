"""Project Janus v0.49 - Native Selection Microbenchmarks & Boundary Overhead (Phases C3 & E1).

Compares:
1. Python eager sort (list.sort)
2. Python stable incremental selection (O(N) search per move)
3. Native batch partial sort (C DLL stable partial sort)
4. Native per-move selection (ctypes per-move call)
5. Existing L1 two-phase generator approach

Measures median runtime, P95, throughput, boundary overhead, and scaling across move-list sizes.
"""

import sys
import os
import time
import json
import statistics
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent / "native"))

from native_picker import (
    native_stable_partial_sort,
    native_select_next_best,
    py_stable_partial_sort,
    native_available,
    native_version,
)


def run_microbenchmarks():
    print("=" * 80, flush=True)
    print(f"PROJECT JANUS v0.49 - NATIVE MOVE-PICKER MICROBENCHMARKS (Native={native_available})", flush=True)
    print("=" * 80, flush=True)

    random.seed(42)
    move_counts = [10, 25, 35, 50, 75]
    iterations_per_test = 5000

    results = {}

    for n in move_counts:
        print(f"\n--- Move List Size: {n} candidate moves ({iterations_per_test} iterations) ---", flush=True)
        # Generate realistic chess score distributions:
        # e.g., 1 TT move (1,000,000), 2-4 captures (50,000 to 200,000), 2 killers, remainder quiets (0 to 10,000)
        test_data = []
        for _ in range(iterations_per_test):
            scores = [random.randint(0, 10000) for _ in range(n)]
            # TT move
            scores[0] = 1000000
            # Captures
            if n > 3:
                scores[1] = random.randint(50000, 200000)
                scores[2] = random.randint(50000, 200000)
            # Killers
            if n > 5:
                scores[3] = 700000
                scores[4] = 600000
            # Shuffle so TT/captures are randomly placed
            random.shuffle(scores)
            test_data.append(scores)

        # 1. Python Eager Sort (list.sort)
        t_py_eager = []
        for scores in test_data:
            t0 = time.perf_counter_ns()
            indices = list(range(n))
            indices.sort(key=lambda idx: scores[idx], reverse=True)
            t_py_eager.append(time.perf_counter_ns() - t0)

        # 2. Python Stable Incremental Selection (Top 1 only - first move cutoff scenario)
        t_py_inc_top1 = []
        for scores in test_data:
            t0 = time.perf_counter_ns()
            best_idx = 0
            best_score = scores[0]
            for i in range(1, n):
                if scores[i] > best_score:
                    best_score = scores[i]
                    best_idx = i
            t_py_inc_top1.append(time.perf_counter_ns() - t0)

        # 3. Python Stable Incremental Selection (Top 5 moves)
        t_py_inc_top5 = []
        for scores in test_data:
            t0 = time.perf_counter_ns()
            selected = [False] * n
            top_moves = []
            for _ in range(min(5, n)):
                best_idx = -1
                best_score = -2147483647
                for i in range(n):
                    if not selected[i] and scores[i] > best_score:
                        best_score = scores[i]
                        best_idx = i
                selected[best_idx] = True
                top_moves.append(best_idx)
            t_py_inc_top5.append(time.perf_counter_ns() - t0)

        # 4. Native Batch Partial Sort (Top 1)
        t_c_partial_top1 = []
        for scores in test_data:
            t0 = time.perf_counter_ns()
            out = native_stable_partial_sort(scores, 1)
            t_c_partial_top1.append(time.perf_counter_ns() - t0)

        # 5. Native Batch Partial Sort (Top 5)
        t_c_partial_top5 = []
        for scores in test_data:
            t0 = time.perf_counter_ns()
            out = native_stable_partial_sort(scores, 5)
            t_c_partial_top5.append(time.perf_counter_ns() - t0)

        # 6. Native Batch Full Sort (Top N)
        t_c_full = []
        for scores in test_data:
            t0 = time.perf_counter_ns()
            out = native_stable_partial_sort(scores, n)
            t_c_full.append(time.perf_counter_ns() - t0)

        # 7. Native Per-Move Call (Top 1)
        t_c_per_move_top1 = []
        for scores in test_data:
            selected = [False] * n
            t0 = time.perf_counter_ns()
            out = native_select_next_best(scores, selected)
            t_c_per_move_top1.append(time.perf_counter_ns() - t0)

        res_n = {
            "move_count": n,
            "py_eager_median_ns": statistics.median(t_py_eager),
            "py_eager_p95_ns": statistics.quantiles(t_py_eager, n=20)[18],
            "py_inc_top1_median_ns": statistics.median(t_py_inc_top1),
            "py_inc_top5_median_ns": statistics.median(t_py_inc_top5),
            "c_partial_top1_median_ns": statistics.median(t_c_partial_top1),
            "c_partial_top5_median_ns": statistics.median(t_c_partial_top5),
            "c_full_median_ns": statistics.median(t_c_full),
            "c_per_move_top1_median_ns": statistics.median(t_c_per_move_top1),
        }
        results[n] = res_n

        print(f"  Python Eager Sort (Full N):       Median={res_n['py_eager_median_ns']/1000:.2f} µs | P95={res_n['py_eager_p95_ns']/1000:.2f} µs")
        print(f"  Python Incremental Top 1:         Median={res_n['py_inc_top1_median_ns']/1000:.2f} µs")
        print(f"  Python Incremental Top 5:         Median={res_n['py_inc_top5_median_ns']/1000:.2f} µs")
        print(f"  Native Batch Partial Sort (Top 1): Median={res_n['c_partial_top1_median_ns']/1000:.2f} µs")
        print(f"  Native Batch Partial Sort (Top 5): Median={res_n['c_partial_top5_median_ns']/1000:.2f} µs")
        print(f"  Native Batch Full Sort (Top N):    Median={res_n['c_full_median_ns']/1000:.2f} µs")
        print(f"  Native Per-Move Call (Top 1):     Median={res_n['c_per_move_top1_median_ns']/1000:.2f} µs")

    out_file = Path("analysis/v0.49/raw/microbenchmarks_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nMicrobenchmarks complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_microbenchmarks()

