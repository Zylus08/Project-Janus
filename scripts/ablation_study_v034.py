"""Controlled 6-way evaluation feature ablation study for Project Janus v0.34."""
from __future__ import annotations

import json
from pathlib import Path
import time
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


# Calibrated configuration derived from Phase 4 dataset tuning
CALIBRATED_PARAMS = {
    "enable_pawn_structure": True,
    "enable_rook_files": True,
    "enable_king_safety": True,
    "doubled_pawn_penalty_mg": 16,
    "doubled_pawn_penalty_eg": 24,
    "isolated_pawn_penalty_mg": 18,
    "isolated_pawn_penalty_eg": 22,
    "king_shield_bonus_mg": 18,
    "king_center_bonus_eg": 8,
    "rook_open_file_bonus_mg": 26,
    "rook_semi_open_file_bonus_mg": 6,
    "bishop_pair_bonus": 18,
}

CONFIG_CALIBRATED_STATIC = EvaluationConfig(
    **{**CALIBRATED_PARAMS, "enable_tapered_eval": False}
)
CONFIG_CALIBRATED_TAPERED = EvaluationConfig(
    **{**CALIBRATED_PARAMS, "enable_tapered_eval": True}
)

CONFIGURATIONS: dict[str, EvaluationConfig] = {
    "A_v030_baseline": CONFIG_V030,
    "B_v033_pawn_structure": EvaluationConfig(
        enable_pawn_structure=True,
        enable_rook_files=False,
        enable_king_safety=False,
        enable_tapered_eval=False,
    ),
    "C_v033_all_features": CONFIG_V033,
    "D_v034_tapered": CONFIG_V034_TAPERED,
    "E_calibrated_static": CONFIG_CALIBRATED_STATIC,
    "F_v034_tapered_calibrated": CONFIG_CALIBRATED_TAPERED,
}


def run_microbenchmark(
    configs: dict[str, EvaluationConfig],
    eval_fens: list[str],
    iterations_per_pos: int = 10_000,
) -> dict[str, dict[str, float]]:
    """Measure raw evaluate_white throughput across diverse board positions."""
    results: dict[str, dict[str, float]] = {}
    boards = [chess.Board(fen) for fen in eval_fens]
    total_evals = len(boards) * iterations_per_pos

    baseline_eps: float | None = None

    for name, cfg in configs.items():
        # Warm-up
        for b in boards:
            _ = evaluate_white(b, cfg)

        start = time.perf_counter()
        for _ in range(iterations_per_pos):
            for b in boards:
                _ = evaluate_white(b, cfg)
        elapsed = time.perf_counter() - start

        eps = total_evals / elapsed
        if baseline_eps is None:
            baseline_eps = eps

        results[name] = {
            "total_evals": total_evals,
            "elapsed_s": round(elapsed, 4),
            "evals_per_sec": round(eps, 1),
            "relative_speed_pct": round((eps / baseline_eps) * 100.0, 2),
        }

    return results


def run_search_ablation(
    configs: dict[str, EvaluationConfig],
    positions: list[dict[str, Any]],
    depths: list[int] = [4, 5],
) -> dict[str, Any]:
    """Run fixed-depth search across diagnostic positions for each configuration."""
    ablation_data: dict[str, Any] = {f"depth_{d}": {} for d in depths}

    # Reference moves from baseline for agreement calculation
    baseline_moves: dict[int, dict[str, str | None]] = {d: {} for d in depths}

    for name, cfg in configs.items():
        print(f"Running search ablation for: {name}...")
        for depth in depths:
            depth_key = f"depth_{depth}"
            pos_results: list[dict[str, Any]] = []
            total_nodes = 0
            total_time = 0.0
            total_tt_hits = 0
            total_tt_probes = 0
            agreed_moves = 0

            for p in positions:
                board = chess.Board(p["fen"])
                engine = JanusSearch(eval_config=cfg)
                res = engine.search(board, max_depth=depth)

                bm_str = res.best_move.uci() if res.best_move else None
                if name == "A_v030_baseline":
                    baseline_moves[depth][p["id"]] = bm_str
                    agreed = True
                else:
                    agreed = (bm_str == baseline_moves[depth].get(p["id"]))

                if agreed:
                    agreed_moves += 1

                total_nodes += res.nodes
                total_time += res.elapsed
                total_tt_hits += engine.tt_hits
                total_tt_probes += engine.tt_probes

                pos_results.append({
                    "id": p["id"],
                    "category": p["category"],
                    "best_move": bm_str,
                    "score_cp": res.score,
                    "nodes": res.nodes,
                    "elapsed_s": round(res.elapsed, 4),
                    "nps": int(res.nodes / max(0.0001, res.elapsed)),
                    "agrees_with_baseline": agreed,
                })

            n = len(positions)
            tt_hit_rate = (total_tt_hits / max(1, total_tt_probes)) * 100.0
            overall_nps = int(total_nodes / max(0.0001, total_time))

            ablation_data[depth_key][name] = {
                "summary": {
                    "total_nodes": total_nodes,
                    "total_elapsed_s": round(total_time, 4),
                    "mean_nodes_per_pos": round(total_nodes / n, 1),
                    "mean_elapsed_s": round(total_time / n, 4),
                    "overall_nps": overall_nps,
                    "tt_hit_rate_pct": round(tt_hit_rate, 2),
                    "move_agreement_with_baseline_pct": round((agreed_moves / n) * 100.0, 2),
                },
                "positions": pos_results,
            }

    return ablation_data


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    benchmarks_path = repo_root / "benchmarks" / "evaluation_positions.json"
    out_dir = repo_root / "analysis" / "v0.34" / "ablation"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(benchmarks_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)
    positions = bench_data["positions"]

    # Microbenchmark test positions
    sample_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # startpos
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",  # four knights
        "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",  # pawn endgame
        "2r3k1/1p3ppp/p7/3p4/8/1P3P2/P5PP/2R3K1 w - - 0 20",  # rook endgame
        "r1b1k2r/ppppqppp/2n5/4p3/2B1P1n1/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 7",  # middlegame
    ]

    print("--- Running Microbenchmark (50,000 evaluations per configuration) ---")
    micro_results = run_microbenchmark(CONFIGURATIONS, sample_fens, iterations_per_pos=10_000)
    for name, m in micro_results.items():
        print(f"{name:26s} | {m['evals_per_sec']:8.1f} eps | {m['relative_speed_pct']:5.1f}% | {m['elapsed_s']:6.3f}s")

    print("\n--- Running Search Benchmark (Depths 4 & 5 across 24 positions) ---")
    search_results = run_search_ablation(CONFIGURATIONS, positions, depths=[4, 5])

    print("\n--- Summary at Depth 4 ---")
    for name in CONFIGURATIONS:
        s = search_results["depth_4"][name]["summary"]
        print(f"{name:26s} | Nodes: {s['total_nodes']:6d} | Time: {s['total_elapsed_s']:5.2f}s | NPS: {s['overall_nps']:6d} | Agree: {s['move_agreement_with_baseline_pct']:5.1f}%")

    print("\n--- Summary at Depth 5 ---")
    for name in CONFIGURATIONS:
        s = search_results["depth_5"][name]["summary"]
        print(f"{name:26s} | Nodes: {s['total_nodes']:6d} | Time: {s['total_elapsed_s']:5.2f}s | NPS: {s['overall_nps']:6d} | Agree: {s['move_agreement_with_baseline_pct']:5.1f}%")

    full_report = {
        "timestamp": time.time(),
        "microbenchmark": micro_results,
        "search_ablation": search_results,
    }

    out_file = out_dir / "ablation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"\nSaved full ablation results to {out_file}")


if __name__ == "__main__":
    main()
