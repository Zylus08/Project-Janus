"""Project Janus v0.59 - Phase 1 Neural Ordering Influence Experiment.

Instruments search move ordering across 50 validation positions at depths 4, 5, and 6.
Measures:
1. Root legal move count distribution.
2. Classical vs neural rank correlation (Spearman rank correlation).
3. Neural top-1 vs classical top-1 agreement and disagreement.
4. How often neural top move is actually searched first vs overridden (by TT move, capture, killer).
5. For disagreements, which heuristic matches the eventual PV move.
6. Eventual PV move rank in neural and classical ordering (Top-1, Top-3).
7. Fraction of root moves reordered by neural policy.
8. First-move beta-cutoff rate and total nodes searched across depths 4, 5, 6.
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
RAW_OUT = ROOT / "analysis" / "v0.59" / "raw" / "phase1_influence_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)


def run_phase1():
    with open(VAL_CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    eng = NativeEngineBridge()
    target_depths = [4, 5, 6]

    results = {
        "depths": target_depths,
        "positions_count": len(corpus),
        "data": []
    }

    print("=" * 80)
    print(f"RUNNING PHASE 1 INFLUENCE INSTRUMENTATION (50 positions, depths {target_depths})")
    print("=" * 80)

    for idx, item in enumerate(corpus, 1):
        pos_id = item["id"]
        fen = item["fen"]
        phase = item["phase"]

        pos_record = {
            "id": pos_id,
            "fen": fen,
            "phase": phase,
            "c1_baseline": {},
            "n8_candidate": {}
        }

        for d in target_depths:
            # 1. Classical Baseline C1 (causal_policy_mode=0, neural disabled)
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.reset_ordering_telemetry()
            eng.reset_root_telemetry()
            eng.set_causal_policy_mode(0)
            eng.set_search_gating_mode(0)
            eng.set_fen(fen)

            t0 = time.perf_counter()
            bm_c1, sc_c1, depth_c1, nodes_c1, el_c1, _ = eng.search(max_depth=d, time_limit=10.0)
            dur_c1 = time.perf_counter() - t0
            c1_telem = eng.get_root_telemetry(d)
            c1_ordering = eng.get_ordering_telemetry()

            # 2. Candidate N8-A (causal_policy_mode=1, root gating)
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.reset_ordering_telemetry()
            eng.reset_root_telemetry()
            eng.reset_neural_telemetry()
            eng.set_causal_policy_mode(1)
            eng.set_search_gating_mode(0)
            eng.set_neural_policy_options(True, max_ply=0, min_depth=4, score_weight=50000)
            eng.set_fen(fen)

            t0 = time.perf_counter()
            bm_n8, sc_n8, depth_n8, nodes_n8, el_n8, _ = eng.search(max_depth=d, time_limit=10.0)
            dur_n8 = time.perf_counter() - t0
            n8_telem = eng.get_root_telemetry(d)
            n8_ordering = eng.get_ordering_telemetry()
            neural_telem = eng.get_neural_telemetry()

            pos_record["c1_baseline"][str(d)] = {
                "best_move": bm_c1,
                "score": sc_c1,
                "depth": depth_c1,
                "nodes": nodes_c1,
                "elapsed": dur_c1,
                "root_telemetry": c1_telem,
                "ordering_telemetry": c1_ordering
            }

            pos_record["n8_candidate"][str(d)] = {
                "best_move": bm_n8,
                "score": sc_n8,
                "depth": depth_n8,
                "nodes": nodes_n8,
                "elapsed": dur_n8,
                "root_telemetry": n8_telem,
                "ordering_telemetry": n8_ordering,
                "neural_telemetry": neural_telem
            }

        results["data"].append(pos_record)
        if idx % 10 == 0 or idx == len(corpus):
            print(f"  Processed {idx:2d}/{len(corpus)} positions...")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nRaw results successfully written to {RAW_OUT}")
    return results


if __name__ == "__main__":
    run_phase1()

