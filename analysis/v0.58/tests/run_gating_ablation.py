"""Project Janus v0.58 - Search Gating Ablation Benchmark.

Compares 4 configurations:
- C1: Baseline Classical Control (Neural OFF)
- N8-A: Root-Only Policy Ordering (UseNeuralPolicyOrdering=true, MaxPly=0, MinDepth=4)
- N8-B: Root + Shallow Internal (UseNeuralPolicyOrdering=true, MaxPly=2, MinDepth=4)
- N8-C: Selective High-Depth (UseNeuralPolicyOrdering=true, MaxPly=2, MinDepth=6)

Evaluates on the 16 validation corpus positions across Depth 5 and Depth 6.
Collects tree compression, latency overhead, neural forward pass counts, and cutoff efficiency.
"""

from __future__ import annotations

import json
import time
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.58" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v58", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

VALIDATION_CORPUS = ROOT / "analysis" / "v0.56" / "corpus" / "validation_corpus.json"
RAW_DIR = ROOT / "analysis" / "v0.58" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def load_validation_positions():
    with open(VALIDATION_CORPUS, "r", encoding="utf-8") as f:
        return json.load(f)


def run_gating_ablation():
    positions = load_validation_positions()
    print(f"Loaded {len(positions)} validation positions for search gating ablation.")

    configs = [
        {"id": "C1", "name": "Classical Baseline (Neural OFF)", "use_policy": False, "max_ply": 0, "min_depth": 4},
        {"id": "N8-A", "name": "Root-Only Policy", "use_policy": True, "max_ply": 0, "min_depth": 4},
        {"id": "N8-B", "name": "Root + Shallow Internal", "use_policy": True, "max_ply": 2, "min_depth": 4},
        {"id": "N8-C", "name": "Selective High-Depth", "use_policy": True, "max_ply": 2, "min_depth": 6},
    ]

    depths = [5, 6]
    results = {
        "positions_count": len(positions),
        "depths": depths,
        "configs": {c["id"]: c for c in configs},
        "per_position": [],
        "aggregates": {},
    }

    eng = NativeEngineBridge()

    for pos_idx, pos in enumerate(positions, 1):
        pos_id = pos["id"]
        fen = pos["fen"]
        desc = pos.get("desc", pos_id)
        print(f"\n[{pos_idx}/{len(positions)}] Position: {pos_id} - {desc}")

        pos_record = {
            "id": pos_id,
            "fen": fen,
            "desc": desc,
            "depth_results": {},
        }

        for d in depths:
            pos_record["depth_results"][str(d)] = {}

            for cfg in configs:
                cfg_id = cfg["id"]

                # Configure engine
                eng.clear_tt()
                eng.clear_killers()
                eng.clear_history_heuristic()
                eng.reset_ordering_telemetry()
                eng.reset_neural_telemetry()
                eng.set_fen(fen)

                eng.set_neural_policy_options(
                    use_policy=cfg["use_policy"],
                    max_ply=cfg["max_ply"],
                    min_depth=cfg["min_depth"],
                )

                t0 = time.perf_counter()
                best_mv, score, depth, nodes, elapsed, pv = eng.search(max_depth=d, time_limit=60.0)
                wall_ms = (time.perf_counter() - t0) * 1000.0

                neural_telem = eng.get_neural_telemetry()
                order_telem = eng.get_ordering_telemetry()

                rec = {
                    "best_move": best_mv,
                    "score": score,
                    "depth": depth,
                    "nodes": nodes,
                    "wall_ms": round(wall_ms, 2),
                    "nps": int(nodes / (wall_ms / 1000.0)) if wall_ms > 0 else 0,
                    "pv": pv,
                    "neural_evals": neural_telem["evaluations"],
                    "neural_moves_scored": neural_telem["moves_scored"],
                    "neural_time_us": neural_telem["inference_time_us"],
                    "first_move_cutoff_rate": round(order_telem["first_move_cutoff_rate"], 2),
                    "mean_cutoff_index": round(order_telem["mean_cutoff_index"], 3),
                    "total_cutoffs": order_telem["total_cutoffs"],
                }

                pos_record["depth_results"][str(d)][cfg_id] = rec
                print(f"  d={d} | {cfg_id:4s} | Nodes: {nodes:6d} | Wall: {wall_ms:6.1f}ms | Neural Evals: {neural_telem['evaluations']:3d} ({neural_telem['inference_time_us']/1000.0:4.1f}ms) | BM: {best_mv}")

        results["per_position"].append(pos_record)

    # Compute aggregates across all positions for each depth and config
    for d in depths:
        d_str = str(d)
        results["aggregates"][d_str] = {}

        # Use C1 as base
        c1_total_nodes = sum(p["depth_results"][d_str]["C1"]["nodes"] for p in results["per_position"])
        c1_total_time = sum(p["depth_results"][d_str]["C1"]["wall_ms"] for p in results["per_position"])

        for cfg in configs:
            cfg_id = cfg["id"]
            tot_nodes = sum(p["depth_results"][d_str][cfg_id]["nodes"] for p in results["per_position"])
            tot_time = sum(p["depth_results"][d_str][cfg_id]["wall_ms"] for p in results["per_position"])
            tot_evals = sum(p["depth_results"][d_str][cfg_id]["neural_evals"] for p in results["per_position"])
            tot_neural_us = sum(p["depth_results"][d_str][cfg_id]["neural_time_us"] for p in results["per_position"])
            
            # Move agreement with C1
            bm_agreements = sum(
                1 for p in results["per_position"]
                if p["depth_results"][d_str][cfg_id]["best_move"] == p["depth_results"][d_str]["C1"]["best_move"]
            )

            node_ratio = tot_nodes / c1_total_nodes if c1_total_nodes > 0 else 1.0
            time_ratio = tot_time / c1_total_time if c1_total_time > 0 else 1.0

            agg = {
                "total_nodes": tot_nodes,
                "node_reduction_pct": round((1.0 - node_ratio) * 100.0, 2),
                "total_time_ms": round(tot_time, 1),
                "time_overhead_pct": round((time_ratio - 1.0) * 100.0, 2),
                "total_neural_evals": tot_evals,
                "total_neural_time_ms": round(tot_neural_us / 1000.0, 1),
                "avg_neural_time_per_pos_ms": round((tot_neural_us / 1000.0) / len(positions), 2),
                "c1_bm_agreement_pct": round(bm_agreements / len(positions) * 100.0, 1),
            }
            results["aggregates"][d_str][cfg_id] = agg

    # Print summary table
    print("\n" + "="*80)
    print("SEARCH GATING ABLATION SUMMARY")
    print("="*80)
    for d in depths:
        d_str = str(d)
        print(f"\n--- Depth {d} Aggregates ({len(positions)} positions) ---")
        print(f"{'Config':8s} | {'Nodes':10s} | {'Node Red %':10s} | {'Time (ms)':10s} | {'Time Overhead':13s} | {'Neural Evals':12s} | {'Neural Time':11s} | {'C1 Agr %':8s}")
        print("-" * 95)
        for cfg in configs:
            cid = cfg["id"]
            a = results["aggregates"][d_str][cid]
            print(f"{cid:8s} | {a['total_nodes']:10d} | {a['node_reduction_pct']:+9.2f}% | {a['total_time_ms']:10.1f} | {a['time_overhead_pct']:+12.2f}% | {a['total_neural_evals']:12d} | {a['total_neural_time_ms']:9.1f}ms | {a['c1_bm_agreement_pct']:7.1f}%")

    out_path = RAW_DIR / "gating_ablation_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved gating ablation results to {out_path}")


if __name__ == "__main__":
    run_gating_ablation()
