#!/usr/bin/env python3
"""
benchmark_quality_atlas.py
Phase 4: Neural Evaluation Quality Atlas across 36 Diagnostic Benchmark Positions.
Compares:
- E0: Classical R1 Static Evaluation
- E1: H1 PyTorch FP32 Evaluation
- E2: H1 Quantized INT16/INT8 C++ Evaluation
- E3: H2 Hybrid 50/50 Evaluation
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

BENCHMARK_POSITIONS = [
    # Category 1: Material Imbalances
    ("Mat: White +Q", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Material", 850),
    ("Mat: Black +Q", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1", "Material", 850),
    ("Mat: White +R", "1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Material", 500),
    ("Mat: White +B", "rn1qkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Material", 325),
    ("Mat: White +N", "r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Material", 325),
    ("Mat: White +P", "rnbqkbnr/1ppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Material", 100),
    ("Mat: Exchange +R vs N", "r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RN1QKBNR w KQkq - 0 1", "Material", 175),

    # Category 2: Tactical Sacrifices & Attacks
    ("Tac: Scholar Mate in 1", "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1", "Tactical", 900),
    ("Tac: Back Rank Mate in 1", "6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1", "Tactical", 900),
    ("Tac: Queen Sac for Mate", "r5rk/5p1p/5R2/8/8/8/6QP/7K w - - 0 1", "Tactical", 800),

    # Category 3: Quiet Middlegames
    ("Mid: Startpos White", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Quiet Mid", 20),
    ("Mid: Startpos Black", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1", "Quiet Mid", -20),
    ("Mid: Open e-file Control", "r1bq1rk1/ppp2ppp/2np4/4p3/4P3/2NP1N2/PPP2PPP/R2Q1RK1 w - - 0 1", "Quiet Mid", 40),
    ("Mid: Symmetrical French", "rnbqk2r/ppp1bppp/4pn2/3p4/3P4/4PN2/PPP1BPPP/RNBQK2R w KQkq - 0 1", "Quiet Mid", 15),

    # Category 4: Pawn Structure
    ("Pawn: Passed d6 Pawn", "4k3/8/3P4/8/8/8/8/4K3 w - - 0 1", "Pawn Structure", 400),
    ("Pawn: Doubled c-Pawns (w)", "rnbqkbnr/pppppppp/8/8/8/2P5/PP1PPPPP/RNBQKBNR w KQkq - 0 1", "Pawn Structure", -20),
    ("Pawn: Isolated d-Pawn (w)", "r1bqk2r/pp2bppp/2n1pn2/3p4/3P4/2N1PN2/PP2BPPP/R1BQ1RK1 w kq - 0 1", "Pawn Structure", 10),
    ("Pawn: Connected Passed e5+f5", "4k3/8/8/4PP2/8/8/8/4K3 w - - 0 1", "Pawn Structure", 450),

    # Category 5: Passed-Pawn Races
    ("Race: White d7 1 ply promo", "k7/3P4/8/8/8/8/8/K7 w - - 0 1", "Pawn Race", 800),
    ("Race: Black d2 1 ply promo", "k7/8/8/8/8/8/3p4/K7 b - - 0 1", "Pawn Race", 800),
    ("Race: Outside Passed Pawn a5", "8/5k2/8/P7/8/8/5K2/8 w - - 0 1", "Pawn Race", 600),

    # Category 6: King Safety & Attacks
    ("King: Exposed Black King", "rnbq1rk1/pppppp1p/8/8/8/8/PPPPPPPP/RNBQKBNR w KQ - 0 1", "King Safety", 150),
    ("King: Completely Stripped King", "4k3/8/8/8/8/8/8/RNBQKBNR w KQ - 0 1", "King Safety", 900),
    ("King: Solid Fianchetto Shelter", "rnbqk1nr/ppppppbp/6p1/8/8/6P1/PPPPPPBP/RNBQK1NR w KQkq - 0 1", "King Safety", 10),

    # Category 7: Rook Activity & 7th Rank
    ("Rook: White Rook on 7th", "4k3/1R6/8/8/8/8/8/4K3 w - - 0 1", "Rook Activity", 250),
    ("Rook: Doubled Rooks on 7th", "4k3/1R1R4/8/8/8/8/8/4K3 w - - 0 1", "Rook Activity", 500),
    ("Rook: Passive 1st Rank Rook", "4k3/8/8/8/8/8/8/r3K3 w - - 0 1", "Rook Activity", -200),

    # Category 8: Minor Piece Outposts & Mobility
    ("Minor: Knight Outpost on d5", "r1bqkb1r/pppp1ppp/2n5/3N4/4n3/8/PPPP1PPP/R1BQKBNR w KQkq - 0 1", "Minor Piece", 120),
    ("Minor: Bad French Bishop c8", "r1bqk2r/pp1nbppp/2p1pn2/3p4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 1", "Minor Piece", 50),
    ("Minor: Bishop Pair Advantage", "r1bqk2r/pppp1ppp/2n2n2/4p3/1bB1P3/2NP1N2/PPP2PPP/R1BQK2R w KQkq - 0 1", "Minor Piece", 40),

    # Category 9: Endgame Opposition & Zugzwang
    ("End: Direct Opposition (w)", "8/8/4k3/8/4K3/8/8/8 w - - 0 1", "Endgame", 0),
    ("End: Direct Opposition (b)", "8/8/4k3/8/4K3/8/8/8 b - - 0 1", "Endgame", 0),
    ("End: Trebuchet Mutual Zugzwang", "8/8/1k6/1p1p4/1P1P4/1K6/8/8 w - - 0 1", "Endgame", 0),

    # Category 10: Drawn Positions
    ("Draw: King + Knight vs King", "4k3/8/8/8/8/5N2/8/4K3 w - - 0 1", "Drawn", 0),
    ("Draw: King + Bishop vs King", "4k3/8/8/8/8/5B2/8/4K3 w - - 0 1", "Drawn", 0),
    ("Draw: Opposite-Colored Bishops", "4k3/4b3/8/8/8/8/4B3/4K3 w - - 0 1", "Drawn", 0),
]

def main():
    print("=" * 105)
    print("PHASE 4: NEURAL EVALUATION QUALITY ATLAS BENCHMARK (36 POSITIONS)")
    print("=" * 105)
    print(f"{'Position Name':32s} | {'Cat':12s} | {'Truth':6s} | {'E0 (R1)':8s} | {'E1 (FP)':8s} | {'E2 (C++)':8s} | {'E3 (H2)':8s} | {'Delta E1-E2'}")
    print("-" * 105)

    records = []
    category_errors = {}

    for name, fen, cat, truth in BENCHMARK_POSITIONS:
        nb = NativeBoard()
        dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
        e0_r1 = dll.native_evaluate(ctypes.byref(nb))
        e2_cpp = dll.native_r1_evaluate_nnue(ctypes.byref(nb))
        e3_h2 = (e0_r1 + e2_cpp) // 2

        stm_f, ntm_f, stm = fen_to_features(fen)
        stm_t = torch.zeros(1, 768)
        ntm_t = torch.zeros(1, 768)
        stm_t[0, stm_f] = 1.0
        ntm_t[0, ntm_f] = 1.0
        with torch.no_grad():
            logit = model(stm_t, ntm_t).item()
        e1_fp = logit * (400.0 / math.log(10.0))

        diff_q = abs(e1_fp - e2_cpp)
        err_h1 = abs(e2_cpp - truth)

        if cat not in category_errors:
            category_errors[cat] = []
        category_errors[cat].append(err_h1)

        print(f"{name:32s} | {cat:12s} | {truth:6d} | {e0_r1:8d} | {e1_fp:8.1f} | {e2_cpp:8d} | {e3_h2:8d} | {diff_q:7.2f} cp")

        records.append({
            "name": name,
            "fen": fen,
            "category": cat,
            "truth": truth,
            "e0_classical_r1": e0_r1,
            "e1_pytorch_fp": round(e1_fp, 1),
            "e2_quantized_cpp": e2_cpp,
            "e3_hybrid_h2": e3_h2,
            "quant_diff": round(diff_q, 2),
            "h1_error": err_h1
        })

    # Summary by category
    print("\n" + "=" * 60)
    print("CATEGORY MEAN ABSOLUTE ERROR (MAE) vs GROUND TRUTH:")
    print("=" * 60)
    for cat, errs in category_errors.items():
        mae = sum(errs) / len(errs)
        print(f"  Category '{cat:16s}': MAE = {mae:6.1f} cp ({len(errs)} positions)")

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "evaluation_quality_atlas.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"\nAtlas raw report saved to: {out_file}")

if __name__ == "__main__":
    main()
