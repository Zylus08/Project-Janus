"""Project Janus v0.49 - Baseline Reproduction & Telemetry Capture (Phase A4).

Reproduces K0 and L1 performance on the inherited 37-position corpus
across Depths 2, 3, 4, 5 (and Depth 6 representative subset).
Saves detailed raw telemetry to analysis/v0.49/raw/baseline_reproduction_raw.json.
"""

import sys
import os
import json
import time
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch


def run_baseline_reproduction():
    corpus_path = Path("analysis/v0.49/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # 9 representative positions for Depth 6
    rep_corpus = corpus[:9]

    depths = [2, 3, 4, 5]
    records = []
    summaries = {}

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.49 - BASELINE PERFORMANCE REPRODUCTION (K0 vs L1)", flush=True)
    print("=" * 80, flush=True)

    for depth in depths:
        print(f"\n--- Running Nominal Depth {depth} across all {len(corpus)} positions ---", flush=True)

        k0_nodes_total = 0
        l1_nodes_total = 0
        k0_time_total = 0.0
        l1_time_total = 0.0
        k0_ordering_time = 0.0
        l1_ordering_time = 0.0
        k0_cutoffs_total = 0
        l1_cutoffs_total = 0
        l1_deferred_total = 0
        l1_executed_total = 0
        move_agreements = 0

        for pos in corpus:
            pos_id = pos["id"]
            fen = pos["fen"]
            board = chess.Board(fen)

            # Search K0
            s_k0 = JanusSearch(enable_lazy_move_selection=False, diagnostic_ordering=True)
            t0 = time.perf_counter()
            res_k0 = s_k0.search(board.copy(), max_depth=depth)
            k0_dur = time.perf_counter() - t0

            # Search L1
            s_l1 = JanusSearch(enable_lazy_move_selection=True, diagnostic_ordering=True)
            t0 = time.perf_counter()
            res_l1 = s_l1.search(board.copy(), max_depth=depth)
            l1_dur = time.perf_counter() - t0

            mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None
            mv_l1 = res_l1.best_move.uci() if res_l1.best_move else None

            same_move = (mv_k0 == mv_l1)
            if same_move:
                move_agreements += 1

            k0_nodes_total += res_k0.nodes
            l1_nodes_total += res_l1.nodes
            k0_time_total += k0_dur
            l1_time_total += l1_dur
            k0_ordering_time += s_k0.total_ordering_time
            l1_ordering_time += s_l1.total_ordering_time
            k0_cutoffs_total += s_k0.beta_cutoffs
            l1_cutoffs_total += s_l1.beta_cutoffs
            l1_deferred_total += s_l1.lazy_sorts_deferred
            l1_executed_total += s_l1.lazy_sorts_executed

            records.append({
                "depth": depth,
                "pos_id": pos_id,
                "k0_nodes": res_k0.nodes,
                "l1_nodes": res_l1.nodes,
                "k0_time": round(k0_dur, 4),
                "l1_time": round(l1_dur, 4),
                "k0_move": mv_k0,
                "l1_move": mv_l1,
                "k0_score": res_k0.score,
                "l1_score": res_l1.score,
                "same_move": same_move,
                "k0_ordering_time": round(s_k0.total_ordering_time, 4),
                "l1_ordering_time": round(s_l1.total_ordering_time, 4),
                "k0_beta_cutoffs": s_k0.beta_cutoffs,
                "l1_beta_cutoffs": s_l1.beta_cutoffs,
                "l1_lazy_sorts_deferred": s_l1.lazy_sorts_deferred,
                "l1_lazy_sorts_executed": s_l1.lazy_sorts_executed,
            })

        runtime_delta_pct = (l1_time_total - k0_time_total) / k0_time_total * 100.0
        node_delta_pct = (l1_nodes_total - k0_nodes_total) / k0_nodes_total * 100.0
        ordering_delta_pct = (l1_ordering_time - k0_ordering_time) / k0_ordering_time * 100.0 if k0_ordering_time > 0 else 0.0

        summaries[depth] = {
            "depth": depth,
            "positions": len(corpus),
            "k0_time_total": round(k0_time_total, 3),
            "l1_time_total": round(l1_time_total, 3),
            "runtime_delta_pct": round(runtime_delta_pct, 2),
            "k0_nodes_total": k0_nodes_total,
            "l1_nodes_total": l1_nodes_total,
            "node_delta_pct": round(node_delta_pct, 2),
            "k0_ordering_time": round(k0_ordering_time, 3),
            "l1_ordering_time": round(l1_ordering_time, 3),
            "ordering_delta_pct": round(ordering_delta_pct, 2),
            "move_agreement": move_agreements,
            "move_agreement_pct": round(move_agreements / len(corpus) * 100.0, 1),
            "l1_sorts_saved": l1_deferred_total - l1_executed_total,
        }

        print(
            f"Depth {depth}: K0={k0_time_total:.2f}s ({k0_nodes_total} nodes) | "
            f"L1={l1_time_total:.2f}s ({l1_nodes_total} nodes) | "
            f"Time Delta: {runtime_delta_pct:+.2f}% | Ordering Delta: {ordering_delta_pct:+.2f}% | "
            f"Agreement: {move_agreements}/{len(corpus)} ({summaries[depth]['move_agreement_pct']}%) | "
            f"Sorts Saved: {l1_deferred_total - l1_executed_total}",
            flush=True,
        )

    # Depth 6 on representative subset
    print("\n--- Running Nominal Depth 6 on representative subset (9 positions) ---", flush=True)
    k0_n6 = 0
    l1_n6 = 0
    k0_t6 = 0.0
    l1_t6 = 0.0
    k0_ord6 = 0.0
    l1_ord6 = 0.0
    agree6 = 0
    # rep_corpus is corpus[:9]

    for pos in rep_corpus:
        pos_id = pos["id"]
        fen = pos["fen"]
        board = chess.Board(fen)

        s_k0 = JanusSearch(enable_lazy_move_selection=False, diagnostic_ordering=True)
        t0 = time.perf_counter()
        res_k0 = s_k0.search(board.copy(), max_depth=6)
        k0_dur = time.perf_counter() - t0

        s_l1 = JanusSearch(enable_lazy_move_selection=True, diagnostic_ordering=True)
        t0 = time.perf_counter()
        res_l1 = s_l1.search(board.copy(), max_depth=6)
        l1_dur = time.perf_counter() - t0

        mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None
        mv_l1 = res_l1.best_move.uci() if res_l1.best_move else None

        same_move = (mv_k0 == mv_l1)
        if same_move:
            agree6 += 1

        k0_n6 += res_k0.nodes
        l1_n6 += res_l1.nodes
        k0_t6 += k0_dur
        l1_t6 += l1_dur
        k0_ord6 += s_k0.total_ordering_time
        l1_ord6 += s_l1.total_ordering_time

        records.append({
            "depth": 6,
            "pos_id": pos_id,
            "k0_nodes": res_k0.nodes,
            "l1_nodes": res_l1.nodes,
            "k0_time": round(k0_dur, 4),
            "l1_time": round(l1_dur, 4),
            "k0_move": mv_k0,
            "l1_move": mv_l1,
            "k0_score": res_k0.score,
            "l1_score": res_l1.score,
            "same_move": same_move,
            "k0_ordering_time": round(s_k0.total_ordering_time, 4),
            "l1_ordering_time": round(s_l1.total_ordering_time, 4),
        })

    summaries[6] = {
        "depth": 6,
        "positions": len(rep_corpus),
        "k0_time_total": round(k0_t6, 3),
        "l1_time_total": round(l1_t6, 3),
        "runtime_delta_pct": round((l1_t6 - k0_t6) / k0_t6 * 100.0, 2),
        "k0_nodes_total": k0_n6,
        "l1_nodes_total": l1_n6,
        "node_delta_pct": round((l1_n6 - k0_n6) / k0_n6 * 100.0, 2),
        "k0_ordering_time": round(k0_ord6, 3),
        "l1_ordering_time": round(l1_ord6, 3),
        "ordering_delta_pct": round((l1_ord6 - k0_ord6) / k0_ord6 * 100.0, 2) if k0_ord6 > 0 else 0.0,
        "move_agreement": agree6,
        "move_agreement_pct": round(agree6 / len(rep_corpus) * 100.0, 1),
    }

    print(
        f"Depth 6: K0={k0_t6:.2f}s ({k0_n6} nodes) | "
        f"L1={l1_t6:.2f}s ({l1_n6} nodes) | "
        f"Time Delta: {summaries[6]['runtime_delta_pct']:+.2f}% | "
        f"Ordering Delta: {summaries[6]['ordering_delta_pct']:+.2f}% | "
        f"Agreement: {agree6}/{len(rep_corpus)} ({summaries[6]['move_agreement_pct']}%)",
        flush=True,
    )

    out_file = Path("analysis/v0.49/raw/baseline_reproduction_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summaries": summaries, "records": records}, f, indent=2)

    print(f"\nBaseline reproduction complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_baseline_reproduction()
