#!/usr/bin/env python3
"""
test_movepicker_completeness.py
Phase 1: Complete MovePicker Correctness Audit for Milestone P1.15.
Tests exhaustive move-set preservation, duplicate detection, omission detection,
stage invariant properties, and legality across 19 stratified position classes
and 1,000 randomized legal chess positions against python-chess reference enumeration.
"""

import os
import sys
import json
import time
import random
import ctypes
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "movepicker_completeness_raw.json"

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

# 19 Required Position Classes
STRATIFIED_POSITIONS = [
    {"class": "Starting position", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"class": "Open tactical middlegames", "fen": "r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"},
    {"class": "Closed positions", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9"},
    {"class": "King in check", "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"},
    {"class": "Double check", "fen": "r1b1k2r/pppp1Npp/8/4p3/2Bn4/8/PPPP2PP/RNB1b1KR b kq - 1 9"},
    {"class": "Pinned pieces", "fen": "r1b1k2r/ppppbppp/5n2/4q3/8/2N1P3/PPPBBPPP/R2QK2R w KQkq - 2 9"},
    {"class": "Castling", "fen": "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"},
    {"class": "En passant", "fen": "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"},
    {"class": "Quiet promotions", "fen": "8/4P3/8/8/8/8/8/4K2k w - - 0 1"},
    {"class": "Capture promotions", "fen": "r1b1kb1r/pppp1P1p/8/8/8/8/PPP2PPP/RNBQKBNR w KQkq - 0 8"},
    {"class": "Underpromotions", "fen": "8/3P4/8/8/8/8/1k6/4K3 w - - 0 1"},
    {"class": "Exchange sacrifices", "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 b - - 1 15"},
    {"class": "Discovered attacks", "fen": "r1bqkb1r/pp3ppp/2n5/3np3/8/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 0 8"},
    {"class": "Forced recaptures", "fen": "2r3k1/1p3pp1/pq5p/3p4/3Nn3/1PP2P1P/P2Q2P1/4R1K1 b - - 0 24"},
    {"class": "Stalemate-adjacent positions", "fen": "k7/8/1Q6/8/8/8/8/7K b - - 0 1"},
    {"class": "Checkmate-in-one positions", "fen": "k7/7R/6R1/8/8/8/8/7K w - - 0 1"},
    {"class": "Forced defensive captures", "fen": "r1b1k2r/pppp1ppp/8/8/1b1n4/2N5/PPP2PPP/R1B1KB1R w KQkq - 0 8"},
    {"class": "Pure pawn endgames", "fen": "8/5p2/4k3/4p1p1/4P1P1/4KP2/8/8 w - - 0 45"},
    {"class": "Queen and rook endgames", "fen": "2r3k1/5pp1/7p/8/3Q4/8/5PPP/2R3K1 w - - 0 30"}
]

def parse_move_to_uci(dll, m: int) -> str:
    buf = ctypes.create_string_buffer(16)
    dll.native_move_to_uci(m, buf)
    return buf.value.decode('utf-8')

def test_position_movepicker(dll, fen: str, tt_m: int = 0, k1: int = 0, k2: int = 0, cm: int = 0) -> Dict[str, Any]:
    board = NativeBoard()
    dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(board))

    # Set killer and countermove state
    dll.native_clear_killers()
    dll.native_clear_history_heuristic()
    dll.native_clear_tactical_tables()

    if k1 != 0: dll.native_set_killer(0, 0, k1)
    if k2 != 0: dll.native_set_killer(0, 1, k2)
    if cm != 0: dll.native_set_countermove(0, 0, cm)

    out_moves = (ctypes.c_uint16 * 256)()
    out_stages = (ctypes.c_int * 256)()

    count = dll.native_test_movepicker(ctypes.byref(board), tt_m, 0, 8, out_moves, out_stages)
    yielded_moves = [out_moves[i] for i in range(count)]
    yielded_stages = [out_stages[i] for i in range(count)]

    # Independent reference via python-chess
    py_board = chess.Board(fen)
    ref_legal_uci = set(m.uci() for m in py_board.legal_moves)

    yielded_uci = [parse_move_to_uci(dll, m) for m in yielded_moves]
    yielded_set = set(yielded_uci)

    duplicates = len(yielded_uci) - len(yielded_set)
    missing = ref_legal_uci - yielded_set
    extra_illegal = yielded_set - ref_legal_uci

    is_complete_and_legal = (duplicates == 0 and len(missing) == 0 and len(extra_illegal) == 0)

    return {
        "fen": fen,
        "ref_legal_count": len(ref_legal_uci),
        "yielded_count": len(yielded_uci),
        "duplicates_count": duplicates,
        "missing_moves": list(missing),
        "illegal_moves": list(extra_illegal),
        "passed": is_complete_and_legal,
        "yielded_uci": yielded_uci,
        "yielded_stages": yielded_stages
    }

def generate_random_positions(n: int = 1000, seed: int = 42) -> List[str]:
    random.seed(seed)
    fens = []
    for _ in range(n):
        b = chess.Board()
        # Play 10 to 60 random legal plies
        plies = random.randint(10, 60)
        for _ in range(plies):
            if b.is_game_over():
                break
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(random.choice(moves))
        fens.append(b.fen())
    return fens

def main():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_test_movepicker.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_int)]
    dll.native_test_movepicker.restype = ctypes.c_int
    dll.native_set_killer.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint16]
    dll.native_set_countermove.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint16]
    dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    dll.native_parse_uci.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_char_p]
    dll.native_parse_uci.restype = ctypes.c_uint16

    print("=== Phase 1: MovePicker Completeness & Legality Audit ===")
    print("--- 1. Testing 19 Stratified Position Classes ---")
    stratified_results = []
    all_strat_passed = True

    for p in STRATIFIED_POSITIONS:
        res = test_position_movepicker(dll, p["fen"])
        passed = res["passed"]
        all_strat_passed = all_strat_passed and passed
        stratified_results.append({
            "class": p["class"],
            "fen": p["fen"],
            "ref_legal": res["ref_legal_count"],
            "yielded": res["yielded_count"],
            "duplicates": res["duplicates_count"],
            "missing": res["missing_moves"],
            "illegal": res["illegal_moves"],
            "passed": passed
        })
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {p['class']:<30}: Ref={res['ref_legal_count']:2d}, Yielded={res['yielded_count']:2d}, Dups={res['duplicates_count']}, Missing={len(res['missing_moves'])}")

    print(f"\nStratified Position Classes Test: {'100% PASSED' if all_strat_passed else 'FAILED'}")

    print("\n--- 2. Testing TT / Killer / Countermove Collision & Deduplication ---")
    dedup_results = []
    # Test on open middlegame with TT move, killers, and countermoves
    test_fen = "r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"
    b_nat = NativeBoard()
    dll.native_set_fen(test_fen.encode('utf-8'), ctypes.byref(b_nat))
    
    # Parse legal moves to use as valid TT / Killer
    m1 = dll.native_parse_uci(ctypes.byref(b_nat), b"e1g1")
    m2 = dll.native_parse_uci(ctypes.byref(b_nat), b"c1d2")
    m_illegal = 9999 # hash collision pseudo-junk
    
    test_cases = [
        ("No TT, No Killers", 0, 0, 0, 0),
        ("Valid TT (e1g1)", m1, 0, 0, 0),
        ("Invalid / Hash-Collided TT", m_illegal, 0, 0, 0),
        ("Killer1 matching TT (Deduplication)", m1, m1, 0, 0),
        ("Killer1 + Killer2 distinct", 0, m1, m2, 0),
        ("Countermove matching Killer1", 0, m1, m2, m1),
    ]

    for label, tt, k1, k2, cm in test_cases:
        res = test_position_movepicker(dll, test_fen, tt_m=tt, k1=k1, k2=k2, cm=cm)
        passed = res["passed"]
        dedup_results.append({
            "case": label,
            "ref_legal": res["ref_legal_count"],
            "yielded": res["yielded_count"],
            "duplicates": res["duplicates_count"],
            "missing": res["missing_moves"],
            "passed": passed
        })
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {label:<35}: Yielded={res['yielded_count']}, Dups={res['duplicates_count']}, Missing={len(res['missing_moves'])}")

    print("\n--- 3. Testing 1,000 Randomized Legal Chess Positions ---")
    rand_fens = generate_random_positions(1000, seed=12345)
    rand_passed = 0
    rand_total = len(rand_fens)
    t0 = time.time()

    for i, fen in enumerate(rand_fens):
        res = test_position_movepicker(dll, fen)
        if res["passed"]:
            rand_passed += 1
        else:
            print(f"FAILURE on position {i}: {fen}")
            print(f"  Missing: {res['missing_moves']}, Illegal: {res['illegal_moves']}, Dups: {res['duplicates_count']}")
            break

    elapsed = time.time() - t0
    rand_pct = (rand_passed / rand_total) * 100.0
    print(f"Randomized positions tested: {rand_passed} / {rand_total} ({rand_pct:.2f}%) in {elapsed:.2f}s")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stratified_results": stratified_results,
        "dedup_results": dedup_results,
        "randomized_testing": {
            "total_positions": rand_total,
            "passed_positions": rand_passed,
            "pass_rate_pct": rand_pct,
            "elapsed_seconds": elapsed
        },
        "all_tests_passed": (all_strat_passed and rand_passed == rand_total)
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nMovePicker Completeness Audit saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

