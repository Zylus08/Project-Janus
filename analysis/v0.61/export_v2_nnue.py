#!/usr/bin/env python3
"""Project Janus v0.61 - NNUE-V2 Model Quantization & Native Serialization.

Exports PyTorch checkpoints to production-ready quantized `.jnnue` binary models
for high-performance C++17 and AVX2 native inference.
"""

from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "analysis" / "v0.61" / "models"
RAW_DIR = ROOT / "analysis" / "v0.61" / "raw"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_v2_nnue import NNUEValueNet


def quantize_and_export_v2(
    checkpoint_path: Path,
    output_bin_path: Path,
    arch_id: int,
    feature_dim: int,
    accum_dim: int,
    l1_dim: int,
    eval_scale: float = 600.0,
) -> Dict[str, Any]:
    print(f"\nQuantizing model: {checkpoint_path.name} -> {output_bin_path.name}")

    model = NNUEValueNet(feature_dim, accum_dim, l1_dim, eval_scale)
    state = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()

    ft_w = model.ft.weight.detach().numpy() # [accum_dim, feature_dim]
    ft_b = model.ft.bias.detach().numpy()   # [accum_dim]
    fc1_w = model.fc1.weight.detach().numpy() # [l1_dim, 2 * accum_dim]
    fc1_b = model.fc1.bias.detach().numpy()   # [l1_dim]
    fc2_w = model.fc2.weight.detach().numpy() # [1, l1_dim]
    fc2_b = model.fc2.bias.detach().numpy()   # [1]

    # Scaling constants
    scale_accum = 128.0
    scale_l1 = 64.0
    scale_output = 64.0

    # 1. Feature Transformer: INT16
    ft_w_q = np.clip(np.round(ft_w * scale_accum), -32768, 32767).astype(np.int16)
    ft_b_q = np.clip(np.round(ft_b * scale_accum), -32768, 32767).astype(np.int16)
    # Store in column-major [feature_dim, accum_dim] for sequential AVX2 SIMD loads
    ft_w_q_col = np.ascontiguousarray(ft_w_q.T)

    # 2. Dense Layer 1: INT8 weights, INT32 biases
    fc1_w_q = np.clip(np.round(fc1_w * scale_l1), -128, 127).astype(np.int8)
    fc1_b_q = np.round(fc1_b * scale_l1 * scale_accum).astype(np.int32)

    # 3. Dense Layer 2: INT8 weights, INT32 bias
    fc2_w_q = np.clip(np.round(fc2_w * scale_output), -128, 127).astype(np.int8)
    fc2_b_q = np.round(fc2_b * scale_output * scale_accum).astype(np.int32)

    # Assemble raw tensor payload
    payload = bytearray()
    payload.extend(ft_w_q_col.tobytes())
    payload.extend(ft_b_q.tobytes())
    payload.extend(fc1_w_q.tobytes())
    payload.extend(fc1_b_q.tobytes())
    payload.extend(fc2_w_q.tobytes())
    payload.extend(fc2_b_q.tobytes())

    crc32_val = zlib.crc32(payload)

    # 64-byte Header
    magic = 0x4A4E5545 # 'JNUE'
    version = 2        # Version 2
    output_dim = 1
    eval_scale_int = int(eval_scale)
    reserved = b"\x00" * 16

    header = struct.pack(
        "<IIIIIIIIIIII16s",
        magic,
        version,
        arch_id,
        feature_dim,
        accum_dim,
        l1_dim,
        output_dim,
        int(scale_accum),
        int(scale_l1),
        int(scale_output),
        eval_scale_int,
        crc32_val,
        reserved,
    )
    assert len(header) == 64

    with open(output_bin_path, "wb") as f:
        f.write(header)
        f.write(payload)

    file_size = output_bin_path.stat().st_size
    print(f"  Wrote {file_size:,} bytes to {output_bin_path.name}")
    print(f"  CRC32 Checksum: {crc32_val:#010x}")

    return {
        "output_path": str(output_bin_path),
        "file_size_bytes": file_size,
        "crc32": f"{crc32_val:#010x}",
        "arch_id": arch_id,
        "feature_dim": feature_dim,
        "accum_dim": accum_dim,
        "l1_dim": l1_dim,
        "total_weights_bytes": len(payload),
    }


def verify_quantized_parity(
    model_pt_path: Path,
    model_bin_path: Path,
    test_ds_samples: List[Dict[str, Any]],
    feature_dim: int,
    accum_dim: int,
    l1_dim: int,
) -> Dict[str, Any]:
    """Computes exact parity between PyTorch FP32 and Quantized Integer Inference."""
    print(f"\nAuditing Quantization Parity: {model_bin_path.name} across {len(test_ds_samples):,} test positions...")

    # Load PyTorch model
    model = NNUEValueNet(feature_dim, accum_dim, l1_dim, 600.0)
    model.load_state_dict(torch.load(model_pt_path, map_location="cpu"))
    model.eval()

    # Load Quantized Binary
    with open(model_bin_path, "rb") as f:
        raw = f.read()
    hdr = raw[:64]
    payload = raw[64:]

    offset = 0
    ft_w_bytes = feature_dim * accum_dim * 2
    ft_w = np.frombuffer(payload[offset:offset+ft_w_bytes], dtype=np.int16).reshape(feature_dim, accum_dim)
    offset += ft_w_bytes

    ft_b_bytes = accum_dim * 2
    ft_b = np.frombuffer(payload[offset:offset+ft_b_bytes], dtype=np.int16)
    offset += ft_b_bytes

    fc1_w_bytes = l1_dim * (2 * accum_dim)
    fc1_w = np.frombuffer(payload[offset:offset+fc1_w_bytes], dtype=np.int8).reshape(l1_dim, 2 * accum_dim)
    offset += fc1_w_bytes

    fc1_b_bytes = l1_dim * 4
    fc1_b = np.frombuffer(payload[offset:offset+fc1_b_bytes], dtype=np.int32)
    offset += fc1_b_bytes

    fc2_w_bytes = l1_dim
    fc2_w = np.frombuffer(payload[offset:offset+fc2_w_bytes], dtype=np.int8)
    offset += fc2_w_bytes

    fc2_b = np.frombuffer(payload[offset:offset+4], dtype=np.int32)[0]

    fp32_scores = []
    quant_scores = []
    errors = []

    for item in test_ds_samples:
        stm_feats = item["stm_feats"]
        opp_feats = item["opp_feats"]

        # 1. PyTorch FP32
        stm_t = torch.zeros(1, 768)
        opp_t = torch.zeros(1, 768)
        stm_t[0, stm_feats] = 1.0
        opp_t[0, opp_feats] = 1.0
        with torch.no_grad():
            fp32_val = float(model(stm_t, opp_t).item())

        # 2. Integer Inference
        acc_stm = np.copy(ft_b)
        for f in stm_feats:
            acc_stm += ft_w[f]
        acc_opp = np.copy(ft_b)
        for f in opp_feats:
            acc_opp += ft_w[f]

        # Clipped ReLU [0, 127]
        act_stm = np.clip(acc_stm, 0, 127).astype(np.uint8)
        act_opp = np.clip(acc_opp, 0, 127).astype(np.uint8)
        dual_act = np.concatenate([act_stm, act_opp]).astype(np.int32)

        # L1: int32 dot product + int32 bias
        l1_sum = np.dot(fc1_w.astype(np.int32), dual_act) + fc1_b
        # L1 Activation: right shift by 6 (divide by 64.0) and clamp to [0, 127]
        l1_act = np.clip(l1_sum >> 6, 0, 127).astype(np.int32)

        # L2: int32 dot product + int32 bias
        l2_sum = np.dot(fc2_w.astype(np.int32), l1_act) + fc2_b

        # Output Centipawns: (l2_sum * 600) / 8192
        quant_val = int((int(l2_sum) * 600) // 8192)

        fp32_scores.append(fp32_val)
        quant_scores.append(quant_val)
        errors.append(abs(fp32_val - quant_val))

    errors_arr = np.array(errors)
    mae = float(np.mean(errors_arr))
    p95 = float(np.percentile(errors_arr, 95))
    max_err = float(np.max(errors_arr))
    r = float(np.corrcoef(fp32_scores, quant_scores)[0, 1])

    fp32_arr = np.array(fp32_scores)
    quant_arr = np.array(quant_scores)
    sign_agree = float(np.mean((fp32_arr > 0) == (quant_arr > 0)) * 100)

    print(f"Quantization Parity Results ({model_bin_path.name}):")
    print(f"  MAE (FP32 vs INT):     {mae:.2f} cp")
    print(f"  P95 Error:             {p95:.2f} cp")
    print(f"  Max Error:             {max_err:.2f} cp")
    print(f"  Pearson Correlation:   {r:.6f}")
    print(f"  Sign Agreement:        {sign_agree:.2f}%")

    return {
        "mae_cp": mae,
        "p95_cp": p95,
        "max_error_cp": max_err,
        "pearson_r": r,
        "sign_agreement_pct": sign_agree,
    }


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Export V2-Small (Arch ID 1, M=64)
    v2_small_pt = MODELS_DIR / "v2_small_best.pt"
    v2_small_bin = MODELS_DIR / "janus_nnue_v2_small.jnnue"
    meta_small = quantize_and_export_v2(
        v2_small_pt, v2_small_bin, arch_id=1, feature_dim=768, accum_dim=64, l1_dim=16
    )

    # 2. Export V2-Compact (Arch ID 2, M=128)
    v2_compact_pt = MODELS_DIR / "v2_compact_best.pt"
    v2_compact_bin = MODELS_DIR / "janus_nnue_v2_compact.jnnue"
    meta_compact = quantize_and_export_v2(
        v2_compact_pt, v2_compact_bin, arch_id=2, feature_dim=768, accum_dim=128, l1_dim=32
    )

    # 3. Parity Audit on Test Samples
    test_json = ROOT / "analysis" / "v0.61" / "dataset" / "value_v2_test.json"
    from train_v2_nnue import ChessValueDataset
    test_ds = ChessValueDataset(test_json, max_samples=1000)

    parity_small = verify_quantized_parity(
        v2_small_pt, v2_small_bin, test_ds.samples, 768, 64, 16
    )
    parity_compact = verify_quantized_parity(
        v2_compact_pt, v2_compact_bin, test_ds.samples, 768, 128, 32
    )

    audit_report = {
        "v2_small": {
            "metadata": meta_small,
            "parity": parity_small,
        },
        "v2_compact": {
            "metadata": meta_compact,
            "parity": parity_compact,
        },
    }

    audit_path = RAW_DIR / "quantization_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    print(f"\nSaved quantization audit report to {audit_path}")


if __name__ == "__main__":
    main()
