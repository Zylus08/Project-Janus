#!/usr/bin/env python3
"""Project Janus v0.64 - Phase 3 NNUE-V3 Controlled Learning Ablation Pipeline.

Trains and evaluates:
- M0: Frozen NNUE-V2 (Baseline control from v0.61, trained on historical data)
- M1: Retrained NNUE-V2 architecture (768 -> 128x2 -> 32 -> 1) on the phase-balanced v3 dataset
- M2: NNUE-V3 architecture with SEF features (768 -> 128x2 + 32 SEF = 288 -> 32 -> 1) on the v3 dataset

Evaluates on the 15,000-position held-out test_v3.json across structural subtypes:
pawn endgames, rook endgames, minor-piece endgames, opposite bishops,
queenless middlegames, and locked pawn structures.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path("E:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "analysis" / "v0.64" / "features"))
from sef_extractor import extract_sef_vector

DATA_DIR = ROOT / "analysis" / "v0.64" / "dataset"
MODELS_DIR = ROOT / "analysis" / "v0.64" / "models"
RAW_DIR = ROOT / "analysis" / "v0.64" / "raw"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

V61_MODEL_PATH = ROOT / "analysis" / "v0.61" / "models" / "v2_compact_best.pt"

TRAIN_JSON = DATA_DIR / "value_v3_train.json"
VAL_JSON = DATA_DIR / "value_v3_val.json"
TEST_JSON = DATA_DIR / "value_v3_test.json"


def spearmanr_numpy(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    x_rank = np.argsort(np.argsort(x)).astype(float)
    y_rank = np.argsort(np.argsort(y)).astype(float)
    c = np.corrcoef(x_rank, y_rank)
    if np.isnan(c[0, 1]):
        return 0.0
    return float(c[0, 1])


def extract_features_half_kp(board: chess.Board) -> Tuple[List[int], List[int]]:
    ft_white = []
    ft_black = []
    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is None:
            continue
        pt = piece.piece_type - 1
        c_white = 0 if piece.color == chess.WHITE else 1
        ft_white.append(c_white * 384 + pt * 64 + sq)

        c_black = 0 if piece.color == chess.BLACK else 1
        sq_black = sq ^ 56
        ft_black.append(c_black * 384 + pt * 64 + sq_black)
    return ft_white, ft_black


class V3PreloadedDataset(Dataset):
    """Pre-extracts features into compact memory tensors for maximum training throughput."""
    def __init__(self, json_path: Path, max_samples: Optional[int] = None):
        print(f"Loading and pre-encoding {json_path.name}...")
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if max_samples:
            raw_data = raw_data[:max_samples]

        N = len(raw_data)
        self.stm_tensors = torch.zeros(N, 768, dtype=torch.float32)
        self.opp_tensors = torch.zeros(N, 768, dtype=torch.float32)
        self.sef_tensors = torch.zeros(N, 32, dtype=torch.float32)
        self.targets = torch.zeros(N, 1, dtype=torch.float32)

        self.metadata = []
        t0 = time.time()

        for idx, item in enumerate(raw_data):
            board = chess.Board(item["fen"])
            w_feats, b_feats = extract_features_half_kp(board)
            sef_vec = extract_sef_vector(board)
            turn = 0 if board.turn == chess.WHITE else 1

            stm_feats = w_feats if turn == 0 else b_feats
            opp_feats = b_feats if turn == 0 else w_feats

            self.stm_tensors[idx, stm_feats] = 1.0
            self.opp_tensors[idx, opp_feats] = 1.0

            if turn == 1:
                sef_stm = sef_vec[16:32] + sef_vec[0:16]
            else:
                sef_stm = sef_vec
            self.sef_tensors[idx] = torch.tensor(sef_stm, dtype=torch.float32)

            self.targets[idx, 0] = float(item["raw_score_stm"])

            self.metadata.append({
                "subtype": item.get("subtype", "unknown"),
                "material_phase": item.get("material_phase", 24),
                "fen": item["fen"],
            })

            if (idx + 1) % 40000 == 0 or idx + 1 == N:
                el = time.time() - t0
                print(f"  Parsed {idx + 1:,}/{N:,} positions in {el:.1f}s ({(idx+1)/el:.1f} pos/sec)...")

        print(f"Preloaded {N:,} positions into memory.")

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.stm_tensors[idx], self.opp_tensors[idx], self.sef_tensors[idx], self.targets[idx]


# =========================================================================
# Model Architectures
# =========================================================================

class NNUEValueNetV2(nn.Module):
    """NNUE-V2 Compact architecture: 768 -> 128x2 -> 32 -> 1."""
    def __init__(self, accum_dim: int = 128, l1_dim: int = 32, eval_scale: float = 600.0):
        super().__init__()
        self.eval_scale = eval_scale
        self.ft = nn.Linear(768, accum_dim)
        self.fc1 = nn.Linear(2 * accum_dim, l1_dim)
        self.fc2 = nn.Linear(l1_dim, 1)

    def forward(self, stm: torch.Tensor, opp: torch.Tensor, sef: Optional[torch.Tensor] = None) -> torch.Tensor:
        acc_stm = torch.clamp(self.ft(stm), 0.0, 1.0)
        acc_opp = torch.clamp(self.ft(opp), 0.0, 1.0)
        dual = torch.cat([acc_stm, acc_opp], dim=1)
        x = torch.clamp(self.fc1(dual), 0.0, 1.0)
        return self.fc2(x) * self.eval_scale


class NNUEValueNetV3(nn.Module):
    """NNUE-V3 Architecture with SEF: 768 -> 128x2 + 32 SEF = 288 -> 32 -> 1."""
    def __init__(self, accum_dim: int = 128, sef_dim: int = 32, l1_dim: int = 32, eval_scale: float = 600.0):
        super().__init__()
        self.eval_scale = eval_scale
        self.ft = nn.Linear(768, accum_dim)
        self.fc1 = nn.Linear(2 * accum_dim + sef_dim, l1_dim)
        self.fc2 = nn.Linear(l1_dim, 1)

    def forward(self, stm: torch.Tensor, opp: torch.Tensor, sef: torch.Tensor) -> torch.Tensor:
        acc_stm = torch.clamp(self.ft(stm), 0.0, 1.0)
        acc_opp = torch.clamp(self.ft(opp), 0.0, 1.0)
        combined = torch.cat([acc_stm, acc_opp, sef], dim=1)
        x = torch.clamp(self.fc1(combined), 0.0, 1.0)
        return self.fc2(x) * self.eval_scale


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    lr: float,
    model_name: str,
    save_path: Path,
) -> Dict[str, Any]:
    print(f"\nTraining {model_name} ({sum(p.numel() for p in model.parameters()):,} parameters)...")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_fn = nn.SmoothL1Loss(beta=50.0)

    best_val_mae = float("inf")
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        n_train = 0
        t0 = time.time()

        for stm, opp, sef, targets in train_loader:
            optimizer.zero_grad()
            preds = model(stm, opp, sef)
            loss = loss_fn(preds, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * len(targets)
            n_train += len(targets)

        scheduler.step()
        train_loss /= n_train

        # Validation
        model.eval()
        val_mae = 0.0
        n_val = 0
        with torch.no_grad():
            for stm, opp, sef, targets in val_loader:
                preds = model(stm, opp, sef)
                val_mae += torch.abs(preds - targets).sum().item()
                n_val += len(targets)
        val_mae /= n_val

        elapsed = time.time() - t0
        print(f"  Epoch {epoch:2d}/{epochs:2d} | Train Loss: {train_loss:.2f} | Val MAE: {val_mae:.2f} cp | {elapsed:.1f}s")
        history.append({"epoch": epoch, "train_loss": train_loss, "val_mae": val_mae})

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            torch.save(model.state_dict(), save_path)
            print(f"    * Saved new best model checkpoint -> {save_path.name} (Val MAE: {val_mae:.2f} cp)")

    print(f"Training complete. Best Val MAE: {best_val_mae:.2f} cp.")
    return {"history": history, "best_val_mae": best_val_mae}


def evaluate_model_on_subtypes(
    model: nn.Module,
    test_dataset: V3PreloadedDataset,
    model_name: str,
) -> Dict[str, Any]:
    print(f"\nEvaluating {model_name} on held-out test set ({len(test_dataset):,} positions)...")
    loader = DataLoader(test_dataset, batch_size=512, shuffle=False)
    model.eval()

    all_preds = []
    all_targets = []
    with torch.no_grad():
        for stm, opp, sef, targets in loader:
            preds = model(stm, opp, sef).squeeze(-1).numpy()
            all_preds.extend(preds)
            all_targets.extend(targets.squeeze(-1).numpy())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    subtypes = set(s["subtype"] for s in test_dataset.metadata)
    subtype_metrics = {}

    for sub in sorted(subtypes):
        indices = [i for i, s in enumerate(test_dataset.metadata) if s["subtype"] == sub]
        if not indices:
            continue
        p = all_preds[indices]
        t = all_targets[indices]
        mae = float(np.mean(np.abs(p - t)))
        rmse = float(np.sqrt(np.mean((p - t) ** 2)))
        rho = spearmanr_numpy(p, t)
        sign_agree = float(np.mean(np.sign(p) == np.sign(t)))
        subtype_metrics[sub] = {
            "count": len(indices),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "spearman_rho": round(rho, 4),
            "sign_agreement": round(sign_agree, 4),
        }

    endgame_indices = [
        i for i, s in enumerate(test_dataset.metadata)
        if s["subtype"] in ("pawn_endgame", "rook_endgame", "minor_piece_endgame", "opposite_bishops")
    ]
    p_end = all_preds[endgame_indices]
    t_end = all_targets[endgame_indices]
    endgame_mae = float(np.mean(np.abs(p_end - t_end)))
    endgame_rho = spearmanr_numpy(p_end, t_end)

    overall_mae = float(np.mean(np.abs(all_preds - all_targets)))
    overall_rmse = float(np.sqrt(np.mean((all_preds - all_targets) ** 2)))
    overall_rho = spearmanr_numpy(all_preds, all_targets)

    results = {
        "model_name": model_name,
        "overall": {
            "count": len(all_preds),
            "mae": round(overall_mae, 2),
            "rmse": round(overall_rmse, 2),
            "spearman_rho": round(overall_rho, 4),
        },
        "pure_endgames": {
            "count": len(endgame_indices),
            "mae": round(endgame_mae, 2),
            "spearman_rho": round(endgame_rho, 4),
        },
        "subtypes": subtype_metrics,
    }

    print(f"Results for {model_name}:")
    print(f"  Overall: MAE={overall_mae:.2f} cp | RMSE={overall_rmse:.2f} cp | rho={overall_rho:.4f}")
    print(f"  Pure Endgames ({len(endgame_indices):,} pos): MAE={endgame_mae:.2f} cp | rho={endgame_rho:.4f}")
    for sub, m in subtype_metrics.items():
        print(f"    - {sub:22s} (N={m['count']:5d}): MAE={m['mae']:6.2f} cp | rho={m['spearman_rho']:6.4f}")

    return results


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.64 — PHASE 3 CONTROLLED LEARNING ABLATION")
    print("=" * 80)

    # 1. Preload datasets
    train_ds = V3PreloadedDataset(TRAIN_JSON)
    val_ds = V3PreloadedDataset(VAL_JSON)
    test_ds = V3PreloadedDataset(TEST_JSON)

    train_loader = DataLoader(train_ds, batch_size=512, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=512, shuffle=False)

    # 2. Evaluate M0: Frozen NNUE-V2 (Compact)
    print("\n--- Model M0: Frozen NNUE-V2 (Baseline Control) ---")
    m0 = NNUEValueNetV2(accum_dim=128, l1_dim=32)
    if V61_MODEL_PATH.exists():
        print(f"Loading weights from {V61_MODEL_PATH.name}...")
        m0.load_state_dict(torch.load(V61_MODEL_PATH, weights_only=True))
    else:
        print("Warning: V61 model path not found, using initialized weights.")
    m0_results = evaluate_model_on_subtypes(m0, test_ds, "M0_Frozen_NNUE_V2")

    # 3. Train and Evaluate M1: Retrained NNUE-V2 Architecture on v3 Data
    print("\n--- Model M1: Retrained NNUE-V2 Architecture on Phase-Balanced Data ---")
    m1 = NNUEValueNetV2(accum_dim=128, l1_dim=32)
    m1_save = MODELS_DIR / "m1_v2_retrained_best.pt"
    train_model(m1, train_loader, val_loader, epochs=8, lr=1e-3, model_name="M1_V2_Retrained", save_path=m1_save)
    m1.load_state_dict(torch.load(m1_save, weights_only=True))
    m1_results = evaluate_model_on_subtypes(m1, test_ds, "M1_V2_Retrained")

    # 4. Train and Evaluate M2: NNUE-V3 with SEF Features on v3 Data
    print("\n--- Model M2: NNUE-V3 Architecture (with SEF) on Phase-Balanced Data ---")
    m2 = NNUEValueNetV3(accum_dim=128, sef_dim=32, l1_dim=32)
    m2_save = MODELS_DIR / "m2_v3_sef_best.pt"
    train_model(m2, train_loader, val_loader, epochs=8, lr=1e-3, model_name="M2_V3_SEF", save_path=m2_save)
    m2.load_state_dict(torch.load(m2_save, weights_only=True))
    m2_results = evaluate_model_on_subtypes(m2, test_ds, "M2_V3_SEF")

    # Save ablation summary
    ablation_summary = {
        "timestamp": time.time(),
        "models": {
            "M0_Frozen_NNUE_V2": m0_results,
            "M1_V2_Retrained": m1_results,
            "M2_V3_SEF": m2_results,
        }
    }
    with open(RAW_DIR / "ablation_results.json", "w", encoding="utf-8") as f:
        json.dump(ablation_summary, f, indent=2)

    print(f"\nSaved ablation results -> {RAW_DIR / 'ablation_results.json'}")


if __name__ == "__main__":
    main()
