import json
import subprocess
import statistics
import sys
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

def run_single(depth: int, no_history: bool):
    cmd = [PYTHON, "scripts/benchmark.py", "--depth", str(depth)]
    if no_history:
        cmd.append("--no-history")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    json_path = None
    for line in proc.stdout.splitlines():
        if line.startswith("JSON:"):
            json_path = Path(line.split(":", 1)[1].strip())
            break
    assert json_path and json_path.exists(), f"Could not find json output: {proc.stdout}"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return {
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
    }

def compute_stats(runs):
    times = [r["total_elapsed_seconds"] for r in runs]
    times_sorted = sorted(times)
    n = len(times_sorted)
    q1 = times_sorted[n // 4] if n >= 4 else times_sorted[0]
    q3 = times_sorted[(3 * n) // 4] if n >= 4 else times_sorted[-1]
    return {
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "mean": round(statistics.mean(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
        "iqr": round(q3 - q1, 4),
        "all_times": times,
    }

def run_interleaved_suite(depth: int, reps: int = 10):
    print(f"\n--- Running {reps} interleaved pairs at Depth {depth} ---")
    disabled_runs = []
    enabled_runs = []
    for i in range(reps):
        # Alternate ordering on each pair to prevent order bias
        if i % 2 == 0:
            res_dis = run_single(depth, no_history=True)
            res_en = run_single(depth, no_history=False)
        else:
            res_en = run_single(depth, no_history=False)
            res_dis = run_single(depth, no_history=True)
        
        disabled_runs.append(res_dis)
        enabled_runs.append(res_en)
        print(f"  Rep {i+1:2d}/{reps}: Disabled={res_dis['total_elapsed_seconds']:.3f}s ({res_dis['total_nodes']} nodes) | Enabled={res_en['total_elapsed_seconds']:.3f}s ({res_en['total_nodes']} nodes)")

    dis_stats = compute_stats(disabled_runs)
    en_stats = compute_stats(enabled_runs)
    
    speedup = (dis_stats["median"] - en_stats["median"]) / dis_stats["median"] * 100
    node_delta = enabled_runs[0]["total_nodes"] - disabled_runs[0]["total_nodes"]
    node_delta_pct = node_delta / disabled_runs[0]["total_nodes"] * 100

    print(f"\nDepth {depth} Summary:")
    print(f"  Nodes: Disabled={disabled_runs[0]['total_nodes']}, Enabled={enabled_runs[0]['total_nodes']} (delta={node_delta:+d}, {node_delta_pct:+.2f}%)")
    print(f"  Disabled Time: Median={dis_stats['median']:.3f}s, Min={dis_stats['min']:.3f}s, Max={dis_stats['max']:.3f}s, IQR={dis_stats['iqr']:.3f}s, Stdev={dis_stats['stdev']:.3f}s")
    print(f"  Enabled Time:  Median={en_stats['median']:.3f}s, Min={en_stats['min']:.3f}s, Max={en_stats['max']:.3f}s, IQR={en_stats['iqr']:.3f}s, Stdev={en_stats['stdev']:.3f}s")
    print(f"  Speedup (based on median): {speedup:+.2f}%")

    return {
        "disabled_nodes": disabled_runs[0]["total_nodes"],
        "enabled_nodes": enabled_runs[0]["total_nodes"],
        "node_delta": node_delta,
        "node_delta_percent": round(node_delta_pct, 2),
        "disabled_stats": dis_stats,
        "enabled_stats": en_stats,
        "speedup_percent": round(speedup, 2),
        "disabled_runs": disabled_runs,
        "enabled_runs": enabled_runs,
    }

depth3_res = run_interleaved_suite(3, reps=10)
depth4_res = run_interleaved_suite(4, reps=10)

out = {
    "description": "v0.14 Phase 1: 10 interleaved independent-process repetitions comparing History Disabled vs Enabled",
    "depth_3": depth3_res,
    "depth_4": depth4_res,
}

out_file = ROOT / "analysis" / "v0.14" / "interleaved_baseline_benchmarks.json"
out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nWrote results to {out_file}")
