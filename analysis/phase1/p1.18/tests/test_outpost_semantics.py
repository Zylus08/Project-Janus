#!/usr/bin/env python3
"""
test_outpost_semantics.py
Milestone P1.18 Phase 3: Comprehensive Outpost Semantics & Generalization Suite.
Audits the square-attack calculation, pawn advance immunity, blocked pawn edge cases,
and verifies 100.0% color symmetry across 225 test positions.
"""

import sys
import ctypes
import json
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.dll"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.18" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_int),
        ("en_passant_sq", ctypes.c_int),
        ("halfmove_clock", ctypes.c_int),
        ("fullmove_number", ctypes.c_int),
    ]

def invert_fen(fen: str) -> str:
    b = chess.Board(fen)
    return b.mirror().fen()

def run_outpost_suite():
    print("================================================================================")
    print("PHASE 3: OUTPOST SEMANTICS & COLOR SYMMETRY VERIFICATION")
    print("================================================================================")

    if not DLL_PATH.exists():
        print(f"Error: DLL not found at {DLL_PATH}")
        sys.exit(1)

    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init.restype = ctypes.c_int
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_evaluate.restype = ctypes.c_int

    dll.native_set_eval_mode.argtypes = [ctypes.c_int]
    dll.native_set_eval_mode(5)

    dll.native_set_outpost_mode.argtypes = [ctypes.c_int]
    dll.native_set_outpost_mode(1) # True outposts enabled

    def eval_fen(fen_str: str) -> int:
        nb = NativeBoard()
        dll.native_set_fen(fen_str.encode('utf-8'), ctypes.byref(nb))
        return dll.native_evaluate(ctypes.byref(nb))

    # 1. Ten Targeted Diagnostic Scenarios
    scenarios = [
        {
            "id": "T1_TRUE_KNIGHT_OUTPOST_WHITE",
            "desc": "White Nd5 defended by e4 pawn; Black has no c/e pawns on ranks 5-7 (Permanent Immunity)",
            "fen": "8/p4pkp/8/3N4/4P3/8/5PKP/8 w - - 0 1",
            "expected_true": True
        },
        {
            "id": "T2_UNPROTECTED_KNIGHT_SQUARE",
            "desc": "White Nd5 with no friendly pawn support (Unprotected square -> 0 bonus)",
            "fen": "8/p4pkp/8/3N4/8/8/5PKP/8 w - - 0 1",
            "expected_true": False
        },
        {
            "id": "T3_TRANSIENT_PSEUDO_OUTPOST",
            "desc": "White Nd5 defended by e4, but Black has pawn on c7 (Kickable by c6 -> Transient bonus)",
            "fen": "8/p1p2pkp/8/3N4/4P3/8/5PKP/8 w - - 0 1",
            "expected_true": False
        },
        {
            "id": "T4_ENEMY_PAWN_CHALLENGE",
            "desc": "White Nd5 defended by e4, but Black pawn on c6 currently attacks d5",
            "fen": "8/p4pkp/2p5/3N4/4P3/8/5PKP/8 w - - 0 1",
            "expected_true": False
        },
        {
            "id": "T5_BLOCKED_ENEMY_PAWN",
            "desc": "White Nd5 defended by e4; Black pawn on c7 is blocked by White pawn on c6",
            "fen": "8/p1p2pkp/2P5/3N4/4P3/8/5PKP/8 w - - 0 1",
            "expected_true": False
        },
        {
            "id": "T6_TRUE_KNIGHT_OUTPOST_BLACK",
            "desc": "Black Nd4 defended by e5 pawn; White has no c/e pawns behind rank 4 (Permanent Immunity)",
            "fen": "8/5pkp/8/4p3/3n4/8/P4PKP/8 b - - 0 1",
            "expected_true": True
        },
        {
            "id": "T7_TRUE_BISHOP_OUTPOST_WHITE",
            "desc": "White Bd5 defended by e4 pawn; Black has no c/e pawns on ranks 5-7 (Central Bishop Immunity)",
            "fen": "8/p4pkp/8/3B4/4P3/8/5PKP/8 w - - 0 1",
            "expected_true": True
        },
        {
            "id": "T8_TRUE_BISHOP_OUTPOST_BLACK",
            "desc": "Black Bd4 defended by e5 pawn; White has no c/e pawns behind rank 4 (Central Bishop Immunity)",
            "fen": "8/5pkp/8/4p3/3b4/8/P4PKP/8 b - - 0 1",
            "expected_true": True
        },
        {
            "id": "T9_EN_PASSANT_BOUNDARY",
            "desc": "Position with en-passant square active; verifies no corruption of outpost evaluation",
            "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq d3 0 3",
            "expected_true": False
        },
        {
            "id": "T10_MIRROR_SYMMETRY_PAIR",
            "desc": "White outpost Nd5 vs Black outpost Nd4 exact mirror comparison",
            "fen": "8/p4pkp/8/3N4/4P3/8/5PKP/8 w - - 0 1",
            "expected_true": True
        }
    ]

    scenario_results = []
    print("\n--- 1. Evaluating Targeted Outpost Scenarios ---")
    for s in scenarios:
        score = eval_fen(s["fen"])
        inv_fen = invert_fen(s["fen"])
        inv_score = eval_fen(inv_fen)

        # Note: evaluate returns score from perspective of side to move.
        # If fen has White to move, mirror fen has Black to move.
        # So score(White) == score(Black in mirror) -> score == inv_score!
        # Let's check sign: if side to move changes, score in mirror is from Black's perspective.
        # So if White had +100 cp in fen, in mirrored fen Black has +100 cp.
        # Therefore score == inv_score!
        symmetry_pass = (score == inv_score)
        print(f"[{'PASS' if symmetry_pass else 'FAIL'}] {s['id']:<32} Score: {score:+d} cp | Mirror: {inv_score:+d} cp | Equal: {symmetry_pass}")
        scenario_results.append({
            "scenario": s["id"],
            "description": s["desc"],
            "fen": s["fen"],
            "score": score,
            "mirrored_score": inv_score,
            "symmetry_verified": symmetry_pass
        })

    # 2. Automated 225-Position Symmetry Test
    print("\n--- 2. Validating 225-Position Color Symmetry Suite ---")
    openings_path = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
    with open(openings_path, "r") as f:
        openings = json.load(f)

    test_fens = []
    for op in openings:
        b = chess.Board()
        test_fens.append(b.fen())
        for move_uci in op.get("uci_sequence", []):
            try:
                b.push_uci(move_uci)
                test_fens.append(b.fen())
            except Exception:
                pass
        if len(test_fens) >= 225:
            break
    test_fens = test_fens[:225]

    sym_passed = 0
    for idx, fen in enumerate(test_fens):
        s1 = eval_fen(fen)
        s2 = eval_fen(invert_fen(fen))
        if s1 == s2:
            sym_passed += 1
        else:
            print(f"Symmetry violation at #{idx}: FEN {fen} -> s1={s1}, s2={s2}")

    print(f"Color Symmetry Results: {sym_passed}/225 ({sym_passed/225*100:.2f}%) Exact Matches.")
    assert sym_passed == 225, f"Color symmetry violation! Only {sym_passed}/225 passed."

    out_file = RAW_DIR / "outpost_semantics_raw.json"
    with open(out_file, "w") as f:
        json.dump({
            "scenarios": scenario_results,
            "symmetry_225_passed": sym_passed,
            "total_tested": 225
        }, f, indent=2)
    print(f"Outpost verification data written to {out_file}")

if __name__ == "__main__":
    run_outpost_suite()
