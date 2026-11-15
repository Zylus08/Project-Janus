#!/usr/bin/env python3
"""
test_correctness_and_referee.py
Milestone P1.21 Phase 11: Correctness & Harness Qualification.

Tests:
1. Standard Perft Suite against ground-truth references:
   - Startpos (depths 1..5)
   - Kiwipete (depths 1..4)
   - Silver Suite (depths 1..5)
   - Position 4 (depths 1..4)
   - Position 5 (depths 1..4)
2. 15-case referee integrity suite:
   - Insufficient material (bare kings, K+N vs K, K+B vs K, K+NN vs K, K+P vs K)
   - 50-move and 75-move rules
   - Threefold and fivefold repetitions
   - Stalemate vs Checkmate detection
   - Castling rights invalidation
   - En passant legality and board state update
   - Promotion piece types
"""

import os
import sys
import json
import time
import ctypes
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "correctness_harness_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

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

class UndoInfo(ctypes.Structure):
    _fields_ = [
        ("captured_piece", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]

def load_bridge():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init.restype = ctypes.c_int
    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int
    dll.native_perft.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
    dll.native_perft.restype = ctypes.c_uint64
    dll.native_is_check.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_is_check.restype = ctypes.c_int
    dll.native_is_insufficient_material.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_is_insufficient_material.restype = ctypes.c_int
    dll.native_can_claim_fifty_moves.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_can_claim_fifty_moves.restype = ctypes.c_int
    dll.native_is_seventyfive_moves.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_is_seventyfive_moves.restype = ctypes.c_int
    dll.native_can_claim_threefold_repetition.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_can_claim_threefold_repetition.restype = ctypes.c_int
    dll.native_is_fivefold_repetition.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_is_fivefold_repetition.restype = ctypes.c_int
    dll.native_generate_legal_moves.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    dll.native_generate_legal_moves.restype = ctypes.c_int
    dll.native_make_move.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.POINTER(UndoInfo)]
    dll.native_make_move.restype = ctypes.c_int
    dll.native_unmake_move.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.POINTER(UndoInfo)]
    dll.native_unmake_move.restype = None
    dll.native_reset_history.restype = None
    dll.native_push_history.argtypes = [ctypes.c_uint64]
    dll.native_push_history.restype = None
    dll.native_init()
    return dll

PERFT_SUITE = [
    {
        "id": "PERFT_01_STARTPOS",
        "name": "Standard Startpos",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "expected": {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609}
    },
    {
        "id": "PERFT_02_KIWIPETE",
        "name": "Kiwipete Complex",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "expected": {1: 48, 2: 2039, 3: 97862, 4: 4085603}
    },
    {
        "id": "PERFT_03_SILVER",
        "name": "Silver Suite King Walks",
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "expected": {1: 14, 2: 191, 3: 2812, 4: 43238, 5: 674624}
    },
    {
        "id": "PERFT_04_POS4",
        "name": "Position 4 Promotions",
        "fen": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "expected": {1: 6, 2: 264, 3: 9467, 4: 422333}
    },
    {
        "id": "PERFT_05_POS5",
        "name": "Position 5 King Defense Checks",
        "fen": "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "expected": {1: 44, 2: 1486, 3: 62379, 4: 2103487}
    }
]

def run_perft_suite(dll):
    print("\n--- Running Perft Correctness Suite ---")
    board = NativeBoard()
    results = []
    total_expected = 0
    total_actual = 0
    all_passed = True
    
    for item in PERFT_SUITE:
        pid = item["id"]
        pname = item["name"]
        fen = item["fen"]
        exp = item["expected"]
        print(f"\n[{pid}] {pname}")
        
        pos_entry = {"id": pid, "name": pname, "fen": fen, "depths": []}
        
        for depth, exp_nodes in exp.items():
            dll.native_set_fen(fen.encode("ascii"), ctypes.byref(board))
            t0 = time.perf_counter()
            actual = dll.native_perft(ctypes.byref(board), depth)
            t1 = time.perf_counter()
            sec = max(t1 - t0, 1e-6)
            nps = int(actual / sec)
            
            passed = (actual == exp_nodes)
            if not passed:
                all_passed = False
            total_expected += exp_nodes
            total_actual += actual
            
            status = "PASS" if passed else f"FAIL (exp {exp_nodes:,})"
            print(f"  Depth {depth}: nodes={actual:,} ({status}) in {sec:.4f}s ({nps:,} NPS)")
            
            pos_entry["depths"].append({
                "depth": depth,
                "expected": exp_nodes,
                "actual": actual,
                "passed": passed,
                "elapsed_sec": round(sec, 5),
                "nps": nps
            })
        results.append(pos_entry)
        
    return {
        "all_passed": all_passed,
        "positions": results
    }

def run_referee_suite(dll):
    print("\n--- Running 15-Case Referee Integrity Suite ---")
    board = NativeBoard()
    moves_buf = (ctypes.c_uint16 * 256)()
    cases = []
    
    def test_case(cid, name, passed, details):
        status = "PASS" if passed else "FAIL"
        print(f"  [{cid}] {name:<42} : {status} ({details})")
        cases.append({"id": cid, "name": name, "passed": passed, "details": details})
        return passed
        
    all_pass = True
    
    # REF_01: Insufficient material - Bare Kings
    dll.native_set_fen(b"8/8/4k3/8/8/4K3/8/8 w - - 0 1", ctypes.byref(board))
    pass_01 = (dll.native_is_insufficient_material(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_01", "Bare Kings (K vs K)", pass_01, "Expected insufficient=1")
    
    # REF_02: Insufficient material - King + Knight vs King
    dll.native_set_fen(b"8/8/4k3/8/5N2/4K3/8/8 w - - 0 1", ctypes.byref(board))
    pass_02 = (dll.native_is_insufficient_material(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_02", "Minor Piece (K+N vs K)", pass_02, "Expected insufficient=1")
    
    # REF_03: Insufficient material - King + Bishop vs King
    dll.native_set_fen(b"8/8/4k3/8/5B2/4K3/8/8 w - - 0 1", ctypes.byref(board))
    pass_03 = (dll.native_is_insufficient_material(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_03", "Minor Piece (K+B vs K)", pass_03, "Expected insufficient=1")
    
    # REF_04: Sufficient material - King + 2 Knights vs King
    dll.native_set_fen(b"8/8/4k3/8/5N2/4K1N1/8/8 w - - 0 1", ctypes.byref(board))
    pass_04 = (dll.native_is_insufficient_material(ctypes.byref(board)) == 0)
    all_pass &= test_case("REF_04", "Two Knights (K+NN vs K)", pass_04, "Expected insufficient=0 (mating material exists)")
    
    # REF_05: Sufficient material - King + Pawn vs King
    dll.native_set_fen(b"8/8/4k3/8/4P3/4K3/8/8 w - - 0 1", ctypes.byref(board))
    pass_05 = (dll.native_is_insufficient_material(ctypes.byref(board)) == 0)
    all_pass &= test_case("REF_05", "Pawn Endgame (K+P vs K)", pass_05, "Expected insufficient=0")
    
    # REF_06: 50-move rule claimable at halfmove >= 100
    dll.native_set_fen(b"8/8/4k3/8/4r3/4K3/8/8 w - - 100 50", ctypes.byref(board))
    pass_06 = (dll.native_can_claim_fifty_moves(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_06", "Fifty-Move Rule Claimable (halfmove=100)", pass_06, "Expected claimable=1")
    
    # REF_07: 75-move rule automatic draw at halfmove >= 150
    dll.native_set_fen(b"8/8/4k3/8/4r3/4K3/8/8 w - - 150 75", ctypes.byref(board))
    pass_07 = (dll.native_is_seventyfive_moves(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_07", "Seventy-Five Move Rule Auto (halfmove=150)", pass_07, "Expected auto_draw=1")
    
    # REF_08: Threefold repetition claimable
    dll.native_reset_history()
    k1 = 0x1122334455667788
    dll.native_push_history(k1)
    dll.native_push_history(0x99887766)
    dll.native_push_history(k1)
    dll.native_push_history(0x55443322)
    dll.native_push_history(k1)
    board.zobrist_key = k1
    pass_08 = (dll.native_can_claim_threefold_repetition(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_08", "Threefold Repetition Claimable (count=3)", pass_08, "Expected claimable=1")
    
    # REF_09: Fivefold repetition automatic draw
    dll.native_push_history(0x1234)
    dll.native_push_history(k1)
    dll.native_push_history(0x5678)
    dll.native_push_history(k1)
    pass_09 = (dll.native_is_fivefold_repetition(ctypes.byref(board)) == 1)
    all_pass &= test_case("REF_09", "Fivefold Repetition Auto Draw (count=5)", pass_09, "Expected auto_draw=1")
    
    # REF_10: Stalemate detection
    dll.native_set_fen(b"k7/8/1Q6/8/8/8/8/7K b - - 0 1", ctypes.byref(board))
    in_chk = dll.native_is_check(ctypes.byref(board))
    n_moves = dll.native_generate_legal_moves(ctypes.byref(board), moves_buf)
    pass_10 = (in_chk == 0 and n_moves == 0)
    all_pass &= test_case("REF_10", "Stalemate (in_check=0, legal_moves=0)", pass_10, f"check={in_chk}, legal={n_moves}")
    
    # REF_11: Checkmate detection
    dll.native_set_fen(b"r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5", ctypes.byref(board))
    # Scholar's mate: Qxf7#
    dll.native_set_fen(b"r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 5", ctypes.byref(board))
    in_chk_mate = dll.native_is_check(ctypes.byref(board))
    n_moves_mate = dll.native_generate_legal_moves(ctypes.byref(board), moves_buf)
    pass_11 = (in_chk_mate == 1 and n_moves_mate == 0)
    all_pass &= test_case("REF_11", "Checkmate (in_check=1, legal_moves=0)", pass_11, f"check={in_chk_mate}, legal={n_moves_mate}")
    
    # REF_12: Castling rights invalidation on king move
    dll.native_set_fen(b"r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", ctypes.byref(board))
    undo = UndoInfo()
    # Move White King e1 to e2
    # Move encoding: from e1 (4) to e2 (12), flag 0
    m_ke2 = 4 | (12 << 6) | (0 << 12)
    dll.native_make_move(ctypes.byref(board), m_ke2, ctypes.byref(undo))
    white_castling_after = board.castling_rights & (1 | 2) # W_OO | W_OOO
    dll.native_unmake_move(ctypes.byref(board), m_ke2, ctypes.byref(undo))
    white_castling_restored = board.castling_rights & (1 | 2)
    pass_12 = (white_castling_after == 0 and white_castling_restored == 3)
    all_pass &= test_case("REF_12", "King Move Castling Rights Invalidation", pass_12, f"after={white_castling_after}, restored={white_castling_restored}")
    
    # REF_13: Castling rights invalidation on rook move
    # Move Rook h1 (7) to h2 (15)
    m_rh2 = 7 | (15 << 6) | (0 << 12)
    dll.native_make_move(ctypes.byref(board), m_rh2, ctypes.byref(undo))
    w_oo_after = board.castling_rights & 1 # W_OO
    w_ooo_after = board.castling_rights & 2 # W_OOO
    dll.native_unmake_move(ctypes.byref(board), m_rh2, ctypes.byref(undo))
    pass_13 = (w_oo_after == 0 and w_ooo_after == 2)
    all_pass &= test_case("REF_13", "Rook Move Castling Invalidation", pass_13, f"W_OO={w_oo_after}, W_OOO={w_ooo_after}")
    
    # REF_14: En Passant capture execution and pawn removal
    dll.native_set_fen(b"rnbqkbnr/pppp1ppp/8/4pP2/8/8/PPPPP1PP/RNBQKBNR w KQkq e6 0 2", ctypes.byref(board))
    # Move f5 (37 = 4*8+5) to e6 (44 = 5*8+4), flag 2 (EP)
    m_ep = 37 | (44 << 6) | (2 << 12)
    dll.native_make_move(ctypes.byref(board), m_ep, ctypes.byref(undo))
    # Black pawn on e5 (36 = 4*8+4) should be removed
    e5_occ = (board.pieces[1][0] & (1 << 36)) != 0 # Black pawn on e5
    dll.native_unmake_move(ctypes.byref(board), m_ep, ctypes.byref(undo))
    e5_restored = (board.pieces[1][0] & (1 << 36)) != 0
    pass_14 = (not e5_occ and e5_restored)
    all_pass &= test_case("REF_14", "En Passant Pawn Capture & Unmake", pass_14, f"e5_cleared={not e5_occ}, restored={e5_restored}")
    
    # REF_15: Promotion piece types
    dll.native_set_fen(b"8/4P3/8/8/8/8/8/4K2k w - - 0 1", ctypes.byref(board))
    n_prom = dll.native_generate_legal_moves(ctypes.byref(board), moves_buf)
    prom_flags = set()
    for i in range(n_prom):
        mv = moves_buf[i]
        f = (mv >> 12) & 0x3
        p = (mv >> 14) & 0x3
        if f == 3: # Promotion flag
            prom_flags.add(p)
    pass_15 = (prom_flags == {0, 1, 2, 3}) # Knight, Bishop, Rook, Queen
    all_pass &= test_case("REF_15", "All Promotion Pieces (Q, R, B, N)", pass_15, f"found_prom_pieces={len(prom_flags)}/4")
    
    return {
        "all_passed": all_pass,
        "cases": cases
    }

def main():
    print("Executing Milestone P1.21 Phase 11 Correctness & Referee Verification...")
    dll = load_bridge()
    
    perft_res = run_perft_suite(dll)
    ref_res = run_referee_suite(dll)
    
    report = {
        "perft_suite": perft_res,
        "referee_suite": ref_res,
        "overall_qualification_passed": (perft_res["all_passed"] and ref_res["all_passed"])
    }
    
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nFinal Correctness Qualification: {'PASSED' if report['overall_qualification_passed'] else 'FAILED'}")
    print(f"Results written to: {OUT_RAW}")

if __name__ == "__main__":
    main()
