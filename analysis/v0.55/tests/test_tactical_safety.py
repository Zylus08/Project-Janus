"""Project Janus v0.55 - Tactical Safety & Differential Benchmark.

Evaluates 4 configurations (F00, F01, F10, F11) across 48 benchmark positions:
1. Tactical Regression Suite (12 positions)
2. Validation Suite (16 positions)
3. Independent Tactical Suite v0.53 (20 positions)

Configurations:
- F00: K=0, H=0, PVS=0 (N3 Control)
- F01: K=0, H=0, PVS=1 (N4 Baseline)
- F10: K=1, H=1, PVS=0 (N5 Production Reference)
- F11: K=1, H=1, PVS=1 (N6 Candidate)

Search Conditions: Fixed Depth 5, Clean TT per position.
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


def load_suite(filename: str):
    with open(CORPUS_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_suite(bridge, suite_name: str, positions: list, depth: int = 5):
    print(f"\n--- Evaluating {suite_name} ({len(positions)} positions) at Depth {depth} ---")
    results = []

    configs = [
        ("f00", False, False, False),
        ("f01", False, False, True),
        ("f10", True, True, False),
        ("f11", True, True, True),
    ]

    totals = {c[0]: {"nodes": 0, "solved": 0} for c in configs}
    f10_agreement = 0

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

        f10_move = None

        for c_name, k, h, pvs in configs:
            bridge.clear_tt()
            bridge.clear_killers()
            bridge.clear_history_heuristic()
            bridge.reset_history()
            bridge.reset_ordering_telemetry()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()

            bridge.set_ordering_options(k, h)
            bridge.set_pvs_options(pvs)
            bridge.set_lmr_options(True)

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

            if c_name == "f10":
                f10_move = best_move

        if entry["configs"]["f11"]["best_move"] == f10_move:
            f10_agreement += 1

        results.append(entry)

    summary = {
        "suite_name": suite_name,
        "positions_count": len(positions),
        "f11_vs_f10_agreement_count": f10_agreement,
        "f11_vs_f10_agreement_pct": (f10_agreement / len(positions) * 100) if len(positions) > 0 else 0,
        "totals": totals
    }

    print(f"Summary for {suite_name}:")
    print(f"  F11 vs F10 Move Agreement: {f10_agreement}/{len(positions)} ({summary['f11_vs_f10_agreement_pct']:.1f}%)")
    for c_name, _, _, _ in configs:
        print(f"  {c_name.upper()}: {totals[c_name]['nodes']:,} nodes | Solved: {totals[c_name]['solved']}")

    return {"summary": summary, "positions": results}


def main():
    bridge = NativeEngineBridge()

    suites = [
        ("tactical_regression", "tactical_regression_corpus.json"),
        ("validation", "validation_corpus.json"),
        ("independent_tactical", "independent_tactical_v053.json"),
    ]

    all_data = {}
    combined_totals = {c: {"nodes": 0, "solved": 0} for c in ["f00", "f01", "f10", "f11"]}
    combined_agreements = 0
    total_positions = 0

    for s_key, s_file in suites:
        positions = load_suite(s_file)
        res = evaluate_suite(bridge, s_key, positions, depth=5)
        all_data[s_key] = res

        s_sum = res["summary"]
        combined_agreements += s_sum["f11_vs_f10_agreement_count"]
        total_positions += s_sum["positions_count"]
        for c in combined_totals:
            combined_totals[c]["nodes"] += s_sum["totals"][c]["nodes"]
            combined_totals[c]["solved"] += s_sum["totals"][c]["solved"]

    all_data["combined_summary"] = {
        "total_positions": total_positions,
        "f11_vs_f10_agreement_count": combined_agreements,
        "f11_vs_f10_agreement_pct": combined_agreements / total_positions * 100,
        "combined_totals": combined_totals,
        "f11_node_reduction_pct_vs_f10": (combined_totals["f10"]["nodes"] - combined_totals["f11"]["nodes"]) / combined_totals["f10"]["nodes"] * 100,
        "f11_node_reduction_pct_vs_f00": (combined_totals["f00"]["nodes"] - combined_totals["f11"]["nodes"]) / combined_totals["f00"]["nodes"] * 100,
    }

    print("\n==========================================")
    print("Combined Tactical Safety Summary (48 Positions):")
    print(f"  F11 vs F10 Move Agreement: {combined_agreements}/{total_positions} ({all_data['combined_summary']['f11_vs_f10_agreement_pct']:.1f}%)")
    for c in ["f00", "f01", "f10", "f11"]:
        print(f"  {c.upper()}: {combined_totals[c]['nodes']:,} nodes | Solved: {combined_totals[c]['solved']}")
    print(f"  F11 Node Reduction vs F10: {all_data['combined_summary']['f11_node_reduction_pct_vs_f10']:.2f}%")
    print(f"  F11 Node Reduction vs F00: {all_data['combined_summary']['f11_node_reduction_pct_vs_f00']:.2f}%")
    print("==========================================")

    out_file = RAW_DIR / "tactical_safety_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"Saved tactical safety results to {out_file}")


if __name__ == "__main__":
    main()

