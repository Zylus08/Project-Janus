"""Phase 6 Secondary Experiment: Interaction of TT Replacement Policies with SEE Ordering & Pruning.

Evaluates TT replacement policies with both SEE ordering and SEE pruning enabled:
- always_replace + SEE
- depth_preferred + SEE
- two_tier + SEE

Depths: 3, 4, 5 (3 interleaved repetitions).
Saves results to analysis/v0.23/see_tt_benchmarks.json.
"""
from __future__ import annotations

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

def main():
    positions = load_positions(ROOT / "benchmarks" / "positions.json")
    out_file = ROOT / "analysis" / "v0.23" / "see_tt_benchmarks.json"
    policies = ["always_replace", "depth_preferred", "two_tier"]
    depths = [3, 4, 5]
    reps = 3
    rng = random.Random(20261017)

    results = {}
    print("=== Phase 6: TT Replacement Policy + SEE Interaction Experiment ===")

    for d in depths:
        print(f"\n--- Running Depth {d} (SEE ON) ---")
        runs_plan = []
        for p in policies:
            runs_plan.extend([p] * reps)
        rng.shuffle(runs_plan)

        policy_data = {p: [] for p in policies}
        for run_idx, pol in enumerate(runs_plan, 1):
            engine = JanusSearch(
                check_extension_policy="disabled",
                enable_history=True,
                enable_pvs=True,
                enable_aspiration=True,
                enable_lmr=True,
                enable_nmp=True,
                enable_see_ordering=True,
                enable_see_pruning=True,
                tt_replacement_policy=pol,
            )
            t0 = time.perf_counter()
            tot_nodes = 0
            for pos in positions:
                engine.tt.clear()
                board = chess.Board(pos["fen"])
                res = engine.search(board, max_depth=d)
                tot_nodes += res.nodes
            elapsed = time.perf_counter() - t0
            policy_data[pol].append({"nodes": tot_nodes, "elapsed": elapsed})
            print(f"  [Depth {d} Run {run_idx:02d}/{len(runs_plan):02d}] {pol:<18} nodes={tot_nodes:<7} elapsed={elapsed:.3f}s")

        d_res = {}
        for pol in policies:
            times = sorted(r["elapsed"] for r in policy_data[pol])
            med_time = times[len(times) // 2]
            d_res[pol] = {
                "nodes": policy_data[pol][0]["nodes"],
                "median_elapsed": round(med_time, 4),
            }
        results[f"depth_{d}"] = d_res

    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved Phase 6 results to {out_file}")
    print("\nSummary with SEE ON:")
    for d in depths:
        print(f"Depth {d}:")
        for pol in policies:
            r = results[f"depth_{d}"][pol]
            print(f"  {pol:<18}: nodes={r['nodes']:<7} median_time={r['median_elapsed']:.3f}s")

if __name__ == "__main__":
    main()
