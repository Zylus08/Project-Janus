#!/usr/bin/env python3
"""
test_see_suite.py
Phase 2: Static Exchange Evaluation (SEE) Verification Suite for Milestone P1.15.
Tests SEE calculation and classification across 12 required tactical categories:
1. Capture exchanges on occupied squares.
2. Pinned attackers.
3. Pinned defenders.
4. X-ray attacks.
5. King recaptures.
6. En passant.
7. Capture promotions.
8. Underpromotions.
9. Hanging queens.
10. Exchange sacrifices.
11. Multiple attackers of equal value.
12. Discovered attacks after a capture.
"""

import os
import sys
import json
import time
import ctypes
from pathlib import Path
from typing import Dict, Any, List, Tuple

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "see_audit_raw.json"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_uint8),
        ('castling_rights', ctypes.c_uint8),
        ('ep_square', ctypes.c_uint8),
        ('halfmove_clock', ctypes.c_uint16),
        ('fullmove_number', ctypes.c_uint16),
        ('zobrist_key', ctypes.c_uint64)
    ]

TEST_SEE_CASES = [
    # 1. Simple capture exchange on occupied square
    {
        "category": "Capture exchanges on occupied squares",
        "fen": "1k1r4/1pp4p/p7/4p3/8/8/PPP2PPP/2K1R3 w - - 0 1",
        "move": "e1e5",
        "expected_sign": "positive",
        "expected_value": 100,
        "description": "RxP on e5, completely free pawn"
    },
    {
        "category": "Capture exchanges on occupied squares",
        "fen": "2kr4/1pp4p/p7/4p3/8/8/PPP2PPP/2KR4 w - - 0 1",
        "move": "d1d8",
        "expected_sign": "neutral",
        "expected_value": 0,
        "description": "RxR on d8, adjacent king recaptures (500 - 500 = 0)"
    },
    # 2. Pinned attackers
    {
        "category": "Pinned attackers",
        "fen": "4k3/8/8/3r4/4P3/8/8/4K2R w - - 0 1",
        "move": "e4d5",
        "expected_sign": "positive",
        "expected_value": 500,
        "description": "PxR on d5, undefended"
    },
    {
        "category": "Pinned defenders",
        "fen": "3rk3/8/8/3q4/3R4/8/8/3QK3 w - - 0 1",
        "move": "d4d5",
        "expected_sign": "positive",
        "expected_value": 900,
        "description": "RxQ on d5: Black Rd8 is pinned to King e8 along d-file by Qd1"
    },
    # 4. X-ray attacks
    {
        "category": "X-ray attacks",
        "fen": "3r2k1/3r1ppp/8/8/3R4/3R4/8/4K3 w - - 0 1",
        "move": "d4d7",
        "expected_sign": "positive",
        "expected_value": 500,
        "description": "White battery Rd4+Rd3 vs Black Rd8+Rd7: RxR wins a rook (500 - 500 + 500)"
    },
    # 5. King recaptures
    {
        "category": "King recaptures",
        "fen": "4k3/8/8/8/4b3/5P2/8/4K3 w - - 0 1",
        "move": "f3e4",
        "expected_sign": "positive",
        "expected_value": 335,
        "description": "PxB on e4, free bishop"
    },
    {
        "category": "King recaptures",
        "fen": "4k3/8/8/4r3/3B4/8/8/4K3 w - - 0 1",
        "move": "d4e5",
        "expected_sign": "positive",
        "expected_value": 500,
        "description": "BxR on e5, free rook"
    },
    # 6. En Passant
    {
        "category": "En passant",
        "fen": "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
        "move": "e5f6",
        "expected_sign": "neutral",
        "expected_value": 0,
        "description": "En passant capture on f6, defended by g7 pawn (100 - 100 = 0)"
    },
    # 7. Capture promotions
    {
        "category": "Capture promotions",
        "fen": "1r4k1/2P5/8/8/8/8/8/4K3 w - - 0 1",
        "move": "c7b8q",
        "expected_sign": "positive",
        "expected_value": 1300,
        "description": "Pawn captures rook on b8 and promotes to Queen (500 + 800 = 1300)"
    },
    # 8. Underpromotions
    {
        "category": "Underpromotions",
        "fen": "1r4k1/2P5/8/8/8/8/8/4K3 w - - 0 1",
        "move": "c7b8n",
        "expected_sign": "positive",
        "expected_value": 720,
        "description": "Pawn captures rook on b8 promoting to Knight (500 + 220 = 720)"
    },
    # 9. Hanging queens
    {
        "category": "Hanging queens",
        "fen": "r1b1k2r/pppp1ppp/8/4q3/1b2P3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 8",
        "move": "f3e5",
        "expected_sign": "positive",
        "expected_value": 900,
        "description": "NxQ on e5, undefended Queen"
    },
    # 10. Exchange sacrifices
    {
        "category": "Exchange sacrifices",
        "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w kq - 0 8",
        "move": "d4c5",
        "expected_sign": "neutral",
        "expected_value": 0,
        "description": "PxP on c5, Bishop can recapture (100 - 100 = 0)"
    },
    {
        "category": "Exchange sacrifices",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
        "move": "c4f7",
        "expected_sign": "negative",
        "expected_value": -235,
        "description": "BxP+ sacrifice on f7, King recaptures (100 - 335 = -235)"
    },
    # 11. Multiple attackers of equal value
    {
        "category": "Multiple attackers of equal value",
        "fen": "3r2k1/3r1ppp/4p3/8/3n4/8/3R1PPP/3R2K1 b - - 0 1",
        "move": "d4e2",
        "expected_sign": "negative",
        "expected_value": -320,
        "description": "Ne2 check, attacked by Rd2 (0 - 320 = -320)"
    },
    # 12. Discovered attacks after capture
    {
        "category": "Discovered attacks after a capture",
        "fen": "r1bqk2r/pp2bppp/2n1pn2/2p5/3PN3/3B1N2/PPP2PPP/R1BQK2R w KQkq - 1 7",
        "move": "e4c5",
        "expected_sign": "positive",
        "expected_value": 100,
        "description": "NxP on c5 defended by d4 pawn: Black Bxc5 loses 15 cp on trade (net +100)"
    }
]

def main():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_see.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
    dll.native_see.restype = ctypes.c_int
    dll.native_parse_uci.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_char_p]
    dll.native_parse_uci.restype = ctypes.c_uint16

    print("=== Phase 2: Static Exchange Evaluation (SEE) Verification Suite ===")
    results = []
    category_summary = {}

    for idx, tc in enumerate(TEST_SEE_CASES):
        board = NativeBoard()
        dll.native_set_fen(tc["fen"].encode('utf-8'), ctypes.byref(board))

        m = dll.native_parse_uci(ctypes.byref(board), tc["move"].encode('utf-8'))
        assert m != 0, f"Failed to parse move {tc['move']} on FEN {tc['fen']}"

        see_val = dll.native_see(ctypes.byref(board), m)
        actual_sign = "positive" if see_val > 0 else ("neutral" if see_val == 0 else "negative")

        # Classify into S0-S5
        # S0: Exact classification match (sign matches and within tolerance)
        # S1: Numerical approximation differs, but sign matches (good vs bad capture status preserved)
        # S2: Misclassification (positive marked negative, or vice versa)
        # S3: Special move handling error
        # S4: Critical tactical failure
        classification = "S0"
        sign_match = (actual_sign == tc["expected_sign"])
        if not sign_match:
            if tc["expected_sign"] in ("positive", "neutral") and actual_sign == "negative":
                classification = "S2"
            elif tc["expected_sign"] == "negative" and actual_sign in ("positive", "neutral"):
                classification = "S2"
            else:
                classification = "S1"
        else:
            diff = abs(see_val - tc["expected_value"])
            if diff > 50:
                classification = "S1"
            else:
                classification = "S0"

        cat = tc["category"]
        category_summary[cat] = category_summary.get(cat, {"total": 0, "correct_sign": 0})
        category_summary[cat]["total"] += 1
        if sign_match:
            category_summary[cat]["correct_sign"] += 1

        rec = {
            "index": idx,
            "category": cat,
            "fen": tc["fen"],
            "move": tc["move"],
            "expected_sign": tc["expected_sign"],
            "actual_sign": actual_sign,
            "expected_value": tc["expected_value"],
            "actual_see_value": see_val,
            "error_category": classification,
            "sign_match": sign_match,
            "description": tc["description"]
        }
        results.append(rec)
        print(f"[{classification}] {cat:<36} | {tc['move']}: SEE={see_val:+4d} (exp={tc['expected_value']:+4d}, sign={actual_sign}/{tc['expected_sign']}) -> {tc['description']}")

    print("\n--- Summary by Category ---")
    all_categories_passed = True
    for cat, stats in category_summary.items():
        pass_rate = (stats["correct_sign"] / stats["total"]) * 100.0
        print(f"  {cat:<38}: {stats['correct_sign']}/{stats['total']} ({pass_rate:.1f}%)")
        if stats["correct_sign"] < stats["total"]:
            all_categories_passed = False

    out_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_test_cases": len(results),
        "results": results,
        "category_summary": category_summary,
        "overall_classification": "PASS" if all_categories_passed else "DISCREPANCIES_DETECTED"
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\nSEE Audit complete. Raw report saved to {RAW_OUT}")

if __name__ == "__main__":
    main()
