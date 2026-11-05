"""Project Janus v0.54 - Fixed-Depth 4-Way Ordering Ablation Benchmark.

Evaluates 4 configurations across Depths 3, 4, 5, 6 on:
- 37 Diagnostic corpus positions
- 16 Validation corpus positions
Total: 53 positions.

Configurations:
1. C0: UseKiller=False, UseHistory=False (Production N3 Control)
2. C1: UseKiller=True,  UseHistory=False (Killer Only)
3. C2: UseKiller=False, UseHistory=True  (History Only)
4. C3: UseKiller=True,  UseHistory=True  (Combined N5 Candidate)

Measures:
- Total nodes, node reduction percentage
- Wall-clock search duration, speedup factor
- Effective NPS
- Move agreement percentage (vs C0)
- Ordering telemetry: total cutoffs, first-move cutoffs, first-move cutoff rate, mean cutoff index
- Killer cutoffs (Killer 1 & Killer 2)
- History cutoffs
- LMR telemetry: reduced moves, re-searches, cutoffs
"""

import json
import time
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.54" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v54", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.54" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.54" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def load_all_positions():
    positions = []
    # 1. Diagnostic corpus (37 positions)
    with open(CORPUS_DIR / "diagnostic_corpus.json", "r", encoding="utf-8") as f:
        diag = json.load(f)
        for item in diag:
            positions.append({"id": item["id"], "fen": item["fen"], "source": "diagnostic"})

    # 2. Validation corpus (16 positions)
    with open(CORPUS_DIR / "validation_corpus.json", "r", encoding="utf-8") as f:
        val = json.load(f)
        for item in val:
            positions.append({"id": item["id"], "fen": item["fen"], "source": "validation"})

    return positions


def run_depth_ablation():
    positions = load_all_positions()
    depths = [3, 4, 5, 6]
    bridge = NativeEngineBridge()

    configs = [
        ("c0", False, False),
        ("c1", True, False),
        ("c2", False, True),
        ("c3", True, True),
    ]

    results_by_depth = {}

    print(f"Loaded {len(positions)} positions (37 diagnostic + 16 validation).")
    print("Beginning 4-Way Fixed-Depth Ablation across Depths 3, 4, 5, 6...\n")

    for depth in depths:
        print(f"=== Running Depth {depth} ===")
        t_depth_start = time.perf_counter()
        depth_data = []

        total_nodes = {cfg[0]: 0 for cfg in configs}
        total_time = {cfg[0]: 0.0 for cfg in configs}
        agreed_vs_c0 = {cfg[0]: 0 for cfg in configs}

        telemetry_totals = {
            cfg[0]: {
                "total_cutoffs": 0,
                "cutoff_move_1": 0,
                "cutoff_move_2": 0,
                "cutoff_move_3": 0,
                "cutoff_move_4plus": 0,
                "cutoff_tt": 0,
                "cutoff_killer1": 0,
                "cutoff_killer2": 0,
                "cutoff_history": 0,
                "cutoff_captures": 0,
                "cutoff_quiet": 0,
                "sum_cutoff_index": 0,
            }
            for cfg in configs
        }

        lmr_totals = {
            cfg[0]: {"reduced_moves": 0, "researches": 0, "cutoffs": 0}
            for cfg in configs
        }

        for i, pos in enumerate(positions):
            fen = pos["fen"]
            pos_id = pos["id"]
            pos_entry = {"id": pos_id, "fen": fen, "configs": {}}

            c0_move = None

            for cfg_id, use_k, use_h in configs:
                bridge.clear_tt()
                bridge.clear_killers()
                bridge.clear_history_heuristic()
                bridge.reset_history()
                bridge.reset_ordering_telemetry()
                bridge.reset_lmr_telemetry()
                bridge.reset_pvs_telemetry()
                bridge.set_pvs_options(False)
                bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
                bridge.set_ordering_options(use_k, use_h)
                bridge.set_fen(fen)

                t0 = time.perf_counter()
                mv, sc, dp, nd, el, pv = bridge.search(max_depth=depth, time_limit=30.0)
                elapsed = time.perf_counter() - t0

                ord_telem = bridge.get_ordering_telemetry()
                lmr_telem = bridge.get_lmr_telemetry()

                if cfg_id == "c0":
                    c0_move = mv

                if mv == c0_move:
                    agreed_vs_c0[cfg_id] += 1

                total_nodes[cfg_id] += nd
                total_time[cfg_id] += elapsed

                for k in ["total_cutoffs", "cutoff_move_1", "cutoff_move_2", "cutoff_move_3",
                          "cutoff_move_4plus", "cutoff_tt", "cutoff_killer1", "cutoff_killer2",
                          "cutoff_history", "cutoff_captures", "cutoff_quiet"]:
                    telemetry_totals[cfg_id][k] += ord_telem.get(k, 0)
                telemetry_totals[cfg_id]["sum_cutoff_index"] += int(ord_telem.get("mean_cutoff_index", 0.0) * ord_telem.get("total_cutoffs", 0))

                for k in ["reduced_moves", "researches", "cutoffs"]:
                    lmr_totals[cfg_id][k] += lmr_telem[k]

                pos_entry["configs"][cfg_id] = {
                    "move": mv,
                    "score": sc,
                    "nodes": nd,
                    "time_sec": elapsed,
                    "telemetry": ord_telem,
                    "lmr_telemetry": lmr_telem,
                }

            depth_data.append(pos_entry)

            if (i + 1) % 15 == 0 or (i + 1) == len(positions):
                print(f"  Processed {i+1}/{len(positions)} positions...")

        # Compute summary stats
        summary = {
            "depth": depth,
            "positions_count": len(positions),
            "total_nodes": total_nodes,
            "total_time_sec": total_time,
            "node_reduction_pct_vs_c0": {
                k: ((total_nodes["c0"] - total_nodes[k]) / total_nodes["c0"] * 100.0) if total_nodes["c0"] > 0 else 0.0
                for k in total_nodes
            },
            "speedup_vs_c0": {
                k: (total_time["c0"] / total_time[k]) if total_time[k] > 0 else 1.0
                for k in total_time
            },
            "agreement_pct_vs_c0": {
                k: (agreed_vs_c0[k] / len(positions) * 100.0)
                for k in agreed_vs_c0
            },
            "nps": {
                k: int(total_nodes[k] / total_time[k]) if total_time[k] > 0 else 0
                for k in total_nodes
            },
            "ordering_telemetry": telemetry_totals,
            "lmr_telemetry": lmr_totals,
        }

        # Calculate first-move cutoff rate and mean cutoff index
        for k in configs:
            cid = k[0]
            tot_cut = telemetry_totals[cid]["total_cutoffs"]
            sum_idx = telemetry_totals[cid]["sum_cutoff_index"]
            cut_1 = telemetry_totals[cid]["cutoff_move_1"]
            telemetry_totals[cid]["first_move_cutoff_rate_pct"] = (cut_1 / tot_cut * 100.0) if tot_cut > 0 else 0.0
            telemetry_totals[cid]["mean_cutoff_index"] = (sum_idx / tot_cut) if tot_cut > 0 else 0.0

        results_by_depth[str(depth)] = {
            "summary": summary,
            "positions": depth_data,
        }

        elapsed_depth = time.perf_counter() - t_depth_start
        print(f"\nDepth {depth} Completed in {elapsed_depth:.2f}s:")
        print(f"  Nodes: C0={total_nodes['c0']:,} | C1={total_nodes['c1']:,} (-{summary['node_reduction_pct_vs_c0']['c1']:.2f}%)")
        print(f"         C2={total_nodes['c2']:,} (-{summary['node_reduction_pct_vs_c0']['c2']:.2f}%) | C3={total_nodes['c3']:,} (-{summary['node_reduction_pct_vs_c0']['c3']:.2f}%)")
        print(f"  Time:  C0={total_time['c0']:.3f}s vs C3={total_time['c3']:.3f}s (Speedup: {summary['speedup_vs_c0']['c3']:.2f}x)")
        print(f"  Agreement C3 vs C0: {agreed_vs_c0['c3']}/{len(positions)} ({summary['agreement_pct_vs_c0']['c3']:.1f}%)")
        print(f"  1st Move Cutoff Rate: C0={telemetry_totals['c0']['first_move_cutoff_rate_pct']:.1f}% vs C3={telemetry_totals['c3']['first_move_cutoff_rate_pct']:.1f}%\n")

    out_file = RAW_DIR / "depth_ablation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_by_depth, f, indent=2)

    print(f"Saved complete fixed-depth ablation data to {out_file}")
    return results_by_depth


if __name__ == "__main__":
    run_depth_ablation()

