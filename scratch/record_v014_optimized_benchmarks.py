import json
import subprocess
import statistics
import sys
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

def run_suite(depth: int, reps: int = 10):
    runs = []
    for r in range(reps):
        cmd = [PYTHON, "scripts/benchmark.py", "--depth", str(depth)]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
        json_path = None
        for line in proc.stdout.splitlines():
            if line.startswith("JSON:"):
                json_path = Path(line.split(":", 1)[1].strip())
                break
        assert json_path and json_path.exists(), f"Could not find json output: {proc.stdout}"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        runs.append({
            "run": r + 1,
            "total_nodes": data["summary"]["total_nodes"],
            "total_elapsed_seconds": data["summary"]["total_elapsed_seconds"],
            "json_file": str(json_path),
            "results": [
                {
                    "id": row["id"],
                    "nodes": row["nodes"],
                    "score": row["score_from_side_to_move"],
                    "best_move": row["best_move_uci"],
                    "pv": row["pv_uci"],
                    "elapsed": row["elapsed_seconds"],
                }
                for row in data["results"]
            ]
        })
    times = [r["total_elapsed_seconds"] for r in runs]
    times_sorted = sorted(times)
    n = len(times_sorted)
    q1 = times_sorted[n // 4] if n >= 4 else times_sorted[0]
    q3 = times_sorted[(3 * n) // 4] if n >= 4 else times_sorted[-1]
    return {
        "runs": runs,
        "stats": {
            "min": round(min(times), 4),
            "max": round(max(times), 4),
            "median": round(statistics.median(times), 4),
            "mean": round(statistics.mean(times), 4),
            "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
            "iqr": round(q3 - q1, 4),
            "all_times": times,
        }
    }

print("Running 10 repetitions at Depth 3 (Optimized History)...")
d3 = run_suite(3, reps=10)
print(f"Depth 3 Optimized: median={d3['stats']['median']:.3f}s (min={d3['stats']['min']:.3f}s, max={d3['stats']['max']:.3f}s, iqr={d3['stats']['iqr']:.3f}s)")

print("Running 10 repetitions at Depth 4 (Optimized History)...")
d4 = run_suite(4, reps=10)
print(f"Depth 4 Optimized: median={d4['stats']['median']:.3f}s (min={d4['stats']['min']:.3f}s, max={d4['stats']['max']:.3f}s, iqr={d4['stats']['iqr']:.3f}s)")

out = {
    "description": "v0.14 Phase 4: 10 independent runs of optimized history heuristic",
    "depth_3": d3,
    "depth_4": d4,
}
out_file = ROOT / "analysis" / "v0.14" / "optimized_history_benchmarks.json"
out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Wrote results to {out_file}")
