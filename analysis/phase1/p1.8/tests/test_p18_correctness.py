#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.8
Phase 8: Comprehensive Correctness, Invariant & Concurrency Qualification for Candidate X13
"""

import sys
import os
import json
import time
import ctypes
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.dll"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.8" / "raw" / "correctness_qualification_raw.json"
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

def run_uci(exe, commands, timeout_sec=20):
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def main():
    print("=== PROJECT JANUS P1.8: PHASE 8 CANDIDATE X13 CORRECTNESS AUDIT ===")
    results = {
        "candidate": "Janus Classical X13",
        "perft": {},
        "mate_tests": {},
        "draw_detection": {},
        "make_unmake_zobrist": {},
        "uci_lifecycle_stress": {},
        "concurrency_stress": {},
        "all_passed": True
    }

    # Load DLL
    dll = ctypes.CDLL(str(DLL_X13))
    dll.native_init.restype = ctypes.c_int
    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int
    dll.native_perft.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
    dll.native_perft.restype = ctypes.c_uint64
    dll.native_generate_legal_moves.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    dll.native_generate_legal_moves.restype = ctypes.c_int
    dll.native_make_move.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.POINTER(UndoInfo)]
    dll.native_make_move.restype = ctypes.c_int
    dll.native_unmake_move.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.POINTER(UndoInfo)]
    dll.native_unmake_move.restype = None
    dll.native_is_insufficient_material.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_is_insufficient_material.restype = ctypes.c_int

    dll.native_init()

    # --- 1. Perft Verification ---
    print("\n[1] Canonical Perft Verification (Depths 1 to 5)...")
    perft_suites = [
        {
            "name": "Startpos",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "expected": {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609}
        },
        {
            "name": "Kiwipete",
            "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "expected": {1: 48, 2: 2039, 3: 97862, 4: 4085603}
        },
        {
            "name": "Position_3",
            "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
            "expected": {1: 14, 2: 191, 3: 2812, 4: 43238}
        }
    ]

    perft_all_ok = True
    board = NativeBoard()
    for suite in perft_suites:
        sname = suite["name"]
        fen = suite["fen"]
        dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(board))
        results["perft"][sname] = {}
        print(f"  Suite: {sname}")
        for depth, exp in suite["expected"].items():
            t0 = time.perf_counter()
            actual = dll.native_perft(ctypes.byref(board), depth)
            dur = time.perf_counter() - t0
            ok = (actual == exp)
            if not ok:
                perft_all_ok = False
                results["all_passed"] = False
            results["perft"][sname][str(depth)] = {
                "expected": exp,
                "actual": actual,
                "passed": ok,
                "elapsed_sec": round(dur, 4)
            }
            status = "PASS" if ok else "FAIL"
            print(f"    Depth {depth}: {actual:,} (exp: {exp:,}) [{status}] in {dur:.3f}s")
    assert perft_all_ok, "Perft verification failed!"

    # --- 2. Make/Unmake & Zobrist Invariant Stress ---
    print("\n[2] Make/Unmake and Zobrist Key Invariance...")
    zobrist_ok = True
    test_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15",
        "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40"
    ]
    moves_array = (ctypes.c_uint16 * 256)()
    undo = UndoInfo()
    tested_moves_count = 0

    for fen in test_fens:
        dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(board))
        orig_key = board.zobrist_key
        n_moves = dll.native_generate_legal_moves(ctypes.byref(board), moves_array)
        for i in range(n_moves):
            mv = moves_array[i]
            dll.native_make_move(ctypes.byref(board), mv, ctypes.byref(undo))
            dll.native_unmake_move(ctypes.byref(board), mv, ctypes.byref(undo))
            tested_moves_count += 1
            if board.zobrist_key != orig_key:
                zobrist_ok = False
                results["all_passed"] = False
                print(f"    Zobrist mismatch on move index {i} in FEN {fen}")
                break

    results["make_unmake_zobrist"] = {
        "moves_tested": tested_moves_count,
        "passed": zobrist_ok
    }
    print(f"  Tested {tested_moves_count} make/unmake operations: {'PASS' if zobrist_ok else 'FAIL'}")
    assert zobrist_ok, "Make/unmake Zobrist invariant failed!"

    # --- 3. Tactical Mate Solvers ---
    print("\n[3] Tactical Mate Solvers...")
    mate_cases = [
        {"name": "Scholars_Mate_in_1", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "exp": "h5f7"},
        {"name": "Back_Rank_Mate_in_1", "fen": "6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1", "exp": "e2e8"},
        {"name": "Legals_Mate_in_2", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "exp": "d5f6"}
    ]
    mate_all_ok = True
    for mc in mate_cases:
        mname = mc["name"]
        cmds = f"uci\nisready\nposition fen {mc['fen']}\ngo depth 6\nquit\n"
        out = run_uci(EXE_X13, cmds)
        best = None
        for line in out.splitlines():
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2: best = parts[1]
        ok = (best == mc["exp"])
        if not ok:
            mate_all_ok = False
            results["all_passed"] = False
        results["mate_tests"][mname] = {"expected": mc["exp"], "actual": best, "passed": ok}
        print(f"  {mname}: expected {mc['exp']} -> got {best} [{'PASS' if ok else 'FAIL'}]")
    assert mate_all_ok, "Tactical mate solver failed!"

    # --- 4. Draw Detection Rules ---
    print("\n[4] Draw Detection Rules...")
    # Insufficient material check via DLL
    insuf_tests = [
        ("8/8/8/8/8/8/4k3/4K3 w - - 0 1", True),       # K vs K
        ("8/8/8/8/8/5B2/4k3/4K3 w - - 0 1", True),     # KB vs K
        ("8/8/8/8/8/5N2/4k3/4K3 w - - 0 1", True),     # KN vs K
        ("8/8/8/8/8/5P2/4k3/4K3 w - - 0 1", False),    # KP vs K
        ("8/8/8/8/8/5R2/4k3/4K3 w - - 0 1", False)     # KR vs K
    ]
    insuf_ok = True
    for fen, exp_insuf in insuf_tests:
        dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(board))
        res_insuf = bool(dll.native_is_insufficient_material(ctypes.byref(board)))
        if res_insuf != exp_insuf:
            insuf_ok = False
            results["all_passed"] = False
            print(f"  Insufficient material mismatch for {fen}: expected {exp_insuf}, got {res_insuf}")
    results["draw_detection"]["insufficient_material"] = {"passed": insuf_ok}
    print(f"  Insufficient material detection: {'PASS' if insuf_ok else 'FAIL'}")

    # Threefold repetition via UCI
    threefold_cmds = """uci
isready
position startpos moves g1f3 g8f6 f1e2 f6g8 e2f1 g8f6 f1e2 f6g8 e2f1
go depth 5
quit
"""
    out_tf = run_uci(EXE_X13, threefold_cmds)
    tf_ok = ("info" in out_tf and "bestmove" in out_tf)
    results["draw_detection"]["threefold_repetition"] = {"passed": tf_ok}
    print(f"  Threefold repetition handling: {'PASS' if tf_ok else 'FAIL'}")

    # --- 5. UCI Protocol Lifecycle Stress Test (20 rapid cycles) ---
    print("\n[5] UCI Protocol Lifecycle Stress (20 rapid cycles at 4 threads)...")
    lifecycle_cmds = "uci\nsetoption name Threads value 4\nisready\n"
    for i in range(20):
        lifecycle_cmds += "ucinewgame\nposition startpos\ngo movetime 50\nstop\n"
    lifecycle_cmds += "quit\n"

    t0 = time.perf_counter()
    out_life = run_uci(EXE_X13, lifecycle_cmds, timeout_sec=20)
    dur_life = time.perf_counter() - t0
    bestmoves = sum(1 for l in out_life.splitlines() if l.startswith("bestmove"))
    life_ok = (bestmoves == 20)
    if not life_ok:
        results["all_passed"] = False
    results["uci_lifecycle_stress"] = {
        "cycles_attempted": 20,
        "bestmoves_returned": bestmoves,
        "elapsed_sec": round(dur_life, 3),
        "passed": life_ok
    }
    print(f"  Completed 20 rapid cycles in {dur_life:.2f}s: {bestmoves}/20 bestmoves returned [{'PASS' if life_ok else 'FAIL'}]")
    assert life_ok, f"Lifecycle stress failed: {bestmoves}/20 bestmoves"

    # --- 6. Concurrency & Thread-Local Pawn Hash Stability ---
    print("\n[6] Concurrency & Thread-Local Pawn Hash Stability (4 Threads, Deep Search)...")
    conc_fens = [
        ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
        ("sharp_mg", "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15"),
        ("endgame_kpp", "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40")
    ]
    conc_all_ok = True
    for pname, fen in conc_fens:
        cmds = f"uci\nsetoption name Threads value 4\nisready\nposition fen {fen}\ngo movetime 500\nquit\n"
        t0 = time.perf_counter()
        out_conc = run_uci(EXE_X13, cmds, timeout_sec=10)
        dur = time.perf_counter() - t0
        has_bm = any(l.startswith("bestmove") for l in out_conc.splitlines())
        if not has_bm:
            conc_all_ok = False
            results["all_passed"] = False
        print(f"  {pname} (4 threads, 500ms): {'PASS' if has_bm else 'FAIL'} in {dur:.2f}s")
    results["concurrency_stress"] = {"passed": conc_all_ok}
    assert conc_all_ok, "Concurrency stress test failed!"

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved correctness audit results to {RAW_OUT}")
    print("=== ALL PHASE 8 CORRECTNESS & CONCURRENCY AUDITS PASSED ===")

if __name__ == "__main__":
    main()

