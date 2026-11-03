"""Project Janus v0.33 - Feature Ablation and Microbenchmarking Study.

Evaluates 5 configurations:
1. Baseline (v0.30 exact evaluation)
2. Candidate A: Pawn Structure only (passed, doubled, isolated)
3. Candidate B: Rook Files only (open, semi-open files)
4. Candidate C: King Safety only (castled pawn shield, open files)
5. Candidate Combo: Pawn Structure + Rook Files + King Safety

Measures:
- Raw evaluation throughput (evals/second)
- Diagnostic suite evaluation scores across all 24 curated positions
- Search benchmark performance (depth 4 & 5 across 6 benchmark positions):
  best moves, scores, node counts, runtime, NPS.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import chess
from janus.evaluation import evaluate_white, evaluate_side_to_move, evaluation_config
from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]
DIAG_POSITIONS_PATH = ROOT / "benchmarks/evaluation_positions.json"
BENCH_POSITIONS_PATH = ROOT / "benchmarks/positions.json"
OUTPUT_DIR = ROOT / "analysis/v0.33/ablation"


CONFIGS = {
    "baseline": {"pawn_structure": False, "rook_files": False, "king_safety": False},
    "pawn_structure": {"pawn_structure": True, "rook_files": False, "king_safety": False},
    "rook_files": {"pawn_structure": False, "rook_files": True, "king_safety": False},
    "king_safety": {"pawn_structure": False, "rook_files": False, "king_safety": True},
    "all_features": {"pawn_structure": True, "rook_files": True, "king_safety": True},
}


def microbenchmark_eval(configs: dict, iterations: int = 20000) -> dict:
    """Benchmark raw evaluation function throughput."""
    test_fens = [
        chess.STARTING_FEN,
        "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
        "r4rk1/pp1q1ppp/2n1pn2/8/3P4/2NB1N2/PP3PPP/R2Q1RK1 w - - 0 12",
        "4k3/8/8/3P4/8/8/8/4K3 w - - 0 1",
        "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",
    ]
    boards = [chess.Board(fen) for fen in test_fens]
    results = {}

    for name, cfg in configs.items():
        with evaluation_config(**cfg):
            # Warm up
            for b in boards:
                evaluate_white(b)

            t0 = time.perf_counter()
            count = 0
            for _ in range(iterations):
                for b in boards:
                    evaluate_white(b)
                    count += 1
            elapsed = time.perf_counter() - t0
            eps = count / elapsed if elapsed > 0 else 0
            results[name] = {
                "evaluations": count,
                "elapsed_s": round(elapsed, 4),
                "evals_per_sec": round(eps, 0),
            }

    base_eps = results["baseline"]["evals_per_sec"]
    for name in results:
        results[name]["relative_speed_pct"] = round(results[name]["evals_per_sec"] / base_eps * 100.0, 1)

    return results


def evaluate_diagnostic_suite(configs: dict) -> dict:
    """Evaluate all 24 curated positions under each configuration."""
    diag_data = json.loads(DIAG_POSITIONS_PATH.read_text(encoding="utf-8"))
    positions = diag_data.get("positions", [])

    results = {}
    for pos in positions:
        pid = pos["id"]
        fen = pos["fen"]
        board = chess.Board(fen)
        pos_res = {
            "category": pos["category"],
            "expected": pos["expected_property"],
            "scores_white": {},
        }
        for name, cfg in configs.items():
            with evaluation_config(**cfg):
                pos_res["scores_white"][name] = evaluate_white(board)
        results[pid] = pos_res

    return results


def search_benchmarks(configs: dict, depths: list[int] = [4, 5]) -> dict:
    """Run search benchmarks across standard positions under each configuration."""
    bench_data = json.loads(BENCH_POSITIONS_PATH.read_text(encoding="utf-8"))

    results = {}
    for name, cfg in configs.items():
        results[name] = {}
        with evaluation_config(**cfg):
            for d in depths:
                depth_key = f"depth_{d}"
                results[name][depth_key] = {}
                total_nodes = 0
                total_time = 0.0

                for pos in bench_data:
                    pid = pos["id"]
                    fen = pos["fen"]
                    board = chess.Board(fen)

                    if board.is_game_over():
                        results[name][depth_key][pid] = {
                            "best_move": None,
                            "score": 0,
                            "nodes": 0,
                            "time_s": 0.0,
                            "nps": 0,
                        }
                        continue

                    searcher = JanusSearch()
                    res = searcher.search(board, max_depth=d)
                    best_move = res.best_move
                    score = res.score
                    nodes = res.nodes
                    elapsed = res.elapsed

                    total_nodes += nodes
                    total_time += elapsed
                    nps = nodes / elapsed if elapsed > 0 else 0

                    results[name][depth_key][pid] = {
                        "best_move": best_move.uci() if best_move else None,
                        "score": score,
                        "nodes": nodes,
                        "time_s": round(elapsed, 4),
                        "nps": round(nps, 0),
                    }

                results[name][depth_key]["summary"] = {
                    "total_nodes": total_nodes,
                    "total_time_s": round(total_time, 4),
                    "avg_nps": round(total_nodes / total_time, 0) if total_time > 0 else 0,
                }

    return results


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 80)
    print("PROJECT JANUS v0.33 — EVALUATION FEATURE ABLATION STUDY")
    print("=" * 80)

    print("\n1. Running Evaluation Microbenchmarks...")
    micro_res = microbenchmark_eval(CONFIGS, iterations=25000)
    for name, data in micro_res.items():
        print(f"  {name:<16}: {data['evals_per_sec']:>10,.0f} evals/s ({data['relative_speed_pct']:>5.1f}% of baseline)")

    print("\n2. Evaluating Diagnostic Position Suite...")
    diag_res = evaluate_diagnostic_suite(CONFIGS)
    print(f"  Evaluated {len(diag_res)} curated positions across 5 configurations.")

    print("\n3. Running Fixed-Depth Search Benchmarks (Depths 4 & 5)...")
    search_res = search_benchmarks(CONFIGS, depths=[4, 5])
    for d in [4, 5]:
        d_key = f"depth_{d}"
        print(f"\n--- Benchmark Summary for Depth {d} ---")
        base_time = search_res["baseline"][d_key]["summary"]["total_time_s"]
        base_nodes = search_res["baseline"][d_key]["summary"]["total_nodes"]
        for name in CONFIGS:
            s = search_res[name][d_key]["summary"]
            time_ratio = (s["total_time_s"] / base_time * 100.0) if base_time > 0 else 100.0
            node_ratio = (s["total_nodes"] / base_nodes * 100.0) if base_nodes > 0 else 100.0
            print(f"  {name:<16}: Nodes = {s['total_nodes']:>6} ({node_ratio:>5.1f}%), "
                  f"Time = {s['total_time_s']:>6.3f}s ({time_ratio:>5.1f}%), "
                  f"NPS = {s['avg_nps']:>7,.0f}")

    # Tactical correctness verification
    print("\n4. Verifying Tactical Integrity Across Configurations...")
    tactics_ok = True
    for name in CONFIGS:
        mate_move = search_res[name]["depth_4"]["mate_in_one"]["best_move"]
        if mate_move != "g5g7":
            print(f"  WARNING: {name} failed mate_in_one! Got {mate_move}")
            tactics_ok = False
        else:
            print(f"  {name:<16}: mate_in_one found correct move g5g7.")

    # Save machine-readable results
    full_output = {
        "timestamp": time.time(),
        "configs": CONFIGS,
        "microbenchmark": micro_res,
        "diagnostic_suite": diag_res,
        "search_benchmarks": search_res,
        "tactics_ok": tactics_ok,
    }

    out_file = OUTPUT_DIR / "ablation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"\nSaved full ablation results to {out_file}")


if __name__ == "__main__":
    main()
