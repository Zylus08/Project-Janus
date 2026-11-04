"""Project Janus v0.53 - Fixed-Depth PVS & LMR Ablation Benchmark.

Evaluates 4 configurations across Depths 3, 4, 5, 6 on:
- 37 Diagnostic corpus positions
- 16 Validation corpus positions
Total: 53 positions.

Configurations:
1. N2:        UsePVS=False, UseLMR=False  (Baseline N2)
2. N2_PVS:    UsePVS=True,  UseLMR=False  (Isolated PVS effect)
3. N3:        UsePVS=False, UseLMR=True   (Production N3 baseline)
4. N4:        UsePVS=True,  UseLMR=True   (Candidate N4)

Measures:
- Total nodes, node reduction percentage
- Wall-clock search duration, speedup factor
- NPS throughput
- Move agreement percentage (N4 vs N3, N2_PVS vs N2)
- PVS telemetry: full-window, null-window, re-searches, cutoffs
- LMR telemetry: reduced moves, re-searches, cutoffs
"""

import json
import time
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.53" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v53", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.53" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.53" / "raw"
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

    results_by_depth = {}

    print(f"Loaded {len(positions)} positions (37 diagnostic + 16 validation).")
    print("Beginning 4-Way Fixed-Depth Ablation across Depths 3, 4, 5, 6...\n")

    for depth in depths:
        print(f"=== Running Depth {depth} ===")
        t_depth_start = time.perf_counter()
        depth_data = []

        total_nodes = {"n2": 0, "n2_pvs": 0, "n3": 0, "n4": 0}
        total_time = {"n2": 0.0, "n2_pvs": 0.0, "n3": 0.0, "n4": 0.0}
        agreed_n4_n3 = 0
        agreed_n2pvs_n2 = 0

        pvs_telem_totals = {
            "n2_pvs": {"full_window": 0, "null_window": 0, "researches": 0, "cutoffs": 0},
            "n4": {"full_window": 0, "null_window": 0, "researches": 0, "cutoffs": 0},
        }

        lmr_telem_totals = {
            "n3": {"reduced_moves": 0, "researches": 0, "cutoffs": 0},
            "n4": {"reduced_moves": 0, "researches": 0, "cutoffs": 0},
        }

        for i, pos in enumerate(positions):
            fen = pos["fen"]
            pos_id = pos["id"]

            # Config 1: N2 (UsePVS=False, UseLMR=False)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(False)
            bridge.set_lmr_options(False)
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            mv_n2, sc_n2, dp_n2, nd_n2, el_n2, pv_n2 = bridge.search(max_depth=depth, time_limit=30.0)
            t_n2 = time.perf_counter() - t0

            # Config 2: N2+PVS (UsePVS=True, UseLMR=False)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(True)
            bridge.set_lmr_options(False)
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            mv_n2pvs, sc_n2pvs, dp_n2pvs, nd_n2pvs, el_n2pvs, pv_n2pvs = bridge.search(max_depth=depth, time_limit=30.0)
            t_n2pvs = time.perf_counter() - t0
            pvs_telem_n2pvs = bridge.get_pvs_telemetry()

            # Config 3: N3 (UsePVS=False, UseLMR=True)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(False)
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            mv_n3, sc_n3, dp_n3, nd_n3, el_n3, pv_n3 = bridge.search(max_depth=depth, time_limit=30.0)
            t_n3 = time.perf_counter() - t0
            lmr_telem_n3 = bridge.get_lmr_telemetry()

            # Config 4: N4 (UsePVS=True, UseLMR=True)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(True)
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            mv_n4, sc_n4, dp_n4, nd_n4, el_n4, pv_n4 = bridge.search(max_depth=depth, time_limit=30.0)
            t_n4 = time.perf_counter() - t0
            pvs_telem_n4 = bridge.get_pvs_telemetry()
            lmr_telem_n4 = bridge.get_lmr_telemetry()

            if mv_n4 == mv_n3:
                agreed_n4_n3 += 1
            if mv_n2pvs == mv_n2:
                agreed_n2pvs_n2 += 1

            total_nodes["n2"] += nd_n2
            total_nodes["n2_pvs"] += nd_n2pvs
            total_nodes["n3"] += nd_n3
            total_nodes["n4"] += nd_n4

            total_time["n2"] += t_n2
            total_time["n2_pvs"] += t_n2pvs
            total_time["n3"] += t_n3
            total_time["n4"] += t_n4

            for k in ["full_window_searches", "null_window_searches", "researches", "cutoffs"]:
                pvs_telem_totals["n2_pvs"][k.replace("_searches", "")] = pvs_telem_totals["n2_pvs"].get(k.replace("_searches", ""), 0) + pvs_telem_n2pvs[k]
                pvs_telem_totals["n4"][k.replace("_searches", "")] = pvs_telem_totals["n4"].get(k.replace("_searches", ""), 0) + pvs_telem_n4[k]

            for k in ["reduced_moves", "researches", "cutoffs"]:
                lmr_telem_totals["n3"][k] += lmr_telem_n3[k]
                lmr_telem_totals["n4"][k] += lmr_telem_n4[k]

            depth_data.append({
                "id": pos_id,
                "fen": fen,
                "n2": {"move": mv_n2, "score": sc_n2, "nodes": nd_n2, "time": t_n2},
                "n2_pvs": {"move": mv_n2pvs, "score": sc_n2pvs, "nodes": nd_n2pvs, "time": t_n2pvs, "pvs_telem": pvs_telem_n2pvs},
                "n3": {"move": mv_n3, "score": sc_n3, "nodes": nd_n3, "time": t_n3, "lmr_telem": lmr_telem_n3},
                "n4": {"move": mv_n4, "score": sc_n4, "nodes": nd_n4, "time": t_n4, "pvs_telem": pvs_telem_n4, "lmr_telem": lmr_telem_n4},
                "agreed_n4_n3": (mv_n4 == mv_n3),
                "agreed_n2pvs_n2": (mv_n2pvs == mv_n2),
            })

            if (i + 1) % 15 == 0 or (i + 1) == len(positions):
                print(f"  Processed {i+1}/{len(positions)} positions...")

        # Calculate metrics
        node_red_pure_pvs = ((total_nodes["n2"] - total_nodes["n2_pvs"]) / total_nodes["n2"] * 100.0) if total_nodes["n2"] > 0 else 0.0
        node_red_n4_vs_n3 = ((total_nodes["n3"] - total_nodes["n4"]) / total_nodes["n3"] * 100.0) if total_nodes["n3"] > 0 else 0.0
        node_red_n4_vs_n2 = ((total_nodes["n2"] - total_nodes["n4"]) / total_nodes["n2"] * 100.0) if total_nodes["n2"] > 0 else 0.0

        speedup_n4_vs_n3 = (total_time["n3"] / total_time["n4"]) if total_time["n4"] > 0 else 1.0
        speedup_n4_vs_n2 = (total_time["n2"] / total_time["n4"]) if total_time["n4"] > 0 else 1.0

        nps = {k: int(total_nodes[k] / total_time[k]) if total_time[k] > 0 else 0 for k in total_nodes}

        summary = {
            "depth": depth,
            "positions_count": len(positions),
            "total_nodes": total_nodes,
            "total_time_sec": total_time,
            "nps": nps,
            "node_reduction_pct_n2pvs_vs_n2": node_red_pure_pvs,
            "node_reduction_pct_n4_vs_n3": node_red_n4_vs_n3,
            "node_reduction_pct_n4_vs_n2": node_red_n4_vs_n2,
            "speedup_n4_vs_n3": speedup_n4_vs_n3,
            "speedup_n4_vs_n2": speedup_n4_vs_n2,
            "agreement_n4_n3_pct": (agreed_n4_n3 / len(positions) * 100.0),
            "agreement_n2pvs_n2_pct": (agreed_n2pvs_n2 / len(positions) * 100.0),
            "pvs_telemetry": pvs_telem_totals,
            "lmr_telemetry": lmr_telem_totals,
        }

        results_by_depth[str(depth)] = {
            "summary": summary,
            "positions": depth_data,
        }

        elapsed_depth = time.perf_counter() - t_depth_start
        print(f"Depth {depth} Completed in {elapsed_depth:.2f}s:")
        print(f"  Nodes: N2={total_nodes['n2']:,} | N2+PVS={total_nodes['n2_pvs']:,} (-{node_red_pure_pvs:.2f}%)")
        print(f"  Nodes: N3={total_nodes['n3']:,} | N4={total_nodes['n4']:,} (-{node_red_n4_vs_n3:.2f}%)")
        print(f"  Overall N4 vs N2 reduction: -{node_red_n4_vs_n2:.2f}%")
        print(f"  Time:  N3={total_time['n3']:.3f}s vs N4={total_time['n4']:.3f}s (Speedup: {speedup_n4_vs_n3:.2f}x)")
        print(f"  Agreement: N4 vs N3 = {agreed_n4_n3}/{len(positions)} ({summary['agreement_n4_n3_pct']:.1f}%) | N2+PVS vs N2 = {agreed_n2pvs_n2}/{len(positions)} ({summary['agreement_n2pvs_n2_pct']:.1f}%)")
        print(f"  N4 PVS Telem: Full={pvs_telem_totals['n4'].get('full_window',0):,}, Null={pvs_telem_totals['n4'].get('null_window',0):,}, Researches={pvs_telem_totals['n4'].get('researches',0):,}\n")

    out_file = RAW_DIR / "depth_ablation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_by_depth, f, indent=2)

    print(f"Saved complete fixed-depth ablation data to {out_file}")
    return results_by_depth


if __name__ == "__main__":
    run_depth_ablation()

