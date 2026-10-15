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

print("Running 5 independent process runs at Depth 3 (Optimized)...")
d3 = run_reps(3, 5)
print(f"Depth 3 stats: median={d3['stats']['median']}s, min={d3['stats']['min']}s, max={d3['stats']['max']}s, iqr={d3['stats']['iqr']}s")

print("Running 5 independent process runs at Depth 4 (Optimized)...")
d4 = run_reps(4, 5)
print(f"Depth 4 stats: median={d4['stats']['median']}s, min={d4['stats']['min']}s, max={d4['stats']['max']}s, iqr={d4['stats']['iqr']}s")

# Load baseline benchmarks to verify equivalence
baseline_path = ROOT / "analysis" / "v0.11" / "baseline_benchmarks.json"
baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

# Equivalence checks
print("\n--- Verifying Exact Equivalence ---")
assert d3["runs"][0]["total_nodes"] == baseline["depth_3"]["runs"][0]["total_nodes"], "Depth 3 total nodes differ!"
assert d4["runs"][0]["total_nodes"] == baseline["depth_4"]["runs"][0]["total_nodes"], "Depth 4 total nodes differ!"

for pos_idx in range(6):
    b3 = baseline["depth_3"]["runs"][0]["results"][pos_idx]
    o3 = d3["runs"][0]["results"][pos_idx]
    assert b3["nodes"] == o3["nodes"], f"Depth 3 nodes differ for {b3['id']}: {b3['nodes']} vs {o3['nodes']}"
    assert b3["best_move"] == o3["best_move"], f"Depth 3 best move differs for {b3['id']}"
    assert b3["score"] == o3["score"], f"Depth 3 score differs for {b3['id']}"
    assert b3["pv"] == o3["pv"], f"Depth 3 PV differs for {b3['id']}"

    b4 = baseline["depth_4"]["runs"][0]["results"][pos_idx]
    o4 = d4["runs"][0]["results"][pos_idx]
    assert b4["nodes"] == o4["nodes"], f"Depth 4 nodes differ for {b4['id']}: {b4['nodes']} vs {o4['nodes']}"
    assert b4["best_move"] == o4["best_move"], f"Depth 4 best move differs for {b4['id']}"
    assert b4["score"] == o4["score"], f"Depth 4 score differs for {b4['id']}"
    assert b4["pv"] == o4["pv"], f"Depth 4 PV differs for {b4['id']}"

print("All node counts, best moves, scores, and PVs match 100% identically!")

# Compute speedup
d3_base_med = baseline["depth_3"]["stats"]["median"]
d3_opt_med = d3["stats"]["median"]
d3_speedup = (d3_base_med - d3_opt_med) / d3_base_med * 100

d4_base_med = baseline["depth_4"]["stats"]["median"]
d4_opt_med = d4["stats"]["median"]
d4_speedup = (d4_base_med - d4_opt_med) / d4_base_med * 100

print(f"\n--- Performance Comparison ---")
print(f"Depth 3 Median: {d3_base_med:.3f}s -> {d3_opt_med:.3f}s (delta: {d3_base_med - d3_opt_med:+.3f}s, speedup: {d3_speedup:+.1f}%)")
print(f"Depth 4 Median: {d4_base_med:.3f}s -> {d4_opt_med:.3f}s (delta: {d4_base_med - d4_opt_med:+.3f}s, speedup: {d4_speedup:+.1f}%)")

output = {
    "engine_commit": "optimized_v0.11",
    "description": "Milestone v0.11 optimized benchmark results across 5 independent process runs",
    "depth_3": d3,
    "depth_4": d4,
    "comparison": {
        "depth_3_baseline_median": d3_base_med,
        "depth_3_optimized_median": d3_opt_med,
        "depth_3_speedup_percent": round(d3_speedup, 2),
        "depth_4_baseline_median": d4_base_med,
        "depth_4_optimized_median": d4_opt_med,
        "depth_4_speedup_percent": round(d4_speedup, 2),
        "nodes_identical": True,
        "best_moves_identical": True,
        "scores_identical": True,
        "pvs_identical": True,
    }
}

out_path = ROOT / "analysis" / "v0.11" / "optimized_benchmarks.json"
out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
print(f"Saved optimized benchmarks to {out_path}")
