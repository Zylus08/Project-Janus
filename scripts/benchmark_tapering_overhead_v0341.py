"""Isolated microbenchmark and search benchmark for tapering overhead in Project Janus v0.34.1."""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import chess

from janus.evaluation import (
    EvaluationConfig,
    CONFIG_V030,
    CONFIG_V033,
    CONFIG_V034_TAPERED,
    evaluate_white,
)
from janus.search import JanusSearch


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis" / "v0.34" / "release_audit"

# Four isolated configurations for controlled comparison:
# 1. Baseline: v0.30 (no positional terms, no tapering)
# 2. Pure Tapering Math: baseline terms with phase calculation & interpolation
# 3. Static Positional: v0.33 (all positional terms, static non-tapered)
# 4. Tapered Positional: v0.34 (all positional terms, tapered)
CONFIGS = {
    "v030_baseline": CONFIG_V030,
    "tapering_math_only": EvaluationConfig(
        enable_pawn_structure=False,
        enable_rook_files=False,
        enable_king_safety=False,
        enable_tapered_eval=True,
    ),
    "v033_static_all": CONFIG_V033,
    "v034_tapered_all": CONFIG_V034_TAPERED,
}


def run_isolated_microbenchmark(
    eval_fens: list[str],
    rounds: int = 5,
    evals_per_round: int = 20_000,
) -> dict[str, Any]:
    """Measure raw evaluate_white throughput with warmup and multiple rounds reporting median and dispersion."""
    boards = [chess.Board(fen) for fen in eval_fens]
    n_boards = len(boards)
    iters_per_board = evals_per_round // n_boards
    total_evals_round = iters_per_board * n_boards

    results: dict[str, Any] = {}

    for name, cfg in CONFIGS.items():
        # Warmup (1,000 evaluations)
        for b in boards:
            for _ in range(200):
                _ = evaluate_white(b, cfg)

        round_times: list[float] = []
        round_eps: list[float] = []

        for _ in range(rounds):
            t0 = time.perf_counter()
            for b in boards:
                for _ in range(iters_per_board):
                    _ = evaluate_white(b, cfg)
            elapsed = time.perf_counter() - t0
            round_times.append(elapsed)
            round_eps.append(total_evals_round / elapsed)

        round_eps.sort()
        n = len(round_eps)
        median_eps = round_eps[n // 2]
        mean_eps = sum(round_eps) / n
        std_eps = (sum((x - mean_eps) ** 2 for x in round_eps) / max(1, n - 1)) ** 0.5

        results[name] = {
            "rounds": rounds,
            "evals_per_round": total_evals_round,
            "round_times_s": [round(t, 4) for t in round_times],
            "round_eps": [round(e, 1) for e in round_eps],
            "median_eps": round(median_eps, 1),
            "mean_eps": round(mean_eps, 1),
            "std_dev_eps": round(std_eps, 1),
            "min_eps": round(round_eps[0], 1),
            "max_eps": round(round_eps[-1], 1),
            "config": {
                "enable_pawn_structure": cfg.enable_pawn_structure,
                "enable_rook_files": cfg.enable_rook_files,
                "enable_king_safety": cfg.enable_king_safety,
                "enable_tapered_eval": cfg.enable_tapered_eval,
            },
        }

    # Relative performance metrics against v0.30 baseline
    base_eps = results["v030_baseline"]["median_eps"]
    static_eps = results["v033_static_all"]["median_eps"]

    for name, r in results.items():
        r["speed_relative_to_baseline_pct"] = round((r["median_eps"] / base_eps) * 100.0, 2)
        r["overhead_relative_to_static_pct"] = round(
            ((static_eps - r["median_eps"]) / static_eps) * 100.0, 2
        ) if "tapered" in name else 0.0

    return results


def run_isolated_search_benchmark(
    positions: list[dict[str, Any]],
    depths: list[int] = [4, 5],
) -> dict[str, Any]:
    """Run fixed-depth search across diagnostic positions for each configuration."""
    search_data: dict[str, Any] = {f"depth_{d}": {} for d in depths}
    baseline_records: dict[int, dict[str, dict[str, Any]]] = {d: {} for d in depths}

    for name, cfg in CONFIGS.items():
        print(f"Running search benchmark for: {name}...")
        for depth in depths:
            d_key = f"depth_{depth}"
            pos_results: list[dict[str, Any]] = []

            total_nodes = 0
            total_time = 0.0
            agreed_moves = 0
            score_diffs: list[int] = []

            for p in positions:
                b = chess.Board(p["fen"])
                engine = JanusSearch(eval_config=cfg)
                res = engine.search(b, max_depth=depth)

                bm = res.best_move.uci() if res.best_move else None
                score = res.score

                if name == "v030_baseline":
                    baseline_records[depth][p["id"]] = {"best_move": bm, "score": score}
                    agreed = True
                    diff = 0
                else:
                    base_ref = baseline_records[depth][p["id"]]
                    agreed = (bm == base_ref["best_move"])
                    diff = score - base_ref["score"]

                if agreed:
                    agreed_moves += 1
                score_diffs.append(abs(diff))

                total_nodes += res.nodes
                total_time += res.elapsed

                pos_results.append({
                    "id": p["id"],
                    "best_move": bm,
                    "score_cp": score,
                    "nodes": res.nodes,
                    "elapsed_s": round(res.elapsed, 4),
                    "nps": int(res.nodes / max(0.0001, res.elapsed)),
                    "agrees_with_baseline": agreed,
                    "abs_score_diff_from_baseline": abs(diff),
                })

            n = len(positions)
            overall_nps = int(total_nodes / max(0.0001, total_time))
            mean_abs_score_diff = sum(score_diffs) / max(1, len(score_diffs))

            search_data[d_key][name] = {
                "summary": {
                    "total_nodes": total_nodes,
                    "total_elapsed_s": round(total_time, 4),
                    "mean_nodes_per_pos": round(total_nodes / n, 1),
                    "mean_elapsed_s": round(total_time / n, 4),
                    "overall_nps": overall_nps,
                    "move_agreement_with_baseline_pct": round((agreed_moves / n) * 100.0, 2),
                    "mean_abs_score_diff_cp": round(mean_abs_score_diff, 1),
                },
                "positions": pos_results,
            }

    return search_data


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bench_file = ROOT / "benchmarks" / "evaluation_positions.json"
    with open(bench_file, "r", encoding="utf-8") as f:
        bench_data = json.load(f)
    positions = bench_data["positions"]

    sample_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Opening (phase 24)
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",  # Symmetrical early middlegame (phase 24)
        "r1b1k2r/ppppqppp/2n5/4p3/2B1P1n1/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 7",  # Dynamic middlegame (phase 24)
        "2r3k1/1p3ppp/p7/3p4/8/1P3P2/P5PP/2R3K1 w - - 0 20",  # Rook endgame (phase 8)
        "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",  # Pawn endgame (phase 0)
    ]

    print("--- Running Isolated Microbenchmark ---")
    micro_results = run_isolated_microbenchmark(sample_fens, rounds=5, evals_per_round=20_000)

    print(f"{'Configuration':22s} | {'Median EPS':11s} | {'Std Dev':9s} | {'Rel Speed':9s} | {'Overhead vs Static'}")
    print("-" * 75)
    for name, r in micro_results.items():
        ovh = f"{r['overhead_relative_to_static_pct']:+.1f}%" if "tapered" in name else "N/A"
        print(f"{name:22s} | {r['median_eps']:9.1f} eps | {r['std_dev_eps']:7.1f} | {r['speed_relative_to_baseline_pct']:7.1f}% | {ovh}")

    print("\n--- Running Search Benchmark (Depths 4 & 5) ---")
    search_results = run_isolated_search_benchmark(positions, depths=[4, 5])

    for depth in [4, 5]:
        d_key = f"depth_{depth}"
        print(f"\n--- Depth {depth} Summary ---")
        for name in CONFIGS:
            s = search_results[d_key][name]["summary"]
            print(f"{name:22s} | Nodes: {s['total_nodes']:6d} | Time: {s['total_elapsed_s']:5.2f}s | NPS: {s['overall_nps']:6d} | Agree: {s['move_agreement_with_baseline_pct']:5.1f}% | ScoreDiff: {s['mean_abs_score_diff_cp']}cp")

    report = {
        "environment": {
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "chess_version": chess.__version__,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "microbenchmark": micro_results,
        "search_benchmark": search_results,
    }

    out_file = OUT_DIR / "tapering_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nTapering benchmark report saved to {out_file}")


if __name__ == "__main__":
    main()
