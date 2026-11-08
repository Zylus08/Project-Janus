#!/usr/bin/env python3
"""Project Janus v0.64 - NNUE-V3 Quantization and Native Serialization.

Exports PyTorch checkpoint m2_v3_sef_best.pt to quantized binary .jnnue
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

ROOT = Path("E:/ChessXML/project-janus")
MODELS_DIR = ROOT / "analysis" / "v0.64" / "models"
RAW_DIR = ROOT / "analysis" / "v0.64" / "raw"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "analysis" / "v0.64" / "training"))
from train_v3_nnue import NNUEValueNetV3


def quantize_and_export_v3(
    checkpoint_path: Path,
    output_bin_path: Path,
    accum_dim: int = 128,
    sef_dim: int = 32,
    l1_dim: int = 32,
    eval_scale: float = 600.0,
) -> Dict[str, Any]:
    print(f"\nQuantizing NNUE-V3 model: {checkpoint_path.name} -> {output_bin_path.name}")

    model = NNUEValueNetV3(accum_dim=accum_dim, sef_dim=sef_dim, l1_dim=l1_dim, eval_scale=eval_scale)
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    ft_w = model.ft.weight.detach().numpy()    # [accum_dim, 768]
    ft_b = model.ft.bias.detach().numpy()      # [accum_dim]
    fc1_w = model.fc1.weight.detach().numpy()  # [l1_dim, 2 * accum_dim + sef_dim] = [32, 288]
    fc1_b = model.fc1.bias.detach().numpy()    # [l1_dim]
    fc2_w = model.fc2.weight.detach().numpy()  # [1, l1_dim]
    fc2_b = model.fc2.bias.detach().numpy()    # [1]

    # Scaling constants
    scale_accum = 128.0
    scale_l1 = 64.0
    scale_output = 64.0

    # 1. Feature Transformer: INT16
    ft_w_q = np.clip(np.round(ft_w * scale_accum), -32768, 32767).astype(np.int16)
    ft_b_q = np.clip(np.round(ft_b * scale_accum), -32768, 32767).astype(np.int16)
    ft_w_q_col = np.ascontiguousarray(ft_w_q.T) # [768, 128] for contiguous SIMD loading

    # 2. Dense Layer 1: INT8 weights, INT32 biases
    fc1_w_q = np.clip(np.round(fc1_w * scale_l1), -128, 127).astype(np.int8)
    fc1_b_q = np.round(fc1_b * scale_l1 * scale_accum).astype(np.int32)

    # 3. Dense Layer 2: INT8 weights, INT32 bias
    fc2_w_q = np.clip(np.round(fc2_w * scale_output), -128, 127).astype(np.int8)
    fc2_b_q = np.round(fc2_b * scale_output * scale_accum).astype(np.int32)

    # Payload
    payload = bytearray()
    payload.extend(ft_w_q_col.tobytes())
    payload.extend(ft_b_q.tobytes())
    payload.extend(fc1_w_q.tobytes())
    payload.extend(fc1_b_q.tobytes())
    payload.extend(fc2_w_q.tobytes())
    payload.extend(fc2_b_q.tobytes())

    crc32_val = zlib.crc32(payload)

    # 64-byte Header
    magic = 0x4A4E5533 # 'JNU3'
    version = 3
    arch_id = 3
    feature_dim = 768
    output_dim = 1
    eval_scale_int = int(eval_scale)
    reserved = b"\x00" * 24

    header = struct.pack(
        "<IIIIIIIIII24s",
        magic,
        version,
        arch_id,
        feature_dim,
        accum_dim,
        sef_dim,
        l1_dim,
        output_dim,
        eval_scale_int,
        crc32_val,
        reserved,
    )

    with open(output_bin_path, "wb") as f:
        f.write(header)
        f.write(payload)

    file_size = output_bin_path.stat().st_size
    print(f"Exported NNUE-V3 binary: {output_bin_path.name} ({file_size:,} bytes | CRC32: 0x{crc32_val:08X})")

    meta = {
        "model_file": output_bin_path.name,
        "size_bytes": file_size,
        "magic": "0x4A4E5533",
        "version": 3,
        "feature_dim": 768,
        "accum_dim": accum_dim,
        "sef_dim": sef_dim,
        "l1_dim": l1_dim,
        "scale_accum": int(scale_accum),
        "scale_l1": int(scale_l1),
        "scale_output": int(scale_output),
        "eval_scale": eval_scale_int,
        "crc32": f"0x{crc32_val:08X}",
    }
    with open(RAW_DIR / "jnnue_v3_manifest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta


if __name__ == "__main__":
    ckpt = MODELS_DIR / "m2_v3_sef_best.pt"
    out = MODELS_DIR / "janus_nnue_v3.jnnue"
    if ckpt.exists():
        quantize_and_export_v3(ckpt, out)
    else:
        print(f"Checkpoint {ckpt} does not exist yet. Run train_v3_nnue.py first.")

