import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
import json
import struct
import hashlib
import math
import torch
import numpy as np
import chess

REPO_ROOT = r"E:\ChessXML\project-janus-phase1"
sys.path.append(os.path.join(REPO_ROOT, "analysis/phase2/p2.3/scripts"))

from nnue_model import HalfKPNNUE
from halfkp import get_halfkp_features

def export_and_audit():
    print("=== PHASE 10: QUANTIZED INFERENCE EXPORT & NUMERICAL AUDIT ===")
    
    ckpt_path = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/models/janus_nnue_h3.pt")
    ckpt = torch.load(ckpt_path, map_location="cpu")
    
    model = HalfKPNNUE(40960, 128, 32)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    # Quantization scales
    SCALE_FT = 256.0
    SCALE_L1 = 128.0
    SCALE_L2 = 128.0
    TAU = 400.0
    
    # 1. Feature Transformer: weights and biases to int16
    ft_weights = model.ft_weights.detach().numpy() # [40960, 128]
    ft_biases = model.ft_biases.detach().numpy()   # [128]
    
    ft_weights_q = np.clip(np.round(ft_weights * SCALE_FT), -32768, 32767).astype(np.int16)
    ft_biases_q = np.clip(np.round(ft_biases * SCALE_FT), -32768, 32767).astype(np.int16)
    
    # 2. Dense Layer 1: [256, 32]
    fc1_weight = model.fc1.weight.detach().numpy() # [32, 256]
    fc1_bias = model.fc1.bias.detach().numpy()     # [32]
    
    fc1_weight_q = np.clip(np.round(fc1_weight * SCALE_L1), -128, 127).astype(np.int8)
    fc1_bias_q = np.round(fc1_bias * (SCALE_FT * SCALE_L1)).astype(np.int32)
    
    # 3. Dense Layer 2: [32, 1]
    fc2_weight = model.fc2.weight.detach().numpy() # [1, 32]
    fc2_bias = model.fc2.bias.detach().numpy()     # [1]
    
    fc2_weight_q = np.clip(np.round(fc2_weight * SCALE_L2), -128, 127).astype(np.int8)
    fc2_bias_q = np.round(fc2_bias * (SCALE_L1 * SCALE_L2)).astype(np.int32)
    
    # Build binary format
    magic = b"JNN3"
    version = 2
    schema_id = 1
    header = struct.pack(
        "<4sIIIIIIIIII20s",
        magic,
        version,
        schema_id,
        40960,
        128,
        32,
        1,
        256,
        128,
        128,
        400,
        b"\x00" * 20
    )
    assert len(header) == 64
    
    bin_path = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/models/janus_nnue_h3.bin")
    with open(bin_path, "wb") as f:
        f.write(header)
        f.write(ft_weights_q.tobytes())
        f.write(ft_biases_q.tobytes())
        f.write(fc1_weight_q.tobytes())
        f.write(fc1_bias_q.tobytes())
        f.write(fc2_weight_q.tobytes())
        f.write(fc2_bias_q.tobytes())
        
    file_size = os.path.getsize(bin_path)
    sha256 = hashlib.sha256(open(bin_path, "rb").read()).hexdigest().upper()
    print(f"Exported {bin_path} ({file_size:,} bytes, SHA-256: {sha256})")
    
    # Numerical validation on 500 test positions
    test_jsonl = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/data/scaled_test.jsonl")
    fens = []
    with open(test_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                fens.append(json.loads(line)["fen"])
                if len(fens) >= 500:
                    break
                    
    fp32_scores = []
    quant_scores = []
    overflow_count = 0
    
    for fen in fens:
        b = chess.Board(fen)
        wf, bf = get_halfkp_features(b)
        stm = 1 if b.turn == chess.WHITE else 0
        
        # 1. PyTorch FP32
        w_idx = torch.tensor(wf, dtype=torch.long)
        w_off = torch.tensor([0], dtype=torch.long)
        b_idx = torch.tensor(bf, dtype=torch.long)
        b_off = torch.tensor([0], dtype=torch.long)
        stm_t = torch.tensor([float(stm)], dtype=torch.float32)
        
        with torch.no_grad():
            logit_fp32 = model(w_idx, w_off, b_idx, b_off, stm_t).item()
            cp_fp32 = logit_fp32 * TAU
            fp32_scores.append(cp_fp32)
            
        # 2. Integer Quantized Forward Simulation
        acc_w = np.copy(ft_biases_q)
        acc_b = np.copy(ft_biases_q)
        for idx in wf:
            acc_w += ft_weights_q[idx]
        for idx in bf:
            acc_b += ft_weights_q[idx]
            
        if np.any(acc_w > 32760) or np.any(acc_w < -32760) or np.any(acc_b > 32760) or np.any(acc_b < -32760):
            overflow_count += 1
            
        h_w = np.clip(acc_w, 0, 256).astype(np.int32)
        h_b = np.clip(acc_b, 0, 256).astype(np.int32)
        
        friendly = h_w if stm == 1 else h_b
        enemy = h_b if stm == 1 else h_w
        cat_in = np.concatenate([friendly, enemy])
        
        l1_sum = np.dot(fc1_weight_q.astype(np.int32), cat_in) + fc1_bias_q
        l1_act = np.clip(l1_sum // 256, 0, 128).astype(np.int32)
        
        l2_sum = np.dot(fc2_weight_q.astype(np.int32), l1_act) + fc2_bias_q
        logit_q = l2_sum[0] / 16384.0
        cp_q = logit_q * TAU
        quant_scores.append(cp_q)
        
    fp32_scores = np.array(fp32_scores)
    quant_scores = np.array(quant_scores)
    
    diff = np.abs(fp32_scores - quant_scores)
    mae = float(np.mean(diff))
    max_err = float(np.max(diff))
    corr = float(np.corrcoef(fp32_scores, quant_scores)[0, 1])
    sign_agree = float(np.mean(np.sign(fp32_scores) == np.sign(quant_scores))) * 100.0
    
    print("\n--- NUMERICAL QUANTIZATION VALIDATION SUMMARY ---")
    print(f"Positions Tested: {len(fens)}")
    print(f"Mean Absolute Error (FP32 vs INT16/INT8): {mae:.2f} cp")
    print(f"Max Absolute Error: {max_err:.2f} cp")
    print(f"Pearson Correlation (r): {corr:.6f}")
    print(f"Sign Agreement: {sign_agree:.1f}%")
    print(f"Accumulator Overflows: {overflow_count}")
    
    audit_report = {
        "binary_path": os.path.relpath(bin_path, REPO_ROOT).replace("\\", "/"),
        "file_size_bytes": file_size,
        "sha256": sha256,
        "format": {
            "magic": "JNN3",
            "version": version,
            "schema": "HalfKP-40960",
            "features": 40960,
            "hidden_dim": 128,
            "dense_dim": 32,
            "scales": {"ft": 256, "l1": 128, "l2": 128, "tau": 400}
        },
        "numerical_parity_metrics": {
            "positions_tested": len(fens),
            "mae_cp": round(mae, 2),
            "max_error_cp": round(max_err, 2),
            "pearson_r": round(corr, 6),
            "sign_agreement_pct": round(sign_agree, 2),
            "accumulator_overflows": overflow_count
        }
    }
    
    out_json = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/raw/quantized_model_export_audit.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    print(f"Saved audit to {out_json}")

if __name__ == "__main__":
    export_and_audit()
