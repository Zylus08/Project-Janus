import subprocess
import json
import statistics
import sys
from pathlib import Path

ROOT = Path("e:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")
SCRIPT = str(ROOT / "scripts" / "benchmark.py")
OUT_DIR = ROOT / "analysis" / "v0.15"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPETITIONS = 5
DEPTHS = [3, 4, 5]

def run_single(depth: int, pvs_enabled: bool) -> dict:
    cmd = [PYTHON, SCRIPT, "--depth", str(depth)]
    if not pvs_enabled:
        cmd.append("--no-pvs")
    
    # We will pass a temporary output directory to keep raw runs organized
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    # The benchmark script outputs the JSON path in its stdout: "JSON: <path>"
    for line in res.stdout.splitlines():
        if line.startswith("JSON:"):
            json_path = Path(line.split(":", 1)[1].strip())
            return json.loads(json_path.read_text(encoding="utf-8"))
    raise RuntimeError(f"Failed to find JSON output in stdout:\n{res.stdout}")

def main():
    print(f"Starting v0.15 PVS benchmark audit: {REPETITIONS} interleaved repetitions at depths {DEPTHS}...")
    
    # Structure: results[depth][config] = list of runs
    raw_data = {
        d: {"pvs_disabled": [], "pvs_enabled": []}
        for d in DEPTHS
    }

    for rep in range(1, REPETITIONS + 1):
        print(f"\n>>> Running Repetition {rep}/{REPETITIONS}")
        for depth in DEPTHS:
            print(f"  Depth {depth}: Running Baseline (PVS Disabled)...", end="", flush=True)
            res_disabled = run_single(depth, pvs_enabled=False)
            raw_data[depth]["pvs_disabled"].append(res_disabled)
            print(f" done ({res_disabled['summary']['total_elapsed_seconds']:.3f}s, {res_disabled['summary']['total_nodes']} nodes)")

            print(f"  Depth {depth}: Running PVS Enabled...", end="", flush=True)
            res_enabled = run_single(depth, pvs_enabled=True)
            raw_data[depth]["pvs_enabled"].append(res_enabled)
            print(f" done ({res_enabled['summary']['total_elapsed_seconds']:.3f}s, {res_enabled['summary']['total_nodes']} nodes)")

    print("\nProcessing benchmark statistics...")

    summary_report = {
        "metadata": {
            "repetitions": REPETITIONS,
            "depths": DEPTHS,
            "engine": "Project Janus",
            "milestone": "v0.15",
            "git_commit": "716bac15016dcbdb315818568b4831c394adfd92",
        },
        "depth_metrics": {},
        "raw_runs": raw_data,
    }

    for depth in DEPTHS:
        dis_runs = raw_data[depth]["pvs_disabled"]
        ena_runs = raw_data[depth]["pvs_enabled"]

        dis_times = [r["summary"]["total_elapsed_seconds"] for r in dis_runs]
        ena_times = [r["summary"]["total_elapsed_seconds"] for r in ena_runs]

        dis_nodes = dis_runs[0]["summary"]["total_nodes"]
        ena_nodes = ena_runs[0]["summary"]["total_nodes"]

        # Telemetry from PVS
        total_scout = ena_runs[0]["summary"]["total_scout_searches"]
        total_fail_high = ena_runs[0]["summary"]["total_scout_fail_highs"]
        total_research = ena_runs[0]["summary"]["total_researches"]
        total_beta_cut = ena_runs[0]["summary"]["total_beta_cutoffs"]

        scout_fail_high_rate = (total_fail_high / total_scout * 100) if total_scout > 0 else 0.0
        research_rate = (total_research / total_scout * 100) if total_scout > 0 else 0.0

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
            }

        dis_stats = calc_dispersion(dis_times)
        ena_stats = calc_dispersion(ena_times)

        node_reduction_pct = round((dis_nodes - ena_nodes) / dis_nodes * 100, 2)
        speedup_pct = round((dis_stats["median"] - ena_stats["median"]) / dis_stats["median"] * 100, 2)

        # Invariance check
        mismatches = []
        for i in range(len(dis_runs[0]["results"])):
            pos_dis = dis_runs[0]["results"][i]
            pos_ena = ena_runs[0]["results"][i]
            if pos_dis["best_move_uci"] != pos_ena["best_move_uci"] or pos_dis["score_from_side_to_move"] != pos_ena["score_from_side_to_move"]:
                mismatches.append({
                    "id": pos_dis["id"],
                    "dis_score": pos_dis["score_from_side_to_move"],
                    "ena_score": pos_ena["score_from_side_to_move"],
                    "dis_best": pos_dis["best_move_uci"],
                    "ena_best": pos_ena["best_move_uci"],
                })

        summary_report["depth_metrics"][f"depth_{depth}"] = {
            "nodes_disabled": dis_nodes,
            "nodes_enabled": ena_nodes,
            "node_delta": ena_nodes - dis_nodes,
            "node_reduction_pct": node_reduction_pct,
            "time_disabled": dis_stats,
            "time_enabled": ena_stats,
            "speedup_pct": speedup_pct,
            "telemetry": {
                "scout_searches": total_scout,
                "scout_fail_highs": total_fail_high,
                "researches": total_research,
                "beta_cutoffs": total_beta_cut,
                "scout_fail_high_rate_pct": round(scout_fail_high_rate, 2),
                "research_rate_pct": round(research_rate, 2),
            },
            "invariance": {
                "verified": len(mismatches) == 0,
                "mismatches": mismatches,
            },
        }

    out_file = OUT_DIR / "pvs_benchmarks.json"
    out_file.write_text(json.dumps(summary_report, indent=2), encoding="utf-8")
    print(f"\nAll benchmark repetitions complete. Results saved to {out_file}")

if __name__ == "__main__":
    main()
