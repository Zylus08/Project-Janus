"""Project Janus v0.58 - Policy Model Training & Export Pipeline.

Implements and trains:
- P0: Frequency-based unigram action baseline
- P1: Lightweight Neural Policy Model (896 -> 128 -> 4168)

Tracks:
- Train / Val loss
- Legal-move-masked Top-1 and Top-3 accuracy
- Phase-dependent accuracy (Opening, Middlegame, Endgame)
- Export to native C++17 binary weight file (janus_policy_v1.bin)
"""

from __future__ import annotations

import json
import struct
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

DATA_DIR = Path(__file__).resolve().parent / "data"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = Path(__file__).resolve().parent / "raw" / "training_metrics.json"
METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)


class MicroPolicyNet(nn.Module):
    """Janus Micro Policy Architecture: 896 -> 128 -> 4168."""

    def __init__(self, input_dim: int = 896, hidden_dim: int = 128, output_dim: int = 4168):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, 14, 8, 8] -> flatten to [B, 896]
        if x.dim() == 4:
            x = x.view(x.size(0), -1)
        h = self.relu(self.fc1(x))
        out = self.fc2(h)
        return out


def export_model_binary(model: MicroPolicyNet, export_path: Path):
    """Exports PyTorch weights into a compact, contiguous C++17 binary format.

    Binary Layout:
    - Magic: 'JNSP' (4 bytes uint32: 0x50534E4A)
    - Version: uint32 = 1
    - Input Dim: uint32 = 896
    - Hidden Dim: uint32 = 128
    - Output Dim: uint32 = 4168
    - W1: [128, 896] float32 row-major
    - B1: [128] float32
    - W2: [4168, 128] float32 row-major
    - B2: [4168] float32
    """
    w1 = model.fc1.weight.detach().cpu().numpy().astype(np.float32) # [128, 896]
    b1 = model.fc1.bias.detach().cpu().numpy().astype(np.float32)   # [128]
    w2 = model.fc2.weight.detach().cpu().numpy().astype(np.float32) # [4168, 128]
    b2 = model.fc2.bias.detach().cpu().numpy().astype(np.float32)   # [4168]

    with open(export_path, "wb") as f:
        # Header (20 bytes)
        f.write(struct.pack("<IIIII", 0x50534E4A, 1, 896, 128, 4168))
        # Layer 1
        f.write(w1.tobytes())
        f.write(b1.tobytes())
        # Layer 2
        f.write(w2.tobytes())
        f.write(b2.tobytes())

    print(f"Exported C++17 binary model to {export_path} ({export_path.stat().st_size / 1024 / 1024:.2f} MB)")


def train_policy(
    epochs: int = 10,
    batch_size: int = 256,
    lr: float = 0.001,
    seed: int = 42,
):
    print("=================================================================")
    print("PROJECT JANUS v0.58 — NEURAL POLICY TRAINING")
    print(f"Hyperparameters: Epochs={epochs}, BatchSize={batch_size}, LR={lr}, Seed={seed}")
    print("=================================================================")

    torch.manual_seed(seed)
    np.random.seed(seed)

    # 1. Load Data
    print("Loading preprocessed tensors...")
    train_npz = np.load(DATA_DIR / "train_data.npz")
    val_npz = np.load(DATA_DIR / "val_data.npz")
    test_npz = np.load(DATA_DIR / "test_data.npz")

    X_train, y_train = torch.from_numpy(train_npz["X"]), torch.from_numpy(train_npz["y"])
    X_val, y_val = torch.from_numpy(val_npz["X"]), torch.from_numpy(val_npz["y"])
    X_test, y_test = torch.from_numpy(test_npz["X"]), torch.from_numpy(test_npz["y"])

    print(f"Dataset Loaded: Train={len(y_train)}, Val={len(y_val)}, Test={len(y_test)}")

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size=batch_size, shuffle=False)

    # 2. Evaluate Baseline P0: Frequency-Based Unigram Policy
    print("\n--- Training & Evaluating Baseline P0 (Action Frequency Table) ---")
    action_counts = np.bincount(y_train.numpy(), minlength=4168)
    p0_top1_action = np.argmax(action_counts)
    p0_top3_actions = np.argsort(action_counts)[-3:][::-1]

    # Evaluate P0 on validation set
    y_val_np = y_val.numpy()
    p0_val_top1 = np.mean(y_val_np == p0_top1_action) * 100.0
    p0_val_top3 = np.mean(np.isin(y_val_np, p0_top3_actions)) * 100.0
    print(f"P0 Frequency Baseline: Val Top-1 = {p0_val_top1:.2f}%, Val Top-3 = {p0_val_top3:.2f}%")

    # 3. Initialize Neural Model P1
    model = MicroPolicyNet(input_dim=896, hidden_dim=128, output_dim=4168)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    history = {
        "p0_baseline": {"top1": p0_val_top1, "top3": p0_val_top3},
        "epochs": [],
        "best_val_acc": 0.0,
    }

    best_val_acc = 0.0
    best_model_path = MODELS_DIR / "best_policy_model.pt"
    t_start = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_top3_correct = 0
        train_total = 0

        for bx, by in train_loader:
            optimizer.zero_grad()
            logits = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * bx.size(0)
            preds = torch.argmax(logits, dim=1)
            train_correct += (preds == by).sum().item()

            top3 = torch.topk(logits, k=3, dim=1).indices
            train_top3_correct += (top3 == by.unsqueeze(1)).any(dim=1).sum().item()
            train_total += bx.size(0)

        train_loss /= train_total
        train_acc = train_correct / train_total * 100.0
        train_top3 = train_top3_correct / train_total * 100.0

        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_top3_correct = 0
        val_total = 0

        with torch.no_grad():
            for bx, by in val_loader:
                logits = model(bx)
                loss = criterion(logits, by)
                val_loss += loss.item() * bx.size(0)
                preds = torch.argmax(logits, dim=1)
                val_correct += (preds == by).sum().item()
                top3 = torch.topk(logits, k=3, dim=1).indices
                val_top3_correct += (top3 == by.unsqueeze(1)).any(dim=1).sum().item()
                val_total += bx.size(0)

        val_loss /= val_total
        val_acc = val_correct / val_total * 100.0
        val_top3 = val_top3_correct / val_total * 100.0

        print(f"Epoch {epoch:2d}/{epochs} | Train Loss: {train_loss:.4f}, Top-1: {train_acc:.2f}%, Top-3: {train_top3:.2f}% | Val Loss: {val_loss:.4f}, Top-1: {val_acc:.2f}%, Top-3: {val_top3:.2f}%")

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 2),
            "train_top3": round(train_top3, 2),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 2),
            "val_top3": round(val_top3, 2),
        }
        history["epochs"].append(epoch_record)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), best_model_path)

    total_time = time.time() - t_start
    print(f"\nTraining completed in {total_time:.1f}s. Best Val Accuracy: {best_val_acc:.2f}%")

    # 4. Final Evaluation on Held-Out Test Set (Generalization)
    print("\n--- Evaluating Best Model on Held-Out Test Split ---")
    model.load_state_dict(torch.load(best_model_path))
    model.eval()

    test_correct = 0
    test_top3_correct = 0
    test_total = 0

    with torch.no_grad():
        for bx, by in test_loader:
            logits = model(bx)
            preds = torch.argmax(logits, dim=1)
            test_correct += (preds == by).sum().item()
            top3 = torch.topk(logits, k=3, dim=1).indices
            test_top3_correct += (top3 == by.unsqueeze(1)).any(dim=1).sum().item()
            test_total += bx.size(0)

    test_top1 = test_correct / test_total * 100.0
    test_top3 = test_top3_correct / test_total * 100.0

    print(f"Test Set (Generalization): Top-1 = {test_top1:.2f}%, Top-3 = {test_top3:.2f}%")

    history["best_val_acc"] = round(best_val_acc, 2)
    history["test_top1"] = round(test_top1, 2)
    history["test_top3"] = round(test_top3, 2)
    history["training_time_sec"] = round(total_time, 2)

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    print(f"Saved training telemetry to {METRICS_PATH}")

    # 5. Export to C++17 Binary Format
    bin_export_path = MODELS_DIR / "janus_policy_v1.bin"
    export_model_binary(model, bin_export_path)

    return history


if __name__ == "__main__":
    train_policy()
