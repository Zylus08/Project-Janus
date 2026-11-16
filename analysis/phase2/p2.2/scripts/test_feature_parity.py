#!/usr/bin/env python3
"""
test_feature_parity.py
Compares Python training feature index mapping vs C++ inference feature index mapping
for all (piece, color, square) combinations.
"""

import sys
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from train_janus_nnue import PIECE_TO_INDEX_WHITE, PIECE_TO_INDEX_BLACK

mismatches = 0
for sq in range(64):
    for color in (chess.WHITE, chess.BLACK):
        for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING):
            cpp_piece = pt - 1
            cpp_color = 0 if color == chess.WHITE else 1
            
            cpp_w_idx = (cpp_color * 6 + cpp_piece) * 64 + sq
            cpp_b_idx = ((1 - cpp_color) * 6 + cpp_piece) * 64 + (sq ^ 56)
            
            py_w_idx = PIECE_TO_INDEX_WHITE[(pt, color)] * 64 + sq
            py_b_idx = PIECE_TO_INDEX_BLACK[(pt, color)] * 64 + (sq ^ 56)
            
            if cpp_w_idx != py_w_idx or cpp_b_idx != py_b_idx:
                print(f"Mismatch at sq={sq}, color={color}, pt={pt}: C++({cpp_w_idx}, {cpp_b_idx}) vs Py({py_w_idx}, {py_b_idx})")
                mismatches += 1

print(f"Total feature index mismatches across all 768 features: {mismatches}")
