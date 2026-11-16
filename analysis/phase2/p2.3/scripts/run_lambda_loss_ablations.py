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

from nnue_model import HalfKPNNUE
from train_nnue import ChessPositionDataset, collate_fn, compute_loss, evaluate_model, evaluate_diagnostic_positions

REPO_ROOT = r"E:\ChessXML\project-janus-phase1"
DATA_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/data")
RAW_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/raw")
MODELS_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/models")

def run_ablation(name, lambda_val, loss_type, train_loader, val_loader, device, epochs=5):
    print(f"\n--- Running Ablation: {name} (lambda={lambda_val}, loss={loss_type}, epochs={epochs}) ---")
    
    torch.manual_seed(42)
    random.seed(42)
    
    model = HalfKPNNUE(feature_count=40960, hidden_dim=128, dense_dim=32).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    t0 = time.time()
    train_history = []
    
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
            
            loss, s_loss, b_loss = compute_loss(logits, target_scores, target_outcomes, lambda_val, loss_type)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            n_batches += 1
            
        scheduler.step()
        avg_train_loss = epoch_loss / n_batches
        
        # Validation
        val_metrics = evaluate_model(model, val_loader, device)
        train_history.append({
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 5),
            "val_cp_mae": round(val_metrics["cp_mae"], 2),
            "val_score_mse": round(val_metrics["score_mse"], 5),
            "val_outcome_bce": round(val_metrics["outcome_bce"], 5)
        })
        print(f"  Epoch {epoch}/{epochs} | Train Loss: {avg_train_loss:.5f} | Val MAE: {val_metrics['cp_mae']:.1f} cp | Score MSE: {val_metrics['score_mse']:.5f} | BCE: {val_metrics['outcome_bce']:.5f}")
        
    elapsed = time.time() - t0
    final_diag = evaluate_diagnostic_positions(model, device)
    
    # Calculate Queen/Knight ratio
    # startpos baseline ~ 0
    q_margin = final_diag["queen_margin"] - final_diag["startpos"]
    n_margin = final_diag["knight_margin"] - final_diag["startpos"]
    qn_ratio = round(q_margin / n_margin, 2) if n_margin > 0 else 0.0
    
    result = {
        "ablation_id": name,
        "lambda": lambda_val,
        "loss_type": loss_type,
        "epochs": epochs,
        "elapsed_sec": round(elapsed, 1),
        "final_val_mae_cp": train_history[-1]["val_cp_mae"],
        "final_val_score_mse": train_history[-1]["val_score_mse"],
        "final_val_outcome_bce": train_history[-1]["val_outcome_bce"],
        "diagnostic_evals": final_diag,
        "queen_margin": round(q_margin, 1),
        "knight_margin": round(n_margin, 1),
        "queen_knight_ratio": qn_ratio,
        "history": train_history
    }
    
    # Save checkpoint if L2
    if name == "L2_calibrated_mixed_08":
        ckpt_path = os.path.join(MODELS_DIR, "h3_pilot_lambda08.pt")
        torch.save({
            "model_state_dict": model.state_dict(),
            "architecture": "HalfKP-40960-128x2-32-1",
            "feature_schema": "HalfKP-40960",
            "lambda": lambda_val,
            "metrics": result
        }, ckpt_path)
        result["checkpoint_path"] = os.path.relpath(ckpt_path, REPO_ROOT).replace("\\", "/")
        print(f"Saved primary checkpoint to {ckpt_path}")
        
    return result

def main():
    print("=== PHASE 6: CALIBRATED LAMBDA-LOSS ABLATION SUITE ===")
    
    train_path = os.path.join(DATA_DIR, "pilot_train.jsonl")
    val_path = os.path.join(DATA_DIR, "pilot_val.jsonl")
    
    if not os.path.exists(train_path) or not os.path.exists(val_path):
        print(f"Error: Data files not found ({train_path}). Waiting for pilot generation to finish...")
        return
        
    train_ds = ChessPositionDataset(train_path)
    val_ds = ChessPositionDataset(val_path)
    
    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False, collate_fn=collate_fn)
    
    print(f"Loaded Train: {len(train_ds)} positions | Val: {len(val_ds)} positions")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training Device: {device}")
    
    ablations = [
        ("L0_outcome_only_bce", 0.0, "mse"),
        ("L1_score_only_mse", 1.0, "mse"),
        ("L2_calibrated_mixed_08", 0.8, "mse"),
        ("L3_robust_huber_08", 0.8, "huber")
    ]
    
    results = {}
    for name, l_val, l_type in ablations:
        res = run_ablation(name, l_val, l_type, train_loader, val_loader, device, epochs=5)
        results[name] = res
        
    out_json = os.path.join(RAW_DIR, "lambda_loss_ablations.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAblation results written to {out_json}")

if __name__ == "__main__":
    main()
