"""Dataset Design, Partitioning, and Evaluation Weight Calibration for Project Janus v0.34."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import NamedTuple

import chess
import chess.pgn

from janus.evaluation import (
    EvaluationConfig,
    CONFIG_V034_TAPERED,
    evaluate_white,
    get_game_phase,
)


class PositionSample(NamedTuple):
    fen: str
    result_white: float  # 1.0 (White win), 0.5 (Draw), 0.0 (Black win)
    phase: int
    pair_id: int
    game_id: int
    ply: int


def sigmoid(score_cp: float, K: float = 173.7178) -> float:
    """Logistic win-probability function with Elo-to-centipawn scaling constant K."""
    scaled = max(-50.0, min(50.0, score_cp / K))
    return 1.0 / (1.0 + math.exp(-scaled))


def extract_quiet_positions(pgn_path: Path) -> list[PositionSample]:
    """Extract quiet positions across games with phase labels and no tactical volatility."""
    samples: list[PositionSample] = []

    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            result_str = game.headers.get("Result", "*")
            if result_str == "1-0":
                r_w = 1.0
            elif result_str == "0-1":
                r_w = 0.0
            elif result_str == "1/2-1/2":
                r_w = 0.5
            else:
                continue

            game_id_str = game.headers.get("Round", "1")
            try:
                game_id = int(game_id_str)
            except ValueError:
                game_id = len(samples) + 1

            # Compute pair_id: pair = (game_id + 1) // 2
            pair_id = (game_id + 1) // 2

            board = game.board()
            moves = list(game.mainline_moves())
            total_moves = len(moves)

            for ply_idx, move in enumerate(moves):
                was_capture = board.is_capture(move)
                board.push(move)

                # Skip early opening book (first 10 plies / 5 full moves)
                if ply_idx < 10:
                    continue

                # Skip final 4 plies to avoid terminal collapse / resignations
                if ply_idx >= total_moves - 4:
                    continue

                # Quiet criteria:
                # 1. Not in check
                if board.is_check():
                    continue

                # 2. Neither incoming move nor next move is a capture
                if was_capture:
                    continue
                if ply_idx + 1 < total_moves and board.is_capture(moves[ply_idx + 1]):
                    continue

                # 3. Not game over
                if board.is_game_over():
                    continue

                phase = get_game_phase(board)

                # Sample every 4th quiet ply to keep samples uncorrelated
                if ply_idx % 4 == 0:
                    samples.append(
                        PositionSample(
                            fen=board.fen(),
                            result_white=r_w,
                            phase=phase,
                            pair_id=pair_id,
                            game_id=game_id,
                            ply=ply_idx,
                        )
                    )

    return samples


def partition_samples(
    samples: list[PositionSample],
) -> tuple[list[PositionSample], list[PositionSample], list[PositionSample]]:
    """Partition cleanly by Pair ID: Train (pairs 1-30), Val (pairs 31-40), Test (pairs 41-50).

    This strictly eliminates position and opening leakage across splits.
    """
    train = [s for s in samples if s.pair_id <= 30]
    val = [s for s in samples if 31 <= s.pair_id <= 40]
    test = [s for s in samples if 41 <= s.pair_id <= 50]
    return train, val, test


def evaluate_dataset_loss(
    samples: list[PositionSample], config: EvaluationConfig
) -> dict[str, float]:
    """Calculate Texel MSE loss, MAE, and prediction accuracy over a dataset."""
    if not samples:
        return {"mse": 0.0, "mae": 0.0, "accuracy": 0.0, "count": 0}

    total_sq_err = 0.0
    total_abs_err = 0.0
    correct_preds = 0

    for sample in samples:
        board = chess.Board(sample.fen)
        score = evaluate_white(board, config)
        pred = sigmoid(score)

        err = sample.result_white - pred
        total_sq_err += err * err
        total_abs_err += abs(err)

        # Directional agreement: win if pred > 0.55, loss if pred < 0.45, draw in between
        if (pred > 0.55 and sample.result_white == 1.0) or \
           (pred < 0.45 and sample.result_white == 0.0) or \
           (0.45 <= pred <= 0.55 and sample.result_white == 0.5):
            correct_preds += 1

    n = len(samples)
    return {
        "mse": total_sq_err / n,
        "mae": total_abs_err / n,
        "accuracy": (correct_preds / n) * 100.0,
        "count": n,
    }


def calibrate_parameters(
    train_samples: list[PositionSample],
    val_samples: list[PositionSample],
    initial_config: EvaluationConfig,
) -> tuple[EvaluationConfig, dict]:
    """Perform coordinate line search to calibrate positional evaluation weights on Train set only."""
    # Pre-parse train and val boards to avoid re-parsing FENs repeatedly
    train_data = [(chess.Board(s.fen), s.result_white) for s in train_samples]
    val_data = [(chess.Board(s.fen), s.result_white) for s in val_samples]

    def compute_loss(cfg: EvaluationConfig, data: list[tuple[chess.Board, float]]) -> float:
        total_loss = 0.0
        for b, r_w in data:
            score = evaluate_white(b, cfg)
            pred = sigmoid(score)
            err = r_w - pred
            total_loss += err * err
        return total_loss / len(data)

    current_cfg = initial_config
    best_train_loss = compute_loss(current_cfg, train_data)
    best_val_loss = compute_loss(current_cfg, val_data)

    param_ranges: dict[str, list[int]] = {
        "doubled_pawn_penalty_mg": [8, 10, 12, 14, 16],
        "doubled_pawn_penalty_eg": [10, 12, 16, 20, 24],
        "isolated_pawn_penalty_mg": [10, 12, 14, 16, 18],
        "isolated_pawn_penalty_eg": [12, 15, 18, 22, 26],
        "king_shield_bonus_mg": [8, 10, 12, 15, 18],
        "king_open_file_penalty_mg": [16, 19, 22, 25, 28],
        "king_center_bonus_eg": [8, 11, 14, 17, 20],
        "rook_open_file_bonus_mg": [14, 17, 20, 23, 26],
        "rook_semi_open_file_bonus_mg": [6, 8, 10, 12, 15],
        "bishop_pair_bonus": [18, 22, 25, 28, 32],
    }

    history: list[dict] = []
    # 2 passes over parameters
    for pass_idx in range(2):
        for param, candidates in param_ranges.items():
            best_candidate_val = getattr(current_cfg, param)
            improved = False

            for cand in candidates:
                cand_kwargs = {**current_cfg.__dict__, param: cand}
                cand_cfg = EvaluationConfig(**cand_kwargs)
                cand_loss = compute_loss(cand_cfg, train_data)

                if cand_loss < best_train_loss - 1e-6:
                    best_train_loss = cand_loss
                    best_candidate_val = cand
                    improved = True

            if improved:
                cand_kwargs = {**current_cfg.__dict__, param: best_candidate_val}
                current_cfg = EvaluationConfig(**cand_kwargs)
                val_loss = compute_loss(current_cfg, val_data)
                history.append({
                    "pass": pass_idx + 1,
                    "parameter": param,
                    "new_value": best_candidate_val,
                    "train_loss": best_train_loss,
                    "val_loss": val_loss,
                })
                best_val_loss = val_loss

    final_val_loss = compute_loss(current_cfg, val_data)
    report = {
        "initial_train_loss": compute_loss(initial_config, train_data),
        "initial_val_loss": compute_loss(initial_config, val_data),
        "final_train_loss": best_train_loss,
        "final_val_loss": final_val_loss,
        "tuning_history": history,
    }
    return current_cfg, report


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    pgn_path = repo_root / "analysis" / "v0.33" / "match" / "v033_match_500ms.pgn"
    out_dir = repo_root / "analysis" / "v0.34" / "calibration"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting quiet positions from {pgn_path}...")
    samples = extract_quiet_positions(pgn_path)
    print(f"Total quiet samples extracted: {len(samples)}")

    train_s, val_s, test_s = partition_samples(samples)
    print(f"Partition sizes: Train={len(train_s)}, Val={len(val_s)}, Test={len(test_s)}")

    # Phase breakdown
    def phase_dist(data: list[PositionSample]) -> dict[str, int]:
        dist = {"opening_mg (16-24)": 0, "midgame (9-15)": 0, "endgame (0-8)": 0}
        for s in data:
            if s.phase >= 16:
                dist["opening_mg (16-24)"] += 1
            elif s.phase >= 9:
                dist["midgame (9-15)"] += 1
            else:
                dist["endgame (0-8)"] += 1
        return dist

    dataset_summary = {
        "total_samples": len(samples),
        "source": "v033_match_500ms.pgn (100 games, 50 opening pairs)",
        "train_samples": len(train_s),
        "val_samples": len(val_s),
        "test_samples": len(test_s),
        "phase_distribution": {
            "train": phase_dist(train_s),
            "val": phase_dist(val_s),
            "test": phase_dist(test_s),
        },
        "leakage_prevention": "Strict partitioning by Pair ID: Train (pairs 1-30), Val (pairs 31-40), Test (pairs 41-50)",
    }

    with open(out_dir / "dataset_summary.json", "w", encoding="utf-8") as f:
        json.dump(dataset_summary, f, indent=2)
    print("Saved dataset summary to dataset_summary.json")

    # Evaluate uncalibrated baseline (CONFIG_V034_TAPERED)
    base_cfg = CONFIG_V034_TAPERED
    print("\n--- Evaluating Uncalibrated Baseline (CONFIG_V034_TAPERED) ---")
    base_train = evaluate_dataset_loss(train_s, base_cfg)
    base_val = evaluate_dataset_loss(val_s, base_cfg)
    base_test = evaluate_dataset_loss(test_s, base_cfg)
    print(f"Train: MSE={base_train['mse']:.5f}, MAE={base_train['mae']:.5f}, Acc={base_train['accuracy']:.1f}%")
    print(f"Val:   MSE={base_val['mse']:.5f}, MAE={base_val['mae']:.5f}, Acc={base_val['accuracy']:.1f}%")
    print(f"Test:  MSE={base_test['mse']:.5f}, MAE={base_test['mae']:.5f}, Acc={base_test['accuracy']:.1f}%")

    # Calibrate weights on Train only
    print("\n--- Calibrating Weights on Train Partition ---")
    calib_cfg, calib_info = calibrate_parameters(train_s, val_s, base_cfg)
    print("Tuning steps applied:", len(calib_info["tuning_history"]))

    # Evaluate calibrated weights out-of-sample
    print("\n--- Evaluating Calibrated Weights ---")
    calib_train = evaluate_dataset_loss(train_s, calib_cfg)
    calib_val = evaluate_dataset_loss(val_s, calib_cfg)
    calib_test = evaluate_dataset_loss(test_s, calib_cfg)
    print(f"Train: MSE={calib_train['mse']:.5f}, MAE={calib_train['mae']:.5f}, Acc={calib_train['accuracy']:.1f}%")
    print(f"Val:   MSE={calib_val['mse']:.5f}, MAE={calib_val['mae']:.5f}, Acc={calib_val['accuracy']:.1f}%")
    print(f"Test:  MSE={calib_test['mse']:.5f}, MAE={calib_test['mae']:.5f}, Acc={calib_test['accuracy']:.1f}%")

    # Compare out-of-sample changes
    test_mse_diff = calib_test["mse"] - base_test["mse"]
    val_mse_diff = calib_val["mse"] - base_val["mse"]
    print(f"\nDelta Val MSE: {val_mse_diff:+.6f}")
    print(f"Delta Test MSE (Out-of-sample): {test_mse_diff:+.6f}")

    tuned_params = list({h["parameter"] for h in calib_info.get("tuning_history", [])})
    calibration_report = {
        "uncalibrated_config": {p: getattr(base_cfg, p) for p in tuned_params},
        "calibrated_config": {p: getattr(calib_cfg, p) for p in tuned_params},
        "uncalibrated_results": {
            "train": base_train,
            "val": base_val,
            "test": base_test,
        },
        "calibrated_results": {
            "train": calib_train,
            "val": calib_val,
            "test": calib_test,
        },
        "out_of_sample_comparison": {
            "val_mse_change": val_mse_diff,
            "test_mse_change": test_mse_diff,
            "val_mae_change": calib_val["mae"] - base_val["mae"],
            "test_mae_change": calib_test["mae"] - base_test["mae"],
            "val_accuracy_change": calib_val["accuracy"] - base_val["accuracy"],
            "test_accuracy_change": calib_test["accuracy"] - base_test["accuracy"],
            "generalization_verdict": (
                "improved" if test_mse_diff < -1e-5
                else "neutral" if abs(test_mse_diff) <= 1e-5
                else "overfit_degradation"
            ),
        },
        "calibration_tuning_info": calib_info,
    }

    report_path = out_dir / "calibration_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(calibration_report, f, indent=2)
    print(f"\nSaved complete calibration report to {report_path}")


if __name__ == "__main__":
    main()
