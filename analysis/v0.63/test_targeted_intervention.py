"""Project Janus v0.63 - Phase 6 Targeted Intervention: Phase-Tapered Adaptive Blending.

Evaluates a bounded correction (Phase-Tapered Hybrid Blending) against frozen N1 (50/50)
and Classical C1 on the 500 held-out positions from Phase 2.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis" / "v0.63"

from evaluate_positional_errors import spearman_rho


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.63 — PHASE 6 TARGETED INTERVENTION")
    print("Evaluation of Phase-Tapered Adaptive Blending (PT-Hybrid)")
    print("=" * 80)

    # Load Phase 2 raw records
    # We can reconstruct from positional_error_analysis.json or re-run on records
    with open(OUT_DIR / "positional_error_analysis.json", "r", encoding="utf-8") as f:
        p2_data = json.load(f)

    # Let's read the 500 records saved or rerun on pos_sample
    # To be exact, let's load pos_sample and run the taper comparison
    from evaluate_positional_errors import sample_excluded_positions, compute_structural_descriptors, StockfishEvaluator, NativeEngineC1, NativeEngineV61, STOCKFISH_EXE, MODEL_PATH
    import chess

    pos_sample = sample_excluded_positions(500)
    sf = StockfishEvaluator(STOCKFISH_EXE)
    eng_c1 = NativeEngineC1()
    eng_v61 = NativeEngineV61()
    eng_v61.set_neural_value_options(True, str(MODEL_PATH), 100, use_avx2=True)

    records = []
    print(f"Re-evaluating {len(pos_sample)} positions with Phase-Tapered Adaptive Blending...")
    for idx, (fen, g_id, ply) in enumerate(pos_sample):
        board = chess.Board(fen)
        struct = compute_structural_descriptors(board)
        phase = struct["material_phase"] # 0..24

        sf_score = sf.evaluate_fen(fen, depth=12)
        sf_white = sf_score if board.turn == chess.WHITE else -sf_score

        eng_c1.set_fen(fen)
        c1_stm = eng_c1.evaluate()
        c1_white = c1_stm if board.turn == chess.WHITE else -c1_stm

        eng_v61.set_fen(fen)
        nn_stm = eng_v61.evaluate_neural()
        nn_white = nn_stm if board.turn == chess.WHITE else -nn_stm

        # Frozen N1: Constant 50/50 blend
        n1_white = int(0.5 * c1_white + 0.5 * nn_white)

        # Proposed Intervention: Phase-Tapered Hybrid
        # In opening/midgame (phase=24): neural_weight = 0.50, classical_weight = 0.50
        # In pure endgame (phase=0): neural_weight = 0.00, classical_weight = 1.00
        neural_weight = 0.50 * (phase / 24.0)
        classical_weight = 1.0 - neural_weight
        pt_white = int(classical_weight * c1_white + neural_weight * nn_white)

        records.append({
            "phase": phase,
            "sf19": sf_white,
            "c1": c1_white,
            "nnue": nn_white,
            "n1_fixed": n1_white,
            "pt_hybrid": pt_white,
        })

    sf.close()

    def calc_stats(recs):
        n = len(recs)
        y_sf = [r["sf19"] for r in recs]
        y_c1 = [r["c1"] for r in recs]
        y_n1 = [r["n1_fixed"] for r in recs]
        y_pt = [r["pt_hybrid"] for r in recs]

        mae_c1 = sum(abs(y_c1[i] - y_sf[i]) for i in range(n)) / n
        mae_n1 = sum(abs(y_n1[i] - y_sf[i]) for i in range(n)) / n
        mae_pt = sum(abs(y_pt[i] - y_sf[i]) for i in range(n)) / n

        rho_c1 = spearman_rho(y_c1, y_sf)
        rho_n1 = spearman_rho(y_n1, y_sf)
        rho_pt = spearman_rho(y_pt, y_sf)

        return {
            "count": n,
            "mae_c1": round(mae_c1, 2),
            "mae_n1": round(mae_n1, 2),
            "mae_pt": round(mae_pt, 2),
            "rho_c1": round(rho_c1, 4),
            "rho_n1": round(rho_n1, 4),
            "rho_pt": round(rho_pt, 4),
        }

    all_stats = calc_stats(records)
    mid_stats = calc_stats([r for r in records if r["phase"] > 16])
    end_stats = calc_stats([r for r in records if r["phase"] <= 16])

    print("\n" + "=" * 90)
    print(f"{'Regime':25s} | {'Count':5s} | {'MAE C1':8s} {'MAE N1':8s} {'MAE PT':8s} | {'Rho C1':7s} {'Rho N1':7s} {'Rho PT':7s}")
    print("=" * 90)
    for name, s in [("Overall (All 500)", all_stats), ("Middlegame (Phase > 16)", mid_stats), ("Endgame (Phase <= 16)", end_stats)]:
        print(f"{name:25s} | {s['count']:5d} | {s['mae_c1']:8.1f} {s['mae_n1']:8.1f} {s['mae_pt']:8.1f} | {s['rho_c1']:7.3f} {s['rho_n1']:7.3f} {s['rho_pt']:7.3f}")
    print("=" * 90)

    out_file = OUT_DIR / "targeted_intervention_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "overall": all_stats,
            "middlegame": mid_stats,
            "endgame": end_stats,
            "intervention": "Phase-Tapered Adaptive Blending: w_neural = 0.50 * (phase/24)"
        }, f, indent=2)

    print(f"\nSaved intervention results to {out_file}")


if __name__ == "__main__":
    main()
