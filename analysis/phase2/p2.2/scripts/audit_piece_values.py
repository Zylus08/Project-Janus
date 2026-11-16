#!/usr/bin/env python3
"""
audit_piece_values.py
Measures marginal value of each piece in Classical R1 vs NNUE H1.
"""

import ctypes
from pathlib import Path

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

def eval_f(fen):
    nb = NativeBoard()
    dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
    return dll.native_evaluate(ctypes.byref(nb)), dll.native_r1_evaluate_nnue(ctypes.byref(nb))

pieces_to_remove = [
    ("Queen d8", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Rook a8", "1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Rook h8", "rnbqkbn1/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Bishop c8", "rn1qkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Bishop f8", "rnbqk1nr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Knight b8", "r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Knight g8", "rnbqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Pawn e7", "rnbqkbnr/pppp1ppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
]

start_c, start_n = eval_f("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
print(f"Startpos: Classical={start_c}, NNUE={start_n}\n")
print(f"{'Missing Black Piece':20s} | {'Classical Margin':18s} | {'NNUE Margin':15s}")
print("-" * 60)
for name, fen in pieces_to_remove:
    c, n = eval_f(fen)
    c_diff = c - start_c
    n_diff = n - start_n
    print(f"{name:20s} | {c_diff:18d} | {n_diff:15d}")
