"""Independent audit of calibration provenance, dataset distribution, and loss recomputation for v0.34.1."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import chess

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from janus.evaluation import (
    CONFIG_V034_TAPERED,
    EvaluationConfig,
    evaluate_white,
)
from scripts.calibrate_weights_v034 import (
    extract_quiet_positions,
    partition_samples,
    sigmoid,
    evaluate_dataset_loss,
)

OUT_DIR = ROOT / "analysis" / "v0.34" / "release_audit"


def run_calibration_provenance_audit() -> dict[str, Any]:
    pgn_path = ROOT / "analysis" / "v0.33" / "match" / "v033_match_500ms.pgn"
    summary_path = ROOT / "analysis" / "v0.34" / "calibration" / "dataset_summary.json"
    results_path = ROOT / "analysis" / "v0.34" / "calibration" / "calibration_results.json"

    with open(summary_path, "r", encoding="utf-8") as f:
        reported_summary = json.load(f)
    with open(results_path, "r", encoding="utf-8") as f:
        reported_results = json.load(f)

    # 1. Re-extract and audit positions
    samples = extract_quiet_positions(pgn_path)
    total_samples = len(samples)

    # Distribution by game and pair
    per_game: dict[int, int] = {}
    per_pair: dict[int, int] = {}
    fens: list[str] = []
    board_set: set[str] = set()
    mirrored_set: set[str] = set()
    duplicate_fens = 0
    mirrored_duplicates = 0

    for s in samples:
        per_game[s.game_id] = per_game.get(s.game_id, 0) + 1
        per_pair[s.pair_id] = per_pair.get(s.pair_id, 0) + 1

        b = chess.Board(s.fen)
        epd = b.epd()
        if epd in board_set:
            duplicate_fens += 1
        else:
            board_set.add(epd)

        m_epd = b.mirror().epd()
        if m_epd in board_set:
            mirrored_duplicates += 1
        mirrored_set.add(m_epd)

        fens.append(s.fen)

    # Partitioning
    train_s, val_s, test_s = partition_samples(samples)

    # Check pair separation
    train_pairs = set(s.pair_id for s in train_s)
    val_pairs = set(s.pair_id for s in val_s)
    test_pairs = set(s.pair_id for s in test_s)

    leakage_train_val = train_pairs.intersection(val_pairs)
    leakage_train_test = train_pairs.intersection(test_pairs)
    leakage_val_test = val_pairs.intersection(test_pairs)

    # 2. Recompute losses
    uncalib_cfg = CONFIG_V034_TAPERED
    calib_params = reported_results.get("calibrated_config", {})
    calib_kwargs = {**uncalib_cfg.to_dict(), **calib_params}
    calib_cfg = EvaluationConfig.from_dict(calib_kwargs)

    uncalib_train = evaluate_dataset_loss(train_s, uncalib_cfg)
    uncalib_val = evaluate_dataset_loss(val_s, uncalib_cfg)
    uncalib_test = evaluate_dataset_loss(test_s, uncalib_cfg)

    calib_train = evaluate_dataset_loss(train_s, calib_cfg)
    calib_val = evaluate_dataset_loss(val_s, calib_cfg)
    calib_test = evaluate_dataset_loss(test_s, calib_cfg)

    # Compare against reported numbers
    rep_u = reported_results["uncalibrated_results"]
    rep_c = reported_results["calibrated_results"]

    discrepancies = {
        "uncalib_train_mse": round(uncalib_train["mse"] - rep_u["train"]["mse"], 6),
        "uncalib_val_mse": round(uncalib_val["mse"] - rep_u["val"]["mse"], 6),
        "uncalib_test_mse": round(uncalib_test["mse"] - rep_u["test"]["mse"], 6),
        "calib_train_mse": round(calib_train["mse"] - rep_c["train"]["mse"], 6),
        "calib_val_mse": round(calib_val["mse"] - rep_c["val"]["mse"], 6),
        "calib_test_mse": round(calib_test["mse"] - rep_c["test"]["mse"], 6),
    }

    report = {
        "dataset_provenance": {
            "source_pgn": str(pgn_path),
            "total_samples": total_samples,
            "unique_positions": len(board_set),
            "duplicate_positions_count": duplicate_fens,
            "mirrored_duplicates_count": mirrored_duplicates,
            "games_represented": len(per_game),
            "pairs_represented": len(per_pair),
            "mean_positions_per_game": round(total_samples / max(1, len(per_game)), 2),
            "min_positions_per_game": min(per_game.values()) if per_game else 0,
            "max_positions_per_game": max(per_game.values()) if per_game else 0,
        },
        "partition_isolation": {
            "train_samples": len(train_s),
            "val_samples": len(val_s),
            "test_samples": len(test_s),
            "train_pairs": sorted(list(train_pairs)),
            "val_pairs": sorted(list(val_pairs)),
            "test_pairs": sorted(list(test_pairs)),
            "leakage_train_val": list(leakage_train_val),
            "leakage_train_test": list(leakage_train_test),
            "leakage_val_test": list(leakage_val_test),
            "zero_leakage_verified": (len(leakage_train_val) == 0 and len(leakage_train_test) == 0 and len(leakage_val_test) == 0),
        },
        "loss_recomputation": {
            "recomputed_uncalibrated": {
                "train": uncalib_train,
                "val": uncalib_val,
                "test": uncalib_test,
            },
            "recomputed_calibrated": {
                "train": calib_train,
                "val": calib_val,
                "test": calib_test,
            },
            "discrepancies_vs_reported": discrepancies,
            "recomputation_matches_reported_exactly": all(v == 0.0 for v in discrepancies.values()),
        },
        "methodological_limitations": {
            "target_label_noise": "Positions were labeled with binary/ternary final game results (1.0, 0.5, 0.0) from shallow games rather than deep engine ground truth (e.g., Stockfish depth 16+ evaluation converted to win probability).",
            "tuning_context_gap": "Static weight calibration on quiet positions ignores dynamic alpha-beta search interaction, quiescence search effects, and move-ordering heuristics.",
            "recommendation_future_milestone": "Generate quiet position datasets labeled by deep Stockfish evaluation scores (e.g. depth 16-20 centipawns mapped to sigmoid), or implement SPSA (Simultaneous Perturbation Stochastic Approximation) playing-strength tuning directly within the search harness.",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / "calibration_provenance.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Calibration provenance audit complete. Saved to {out_file}")
    return report


if __name__ == "__main__":
    run_calibration_provenance_audit()
