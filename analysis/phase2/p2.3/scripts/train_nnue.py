import os
import sys
import json
import time
import math
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import chess

from halfkp import get_halfkp_features
from nnue_model import HalfKPNNUE

class ChessPositionDataset(Dataset):
    def __init__(self, jsonl_path):
        self.samples = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                self.samples.append(record)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        fen = item["fen"]
        board = chess.Board(fen)
        
        wf, bf = get_halfkp_features(board)
        stm = 1.0 if board.turn == chess.WHITE else 0.0
        
        # Teacher score target prob
        teacher_cp = item.get("teacher_score_cp", 0)
        target_score_prob = 1.0 / (1.0 + math.exp(-teacher_cp / 400.0))
        
        # Outcome target
        target_outcome = item.get("target_outcome", 0.5)
        
        return {
            "wf": wf,
            "bf": bf,
            "stm": stm,
            "teacher_cp": teacher_cp,
            "score_prob": target_score_prob,
            "outcome": target_outcome
        }

def collate_fn(batch):
    w_indices = []
    w_offsets = [0]
    b_indices = []
    b_offsets = [0]
    
    stms = []
    score_probs = []
    outcomes = []
    teacher_cps = []
    
    for item in batch:
        wf = item["wf"]
        bf = item["bf"]
        
        w_indices.extend(wf)
        w_offsets.append(len(w_indices))
        
        b_indices.extend(bf)
        b_offsets.append(len(b_indices))
        
        stms.append(item["stm"])
        score_probs.append(item["score_prob"])
        outcomes.append(item["outcome"])
        teacher_cps.append(item["teacher_cp"])
        
    w_offsets.pop()
    b_offsets.pop()
    
    return {
        "w_indices": torch.tensor(w_indices, dtype=torch.long),
        "w_offsets": torch.tensor(w_offsets, dtype=torch.long),
        "b_indices": torch.tensor(b_indices, dtype=torch.long),
        "b_offsets": torch.tensor(b_offsets, dtype=torch.long),
        "stm": torch.tensor(stms, dtype=torch.float32),
        "score_probs": torch.tensor(score_probs, dtype=torch.float32).unsqueeze(1),
        "outcomes": torch.tensor(outcomes, dtype=torch.float32).unsqueeze(1),
        "teacher_cps": torch.tensor(teacher_cps, dtype=torch.float32).unsqueeze(1)
    }

def compute_loss(pred_logits, target_scores, target_outcomes, lambda_val=0.8, loss_type="mse"):
    pred_prob = torch.sigmoid(pred_logits)
    
    # Outcome Loss: BCE
    bce_loss = nn.functional.binary_cross_entropy(pred_prob, target_outcomes)
    
    # Score Loss
    if loss_type == "mse":
        score_loss = nn.functional.mse_loss(pred_prob, target_scores)
    elif loss_type == "huber":
        score_loss = nn.functional.huber_loss(pred_prob, target_scores, delta=0.1)
    else:
        score_loss = nn.functional.mse_loss(pred_prob, target_scores)
        
    total_loss = lambda_val * score_loss + (1.0 - lambda_val) * bce_loss
    return total_loss, score_loss.item(), bce_loss.item()

def evaluate_model(model, dataloader, device, tau=400.0):
    model.eval()
    total_cp_mae = 0.0
    total_samples = 0
    total_score_mse = 0.0
    total_outcome_bce = 0.0
    
    with torch.no_grad():
        for batch in dataloader:
            w_idx = batch["w_indices"].to(device)
            w_off = batch["w_offsets"].to(device)
            b_idx = batch["b_indices"].to(device)
            b_off = batch["b_offsets"].to(device)
            stm = batch["stm"].to(device)
            target_scores = batch["score_probs"].to(device)
            target_outcomes = batch["outcomes"].to(device)
            teacher_cps = batch["teacher_cps"].to(device)
            
            logits = model(w_idx, w_off, b_idx, b_off, stm)
            pred_cp = logits * tau
            pred_prob = torch.sigmoid(logits)
            
            mae = torch.abs(pred_cp - teacher_cps).sum().item()
            score_mse = nn.functional.mse_loss(pred_prob, target_scores, reduction='sum').item()
            outcome_bce = nn.functional.binary_cross_entropy(pred_prob, target_outcomes, reduction='sum').item()
            
            b_size = len(stm)
            total_cp_mae += mae
            total_score_mse += score_mse
            total_outcome_bce += outcome_bce
            total_samples += b_size
            
    return {
        "cp_mae": total_cp_mae / total_samples,
        "score_mse": total_score_mse / total_samples,
        "outcome_bce": total_outcome_bce / total_samples
    }

def evaluate_diagnostic_positions(model, device, tau=400.0):
    model.eval()
    diagnostics = [
        ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        ("queen_margin", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"), # White +Q
        ("knight_margin", "r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"), # White +N
        ("damaged_king", "r1bq1rk1/pppp1p1p/2n3p1/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 8")
    ]
    results = {}
    with torch.no_grad():
        for name, fen in diagnostics:
            board = chess.Board(fen)
            wf, bf = get_halfkp_features(board)
            stm = 1.0 if board.turn == chess.WHITE else 0.0
            
            w_idx = torch.tensor(wf, dtype=torch.long, device=device)
            w_off = torch.tensor([0], dtype=torch.long, device=device)
            b_idx = torch.tensor(bf, dtype=torch.long, device=device)
            b_off = torch.tensor([0], dtype=torch.long, device=device)
            stm_t = torch.tensor([stm], dtype=torch.float32, device=device)
            
            logit = model(w_idx, w_off, b_idx, b_off, stm_t).item()
            cp = logit * tau
            results[name] = round(cp, 1)
            
    return results
