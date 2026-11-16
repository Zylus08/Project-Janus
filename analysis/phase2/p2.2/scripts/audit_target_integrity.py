#!/usr/bin/env python3
"""
audit_target_integrity.py
Phase 2: Label Perspective & Target Integrity Audit.
Compares:
1. Ground Truth Chess Expectation
2. PyTorch FP32 Model Output
3. Quantized C++ Output
4. R1 Search Interpretation
Across the 10 mandatory diagnostic positions.
"""

import sys
import ctypes
import json
import math
from pathlib import Path
import torch
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from train_janus_nnue import JanusNNUE, fen_to_features

# Load PyTorch model
pt_path = ROOT / "analysis" / "phase2" / "p2.1" / "models" / "janus_nnue_h1_float.pt"
model = JanusNNUE(feature_dim=768, accum_dim=128, hidden_dim=32)
checkpoint = torch.load(pt_path, map_location="cpu")
if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
    model.load_state_dict(checkpoint["model_state_dict"])
else:
    model.load_state_dict(checkpoint)
model.eval()

# Load C++ DLL
dll_path = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.dll"
dll = ctypes.CDLL(str(dll_path))

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
dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_evaluate.restype = ctypes.c_int
dll.native_r1_evaluate_nnue.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_r1_evaluate_nnue.restype = ctypes.c_int

MANDATORY_CASES = [
    # 1. White Queen advantage (White to move)
    ("1. White Queen Advantage (w to move)", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Win for STM (White)", "> 0"),
    # 2. White Queen advantage (Black to move)
    ("2. White Queen Advantage (b to move)", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1", "Loss for STM (Black)", "< 0"),
    # 3. Black Queen advantage (Black to move)
    ("3. Black Queen Advantage (b to move)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1", "Win for STM (Black)", "> 0"),
    # 4. Black Queen advantage (White to move)
    ("4. Black Queen Advantage (w to move)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1", "Loss for STM (White)", "< 0"),
    # 5. White passed-pawn advantage (White to move)
    ("5. White Passed Pawn d7 (w to move)", "k7/3P4/8/8/8/8/8/K7 w - - 0 1", "Win for STM (White)", "> 0"),
    # 6. Black passed-pawn advantage (Black to move)
    ("6. Black Passed Pawn d2 (b to move)", "k7/8/8/8/8/8/3p4/K7 b - - 0 1", "Win for STM (Black)", "> 0"),
    # 7. Forced mate for White (White delivers mate)
    ("7. Forced Mate for White (w to move)", "6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1", "Mate for STM (White)", ">> 0"),
    # 8. Forced mate for Black (White is mated)
    ("8. Forced Mate for White (b to move)", "4r1k1/8/8/8/8/8/5PPP/6K1 b - - 0 1", "Mate for STM (Black)", ">> 0"),
    # 9. Drawn equal-material endgame
    ("9. Drawn Equal Endgame", "8/8/4k3/8/8/4K3/8/8 w - - 0 1", "Draw (Equal)", "~ 0"),
    # 10. Stalemate position
    ("10. Stalemate Position (b to move)", "k7/2Q5/1K6/8/8/8/8/8 b - - 0 1", "Stalemate (Draw)", "0"),
]

def audit_cases():
    print("=" * 95)
    print("PHASE 2: NEURAL LABEL & SCORE PERSPECTIVE AUDIT ACROSS MANDATORY CASES")
    print("=" * 95)
    print(f"{'Case Description':36s} | {'Classical':10s} | {'PyTorch cp':10s} | {'Quant C++':10s} | {'Expected Sign'}")
    print("-" * 95)

    audit_records = []

    for name, fen, exp_desc, exp_sign in MANDATORY_CASES:
        # Classical R1
        nb = NativeBoard()
        dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
        c_score = dll.native_evaluate(ctypes.byref(nb))

        # Quantized C++ NNUE
        n_cpp_score = dll.native_r1_evaluate_nnue(ctypes.byref(nb))

        # PyTorch Float
        stm_f, ntm_f, stm = fen_to_features(fen)
        stm_t = torch.zeros(1, 768)
        ntm_t = torch.zeros(1, 768)
        stm_t[0, stm_f] = 1.0
        ntm_t[0, ntm_f] = 1.0
        with torch.no_grad():
            logit = model(stm_t, ntm_t).item()
        py_cp = logit * (400.0 / math.log(10.0))

        # Check sign correctness
        sign_correct = True
        if "> 0" in exp_sign and n_cpp_score <= 0: sign_correct = False
        if "< 0" in exp_sign and n_cpp_score >= 0: sign_correct = False

        print(f"{name:36s} | {c_score:10d} | {py_cp:10.1f} | {n_cpp_score:10d} | {exp_sign:10s} (Correct: {sign_correct})")

        audit_records.append({
            "name": name,
            "fen": fen,
            "expected_desc": exp_desc,
            "expected_sign": exp_sign,
            "classical_r1": c_score,
            "pytorch_cp": round(py_cp, 1),
            "quantized_cpp": n_cpp_score,
            "sign_correct": sign_correct
        })

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "target_integrity_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_records, f, indent=2)

    print(f"\nRaw target audit saved to: {out_file}")

if __name__ == "__main__":
    audit_cases()
