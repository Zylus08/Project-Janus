"""Fixed-depth search ladder execution script for Project Janus v0.46.

Evaluates K0 (production baseline) and RFP (experimental baseline) across depths 2, 3, 4, 5
(and depth 6 on a representative subset of positions).
Records: nodes, NPS, elapsed_time, cutoffs, first-move cutoff rate, ordering time, TT hits.
"""

import sys
import os
import json
import time
from pathlib import Path
import chess

from janus.search import JanusSearch


def run_ladder():
    corpus_path = Path("analysis/v0.46/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        positions = json.load(f)

    depths = [2, 3, 4, 5]
    depth6_subset_ids = [
        "pos_01_p02_b_e4_c5_p30",
        "pos_04_p06_b_e4_e5_p16",
        "pos_07_p08_b_e4_c5_p46",
        "pos_10_p11_w_d4_d5_p35",
        "pos_15_p15_w_e4_e6_p43",
        "pos_20_p19_w_e4_c5_p41",
        "pos_25_p27_b_d4_d5_p22",
        "pos_30_p31_w_d4_nf6_p49",
        "pos_35_p38_b_e4_c5_p50",
    ]

    configs = [
        {"name": "K0", "enable_rfp": False},
        {"name": "RFP", "enable_rfp": True, "rfp_max_depth": 2, "rfp_margin_per_depth": 120},
    ]

    results = []

    print(f"Starting Fixed-Depth Search Ladder across {len(positions)} positions...")
    start_total = time.time()

    for cfg in configs:
        cfg_name = cfg["name"]
        print(f"\n--- Running Configuration: {cfg_name} ---")

        for pos in positions:
            pos_id = pos["id"]
            fen = pos["fen"]
            category = pos.get("category", "unknown")

            pos_depths = list(depths)
            if pos_id in depth6_subset_ids:
                pos_depths.append(6)

            for d in pos_depths:
                # Initialize searcher per position to avoid TT contamination between positions
                searcher = JanusSearch(
                    enable_rfp=cfg["enable_rfp"],
                    rfp_max_depth=cfg.get("rfp_max_depth", 2),
                    rfp_margin_per_depth=cfg.get("rfp_margin_per_depth", 120),
                    diagnostic_ordering=True,
                )

                board = chess.Board(fen)
                t0 = time.perf_counter()
                res = searcher.search(board, max_depth=d)
                elapsed = time.perf_counter() - t0

                nps = int(res.nodes / elapsed) if elapsed > 0 else 0

                record = {
                    "config": cfg_name,
                    "pos_id": pos_id,
                    "category": category,
                    "depth": d,
                    "best_move": res.best_move.uci() if res.best_move else None,
                    "score": res.score,
                    "nodes": res.nodes,
                    "elapsed_s": round(elapsed, 4),
                    "nps": nps,
                    "tt_hits": res.tt_hits,
                    "beta_cutoffs": res.beta_cutoffs,
                    "ordering_stats": res.ordering_stats,
                }
                results.append(record)
                print(f"[{cfg_name}] {pos_id} d={d}: move={record['best_move']}, nodes={res.nodes}, time={elapsed:.3f}s, nps={nps}, first_move_rate={res.ordering_stats.get('first_move_cutoff_rate', 0):.2%}")

    out_file = Path("analysis/v0.46/raw/fixed_depth_ladder.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nCompleted {len(results)} runs in {time.time() - start_total:.2f}s.")
    print(f"Results saved to {out_file}")


if __name__ == "__main__":
    run_ladder()
