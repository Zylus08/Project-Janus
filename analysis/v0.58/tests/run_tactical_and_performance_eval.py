"""Project Janus v0.58 - Tactical Safety & Fixed-Time Performance Evaluation.

Evaluates:
Part A: Tactical Safety Regression (10 positions with known solutions).
        Verifies Candidate N8-A maintains 100% tactical resolution parity with Baseline C1.
Part B: Fixed-Time Performance Ladder (16 validation positions at 50ms, 100ms, 200ms).
        Measures effective nominal depth reached, NPS, cutoff index, and move stability.
"""

from __future__ import annotations

import json
import time
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.58" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v58", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

TACTICAL_CORPUS = ROOT / "analysis" / "v0.56" / "corpus" / "tactical_regression_corpus.json"
VALIDATION_CORPUS = ROOT / "analysis" / "v0.56" / "corpus" / "validation_corpus.json"
RAW_DIR = ROOT / "analysis" / "v0.58" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def run_tactical_safety():
    print("\n" + "="*80)
    print("PART A: TACTICAL SAFETY REGRESSION (10 Curated Positions)")
    print("="*80)

    with open(TACTICAL_CORPUS, "r", encoding="utf-8") as f:
        tactical_positions = json.load(f)

    eng = NativeEngineBridge()
    results = []

    c1_passed = 0
    n8_passed = 0

    for idx, pos in enumerate(tactical_positions, 1):
        pos_id = pos["id"]
        fen = pos["fen"]
        expected = pos["solution"]
        desc = pos["description"]

        # 1. Test C1 (Neural OFF)
        eng.clear_tt()
        eng.clear_killers()
        eng.clear_history_heuristic()
        eng.set_neural_policy_options(False)
        eng.set_fen(fen)
        c1_bm, c1_score, c1_depth, c1_nodes, c1_elapsed, _ = eng.search(max_depth=6, time_limit=5.0)

        c1_ok = (c1_bm == expected)
        if c1_ok:
            c1_passed += 1

        # 2. Test N8-A (Candidate: Root-Only Policy)
        eng.clear_tt()
        eng.clear_killers()
        eng.clear_history_heuristic()
        eng.reset_neural_telemetry()
        eng.set_neural_policy_options(True, max_ply=0, min_depth=4)
        eng.set_fen(fen)
        n8_bm, n8_score, n8_depth, n8_nodes, n8_elapsed, _ = eng.search(max_depth=6, time_limit=5.0)
        n8_telem = eng.get_neural_telemetry()

        n8_ok = (n8_bm == expected)
        if n8_ok:
            n8_passed += 1

        rec = {
            "id": pos_id,
            "theme": pos.get("theme", ""),
            "fen": fen,
            "expected": expected,
            "c1_bm": c1_bm,
            "c1_nodes": c1_nodes,
            "c1_ok": c1_ok,
            "n8_bm": n8_bm,
            "n8_nodes": n8_nodes,
            "n8_ok": n8_ok,
            "neural_evals": n8_telem["evaluations"],
        }
        results.append(rec)
        print(f"[{idx:2d}/10] {pos_id:25s} | Solution: {expected:5s} | C1: {c1_bm:5s} ({'PASS' if c1_ok else 'FAIL'}) | N8-A: {n8_bm:5s} ({'PASS' if n8_ok else 'FAIL'})")

    print(f"\nTactical Safety Summary: C1 = {c1_passed}/10 ({c1_passed*10}%), N8-A = {n8_passed}/10 ({n8_passed*10}%)")
    return results, c1_passed, n8_passed


def run_fixed_time_performance():
    print("\n" + "="*80)
    print("PART B: FIXED-TIME PERFORMANCE LADDER (16 Positions x [50ms, 100ms, 200ms])")
    print("="*80)

    with open(VALIDATION_CORPUS, "r", encoding="utf-8") as f:
        val_positions = json.load(f)

    eng = NativeEngineBridge()
    time_controls = [0.050, 0.100, 0.200] # 50ms, 100ms, 200ms
    tc_labels = ["50ms", "100ms", "200ms"]

    ladder_results = {tc: {"C1": [], "N8-A": []} for tc in tc_labels}

    for pos_idx, pos in enumerate(val_positions, 1):
        fen = pos["fen"]
        pos_id = pos["id"]

        for tc_sec, tc_label in zip(time_controls, tc_labels):
            # C1
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.reset_ordering_telemetry()
            eng.set_neural_policy_options(False)
            eng.set_fen(fen)
            c1_bm, c1_score, c1_depth, c1_nodes, c1_elapsed, _ = eng.search(max_depth=64, time_limit=tc_sec)
            c1_ord = eng.get_ordering_telemetry()

            c1_rec = {
                "id": pos_id,
                "best_move": c1_bm,
                "score": c1_score,
                "depth": c1_depth,
                "nodes": c1_nodes,
                "elapsed": round(c1_elapsed, 4),
                "nps": int(c1_nodes / c1_elapsed) if c1_elapsed > 0 else 0,
                "first_move_cutoff_rate": c1_ord["first_move_cutoff_rate"],
                "mean_cutoff_index": c1_ord["mean_cutoff_index"],
            }
            ladder_results[tc_label]["C1"].append(c1_rec)

            # N8-A
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.reset_ordering_telemetry()
            eng.reset_neural_telemetry()
            eng.set_neural_policy_options(True, max_ply=0, min_depth=4)
            eng.set_fen(fen)
            n8_bm, n8_score, n8_depth, n8_nodes, n8_elapsed, _ = eng.search(max_depth=64, time_limit=tc_sec)
            n8_ord = eng.get_ordering_telemetry()
            n8_telem = eng.get_neural_telemetry()

            n8_rec = {
                "id": pos_id,
                "best_move": n8_bm,
                "score": n8_score,
                "depth": n8_depth,
                "nodes": n8_nodes,
                "elapsed": round(n8_elapsed, 4),
                "nps": int(n8_nodes / n8_elapsed) if n8_elapsed > 0 else 0,
                "first_move_cutoff_rate": n8_ord["first_move_cutoff_rate"],
                "mean_cutoff_index": n8_ord["mean_cutoff_index"],
                "neural_evals": n8_telem["evaluations"],
                "neural_time_us": n8_telem["inference_time_us"],
            }
            ladder_results[tc_label]["N8-A"].append(n8_rec)

        print(f"[{pos_idx:2d}/16] {pos_id:25s} tested across 50ms, 100ms, 200ms.")

    # Aggregates
    summary = {}
    for tc_label in tc_labels:
        c1_list = ladder_results[tc_label]["C1"]
        n8_list = ladder_results[tc_label]["N8-A"]

        c1_avg_depth = sum(x["depth"] for x in c1_list) / len(c1_list)
        n8_avg_depth = sum(x["depth"] for x in n8_list) / len(n8_list)

        c1_tot_nodes = sum(x["nodes"] for x in c1_list)
        n8_tot_nodes = sum(x["nodes"] for x in n8_list)

        c1_avg_nps = sum(x["nps"] for x in c1_list) / len(c1_list)
        n8_avg_nps = sum(x["nps"] for x in n8_list) / len(n8_list)

        c1_avg_cutoff = sum(x["first_move_cutoff_rate"] for x in c1_list) / len(c1_list)
        n8_avg_cutoff = sum(x["first_move_cutoff_rate"] for x in n8_list) / len(n8_list)

        bm_agreement = sum(1 for c, n in zip(c1_list, n8_list) if c["best_move"] == n["best_move"]) / len(c1_list) * 100.0

        summary[tc_label] = {
            "c1_avg_depth": round(c1_avg_depth, 2),
            "n8_avg_depth": round(n8_avg_depth, 2),
            "c1_total_nodes": c1_tot_nodes,
            "n8_total_nodes": n8_tot_nodes,
            "c1_avg_nps": int(c1_avg_nps),
            "n8_avg_nps": int(n8_avg_nps),
            "nps_retention_pct": round(n8_avg_nps / c1_avg_nps * 100.0, 1) if c1_avg_nps > 0 else 100.0,
            "c1_first_move_cutoff_pct": round(c1_avg_cutoff, 2),
            "n8_first_move_cutoff_pct": round(n8_avg_cutoff, 2),
            "best_move_agreement_pct": round(bm_agreement, 1),
        }

    print("\n" + "="*80)
    print("FIXED-TIME PERFORMANCE SUMMARY")
    print("="*80)
    print(f"{'Time Control':12s} | {'C1 Depth':9s} | {'N8 Depth':9s} | {'C1 NPS':10s} | {'N8 NPS':10s} | {'NPS Ret %':10s} | {'BM Agr %':9s}")
    print("-" * 80)
    for tc_label in tc_labels:
        s = summary[tc_label]
        print(f"{tc_label:12s} | {s['c1_avg_depth']:9.2f} | {s['n8_avg_depth']:9.2f} | {s['c1_avg_nps']:10d} | {s['n8_avg_nps']:10d} | {s['nps_retention_pct']:9.1f}% | {s['best_move_agreement_pct']:8.1f}%")

    return ladder_results, summary


def main():
    tac_results, c1_tac, n8_tac = run_tactical_safety()
    perf_results, perf_summary = run_fixed_time_performance()

    full_eval = {
        "tactical_safety": {
            "c1_passed": c1_tac,
            "n8_passed": n8_tac,
            "total": 10,
            "positions": tac_results,
        },
        "fixed_time_ladder": {
            "summary": perf_summary,
            "data": perf_results,
        }
    }

    out_file = RAW_DIR / "performance_evaluation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_eval, f, indent=2)
    print(f"\nSaved full evaluation to {out_file}")


if __name__ == "__main__":
    main()

