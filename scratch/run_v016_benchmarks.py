import subprocess
import json
import statistics
import time
import sys
from pathlib import Path

ROOT = Path("e:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")
SCRIPT = str(ROOT / "scripts" / "benchmark.py")
OUT_DIR = ROOT / "analysis" / "v0.16"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPETITIONS = 5
DEPTHS = [3, 4, 5]

def run_single(depth: int, pvs_enabled: bool) -> dict:
    cmd = [PYTHON, SCRIPT, "--depth", str(depth)]
    if not pvs_enabled:
        cmd.append("--no-pvs")
    
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    for line in proc.stdout.splitlines():
        if line.startswith("JSON:"):
            json_path = Path(line.split(":", 1)[1].strip())
            return json.loads(json_path.read_text(encoding="utf-8"))
    raise RuntimeError(f"Could not find JSON output in stdout:\n{proc.stdout}")

def calc_dispersion(times):
    med = statistics.median(times)
    mean = statistics.mean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0.0
    sorted_t = sorted(times)
    q1 = sorted_t[len(times) // 4]
    q3 = sorted_t[(3 * len(times)) // 4]
    iqr = q3 - q1
    return {
        "median": round(med, 4),
        "mean": round(mean, 4),
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "stdev": round(stdev, 4),
        "iqr": round(iqr, 4),
        "raw_times": [round(t, 4) for t in times],
    }

def main():
    print(f"Starting Milestone v0.16 Search Benchmark...")
    print(f"Configurations: 5 interleaved paired repetitions per depth {DEPTHS}")
    print(f"Alternating order: Reps 1, 3, 5 = Baseline then PVS; Reps 2, 4 = PVS then Baseline\n")

    raw_runs = {
        d: {"pvs_disabled": [], "pvs_enabled": []}
        for d in DEPTHS
    }

    for depth in DEPTHS:
        print(f"==================================================")
        print(f"BENCHMARKING DEPTH {depth}")
        print(f"==================================================")
        for rep in range(1, REPETITIONS + 1):
            # Alternating order
            if rep % 2 == 1:
                # Baseline then PVS
                print(f"  Rep {rep}/{REPETITIONS} (Order: Baseline -> PVS):")
                print(f"    Running Baseline (PVS Disabled)...", end="", flush=True)
                res_dis = run_single(depth, pvs_enabled=False)
                raw_runs[depth]["pvs_disabled"].append(res_dis)
                print(f" {res_dis['summary']['total_elapsed_seconds']:.3f}s, {res_dis['summary']['total_nodes']} nodes")

                time.sleep(0.5)

                print(f"    Running PVS Enabled...", end="", flush=True)
                res_ena = run_single(depth, pvs_enabled=True)
                raw_runs[depth]["pvs_enabled"].append(res_ena)
                print(f" {res_ena['summary']['total_elapsed_seconds']:.3f}s, {res_ena['summary']['total_nodes']} nodes")
            else:
                # PVS then Baseline
                print(f"  Rep {rep}/{REPETITIONS} (Order: PVS -> Baseline):")
                print(f"    Running PVS Enabled...", end="", flush=True)
                res_ena = run_single(depth, pvs_enabled=True)
                raw_runs[depth]["pvs_enabled"].append(res_ena)
                print(f" {res_ena['summary']['total_elapsed_seconds']:.3f}s, {res_ena['summary']['total_nodes']} nodes")

                time.sleep(0.5)

                print(f"    Running Baseline (PVS Disabled)...", end="", flush=True)
                res_dis = run_single(depth, pvs_enabled=False)
                raw_runs[depth]["pvs_disabled"].append(res_dis)
                print(f" {res_dis['summary']['total_elapsed_seconds']:.3f}s, {res_dis['summary']['total_nodes']} nodes")

            time.sleep(1.0)

    print("\nComputing statistical summaries and verifying correctness...")

    summary_report = {
        "metadata": {
            "milestone": "v0.16",
            "git_commit": "9e8de8e01bfbb7ee937015cf1f3ca69ea238712f",
            "repetitions": REPETITIONS,
            "depths": DEPTHS,
            "alternating_order": True,
            "python_version": "3.12.8",
            "platform": "Windows 11 Pro",
            "cpu": "Intel(R) Core(TM) i7-12650H",
            "power_state": "AC mains connected / charging",
        },
        "depth_metrics": {},
        "raw_runs": raw_runs,
    }

    for depth in DEPTHS:
        dis_runs = raw_runs[depth]["pvs_disabled"]
        ena_runs = raw_runs[depth]["pvs_enabled"]

        dis_times = [r["summary"]["total_elapsed_seconds"] for r in dis_runs]
        ena_times = [r["summary"]["total_elapsed_seconds"] for r in ena_runs]

        dis_nodes = dis_runs[0]["summary"]["total_nodes"]
        ena_nodes = ena_runs[0]["summary"]["total_nodes"]

        # Telemetry
        scout = ena_runs[0]["summary"]["total_scout_searches"]
        fh = ena_runs[0]["summary"]["total_scout_fail_highs"]
        res = ena_runs[0]["summary"]["total_researches"]
        cut_dis = dis_runs[0]["summary"]["total_beta_cutoffs"]
        cut_ena = ena_runs[0]["summary"]["total_beta_cutoffs"]

        dis_stats = calc_dispersion(dis_times)
        ena_stats = calc_dispersion(ena_times)

        node_reduction_pct = round((dis_nodes - ena_nodes) / dis_nodes * 100, 2)
        speedup_median_pct = round((dis_stats["median"] - ena_stats["median"]) / dis_stats["median"] * 100, 2)
        speedup_mean_pct = round((dis_stats["mean"] - ena_stats["mean"]) / dis_stats["mean"] * 100, 2)

        # Invariance verification
        mismatches = []
        for i in range(len(dis_runs[0]["results"])):
            pos_dis = dis_runs[0]["results"][i]
            pos_ena = ena_runs[0]["results"][i]
            if pos_dis["best_move_uci"] != pos_ena["best_move_uci"] or pos_dis["score_from_side_to_move"] != pos_ena["score_from_side_to_move"]:
                mismatches.append({
                    "id": pos_dis["id"],
                    "baseline_score": pos_dis["score_from_side_to_move"],
                    "pvs_score": pos_ena["score_from_side_to_move"],
                    "baseline_move": pos_dis["best_move_uci"],
                    "pvs_move": pos_ena["best_move_uci"],
                })

        summary_report["depth_metrics"][f"depth_{depth}"] = {
            "nodes_disabled": dis_nodes,
            "nodes_enabled": ena_nodes,
            "node_delta": ena_nodes - dis_nodes,
            "node_reduction_pct": node_reduction_pct,
            "time_disabled": dis_stats,
            "time_enabled": ena_stats,
            "speedup_median_pct": speedup_median_pct,
            "speedup_mean_pct": speedup_mean_pct,
            "telemetry": {
                "scout_searches": scout,
                "scout_fail_highs": fh,
                "researches": res,
                "beta_cutoffs_disabled": cut_dis,
                "beta_cutoffs_enabled": cut_ena,
                "scout_refutation_rate_pct": round((1.0 - (res / scout)) * 100, 2) if scout > 0 else 100.0,
            },
            "invariance": {
                "verified": len(mismatches) == 0,
                "mismatches": mismatches,
            },
        }

    out_file = OUT_DIR / "search_benchmarks.json"
    out_file.write_text(json.dumps(summary_report, indent=2), encoding="utf-8")
    print(f"\nBenchmark completed successfully! Artifact written to {out_file}")

if __name__ == "__main__":
    main()
