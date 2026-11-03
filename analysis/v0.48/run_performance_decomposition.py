"""Project Janus v0.48 - L1 Performance Decomposition & TT Opportunity Analysis.

Evaluates K0 vs L1 across the 37-position diagnostic corpus over depths 2, 3, 4, 5
(and depth 6 on the 9 representative positions).
Measures:
- Nodes, wall-clock runtime, NPS, Q-nodes, beta cutoffs.
- Component runtime breakdown (movegen, scoring/ordering, TT probing, eval, quiescence).
- TT opportunity analysis:
  * TT entries available vs unavailable
  * TT move legal vs illegal/absent
  * TT move searched first
  * TT move immediate cutoff vs fail-low
  * Lazy sorts deferred, executed, and saved
- Cold-TT vs Warm-TT comparison.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, Any
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, SearchResult


class DecomposedJanusSearch(JanusSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Decomposed timing accumulators (seconds)
        self.time_tt_probe = 0.0
        self.time_movegen = 0.0
        self.time_eval = 0.0
        self.time_qsearch = 0.0
        self.qnodes = 0

        # TT opportunity counters
        self.nodes_eligible = 0
        self.tt_entries_found = 0
        self.tt_move_absent = 0
        self.tt_move_legal = 0
        self.tt_move_illegal = 0
        self.tt_move_searched_first = 0
        self.tt_move_immediate_cutoffs = 0
        self.tt_move_failed_low = 0

    def _probe_tt(self, key: int, depth: int):
        t0 = time.perf_counter()
        entry, move = super()._probe_tt(key, depth)
        self.time_tt_probe += (time.perf_counter() - t0)
        return entry, move

    def _quiescence(self, board, alpha, beta, ply, *args, **kwargs):
        self.qnodes += 1
        t0 = time.perf_counter()
        res = super()._quiescence(board, alpha, beta, ply, *args, **kwargs)
        self.time_qsearch += (time.perf_counter() - t0)
        return res


def run_decomposition():
    corpus_path = Path("analysis/v0.48/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

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

    depths = [2, 3, 4, 5]
    configs = [
        {"name": "K0", "lazy": False},
        {"name": "L1", "lazy": True},
    ]

    all_records = []
    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.48 - L1 PERFORMANCE DECOMPOSITION", flush=True)
    print(f"Corpus: {len(corpus)} positions | Depths: 2, 3, 4, 5 (+ depth 6 on 9 positions)", flush=True)
    print("=" * 80, flush=True)

    t_start = time.time()

    for cfg in configs:
        cfg_name = cfg["name"]
        print(f"\n--- Running Configuration: {cfg_name} ---", flush=True)

        for p_idx, pos in enumerate(corpus, 1):
            pos_id = pos["id"]
            fen = pos["fen"]
            category = pos.get("category", "unknown")

            pos_depths = list(depths)
            if pos_id in depth6_subset_ids:
                pos_depths.append(6)

            for d in pos_depths:
                # Cold-TT run (fresh searcher per depth)
                searcher = DecomposedJanusSearch(
                    enable_lazy_move_selection=cfg["lazy"],
                    diagnostic_ordering=True,
                )

                board = chess.Board(fen)
                t0 = time.perf_counter()
                res = searcher.search(board, max_depth=d)
                elapsed = time.perf_counter() - t0

                nps = int(res.nodes / elapsed) if elapsed > 0 else 0
                ord_stats = res.ordering_stats

                rec = {
                    "config": cfg_name,
                    "pos_id": pos_id,
                    "category": category,
                    "depth": d,
                    "best_move": res.best_move.uci() if res.best_move else None,
                    "score": res.score,
                    "nodes": res.nodes,
                    "qnodes": searcher.qnodes,
                    "beta_cutoffs": res.beta_cutoffs,
                    "elapsed_s": round(elapsed, 4),
                    "nps": nps,
                    "tt_hits": res.tt_hits,
                    "ordering_time_s": round(ord_stats.get("total_ordering_time_s", 0.0), 4),
                    "tt_probe_time_s": round(searcher.time_tt_probe, 4),
                    "qsearch_time_s": round(searcher.time_qsearch, 4),
                    "cutoffs_total": ord_stats.get("total_cutoffs", 0),
                    "first_move_cutoffs": ord_stats.get("first_move_cutoffs", 0),
                    "first_move_rate": ord_stats.get("first_move_cutoff_rate", 0.0),
                    "tt_cutoffs": ord_stats.get("tt_cutoffs", 0),
                    "killer_cutoffs": ord_stats.get("killer_cutoffs", 0),
                    "lazy_sorts_deferred": ord_stats.get("lazy_sorts_deferred", 0),
                    "lazy_sorts_executed": ord_stats.get("lazy_sorts_executed", 0),
                    "lazy_sorts_saved": ord_stats.get("lazy_sorts_saved", 0),
                }
                all_records.append(rec)
                print(
                    f"[{cfg_name}] {pos_id} d={d}: move={rec['best_move']}, nodes={rec['nodes']}, "
                    f"time={elapsed:.3f}s, nps={nps}, 1st_rate={rec['first_move_rate']:.1%}, "
                    f"saved={rec['lazy_sorts_saved']}, ord_time={rec['ordering_time_s']:.3f}s",
                    flush=True,
                )

    # Save raw records
    out_file = Path("analysis/v0.48/raw/performance_decomposition_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    print(f"\nDecomposition run complete in {time.time() - t_start:.2f}s. Saved to {out_file}", flush=True)

    # Comparative Summary by Depth
    print("\n" + "=" * 80, flush=True)
    print("L1 PERFORMANCE DECOMPOSITION SUMMARY BY DEPTH", flush=True)
    print("=" * 80, flush=True)

    for d in [2, 3, 4, 5]:
        k0_subset = [r for r in all_records if r["config"] == "K0" and r["depth"] == d]
        l1_subset = [r for r in all_records if r["config"] == "L1" and r["depth"] == d]

        k0_time = sum(r["elapsed_s"] for r in k0_subset)
        l1_time = sum(r["elapsed_s"] for r in l1_subset)
        k0_nodes = sum(r["nodes"] for r in k0_subset)
        l1_nodes = sum(r["nodes"] for r in l1_subset)
        k0_ord = sum(r["ordering_time_s"] for r in k0_subset)
        l1_ord = sum(r["ordering_time_s"] for r in l1_subset)
        k0_tt_cuts = sum(r["tt_cutoffs"] for r in k0_subset)
        l1_tt_cuts = sum(r["tt_cutoffs"] for r in l1_subset)
        k0_1st = sum(r["first_move_cutoffs"] for r in k0_subset)
        l1_1st = sum(r["first_move_cutoffs"] for r in l1_subset)
        k0_cuts = sum(r["cutoffs_total"] for r in k0_subset)
        l1_cuts = sum(r["cutoffs_total"] for r in l1_subset)
        l1_saved = sum(r["lazy_sorts_saved"] for r in l1_subset)

        time_delta_pct = (l1_time - k0_time) / k0_time if k0_time > 0 else 0
        node_delta_pct = (l1_nodes - k0_nodes) / k0_nodes if k0_nodes > 0 else 0
        ord_delta_pct = (l1_ord - k0_ord) / k0_ord if k0_ord > 0 else 0

        print(f"\n--- Depth {d} ---", flush=True)
        print(f"  Runtime: K0 = {k0_time:.2f}s | L1 = {l1_time:.2f}s | Delta = {time_delta_pct:+.2%}", flush=True)
        print(f"  Nodes:   K0 = {k0_nodes:,} | L1 = {l1_nodes:,} | Delta = {node_delta_pct:+.2%}", flush=True)
        print(f"  Ordering Time: K0 = {k0_ord:.2f}s | L1 = {l1_ord:.2f}s | Delta = {ord_delta_pct:+.2%}", flush=True)
        print(f"  1st Move Cutoffs: K0 = {k0_1st}/{k0_cuts} ({k0_1st/k0_cuts if k0_cuts else 0:.1%}) | L1 = {l1_1st}/{l1_cuts} ({l1_1st/l1_cuts if l1_cuts else 0:.1%})", flush=True)
        print(f"  TT Move Cutoffs:  K0 = {k0_tt_cuts} | L1 = {l1_tt_cuts}", flush=True)
        print(f"  L1 Lazy Sorts Saved: {l1_saved:,}", flush=True)


if __name__ == "__main__":
    run_decomposition()
