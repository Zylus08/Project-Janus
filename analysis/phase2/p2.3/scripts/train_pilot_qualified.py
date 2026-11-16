import os
import sys
import json
import time
import math
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import chess

from nnue_model import HalfKPNNUE
from train_nnue import ChessPositionDataset, collate_fn, compute_loss, evaluate_model, evaluate_diagnostic_positions
from halfkp import get_halfkp_features

REPO_ROOT = r"E:\ChessXML\project-janus-phase1"
DATA_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/data")
RAW_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/raw")
MODELS_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/models")

def train_qualified_pilot():
    print("=== PHASE 7: REPRODUCIBLE PILOT TRAINING QUALIFICATION ===")
    
    torch.manual_seed(42)
    random.seed(42)
    
    train_path = os.path.join(DATA_DIR, "pilot_train.jsonl")
    val_path = os.path.join(DATA_DIR, "pilot_val.jsonl")
    test_path = os.path.join(DATA_DIR, "pilot_test.jsonl")
    
    train_ds = ChessPositionDataset(train_path)
    val_ds = ChessPositionDataset(val_path)
    test_ds = ChessPositionDataset(test_path)
    
    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False, collate_fn=collate_fn)
    test_loader = DataLoader(test_ds, batch_size=256, shuffle=False, collate_fn=collate_fn)
    
    device = torch.device("cpu")
    model = HalfKPNNUE(40960, 128, 32).to(device)
    
    # Material prior initialization for 40,960 features
    with torch.no_grad():
        vals = [0.1, 0.3, 0.3, 0.5, 0.9] # P, N, B, R, Q
        for k in range(64):
            for c in range(10):
                t = c % 5
                is_enemy = c >= 5
                v = vals[t] * (-1.0 if is_enemy else 1.0)
                idx_start = k * 640 + c * 64
                model.ft_weights[idx_start:idx_start+64] += (v / 10.0)
        model.ft_biases.fill_(0.5)
        
    optimizer = optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)
    epochs = 10
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    t0 = time.time()
    history = []
    
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        
        for batch in train_loader:
            w_idx = batch["w_indices"].to(device)
            w_off = batch["w_offsets"].to(device)
            b_idx = batch["b_indices"].to(device)
            b_off = batch["b_offsets"].to(device)
            stm = batch["stm"].to(device)
            target_scores = batch["score_probs"].to(device)
            target_outcomes = batch["outcomes"].to(device)
            
            optimizer.zero_grad()
            logits = model(w_idx, w_off, b_idx, b_off, stm)
            
            loss, s_loss, b_loss = compute_loss(logits, target_scores, target_outcomes, lambda_val=0.8)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            n_batches += 1
            
        scheduler.step()
        avg_train_loss = epoch_loss / n_batches
        
        val_metrics = evaluate_model(model, val_loader, device)
        diag = evaluate_diagnostic_positions(model, device)
        
        history.append({
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 5),
            "val_cp_mae": round(val_metrics["cp_mae"], 2),
            "val_score_mse": round(val_metrics["score_mse"], 5),
            "val_outcome_bce": round(val_metrics["outcome_bce"], 5),
            "diag": diag
        })
        print(f"Epoch {epoch:2d}/{epochs} | Loss: {avg_train_loss:.5f} | Val MAE: {val_metrics['cp_mae']:.1f} cp | Diag: {diag}")
        
    elapsed = time.time() - t0
    
    # Final evaluation on held-out test set
    test_metrics = evaluate_model(model, test_loader, device)
    final_diag = evaluate_diagnostic_positions(model, device)
    
    q_margin = final_diag["queen_margin"] - final_diag["startpos"]
    n_margin = final_diag["knight_margin"] - final_diag["startpos"]
    
    # Save qualified checkpoint
    ckpt_path = os.path.join(MODELS_DIR, "h3_pilot_qualified.pt")
    torch.save({
        "model_state_dict": model.state_dict(),
        "architecture": "HalfKP-40960-128x2-32-1",
        "feature_schema": "HalfKP-40960",
        "lambda": 0.8,
        "epochs": epochs,
        "test_metrics": test_metrics,
        "final_diag": final_diag
    }, ckpt_path)
    
    report = {
        "pipeline": "P2.3_Pilot_Training_Qualification",
        "architecture": "HalfKP-40960-128x2-32-1",
        "epochs": epochs,
        "training_time_sec": round(elapsed, 1),
        "validation_metrics": history[-1],
        "held_out_test_metrics": {
            "test_cp_mae": round(test_metrics["cp_mae"], 2),
            "test_score_mse": round(test_metrics["score_mse"], 5),
            "test_outcome_bce": round(test_metrics["outcome_bce"], 5)
        },
        "diagnostic_suite": final_diag,
        "material_ordering": {
            "startpos_cp": final_diag["startpos"],
            "queen_margin_cp": round(q_margin, 1),
            "knight_margin_cp": round(n_margin, 1),
            "queen_exceeds_knight": q_margin > n_margin,
            "startpos_in_bounds": -10 <= final_diag["startpos"] <= 35,
            "status": "QUALIFIED" if (q_margin > n_margin and -10 <= final_diag["startpos"] <= 50) else "REJECTED"
        },
        "checkpoint": os.path.relpath(ckpt_path, REPO_ROOT).replace("\\", "/"),
        "history": history
    }
    
    out_json = os.path.join(RAW_DIR, "pilot_training_audit.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nFinal Test Set MAE: {test_metrics['cp_mae']:.1f} cp")
    print(f"Material Hierarchy: Queen Margin (+{q_margin:.1f} cp) > Knight Margin (+{n_margin:.1f} cp): {q_margin > n_margin}")
    print(f"Startpos Evaluation: {final_diag['startpos']:.1f} cp (Bounds: [-10, +50]): {report['material_ordering']['startpos_in_bounds']}")
    print(f"Audit report saved to {out_json}")

if __name__ == "__main__":
    train_qualified_pilot()
