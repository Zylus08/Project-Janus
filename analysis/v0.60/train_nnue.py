"""Project Janus v0.60 - Neural Value Evaluation Training Pipeline.

Trains and evaluates:
- E0: Janus Classical Baseline C1 Static Evaluator (Control)
- E1: NNUE V1-Small (768 -> 64 -> 16 -> 1, CReLU [0, 127])
- E2: NNUE V1-Compact (3072 -> 128 -> 32 -> 1, CReLU [0, 127])

Computes all required metrics:
1. MAE against held-out teacher evaluations
2. RMSE
3. Spearman rank correlation
4. Score sign agreement
5. Breakdown by Opening, Middlegame, Endgame
6. Breakdown by evaluation magnitude

Exports trained models and checkpoints for native C++ inference.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import chess
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

def compute_spearman_rank_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Computes Spearman rank correlation using numpy without scipy dependency."""
    def get_ranks(x: np.ndarray) -> np.ndarray:
        temp = x.argsort()
        ranks = np.empty_like(temp)
        ranks[temp] = np.arange(len(x))
        return ranks.astype(float)

    ra = get_ranks(a)
    rb = get_ranks(b)
    corr = np.corrcoef(ra, rb)[0, 1]
    return float(corr) if not np.isnan(corr) else 0.0

sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "analysis" / "v0.60" / "dataset"
MODELS_DIR = ROOT / "analysis" / "v0.60" / "models"
RAW_DIR = ROOT / "analysis" / "v0.60" / "raw"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================================
# 1. Feature Extraction Routines
# =========================================================================

def extract_features_v1_small(board: chess.Board) -> Tuple[List[int], List[int]]:
    """Extracts sparse feature indices for V1-Small (768 features per perspective)."""
    ft_white = []
    ft_black = []

    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is None:
            continue
        pt = piece.piece_type - 1  # 0..5

        # White perspective (normal orientation)
        c_white = 0 if piece.color == chess.WHITE else 1
        sq_white = sq
        ft_white.append(c_white * 384 + pt * 64 + sq_white)

        # Black perspective (vertically mirrored: rank r -> 7 - r)
        c_black = 0 if piece.color == chess.BLACK else 1
        sq_black = sq ^ 56
        ft_black.append(c_black * 384 + pt * 64 + sq_black)

    return ft_white, ft_black


def extract_features_v1_compact(board: chess.Board) -> Tuple[List[int], List[int]]:
    """Extracts sparse feature indices for V1-Compact (4 king buckets * 768 = 3072 features)."""
    # Find king squares
    white_king_sq = board.king(chess.WHITE)
    black_king_sq = board.king(chess.BLACK)

    # 4 buckets based on file (0: a-b, 1: c-d, 2: e-f, 3: g-h)
    bucket_white = (white_king_sq % 8) // 2
    # For Black perspective, mirror square
    black_king_sq_mirrored = black_king_sq ^ 56
    bucket_black = (black_king_sq_mirrored % 8) // 2

    ft_white = []
    ft_black = []

    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is None:
            continue
        pt = piece.piece_type - 1

        c_white = 0 if piece.color == chess.WHITE else 1
        sq_white = sq
        base_white = c_white * 384 + pt * 64 + sq_white
        ft_white.append(bucket_white * 768 + base_white)

        c_black = 0 if piece.color == chess.BLACK else 1
        sq_black = sq ^ 56
        base_black = c_black * 384 + pt * 64 + sq_black
        ft_black.append(bucket_black * 768 + base_black)

    return ft_white, ft_black


# =========================================================================
# 2. PyTorch Dataset & Models
# =========================================================================

class ChessValueDataset(Dataset):
    """PyTorch Dataset loading pre-labeled position records with pre-cached features."""

    def __init__(self, json_file: Path, arch: str = "v1_small"):
        with open(json_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        self.arch = arch
        self.is_small = ("small" in arch.lower())
        self.max_feat = 768 if self.is_small else 3072

        self.samples = []
        for rec in raw_data:
            board = chess.Board(rec["fen"])
            if self.is_small:
                ft_w, ft_b = extract_features_v1_small(board)
            else:
                ft_w, ft_b = extract_features_v1_compact(board)

            is_white_stm = (board.turn == chess.WHITE)
            ft_stm = ft_w if is_white_stm else ft_b
            ft_nstm = ft_b if is_white_stm else ft_w

            x_stm = torch.zeros(self.max_feat, dtype=torch.float32)
            x_nstm = torch.zeros(self.max_feat, dtype=torch.float32)
            x_stm[ft_stm] = 1.0
            x_nstm[ft_nstm] = 1.0

            score_stm = float(rec["sf_score_stm"])
            clipped_score = max(-2000.0, min(2000.0, score_stm))

            self.samples.append({
                "x_stm": x_stm,
                "x_nstm": x_nstm,
                "target_score": torch.tensor(clipped_score, dtype=torch.float32),
                "raw_sf_score": score_stm,
                "c1_score": float(rec["c1_score_stm"]),
                "phase": rec["phase"],
                "fen": rec["fen"],
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


class NNUEValueNet(nn.Module):
    """Configurable NNUE Value Network supporting V1-Small and V1-Compact."""

    def __init__(self, feature_dim: int, accum_dim: int, l1_dim: int, eval_scale: float = 600.0):
        super().__init__()
        self.feature_dim = feature_dim
        self.accum_dim = accum_dim
        self.l1_dim = l1_dim
        self.eval_scale = eval_scale

        # Shared Feature Transformer layer for both perspectives
        self.ft = nn.Linear(feature_dim, accum_dim)

        # Dense Feedforward Output Network
        # Input: [accum_dim (stm) + accum_dim (nstm)] = 2 * accum_dim
        self.fc1 = nn.Linear(accum_dim * 2, l1_dim)
        self.fc2 = nn.Linear(l1_dim, 1)

    def forward(self, x_stm: torch.Tensor, x_nstm: torch.Tensor) -> torch.Tensor:
        # Accumulator computation
        acc_stm = self.ft(x_stm)
        acc_nstm = self.ft(x_nstm)

        # Clipped ReLU activation [0, 1.0] (corresponding to native [0, 127])
        act_stm = torch.clamp(acc_stm, min=0.0, max=1.0)
        act_nstm = torch.clamp(acc_nstm, min=0.0, max=1.0)

        # Concatenate perspectives: (stm, nstm)
        h = torch.cat([act_stm, act_nstm], dim=-1)

        # Hidden layer + Clipped ReLU
        h1 = torch.clamp(self.fc1(h), min=0.0, max=1.0)

        # Output linear projection scaled to centipawns
        out = self.fc2(h1) * self.eval_scale
        return out.squeeze(-1)


# =========================================================================
# 3. Training & Evaluation Engine
# =========================================================================

def train_model(
    arch_name: str,
    feature_dim: int,
    accum_dim: int,
    l1_dim: int,
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    seed: int = 42,
) -> Tuple[NNUEValueNet, Dict[str, Any]]:
    """Trains an NNUE candidate model on the training set with early stopping on validation."""
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

    print(f"\nTraining Candidate: {arch_name} (Inputs={feature_dim}, Accum={accum_dim}, L1={l1_dim})")

    train_dataset = ChessValueDataset(DATA_DIR / "value_train.json", arch=arch_name.lower())
    val_dataset = ChessValueDataset(DATA_DIR / "value_val.json", arch=arch_name.lower())

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    model = NNUEValueNet(feature_dim, accum_dim, l1_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)
    loss_fn = nn.SmoothL1Loss(beta=50.0)

    best_val_loss = float("inf")
    best_weights = None
    history = []

    t_start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss_sum = 0.0
        train_count = 0

        for batch in train_loader:
            x_stm = batch["x_stm"]
            x_nstm = batch["x_nstm"]
            targets = batch["target_score"]

            optimizer.zero_grad()
            preds = model(x_stm, x_nstm)
            loss = loss_fn(preds, targets)
            loss.backward()
            optimizer.step()

            train_loss_sum += loss.item() * len(targets)
            train_count += len(targets)

        train_loss = train_loss_sum / train_count

        # Validation
        model.eval()
        val_loss_sum = 0.0
        val_count = 0
        val_abs_err_sum = 0.0

        with torch.no_grad():
            for batch in val_loader:
                x_stm = batch["x_stm"]
                x_nstm = batch["x_nstm"]
                targets = batch["target_score"]

                preds = model(x_stm, x_nstm)
                loss = loss_fn(preds, targets)

                val_loss_sum += loss.item() * len(targets)
                val_abs_err_sum += torch.sum(torch.abs(preds - targets)).item()
                val_count += len(targets)

        val_loss = val_loss_sum / val_count
        val_mae = val_abs_err_sum / val_count
        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_mae": val_mae,
            "lr": optimizer.param_groups[0]["lr"],
        })

        if epoch % 5 == 0 or epoch == epochs:
            print(f"  Epoch {epoch:2d}/{epochs} | Train Loss: {train_loss:.2f} | Val Loss: {val_loss:.2f} | Val MAE: {val_mae:.1f} cp")

    train_duration = time.perf_counter() - t_start
    print(f"  Training finished in {train_duration:.2f}s. Best Val Loss: {best_val_loss:.2f}")

    # Restore best weights
    model.load_state_dict(best_weights)

    # Save FP32 checkpoint
    model_path = MODELS_DIR / f"{arch_name.lower()}_best.pt"
    torch.save(model.state_dict(), model_path)
    print(f"  Saved best model checkpoint to {model_path}")

    return model, {
        "arch_name": arch_name,
        "feature_dim": feature_dim,
        "accum_dim": accum_dim,
        "l1_dim": l1_dim,
        "total_params": sum(p.numel() for p in model.parameters()),
        "best_val_loss": best_val_loss,
        "train_duration_sec": train_duration,
        "history": history,
        "checkpoint_file": str(model_path.name),
    }


def evaluate_on_test_set(
    model: Optional[NNUEValueNet],
    arch_name: str,
    is_classical_c1: bool = False,
) -> Dict[str, Any]:
    """Computes comprehensive metrics on the held-out test partition."""
    print(f"\nEvaluating {'Classical C1 (Control)' if is_classical_c1 else arch_name} on held-out test set...")
    test_dataset = ChessValueDataset(DATA_DIR / "value_test.json", arch=arch_name.lower())
    loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

    predictions = []
    targets = []
    phases = []

    if is_classical_c1:
        for batch in loader:
            c1_scores = batch["c1_score"].numpy()
            sf_scores = batch["raw_sf_score"].numpy()
            batch_phases = batch["phase"]

            predictions.extend(c1_scores)
            targets.extend(sf_scores)
            phases.extend(batch_phases)
    else:
        model.eval()
        with torch.no_grad():
            for batch in loader:
                x_stm = batch["x_stm"]
                x_nstm = batch["x_nstm"]
                preds = model(x_stm, x_nstm).numpy()
                sf_scores = batch["raw_sf_score"].numpy()
                batch_phases = batch["phase"]

                predictions.extend(preds)
                targets.extend(sf_scores)
                phases.extend(batch_phases)

    preds_np = np.array(predictions)
    targets_np = np.array(targets)

    # Clip targets to [-2000, 2000] to evaluate standard tactical/positional range
    clipped_targets = np.clip(targets_np, -2000.0, 2000.0)
    clipped_preds = np.clip(preds_np, -2000.0, 2000.0)

    # Core Metrics
    mae = float(np.mean(np.abs(clipped_preds - clipped_targets)))
    rmse = float(np.sqrt(np.mean((clipped_preds - clipped_targets) ** 2)))
    spearman_corr = compute_spearman_rank_corr(preds_np, targets_np)

    # Sign Agreement (excluding near-equal positions |score| < 10)
    non_trivial_mask = np.abs(targets_np) >= 10.0
    if np.sum(non_trivial_mask) > 0:
        sign_agreement = float(
            np.mean(np.sign(preds_np[non_trivial_mask]) == np.sign(targets_np[non_trivial_mask]))
        )
    else:
        sign_agreement = 1.0

    # Phase Breakdown
    phase_metrics = {}
    for p_name in ["opening", "middlegame", "endgame"]:
        mask = np.array([p == p_name for p in phases])
        if np.sum(mask) > 0:
            phase_mae = float(np.mean(np.abs(clipped_preds[mask] - clipped_targets[mask])))
            phase_rmse = float(np.sqrt(np.mean((clipped_preds[mask] - clipped_targets[mask]) ** 2)))
            phase_metrics[p_name] = {
                "count": int(np.sum(mask)),
                "mae": phase_mae,
                "rmse": phase_rmse,
            }

    # Score Magnitude Breakdown
    mag_brackets = [
        ("balanced_[-100,100]", (np.abs(targets_np) <= 100)),
        ("slight_adv_[100,300]", ((np.abs(targets_np) > 100) & (np.abs(targets_np) <= 300))),
        ("large_adv_[>300]", (np.abs(targets_np) > 300)),
    ]
    bracket_metrics = {}
    for b_name, mask in mag_brackets:
        if np.sum(mask) > 0:
            bracket_metrics[b_name] = {
                "count": int(np.sum(mask)),
                "mae": float(np.mean(np.abs(clipped_preds[mask] - clipped_targets[mask]))),
                "bias": float(np.mean(clipped_preds[mask] - clipped_targets[mask])),
            }

    print(f"  Results for {arch_name}:")
    print(f"    MAE: {mae:.2f} cp | RMSE: {rmse:.2f} cp")
    print(f"    Spearman Rank Corr: {spearman_corr:.4f} | Sign Agreement: {sign_agreement*100:.1f}%")

    return {
        "model_name": arch_name,
        "mae": mae,
        "rmse": rmse,
        "spearman_rank_corr": float(spearman_corr),
        "sign_agreement": sign_agreement,
        "phase_breakdown": phase_metrics,
        "magnitude_breakdown": bracket_metrics,
    }


def main():
    print("=" * 60)
    print("PROJECT JANUS v0.60 — NEURAL VALUE TRAINING PIPELINE")
    print("=" * 60)

    # 1. Evaluate E0 (Classical Control C1)
    e0_metrics = evaluate_on_test_set(None, "E0_Classical_C1", is_classical_c1=True)

    # 2. Train and Evaluate E1 (V1-Small: 768 -> 64 -> 16 -> 1)
    e1_model, e1_train_info = train_model(
        arch_name="V1_Small",
        feature_dim=768,
        accum_dim=64,
        l1_dim=16,
        epochs=20,
        batch_size=64,
        lr=1e-3,
        seed=42,
    )
    e1_metrics = evaluate_on_test_set(e1_model, "E1_V1_Small")

    # 3. Train and Evaluate E2 (V1-Compact: 3072 -> 128 -> 32 -> 1)
    e2_model, e2_train_info = train_model(
        arch_name="V1_Compact",
        feature_dim=3072,
        accum_dim=128,
        l1_dim=32,
        epochs=20,
        batch_size=64,
        lr=1e-3,
        seed=42,
    )
    e2_metrics = evaluate_on_test_set(e2_model, "E2_V1_Compact")

    # Save telemetry JSON
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "e0_classical_control": e0_metrics,
        "e1_v1_small": {
            "train_info": e1_train_info,
            "test_metrics": e1_metrics,
        },
        "e2_v1_compact": {
            "train_info": e2_train_info,
            "test_metrics": e2_metrics,
        },
    }

    metrics_file = RAW_DIR / "training_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("TRAINING PIPELINE COMPLETE")
    print(f"Metrics saved to: {metrics_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
