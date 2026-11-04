"""Project Janus v0.50 - Native Performance & Fixed-Time Experiments (Phase I).

Evaluates Native N2 across the 7 established fixed-time budget tiers:
[50ms, 100ms, 180ms, 250ms, 500ms, 1000ms, 3000ms]
across all 37 diagnostic positions.

For each tier:
- Mean completed depth
- Total & mean nodes searched
- Mean effective NPS
- Best move match vs Stockfish 19 reference move
- Best move match vs Python K0 baseline (from v0.49 freeze)
- Writes raw results to analysis/v0.50/raw/native_performance_raw.json
"""

import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))

from janus_native_bridge import NativeEngineBridge


def run_native_fixed_time():
    corpus_path = Path("analysis/v0.50/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    ladder_path = Path("analysis/v0.50/reference/stockfish_reference_ladder.json")
    with open(ladder_path, "r", encoding="utf-8") as f:
        sf_ladder = json.load(f)

    # Load v0.49 K0 reference for exact cross-comparison
    v49_raw_path = Path("analysis/v0.49/raw/fixed_time_validation_raw.json")
    k0_ref_by_budget_pos = {}
    if v49_raw_path.exists():
        with open(v49_raw_path, "r", encoding="utf-8") as f:
            v49_data = json.load(f)
            for rec in v49_data.get("results", []):
                k0_ref_by_budget_pos[(rec["budget_ms"], rec["pos_id"])] = rec

    bridge = NativeEngineBridge()

    tiers_ms = [50, 100, 180, 250, 500, 1000, 3000]
    all_tier_summaries = {}
    all_tier_records = []

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.50 - NATIVE FIXED-TIME EVALUATION (N2)", flush=True)
    print(f"Testing {len(corpus)} positions across 7 budget tiers: {tiers_ms}", flush=True)
    print("=" * 80, flush=True)

    for budget_ms in tiers_ms:
        time_limit_sec = budget_ms / 1000.0
        print(f"\n--- Testing Budget Tier: {budget_ms} ms ({time_limit_sec:.3f} s) ---", flush=True)

        tier_records = []
        total_nodes = 0
        total_time = 0.0
        total_depth = 0
        sf_matches = 0
        k0_matches = 0

        for item in corpus:
            pos_id = item["id"]
            fen = item["fen"]
            sf_ref = sf_ladder.get(pos_id, {})
            sf_move = sf_ref.get("reference_move_d14") or sf_ref.get("reference_move_d12")

            bridge.set_fen(fen)
            t0 = time.perf_counter()
            best_mv, score, depth, nodes, elapsed = bridge.search(max_depth=64, time_limit=time_limit_sec)
            actual_time = time.perf_counter() - t0

            total_nodes += nodes
            total_time += actual_time
            total_depth += depth

            is_sf_match = (best_mv == sf_move) if best_mv and sf_move else False
            if is_sf_match:
                sf_matches += 1

            k0_rec = k0_ref_by_budget_pos.get((budget_ms, pos_id), {})
            k0_move = k0_rec.get("k0_move")
            k0_depth = k0_rec.get("k0_depth")
            is_k0_match = (best_mv == k0_move) if best_mv and k0_move else False
            if is_k0_match:
                k0_matches += 1

            rec = {
                "budget_ms": budget_ms,
                "pos_id": pos_id,
                "fen": fen,
                "n2_move": best_mv,
                "n2_score": score,
                "n2_depth": depth,
                "n2_nodes": nodes,
                "n2_time": actual_time,
                "sf_move": sf_move,
                "sf_match": is_sf_match,
                "k0_move": k0_move,
                "k0_depth": k0_depth,
                "k0_match": is_k0_match,
            }
            tier_records.append(rec)
            all_tier_records.append(rec)

        n_pos = len(corpus)
        mean_depth = total_depth / n_pos
        mean_nps = int(total_nodes / total_time) if total_time > 0 else 0
        sf_pct = (sf_matches / n_pos) * 100.0
        k0_pct = (k0_matches / n_pos) * 100.0

        summary = {
            "budget_ms": budget_ms,
            "total_positions": n_pos,
            "mean_depth": round(mean_depth, 2),
            "total_nodes": total_nodes,
            "mean_nodes_per_pos": int(total_nodes / n_pos),
            "total_time_sec": round(total_time, 3),
            "mean_nps": mean_nps,
            "sf_matches": sf_matches,
            "sf_match_pct": round(sf_pct, 1),
            "k0_matches": k0_matches,
            "k0_match_pct": round(k0_pct, 1),
        }
        all_tier_summaries[str(budget_ms)] = summary

        print(f"Tier {budget_ms:4d}ms: Mean Depth={mean_depth:.2f} | NPS={mean_nps:,} | "
              f"SF Match={sf_matches}/{n_pos} ({sf_pct:.1f}%) | K0 Match={k0_matches}/{n_pos} ({k0_pct:.1f}%)",
              flush=True)

    output = {
        "summaries": all_tier_summaries,
        "results": all_tier_records,
    }

    out_file = Path("analysis/v0.50/raw/native_performance_raw.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved raw performance data to {out_file}", flush=True)


if __name__ == "__main__":
    run_native_fixed_time()

