#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 7 Test Suite: Correctness, Perft Qualification, & C1 Parity Verification.
"""

import os
import sys
import json
import time
import ctypes
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXE_X_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
DLL_X_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
EXE_C1_PATH = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
SUITE_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.1" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Perft ground truth references
PERFT_TESTS = [
    {
        "id": "PERFT_01_STARTPOS",
        "name": "Standard Initial Position",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "depth": 5,
        "expected": 4865609
    },
    {
        "id": "PERFT_02_KIWIPETE",
        "name": "Kiwipete (Complex Tactically & Castling/EP)",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "depth": 4,
        "expected": 4085603
    },
    {
        "id": "PERFT_03_POSITION3",
        "name": "Position 3 (Pawn Endgame & Pins)",
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "depth": 5,
        "expected": 674624
    },
    {
        "id": "PERFT_04_POSITION4",
        "name": "Position 4 (Promotions & Discovered Checks)",
        "fen": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "depth": 4,
        "expected": 422333
    },
    {
        "id": "PERFT_05_POSITION5",
        "name": "Position 5 (Tactical King Hunting)",
        "fen": "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "depth": 4,
        "expected": 2103487
    },
    {
        "id": "PERFT_06_POSITION6",
        "name": "Position 6 (Symmetric Middlegame)",
        "fen": "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
        "depth": 4,
        "expected": 3894594
    }
]

# Mate test positions
MATE_TESTS = [
    {
        "name": "Mate in 1 (Corner King Rook Mate)",
        "fen": "k7/8/1K6/8/8/8/8/7R w - - 0 1",
        "expected_move": "h1h8",
        "expected_score_min": 28990
    },
    {
        "name": "Mate in 1 (Back Rank)",
        "fen": "6k1/5ppp/8/8/8/8/8/3R2K1 w - - 0 1",
        "expected_move": "d1d8",
        "expected_score_min": 28990
    },
    {
        "name": "Mate in 2 (Legal's Mate Trap)",
        "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9",
        "expected_move": "d5f6",
        "expected_score_min": 28990
    }
]


def run_perft_suite() -> dict:
    print("=" * 80)
    print("TEST 1: COMPLETE PERFT SUITE ON JANUS CLASSICAL X DLL")
    print("=" * 80)

    # Load DLL
    dll = ctypes.CDLL(str(DLL_X_PATH))
    
    # Define C types
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

    dll.native_init.restype = ctypes.c_int
    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int
    dll.native_perft.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
    dll.native_perft.restype = ctypes.c_uint64

    dll.native_init()
    b = NativeBoard()
    all_passed = True
    perft_results = []

    for test in PERFT_TESTS:
        dll.native_set_fen(test["fen"].encode("ascii"), ctypes.byref(b))
        t0 = time.perf_counter()
        count = dll.native_perft(ctypes.byref(b), test["depth"])
        dur = time.perf_counter() - t0
        passed = (count == test["expected"])
        if not passed: all_passed = False
        nps = int(count / max(dur, 0.001))
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test['name']:<42} (d={test['depth']}): {count:,} / {test['expected']:,} ({dur:.3f}s, {nps:,} nps)")
        perft_results.append({
            "id": test["id"],
            "name": test["name"],
            "depth": test["depth"],
            "result": count,
            "expected": test["expected"],
            "passed": passed,
            "elapsed_sec": round(dur, 4),
            "nps": nps
        })

    print(f"\nPerft Suite Qualification: {'ALL PASSED (6/6)' if all_passed else 'FAILED'}")
    return {"passed": all_passed, "tests": perft_results}


def run_c1_parity_check() -> dict:
    print("\n" + "=" * 80)
    print("TEST 2: C1 BASELINE BIT-EXACT PARITY CHECK (C1 VS X0)")
    print("=" * 80)

    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)

    # Check 15 diverse positions at depth 5
    sample = positions[:15]
    exact_matches = 0
    parity_records = []

    for pos in sample:
        # 1. C1
        p_c1 = subprocess.Popen([str(EXE_C1_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        out_c1, _ = p_c1.communicate(f"uci\nisready\nposition fen {pos['fen']}\ngo depth 5\nquit\n", timeout=10)
        c1_bm, c1_nodes, c1_score = None, 0, 0
        for l in out_c1.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: c1_nodes = int(parts[parts.index("nodes")+1])
                if "cp" in parts: c1_score = int(parts[parts.index("cp")+1])
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: c1_bm = parts[1]

        # 2. Classical X (Variant X0)
        p_x0 = subprocess.Popen([str(EXE_X_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        out_x0, _ = p_x0.communicate(f"uci\nisready\nsetoption name UCI_Variant value X0\nposition fen {pos['fen']}\ngo depth 5\nquit\n", timeout=10)
        x0_bm, x0_nodes, x0_score = None, 0, 0
        for l in out_x0.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: x0_nodes = int(parts[parts.index("nodes")+1])
                if "cp" in parts: x0_score = int(parts[parts.index("cp")+1])
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: x0_bm = parts[1]

        matched = (c1_bm == x0_bm) and (c1_nodes == x0_nodes) and (c1_score == x0_score)
        if matched: exact_matches += 1
        status = "MATCH" if matched else "DIFF"
        print(f"  [{status}] {pos['id']:<8} C1: ({c1_bm}, {c1_score}cp, {c1_nodes}n) | X0: ({x0_bm}, {x0_score}cp, {x0_nodes}n)")
        parity_records.append({
            "id": pos["id"],
            "c1": {"bestmove": c1_bm, "score": c1_score, "nodes": c1_nodes},
            "x0": {"bestmove": x0_bm, "score": x0_score, "nodes": x0_nodes},
            "matched": matched
        })

    print(f"\nC1 vs X0 Bit-Exact Parity: {exact_matches} / {len(sample)} ({round(exact_matches/len(sample)*100, 1)}%)")
    return {"exact_matches": exact_matches, "total": len(sample), "records": parity_records}


def run_mate_and_legality_test() -> dict:
    print("\n" + "=" * 80)
    print("TEST 3: CHECKMATE RESOLUTION & MOVE LEGALITY ON X6")
    print("=" * 80)

    mate_results = []
    all_passed = True
    for t in MATE_TESTS:
        p = subprocess.Popen([str(EXE_X_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value X6\nposition fen {t['fen']}\ngo depth 5\nquit\n"
        out, _ = p.communicate(cmds, timeout=10)
        bm, score = None, 0
        for l in out.splitlines():
            if l.startswith("info") and "score" in l:
                parts = l.split()
                if "cp" in parts: score = int(parts[parts.index("cp")+1])
                elif "mate" in parts: score = 32000 - int(parts[parts.index("mate")+1]) * 100
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: bm = parts[1]

        passed = (bm == t["expected_move"]) and (score >= t["expected_score_min"])
        if not passed: all_passed = False
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {t['name']:<35}: Move {bm} (exp: {t['expected_move']}), Score {score}")
        mate_results.append({
            "name": t["name"],
            "bestmove": bm,
            "expected_move": t["expected_move"],
            "score": score,
            "passed": passed
        })

    print(f"\nMate & Legality Qualification: {'ALL PASSED' if all_passed else 'FAILED'}")
    return {"passed": all_passed, "tests": mate_results}


def main():
    perft_res = run_perft_suite()
    parity_res = run_c1_parity_check()
    mate_res = run_mate_and_legality_test()

    out_file = RAW_DIR / "search_correctness_raw.json"
    full_output = {
        "perft": perft_res,
        "c1_parity": parity_res,
        "mate_and_legality": mate_res
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"\nWrote Correctness qualification raw data to: {out_file}")


if __name__ == "__main__":
    main()
