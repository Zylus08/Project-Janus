#!/usr/bin/env python3
"""Project Janus v0.61 - Phase 1, Step 1: Teacher-Label Reliability Study.

Compares Stockfish 19 evaluations at the existing 5,000-node budget vs a deeper
25,000-node budget across a stratified sample of positions.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import chess
import chess.engine
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SF_PATH = ROOT.parent / "tools" / "stockfish" / "stockfish.exe"
V60_VAL = ROOT / "analysis" / "v0.60" / "dataset" / "value_val.json"
V60_TRAIN = ROOT / "analysis" / "v0.60" / "dataset" / "value_train.json"
OUT_JSON = ROOT / "analysis" / "v0.61" / "raw" / "teacher_reliability_study.json"


def compute_spearman(x: List[float], y: List[float]) -> float:
    """Computes Spearman rank correlation using numpy."""
    x_arr = np.array(x)
    y_arr = np.array(y)
    rx = np.argsort(np.argsort(x_arr))
    ry = np.argsort(np.argsort(y_arr))
    n = len(x)
    if n < 2:
        return 0.0
    d = rx - ry
    return float(1.0 - 6.0 * np.sum(d**2) / (n * (n**2 - 1)))


def classify_phase(board: chess.Board, ply: int) -> str:
    piece_count = len(board.piece_map())
    if ply <= 16:
        return "opening"
    elif piece_count <= 10:
        return "endgame"
    else:
        return "middlegame"


def main():
    print(f"Loading reference positions...")
    val_data = json.load(open(V60_VAL, "r", encoding="utf-8"))
    train_data = json.load(open(V60_TRAIN, "r", encoding="utf-8"))
    all_data = val_data + train_data

    # Stratified sampling: 500 positions
    # 150 opening, 200 middlegame, 150 endgame
    opening_pos = [p for p in all_data if p.get("phase") == "opening"]
    middle_pos = [p for p in all_data if p.get("phase") == "middlegame"]
    endgame_pos = [p for p in all_data if p.get("phase") == "endgame"]

    np.random.seed(42)
    sample_opening = list(np.random.choice(opening_pos, size=150, replace=False))
    sample_middle = list(np.random.choice(middle_pos, size=200, replace=False))
    sample_endgame = list(np.random.choice(endgame_pos, size=150, replace=False))

    stratified_sample = sample_opening + sample_middle + sample_endgame
    print(f"Sampled {len(stratified_sample)} positions: 150 Opening, 200 Middlegame, 150 Endgame")

    assert SF_PATH.exists(), f"Stockfish not found at {SF_PATH}"
    print(f"Connecting to Stockfish 19 at {SF_PATH}...")
    engine = chess.engine.SimpleEngine.popen_uci(str(SF_PATH))

    results = []
    t0 = time.time()
    for idx, item in enumerate(stratified_sample):
        fen = item["fen"]
        board = chess.Board(fen)
        score_5k = item["sf_score_stm"]
        best_5k = item.get("sf_best_move", "")

        # Evaluate at 25,000 nodes
        info_25k = engine.analyse(board, chess.engine.Limit(nodes=25000))
        score_obj = info_25k["score"].relative
        is_mate = score_obj.is_mate()
        mate_depth = score_obj.mate() if is_mate else None
        score_25k = score_obj.score(mate_score=30000)
        best_25k = str(info_25k.get("pv", [None])[0]) if info_25k.get("pv") else ""
        depth_25k = info_25k.get("depth", 0)

        # Clamping for extreme non-mate centipawns
        score_25k_clamped = max(-2000, min(2000, score_25k))
        score_5k_clamped = max(-2000, min(2000, score_5k))

        results.append({
            "fen": fen,
            "phase": item["phase"],
            "ply": item["ply"],
            "score_5k": score_5k_clamped,
            "score_25k": score_25k_clamped,
            "abs_diff": abs(score_25k_clamped - score_5k_clamped),
            "sign_agree": (score_5k_clamped > 0 and score_25k_clamped > 0) or 
                          (score_5k_clamped < 0 and score_25k_clamped < 0) or
                          (score_5k_clamped == 0 and score_25k_clamped == 0),
            "move_agree": (best_5k == best_25k),
            "is_mate_5k": item.get("sf_is_mate", False),
            "is_mate_25k": is_mate,
            "mate_depth_25k": mate_depth,
            "depth_25k": depth_25k,
            "best_move_5k": best_5k,
            "best_move_25k": best_25k,
            "is_balanced_c1": abs(item.get("c1_score_stm", 0)) <= 50,
        })

        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(stratified_sample)} positions... (elapsed: {time.time()-t0:.1f}s)")

    engine.quit()
    elapsed = time.time() - t0
    print(f"Completed evaluation in {elapsed:.2f}s ({elapsed/len(stratified_sample)*1000:.1f} ms/pos)")

    # Aggregate Statistics
    scores_5k = [r["score_5k"] for r in results]
    scores_25k = [r["score_25k"] for r in results]
    diffs = [r["abs_diff"] for r in results]

    overall_mae = float(np.mean(diffs))
    overall_rmse = float(np.sqrt(np.mean(np.array(diffs)**2)))
    overall_p95 = float(np.percentile(diffs, 95))
    overall_max = float(np.max(diffs))
    spearman_rho = compute_spearman(scores_5k, scores_25k)
    pearson_r = float(np.corrcoef(scores_5k, scores_25k)[0, 1])

    # Sign agreement filter for non-trivial positions (|score| >= 25 cp)
    non_trivial = [r for r in results if abs(r["score_5k"]) >= 25 or abs(r["score_25k"]) >= 25]
    sign_agree_pct = float(np.mean([r["sign_agree"] for r in non_trivial]) * 100) if non_trivial else 100.0
    move_agree_pct = float(np.mean([r["move_agree"] for r in results]) * 100)

    # By game phase
    phase_stats = {}
    for ph in ["opening", "middlegame", "endgame"]:
        ph_items = [r for r in results if r["phase"] == ph]
        ph_diffs = [r["abs_diff"] for r in ph_items]
        ph_spearman = compute_spearman([r["score_5k"] for r in ph_items], [r["score_25k"] for r in ph_items])
        ph_move_agree = float(np.mean([r["move_agree"] for r in ph_items]) * 100)
        phase_stats[ph] = {
            "count": len(ph_items),
            "mae": float(np.mean(ph_diffs)),
            "rmse": float(np.sqrt(np.mean(np.array(ph_diffs)**2))),
            "p95": float(np.percentile(ph_diffs, 95)),
            "spearman_rho": ph_spearman,
            "move_agreement_pct": ph_move_agree,
        }

    # Materially balanced positions
    balanced_items = [r for r in results if r["is_balanced_c1"]]
    balanced_mae = float(np.mean([r["abs_diff"] for r in balanced_items])) if balanced_items else 0.0

    summary = {
        "sample_size": len(results),
        "elapsed_seconds": elapsed,
        "mean_latency_ms_per_pos": elapsed / len(results) * 1000,
        "overall_mae": overall_mae,
        "overall_rmse": overall_rmse,
        "overall_p95": overall_p95,
        "overall_max": overall_max,
        "spearman_rho": spearman_rho,
        "pearson_r": pearson_r,
        "sign_agreement_pct_nontrivial": sign_agree_pct,
        "best_move_agreement_pct": move_agree_pct,
        "balanced_positions_mae": balanced_mae,
        "balanced_positions_count": len(balanced_items),
        "phase_breakdown": phase_stats,
    }

    print("\n" + "="*60)
    print("TEACHER RELIABILITY STUDY RESULTS (5K vs 25K Nodes):")
    print("="*60)
    print(f"Overall MAE: {overall_mae:.2f} cp | RMSE: {overall_rmse:.2f} cp | P95: {overall_p95:.2f} cp | Max: {overall_max:.2f} cp")
    print(f"Spearman Rank Correlation: {spearman_rho:.4f} | Pearson Correlation: {pearson_r:.4f}")
    print(f"Sign Agreement (|score|>=25cp): {sign_agree_pct:.2f}%")
    print(f"Best Move Agreement: {move_agree_pct:.2f}%")
    print(f"Balanced Positions MAE (|C1|<=50cp, n={len(balanced_items)}): {balanced_mae:.2f} cp")
    print("\nPhase Breakdown:")
    for ph, stats in phase_stats.items():
        print(f"  {ph.capitalize()} (n={stats['count']}): MAE={stats['mae']:.2f} cp, RMSE={stats['rmse']:.2f} cp, rho={stats['spearman_rho']:.4f}, MoveAgree={stats['move_agreement_pct']:.1f}%")

    output_payload = {
        "summary": summary,
        "records": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)
    print(f"\nSaved detailed results to {OUT_JSON}")


if __name__ == "__main__":
    main()
