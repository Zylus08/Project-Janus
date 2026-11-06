"""Project Janus v0.60 - Preliminary Search Evaluation Runner.

Compares:
- C1: Frozen Handcrafted Static Evaluation (UseNeuralValue=false)
- V1-A: Pure Learned Value Evaluation (UseNeuralValue=true, Blend=100)
- V1-B: Hybrid Classical + Learned Evaluation (UseNeuralValue=true, Blend=50)

Evaluates on 10 standardized tactical and strategic benchmark positions under:
1. Fixed-depth Search (Depth 5)
2. Fixed-time Search (500 ms)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
BRIDGE_PATH = ROOT / "analysis" / "v0.60" / "native" / "janus_native_bridge.py"
MODEL_PATH = ROOT / "analysis" / "v0.60" / "models" / "janus_nnue_v1_small.jnnue"
RAW_DIR = ROOT / "analysis" / "v0.60" / "raw"

spec = importlib.util.spec_from_file_location("bridge_v60", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

BENCHMARK_POSITIONS = [
    {
        "name": "Starting Position",
        "category": "opening",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    },
    {
        "name": "Italian Game Open",
        "category": "opening",
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5",
    },
    {
        "name": "Sicilian Defense Classical",
        "category": "opening",
        "fen": "r1bqkbnr/pp1ppppp/2n5/8/3NP3/8/PPP2PPP/RNBQKB1R b KQkq - 2 4",
    },
    {
        "name": "Middlegame Complex Center",
        "category": "middlegame",
        "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PNP3/2N1BP2/PP4PP/R2QKB1R b KQ - 2 9",
    },
    {
        "name": "French Defense Closed",
        "category": "middlegame",
        "fen": "r1b1k2r/ppqn1ppp/2p1p3/3pP3/3P4/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 1 8",
    },
    {
        "name": "Tactical Pin and Skewer",
        "category": "middlegame",
        "fen": "2r1r1k1/p4p1p/1p4p1/2n5/5N1Q/P3PRP1/3q1PKP/8 b - - 0 27",
    },
    {
        "name": "Heavy Piece Infiltration",
        "category": "middlegame",
        "fen": "4r1k1/1p3pp1/p1q4p/8/6Q1/P7/1P4PP/K2R4 w - - 4 35",
    },
    {
        "name": "Rook & Pawn Endgame",
        "category": "endgame",
        "fen": "8/5pk1/1p1R4/p3r3/P1P5/1P6/5KP1/8 b - - 2 39",
    },
    {
        "name": "Knight vs Bishop Endgame",
        "category": "endgame",
        "fen": "8/7p/1pp1kp2/p2p2p1/P2Pn1P1/2P1K2P/1P6/4N3 b - - 1 36",
    },
    {
        "name": "Pawn Race Endgame",
        "category": "endgame",
        "fen": "8/8/4k3/1p1p4/pP1P1K2/P7/8/8 w - - 0 45",
    },
]


def run_benchmarks() -> Dict[str, Any]:
    print("=" * 60)
    print("PROJECT JANUS v0.60 — PRELIMINARY SEARCH EVALUATION")
    print("=" * 60)

    eng = NativeEngineBridge()

    # Define configurations
    configs = [
        {"id": "C1", "name": "C1_Classical_Control", "use_nnue": False, "blend": 0},
        {"id": "V1-A", "name": "V1-A_Pure_Neural", "use_nnue": True, "blend": 100},
        {"id": "V1-B", "name": "V1-B_Hybrid_Blend50", "use_nnue": True, "blend": 50},
    ]

    all_results = {}

    for cfg in configs:
        cfg_id = cfg["id"]
        cfg_name = cfg["name"]
        print(f"\nRunning Search Benchmark for Configuration: {cfg_id} ({cfg_name})...")

        fixed_depth_results = []
        fixed_time_results = []

        # Configure engine options
        eng.set_ordering_options(True, True)
        eng.set_pvs_options(False)
        eng.set_lmr_options(True, 3, 4, 1)
        eng.set_see_options(False, False)
        eng.set_neural_value_options(cfg["use_nnue"], str(MODEL_PATH), cfg["blend"])

        # 1. Fixed Depth 5
        for pos in BENCHMARK_POSITIONS:
            fen = pos["fen"]
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.set_fen(fen)

            t0 = time.perf_counter()
            bm, sc, d, n, elapsed, pv = eng.search(max_depth=5, time_limit=10.0)
            t1 = time.perf_counter()
            real_time = t1 - t0
            nps = n / max(0.0001, real_time)

            fixed_depth_results.append({
                "position": pos["name"],
                "category": pos["category"],
                "fen": fen,
                "best_move": bm,
                "score_cp": sc,
                "depth": d,
                "nodes": n,
                "elapsed_sec": real_time,
                "nps": nps,
                "pv": pv[:4],
            })

        # 2. Fixed Time 500ms
        for pos in BENCHMARK_POSITIONS:
            fen = pos["fen"]
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.set_fen(fen)

            t0 = time.perf_counter()
            bm, sc, d, n, elapsed, pv = eng.search(max_depth=30, time_limit=0.5)
            t1 = time.perf_counter()
            real_time = t1 - t0
            nps = n / max(0.0001, real_time)

            fixed_time_results.append({
                "position": pos["name"],
                "category": pos["category"],
                "fen": fen,
                "best_move": bm,
                "score_cp": sc,
                "completed_depth": d,
                "nodes": n,
                "elapsed_sec": real_time,
                "nps": nps,
                "pv": pv[:4],
            })

        # Summary statistics
        mean_d5_nodes = sum(r["nodes"] for r in fixed_depth_results) / len(fixed_depth_results)
        mean_d5_time = sum(r["elapsed_sec"] for r in fixed_depth_results) / len(fixed_depth_results)
        mean_d5_nps = sum(r["nps"] for r in fixed_depth_results) / len(fixed_depth_results)

        mean_ft_depth = sum(r["completed_depth"] for r in fixed_time_results) / len(fixed_time_results)
        mean_ft_nodes = sum(r["nodes"] for r in fixed_time_results) / len(fixed_time_results)
        mean_ft_nps = sum(r["nps"] for r in fixed_time_results) / len(fixed_time_results)

        print(f"  [Depth 5 Summary] Avg Nodes: {mean_d5_nodes:,.0f} | Avg Time: {mean_d5_time*1000:.1f} ms | Avg NPS: {mean_d5_nps:,.0f}")
        print(f"  [Fixed Time 500ms] Avg Depth: {mean_ft_depth:.1f} | Avg Nodes: {mean_ft_nodes:,.0f} | Avg NPS: {mean_ft_nps:,.0f}")

        all_results[cfg_id] = {
            "config": cfg,
            "depth5_summary": {
                "mean_nodes": mean_d5_nodes,
                "mean_time_sec": mean_d5_time,
                "mean_nps": mean_d5_nps,
            },
            "fixed_time_summary": {
                "mean_depth": mean_ft_depth,
                "mean_nodes": mean_ft_nodes,
                "mean_nps": mean_ft_nps,
            },
            "fixed_depth_positions": fixed_depth_results,
            "fixed_time_positions": fixed_time_results,
        }

    # Save telemetry JSON
    out_file = RAW_DIR / "preliminary_search_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 60)
    print("PRELIMINARY SEARCH EVALUATION COMPLETE")
    print(f"Results written to: {out_file}")
    print("=" * 60)
    return all_results


if __name__ == "__main__":
    run_benchmarks()
