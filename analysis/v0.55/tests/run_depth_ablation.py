"""Project Janus v0.55 - Fixed-Depth Factorial Ablation Benchmark.

Evaluates 4 configurations across Depths 3, 4, 5, 6 on 53 test positions:
- 37 Diagnostic corpus positions
- 16 Validation corpus positions

Configurations:
1. F00: Killer=0, History=0, PVS=0 (N3 control)
2. F01: Killer=0, History=0, PVS=1 (N4 baseline)
3. F10: Killer=1, History=1, PVS=0 (N5 production)
4. F11: Killer=1, History=1, PVS=1 (N6 candidate)

Captures:
- Nodes, wall-clock time, NPS, best move, score, PV
- First-move cutoff rate, mean cutoff index
- PVS telemetry: null-window searches, re-searches, cutoffs
- LMR telemetry: reduced moves, re-searches, cutoffs
- Killer & History cutoffs
"""

import json
import time
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.55" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v55", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.55" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.55" / "raw"
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


def run_benchmark(depths=(3, 4, 5, 6)):
    positions = load_all_positions()
    print(f"Loaded {len(positions)} positions for factorial depth ablation.")

    bridge = NativeEngineBridge()

    configs = {
        "f00": {"killer": False, "history": False, "pvs": False, "desc": "N3 Control (K=0, H=0, PVS=0)"},
        "f01": {"killer": False, "history": False, "pvs": True,  "desc": "N4 (K=0, H=0, PVS=1)"},
        "f10": {"killer": True,  "history": True,  "pvs": False, "desc": "N5 Production (K=1, H=1, PVS=0)"},
        "f11": {"killer": True,  "history": True,  "pvs": True,  "desc": "N6 Candidate (K=1, H=1, PVS=1)"},
    }

    all_results = {}

    for d in depths:
        print(f"\n==========================================")
        print(f"Running Factorial Ablation at Depth {d}...")
        print(f"==========================================")

        depth_records = []
        cfg_totals = {c: {"nodes": 0, "time_sec": 0.0, "cutoffs": 0, "cutoff_1": 0} for c in configs}

        for idx, pos in enumerate(positions):
            pos_id = pos["id"]
            fen = pos["fen"]
            pos_record = {"id": pos_id, "fen": fen, "source": pos["source"]}

            for c_name, c_cfg in configs.items():
                # Reset engine state for fair benchmarking
                bridge.clear_tt()
                bridge.clear_killers()
                bridge.clear_history_heuristic()
                bridge.reset_history()
                bridge.reset_ordering_telemetry()
                bridge.reset_pvs_telemetry()
                bridge.reset_lmr_telemetry()

                # Configure
                bridge.set_ordering_options(c_cfg["killer"], c_cfg["history"])
                bridge.set_pvs_options(c_cfg["pvs"])
                bridge.set_lmr_options(True)

                bridge.set_fen(fen)

                t0 = time.perf_counter()
                best_move, score_cp, depth_reached, nodes, elapsed_sec, pv = bridge.search(max_depth=d, time_limit=60.0)
                t1 = time.perf_counter()
                wall_sec = t1 - t0

                ord_telem = bridge.get_ordering_telemetry()
                pvs_telem = bridge.get_pvs_telemetry()
                lmr_telem = bridge.get_lmr_telemetry()

                pos_record[c_name] = {
                    "best_move": best_move,
                    "score_cp": score_cp,
                    "depth_reached": depth_reached,
                    "nodes": nodes,
                    "elapsed_sec": wall_sec,
                    "pv": pv,
                    "ordering_telemetry": ord_telem,
                    "pvs_telemetry": pvs_telem,
                    "lmr_telemetry": lmr_telem,
                }

                cfg_totals[c_name]["nodes"] += nodes
                cfg_totals[c_name]["time_sec"] += wall_sec
                cfg_totals[c_name]["cutoffs"] += ord_telem.get("total_cutoffs", 0)
                cfg_totals[c_name]["cutoff_1"] += ord_telem.get("cutoff_move_1", 0)

            depth_records.append(pos_record)
            if (idx + 1) % 15 == 0 or (idx + 1) == len(positions):
                print(f"  Processed {idx + 1}/{len(positions)} positions...")

        # Summary for depth d
        summary_d = {
            "depth": d,
            "positions_count": len(positions),
            "total_nodes": {c: cfg_totals[c]["nodes"] for c in configs},
            "total_time_sec": {c: cfg_totals[c]["time_sec"] for c in configs},
            "node_reduction_pct_vs_f00": {
                c: ((cfg_totals["f00"]["nodes"] - cfg_totals[c]["nodes"]) / cfg_totals["f00"]["nodes"] * 100)
                for c in configs
            },
            "speedup_vs_f00": {
                c: (cfg_totals["f00"]["time_sec"] / cfg_totals[c]["time_sec"]) if cfg_totals[c]["time_sec"] > 0 else 1.0
                for c in configs
            },
            "first_move_cutoff_rate_pct": {
                c: (cfg_totals[c]["cutoff_1"] / cfg_totals[c]["cutoffs"] * 100) if cfg_totals[c]["cutoffs"] > 0 else 0
                for c in configs
            },
        }

        print(f"\n--- Depth {d} Summary ---")
        for c in configs:
            n = cfg_totals[c]["nodes"]
            t = cfg_totals[c]["time_sec"]
            red = summary_d["node_reduction_pct_vs_f00"][c]
            spd = summary_d["speedup_vs_f00"][c]
            fc = summary_d["first_move_cutoff_rate_pct"][c]
            print(f"  {c.upper()} ({configs[c]['desc']}): {n:,} nodes ({red:+.2f}%), {t:.2f}s ({spd:.2f}x), 1st-cutoff: {fc:.1f}%")

        all_results[str(d)] = {
            "summary": summary_d,
            "positions": depth_records
        }

    out_file = RAW_DIR / "depth_ablation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved full depth ablation telemetry to {out_file}")


if __name__ == "__main__":
    run_benchmark()

