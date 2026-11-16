#!/usr/bin/env python3
"""
audit_training_objective.py
Phase 9: Training Objective Review & Pilot Retraining Experiment.
Audits the training parameters of H1 and performs a controlled 5-epoch pilot retraining
with Lambda-Loss (search score + outcome) on a subset of the dataset to compare
piece value calibration against the P2.1 baseline.
"""

import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import json
import math
import time
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DATA_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "data"

sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from train_janus_nnue import JanusNNUE, fen_to_features

class LambdaPilotDataset(Dataset):
    """
    Dataset that computes classical material balance as teacher evaluation
    combined with game outcome:
    y_target = (1 - lambda) * outcome + lambda * sigmoid(eval / 400)
    """
    def __init__(self, jsonl_path: Path, max_samples=10000, lambda_val=0.8):
        self.samples = []
        self.lambda_val = lambda_val
        
        piece_vals = {chess.PAWN: 100, chess.KNIGHT: 325, chess.BISHOP: 325, chess.ROOK: 500, chess.QUEEN: 900}
        
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    fen = rec["fen"]
                    outcome = float(rec["target_res"])
                    
                    # Compute approximate material balance from side-to-move perspective
                    b = chess.Board(fen)
                    mat_w = sum(len(b.pieces(pt, chess.WHITE)) * val for pt, val in piece_vals.items())
                    mat_b = sum(len(b.pieces(pt, chess.BLACK)) * val for pt, val in piece_vals.items())
                    mat_stm = (mat_w - mat_b) if b.turn == chess.WHITE else (mat_b - mat_w)
                    
                    # Sigmoid target from centipawns
                    eval_prob = 1.0 / (1.0 + math.exp(-mat_stm / 400.0))
                    
                    # Blended target
                    blended_target = (1.0 - lambda_val) * outcome + lambda_val * eval_prob
                    
                    self.samples.append((fen, blended_target, mat_stm))
                    if len(self.samples) >= max_samples:
                        break

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        fen, target, mat_cp = self.samples[idx]
        stm_f, ntm_f, stm = fen_to_features(fen)
        return stm_f, ntm_f, target

def collate_fn(batch):
    bsz = len(batch)
    stm_t = torch.zeros(bsz, 768)
    ntm_t = torch.zeros(bsz, 768)
    targets = torch.zeros(bsz, 1)
    for i, (sf, nf, t) in enumerate(batch):
        stm_t[i, sf] = 1.0
        ntm_t[i, nf] = 1.0
        targets[i, 0] = t
    return stm_t, ntm_t, targets

def run_training_objective_experiment():
    print("=" * 80)
    print("PHASE 9: TRAINING OBJECTIVE AUDIT & PILOT RETRAINING EXPERIMENT")
    print("=" * 80)

    # 1. Audit Parameters of Original H1
    h1_params = {
        "loss_function": "BCEWithLogitsLoss",
        "target_type": "Binary / Trinary Game Outcome (STM perspective)",
        "target_range": "[0.0, 1.0]",
        "optimizer": "Adam (lr=1e-3, weight_decay=1e-5)",
        "lr_schedule": "None (Constant 1e-3)",
        "batch_size": 256,
        "epochs": 5,
        "checkpoint_selection": "Final epoch (Epoch 5)",
        "random_seed": 42,
        "train_loss_history": [0.6219, 0.4502, 0.4112, 0.3980, 0.3906],
        "primary_defects": [
            "Outcome-only labeling introduces massive noise on blunders/reversals",
            "49.5% draw rate pulls logits toward zero, causing 4x-10x score compression",
            "Zero centipawn grounding causes Queen (203 cp) < Knight (226 cp) distortion"
        ]
    }

    print("\n--- 1. Original H1 Training Specification Audit ---")
    for k, v in h1_params.items():
        if k != "primary_defects":
            print(f"  {k:22s}: {v}")

    # 2. Pilot Retraining with Lambda-Loss on 10,000 samples
    print("\n--- 2. Pilot Retraining Experiment: Lambda-Loss (lambda=0.8) vs Baseline ---")
    train_ds = LambdaPilotDataset(DATA_DIR / "janus_nnue_train.jsonl", max_samples=10000, lambda_val=0.8)
    val_ds = LambdaPilotDataset(DATA_DIR / "janus_nnue_val.jsonl", max_samples=2000, lambda_val=0.8)

    loader_train = DataLoader(train_ds, batch_size=256, shuffle=True, collate_fn=collate_fn)
    loader_val = DataLoader(val_ds, batch_size=256, shuffle=False, collate_fn=collate_fn)

    torch.manual_seed(42)
    pilot_model = JanusNNUE(feature_dim=768, accum_dim=128, hidden_dim=32)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(pilot_model.parameters(), lr=1e-3, weight_decay=1e-5)

    t0 = time.time()
    for epoch in range(1, 6):
        pilot_model.train()
        total_loss = 0.0
        n_batches = 0
        for stm_x, ntm_x, targets in loader_train:
            optimizer.zero_grad()
            out = pilot_model(stm_x, ntm_x)
            loss = criterion(out, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1

        pilot_model.eval()
        val_loss = 0.0
        val_batches = 0
        with torch.no_grad():
            for stm_x, ntm_x, targets in loader_val:
                out = pilot_model(stm_x, ntm_x)
                loss = criterion(out, targets)
                val_loss += loss.item()
                val_batches += 1

        print(f"  Pilot Epoch {epoch}/5 | Train Loss: {total_loss/n_batches:.5f} | Val Loss: {val_loss/val_batches:.5f}")

    # Test piece values of pilot model
    def eval_pilot(fen):
        stm_f, ntm_f, _ = fen_to_features(fen)
        st = torch.zeros(1, 768); nt = torch.zeros(1, 768)
        st[0, stm_f] = 1.0; nt[0, ntm_f] = 1.0
        pilot_model.eval()
        with torch.no_grad():
            logit = pilot_model(st, nt).item()
        return logit * (400.0 / math.log(10.0))

    start_cp = eval_pilot("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    q_cp = eval_pilot("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    r_cp = eval_pilot("1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    n_cp = eval_pilot("r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    print("\n--- 3. Pilot Model Marginal Piece Values ---")
    print(f"  Startpos Score : {start_cp:.1f} cp")
    print(f"  White +Queen   : {q_cp:.1f} cp (Margin: +{q_cp - start_cp:.1f} cp)")
    print(f"  White +Rook    : {r_cp:.1f} cp (Margin: +{r_cp - start_cp:.1f} cp)")
    print(f"  White +Knight  : {n_cp:.1f} cp (Margin: +{n_cp - start_cp:.1f} cp)")

    ratio_q_n = (q_cp - start_cp) / (n_cp - start_cp) if (n_cp - start_cp) > 0 else 0
    print(f"  Queen / Knight Ratio: {ratio_q_n:.2f} (In original H1 this was 0.90!)")

    report_data = {
        "h1_original_params": h1_params,
        "pilot_retraining": {
            "lambda_val": 0.8,
            "samples": 10000,
            "epochs": 5,
            "queen_margin": round(q_cp - start_cp, 1),
            "rook_margin": round(r_cp - start_cp, 1),
            "knight_margin": round(n_cp - start_cp, 1),
            "queen_knight_ratio": round(ratio_q_n, 2),
            "monotonic_piece_ordering_restored": (q_cp > r_cp > n_cp > start_cp)
        }
    }

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "training_objective_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nTraining objective audit report saved to: {out_file}")

if __name__ == "__main__":
    run_training_objective_experiment()
