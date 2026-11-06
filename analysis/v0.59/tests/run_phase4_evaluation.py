"""Project Janus v0.59 - Phase 4 Held-Out Evaluation Experiment.

Evaluates 4 configurations on the strictly held-out 50-position evaluation corpus:
- C1: Classical Baseline (Control)
- N8-A: Root-Only Policy (MaxPly=0, MinDepth=4)
- N8-B: Root + Internal Policy (MaxPly=2, MinDepth=4, budget 1.0%)
- N8-C: PV-Selective Policy (is_pv=true, MinDepth=4, budget 1.0%)

Evaluates under:
1. Fixed Depth: Depths 5 and 6
2. Fixed Time: 50 ms and 100 ms

Records:
- Nodes, Time, NPS, Cutoff Rate, Completed Depth, Best Move Agreement, Neural Latency, Phase Breakdown.
"""

import json
import time
import importlib.util
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.59" / "native" / "janus_native_bridge.py"
spec = importlib.util.spec_from_file_location("bridge_v59", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

EVAL_CORPUS_PATH = ROOT / "analysis" / "v0.59" / "corpus" / "evaluation_corpus_50.json"
RAW_OUT = ROOT / "analysis" / "v0.59" / "raw" / "phase4_evaluation_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)


def run_phase4():
    with open(EVAL_CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    eng = NativeEngineBridge()

    configs = [
        {"id": "C1", "name": "Classical Baseline C1", "mode": 0, "gating": 0, "max_ply": 0, "min_depth": 4, "budget_pct": 0.0},
        {"id": "N8-A", "name": "Neural Root-Only (N8-A)", "mode": 1, "gating": 0, "max_ply": 0, "min_depth": 4, "budget_pct": 0.01},
        {"id": "N8-B", "name": "Neural Root+Internal (N8-B)", "mode": 1, "gating": 1, "max_ply": 2, "min_depth": 4, "budget_pct": 0.01},
        {"id": "N8-C", "name": "Neural PV-Selective (N8-C)", "mode": 1, "gating": 2, "max_ply": 4, "min_depth": 4, "budget_pct": 0.01},
    ]

    fixed_depths = [5, 6]
    fixed_times = [0.050, 0.100] # 50ms, 100ms

    results = {
        "depth_runs": [],
        "time_runs": []
    }

    print("=" * 80)
    print("RUNNING PHASE 4 HELD-OUT EVALUATION (50 independent positions)")
    print("=" * 80)

    # 1. Fixed Depth Runs
    print("\n--- Part A: Held-Out Fixed Depth Runs (Depths 5, 6) ---")
    for idx, item in enumerate(corpus, 1):
        fen = item["fen"]
        pos_id = item["id"]
        phase = item["phase"]
        pos_rec = {"id": pos_id, "fen": fen, "phase": phase, "depths": {}}

        for d in fixed_depths:
            pos_rec["depths"][str(d)] = {}
            for cfg in configs:
                eng.clear_tt()
                eng.clear_killers()
                eng.clear_history_heuristic()
                eng.reset_ordering_telemetry()
                eng.reset_root_telemetry()
                eng.reset_neural_telemetry()

                eng.set_causal_policy_mode(cfg["mode"])
                eng.set_search_gating_mode(cfg["gating"])
                eng.set_neural_budget_us(0) # Unbounded for depth tests
                if cfg["mode"] != 0:
                    eng.set_neural_policy_options(True, max_ply=cfg["max_ply"], min_depth=cfg["min_depth"], score_weight=50000)
                else:
                    eng.set_neural_policy_options(False)

                eng.set_fen(fen)
                t0 = time.perf_counter()
                bm, sc, depth, nodes, el, _ = eng.search(max_depth=d, time_limit=10.0)
                dur = time.perf_counter() - t0

                order_t = eng.get_ordering_telemetry()
                neu_t = eng.get_neural_telemetry()

                pos_rec["depths"][str(d)][cfg["id"]] = {
                    "best_move": bm,
                    "score": sc,
                    "nodes": nodes,
                    "elapsed": dur,
                    "first_move_cutoff_rate": order_t.get("first_move_cutoff_rate", 0.0),
                    "neural_evals": neu_t.get("evaluations", 0),
                    "neural_time_us": neu_t.get("inference_time_us", 0)
                }

        results["depth_runs"].append(pos_rec)
        if idx % 10 == 0 or idx == len(corpus):
            print(f"  [Held-Out Depth] Processed {idx:2d}/{len(corpus)} positions...")

    # 2. Fixed Time Runs
    print("\n--- Part B: Held-Out Fixed Time Runs (50ms, 100ms) ---")
    for idx, item in enumerate(corpus, 1):
        fen = item["fen"]
        pos_id = item["id"]
        phase = item["phase"]
        pos_rec = {"id": pos_id, "fen": fen, "phase": phase, "times": {}}

        for t_limit in fixed_times:
            t_ms = int(t_limit * 1000)
            pos_rec["times"][str(t_ms)] = {}

            for cfg in configs:
                bcap_us = int(t_limit * 1_000_000 * cfg["budget_pct"])

                eng.clear_tt()
                eng.clear_killers()
                eng.clear_history_heuristic()
                eng.reset_ordering_telemetry()
                eng.reset_root_telemetry()
                eng.reset_neural_telemetry()

                eng.set_causal_policy_mode(cfg["mode"])
                eng.set_search_gating_mode(cfg["gating"])
                eng.set_neural_budget_us(bcap_us)
                if cfg["mode"] != 0:
                    eng.set_neural_policy_options(True, max_ply=cfg["max_ply"], min_depth=cfg["min_depth"], score_weight=50000)
                else:
                    eng.set_neural_policy_options(False)

                eng.set_fen(fen)
                t0 = time.perf_counter()
                bm, sc, d_reached, nodes, el, _ = eng.search(max_depth=30, time_limit=t_limit)
                dur = time.perf_counter() - t0

                order_t = eng.get_ordering_telemetry()
                neu_t = eng.get_neural_telemetry()

                pos_rec["times"][str(t_ms)][cfg["id"]] = {
                    "best_move": bm,
                    "score": sc,
                    "depth": d_reached,
                    "nodes": nodes,
                    "elapsed": dur,
                    "first_move_cutoff_rate": order_t.get("first_move_cutoff_rate", 0.0),
                    "neural_evals": neu_t.get("evaluations", 0),
                    "neural_time_us": neu_t.get("inference_time_us", 0)
                }

        results["time_runs"].append(pos_rec)
        if idx % 10 == 0 or idx == len(corpus):
            print(f"  [Held-Out Time] Processed {idx:2d}/{len(corpus)} positions...")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nPhase 4 held-out raw results written to {RAW_OUT}")
    return results


if __name__ == "__main__":
    run_phase4()

