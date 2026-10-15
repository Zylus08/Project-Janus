import json
import statistics
import time
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus")
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))

def benchmark_suite(enable_history: bool, depth: int, reps: int = 5):
    all_runs = []
    for r in range(reps):
        total_time = 0.0
        total_nodes = 0
        pos_results = []
        for p in positions_data:
            eng = JanusSearch(enable_history=enable_history)
            b = chess.Board(p["fen"])
            eng.tt.clear()
            res = eng.search(b, max_depth=depth)
            total_time += res.elapsed
            total_nodes += res.nodes
            pos_results.append({
                "id": p["id"],
                "nodes": res.nodes,
                "best_move": None if res.best_move is None else res.best_move.uci(),
                "score": res.score,
                "elapsed": round(res.elapsed, 4),
            })
        all_runs.append({
            "run": r + 1,
            "total_nodes": total_nodes,
            "total_elapsed_seconds": round(total_time, 4),
            "results": pos_results,
        })
    times = [r["total_elapsed_seconds"] for r in all_runs]
    stats = {
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "mean": round(statistics.mean(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
    }
    return {"runs": all_runs, "stats": stats}

print("Running 5 contemporary Depth 3 runs without history...")
base_d3 = benchmark_suite(False, 3, 5)
print(f"Base Depth 3: median={base_d3['stats']['median']}s (min={base_d3['stats']['min']}s, max={base_d3['stats']['max']}s)")

print("Running 5 contemporary Depth 3 runs with history...")
hist_d3 = benchmark_suite(True, 3, 5)
print(f"Hist Depth 3: median={hist_d3['stats']['median']}s (min={hist_d3['stats']['min']}s, max={hist_d3['stats']['max']}s)")

print("Running 5 contemporary Depth 4 runs without history...")
base_d4 = benchmark_suite(False, 4, 5)
print(f"Base Depth 4: median={base_d4['stats']['median']}s (min={base_d4['stats']['min']}s, max={base_d4['stats']['max']}s)")

print("Running 5 contemporary Depth 4 runs with history...")
hist_d4 = benchmark_suite(True, 4, 5)
print(f"Hist Depth 4: median={hist_d4['stats']['median']}s (min={hist_d4['stats']['min']}s, max={hist_d4['stats']['max']}s)")

d3_sp = (base_d3['stats']['median'] - hist_d3['stats']['median']) / base_d3['stats']['median'] * 100
d4_sp = (base_d4['stats']['median'] - hist_d4['stats']['median']) / base_d4['stats']['median'] * 100

print(f"\nContemporary Depth 3 speedup: {d3_sp:+.1f}%")
print(f"Contemporary Depth 4 speedup: {d4_sp:+.1f}%")

out = {
    "baseline_depth_3": base_d3,
    "history_depth_3": hist_d3,
    "baseline_depth_4": base_d4,
    "history_depth_4": hist_d4,
    "contemporary_speedup": {
        "depth_3": round(d3_sp, 2),
        "depth_4": round(d4_sp, 2),
    }
}
(ROOT / "analysis" / "v0.13" / "contemporary_baseline_vs_history.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("Saved contemporary benchmark data to analysis/v0.13/contemporary_baseline_vs_history.json")
