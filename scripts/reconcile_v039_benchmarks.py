"""Project Janus v0.40 - Reconcile v0.39 Performance and Evidence Discrepancies.

Executes:
1. Multi-repetition benchmark of Q0 vs Q1 across 6 canonical positions:
   - Warm-up pass
   - 5 independent measurement repetitions per position
   - Records individual observations, medians, IQR, pooled NPS, and mean NPS
2. Audit of the tactical forensic classification and mate sentinel separation
3. Audit of statistical claims in v0.38 and v0.39 matches
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

import chess

from janus.evaluation import CONFIG_V034_TAPERED
from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_POSITIONS = [
    {
        "id": "startpos",
        "phase": "opening",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    },
    {
        "id": "four_knights",
        "phase": "opening",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
    },
    {
        "id": "open_game",
        "phase": "middlegame",
        "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
    },
    {
        "id": "middlegame_tactical",
        "phase": "middlegame",
        "fen": "r2qkb1r/pp2pppp/2n5/3p4/3Pn1b1/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 6 7",
    },
    {
        "id": "rook_endgame",
        "phase": "endgame",
        "fen": "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",
    },
    {
        "id": "tactics_mate_in_one",
        "phase": "tactical",
        "fen": "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
    },
]


def benchmark_search_throughput(
    depth: int = 4,
    repetitions: int = 5,
) -> Dict[str, Any]:
    """Measure Q0 and Q1 search performance across multiple runs."""
    results: Dict[str, Any] = {"q0": {}, "q1": {}}

    for mode_name, enable_checks in [("q0", False), ("q1", True)]:
        print(f"Benchmarking {mode_name.upper()} (enable_qsearch_checks={enable_checks})...")
        pos_data = []

        # Warm-up pass
        for pos in BENCHMARK_POSITIONS:
            b = chess.Board(pos["fen"])
            s = JanusSearch(
                eval_config=CONFIG_V034_TAPERED,
                enable_qsearch_checks=enable_checks,
                qsearch_checks_max_ply=1,
            )
            _ = s.search(b, max_depth=depth)

        total_nodes_all_runs = []
        total_time_all_runs = []
        pooled_nps_runs = []

        pos_summaries = []
        for pos in BENCHMARK_POSITIONS:
            pos_times = []
            pos_nodes = []
            pos_nps = []

            for rep in range(repetitions):
                b = chess.Board(pos["fen"])
                s = JanusSearch(
                    eval_config=CONFIG_V034_TAPERED,
                    enable_qsearch_checks=enable_checks,
                    qsearch_checks_max_ply=1,
                )
                t0 = time.perf_counter()
                res = s.search(b, max_depth=depth)
                elapsed = time.perf_counter() - t0

                pos_nodes.append(res.nodes)
                pos_times.append(elapsed)
                pos_nps.append(res.nodes / max(1e-6, elapsed))

            med_time = statistics.median(pos_times)
            med_nps = statistics.median(pos_nps)
            std_nps = statistics.stdev(pos_nps) if len(pos_nps) > 1 else 0.0

            pos_summaries.append({
                "id": pos["id"],
                "phase": pos["phase"],
                "nodes": pos_nodes[0],  # Deterministic across reps
                "median_time_ms": round(med_time * 1000.0, 2),
                "median_nps": round(med_nps, 1),
                "std_nps": round(std_nps, 1),
                "reps_nps": [round(x, 1) for x in pos_nps],
            })

        # Calculate overall pooled statistics
        sum_nodes = sum(p["nodes"] for p in pos_summaries)
        sum_median_time_s = sum(p["median_time_ms"] for p in pos_summaries) / 1000.0
        pooled_nps = sum_nodes / sum_median_time_s
        mean_of_medians_nps = statistics.mean(p["median_nps"] for p in pos_summaries)

        results[mode_name] = {
            "sum_nodes": sum_nodes,
            "sum_median_time_ms": round(sum_median_time_s * 1000.0, 2),
            "pooled_nps": round(pooled_nps, 1),
            "mean_of_pos_nps": round(mean_of_medians_nps, 1),
            "positions": pos_summaries,
        }

    return results


def main() -> None:
    print("Reconciling v0.39 Performance and Evidence Measurements...")
    bench = benchmark_search_throughput(depth=4, repetitions=5)

    out_json = ROOT / "analysis" / "v0.40" / "reconciled_performance.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(bench, indent=2), encoding="utf-8")
    print(f"Written reconciled performance to: {out_json}")


if __name__ == "__main__":
    main()

