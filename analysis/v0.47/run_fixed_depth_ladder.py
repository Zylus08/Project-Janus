"""Fixed-depth search ladder execution script for Project Janus v0.47.

Evaluates K0 (production baseline: eager sorting) and L1 (candidate: lazy move selection)
across depths 2, 3, 4, 5 on the 37-position diagnostic corpus.
Records: nodes, NPS, elapsed_time, cutoffs, first-move cutoff rate, ordering time,
lazy sorts deferred, lazy sorts executed, lazy sorts saved, best move, and score.
"""

import sys
import os
import json
import time
from pathlib import Path
import chess

from janus.search import JanusSearch


def run_ladder():
    corpus_path = Path("analysis/v0.47/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        positions = json.load(f)

    depths = [2, 3, 4, 5]
    configs = [
        {"name": "K0", "enable_lazy_move_selection": False},
        {"name": "L1", "enable_lazy_move_selection": True},
    ]

    results = []
    print(f"Starting Fixed-Depth Search Ladder across {len(positions)} positions...", flush=True)
    start_total = time.time()

    for cfg in configs:
        cfg_name = cfg["name"]
        print(f"\n--- Running Configuration: {cfg_name} ---", flush=True)

        for pos in positions:
            pos_id = pos["id"]
            fen = pos["fen"]
            category = pos.get("category", "unknown")

            for d in depths:
                # Initialize searcher per position to avoid TT contamination between positions
                searcher = JanusSearch(
                    enable_lazy_move_selection=cfg["enable_lazy_move_selection"],
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
                f_rate = res.ordering_stats.get("first_move_cutoff_rate", 0.0)
                saved = res.ordering_stats.get("lazy_sorts_saved", 0)
                print(
                    f"[{cfg_name}] {pos_id} d={d}: move={record['best_move']}, nodes={res.nodes}, "
                    f"time={elapsed:.3f}s, nps={nps}, first_rate={f_rate:.1%}, saved={saved}",
                    flush=True,
                )

    out_file = Path("analysis/v0.47/raw/fixed_depth_ladder.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nCompleted {len(results)} runs in {time.time() - start_total:.2f}s.", flush=True)
    print(f"Results saved to {out_file}", flush=True)

    # Comparative summary
    print("\n=== COMPARATIVE SUMMARY BY DEPTH ===", flush=True)
    for d in depths:
        k0_subset = [r for r in results if r["config"] == "K0" and r["depth"] == d]
        l1_subset = [r for r in results if r["config"] == "L1" and r["depth"] == d]

        k0_nodes = sum(r["nodes"] for r in k0_subset)
        l1_nodes = sum(r["nodes"] for r in l1_subset)
        k0_time = sum(r["elapsed_s"] for r in k0_subset)
        l1_time = sum(r["elapsed_s"] for r in l1_subset)

        k0_moves = {r["pos_id"]: r["best_move"] for r in k0_subset}
        l1_moves = {r["pos_id"]: r["best_move"] for r in l1_subset}
        k0_scores = {r["pos_id"]: r["score"] for r in k0_subset}
        l1_scores = {r["pos_id"]: r["score"] for r in l1_subset}

        move_agree = sum(1 for pid in k0_moves if k0_moves[pid] == l1_moves[pid])
        score_agree = sum(1 for pid in k0_scores if k0_scores[pid] == l1_scores[pid])
        l1_saved = sum(r["ordering_stats"].get("lazy_sorts_saved", 0) for r in l1_subset)

        node_pct = (l1_nodes - k0_nodes) / k0_nodes if k0_nodes > 0 else 0
        time_pct = (l1_time - k0_time) / k0_time if k0_time > 0 else 0

        print(f"\nDepth {d}:", flush=True)
        print(f"  K0: Time = {k0_time:.2f}s, Nodes = {k0_nodes:,}, NPS = {int(k0_nodes/k0_time) if k0_time > 0 else 0:,}", flush=True)
        print(f"  L1: Time = {l1_time:.2f}s, Nodes = {l1_nodes:,}, NPS = {int(l1_nodes/l1_time) if l1_time > 0 else 0:,}", flush=True)
        print(f"  Delta: Time = {time_pct:+.2%}, Nodes = {node_pct:+.2%}", flush=True)
        print(f"  Move Agreement: {move_agree}/{len(k0_moves)} ({move_agree/len(k0_moves):.1%})", flush=True)
        print(f"  Score Agreement: {score_agree}/{len(k0_scores)} ({score_agree/len(k0_scores):.1%})", flush=True)
        print(f"  L1 Lazy Sorts Saved: {l1_saved:,}", flush=True)


if __name__ == "__main__":
    run_ladder()

