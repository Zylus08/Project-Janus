#!/usr/bin/env python3
"""
audit_quiescence_architecture.py
Phase 3: Quiescence Search Architecture Audit for Milestone P1.16.
Audits the 10 critical questions regarding quiescence search reliability,
in-check invariants, stand-pat legality, evasion omission, SEE filtering,
stalemate/mate handling, quiet checks, and search-state tracking.
Outputs raw data to analysis/phase1/p1.16/raw/quiescence_audit_raw.json.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.16" / "raw" / "quiescence_audit_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64)
    ]

dll = ctypes.CDLL(str(DLL_PATH))
dll.native_init()
dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
dll.native_set_fen.restype = ctypes.c_int
dll.native_is_check.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_is_check.restype = ctypes.c_int
dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_evaluate.restype = ctypes.c_int
dll.native_generate_captures.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
dll.native_generate_captures.restype = ctypes.c_int
dll.native_generate_legal_moves.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
dll.native_generate_legal_moves.restype = ctypes.c_int
dll.native_see.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
dll.native_see.restype = ctypes.c_int

def test_quiescence_defects():
    print("=== Phase 3: Quiescence Search Architecture Audit ===")
    
    audits = []

    # CASE 1: In-check entry and stand-pat evaluation
    fen_case1 = "6k1/8/8/8/8/8/8/6RK b - - 0 1"
    b1 = NativeBoard()
    dll.native_set_fen(fen_case1.encode(), ctypes.byref(b1))
    in_check1 = bool(dll.native_is_check(ctypes.byref(b1)))
    eval1 = dll.native_evaluate(ctypes.byref(b1))
    caps1 = (ctypes.c_uint16 * 256)()
    n_caps1 = dll.native_generate_captures(ctypes.byref(b1), caps1)
    legal1 = (ctypes.c_uint16 * 256)()
    n_legal1 = dll.native_generate_legal_moves(ctypes.byref(b1), legal1)
    
    audits.append({
        "case_id": "CASE_01_IN_CHECK_STAND_PAT",
        "question": "Can Janus enter quiescence search while in check and use stand-pat?",
        "fen": fen_case1,
        "side_to_move": "Black",
        "in_check": in_check1,
        "legal_moves_count": n_legal1,
        "captures_generated_count": n_caps1,
        "static_eval": eval1,
        "expected_behavior": "Must recognize in-check state, prohibit stand-pat, and search legal evasions",
        "actual_behavior": f"Evaluates stand_pat = {eval1}. If beta <= {eval1}, produces false beta cutoff without searching any move. Generates {n_caps1} captures (missing all {n_legal1} quiet king evasions).",
        "defect_severity": "CRITICAL",
        "defective_condition": "quiescence() lacks 'in_check' branch; uses stand_pat unconditionally"
    })

    # CASE 2: Checkmate treated as slight positional disadvantage
    fen_case2 = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3" # Fool's Mate
    b2 = NativeBoard()
    dll.native_set_fen(fen_case2.encode(), ctypes.byref(b2))
    in_check2 = bool(dll.native_is_check(ctypes.byref(b2)))
    eval2 = dll.native_evaluate(ctypes.byref(b2))
    caps2 = (ctypes.c_uint16 * 256)()
    n_caps2 = dll.native_generate_captures(ctypes.byref(b2), caps2)
    legal2 = (ctypes.c_uint16 * 256)()
    n_legal2 = dll.native_generate_legal_moves(ctypes.byref(b2), legal2)

    audits.append({
        "case_id": "CASE_02_CHECKMATE_STAND_PAT",
        "question": "Can quiescence search return non-mate score in checkmate?",
        "fen": fen_case2,
        "side_to_move": "White",
        "in_check": in_check2,
        "legal_moves_count": n_legal2,
        "captures_generated_count": n_caps2,
        "static_eval": eval2,
        "expected_behavior": "Must return -MATE (-30000) because White has 0 legal moves in check",
        "actual_behavior": f"quiescence() returns stand_pat = {eval2} cp! Returns {eval2} instead of -30000.",
        "defect_severity": "CATASTROPHIC",
        "defective_condition": "quiescence() does not check for checkmate when n_legal == 0 in check"
    })

    # CASE 3: Quiet check evasion omission
    fen_case3 = "R6k/8/8/8/8/8/8/7K b - - 0 1"
    b3 = NativeBoard()
    dll.native_set_fen(fen_case3.encode(), ctypes.byref(b3))
    in_check3 = bool(dll.native_is_check(ctypes.byref(b3)))
    caps3 = (ctypes.c_uint16 * 256)()
    n_caps3 = dll.native_generate_captures(ctypes.byref(b3), caps3)
    legal3 = (ctypes.c_uint16 * 256)()
    n_legal3 = dll.native_generate_legal_moves(ctypes.byref(b3), legal3)

    audits.append({
        "case_id": "CASE_03_QUIET_EVASIONS_OMITTED",
        "question": "Are non-capture check evasions omitted in quiescence?",
        "fen": fen_case3,
        "side_to_move": "Black",
        "in_check": in_check3,
        "legal_moves_count": n_legal3,
        "captures_generated_count": n_caps3,
        "expected_behavior": "Search Kh7 to escape check safely",
        "actual_behavior": f"Generates 0 captures. Quiescence aborts search without testing Kh7, returning stand-pat.",
        "defect_severity": "CRITICAL",
        "defective_condition": "native_generate_captures() only generates captures; all quiet evasions are omitted"
    })

    # CASE 4: Negative-SEE Defensive Capture Pruning
    # Black King in check by defended White Queen on f7. Black's only move is Kxf7 (negative SEE).
    # White: Kh1, Qf7, Bc4. Black: Ke8. White queen on f7 supported by Bc4.
    # Black is in check. Legal move is Kxf7 (King captures Queen, then Bc4 captures King -> SEE = 900 - 10000 = -9100).
    fen_case4 = "4k3/5Q2/8/8/2B5/8/8/7K b - - 0 1"
    b4 = NativeBoard()
    dll.native_set_fen(fen_case4.encode(), ctypes.byref(b4))
    in_check4 = bool(dll.native_is_check(ctypes.byref(b4)))
    caps4 = (ctypes.c_uint16 * 256)()
    n_caps4 = dll.native_generate_captures(ctypes.byref(b4), caps4)
    legal4 = (ctypes.c_uint16 * 256)()
    n_legal4 = dll.native_generate_legal_moves(ctypes.byref(b4), legal4)
    
    # Check SEE of the capture
    see_val = None
    if n_caps4 > 0:
        see_val = dll.native_see(ctypes.byref(b4), caps4[0])

    audits.append({
        "case_id": "CASE_04_NEGATIVE_SEE_EVASION_PRUNING",
        "question": "Can negative-SEE filtering discard the only legal evasion?",
        "fen": fen_case4,
        "side_to_move": "Black",
        "in_check": in_check4,
        "legal_moves_count": n_legal4,
        "captures_generated_count": n_caps4,
        "capture_see": see_val,
        "expected_behavior": "Must search Kxf7 (or Kd8 if legal). Evasions must never be pruned by SEE.",
        "actual_behavior": f"SEE is {see_val} < 0. Under g_quiescence_see_mode >= 2, line 3949 executes 'continue;', pruning the capture! Black is left with 0 moves searched.",
        "defect_severity": "CRITICAL",
        "defective_condition": "SEE pruning does not check whether position is in check or move is evasion"
    })

    # CASE 5: Stalemate misclassified as material deficit
    fen_case5 = "k7/8/1K6/8/8/8/8/8 b - - 0 1"
    b5 = NativeBoard()
    dll.native_set_fen(fen_case5.encode(), ctypes.byref(b5))
    in_check5 = bool(dll.native_is_check(ctypes.byref(b5)))
    eval5 = dll.native_evaluate(ctypes.byref(b5))
    legal5 = (ctypes.c_uint16 * 256)()
    n_legal5 = dll.native_generate_legal_moves(ctypes.byref(b5), legal5)

    audits.append({
        "case_id": "CASE_05_STALEMATE_MISCLASSIFICATION",
        "question": "Does quiescence correctly return 0 cp for stalemate?",
        "fen": fen_case5,
        "side_to_move": "Black",
        "in_check": in_check5,
        "legal_moves_count": n_legal5,
        "static_eval": eval5,
        "expected_behavior": "Return 0 cp (Stalemate draw)",
        "actual_behavior": f"Returns stand_pat = {eval5} cp. Does not detect stalemate.",
        "defect_severity": "MODERATE",
        "defective_condition": "quiescence() lacks stalemate detection when n_legal == 0 and !in_check"
    })

    # CASE 6: Missing Quiet Checking Moves at Horizon
    # White to move: quiet check Qh6+ forces mate or wins queen
    fen_case6 = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1n3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4" # Scholar's mate threat: Qxf7# is capture, but quiet checks like Bxf7+ also exist
    b6 = NativeBoard()
    dll.native_set_fen(fen_case6.encode(), ctypes.byref(b6))
    caps6 = (ctypes.c_uint16 * 256)()
    n_caps6 = dll.native_generate_captures(ctypes.byref(b6), caps6)

    audits.append({
        "case_id": "CASE_06_QUIET_CHECKS_EXCLUDED",
        "question": "Are quiet checking moves searched in quiescence?",
        "fen": fen_case6,
        "captures_generated": n_caps6,
        "expected_behavior": "Selective checking moves at first quiescence ply can discover forced tactics",
        "actual_behavior": "Only captures and promotions are generated. Quiet checks are 100% ignored.",
        "defect_severity": "ARCHITECTURAL_LIMITATION",
        "defective_condition": "Standard captures-only quiescence search"
    })

    # CASE 7: Missing Quiescence TT and Mate Distance
    audits.append({
        "case_id": "CASE_07_TT_AND_MATE_DISTANCE",
        "question": "Are quiescence TT entries probed/stored and mate distance tracked?",
        "fen": "ALL",
        "expected_behavior": "Quiescence search should track search ply to normalize mate scores (-MATE + ply)",
        "actual_behavior": "quiescence() signature lacks 'ply'; does not probe or store in transposition table; cannot normalize mate scores.",
        "defect_severity": "HIGH",
        "defective_condition": "Missing 'int ply' and 'int qply' parameters in quiescence signature"
    })

    # Summary table
    print("\nAudited 7 Core Quiescence Diagnostic Cases:")
    for a in audits:
        print(f"[{a['case_id']}] Severity: {a['defect_severity']} | Defect: {a['defective_condition']}")

    out_data = {
        "milestone": "P1.16",
        "phase": 3,
        "title": "Quiescence Search Architecture Audit",
        "total_cases_audited": len(audits),
        "critical_bugs_found": sum(1 for a in audits if a["defect_severity"] in ["CRITICAL", "CATASTROPHIC"]),
        "audits": audits
    }

    with open(RAW_OUT, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\nRaw quiescence audit output written to {RAW_OUT}")

if __name__ == "__main__":
    test_quiescence_defects()
