"""Benchmark diagnostic instrumentation overhead across configurations."""
import json
import time
from pathlib import Path
import chess

from janus.search import JanusSearch

def run():
    fen = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5"
    board = chess.Board(fen)

    configs = [
        {"name": "K0_no_diagnostics", "enable_rfp": False, "diag_rfp": False, "diag_iter": False},
        {"name": "K0_diag_disabled", "enable_rfp": False, "diagnostic_rfp": False, "diagnostic_iterations": False},
        {"name": "K0_diag_enabled", "enable_rfp": False, "diagnostic_rfp": True, "diagnostic_iterations": True},
        {"name": "RFP_no_diagnostics", "enable_rfp": True, "diag_rfp": False, "diag_iter": False},
        {"name": "RFP_diag_disabled", "enable_rfp": True, "diagnostic_rfp": False, "diagnostic_iterations": False},
        {"name": "RFP_diag_enabled", "enable_rfp": True, "diagnostic_rfp": True, "diagnostic_iterations": True},
    ]

    runs_per_cfg = 5
    bench_results = {}

    print("Measuring instrumentation overhead at depth 4...")
    for cfg in configs:
        times = []
        nodes = []
        for _ in range(runs_per_cfg):
            e = JanusSearch(
                enable_rfp=cfg["enable_rfp"],
                rfp_max_depth=2,
                rfp_margin_per_depth=120,
                diagnostic_rfp=cfg.get("diagnostic_rfp", False),
                diagnostic_iterations=cfg.get("diagnostic_iterations", False),
            )
            t0 = time.perf_counter()
            res = e.search(board.copy(), max_depth=4)
            t1 = time.perf_counter()
            times.append(t1 - t0)
            nodes.append(res.nodes)

        avg_time = sum(times) / len(times)
        avg_nodes = sum(nodes) / len(nodes)
        nps = int(avg_nodes / avg_time) if avg_time > 0 else 0

        bench_results[cfg["name"]] = {
            "mean_elapsed_s": avg_time,
            "mean_nodes": avg_nodes,
            "nps": nps,
        }
        print(f"  {cfg['name']:22s}: Time={avg_time*1000:6.2f} ms | Nodes={avg_nodes:6.0f} | NPS={nps:6d}")

    # Quantify overhead
    k0_base = bench_results["K0_diag_disabled"]["mean_elapsed_s"]
    k0_active = bench_results["K0_diag_enabled"]["mean_elapsed_s"]
    k0_overhead_pct = ((k0_active - k0_base) / k0_base) * 100.0

    rfp_base = bench_results["RFP_diag_disabled"]["mean_elapsed_s"]
    rfp_active = bench_results["RFP_diag_enabled"]["mean_elapsed_s"]
    rfp_overhead_pct = ((rfp_active - rfp_base) / rfp_base) * 100.0

    report = {
        "configurations": bench_results,
        "overhead_analysis": {
            "k0_diagnostic_overhead_pct": k0_overhead_pct,
            "rfp_diagnostic_overhead_pct": rfp_overhead_pct,
            "disabled_overhead_vs_bare_code_pct": ((bench_results["K0_diag_disabled"]["mean_elapsed_s"] - bench_results["K0_no_diagnostics"]["mean_elapsed_s"]) / bench_results["K0_no_diagnostics"]["mean_elapsed_s"]) * 100.0,
        }
    }

    out_file = Path("analysis/v0.45/reports/telemetry_overhead.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved overhead benchmark to {out_file}")

if __name__ == "__main__":
    run()

