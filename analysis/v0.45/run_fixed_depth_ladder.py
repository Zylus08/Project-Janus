"""Run controlled fixed-depth experiments (depths 2, 3, 4, 5) on the diagnostic corpus."""
import json
import shutil
import time
from pathlib import Path
import chess

from janus.search import JanusSearch

def run():
    src_corpus = Path("analysis/v0.44/diagnostic_positions.json")
    dst_corpus = Path("analysis/v0.45/diagnostic_positions/diagnostic_corpus.json")
    shutil.copy(src_corpus, dst_corpus)
    print(f"Copied corpus to {dst_corpus}")

    with open(dst_corpus, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    depth_ladder = [2, 3, 4, 5]
    raw_results = []
    depth_summaries = {}

    for d in depth_ladder:
        print(f"\n--- Running Fixed-Depth Ladder: Depth {d} ---")
        agreements = 0
        total_k0_nodes = 0
        total_rfp_nodes = 0
        score_diffs = []
        depth_records = []

        for idx, item in enumerate(corpus, 1):
            fen = item["fen"]
            board = chess.Board(fen)

            # 1. K0 run (fresh instance)
            k0_engine = JanusSearch(enable_rfp=False, diagnostic_rfp=False, diagnostic_iterations=False)
            t0 = time.perf_counter()
            res_k0 = k0_engine.search(board.copy(), max_depth=d)
            k0_time = time.perf_counter() - t0

            # 2. RFP run (fresh instance)
            rfp_engine = JanusSearch(enable_rfp=True, rfp_max_depth=2, rfp_margin_per_depth=120, diagnostic_rfp=True, diagnostic_iterations=False)
            t0 = time.perf_counter()
            res_rfp = rfp_engine.search(board.copy(), max_depth=d)
            rfp_time = time.perf_counter() - t0

            k0_mv = res_k0.best_move.uci() if res_k0.best_move else None
            rfp_mv = res_rfp.best_move.uci() if res_rfp.best_move else None

            same_move = (k0_mv == rfp_mv)
            if same_move: agreements += 1

            total_k0_nodes += res_k0.nodes
            total_rfp_nodes += res_rfp.nodes
            score_diff = abs(res_k0.score - res_rfp.score)
            score_diffs.append(score_diff)

            node_reduction_pct = ((res_k0.nodes - res_rfp.nodes) / res_k0.nodes * 100.0) if res_k0.nodes > 0 else 0.0

            rec = {
                "position_id": item["id"],
                "target_depth": d,
                "fen": fen,
                "k0": {
                    "move": k0_mv,
                    "score": res_k0.score,
                    "nodes": res_k0.nodes,
                    "time_s": k0_time,
                    "pv": [m.uci() for m in res_k0.pv],
                },
                "rfp": {
                    "move": rfp_mv,
                    "score": res_rfp.score,
                    "nodes": res_rfp.nodes,
                    "time_s": rfp_time,
                    "rfp_considered": res_rfp.rfp_considered,
                    "rfp_cutoffs": res_rfp.rfp_cutoffs,
                    "pv": [m.uci() for m in res_rfp.pv],
                },
                "same_move": same_move,
                "score_diff_cp": score_diff,
                "node_reduction_pct": node_reduction_pct,
            }
            depth_records.append(rec)
            raw_results.append(rec)

        overall_red = ((total_k0_nodes - total_rfp_nodes) / total_k0_nodes * 100.0) if total_k0_nodes > 0 else 0.0
        depth_summaries[d] = {
            "depth": d,
            "total_positions": len(corpus),
            "move_agreement_count": agreements,
            "move_agreement_pct": (agreements / len(corpus)) * 100.0,
            "total_k0_nodes": total_k0_nodes,
            "total_rfp_nodes": total_rfp_nodes,
            "aggregate_node_reduction_pct": overall_red,
            "mean_score_diff_cp": sum(score_diffs) / len(score_diffs) if score_diffs else 0.0,
        }
        print(f"Depth {d} complete: Agreement={agreements}/{len(corpus)} ({depth_summaries[d]['move_agreement_pct']:.1f}%), Node Reduction={overall_red:.2f}%, Mean Score Diff={depth_summaries[d]['mean_score_diff_cp']:.1f} cp")

    # Save raw outputs
    out_raw = Path("analysis/v0.45/fixed_depth/fixed_depth_ladder_raw.json")
    with open(out_raw, "w", encoding="utf-8") as f:
        json.dump({
            "summaries": depth_summaries,
            "results": raw_results,
        }, f, indent=2)
    print(f"\nWrote full fixed-depth ladder results to {out_raw}")

if __name__ == "__main__":
    run()

