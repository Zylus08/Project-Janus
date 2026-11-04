"""Fixed-time search budget ladder experiment (50ms to 3000ms) for Project Janus v0.47.

Evaluates K0 (production baseline: eager sorting) vs L1 (lazy move selection candidate)
across budgets: 50ms, 100ms, 150ms, 180ms, 250ms, 500ms, 1000ms, 3000ms
on the 37-position diagnostic corpus.
Evaluates:
- Completed nominal depth and iterations
- Total nodes and effective NPS
- Best move stability and agreement between K0 and L1
- Decision quality vs Stockfish 19 reference ladder
"""

import json
import time
from pathlib import Path
import chess

from janus.search import JanusSearch


def run_fixed_time_ladder():
    corpus_path = Path("analysis/v0.47/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # Load SF19 reference if available
    sf_ref_path = Path("analysis/v0.47/reference/stockfish_reference_ladder.json")
    sf_ref = {}
    if sf_ref_path.exists():
        with open(sf_ref_path, "r", encoding="utf-8") as f:
            sf_ref = json.load(f)

    budgets_ms = [50, 100, 150, 180, 250, 500, 1000, 3000]
    raw_results = []
    budget_summaries = {}

    print(f"Starting Fixed-Time Ladder on {len(corpus)} positions across {len(budgets_ms)} budget tiers...", flush=True)

    for b_ms in budgets_ms:
        time_limit_s = b_ms / 1000.0
        print(f"\n--- Running Fixed-Time Budget: {b_ms} ms ---", flush=True)

        tier_records = []
        agreements = 0
        depth_diffs = []
        node_ratios = []

        for item in corpus:
            pos_id = item["id"]
            fen = item["fen"]
            category = item.get("category", "unknown")
            board = chess.Board(fen)

            # 1. K0 run
            k0_searcher = JanusSearch(
                enable_lazy_move_selection=False,
                diagnostic_iterations=True,
                diagnostic_ordering=True,
            )
            t0 = time.perf_counter()
            res_k0 = k0_searcher.search(board.copy(), max_depth=64, time_limit=time_limit_s)
            k0_wall_s = time.perf_counter() - t0

            # 2. L1 run
            l1_searcher = JanusSearch(
                enable_lazy_move_selection=True,
                diagnostic_iterations=True,
                diagnostic_ordering=True,
            )
            t0 = time.perf_counter()
            res_l1 = l1_searcher.search(board.copy(), max_depth=64, time_limit=time_limit_s)
            l1_wall_s = time.perf_counter() - t0

            k0_mv = res_k0.best_move.uci() if res_k0.best_move else None
            l1_mv = res_l1.best_move.uci() if res_l1.best_move else None

            same_move = (k0_mv == l1_mv)
            if same_move:
                agreements += 1

            depth_diff = res_l1.depth - res_k0.depth
            depth_diffs.append(depth_diff)
            n_ratio = res_l1.nodes / res_k0.nodes if res_k0.nodes > 0 else 1.0
            node_ratios.append(n_ratio)

            # Compare against SF19 reference
            sf_rec = sf_ref.get(pos_id)
            sf_mv = sf_rec.get("reference_move_d14") or sf_rec.get("reference_move_d12") if sf_rec else None

            rec = {
                "pos_id": pos_id,
                "category": category,
                "budget_ms": b_ms,
                "fen": fen,
                "same_move": same_move,
                "depth_delta": depth_diff,
                "k0": {
                    "move": k0_mv,
                    "depth": res_k0.depth,
                    "score": res_k0.score,
                    "nodes": res_k0.nodes,
                    "elapsed_s": round(k0_wall_s, 4),
                    "nps": int(res_k0.nodes / k0_wall_s) if k0_wall_s > 0 else 0,
                    "completed_iterations": len([r for r in res_k0.iteration_records if r.get("completed")]),
                    "matches_sf": (k0_mv == sf_mv) if sf_mv else None,
                },
                "l1": {
                    "move": l1_mv,
                    "depth": res_l1.depth,
                    "score": res_l1.score,
                    "nodes": res_l1.nodes,
                    "elapsed_s": round(l1_wall_s, 4),
                    "nps": int(res_l1.nodes / l1_wall_s) if l1_wall_s > 0 else 0,
                    "completed_iterations": len([r for r in res_l1.iteration_records if r.get("completed")]),
                    "lazy_sorts_saved": res_l1.ordering_stats.get("lazy_sorts_saved", 0),
                    "matches_sf": (l1_mv == sf_mv) if sf_mv else None,
                },
                "stockfish_ref_move": sf_mv,
            }
            tier_records.append(rec)
            raw_results.append(rec)

        mean_k0_d = sum(r["k0"]["depth"] for r in tier_records) / len(tier_records)
        mean_l1_d = sum(r["l1"]["depth"] for r in tier_records) / len(tier_records)
        mean_k0_n = sum(r["k0"]["nodes"] for r in tier_records) / len(tier_records)
        mean_l1_n = sum(r["l1"]["nodes"] for r in tier_records) / len(tier_records)
        l1_sf_matches = sum(1 for r in tier_records if r["l1"]["matches_sf"] is True)
        k0_sf_matches = sum(1 for r in tier_records if r["k0"]["matches_sf"] is True)
        total_sf_eval = sum(1 for r in tier_records if r["stockfish_ref_move"] is not None)

        budget_summaries[b_ms] = {
            "budget_ms": b_ms,
            "total_positions": len(corpus),
            "move_agreement_count": agreements,
            "move_agreement_pct": round((agreements / len(corpus)) * 100.0, 2),
            "mean_k0_depth": round(mean_k0_d, 2),
            "mean_l1_depth": round(mean_l1_d, 2),
            "mean_depth_delta": round(sum(depth_diffs) / len(depth_diffs), 3),
            "mean_k0_nodes": int(mean_k0_n),
            "mean_l1_nodes": int(mean_l1_n),
            "node_delta_pct": round((mean_l1_n - mean_k0_n) / mean_k0_n * 100.0, 2) if mean_k0_n > 0 else 0,
            "k0_sf_agreement": f"{k0_sf_matches}/{total_sf_eval} ({k0_sf_matches/total_sf_eval:.1%})" if total_sf_eval else "N/A",
            "l1_sf_agreement": f"{l1_sf_matches}/{total_sf_eval} ({l1_sf_matches/total_sf_eval:.1%})" if total_sf_eval else "N/A",
        }

        print(
            f"Budget {b_ms:4d}ms: Agreement={agreements:2d}/{len(corpus)} ({agreements/len(corpus)*100:5.1f}%) | "
            f"Mean Depths: K0={mean_k0_d:.2f}, L1={mean_l1_d:.2f} (delta={mean_l1_d - mean_k0_d:+.2f}) | "
            f"SF19 Agreement: K0={k0_sf_matches}/{total_sf_eval}, L1={l1_sf_matches}/{total_sf_eval}",
            flush=True,
        )

    out_file = Path("analysis/v0.47/raw/fixed_time_ladder_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summaries": budget_summaries, "results": raw_results}, f, indent=2)

    print(f"\nAll fixed-time budget tiers completed! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_fixed_time_ladder()

