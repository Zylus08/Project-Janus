"""Project Janus v0.56 - Fixed-Depth SEE Ablation Benchmark.

Evaluates 4 configurations (S0, S1, S2, S3) across Depths 3, 4, 5, 6
on 69 diagnostic, validation, and capture-focused positions:
- 37 Diagnostic corpus positions
- 16 Validation corpus positions
- 16 Capture evaluation corpus positions

Configurations:
- S0: Baseline N5 (UseSEEOrdering=false, UseSEEInQuiescence=false)
- S1: Main Only   (UseSEEOrdering=true,  UseSEEInQuiescence=false)
- S2: Q-Only      (UseSEEOrdering=false, UseSEEInQuiescence=true)
- S3: Candidate N7(UseSEEOrdering=true,  UseSEEInQuiescence=true)

Captures full telemetry:
- Nodes, wall-clock time, NPS, best move, score, PV
- First-move cutoff rate, mean cutoff index
- Cutoffs breakdown (TT, Killer1, Killer2, History, Captures, Quiet)
- SEE telemetry (evaluations, positive, neutral, negative, inversions)
"""

from __future__ import annotations

import json
import time
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v56", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.56" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.56" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def load_all_positions():
    positions = []
    # 1. Diagnostic corpus (37 positions)
    with open(CORPUS_DIR / "diagnostic_corpus.json", "r", encoding="utf-8") as f:
        for item in json.load(f):
            positions.append({"id": item["id"], "fen": item["fen"], "source": "diagnostic"})

    # 2. Validation corpus (16 positions)
    with open(CORPUS_DIR / "validation_corpus.json", "r", encoding="utf-8") as f:
        for item in json.load(f):
            positions.append({"id": item["id"], "fen": item["fen"], "source": "validation"})

    # 3. Capture evaluation corpus (16 positions)
    with open(CORPUS_DIR / "capture_evaluation_corpus.json", "r", encoding="utf-8") as f:
        for item in json.load(f):
            positions.append({"id": item["id"], "fen": item["fen"], "source": "capture"})

    return positions


def run_benchmark(depths=(3, 4, 5, 6)):
    positions = load_all_positions()
    print(f"Loaded {len(positions)} positions for SEE depth ablation.")

    bridge = NativeEngineBridge()

    configs = {
        "s0": {"see_main": False, "see_q": False, "desc": "S0: Baseline N5 (SEE Disabled)"},
        "s1": {"see_main": True,  "see_q": False, "desc": "S1: Main-Search SEE Only"},
        "s2": {"see_main": False, "see_q": True,  "desc": "S2: Quiescence SEE Only"},
        "s3": {"see_main": True,  "see_q": True,  "desc": "S3: Candidate N7 (Combined SEE)"},
    }

    all_results = {}

    for d in depths:
        print(f"\n==========================================")
        print(f"Running SEE Ablation at Depth {d}...")
        print(f"==========================================")

        depth_records = []
        cfg_totals = {
            c: {
                "nodes": 0,
                "time_sec": 0.0,
                "total_cutoffs": 0,
                "cutoff_1": 0,
                "see_evals": 0,
                "see_pos": 0,
                "see_neu": 0,
                "see_neg": 0,
                "see_inv": 0,
            }
            for c in configs
        }

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
                bridge.reset_see_telemetry()

                # Configure
                bridge.set_ordering_options(use_killer=True, use_history=True)
                bridge.set_pvs_options(use_pvs=False)
                bridge.set_lmr_options(use_lmr=True, min_depth=3, move_threshold=4, base_reduction=1)
                bridge.set_see_options(c_cfg["see_main"], c_cfg["see_q"])

                bridge.set_fen(fen)

                t0 = time.perf_counter()
                best_move, score_cp, depth_completed, nodes, elapsed_s, pv = bridge.search(
                    max_depth=d, time_limit=30.0
                )
                t1 = time.perf_counter()
                duration = t1 - t0

                ordering_telem = bridge.get_ordering_telemetry()
                see_telem = bridge.get_see_telemetry()

                pos_record[c_name] = {
                    "best_move": best_move,
                    "score_cp": score_cp,
                    "depth": depth_completed,
                    "nodes": nodes,
                    "elapsed_s": duration,
                    "nps": int(nodes / duration) if duration > 0 else 0,
                    "pv": pv,
                    "ordering": ordering_telem,
                    "see": see_telem,
                }

                cfg_totals[c_name]["nodes"] += nodes
                cfg_totals[c_name]["time_sec"] += duration
                cfg_totals[c_name]["total_cutoffs"] += ordering_telem["total_cutoffs"]
                cfg_totals[c_name]["cutoff_1"] += ordering_telem["cutoff_move_1"]
                cfg_totals[c_name]["see_evals"] += see_telem["total_evaluations"]
                cfg_totals[c_name]["see_pos"] += see_telem["positive_captures"]
                cfg_totals[c_name]["see_neu"] += see_telem["neutral_captures"]
                cfg_totals[c_name]["see_neg"] += see_telem["negative_captures"]
                cfg_totals[c_name]["see_inv"] += see_telem["ordering_inversions"]

            depth_records.append(pos_record)

            if (idx + 1) % 15 == 0 or (idx + 1) == len(positions):
                print(f"  Processed {idx + 1}/{len(positions)} positions at depth {d}...")

        summary = {}
        for c_name in configs:
            t = cfg_totals[c_name]
            first_move_pct = (t["cutoff_1"] / t["total_cutoffs"] * 100.0) if t["total_cutoffs"] > 0 else 0.0
            summary[c_name] = {
                "total_nodes": t["nodes"],
                "total_time_sec": t["time_sec"],
                "overall_nps": int(t["nodes"] / t["time_sec"]) if t["time_sec"] > 0 else 0,
                "first_move_cutoff_rate": first_move_pct,
                "see_evaluations": t["see_evals"],
                "see_positive": t["see_pos"],
                "see_neutral": t["see_neu"],
                "see_negative": t["see_neg"],
                "ordering_inversions": t["see_inv"],
            }

        s0_nodes = summary["s0"]["total_nodes"]
        for c in ["s1", "s2", "s3"]:
            diff = summary[c]["total_nodes"] - s0_nodes
            pct = (diff / s0_nodes) * 100.0 if s0_nodes > 0 else 0.0
            summary[c]["node_delta_vs_s0"] = diff
            summary[c]["node_reduction_pct_vs_s0"] = -pct

        print(f"\n--- Depth {d} Summary ---")
        for c_name, s in summary.items():
            red = s.get("node_reduction_pct_vs_s0", 0.0)
            print(f"  {configs[c_name]['desc']}: {s['total_nodes']:,} nodes ({red:+.2f}%), {s['total_time_sec']:.2f}s, 1st-cutoff: {s['first_move_cutoff_rate']:.1f}%")

        all_results[f"depth_{d}"] = {
            "summary": summary,
            "positions": depth_records,
        }

    raw_path = RAW_DIR / "depth_ablation_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n[OK] Saved complete raw benchmark results to {raw_path}")
    return all_results


if __name__ == "__main__":
    run_benchmark(depths=(3, 4, 5, 6))
