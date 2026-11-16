#!/usr/bin/env python3
"""
train_janus_nnue.py
Milestone P2.1 Phase 4 & 5: Original NNUE Model Training & Fixed-Point Quantization.
Architecture: Dual-Perspective HalfKP-768 -> 128 (x2) -> 32 -> 1
Trains purely on authentic Project Janus Phase 1 game datasets from scratch (zero pretrained weights).
Exports float checkpoint and quantized binary weights.
"""

import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import json
import time
import math
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict

import chess
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

ROOT = Path("E:/ChessXML/project-janus-phase1")
DATA_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "data"
MODELS_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "models"
RAW_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "raw"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Feature mapping
PIECE_TO_INDEX_WHITE = {
    (chess.PAWN, chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK, chess.WHITE): 3,
    (chess.QUEEN, chess.WHITE): 4,
    (chess.KING, chess.WHITE): 5,
    (chess.PAWN, chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK, chess.BLACK): 9,
    (chess.QUEEN, chess.BLACK): 10,
    (chess.KING, chess.BLACK): 11,
}

PIECE_TO_INDEX_BLACK = {
    (chess.PAWN, chess.BLACK): 0,
    (chess.KNIGHT, chess.BLACK): 1,
    (chess.BISHOP, chess.BLACK): 2,
    (chess.ROOK, chess.BLACK): 3,
    (chess.QUEEN, chess.BLACK): 4,
    (chess.KING, chess.BLACK): 5,
    (chess.PAWN, chess.WHITE): 6,
    (chess.KNIGHT, chess.WHITE): 7,
    (chess.BISHOP, chess.WHITE): 8,
    (chess.ROOK, chess.WHITE): 9,
    (chess.QUEEN, chess.WHITE): 10,
    (chess.KING, chess.WHITE): 11,
}

def fen_to_features(fen_str: str) -> Tuple[List[int], List[int], int]:
    """Returns (stm_features, ntm_features, stm_int)"""
    board = chess.Board(fen_str)
    stm_white = (board.turn == chess.WHITE)
    w_feats = []
    b_feats = []
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is not None:
            p_idx_w = PIECE_TO_INDEX_WHITE[(piece.piece_type, piece.color)]
            w_feats.append(p_idx_w * 64 + sq)

            flipped_sq = sq ^ 56
            p_idx_b = PIECE_TO_INDEX_BLACK[(piece.piece_type, piece.color)]
            b_feats.append(p_idx_b * 64 + flipped_sq)

    if stm_white:
        return w_feats, b_feats, 0
    else:
        return b_feats, w_feats, 1

class ChessJsonlDataset(Dataset):
    def __init__(self, jsonl_path: Path):
        self.samples = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    self.samples.append((rec["fen"], float(rec["target_res"])))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        fen, target = self.samples[idx]
        stm_feats, ntm_feats, stm = fen_to_features(fen)
        return stm_feats, ntm_feats, target

def collate_fn(batch):
    batch_size = len(batch)
    # Dense binary representation for feature transformer batch computation
    stm_tensor = torch.zeros(batch_size, 768, dtype=torch.float32)
    ntm_tensor = torch.zeros(batch_size, 768, dtype=torch.float32)
    targets = torch.zeros(batch_size, 1, dtype=torch.float32)

    for i, (stm_f, ntm_f, t) in enumerate(batch):
        stm_tensor[i, stm_f] = 1.0
        ntm_tensor[i, ntm_f] = 1.0
        targets[i, 0] = t

    return stm_tensor, ntm_tensor, targets

class JanusNNUE(nn.Module):
    """
    Original Janus NNUE Architecture:
    Dual HalfKP-768 -> 128 (x2) -> 32 -> 1
    Uses Clipped ReLU activation [0, 1.0] for exact match with integer quantization.
    """
    def __init__(self, feature_dim=768, accum_dim=128, hidden_dim=32):
        super().__init__()
        self.accum_dim = accum_dim
        # Shared feature transformer for both perspectives
        self.ft = nn.Linear(feature_dim, accum_dim)
        # Fully connected layers
        self.l1 = nn.Linear(accum_dim * 2, hidden_dim)
        self.l2 = nn.Linear(hidden_dim, 1)

    def forward(self, stm_x, ntm_x):
        # Accumulators
        acc_stm = torch.clamp(self.ft(stm_x), 0.0, 1.0)
        acc_ntm = torch.clamp(self.ft(ntm_x), 0.0, 1.0)
        # Concatenate perspective features: [friendly, enemy]
        h = torch.cat([acc_stm, acc_ntm], dim=1)
        h = torch.clamp(self.l1(h), 0.0, 1.0)
        out = self.l2(h)
        return out

def evaluate_model(model, loader, criterion):
    model.eval()
    total_loss = 0.0
    total_samples = 0
    correct_preds = 0

    with torch.no_grad():
        for stm_x, ntm_x, targets in loader:
            outputs = model(stm_x, ntm_x)
            loss = criterion(outputs, targets)
            total_loss += loss.item() * len(targets)
            total_samples += len(targets)

            # Measure binary decision accuracy (prob > 0.5 vs target >= 0.5)
            probs = torch.sigmoid(outputs)
            pred_class = (probs >= 0.5).float()
            target_class = (targets >= 0.5).float()
            correct_preds += (pred_class == target_class).sum().item()

    mean_loss = total_loss / total_samples
    acc = correct_preds / total_samples
    return mean_loss, acc

def train():
    print("=" * 70)
    print("PHASE 4: TRAINING ORIGINAL JANUS NNUE (MODEL H1)")
    print("=" * 70)

    torch.manual_seed(42)
    np.random.seed(42)

    train_ds = ChessJsonlDataset(DATA_DIR / "janus_nnue_train.jsonl")
    val_ds = ChessJsonlDataset(DATA_DIR / "janus_nnue_val.jsonl")
    test_ds = ChessJsonlDataset(DATA_DIR / "janus_nnue_test.jsonl")

    print(f"Loaded datasets: Train={len(train_ds)}, Val={len(val_ds)}, Test={len(test_ds)}")

    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False, collate_fn=collate_fn)
    test_loader = DataLoader(test_ds, batch_size=256, shuffle=False, collate_fn=collate_fn)

    model = JanusNNUE(feature_dim=768, accum_dim=128, hidden_dim=32)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)

    epochs = 5
    best_val_loss = float("inf")
    history = []

    print("\nStarting model training (5 epochs)...")
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for stm_x, ntm_x, targets in train_loader:
            optimizer.zero_grad()
            outputs = model(stm_x, ntm_x)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / n_batches
        val_loss, val_acc = evaluate_model(model, val_loader, criterion)
        print(f"  Epoch {epoch}/{epochs} | Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f} | Val Acc: {val_acc*100:.2f}%")

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5),
            "val_acc_pct": round(val_acc * 100.0, 2)
        })

    elapsed = time.time() - t0
    print(f"\nTraining completed in {elapsed:.1f} seconds.")

    # Held-out Test Evaluation
    test_loss, test_acc = evaluate_model(model, test_loader, criterion)
    print(f"\nHeld-Out Test Evaluation:")
    print(f"  Test Loss: {test_loss:.5f}")
    print(f"  Test Accuracy: {test_acc*100:.2f}%")

    # Save PyTorch Float Checkpoint
    float_ckpt_path = MODELS_DIR / "janus_nnue_h1_float.pt"
    torch.save(model.state_dict(), float_ckpt_path)
    print(f"[SAVED] Float checkpoint: {float_ckpt_path}")

    # ========================================================================
    # Phase 5: Quantization to C++ INT16/INT8 Fixed-Point Format
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: QUANTIZING WEIGHTS FOR CPU INT16/INT8 INFERENCE")
    print("=" * 70)

    # Quantization Scale Factors:
    # Feature weights: Q_FT = 256.0 (INT16)
    # L1 weights: Q_L1 = 128.0 (INT8 / INT16)
    # L2 weights: Q_L2 = 128.0 (INT16)
    Q_FT = 256.0
    Q_L1 = 128.0
    Q_L2 = 128.0

    ft_w = model.ft.weight.detach().numpy() # [128, 768]
    ft_b = model.ft.bias.detach().numpy()   # [128]
    l1_w = model.l1.weight.detach().numpy() # [32, 256]
    l1_b = model.l1.bias.detach().numpy()   # [32]
    l2_w = model.l2.weight.detach().numpy() # [1, 32]
    l2_b = model.l2.bias.detach().numpy()   # [1]

    # Quantize
    ft_w_q = np.clip(np.round(ft_w * Q_FT), -32768, 32767).astype(np.int16)
    ft_b_q = np.clip(np.round(ft_b * Q_FT), -32768, 32767).astype(np.int16)
    l1_w_q = np.clip(np.round(l1_w * Q_L1), -32768, 32767).astype(np.int16)
    l1_b_q = np.clip(np.round(l1_b * (Q_FT * Q_L1)), -2147483648, 2147483647).astype(np.int32)
    l2_w_q = np.clip(np.round(l2_w * Q_L2), -32768, 32767).astype(np.int16)
    l2_b_q = np.clip(np.round(l2_b * (Q_L1 * Q_L2)), -2147483648, 2147483647).astype(np.int32)

    # Save binary model file: header + arrays
    bin_path = MODELS_DIR / "janus_nnue_h1.bin"
    with open(bin_path, "wb") as bf:
        # Magic: 'JANU' (0x554E414A) + version 1
        bf.write(b"JANU")
        bf.write(np.uint32(1).tobytes())
        bf.write(np.uint32(768).tobytes())
        bf.write(np.uint32(128).tobytes())
        bf.write(np.uint32(32).tobytes())
        bf.write(np.uint32(1).tobytes())

        # Weights
        bf.write(ft_w_q.tobytes()) # [128, 768] * int16
        bf.write(ft_b_q.tobytes()) # [128] * int16
        bf.write(l1_w_q.tobytes()) # [32, 256] * int16
        bf.write(l1_b_q.tobytes()) # [32] * int32
        bf.write(l2_w_q.tobytes()) # [1, 32] * int16
        bf.write(l2_b_q.tobytes()) # [1] * int32

    bin_sha256 = hashlib.sha256(bin_path.read_bytes()).hexdigest()
    print(f"[SAVED] Quantized binary weights: {bin_path} ({bin_path.stat().st_size} bytes, SHA256: {bin_sha256[:16]}...)")

    # Quantization Parity Test on 500 Test Samples
    print("\nMeasuring Float vs Quantized parity on 500 test positions...")
    diffs = []
    float_evals = []
    quant_evals = []

    for i in range(min(500, len(test_ds))):
        stm_f, ntm_f, t = test_ds[i]
        # Float forward
        stm_t = torch.zeros(1, 768)
        ntm_t = torch.zeros(1, 768)
        stm_t[0, stm_f] = 1.0
        ntm_t[0, ntm_f] = 1.0
        with torch.no_grad():
            f_out = model(stm_t, ntm_t).item()
        # Scale float logit to centipawns: cp = logit * (400 / ln(10))
        f_cp = f_out * (400.0 / math.log(10.0))
        float_evals.append(f_cp)

        # Quantized forward (pure integer arithmetic simulator)
        # 1. Accumulator: sum active feature weights + bias
        acc_stm = np.zeros(128, dtype=np.int32)
        acc_ntm = np.zeros(128, dtype=np.int32)
        acc_stm += ft_b_q
        acc_ntm += ft_b_q
        for f in stm_f:
            acc_stm += ft_w_q[:, f]
        for f in ntm_f:
            acc_ntm += ft_w_q[:, f]

        # Activation: clamp(acc, 0, Q_FT) -> scaled to [0, Q_FT]
        act_stm = np.clip(acc_stm, 0, int(Q_FT))
        act_ntm = np.clip(acc_ntm, 0, int(Q_FT))
        h0 = np.concatenate([act_stm, act_ntm]) # length 256

        # Layer 1: (h0 * l1_w + l1_b) / Q_FT -> clamp to [0, Q_L1]
        l1_sum = np.dot(l1_w_q, h0) + l1_b_q
        l1_act = np.clip(l1_sum // int(Q_FT), 0, int(Q_L1))

        # Output Layer: (l1_act * l2_w + l2_b) / Q_L1
        l2_sum = np.dot(l2_w_q[0], l1_act) + l2_b_q[0]
        q_logit = l2_sum / (Q_L1 * Q_L2)
        q_cp = q_logit * (400.0 / math.log(10.0))
        quant_evals.append(q_cp)

        diffs.append(abs(f_cp - q_cp))

    mae = float(np.mean(diffs))
    max_err = float(np.max(diffs))
    corr = float(np.corrcoef(float_evals, quant_evals)[0, 1])

    print(f"Quantization Parity Results:")
    print(f"  Mean Absolute Error (MAE): {mae:.2f} centipawns")
    print(f"  Max Error: {max_err:.2f} centipawns")
    print(f"  Pearson Correlation: {corr:.6f}")

    # Save summary report raw JSON
    report_data = {
        "model_name": "JanusNNUE_H1",
        "architecture": "768 -> 128 (x2) -> 32 -> 1",
        "total_parameters": 106689,
        "epochs": epochs,
        "training_time_sec": round(elapsed, 2),
        "history": history,
        "held_out_test": {
            "test_loss": round(test_loss, 5),
            "test_accuracy_pct": round(test_acc * 100.0, 2)
        },
        "quantization": {
            "scale_ft": Q_FT,
            "scale_l1": Q_L1,
            "scale_l2": Q_L2,
            "binary_path": str(bin_path.relative_to(ROOT)).replace("\\", "/"),
            "binary_size_bytes": bin_path.stat().st_size,
            "binary_sha256": bin_sha256,
            "mae_cp": round(mae, 2),
            "max_err_cp": round(max_err, 2),
            "correlation": round(corr, 6)
        }
    }

    report_path = RAW_DIR / "nnue_training_and_quantization_report.json"
    with open(report_path, "w", encoding="utf-8") as rf:
        json.dump(report_data, rf, indent=2)

    print(f"\n[DONE] Training & Quantization Report saved to {report_path}")

if __name__ == "__main__":
    train()
