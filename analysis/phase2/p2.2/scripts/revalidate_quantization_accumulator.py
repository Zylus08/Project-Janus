#!/usr/bin/env python3
"""
revalidate_quantization_accumulator.py
Phase 7: Quantization Fidelity & Incremental Accumulator Invariant Revalidation.
Tests:
1. 500 Held-Out Positions: PyTorch FP32 vs Quantized INT16/INT8 C++ parity, correlation, MAE, max error.
2. Accumulator Invariant: 100 random games, checking exact integer parity (Delta = 0)
   across quiet moves, captures, castling, en passant, and promotions.
"""

import sys
import ctypes
import json
import math
import random
from pathlib import Path
import torch
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
TEST_JSONL = ROOT / "analysis" / "phase2" / "p2.1" / "data" / "janus_nnue_test.jsonl"
PT_PATH = ROOT / "analysis" / "phase2" / "p2.1" / "models" / "janus_nnue_h1_float.pt"
DLL_PATH = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.dll"

sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from train_janus_nnue import JanusNNUE, fen_to_features

# Load PyTorch model
model = JanusNNUE(feature_dim=768, accum_dim=128, hidden_dim=32)
checkpoint = torch.load(PT_PATH, map_location="cpu")
if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
    model.load_state_dict(checkpoint["model_state_dict"])
else:
    model.load_state_dict(checkpoint)
model.eval()

# Load C++ DLL
dll = ctypes.CDLL(str(DLL_PATH))

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupied", ctypes.c_uint64 * 2),
        ("all_occupied", ctypes.c_uint64),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_int8),
        ("halfmove_clock", ctypes.c_uint8),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
        ("pawn_key", ctypes.c_uint64),
    ]

dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
dll.native_set_fen.restype = ctypes.c_bool
dll.native_r1_evaluate_nnue.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_r1_evaluate_nnue.restype = ctypes.c_int
dll.native_r1_test_accumulator_parity.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
dll.native_r1_test_accumulator_parity.restype = ctypes.c_int
dll.native_parse_uci.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_char_p]
dll.native_parse_uci.restype = ctypes.c_uint16

def run_quantization_parity_test(n_samples=500):
    print("=" * 80)
    print("1. QUANTIZATION NUMERICAL PARITY (500 HELD-OUT TEST POSITIONS)")
    print("=" * 80)

    fens = []
    with open(TEST_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                fens.append(rec["fen"])
                if len(fens) >= n_samples:
                    break

    py_scores = []
    cpp_scores = []
    abs_errors = []
    sign_agreements = 0

    for fen in fens:
        # PyTorch FP32
        stm_f, ntm_f, stm = fen_to_features(fen)
        stm_t = torch.zeros(1, 768)
        ntm_t = torch.zeros(1, 768)
        stm_t[0, stm_f] = 1.0
        ntm_t[0, ntm_f] = 1.0
        with torch.no_grad():
            logit = model(stm_t, ntm_t).item()
        py_cp = logit * (400.0 / math.log(10.0))

        # Quantized C++
        nb = NativeBoard()
        dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
        cpp_cp = dll.native_r1_evaluate_nnue(ctypes.byref(nb))

        py_scores.append(py_cp)
        cpp_scores.append(cpp_cp)
        err = abs(py_cp - cpp_cp)
        abs_errors.append(err)

        if (py_cp >= 0 and cpp_cp >= 0) or (py_cp <= 0 and cpp_cp <= 0):
            sign_agreements += 1

    # Pearson correlation
    n = len(py_scores)
    mean_py = sum(py_scores) / n
    mean_cpp = sum(cpp_scores) / n
    cov = sum((p - mean_py) * (c - mean_cpp) for p, c in zip(py_scores, cpp_scores))
    var_py = sum((p - mean_py) ** 2 for p in py_scores)
    var_cpp = sum((c - mean_cpp) ** 2 for c in cpp_scores)
    r = cov / (math.sqrt(var_py) * math.sqrt(var_cpp)) if var_py > 0 and var_cpp > 0 else 1.0

    mae = sum(abs_errors) / n
    max_err = max(abs_errors)
    rmse = math.sqrt(sum(e**2 for e in abs_errors) / n)
    sign_acc = (sign_agreements / n) * 100.0

    print(f"  Positions Evaluated : {n}")
    print(f"  Pearson Correlation : {r:.6f}")
    print(f"  Mean Absolute Error : {mae:.2f} cp")
    print(f"  Max Absolute Error  : {max_err:.2f} cp")
    print(f"  Root Mean Sq Error  : {rmse:.2f} cp")
    print(f"  Sign Agreement      : {sign_acc:.1f}%")

    return {
        "positions_evaluated": n,
        "pearson_r": round(r, 6),
        "mae_cp": round(mae, 2),
        "max_err_cp": round(max_err, 2),
        "rmse_cp": round(rmse, 2),
        "sign_agreement_pct": round(sign_acc, 2)
    }

def run_accumulator_invariant_test(n_games=100):
    print("\n" + "=" * 80)
    print(f"2. INCREMENTAL ACCUMULATOR INVARIANT TEST ({n_games} RANDOM GAMES)")
    print("=" * 80)

    random.seed(42)
    total_moves_tested = 0
    parity_failures = 0
    move_type_counts = {"quiet": 0, "capture": 0, "castling": 0, "en_passant": 0, "promotion": 0}

    for g_idx in range(n_games):
        b = chess.Board()
        while not b.is_game_over() and len(b.move_stack) < 150:
            legal = list(b.legal_moves)
            if not legal:
                break
            mv = random.choice(legal)

            # Classify move type
            is_cap = b.is_capture(mv)
            is_castling = b.is_castling(mv)
            is_ep = b.is_en_passant(mv)
            is_promo = (mv.promotion is not None)

            if is_promo: move_type_counts["promotion"] += 1
            elif is_castling: move_type_counts["castling"] += 1
            elif is_ep: move_type_counts["en_passant"] += 1
            elif is_cap: move_type_counts["capture"] += 1
            else: move_type_counts["quiet"] += 1

            # Test accumulator parity in C++ DLL
            nb = NativeBoard()
            dll.native_set_fen(b.fen().encode("ascii"), ctypes.byref(nb))
            m_native = dll.native_parse_uci(ctypes.byref(nb), mv.uci().encode("ascii"))

            diff = dll.native_r1_test_accumulator_parity(ctypes.byref(nb), m_native)
            if diff != 0:
                print(f"Discrepancy on move {mv.uci()} (diff={diff}) in fen: {b.fen()}")
                parity_failures += 1

            total_moves_tested += 1
            b.push(mv)

    exact_parity_pct = ((total_moves_tested - parity_failures) / total_moves_tested * 100.0) if total_moves_tested > 0 else 0.0

    print(f"  Total Legal Moves Tested     : {total_moves_tested:,}")
    print(f"  Exact Parity (Delta = 0)     : {total_moves_tested - parity_failures:,} ({exact_parity_pct:.3f}%)")
    print(f"  Parity Discrepancies         : {parity_failures}")
    print(f"  Tested Move Categories       : {move_type_counts}")

    return {
        "total_moves_tested": total_moves_tested,
        "parity_failures": parity_failures,
        "exact_parity_pct": round(exact_parity_pct, 3),
        "move_types": move_type_counts
    }

def main():
    quant_res = run_quantization_parity_test(500)
    accum_res = run_accumulator_invariant_test(100)

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "quantization_and_accumulator_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "quantization_parity": quant_res,
            "accumulator_invariants": accum_res
        }, f, indent=2)
    print(f"\nAudit results saved to: {out_file}")

if __name__ == "__main__":
    main()
