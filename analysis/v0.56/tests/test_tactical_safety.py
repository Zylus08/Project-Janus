"""Project Janus v0.56 - Tactical Safety & Capture-Focused Benchmark.

Evaluates 4 configurations (S0, S1, S2, S3) across 64 benchmark positions in 4 suites:
1. Tactical Regression Suite (12 positions)
2. Validation Suite (16 positions)
3. Independent Tactical Suite v0.53 (20 positions)
4. Capture Evaluation Corpus (16 positions)

Configurations:
- S0: Baseline N5 (UseSEEOrdering=false, UseSEEInQuiescence=false)
- S1: Main Only   (UseSEEOrdering=true,  UseSEEInQuiescence=false)
- S2: Q-Only      (UseSEEOrdering=false, UseSEEInQuiescence=true)
- S3: Candidate N7(UseSEEOrdering=true,  UseSEEInQuiescence=true)

Evaluates:
- Exact ground truth solution solve count
- Baseline solution retention (did S3 lose any solution that S0 solved?)
- New solutions gained by S3
- Move agreement between Candidate S3 and Baseline S0
- Total search nodes and tree compression
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


def load_suite(filename: str):
    with open(CORPUS_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_suite(bridge, suite_name: str, positions: list, depth: int = 5):
    print(f"\n--- Evaluating {suite_name} ({len(positions)} positions) at Depth {depth} ---")
    results = []

    configs = [
        ("s0", False, False),
        ("s1", True, False),
        ("s2", False, True),
        ("s3", True, True),
    ]

    totals = {c[0]: {"nodes": 0, "solved": 0} for c in configs}
    s0_agreement = 0

    for idx, pos in enumerate(positions):
        fen = pos["fen"]
        pos_id = pos["id"]
        exp_move = pos.get("solution") or pos.get("expected_move") or pos.get("expected") or ""

        entry = {
            "id": pos_id,
            "fen": fen,
            "expected_move": exp_move,
            "category": pos.get("category", "tactical"),
            "configs": {}
        }

        s0_move = None

        for c_name, see_main, see_q in configs:
            bridge.clear_tt()
            bridge.clear_killers()
            bridge.clear_history_heuristic()
            bridge.reset_history()
            bridge.reset_ordering_telemetry()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.reset_see_telemetry()

            bridge.set_ordering_options(use_killer=True, use_history=True)
            bridge.set_pvs_options(use_pvs=False)
            bridge.set_lmr_options(use_lmr=True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_see_options(see_main, see_q)

            bridge.set_fen(fen)

            t0 = time.perf_counter()
            best_move, score_cp, depth_reached, nodes, elapsed_sec, pv = bridge.search(max_depth=depth, time_limit=10.0)
            t1 = time.perf_counter()

            is_solved = (best_move == exp_move) if exp_move else False

            entry["configs"][c_name] = {
                "best_move": best_move,
                "score_cp": score_cp,
                "nodes": nodes,
                "elapsed_ms": (t1 - t0) * 1000.0,
                "pv": pv,
                "solved": is_solved,
            }

            totals[c_name]["nodes"] += nodes
            if is_solved:
                totals[c_name]["solved"] += 1

            if c_name == "s0":
                s0_move = best_move
            elif c_name == "s3" and best_move == s0_move:
                s0_agreement += 1

        results.append(entry)

    agree_pct = (s0_agreement / len(positions)) * 100.0 if positions else 0.0
    print(f"Results for {suite_name}:")
    for c_name, data in totals.items():
        print(f"  {c_name}: Solved {data['solved']}/{len(positions)}, Nodes: {data['nodes']:,}")
    print(f"  S3 vs S0 Move Agreement: {s0_agreement}/{len(positions)} ({agree_pct:.1f}%)")

    return {
        "suite_name": suite_name,
        "positions_count": len(positions),
        "s3_vs_s0_agreement_count": s0_agreement,
        "s3_vs_s0_agreement_pct": agree_pct,
        "totals": totals,
        "positions": results
    }


def main():
    bridge = NativeEngineBridge()

    s1 = evaluate_suite(bridge, "tactical_regression", load_suite("tactical_regression_corpus.json"), depth=5)
    s2 = evaluate_suite(bridge, "validation", load_suite("validation_corpus.json"), depth=5)
    s3 = evaluate_suite(bridge, "independent_tactical", load_suite("independent_tactical_v053.json"), depth=5)
    s4 = evaluate_suite(bridge, "capture_evaluation", load_suite("capture_evaluation_corpus.json"), depth=5)

    all_data = {
        "tactical_regression": s1,
        "validation": s2,
        "independent_tactical": s3,
        "capture_evaluation": s4,
    }

    # Combined summary
    total_positions = sum(s["positions_count"] for s in all_data.values())
    total_agreement = sum(s["s3_vs_s0_agreement_count"] for s in all_data.values())
    combined_totals = {c: {"nodes": 0, "solved": 0} for c in ["s0", "s1", "s2", "s3"]}

    for s in all_data.values():
        for c in ["s0", "s1", "s2", "s3"]:
            combined_totals[c]["nodes"] += s["totals"][c]["nodes"]
            combined_totals[c]["solved"] += s["totals"][c]["solved"]

    s0_nodes = combined_totals["s0"]["nodes"]
    s3_nodes = combined_totals["s3"]["nodes"]
    node_red_s3 = ((s0_nodes - s3_nodes) / s0_nodes * 100.0) if s0_nodes > 0 else 0.0

    all_data["combined_summary"] = {
        "total_positions": total_positions,
        "s3_vs_s0_agreement_count": total_agreement,
        "s3_vs_s0_agreement_pct": (total_agreement / total_positions) * 100.0,
        "combined_totals": combined_totals,
        "s3_node_reduction_pct_vs_s0": node_red_s3,
    }

    out_path = RAW_DIR / "tactical_safety_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\n==========================================")
    print(f"COMBINED TACTICAL BENCHMARK SUMMARY (64 Positions, Depth 5)")
    print(f"==========================================")
    print(f"S0 Baseline Solved: {combined_totals['s0']['solved']}/{total_positions} ({combined_totals['s0']['solved']/total_positions*100:.1f}%)")
    print(f"S1 Main-SEE Solved: {combined_totals['s1']['solved']}/{total_positions} ({combined_totals['s1']['solved']/total_positions*100:.1f}%)")
    print(f"S2 Q-SEE Solved:    {combined_totals['s2']['solved']}/{total_positions} ({combined_totals['s2']['solved']/total_positions*100:.1f}%)")
    print(f"S3 Combined Solved: {combined_totals['s3']['solved']}/{total_positions} ({combined_totals['s3']['solved']/total_positions*100:.1f}%)")
    print(f"S3 vs S0 Agreement: {total_agreement}/{total_positions} ({(total_agreement/total_positions)*100.0:.1f}%)")
    print(f"S0 Nodes: {s0_nodes:,} | S3 Nodes: {s3_nodes:,} ({node_red_s3:+.2f}% node reduction)")
    print(f"Saved results to {out_path}")


if __name__ == "__main__":
    main()
