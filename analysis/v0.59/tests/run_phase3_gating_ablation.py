"""Project Janus v0.59 - Phase 3 Neural Search Gating Experiment.

Evaluates 3 bounded neural search gating strategies across 50 validation positions:
- G1: Root-only (N8-A baseline behaviour, MaxPly=0, MinDepth=4)
- G2: Root plus selected internal nodes (MaxPly=2, MinDepth=4)
- G3: PV-selective integration (evaluated only along verified PV search path, MinDepth=4)

Evaluated under:
1. Fixed nominal depth: Depth 5 and Depth 6.
2. Fixed search time: 50 ms and 100 ms with bounded inference budgets (0.5%, 1.0%, 2.0% of search time).
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

VAL_CORPUS_PATH = ROOT / "analysis" / "v0.59" / "corpus" / "validation_corpus_50.json"
RAW_OUT = ROOT / "analysis" / "v0.59" / "raw" / "phase3_gating_ablation_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)


def run_phase3():
    with open(VAL_CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    eng = NativeEngineBridge()

    gating_configs = [
        {"id": "C0", "desc": "Classical Baseline C1", "mode": 0, "gating": 0, "max_ply": 0, "min_depth": 4},
        {"id": "G1", "desc": "Root-Only (N8-A)", "mode": 1, "gating": 0, "max_ply": 0, "min_depth": 4},
        {"id": "G2", "desc": "Root + Internal Nodes (ply<=2)", "mode": 1, "gating": 1, "max_ply": 2, "min_depth": 4},
        {"id": "G3", "desc": "PV-Selective Integration", "mode": 1, "gating": 2, "max_ply": 4, "min_depth": 4},
    ]

    fixed_depths = [5, 6]
    fixed_times = [0.050, 0.100] # 50ms, 100ms
    budgets_pct = [0.005, 0.010, 0.020] # 0.5%, 1.0%, 2.0%

    results = {
        "fixed_depth_results": [],
        "fixed_time_results": []
    }

    print("=" * 80)
    print("RUNNING PHASE 3 SEARCH GATING EXPERIMENT (50 positions)")
    print("=" * 80)

    # Part A: Fixed Depth Evaluation (Depths 5 and 6)
    print("\n--- Part A: Fixed Depth Gating Comparison (Depths 5, 6) ---")
    for idx, item in enumerate(corpus, 1):
        fen = item["fen"]
        pos_id = item["id"]
        pos_rec = {"id": pos_id, "fen": fen, "depths": {}}

        for d in fixed_depths:
            pos_rec["depths"][str(d)] = {}
            for cfg in gating_configs:
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

                order_telem = eng.get_ordering_telemetry()
                neural_telem = eng.get_neural_telemetry()

                pos_rec["depths"][str(d)][cfg["id"]] = {
                    "best_move": bm,
                    "score": sc,
                    "nodes": nodes,
                    "elapsed": dur,
                    "first_move_cutoff_rate": order_telem.get("first_move_cutoff_rate", 0.0),
                    "neural_evals": neural_telem.get("evaluations", 0),
                    "neural_time_us": neural_telem.get("inference_time_us", 0)
                }

        results["fixed_depth_results"].append(pos_rec)
        if idx % 10 == 0 or idx == len(corpus):
            print(f"  [Fixed Depth] Completed {idx:2d}/{len(corpus)} positions...")

    # Part B: Fixed Time Evaluation with Latency Budgets (50ms, 100ms)
    print("\n--- Part B: Fixed Time with Inference Budgets (50ms, 100ms) ---")
    for idx, item in enumerate(corpus, 1):
        fen = item["fen"]
        pos_id = item["id"]
        pos_rec = {"id": pos_id, "fen": fen, "times": {}}

        for t_limit in fixed_times:
            t_ms = int(t_limit * 1000)
            pos_rec["times"][str(t_ms)] = {}

            # 1. C0 Baseline
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.reset_ordering_telemetry()
            eng.reset_root_telemetry()
            eng.reset_neural_telemetry()
            eng.set_causal_policy_mode(0)
            eng.set_search_gating_mode(0)
            eng.set_neural_budget_us(0)
            eng.set_neural_policy_options(False)
            eng.set_fen(fen)
            bm_c0, sc_c0, d_c0, n_c0, el_c0, _ = eng.search(max_depth=30, time_limit=t_limit)
            c0_order = eng.get_ordering_telemetry()

            pos_rec["times"][str(t_ms)]["C0"] = {
                "best_move": bm_c0,
                "score": sc_c0,
                "depth": d_c0,
                "nodes": n_c0,
                "elapsed": el_c0,
                "first_move_cutoff_rate": c0_order.get("first_move_cutoff_rate", 0.0),
                "neural_evals": 0,
                "neural_time_us": 0
            }

            # 2. G1, G2, G3 under different budget caps
            for g_cfg in gating_configs[1:]:
                gid = g_cfg["id"]
                pos_rec["times"][str(t_ms)][gid] = {}
                for bpct in budgets_pct:
                    bcap_us = int(t_limit * 1_000_000 * bpct)
                    b_label = f"{bpct*100:.1f}pct"

                    eng.clear_tt()
                    eng.clear_killers()
                    eng.clear_history_heuristic()
                    eng.reset_ordering_telemetry()
                    eng.reset_root_telemetry()
                    eng.reset_neural_telemetry()

                    eng.set_causal_policy_mode(g_cfg["mode"])
                    eng.set_search_gating_mode(g_cfg["gating"])
                    eng.set_neural_budget_us(bcap_us)
                    eng.set_neural_policy_options(True, max_ply=g_cfg["max_ply"], min_depth=g_cfg["min_depth"], score_weight=50000)

                    eng.set_fen(fen)
                    bm, sc, d_reached, nodes, el, _ = eng.search(max_depth=30, time_limit=t_limit)
                    order_t = eng.get_ordering_telemetry()
                    neu_t = eng.get_neural_telemetry()

                    pos_rec["times"][str(t_ms)][gid][b_label] = {
                        "best_move": bm,
                        "score": sc,
                        "depth": d_reached,
                        "nodes": nodes,
                        "elapsed": el,
                        "first_move_cutoff_rate": order_t.get("first_move_cutoff_rate", 0.0),
                        "neural_evals": neu_t.get("evaluations", 0),
                        "neural_time_us": neu_t.get("inference_time_us", 0),
                        "budget_us": bcap_us
                    }

        results["fixed_time_results"].append(pos_rec)
        if idx % 10 == 0 or idx == len(corpus):
            print(f"  [Fixed Time] Completed {idx:2d}/{len(corpus)} positions...")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nPhase 3 raw results successfully written to {RAW_OUT}")
    return results


if __name__ == "__main__":
    run_phase3()

