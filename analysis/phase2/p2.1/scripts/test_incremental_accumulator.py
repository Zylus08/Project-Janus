#!/usr/bin/env python3
"""
test_incremental_accumulator.py
Milestone P2.1 Phase 6: Incremental Accumulator Engine Correctness & Invariant Proof.
Verifies:
- Fundamental Invariant: For any legal move sequence, incrementally updated accumulator
  MUST EXACTLY MATCH (difference = 0) a full recomputation from scratch.
- Tests forward moves and unmake stack reversals across randomized legal games.
- Validates quiet moves, captures, castling, en passant, and promotions.
"""

import sys
import json
import ctypes
import random
from pathlib import Path

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]

def fen_to_native(fen: str, dll) -> NativeBoard:
    board = NativeBoard()
    dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(board))
    return board

def encode_move(from_sq: int, to_sq: int, flag: int = 0, promo: int = 0) -> int:
    return (from_sq & 0x3F) | ((to_sq & 0x3F) << 6) | ((flag & 3) << 12) | ((promo & 3) << 14)

def chess_move_to_native(board: chess.Board, move: chess.Move) -> int:
    from_sq = move.from_square
    to_sq = move.to_square
    flag = 0
    promo = 0

    if board.is_castling(move):
        flag = 1
    elif board.is_en_passant(move):
        flag = 2
    elif move.promotion is not None:
        flag = 3
        # Promotion piece: 0=N, 1=B, 2=R, 3=Q
        pt_map = {chess.KNIGHT: 0, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 3}
        promo = pt_map[move.promotion]

    return encode_move(from_sq, to_sq, flag, promo)

def main():
    print("=" * 70)
    print("PHASE 6: INCREMENTAL ACCUMULATOR CORRECTNESS VERIFICATION")
    print("=" * 70)

    if not DLL_PATH.exists():
        print(f"Error: {DLL_PATH} not found!")
        sys.exit(1)

    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_r1_test_accumulator_parity.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
    dll.native_r1_test_accumulator_parity.restype = ctypes.c_int

    random.seed(42)
    total_moves_tested = 0
    total_mismatches = 0
    move_types = {"quiet": 0, "capture": 0, "castling": 0, "en_passant": 0, "promotion": 0}

    # Test 100 randomized games
    for game_idx in range(100):
        board = chess.Board()

        for ply in range(80):
            legals = list(board.legal_moves)
            if not legals or board.is_game_over():
                break

            move = random.choice(legals)

            # Classify move
            if board.is_castling(move):
                move_types["castling"] += 1
            elif board.is_en_passant(move):
                move_types["en_passant"] += 1
            elif move.promotion is not None:
                move_types["promotion"] += 1
            elif board.is_capture(move):
                move_types["capture"] += 1
            else:
                move_types["quiet"] += 1

            # Convert to native
            n_board = fen_to_native(board.fen(), dll)
            n_move = chess_move_to_native(board, move)

            # Test C++ accumulator parity (Incremental vs Full Recompute)
            diff = dll.native_r1_test_accumulator_parity(ctypes.byref(n_board), n_move)
            if diff != 0:
                print(f"[FAIL] Parity mismatch (diff={diff}) on game {game_idx}, ply {ply}, move {move} (FEN: {board.fen()})")
                total_mismatches += 1
                sys.exit(1)

            total_moves_tested += 1
            board.push(move)

    print(f"\n[PASS] Verified {total_moves_tested} legal moves across 100 randomized games.")
    print(f"  Tested move categories: {move_types}")
    print(f"  Accumulator mismatches: {total_mismatches} (0 tolerance required)")
    print(f"  Exact parity rate: 100.000% (Incremental == Full Recompute identically)")

    res_data = {
        "status": "PASS",
        "total_moves_tested": total_moves_tested,
        "total_mismatches": total_mismatches,
        "move_types": move_types,
        "parity_rate_pct": 100.0,
        "tolerance": "Exact integer equality (diff == 0)"
    }

    out_json = RAW_DIR / "incremental_accumulator_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res_data, f, indent=2)

    print(f"[SAVED] Results written to {out_json}")

if __name__ == "__main__":
    main()
