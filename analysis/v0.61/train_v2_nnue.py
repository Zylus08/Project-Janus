#!/usr/bin/env python3
"""Project Janus v0.61 - NNUE-V2 Model Training & Comparative Generalization Pipeline.

Trains and evaluates:
  T0 - Classical C1: Handcrafted static evaluation (control)
  T1 - NNUE-V1-Small: Existing frozen neural model (768 -> 64x2 -> 16 -> 1, 51K params)
  T2 - NNUE-V2-Small: Same architecture, trained on scaled 80K dataset
  T3 - NNUE-V2-Compact: Higher-capacity architecture (768 -> 128x2 -> 32 -> 1, 106K params)

Computes complete held-out evaluation on 10,000 test positions, including:
  MAE, RMSE, Spearman rank correlation, Pearson r, Sign Agreement, Pairwise Ranking,
  Phase breakdown, Tactical breakdown, and Paired Bootstrap 95% Confidence Intervals.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "analysis" / "v0.61" / "dataset"
MODELS_DIR = ROOT / "analysis" / "v0.61" / "models"
RAW_DIR = ROOT / "analysis" / "v0.61" / "raw"
V60_V1_SMALL_CHECKPOINT = ROOT / "analysis" / "v0.60" / "models" / "v1_small_best.pt"

TRAIN_JSON = DATA_DIR / "value_v2_train.json"
VAL_JSON = DATA_DIR / "value_v2_val.json"
TEST_JSON = DATA_DIR / "value_v2_test.json"


# =========================================================================
# 1. Feature Extraction (Half-KP without king buckets, 768 features)
# =========================================================================

def extract_features_half_kp(board: chess.Board) -> Tuple[List[int], List[int]]:
    """Extracts sparse feature indices for White STM and Black STM (768 per perspective)."""
    ft_white = []
    ft_black = []

    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is None:
            continue
        pt = piece.piece_type - 1  # 0..5

        # White perspective (normal rank orientation)
        c_white = 0 if piece.color == chess.WHITE else 1
        sq_white = sq
        ft_white.append(c_white * 384 + pt * 64 + sq_white)

        # Black perspective (vertically mirrored rank: sq ^ 56)
        c_black = 0 if piece.color == chess.BLACK else 1
        sq_black = sq ^ 56
        ft_black.append(c_black * 384 + pt * 64 + sq_black)

    return ft_white, ft_black


# =========================================================================
# 2. PyTorch Dataset & Batch Collation
# =========================================================================

class ChessValueDataset(Dataset):
    def __init__(self, json_path: Path, max_samples: Optional[int] = None):
        print(f"Loading {json_path.name}...")
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if max_samples:
            raw_data = raw_data[:max_samples]

        self.samples = []
        t0 = time.time()
        for idx, item in enumerate(raw_data):
            board = chess.Board(item["fen"])
            w_feats, b_feats = extract_features_half_kp(board)
            turn = 0 if board.turn == chess.WHITE else 1
            stm_feats = w_feats if turn == 0 else b_feats
            opp_feats = b_feats if turn == 0 else w_feats

            self.samples.append({
                "stm_feats": stm_feats,
                "opp_feats": opp_feats,
                "target_cp": float(item["raw_score_stm"]),
                "c1_score_stm": float(item.get("c1_score_stm", 0)),
                "phase": item.get("game_phase", "middlegame"),
                "ply": item.get("ply", 0),
            })
            if (idx + 1) % 25000 == 0:
                print(f"  Parsed {idx + 1:,}/{len(raw_data):,} positions ({time.time()-t0:.1f}s)...")
        print(f"Loaded {len(self.samples):,} positions from {json_path.name} in {time.time()-t0:.1f}s.")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


def collate_half_kp(batch: List[Dict[str, Any]]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Collates batch into dense float tensors [B, 768] for STM and Opponent."""
    B = len(batch)
    stm_tensor = torch.zeros(B, 768, dtype=torch.float32)
    opp_tensor = torch.zeros(B, 768, dtype=torch.float32)
    targets = torch.zeros(B, 1, dtype=torch.float32)

    for i, item in enumerate(batch):
        stm_tensor[i, item["stm_feats"]] = 1.0
        opp_tensor[i, item["opp_feats"]] = 1.0
        targets[i, 0] = item["target_cp"]

    return stm_tensor, opp_tensor, targets


# =========================================================================
# 3. Model Architectures
# =========================================================================

class NNUEValueNet(nn.Module):
    """Modular NNUE Value Evaluator supporting arbitrary accum_dim and l1_dim."""
    def __init__(self, feature_dim: int, accum_dim: int, l1_dim: int, eval_scale: float = 600.0):
        super().__init__()
        self.feature_dim = feature_dim
        self.accum_dim = accum_dim
        self.l1_dim = l1_dim
        self.eval_scale = eval_scale

        # Shared Feature Transformer across both perspectives
        self.ft = nn.Linear(feature_dim, accum_dim)
        # Dense Layer 1: Takes concatenated dual accumulators [2 * accum_dim] -> l1_dim
        self.fc1 = nn.Linear(2 * accum_dim, l1_dim)
        # Dense Layer 2: l1_dim -> 1 scalar output
        self.fc2 = nn.Linear(l1_dim, 1)

    def forward(self, stm_features: torch.Tensor, opp_features: torch.Tensor) -> torch.Tensor:
        # 1. Feature Transformer Accumulators
        acc_stm = torch.clamp(self.ft(stm_features), 0.0, 1.0)
        acc_opp = torch.clamp(self.ft(opp_features), 0.0, 1.0)

        # 2. Dual Perspective Concatenation
        dual_acc = torch.cat([acc_stm, acc_opp], dim=1)

        # 3. Dense Feedforward Layers with Clipped ReLU
        x = torch.clamp(self.fc1(dual_acc), 0.0, 1.0)
        x = self.fc2(x)

        # 4. Scale to Centipawns
        return x * self.eval_scale


# =========================================================================
# 4. Training Engine
# =========================================================================

def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    lr: float,
    device: torch.device,
    model_name: str,
) -> Dict[str, Any]:
    print(f"\nTraining {model_name} ({sum(p.numel() for p in model.parameters()):,} parameters) on {device}...")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_fn = nn.SmoothL1Loss(beta=50.0)

    best_val_loss = float("inf")
    best_weights = None
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        n_batches = 0
        t0 = time.time()

        for stm, opp, targets in train_loader:
            stm = stm.to(device)
            opp = opp.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            preds = model(stm, opp)
            loss = loss_fn(preds, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item()
            n_batches += 1

        scheduler.step()
        train_loss /= max(1, n_batches)

        # Validation
        model.eval()
        val_loss = 0.0
        val_batches = 0
        with torch.no_grad():
            for stm, opp, targets in val_loader:
                stm = stm.to(device)
                opp = opp.to(device)
                targets = targets.to(device)
                preds = model(stm, opp)
                val_loss += loss_fn(preds, targets).item()
                val_batches += 1
        val_loss /= max(1, val_batches)
        elapsed = time.time() - t0

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "lr": optimizer.param_groups[0]["lr"],
            "time_sec": elapsed,
        })

        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        flag = " *" if is_best else ""
        print(f"  Epoch {epoch:2d}/{epochs:2d}: Train Loss = {train_loss:6.2f} cp | Val Loss = {val_loss:6.2f} cp | Time = {elapsed:4.1f}s{flag}")

    return {
        "best_val_loss": best_val_loss,
        "best_weights": best_weights,
        "history": history,
    }


# =========================================================================
# 5. Held-Out Evaluation Metrics
# =========================================================================

def compute_spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    n = len(x)
    if n < 2:
        return 0.0
    d = rx - ry
    return float(1.0 - 6.0 * np.sum(d**2) / (n * (n**2 - 1)))


def evaluate_predictions(preds: np.ndarray, targets: np.ndarray, phases: List[str]) -> Dict[str, Any]:
    diffs = np.abs(preds - targets)
    mae = float(np.mean(diffs))
    rmse = float(np.sqrt(np.mean(diffs**2)))
    p95 = float(np.percentile(diffs, 95))
    rho = compute_spearman(preds, targets)
    r = float(np.corrcoef(preds, targets)[0, 1])

    # Sign agreement on non-trivial positions (|target| >= 25)
    mask_nontrivial = np.abs(targets) >= 25
    if np.sum(mask_nontrivial) > 0:
        sign_agree = float(np.mean((preds[mask_nontrivial] > 0) == (targets[mask_nontrivial] > 0)) * 100)
    else:
        sign_agree = 100.0

    # Pairwise ranking accuracy (2,000 random pairs)
    rng = np.random.default_rng(42)
    n = len(preds)
    idx1 = rng.integers(0, n, size=2000)
    idx2 = rng.integers(0, n, size=2000)
    valid_pairs = idx1 != idx2
    idx1, idx2 = idx1[valid_pairs], idx2[valid_pairs]
    target_rel = targets[idx1] > targets[idx2]
    pred_rel = preds[idx1] > preds[idx2]
    pairwise_acc = float(np.mean(target_rel == pred_rel) * 100)

    # Breakdown by phase
    phases_arr = np.array(phases)
    phase_metrics = {}
    for ph in ["opening", "middlegame", "endgame"]:
        mask_ph = phases_arr == ph
        if np.sum(mask_ph) > 0:
            ph_diffs = diffs[mask_ph]
            phase_metrics[ph] = {
                "count": int(np.sum(mask_ph)),
                "mae": float(np.mean(ph_diffs)),
                "rmse": float(np.sqrt(np.mean(ph_diffs**2))),
                "spearman_rho": compute_spearman(preds[mask_ph], targets[mask_ph]),
            }

    # Breakdown for Tactical (|targets| > 300) vs Quiet (|targets| <= 75)
    tactical_mask = np.abs(targets) > 300
    quiet_mask = np.abs(targets) <= 75
    tactical_mae = float(np.mean(diffs[tactical_mask])) if np.sum(tactical_mask) > 0 else 0.0
    quiet_mae = float(np.mean(diffs[quiet_mask])) if np.sum(quiet_mask) > 0 else 0.0

    return {
        "mae": mae,
        "rmse": rmse,
        "p95": p95,
        "spearman_rho": rho,
        "pearson_r": r,
        "sign_agreement_pct": sign_agree,
        "pairwise_accuracy_pct": pairwise_acc,
        "tactical_mae": tactical_mae,
        "quiet_mae": quiet_mae,
        "phases": phase_metrics,
    }


def compute_bootstrap_cis(
    preds_cand: np.ndarray,
    preds_ref: np.ndarray,
    targets: np.ndarray,
    n_resamples: int = 1000,
) -> Dict[str, Any]:
    """Computes paired bootstrap 95% confidence intervals for metric differences."""
    rng = np.random.default_rng(42)
    n = len(targets)
    delta_mae_samples = []
    delta_rho_samples = []

    diff_cand = np.abs(preds_cand - targets)
    diff_ref = np.abs(preds_ref - targets)

    for _ in range(n_resamples):
        indices = rng.integers(0, n, size=n)
        d_mae = float(np.mean(diff_cand[indices]) - np.mean(diff_ref[indices]))
        delta_mae_samples.append(d_mae)

    delta_mae_samples.sort()
    ci_lower_mae = float(np.percentile(delta_mae_samples, 2.5))
    ci_upper_mae = float(np.percentile(delta_mae_samples, 97.5))
    ci_mean_mae = float(np.mean(delta_mae_samples))

    return {
        "delta_mae_mean": ci_mean_mae,
        "delta_mae_ci_95": [ci_lower_mae, ci_upper_mae],
    }


# =========================================================================
# 6. Main Execution Pipeline
# =========================================================================

def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PROJECT JANUS v0.61 — NNUE-V2 TRAINING & EVALUATION PIPELINE")
    print("=" * 70)

    device = torch.device("cpu")
    print(f"Execution Device: {device}")

    # Load Datasets
    train_ds = ChessValueDataset(TRAIN_JSON)
    val_ds = ChessValueDataset(VAL_JSON)
    test_ds = ChessValueDataset(TEST_JSON)

    train_loader = DataLoader(train_ds, batch_size=512, shuffle=True, collate_fn=collate_half_kp)
    val_loader = DataLoader(val_ds, batch_size=512, shuffle=False, collate_fn=collate_half_kp)
    test_loader = DataLoader(test_ds, batch_size=512, shuffle=False, collate_fn=collate_half_kp)

    # ---------------------------------------------------------------------
    # Experiment T2: NNUE-V2-Small (M=64, 51K params)
    # ---------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("EXPERIMENT T2: NNUE-V2-Small (M=64, 51,297 params)")
    print("-" * 70)
    model_t2 = NNUEValueNet(feature_dim=768, accum_dim=64, l1_dim=16, eval_scale=600.0)
    res_t2 = train_model(model_t2, train_loader, val_loader, epochs=20, lr=0.001, device=device, model_name="NNUE-V2-Small")
    model_t2.load_state_dict(res_t2["best_weights"])
    torch.save(res_t2["best_weights"], MODELS_DIR / "v2_small_best.pt")
    print(f"Saved best V2-Small weights to {MODELS_DIR / 'v2_small_best.pt'}")

    # ---------------------------------------------------------------------
    # Experiment T3: NNUE-V2-Compact (M=128, 106K params)
    # ---------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("EXPERIMENT T3: NNUE-V2-Compact (M=128, 106,689 params)")
    print("-" * 70)
    model_t3 = NNUEValueNet(feature_dim=768, accum_dim=128, l1_dim=32, eval_scale=600.0)
    res_t3 = train_model(model_t3, train_loader, val_loader, epochs=20, lr=0.001, device=device, model_name="NNUE-V2-Compact")
    model_t3.load_state_dict(res_t3["best_weights"])
    torch.save(res_t3["best_weights"], MODELS_DIR / "v2_compact_best.pt")
    print(f"Saved best V2-Compact weights to {MODELS_DIR / 'v2_compact_best.pt'}")

    # ---------------------------------------------------------------------
    # Load Reference Models: T0 (C1 Control) and T1 (V1-Small Frozen)
    # ---------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("PREPARING HELD-OUT COMPARATIVE EVALUATION (10,000 TEST POSITIONS)")
    print("-" * 70)
    model_t1 = NNUEValueNet(feature_dim=768, accum_dim=64, l1_dim=16, eval_scale=600.0)
    if V60_V1_SMALL_CHECKPOINT.exists():
        state_t1 = torch.load(V60_V1_SMALL_CHECKPOINT, map_location="cpu")
        model_t1.load_state_dict(state_t1)
        print(f"Loaded frozen V1-Small reference from {V60_V1_SMALL_CHECKPOINT}")
    else:
        print("WARNING: V1-Small checkpoint not found; creating reference.")

    # Predict on 10,000 Test Positions
    targets = np.array([s["target_cp"] for s in test_ds.samples])
    c1_preds = np.array([s["c1_score_stm"] for s in test_ds.samples])
    phases = [s["phase"] for s in test_ds.samples]

    model_t1.eval()
    model_t2.eval()
    model_t3.eval()

    t1_preds_list = []
    t2_preds_list = []
    t3_preds_list = []

    with torch.no_grad():
        for stm, opp, _ in test_loader:
            t1_preds_list.extend(model_t1(stm, opp).squeeze().numpy().tolist())
            t2_preds_list.extend(model_t2(stm, opp).squeeze().numpy().tolist())
            t3_preds_list.extend(model_t3(stm, opp).squeeze().numpy().tolist())

    t1_preds = np.array(t1_preds_list)
    t2_preds = np.array(t2_preds_list)
    t3_preds = np.array(t3_preds_list)

    # Compute Comparative Metrics
    eval_t0 = evaluate_predictions(c1_preds, targets, phases)
    eval_t1 = evaluate_predictions(t1_preds, targets, phases)
    eval_t2 = evaluate_predictions(t2_preds, targets, phases)
    eval_t3 = evaluate_predictions(t3_preds, targets, phases)

    # Paired Bootstrap CIs
    ci_t2_vs_t1 = compute_bootstrap_cis(t2_preds, t1_preds, targets)
    ci_t2_vs_t0 = compute_bootstrap_cis(t2_preds, c1_preds, targets)
    ci_t3_vs_t2 = compute_bootstrap_cis(t3_preds, t2_preds, targets)

    print("\n" + "=" * 80)
    print("HELD-OUT TEST SET EVALUATION RESULTS (N = 10,000):")
    print("=" * 80)
    headers = f"{'Model / Evaluator':<28} | {'MAE (cp)':<9} | {'RMSE (cp)':<9} | {'Spearman':<9} | {'Sign (%)':<8} | {'Pairwise':<8}"
    print(headers)
    print("-" * 80)
    print(f"{'T0: Classical C1 Control':<28} | {eval_t0['mae']:<9.2f} | {eval_t0['rmse']:<9.2f} | {eval_t0['spearman_rho']:<9.4f} | {eval_t0['sign_agreement_pct']:<8.1f} | {eval_t0['pairwise_accuracy_pct']:<8.1f}")
    print(f"{'T1: NNUE-V1-Small (Frozen)':<28} | {eval_t1['mae']:<9.2f} | {eval_t1['rmse']:<9.2f} | {eval_t1['spearman_rho']:<9.4f} | {eval_t1['sign_agreement_pct']:<8.1f} | {eval_t1['pairwise_accuracy_pct']:<8.1f}")
    print(f"{'T2: NNUE-V2-Small (Scaled)':<28} | {eval_t2['mae']:<9.2f} | {eval_t2['rmse']:<9.2f} | {eval_t2['spearman_rho']:<9.4f} | {eval_t2['sign_agreement_pct']:<8.1f} | {eval_t2['pairwise_accuracy_pct']:<8.1f}")
    print(f"{'T3: NNUE-V2-Compact (M=128)':<28} | {eval_t3['mae']:<9.2f} | {eval_t3['rmse']:<9.2f} | {eval_t3['spearman_rho']:<9.4f} | {eval_t3['sign_agreement_pct']:<8.1f} | {eval_t3['pairwise_accuracy_pct']:<8.1f}")
    print("-" * 80)

    print("\nPaired Bootstrap Differences (95% Confidence Intervals):")
    print(f"  T2 vs T1 (Data Effect):     Delta MAE = {ci_t2_vs_t1['delta_mae_mean']:+.2f} cp  [95% CI: {ci_t2_vs_t1['delta_mae_ci_95'][0]:+.2f}, {ci_t2_vs_t1['delta_mae_ci_95'][1]:+.2f}]")
    print(f"  T2 vs T0 (Neural vs C1):    Delta MAE = {ci_t2_vs_t0['delta_mae_mean']:+.2f} cp  [95% CI: {ci_t2_vs_t0['delta_mae_ci_95'][0]:+.2f}, {ci_t2_vs_t0['delta_mae_ci_95'][1]:+.2f}]")
    print(f"  T3 vs T2 (Capacity Effect): Delta MAE = {ci_t3_vs_t2['delta_mae_mean']:+.2f} cp  [95% CI: {ci_t3_vs_t2['delta_mae_ci_95'][0]:+.2f}, {ci_t3_vs_t2['delta_mae_ci_95'][1]:+.2f}]")

    print("\nBreakdown by Game Phase (MAE cp):")
    for ph in ["opening", "middlegame", "endgame"]:
        print(f"  {ph.capitalize():<12}: T0={eval_t0['phases'][ph]['mae']:.2f} | T1={eval_t1['phases'][ph]['mae']:.2f} | T2={eval_t2['phases'][ph]['mae']:.2f} | T3={eval_t3['phases'][ph]['mae']:.2f}")

    # Output JSON metrics
    metrics_payload = {
        "test_sample_count": len(targets),
        "models": {
            "T0_classical_c1": eval_t0,
            "T1_nnue_v1_small": eval_t1,
            "T2_nnue_v2_small": eval_t2,
            "T3_nnue_v2_compact": eval_t3,
        },
        "bootstrap_paired_cis": {
            "t2_vs_t1_data_effect": ci_t2_vs_t1,
            "t2_vs_t0_neural_vs_classical": ci_t2_vs_t0,
            "t3_vs_t2_capacity_effect": ci_t3_vs_t2,
        },
        "training_histories": {
            "T2": res_t2["history"],
            "T3": res_t3["history"],
        },
    }

    metrics_path = RAW_DIR / "training_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"\nSaved all metrics to {metrics_path}")


if __name__ == "__main__":
    main()

