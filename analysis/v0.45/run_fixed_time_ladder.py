"""Execute the fixed-time search budget ladder experiment (50ms to 1000ms) on the diagnostic corpus."""
import json
import time
from pathlib import Path
import chess

from janus.search import JanusSearch

def run():
    corpus_path = Path("analysis/v0.45/diagnostic_positions/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    budgets_ms = [50, 100, 150, 180, 250, 500, 1000]
    raw_results = []
    budget_summaries = {}

    print(f"Loaded {len(corpus)} positions. Evaluating {len(budgets_ms)} budget tiers...")

    for b_ms in budgets_ms:
        time_limit_s = b_ms / 1000.0
        print(f"\n--- Running Fixed-Time Budget: {b_ms} ms ---")

        agreements = 0
        diff_depth_count = 0
        cat_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        tier_results = []

        for idx, item in enumerate(corpus, 1):
            fen = item["fen"]
            board = chess.Board(fen)

            # 1. K0 run (fresh instance)
            k0_engine = JanusSearch(enable_rfp=False, diagnostic_rfp=False, diagnostic_iterations=True)
            t0 = time.perf_counter()
            res_k0 = k0_engine.search(board.copy(), max_depth=64, time_limit=time_limit_s)
            k0_wall_s = time.perf_counter() - t0

            # 2. RFP run (fresh instance)
            rfp_engine = JanusSearch(enable_rfp=True, rfp_max_depth=2, rfp_margin_per_depth=120, diagnostic_rfp=True, diagnostic_iterations=True)
            t0 = time.perf_counter()
            res_rfp = rfp_engine.search(board.copy(), max_depth=64, time_limit=time_limit_s)
            rfp_wall_s = time.perf_counter() - t0

            k0_mv = res_k0.best_move.uci() if res_k0.best_move else None
            rfp_mv = res_rfp.best_move.uci() if res_rfp.best_move else None

            same_move = (k0_mv == rfp_mv)
            if same_move: agreements += 1

            depth_diff = res_rfp.depth - res_k0.depth
            if depth_diff != 0: diff_depth_count += 1

            # Categorization:
            # D — Stable agreement: same move, score difference < 50 cp
            # C — Search-score divergence: same move, score difference >= 50 cp
            # A — Iteration-boundary divergence: different moves under fixed-time, but different completed depths
            # B — Same-depth search divergence: different moves despite same completed depth
            # E — Unresolved
            score_diff = abs(res_k0.score - res_rfp.score)

            if same_move:
                if score_diff < 50:
                    cat = "D"
                else:
                    cat = "C"
            else:
                if res_k0.depth != res_rfp.depth:
                    cat = "A"
                else:
                    cat = "B"

            cat_counts[cat] += 1

            rec = {
                "position_id": item["id"],
                "budget_ms": b_ms,
                "fen": fen,
                "classification": cat,
                "k0": {
                    "move": k0_mv,
                    "depth": res_k0.depth,
                    "score": res_k0.score,
                    "nodes": res_k0.nodes,
                    "elapsed_s": k0_wall_s,
                    "pv": [m.uci() for m in res_k0.pv],
                    "completed_iterations": len([r for r in res_k0.iteration_records if r["completed"]]),
                    "aborted_iterations": len([r for r in res_k0.iteration_records if r["aborted"]]),
                    "iteration_trace": res_k0.iteration_records,
                },
                "rfp": {
                    "move": rfp_mv,
                    "depth": res_rfp.depth,
                    "score": res_rfp.score,
                    "nodes": res_rfp.nodes,
                    "elapsed_s": rfp_wall_s,
                    "pv": [m.uci() for m in res_rfp.pv],
                    "rfp_considered": res_rfp.rfp_considered,
                    "rfp_cutoffs": res_rfp.rfp_cutoffs,
                    "completed_iterations": len([r for r in res_rfp.iteration_records if r["completed"]]),
                    "aborted_iterations": len([r for r in res_rfp.iteration_records if r["aborted"]]),
                    "iteration_trace": res_rfp.iteration_records,
                },
                "same_move": same_move,
                "depth_delta": depth_diff,
                "score_diff_cp": score_diff,
            }
            tier_results.append(rec)
            raw_results.append(rec)

        budget_summaries[b_ms] = {
            "budget_ms": b_ms,
            "total_positions": len(corpus),
            "move_agreement_count": agreements,
            "move_agreement_pct": (agreements / len(corpus)) * 100.0,
            "mean_k0_depth": sum(r["k0"]["depth"] for r in tier_results) / len(tier_results),
            "mean_rfp_depth": sum(r["rfp"]["depth"] for r in tier_results) / len(tier_results),
            "depth_delta_positions": diff_depth_count,
            "classification_counts": cat_counts,
        }

        print(f"Budget {b_ms:4d}ms: Agreement={agreements:2d}/{len(corpus)} ({agreements/len(corpus)*100:5.1f}%) | Depths: K0={budget_summaries[b_ms]['mean_k0_depth']:.2f}, RFP={budget_summaries[b_ms]['mean_rfp_depth']:.2f} | Cats: A={cat_counts['A']} B={cat_counts['B']} C={cat_counts['C']} D={cat_counts['D']}")

    # Save outputs
    out_raw = Path("analysis/v0.45/fixed_time/fixed_time_ladder_raw.json")
    with open(out_raw, "w", encoding="utf-8") as f:
        json.dump({
            "summaries": budget_summaries,
            "results": raw_results,
        }, f, indent=2)

    # Export telemetry JSONL
    telemetry_file = Path("analysis/v0.45/telemetry/iteration_records.jsonl")
    with open(telemetry_file, "w", encoding="utf-8") as f:
        for r in raw_results:
            for it in r["k0"]["iteration_trace"]:
                it["engine"] = "K0"
                it["budget_ms"] = r["budget_ms"]
                it["position_id"] = r["position_id"]
                f.write(json.dumps(it) + "\n")
            for it in r["rfp"]["iteration_trace"]:
                it["engine"] = "RFP"
                it["budget_ms"] = r["budget_ms"]
                it["position_id"] = r["position_id"]
                f.write(json.dumps(it) + "\n")

    print(f"\nSaved raw results to {out_raw} and iteration telemetry to {telemetry_file}")

if __name__ == "__main__":
    run()

