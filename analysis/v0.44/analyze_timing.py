"""Analyze move times, node counts, NPS distributions and timing metrics in match_moves.csv using pure standard library."""
import csv
import json
import math
from pathlib import Path
import statistics

def run():
    csv_path = Path("analysis/v0.43/match_replication/match_moves.csv")
    
    k0_times = []
    rfp_times = []
    sf_times = []
    
    k0_nodes = []
    rfp_nodes = []
    
    k0_depths = []
    rfp_depths = []
    
    k0_overshoots = []
    rfp_overshoots = []

    k0_nps = []
    rfp_nps = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            is_janus = (row["is_janus"] == "True")
            cand = row["candidate"]
            time_ms = float(row["actual_time_ms"])
            nodes = int(row["nodes"])
            depth = int(row["depth"])
            overshoot = float(row["overshoot_ms"])
            nps = int(row["nps"])

            if is_janus:
                if cand == "k0":
                    k0_times.append(time_ms)
                    k0_nodes.append(nodes)
                    k0_depths.append(depth)
                    k0_overshoots.append(overshoot)
                    k0_nps.append(nps)
                elif cand == "rfp":
                    rfp_times.append(time_ms)
                    rfp_nodes.append(nodes)
                    rfp_depths.append(depth)
                    rfp_overshoots.append(overshoot)
                    rfp_nps.append(nps)
            else:
                sf_times.append(time_ms)

    def stats(arr):
        s = sorted(arr)
        n = len(s)
        def percentile(p):
            if not s: return 0.0
            k = (n - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return float(s[int(k)])
            d0 = s[int(f)] * (c - k)
            d1 = s[int(c)] * (k - f)
            return float(d0 + d1)

        return {
            "count": n,
            "mean": float(statistics.mean(s)),
            "std": float(statistics.stdev(s)) if n > 1 else 0.0,
            "median": float(statistics.median(s)),
            "p25": percentile(25),
            "p75": percentile(75),
            "p90": percentile(90),
            "p95": percentile(95),
            "max": float(max(s)),
            "min": float(min(s)),
        }

    timing_summary = {
        "k0_actual_time_ms": stats(k0_times),
        "rfp_actual_time_ms": stats(rfp_times),
        "sf_actual_time_ms": stats(sf_times),
        "k0_nodes": stats(k0_nodes),
        "rfp_nodes": stats(rfp_nodes),
        "k0_depth": stats(k0_depths),
        "rfp_depth": stats(rfp_depths),
        "k0_overshoot_ms": stats(k0_overshoots),
        "rfp_overshoot_ms": stats(rfp_overshoots),
        "k0_nps": stats(k0_nps),
        "rfp_nps": stats(rfp_nps),
    }

    out_file = Path("analysis/v0.44/timing_distribution.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(timing_summary, f, indent=2)

    print("=== Timing & Search Statistics Summary ===")
    print(f"K0 moves: {len(k0_times)}, RFP moves: {len(rfp_times)}, SF moves: {len(sf_times)}")
    print(f"K0 Time (ms): Mean={timing_summary['k0_actual_time_ms']['mean']:.1f}, Median={timing_summary['k0_actual_time_ms']['median']:.1f}, P95={timing_summary['k0_actual_time_ms']['p95']:.1f}, Max={timing_summary['k0_actual_time_ms']['max']:.1f}")
    print(f"RFP Time (ms): Mean={timing_summary['rfp_actual_time_ms']['mean']:.1f}, Median={timing_summary['rfp_actual_time_ms']['median']:.1f}, P95={timing_summary['rfp_actual_time_ms']['p95']:.1f}, Max={timing_summary['rfp_actual_time_ms']['max']:.1f}")
    print(f"Stockfish Time (ms): Mean={timing_summary['sf_actual_time_ms']['mean']:.1f}, Median={timing_summary['sf_actual_time_ms']['median']:.1f}, Max={timing_summary['sf_actual_time_ms']['max']:.1f}")
    print(f"K0 Nodes: Mean={timing_summary['k0_nodes']['mean']:.1f}, Median={timing_summary['k0_nodes']['median']:.1f}")
    print(f"RFP Nodes: Mean={timing_summary['rfp_nodes']['mean']:.1f}, Median={timing_summary['rfp_nodes']['median']:.1f}")
    print(f"Node reduction: {(1 - timing_summary['rfp_nodes']['mean'] / timing_summary['k0_nodes']['mean']) * 100:.2f}%")
    print(f"K0 Depth: Mean={timing_summary['k0_depth']['mean']:.2f}, Median={timing_summary['k0_depth']['median']:.1f}")
    print(f"RFP Depth: Mean={timing_summary['rfp_depth']['mean']:.2f}, Median={timing_summary['rfp_depth']['median']:.1f}")
    print(f"Depth increase: +{timing_summary['rfp_depth']['mean'] - timing_summary['k0_depth']['mean']:.2f} plies")

if __name__ == "__main__":
    run()
