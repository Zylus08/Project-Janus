#!/usr/bin/env python3
"""
audit_evaluation_signs.py
Tests sign orientation, magnitude, and perspective of Classical (R1), NNUE (H1), and Hybrid (H2)
across diagnostic material and positional imbalances.
"""

import ctypes
from pathlib import Path
import chess

dll_path = Path("E:/ChessXML/project-janus-phase1/analysis/phase2/p2.1/control/janus_hybrid_h1.dll")
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

def eval_fen(fen):
    nb = NativeBoard()
    dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
    c_score = dll.native_evaluate(ctypes.byref(nb))
    n_score = dll.native_r1_evaluate_nnue(ctypes.byref(nb))
    h_score = (c_score + n_score) // 2
    return c_score, n_score, h_score

test_fens = [
    ("Startpos (White to move)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Startpos (Black to move)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"),
    ("White +Q (White to move)", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("White +Q (Black to move)", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"),
    ("Black +Q (Black to move)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1"),
    ("Black +Q (White to move)", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1"),
    ("White +R (White to move)", "1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("White +R (Black to move)", "1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"),
    ("White +P (White to move)", "rnbqkbnr/1ppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("White +P (Black to move)", "rnbqkbnr/1ppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"),
    ("White Passed Pawn d7 (w)", "k7/3P4/8/8/8/8/8/K7 w - - 0 1"),
    ("White Passed Pawn d7 (b)", "k7/3P4/8/8/8/8/8/K7 b - - 0 1"),
    ("Black Passed Pawn d2 (b)", "k7/8/8/8/8/8/3p4/K7 b - - 0 1"),
    ("Black Passed Pawn d2 (w)", "k7/8/8/8/8/8/3p4/K7 w - - 0 1"),
]

print(f"{'Position':30s} | {'Classical R1':15s} | {'NNUE H1':15s} | {'Hybrid H2':15s}")
print("-" * 85)
for name, fen in test_fens:
    c_score, n_score, h_score = eval_fen(fen)
    print(f"{name:30s} | {c_score:15d} | {n_score:15d} | {h_score:15d}")
