import json
import subprocess
import statistics
import sys
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

def run_reps(depth: int, reps: int = 5):
    runs = []
    for r in range(reps):
        cmd = [PYTHON, "scripts/benchmark.py", "--depth", str(depth)]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
        # Find JSON path in stdout
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
    stats = {
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "mean": round(statistics.mean(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
        "iqr": round(q3 - q1, 4),
    }
    return {"runs": runs, "stats": stats}

print("Running 5 independent process runs at Depth 3...")
d3 = run_reps(3, 5)
print(f"Depth 3 stats: median={d3['stats']['median']}s, min={d3['stats']['min']}s, max={d3['stats']['max']}s, iqr={d3['stats']['iqr']}s")

print("Running 5 independent process runs at Depth 4...")
d4 = run_reps(4, 5)
print(f"Depth 4 stats: median={d4['stats']['median']}s, min={d4['stats']['min']}s, max={d4['stats']['max']}s, iqr={d4['stats']['iqr']}s")

output = {
    "engine_commit": "30f2f78",
    "description": "Milestone v0.11 pre-optimization baseline across 5 independent process runs",
    "depth_3": d3,
    "depth_4": d4,
}

out_path = ROOT / "analysis" / "v0.11" / "baseline_benchmarks.json"
out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
print(f"Saved baseline benchmarks to {out_path}")
