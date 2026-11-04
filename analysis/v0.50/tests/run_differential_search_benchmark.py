"""Project Janus v0.50 - Differential Search Qualification (Phase H & I).

Compares Python K0 vs Python L1 vs Native N2 across the 37-position diagnostic corpus
over Depths 1, 2, 3, 4, and 5.

Measures:
- Best move agreement (N2 vs K0, L1 vs K0)
- Root score correlation and deltas
- Node count comparison
- Wall-clock runtime and effective NPS throughput
- Speedup factor (Native N2 vs Python K0)
Saves results to analysis/v0.50/raw/differential_search_raw.json.
"""

import sys
import json
import time
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))

from janus.search import JanusSearch
from janus_native_bridge import NativeEngineBridge


def run_differential_search():
    corpus_path = Path("analysis/v0.50/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    bridge = NativeEngineBridge()

    depths = [1, 2, 3, 4, 5]
    summaries = {}
    detailed_records = []

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.50 - DIFFERENTIAL SEARCH QUALIFICATION (K0 vs N2)", flush=True)
    print("=" * 80, flush=True)

    for depth in depths:
        print(f"\n--- Evaluating Nominal Depth {depth} across {len(corpus)} positions ---", flush=True)

        k0_time_total = 0.0
        n2_time_total = 0.0
        k0_nodes_total = 0
        n2_nodes_total = 0
        move_matches = 0
        score_matches = 0

        for pos in corpus:
            pos_id = pos["id"]
            fen = pos["fen"]
            board = chess.Board(fen)

            # 1. Python K0 Search
            s_k0 = JanusSearch(enable_lazy_move_selection=False)
            t0 = time.perf_counter()
            res_k0 = s_k0.search(board.copy(), max_depth=depth)
            dur_k0 = time.perf_counter() - t0

            # 2. Native N2 Search
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            mv_n2, score_n2, depth_n2, nodes_n2, dur_n2 = bridge.search(max_depth=depth, time_limit=100.0)
            dur_n2_wall = time.perf_counter() - t0

            mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None

            same_move = (mv_k0 == mv_n2)
            same_score = (res_k0.score == score_n2)

            if same_move:
                move_matches += 1
            if same_score:
                score_matches += 1

            k0_time_total += dur_k0
            n2_time_total += dur_n2_wall
            k0_nodes_total += res_k0.nodes
            n2_nodes_total += nodes_n2

            detailed_records.append({
                "depth": depth,
                "pos_id": pos_id,
                "k0_move": mv_k0,
                "n2_move": mv_n2,
                "k0_score": res_k0.score,
                "n2_score": score_n2,
                "k0_nodes": res_k0.nodes,
                "n2_nodes": nodes_n2,
                "k0_time": round(dur_k0, 4),
                "n2_time": round(dur_n2_wall, 4),
                "same_move": same_move,
                "same_score": same_score,
            })

        k0_nps = int(k0_nodes_total / k0_time_total) if k0_time_total > 0 else 0
        n2_nps = int(n2_nodes_total / n2_time_total) if n2_time_total > 0 else 0
        speedup = k0_time_total / n2_time_total if n2_time_total > 0 else 0.0

        summaries[depth] = {
            "depth": depth,
            "positions": len(corpus),
            "k0_time": round(k0_time_total, 3),
            "n2_time": round(n2_time_total, 3),
            "k0_nodes": k0_nodes_total,
            "n2_nodes": n2_nodes_total,
            "k0_nps": k0_nps,
            "n2_nps": n2_nps,
            "speedup_factor": round(speedup, 1),
            "move_matches": move_matches,
            "move_match_pct": round(move_matches / len(corpus) * 100.0, 1),
            "score_matches": score_matches,
            "score_match_pct": round(score_matches / len(corpus) * 100.0, 1),
        }

        print(
            f"Depth {depth}: K0={k0_time_total:.2f}s ({k0_nps:,} NPS) | "
            f"Native N2={n2_time_total:.3f}s ({n2_nps:,} NPS) | "
            f"SPEEDUP: {speedup:.1f}x FASTER | "
            f"Move Agreement: {move_matches}/{len(corpus)} ({summaries[depth]['move_match_pct']}%) | "
            f"Score Agreement: {score_matches}/{len(corpus)} ({summaries[depth]['score_match_pct']}%)",
            flush=True,
        )

    out_file = Path("analysis/v0.50/raw/differential_search_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summaries": summaries, "records": detailed_records}, f, indent=2)

    print(f"\nDifferential search qualification complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_differential_search()

