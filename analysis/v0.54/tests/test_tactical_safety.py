"""Project Janus v0.54 - Tactical Safety & Search Quality Benchmark.

Evaluates 4 configurations across 48 benchmark positions:
1. Tactical Regression Suite (12 positions)
2. Validation Suite (16 positions)
3. Independent Tactical Suite v0.53 (20 positions)

Configurations:
- C0 (Control):       UseKiller=False, UseHistory=False (Production N3)
- C1 (Killer Only):   UseKiller=True,  UseHistory=False
- C2 (History Only):  UseKiller=False, UseHistory=True
- C3 (Combined N5):   UseKiller=True,  UseHistory=True

Search Conditions: Fixed Depth 5, Clean TT per position.
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


def load_suite(filename: str):
    with open(CORPUS_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_suite(bridge, suite_name: str, positions: list, depth: int = 5):
    print(f"\n--- Evaluating {suite_name} ({len(positions)} positions) at Depth {depth} ---")
    results = []

    configs = [
        ("c0", False, False),
        ("c1", True, False),
        ("c2", False, True),
        ("c3", True, True),
    ]

    tot_nodes = {"c0": 0, "c1": 0, "c2": 0, "c3": 0}
    tot_solved = {"c0": 0, "c1": 0, "c2": 0, "c3": 0}

    for pos_idx, entry in enumerate(positions):
        fen = entry["fen"]
        pos_id = entry.get("id", f"pos_{pos_idx}")
        expected = entry.get("solution") or entry.get("expected_move") or entry.get("expected", "")

        pos_data = {"id": pos_id, "fen": fen, "expected": expected, "configs": {}}

        for cfg_id, use_k, use_h in configs:
            bridge.clear_tt()
            bridge.clear_killers()
            bridge.clear_history_heuristic()
            bridge.reset_history()
            bridge.reset_ordering_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(False)
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_ordering_options(use_k, use_h)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv, sc, dp, nd, el, pv = bridge.search(max_depth=depth, time_limit=30.0)
            elapsed = time.perf_counter() - t0
            telem = bridge.get_ordering_telemetry()

            is_solved = (mv == expected) if expected else False
            if is_solved:
                tot_solved[cfg_id] += 1
            tot_nodes[cfg_id] += nd

            pos_data["configs"][cfg_id] = {
                "move": mv,
                "score": sc,
                "nodes": nd,
                "time_sec": elapsed,
                "solved": is_solved,
                "telemetry": telem,
            }

        # Check move agreement between C3 and C0
        c0_mv = pos_data["configs"]["c0"]["move"]
        c3_mv = pos_data["configs"]["c3"]["move"]
        pos_data["agreed_c3_c0"] = (c3_mv == c0_mv)
        results.append(pos_data)

    n_pos = len(positions)
    agreed_c3_c0 = sum(1 for p in results if p["agreed_c3_c0"])

    summary = {
        "suite_name": suite_name,
        "total_positions": n_pos,
        "solved": tot_solved,
        "total_nodes": tot_nodes,
        "node_reduction_c3_vs_c0_pct": ((tot_nodes["c0"] - tot_nodes["c3"]) / tot_nodes["c0"] * 100.0) if tot_nodes["c0"] > 0 else 0.0,
        "agreement_c3_c0_pct": (agreed_c3_c0 / n_pos * 100.0) if n_pos > 0 else 0.0,
        "agreed_count": agreed_c3_c0,
    }

    print(f"Summary for {suite_name}:")
    print(f"  Solved: C0={tot_solved['c0']} | C1={tot_solved['c1']} | C2={tot_solved['c2']} | C3={tot_solved['c3']}")
    print(f"  Nodes:  C0={tot_nodes['c0']:,} vs C3={tot_nodes['c3']:,} (Delta: {summary['node_reduction_c3_vs_c0_pct']:+.2f}%)")
    print(f"  Agreement C3 vs C0: {agreed_c3_c0}/{n_pos} ({summary['agreement_c3_c0_pct']:.1f}%)")

    return {"summary": summary, "positions": results}


def run_all_suites():
    bridge = NativeEngineBridge()

    tac_reg = load_suite("tactical_regression_corpus.json")
    val_suite = load_suite("validation_corpus.json")
    ind_suite = load_suite("independent_tactical_v053.json")

    results = {
        "tactical_regression": evaluate_suite(bridge, "Tactical Regression Suite (12)", tac_reg),
        "validation": evaluate_suite(bridge, "Validation Suite (16)", val_suite),
        "independent_tactical": evaluate_suite(bridge, "Independent Tactical Suite (20)", ind_suite),
    }

    # Combined summary
    total_pos = len(tac_reg) + len(val_suite) + len(ind_suite)
    tot_solved_all = {
        k: results["tactical_regression"]["summary"]["solved"][k] +
           results["validation"]["summary"]["solved"][k] +
           results["independent_tactical"]["summary"]["solved"][k]
        for k in ["c0", "c1", "c2", "c3"]
    }
    tot_nodes_all = {
        k: results["tactical_regression"]["summary"]["total_nodes"][k] +
           results["validation"]["summary"]["total_nodes"][k] +
           results["independent_tactical"]["summary"]["total_nodes"][k]
        for k in ["c0", "c1", "c2", "c3"]
    }
    tot_agreed = (
        results["tactical_regression"]["summary"]["agreed_count"] +
        results["validation"]["summary"]["agreed_count"] +
        results["independent_tactical"]["summary"]["agreed_count"]
    )

    combined_summary = {
        "total_positions": total_pos,
        "solved": tot_solved_all,
        "total_nodes": tot_nodes_all,
        "node_reduction_c3_vs_c0_pct": ((tot_nodes_all["c0"] - tot_nodes_all["c3"]) / tot_nodes_all["c0"] * 100.0) if tot_nodes_all["c0"] > 0 else 0.0,
        "agreement_c3_c0_pct": (tot_agreed / total_pos * 100.0),
        "total_agreed": tot_agreed,
    }
    results["combined_summary"] = combined_summary

    print("\n" + "=" * 60)
    print("COMBINED TACTICAL SAFETY SUMMARY across 48 Positions:")
    print("=" * 60)
    print(f"Solved: C0={tot_solved_all['c0']} | C1={tot_solved_all['c1']} | C2={tot_solved_all['c2']} | C3={tot_solved_all['c3']}")
    print(f"Nodes:  C0={tot_nodes_all['c0']:,} | C1={tot_nodes_all['c1']:,} | C2={tot_nodes_all['c2']:,} | C3={tot_nodes_all['c3']:,}")
    print(f"Node Reduction C3 vs C0: {combined_summary['node_reduction_c3_vs_c0_pct']:+.2f}%")
    print(f"Move Agreement C3 vs C0: {tot_agreed}/{total_pos} ({combined_summary['agreement_c3_c0_pct']:.1f}%)")
    print("=" * 60)

    out_file = RAW_DIR / "tactical_safety_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw tactical safety data to {out_file}")


if __name__ == "__main__":
    run_all_suites()
