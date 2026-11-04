"""Project Janus v0.50 - Tactical Regression Qualification.

Evaluates Python K0 and Native N2 on the 12-position tactical regression corpus:
- Mate-in-2, hanging piece, forks, skewers, pins, pawn promotions, stalemate avoidance.
- Evaluates solve rate at Depth 4 and Depth 5.
- Measures speedup and node throughput.
- Writes raw output to analysis/v0.50/raw/tactical_regression_raw.json.
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


def run_tactical_regression():
    corpus_path = Path("analysis/v0.50/corpus/tactical_regression_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    bridge = NativeEngineBridge()
    results = []

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.50 - TACTICAL REGRESSION QUALIFICATION (K0 vs N2)", flush=True)
    print(f"Loaded {len(corpus)} tactical positions", flush=True)
    print("=" * 80, flush=True)

    for depth in [4, 5]:
        print(f"\n--- Running at Depth {depth} ---", flush=True)
        k0_solved = 0
        n2_solved = 0
        agreed = 0
        k0_total_nodes = 0
        n2_total_nodes = 0
        k0_total_time = 0.0
        n2_total_time = 0.0

        depth_records = []

        for item in corpus:
            fen = item["fen"]
            sol = item["solution"]
            tid = item["id"]

            # 1. Python K0
            py_board = chess.Board(fen)
            k0_searcher = JanusSearch(enable_lazy_move_selection=False, enable_rfp=False)
            t0 = time.perf_counter()
            k0_res = k0_searcher.search(py_board, max_depth=depth, time_limit=60.0)
            k0_elapsed = time.perf_counter() - t0
            k0_move = k0_res.best_move.uci() if k0_res.best_move else None
            k0_nodes = k0_res.nodes
            k0_score = k0_res.score

            # 2. Native N2
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            n2_move, n2_score, n2_depth, n2_nodes, n2_elapsed = bridge.search(max_depth=depth, time_limit=60.0)

            k0_total_nodes += k0_nodes
            n2_total_nodes += n2_nodes
            k0_total_time += k0_elapsed
            n2_total_time += n2_elapsed

            k0_is_correct = (k0_move.lower() == sol.lower()) if k0_move else False
            n2_is_correct = (n2_move.lower() == sol.lower()) if n2_move else False
            moves_match = (k0_move == n2_move)

            if k0_is_correct:
                k0_solved += 1
            if n2_is_correct:
                n2_solved += 1
            if moves_match:
                agreed += 1

            record = {
                "id": tid,
                "theme": item["theme"],
                "fen": fen,
                "solution": sol,
                "depth": depth,
                "k0_move": k0_move,
                "k0_score": k0_score,
                "k0_nodes": k0_nodes,
                "k0_time": k0_elapsed,
                "k0_correct": k0_is_correct,
                "n2_move": n2_move,
                "n2_score": n2_score,
                "n2_nodes": n2_nodes,
                "n2_time": n2_elapsed,
                "n2_correct": n2_is_correct,
                "moves_match": moves_match,
            }
            depth_records.append(record)

            print(
                f"[{tid:22s}] Sol:{sol:5s} | K0:{str(k0_move):5s} ({'OK' if k0_is_correct else 'FAIL'}) "
                f"{k0_elapsed*1000:6.1f}ms | N2:{str(n2_move):5s} ({'OK' if n2_is_correct else 'FAIL'}) "
                f"{n2_elapsed*1000:6.1f}ms | Match:{'Y' if moves_match else 'N'}",
                flush=True
            )

        speedup = k0_total_time / n2_total_time if n2_total_time > 0 else 0
        summary = {
            "depth": depth,
            "total_positions": len(corpus),
            "k0_solved": k0_solved,
            "k0_solve_rate": k0_solved / len(corpus),
            "n2_solved": n2_solved,
            "n2_solve_rate": n2_solved / len(corpus),
            "k0_n2_agreement": agreed / len(corpus),
            "k0_total_nodes": k0_total_nodes,
            "n2_total_nodes": n2_total_nodes,
            "k0_total_time_sec": k0_total_time,
            "n2_total_time_sec": n2_total_time,
            "speedup_factor": speedup,
            "records": depth_records
        }
        results.append(summary)
        print(f"\nSummary Depth {depth}: K0 Solved={k0_solved}/{len(corpus)} ({k0_solved/len(corpus)*100:.1f}%), "
              f"N2 Solved={n2_solved}/{len(corpus)} ({n2_solved/len(corpus)*100:.1f}%), "
              f"Agreement={agreed}/{len(corpus)} ({agreed/len(corpus)*100:.1f}%), "
              f"Speedup={speedup:.2f}x", flush=True)

    out_file = Path("analysis/v0.50/raw/tactical_regression_raw.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved raw results to {out_file}", flush=True)


if __name__ == "__main__":
    run_tactical_regression()

