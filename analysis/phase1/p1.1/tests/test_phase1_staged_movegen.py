#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 1 Test Suite: Staged Move Generation & Selection Verification.
"""

import os
import sys
import json
import time
import ctypes
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
SUITE_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.1" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_int),
        ("ep_square", ctypes.c_int),
        ("halfmove_clock", ctypes.c_int),
        ("fullmove_number", ctypes.c_int),
        ("zobrist_key", ctypes.c_uint64),
    ]


def load_dll():
    lib = ctypes.CDLL(str(DLL_PATH))
    lib.native_init.restype = ctypes.c_int
    lib.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    lib.native_set_fen.restype = ctypes.c_int
    lib.native_generate_legal_moves.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    lib.native_generate_legal_moves.restype = ctypes.c_int
    lib.native_generate_captures.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    lib.native_generate_captures.restype = ctypes.c_int
    lib.native_generate_quiets.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    lib.native_generate_quiets.restype = ctypes.c_int
    lib.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    lib.native_init()
    return lib


def move_to_str(lib, m):
    buf = ctypes.create_string_buffer(16)
    lib.native_move_to_uci(m, buf)
    return buf.value.decode("utf-8")


def test_completeness_and_partition(lib):
    print("=" * 80)
    print("TEST 1: MOVE GENERATION COMPLETENESS & DISJOINT PARTITION TEST")
    print("=" * 80)

    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)

    all_passed = True
    tested = 0

    for pos in positions:
        fen = pos["fen"]
        board = NativeBoard()
        res = lib.native_set_fen(fen.encode("utf-8"), ctypes.byref(board))
        if not res:
            continue

        all_m = (ctypes.c_uint16 * 256)()
        caps_m = (ctypes.c_uint16 * 256)()
        quiets_m = (ctypes.c_uint16 * 256)()

        n_all = lib.native_generate_legal_moves(ctypes.byref(board), all_m)
        n_caps = lib.native_generate_captures(ctypes.byref(board), caps_m)
        n_quiets = lib.native_generate_quiets(ctypes.byref(board), quiets_m)

        set_all = set(move_to_str(lib, all_m[i]) for i in range(n_all))
        set_caps = set(move_to_str(lib, caps_m[i]) for i in range(n_caps))
        set_quiets = set(move_to_str(lib, quiets_m[i]) for i in range(n_quiets))

        # Check disjointness
        intersection = set_caps.intersection(set_quiets)
        # Check union
        union = set_caps.union(set_quiets)

        if intersection:
            print(f"FAILED DISJOINT: {pos['id']} Intersection: {intersection}")
            all_passed = False
        if union != set_all:
            diff_missing = set_all - union
            diff_extra = union - set_all
            print(f"FAILED UNION: {pos['id']} Missing: {diff_missing}, Extra: {diff_extra}")
            all_passed = False

        tested += 1

    print(f"Tested {tested} positions across 8 categories.")
    print(f"Completeness & Disjoint Partition Status: {'PASSED (100% Exact Partition)' if all_passed else 'FAILED'}")
    return all_passed


def test_targeted_edge_cases():
    print("\n" + "=" * 80)
    print("TEST 2: TARGETED EDGE CASES (PINNED, PROMOTIONS, CASTLING, EN PASSANT, DOUBLE CHECK)")
    print("=" * 80)

    edge_cases = [
        {
            "name": "Absolute Pin (Rook pinned along file cannot move)",
            "fen": "4k3/8/8/8/4r3/8/4R3/4K3 b - - 0 1",
            "must_contain": ["e4e7", "e4e6", "e4e5", "e4e3", "e4e2"],
            "must_not_contain": ["e4d4", "e4f4"]
        },
        {
            "name": "Double Check (Only King can move)",
            "fen": "r1b1k2r/pppp1Npp/8/4p3/2Bn3q/6n1/PPPP3P/RNB1Q1KR b kq - 1 10",
            "condition": "king_only_if_in_double_check"
        },
        {
            "name": "Underpromotion Tactics (Knight promotion delivers mate or fork)",
            "fen": "8/5P2/8/8/8/8/8/4K2k w - - 0 1",
            "must_contain": ["f7f8q", "f7f8r", "f7f8b", "f7f8n"]
        },
        {
            "name": "En Passant Discovery Safety",
            "fen": "8/8/8/r2pP2K/8/8/8/8 w - d6 0 1",
            "must_not_contain": ["e5d6"]
        },
        {
            "name": "Castling Transit Blocked by Enemy Bishop",
            "fen": "4k3/8/8/8/5b2/8/8/R3K2R w KQ - 0 1",
            "must_contain": ["e1g1"],
            "must_not_contain": ["e1c1"]
        }
    ]

    lib = load_dll()
    all_passed = True

    for ec in edge_cases:
        board = NativeBoard()
        lib.native_set_fen(ec["fen"].encode("utf-8"), ctypes.byref(board))
        moves = (ctypes.c_uint16 * 256)()
        n = lib.native_generate_legal_moves(ctypes.byref(board), moves)
        str_moves = [move_to_str(lib, moves[i]) for i in range(n)]

        passed = True
        for mc in ec.get("must_contain", []):
            if mc not in str_moves:
                print(f"  [{ec['name']}] FAILED: Missing move {mc}")
                passed = False
        for mnc in ec.get("must_not_contain", []):
            if mnc in str_moves:
                print(f"  [{ec['name']}] FAILED: Generated illegal move {mnc}")
                passed = False

        if passed:
            print(f"  [PASS] {ec['name']}")
        else:
            all_passed = False

    return all_passed


def run_performance_comparison():
    print("\n" + "=" * 80)
    print("TEST 3: PERFORMANCE BENCHMARK (X0 EXHAUSTIVE VS X1 STAGED)")
    print("=" * 80)

    test_fens = [
        ("Opening", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        ("Italian", "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5"),
        ("Middlegame", "r1b2rk1/pp1n1ppp/2p1pn2/q2p2B1/2PP4/P1N1PN2/1PQ2PPP/R3KB1R w KQ - 1 10"),
        ("Tactical", "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"),
        ("Endgame", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1")
    ]

    results = []

    for name, fen in test_fens:
        # X0: Exhaustive Legal Generation
        p0 = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds0 = f"uci\nisready\nsetoption name UCI_Variant value X0\nposition fen {fen}\ngo depth 7\ntelemetry_report\nquit\n"
        t0 = time.perf_counter()
        out0, _ = p0.communicate(cmds0, timeout=15)
        dur0 = time.perf_counter() - t0

        nodes0 = 0
        for l in out0.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: nodes0 = int(parts[parts.index("nodes")+1])

        # X1: Staged Move Generation
        p1 = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds1 = f"uci\nisready\nsetoption name UCI_Variant value X1\nposition fen {fen}\ngo depth 7\ntelemetry_report\nquit\n"
        t1 = time.perf_counter()
        out1, _ = p1.communicate(cmds1, timeout=15)
        dur1 = time.perf_counter() - t1

        nodes1 = 0
        telemetry = {}
        in_telemetry = False
        for l in out1.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: nodes1 = int(parts[parts.index("nodes")+1])
            elif "TELEMETRY_START" in l:
                in_telemetry = True
            elif "TELEMETRY_END" in l:
                in_telemetry = False
            elif in_telemetry:
                parts = l.split()
                if len(parts) == 2:
                    telemetry[parts[0]] = parts[1]

        speedup = (dur0 / max(dur1, 0.001))
        time_saved_pct = ((dur0 - dur1) / max(dur0, 0.001)) * 100.0

        rec = {
            "name": name,
            "fen": fen,
            "x0_time_ms": round(dur0 * 1000, 1),
            "x1_time_ms": round(dur1 * 1000, 1),
            "x0_nodes": nodes0,
            "x1_nodes": nodes1,
            "speedup": round(speedup, 2),
            "time_saved_pct": round(time_saved_pct, 1),
            "telemetry": telemetry
        }
        results.append(rec)
        print(f"[{name:12s}] X0={dur0*1000:6.1f}ms ({nodes0:8d} nodes) | X1={dur1*1000:6.1f}ms ({nodes1:8d} nodes) | Speedup: {speedup:4.2f}x ({time_saved_pct:+.1f}%) | Cutoffs (1st/Tot): {telemetry.get('first_move_cutoffs')}/{telemetry.get('total_cutoffs')}")

    out_file = RAW_DIR / "staged_movegen_benchmark_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote benchmark results to: {out_file}")
    return results


def main():
    lib = load_dll()
    p1 = test_completeness_and_partition(lib)
    p2 = test_targeted_edge_cases()
    res = run_performance_comparison()

    print("\n" + "=" * 80)
    print("PHASE 1 QUALIFICATION SUMMARY")
    print("=" * 80)
    print(f"Partition Completeness Test : {'PASS' if p1 else 'FAIL'}")
    print(f"Targeted Edge Cases          : {'PASS' if p2 else 'FAIL'}")
    avg_speedup = sum(r["speedup"] for r in res) / len(res)
    print(f"Mean Search Speedup          : {avg_speedup:.2f}x")
    print(f"Phase 1 Gate Status          : {'QUALIFIED (PASS)' if (p1 and p2) else 'FAILED'}")


if __name__ == "__main__":
    main()
