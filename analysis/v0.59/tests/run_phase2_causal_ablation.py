"""Project Janus v0.59 - Phase 2 Causal Policy Control Experiments.

Evaluates 4 policy-ordering conditions across 50 validation positions at depths 4, 5, 6:
- C0: Classical C1 baseline (Frozen control)
- C1: Trained MicroPolicyNet (Learned chess information)
- C2: Random Policy Ordering (Deterministic PRNG perturbation control, seed=42)
- C3: Shuffled Neural Logits (Preserves logit/score distribution, destroys move semantics, seed=42)
"""

import json
import time
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.59" / "native" / "janus_native_bridge.py"
spec = importlib.util.spec_from_file_location("bridge_v59", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

VAL_CORPUS_PATH = ROOT / "analysis" / "v0.59" / "corpus" / "validation_corpus_50.json"
RAW_OUT = ROOT / "analysis" / "v0.59" / "raw" / "phase2_causal_ablation_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)


def run_phase2():
    with open(VAL_CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    eng = NativeEngineBridge()
    target_depths = [4, 5, 6]
    conditions = [
        {"id": "C0", "mode": 0, "desc": "Classical C1 Baseline"},
        {"id": "C1", "mode": 1, "desc": "Trained MicroPolicyNet"},
        {"id": "C2", "mode": 2, "desc": "Random Policy Ordering"},
        {"id": "C3", "mode": 3, "desc": "Shuffled Neural Logits"}
    ]

    results = {
        "depths": target_depths,
        "conditions": conditions,
        "positions_count": len(corpus),
        "data": []
    }

    print("=" * 80)
    print(f"RUNNING PHASE 2 CAUSAL CONTROL EXPERIMENTS (50 positions, depths {target_depths})")
    print("=" * 80)

    for idx, item in enumerate(corpus, 1):
        pos_id = item["id"]
        fen = item["fen"]
        phase = item["phase"]

        pos_record = {
            "id": pos_id,
            "fen": fen,
            "phase": phase,
            "runs": {}
        }

        for cond in conditions:
            c_id = cond["id"]
            c_mode = cond["mode"]
            pos_record["runs"][c_id] = {}

            for d in target_depths:
                eng.clear_tt()
                eng.clear_killers()
                eng.clear_history_heuristic()
                eng.reset_ordering_telemetry()
                eng.reset_root_telemetry()
                eng.reset_neural_telemetry()

                eng.set_causal_policy_mode(c_mode)
                eng.set_search_gating_mode(0) # Root gating
                eng.set_deterministic_seed(42)
                if c_mode != 0:
                    eng.set_neural_policy_options(True, max_ply=0, min_depth=4, score_weight=50000)
                else:
                    eng.set_neural_policy_options(False)

                eng.set_fen(fen)
                t0 = time.perf_counter()
                bm, sc, depth, nodes, el, _ = eng.search(max_depth=d, time_limit=10.0)
                dur = time.perf_counter() - t0

                root_telem = eng.get_root_telemetry(d)
                order_telem = eng.get_ordering_telemetry()
                neural_telem = eng.get_neural_telemetry()

                pos_record["runs"][c_id][str(d)] = {
                    "best_move": bm,
                    "score": sc,
                    "depth": depth,
                    "nodes": nodes,
                    "elapsed": dur,
                    "first_move_cutoff_rate": order_telem.get("first_move_cutoff_rate", 0.0),
                    "total_cutoffs": order_telem.get("total_cutoffs", 0),
                    "move1_cutoffs": order_telem.get("cutoff_move_1", 0),
                    "spearman_correlation": root_telem.get("spearman_correlation", 0.0),
                    "moves_reordered": root_telem.get("moves_reordered_count", 0),
                    "neural_evals": neural_telem.get("evaluations", 0),
                    "neural_time_us": neural_telem.get("inference_time_us", 0)
                }

        results["data"].append(pos_record)
        if idx % 10 == 0 or idx == len(corpus):
            print(f"  Completed {idx:2d}/{len(corpus)} positions across 4 conditions...")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nRaw results successfully saved to {RAW_OUT}")
    return results


if __name__ == "__main__":
    run_phase2()

