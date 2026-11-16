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

def train_h3():
    print("=== PHASE 9: FULL H3 CANDIDATE TRAINING (SCALED DATASET) ===")
    
    torch.manual_seed(42)
    random.seed(42)
    
    train_path = os.path.join(DATA_DIR, "scaled_train.jsonl")
    val_path = os.path.join(DATA_DIR, "scaled_val.jsonl")
    test_path = os.path.join(DATA_DIR, "scaled_test.jsonl")
    
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
    epochs = 15
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
    
    # Evaluate held-out test set
    model.eval()
    total_mae_clipped = 0.0
    total_mae_non_mate = 0.0
    non_mate_count = 0
    total_n = 0
    
    with torch.no_grad():
        for b in test_loader:
            logits = model(b['w_indices'], b['w_offsets'], b['b_indices'], b['b_offsets'], b['stm'])
            pred_cp = logits * 400.0
            
            target_clipped = torch.clamp(b['teacher_cps'], -2000.0, 2000.0)
            mae_clipped = torch.abs(pred_cp - target_clipped).sum().item()
            total_mae_clipped += mae_clipped
            
            mask = torch.abs(b['teacher_cps']) <= 1500.0
            if mask.sum() > 0:
                mae_non_mate = torch.abs(pred_cp[mask] - b['teacher_cps'][mask]).sum().item()
                total_mae_non_mate += mae_non_mate
                non_mate_count += mask.sum().item()
            total_n += len(b['stm'])
            
    mae_clipped_final = total_mae_clipped / total_n
    mae_non_mate_final = total_mae_non_mate / non_mate_count if non_mate_count > 0 else 0.0
    
    final_diag = evaluate_diagnostic_positions(model, device)
    q_margin = final_diag["queen_margin"] - final_diag["startpos"]
    n_margin = final_diag["knight_margin"] - final_diag["startpos"]
    
    # Save frozen Candidate H3 checkpoint
    ckpt_path = os.path.join(MODELS_DIR, "janus_nnue_h3.pt")
    torch.save({
        "model_state_dict": model.state_dict(),
        "architecture": "HalfKP-40960-128x2-32-1",
        "feature_schema": "HalfKP-40960",
        "lambda": 0.8,
        "epochs": epochs,
        "dataset_train_positions": len(train_ds),
        "dataset_val_positions": len(val_ds),
        "dataset_test_positions": len(test_ds),
        "test_mae_clipped": mae_clipped_final,
        "test_mae_non_mate": mae_non_mate_final,
        "final_diag": final_diag
    }, ckpt_path)
    
    report = {
        "candidate": "Janus_Hybrid_H3",
        "architecture": "HalfKP-40960-128x2-32-1",
        "total_parameters": 5251265,
        "training_time_sec": round(elapsed, 1),
        "dataset": {
            "train_positions": len(train_ds),
            "val_positions": len(val_ds),
            "test_positions": len(test_ds)
        },
        "held_out_test_metrics": {
            "test_cp_mae_clipped": round(mae_clipped_final, 2),
            "test_cp_mae_non_mate": round(mae_non_mate_final, 2),
            "val_score_mse": history[-1]["val_score_mse"],
            "val_outcome_bce": history[-1]["val_outcome_bce"]
        },
        "diagnostic_suite": final_diag,
        "material_hierarchy": {
            "startpos_cp": final_diag["startpos"],
            "queen_margin_cp": round(q_margin, 1),
            "knight_margin_cp": round(n_margin, 1),
            "queen_exceeds_knight": q_margin > n_margin,
            "king_shelter_penalty_cp": round(final_diag["damaged_king"] - final_diag["startpos"], 1)
        },
        "checkpoint": os.path.relpath(ckpt_path, REPO_ROOT).replace("\\", "/"),
        "history": history
    }
    
    out_json = os.path.join(RAW_DIR, "h3_training_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nCandidate H3 Training Complete!")
    print(f"Test MAE (Non-Mate, N={non_mate_count}): {mae_non_mate_final:.1f} cp")
    print(f"Material Hierarchy: Queen Margin (+{q_margin:.1f} cp) > Knight Margin (+{n_margin:.1f} cp): {q_margin > n_margin}")
    print(f"King Safety Penalty: {report['material_hierarchy']['king_shelter_penalty_cp']} cp")
    print(f"Checkpoint saved to {ckpt_path}")
    print(f"Audit report saved to {out_json}")

if __name__ == "__main__":
    train_h3()
