"""Project Janus v0.60 - NNUE Model Quantization & Binary Serialization Pipeline.

Converts PyTorch FP32 checkpoints into production-ready quantized `.jnnue` binary models
for high-performance C++17 native inference.

Integer Scaling:
- Feature Transformer: Weights round(W * 128.0) int16, Biases round(b * 128.0) int16
  -> Accumulator clamp(acc, 0, 127) uint8 (ZERO division, single clamp)
- Dense Layer 1: Weights round(W1 * 64.0) int8, Biases round(b1 * 64.0 * 128.0) int32
  -> Activation clamp(sum1 / 64, 0, 127) uint8 (right shift >> 6)
- Dense Layer 2: Weights round(W2 * 64.0) int8, Bias round(b2 * 64.0 * 128.0) int32
  -> Output Centipawns: (sum2 * eval_scale) / (64 * 128)
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Dict

import chess
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_nnue import NNUEValueNet, extract_features_v1_small, extract_features_v1_compact

MODELS_DIR = ROOT / "analysis" / "v0.60" / "models"


def quantize_and_export(
    checkpoint_path: Path,
    output_bin_path: Path,
    arch_id: int,
    feature_dim: int,
    accum_dim: int,
    l1_dim: int,
    eval_scale: float = 600.0,
) -> Dict[str, Any]:
    """Quantizes PyTorch FP32 model and writes `.jnnue` binary."""
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

    # Quantization scales
    scale_accum = 128.0
    scale_l1 = 64.0
    scale_output = 64.0

    # 1. Feature Transformer: int16
    ft_w_q = np.clip(np.round(ft_w * scale_accum), -32768, 32767).astype(np.int16)
    ft_b_q = np.clip(np.round(ft_b * scale_accum), -32768, 32767).astype(np.int16)
    ft_w_q_col = np.ascontiguousarray(ft_w_q.T) # [feature_dim, accum_dim]

    # 2. Dense Layer 1: int8 weights, int32 biases (scaled by scale_l1 * scale_accum)
    fc1_w_q = np.clip(np.round(fc1_w * scale_l1), -128, 127).astype(np.int8)
    fc1_b_q = np.round(fc1_b * scale_l1 * scale_accum).astype(np.int32)

    # 3. Dense Layer 2: int8 weights, int32 biases (scaled by scale_output * scale_accum)
    fc2_w_q = np.clip(np.round(fc2_w * scale_output), -128, 127).astype(np.int8)
    fc2_b_q = np.round(fc2_b * scale_output * scale_accum).astype(np.int32)

    # Pack raw tensor bytes
    payload_bytes = bytearray()
    payload_bytes.extend(ft_w_q_col.tobytes())
    payload_bytes.extend(ft_b_q.tobytes())
    payload_bytes.extend(fc1_w_q.tobytes())
    payload_bytes.extend(fc1_b_q.tobytes())
    payload_bytes.extend(fc2_w_q.tobytes())
    payload_bytes.extend(fc2_b_q.tobytes())

    crc32_val = zlib.crc32(payload_bytes)

    # 64-byte Header
    magic = 0x4A4E5545 # 'JNUE'
    version = 1
    output_dim = 1
    eval_scale_int = int(eval_scale)
    reserved = b"\x00" * 16

    header_bytes = struct.pack(
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

    assert len(header_bytes) == 64

    with open(output_bin_path, "wb") as f:
        f.write(header_bytes)
        f.write(payload_bytes)

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
    }


def simulate_quantized_inference(
    bin_path: Path, board: chess.Board, arch_id: int
) -> int:
    """Performs exact bit-level emulation of native C++ integer inference."""
    with open(bin_path, "rb") as f:
        header_data = f.read(64)
        magic, ver, a_id, f_dim, m_dim, l1_dim, out_dim, s_acc, s_l1, s_out, e_scale, crc, _ = struct.unpack(
            "<IIIIIIIIIIII16s", header_data
        )

        ft_w = np.frombuffer(f.read(f_dim * m_dim * 2), dtype=np.int16).reshape((f_dim, m_dim))
        ft_b = np.frombuffer(f.read(m_dim * 2), dtype=np.int16)
        fc1_w = np.frombuffer(f.read(l1_dim * 2 * m_dim), dtype=np.int8).reshape((l1_dim, 2 * m_dim))
        fc1_b = np.frombuffer(f.read(l1_dim * 4), dtype=np.int32)
        fc2_w = np.frombuffer(f.read(1 * l1_dim), dtype=np.int8).reshape((1, l1_dim))
        fc2_b = np.frombuffer(f.read(4), dtype=np.int32)

    if a_id == 1:
        ft_w_idx, ft_b_idx = extract_features_v1_small(board)
    else:
        ft_w_idx, ft_b_idx = extract_features_v1_compact(board)

    is_white_stm = (board.turn == chess.WHITE)
    stm_idx = ft_w_idx if is_white_stm else ft_b_idx
    nstm_idx = ft_b_idx if is_white_stm else ft_w_idx

    acc_stm = np.copy(ft_b)
    for idx in stm_idx:
        acc_stm += ft_w[idx]

    acc_nstm = np.copy(ft_b)
    for idx in nstm_idx:
        acc_nstm += ft_w[idx]

    act_stm = np.clip(acc_stm, 0, 127).astype(np.int32)
    act_nstm = np.clip(acc_nstm, 0, 127).astype(np.int32)
    h0 = np.concatenate([act_stm, act_nstm])

    sum1 = fc1_b + np.dot(fc1_w.astype(np.int32), h0)
    act1 = np.clip(sum1 // s_l1, 0, 127).astype(np.int32)

    sum2 = fc2_b[0] + np.dot(fc2_w[0].astype(np.int32), act1)
    score_cp = int((sum2 * e_scale) // (s_out * s_acc))
    return score_cp


if __name__ == "__main__":
    v1_small_pt = MODELS_DIR / "v1_small_best.pt"
    if v1_small_pt.exists():
        quantize_and_export(
            v1_small_pt,
            MODELS_DIR / "janus_nnue_v1_small.jnnue",
            arch_id=1,
            feature_dim=768,
            accum_dim=64,
            l1_dim=16,
        )

    v1_compact_pt = MODELS_DIR / "v1_compact_best.pt"
    if v1_compact_pt.exists():
        quantize_and_export(
            v1_compact_pt,
            MODELS_DIR / "janus_nnue_v1_compact.jnnue",
            arch_id=2,
            feature_dim=3072,
            accum_dim=128,
            l1_dim=32,
        )
