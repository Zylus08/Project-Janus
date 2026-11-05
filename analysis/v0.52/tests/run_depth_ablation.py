"""Project Janus v0.52 - Fixed-Depth LMR Ablation Benchmark.

Evaluates N2 (control) vs N3 (candidate) across Depths 3, 4, 5, 6 on:
- 37 Diagnostic corpus positions
- 16 Validation corpus positions
Total: 53 positions.

Measures:
- Total nodes, node reduction percentage
- Wall-clock search duration, speedup factor
- NPS throughput
- Move agreement percentage
- Re-search counts and re-search rate
- LMR cutoffs
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
    print("Beginning Fixed-Depth Ablation across Depths 3, 4, 5, 6...\n")

    for depth in depths:
        print(f"--- Running Depth {depth} ---")
        depth_data = []

        total_nodes_n2 = 0
        total_nodes_n3 = 0
        total_time_n2 = 0.0
        total_time_n3 = 0.0
        agreed_count = 0
        total_reduced = 0
        total_researches = 0
        total_cutoffs = 0

        for i, pos in enumerate(positions):
            fen = pos["fen"]
            pos_id = pos["id"]

            # Baseline N2 (UseLMR=false)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_lmr_telemetry()
            bridge.set_lmr_options(False)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv_n2, sc_n2, dp_n2, nd_n2, el_n2, pv_n2 = bridge.search(max_depth=depth, time_limit=30.0)
            t_n2 = time.perf_counter() - t0

            # Candidate N3 (UseLMR=true)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_lmr_telemetry()
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv_n3, sc_n3, dp_n3, nd_n3, el_n3, pv_n3 = bridge.search(max_depth=depth, time_limit=30.0)
            t_n3 = time.perf_counter() - t0
            telem_n3 = bridge.get_lmr_telemetry()

            agreed = (mv_n2 == mv_n3)
            if agreed:
                agreed_count += 1

            total_nodes_n2 += nd_n2
            total_nodes_n3 += nd_n3
            total_time_n2 += t_n2
            total_time_n3 += t_n3

            total_reduced += telem_n3["reduced_moves"]
            total_researches += telem_n3["researches"]
            total_cutoffs += telem_n3["cutoffs"]

            depth_data.append({
                "id": pos_id,
                "fen": fen,
                "n2_move": mv_n2,
                "n2_score": sc_n2,
                "n2_nodes": nd_n2,
                "n2_time": t_n2,
                "n3_move": mv_n3,
                "n3_score": sc_n3,
                "n3_nodes": nd_n3,
                "n3_time": t_n3,
                "agreed": agreed,
                "telemetry": telem_n3,
            })

        node_red_pct = ((total_nodes_n2 - total_nodes_n3) / total_nodes_n2 * 100.0) if total_nodes_n2 > 0 else 0.0
        speedup = (total_time_n2 / total_time_n3) if total_time_n3 > 0 else 1.0
        agreement_pct = (agreed_count / len(positions) * 100.0)
        research_rate_pct = (total_researches / total_reduced * 100.0) if total_reduced > 0 else 0.0
        cutoff_rate_pct = (total_cutoffs / total_reduced * 100.0) if total_reduced > 0 else 0.0

        nps_n2 = int(total_nodes_n2 / total_time_n2) if total_time_n2 > 0 else 0
        nps_n3 = int(total_nodes_n3 / total_time_n3) if total_time_n3 > 0 else 0

        summary = {
            "depth": depth,
            "positions_count": len(positions),
            "total_nodes_n2": total_nodes_n2,
            "total_nodes_n3": total_nodes_n3,
            "node_reduction_pct": node_red_pct,
            "total_time_n2_sec": total_time_n2,
            "total_time_n3_sec": total_time_n3,
            "speedup_factor": speedup,
            "nps_n2": nps_n2,
            "nps_n3": nps_n3,
            "move_agreement_pct": agreement_pct,
            "agreed_count": agreed_count,
            "total_reduced": total_reduced,
            "total_researches": total_researches,
            "research_rate_pct": research_rate_pct,
            "total_cutoffs": total_cutoffs,
            "cutoff_rate_pct": cutoff_rate_pct,
        }

        results_by_depth[str(depth)] = {
            "summary": summary,
            "positions": depth_data,
        }

        print(f"Depth {depth} Summary:")
        print(f"  Nodes: N2={total_nodes_n2:,} vs N3={total_nodes_n3:,} ({node_red_pct:+.2f}% tree reduction)")
        print(f"  Time:  N2={total_time_n2:.3f}s vs N3={total_time_n3:.3f}s (Speedup: {speedup:.2f}x)")
        print(f"  NPS:   N2={nps_n2:,} vs N3={nps_n3:,}")
        print(f"  Move Agreement: {agreed_count}/{len(positions)} ({agreement_pct:.1f}%)")
        print(f"  Reduced Moves: {total_reduced:,}, Re-searches: {total_researches:,} ({research_rate_pct:.2f}%)")
        print(f"  LMR Beta Cutoffs: {total_cutoffs:,} ({cutoff_rate_pct:.2f}%)\n")

    out_file = RAW_DIR / "depth_ablation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_by_depth, f, indent=2)

    print(f"Saved complete fixed-depth ablation data to {out_file}")
    return results_by_depth


if __name__ == "__main__":
    run_depth_ablation()

