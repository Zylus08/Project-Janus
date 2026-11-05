"""Project Janus v0.52 - Tactical Safety & Regression Benchmark.

Evaluates N2 (control, UseLMR=false) vs N3 (candidate, UseLMR=true) across:
1. 12-position tactical regression corpus (tactical_regression_corpus.json)
2. 16-position validation corpus (validation_corpus.json)

Verifies that LMR does not introduce tactical blindness, sacrifice solve rates,
or fail to solve known tactical combinations.
"""

import json
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.52" / "native"))

from janus_native_bridge import NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.52" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.52" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def evaluate_corpus(corpus_path: Path, depth: int = 5):
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    bridge = NativeEngineBridge()
    results = []

    for entry in corpus:
        pos_id = entry["id"]
        fen = entry["fen"]
        expected = entry.get("solution") or entry.get("expected_move")
        theme = entry.get("theme", "Tactical")

        # 1. Search N2 (Baseline, UseLMR=false)
        bridge.clear_tt()
        bridge.reset_history()
        bridge.reset_lmr_telemetry()
        bridge.set_lmr_options(False)
        bridge.set_fen(fen)

        t0 = time.perf_counter()
        mv_n2, sc_n2, dp_n2, nd_n2, el_n2, pv_n2 = bridge.search(max_depth=depth, time_limit=5.0)
        t_n2 = time.perf_counter() - t0

        # 2. Search N3 (Candidate, UseLMR=true)
        bridge.clear_tt()
        bridge.reset_history()
        bridge.reset_lmr_telemetry()
        bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
        bridge.set_fen(fen)

        t0 = time.perf_counter()
        mv_n3, sc_n3, dp_n3, nd_n3, el_n3, pv_n3 = bridge.search(max_depth=depth, time_limit=5.0)
        t_n3 = time.perf_counter() - t0
        telem_n3 = bridge.get_lmr_telemetry()

        n2_solved = (mv_n2 == expected) if expected else None
        n3_solved = (mv_n3 == expected) if expected else None
        agreed = (mv_n2 == mv_n3)
        node_reduction_pct = ((nd_n2 - nd_n3) / nd_n2 * 100.0) if nd_n2 > 0 else 0.0

        results.append({
            "id": pos_id,
            "theme": theme,
            "fen": fen,
            "expected": expected,
            "n2_move": mv_n2,
            "n2_score": sc_n2,
            "n2_nodes": nd_n2,
            "n2_time": t_n2,
            "n2_solved": n2_solved,
            "n3_move": mv_n3,
            "n3_score": sc_n3,
            "n3_nodes": nd_n3,
            "n3_time": t_n3,
            "n3_solved": n3_solved,
            "agreed": agreed,
            "node_reduction_pct": node_reduction_pct,
            "telemetry": telem_n3,
        })

    return results


def main():
    print("=" * 70)
    print("Project Janus v0.52 - Tactical Safety & Regression Benchmark")
    print("=" * 70)

    # 1. Tactical regression corpus (12 positions)
    tac_path = CORPUS_DIR / "tactical_regression_corpus.json"
    print(f"\nEvaluating Tactical Regression Corpus (12 positions, Depth 5)...")
    tac_results = evaluate_corpus(tac_path, depth=5)

    n2_tac_solved = sum(1 for r in tac_results if r["n2_solved"])
    n3_tac_solved = sum(1 for r in tac_results if r["n3_solved"])
    tac_agreed = sum(1 for r in tac_results if r["agreed"])
    total_tac = len(tac_results)

    tot_nd_n2 = sum(r["n2_nodes"] for r in tac_results)
    tot_nd_n3 = sum(r["n3_nodes"] for r in tac_results)
    tot_red_pct = ((tot_nd_n2 - tot_nd_n3) / tot_nd_n2 * 100.0) if tot_nd_n2 > 0 else 0

    print(f"Tactical Results:")
    print(f"  N2 Solved: {n2_tac_solved}/{total_tac} ({n2_tac_solved/total_tac*100:.1f}%)")
    print(f"  N3 Solved: {n3_tac_solved}/{total_tac} ({n3_tac_solved/total_tac*100:.1f}%)")
    print(f"  Move Agreement: {tac_agreed}/{total_tac} ({tac_agreed/total_tac*100:.1f}%)")
    print(f"  Total Nodes: N2={tot_nd_n2:,} vs N3={tot_nd_n3:,} ({tot_red_pct:+.1f}% nodes)")

    for r in tac_results:
        status = "SOLVED" if r["n3_solved"] else ("AGREED" if r["agreed"] else "DIFF")
        print(f"  {r['id']:<25} Exp: {r['expected']:<5} N2: {r['n2_move']:<5} N3: {r['n3_move']:<5} [{status}] Nodes: {r['n2_nodes']} -> {r['n3_nodes']} ({r['node_reduction_pct']:+.1f}%)")

    # 2. Validation corpus (16 positions)
    val_path = CORPUS_DIR / "validation_corpus.json"
    print(f"\nEvaluating Validation Corpus (16 positions, Depth 5)...")
    val_results = evaluate_corpus(val_path, depth=5)

    n2_val_solved = sum(1 for r in val_results if r["n2_solved"])
    n3_val_solved = sum(1 for r in val_results if r["n3_solved"])
    val_agreed = sum(1 for r in val_results if r["agreed"])
    total_val = len(val_results)

    tot_val_nd_n2 = sum(r["n2_nodes"] for r in val_results)
    tot_val_nd_n3 = sum(r["n3_nodes"] for r in val_results)
    tot_val_red_pct = ((tot_val_nd_n2 - tot_val_nd_n3) / tot_val_nd_n2 * 100.0) if tot_val_nd_n2 > 0 else 0

    print(f"Validation Results:")
    print(f"  N2 Solved: {n2_val_solved}/{total_val} ({n2_val_solved/total_val*100:.1f}%)")
    print(f"  N3 Solved: {n3_val_solved}/{total_val} ({n3_val_solved/total_val*100:.1f}%)")
    print(f"  Move Agreement: {val_agreed}/{total_val} ({val_agreed/total_val*100:.1f}%)")
    print(f"  Total Nodes: N2={tot_val_nd_n2:,} vs N3={tot_val_nd_n3:,} ({tot_val_red_pct:+.1f}% nodes)")

    for r in val_results:
        status = "SOLVED" if r["n3_solved"] else ("AGREED" if r["agreed"] else "DIFF")
        print(f"  {r['id']:<25} Exp: {r['expected']:<5} N2: {r['n2_move']:<5} N3: {r['n3_move']:<5} [{status}] Nodes: {r['n2_nodes']} -> {r['n3_nodes']} ({r['node_reduction_pct']:+.1f}%)")

    # Save to raw JSON
    combined = {
        "timestamp": time.time(),
        "depth": 5,
        "tactical_corpus": tac_results,
        "validation_corpus": val_results,
        "summary": {
            "tactical_n2_solved": n2_tac_solved,
            "tactical_n3_solved": n3_tac_solved,
            "tactical_agreement": tac_agreed,
            "tactical_total": total_tac,
            "tactical_node_reduction_pct": tot_red_pct,
            "validation_n2_solved": n2_val_solved,
            "validation_n3_solved": n3_val_solved,
            "validation_agreement": val_agreed,
            "validation_total": total_val,
            "validation_node_reduction_pct": tot_val_red_pct,
        }
    }
    out_file = RAW_DIR / "tactical_safety_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)

    print(f"\nRaw results written to {out_file}")


if __name__ == "__main__":
    main()

