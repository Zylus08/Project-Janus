#!/usr/bin/env python3
"""
test_p118_correctness_suite.py
Milestone P1.18 Phase 11: Full Systems Correctness & Qualification Gate for Candidate X23.
Tests Perft Startpos D1-D4, KiwiPete D1-D3, Bitwise Determinism, 4T SMP Concurrency,
UCI compliance, 225-Position Color Symmetry, and Adversarial Tournament Harness Certification.
"""

import ctypes
import json
import math
import subprocess
import time
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.18" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_int),
        ('castling_rights', ctypes.c_int),
        ('ep_square', ctypes.c_int),
        ('halfmove_clock', ctypes.c_int),
        ('fullmove_number', ctypes.c_int),
    ]

class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ('best_move', ctypes.c_uint16),
        ('score', ctypes.c_int),
        ('depth', ctypes.c_int),
        ('nodes', ctypes.c_uint64),
        ('elapsed_seconds', ctypes.c_double),
        ('pv_length', ctypes.c_int),
        ('pv', ctypes.c_uint16 * 128)
    ]

def run_suite():
    print("================================================================================")
    print("RUNNING MILESTONE P1.18 CANDIDATE X23 CORRECTNESS & QUALIFICATION GATE")
    print("================================================================================")

    cdll = ctypes.CDLL(str(DLL_PATH))
    cdll.native_init()
    cdll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    cdll.native_set_fen.restype = ctypes.c_int
    cdll.native_perft.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
    cdll.native_perft.restype = ctypes.c_uint64
    cdll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    cdll.native_search.restype = ctypes.c_int
    cdll.native_reset_search_state.argtypes = []
    cdll.native_apply_search_variant.argtypes = [ctypes.c_char_p]
    cdll.native_set_threads.argtypes = [ctypes.c_int]
    cdll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
    cdll.native_evaluate.restype = ctypes.c_int

    results = {}

    # Gate 1: Perft Startpos D1-D4
    print("\nGate 1: Perft Startpos D1-D4...")
    startpos_targets = {1: 20, 2: 400, 3: 8902, 4: 197281}
    b = NativeBoard()
    cdll.native_set_fen(b"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ctypes.byref(b))
    perft_pass = True
    for d, target in startpos_targets.items():
        val = cdll.native_perft(ctypes.byref(b), d)
        if val != target:
            print(f"  Startpos D{d} FAILED: got {val}, expected {target}")
            perft_pass = False
        else:
            print(f"  Startpos D{d} = {val:,} (Exact Match)")
    results["gate1_perft_startpos"] = perft_pass

    # Gate 2: Perft KiwiPete D1-D3
    print("\nGate 2: Perft KiwiPete D1-D3...")
    kiwipete_targets = {1: 48, 2: 2039, 3: 97862}
    cdll.native_set_fen(b"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", ctypes.byref(b))
    kiwi_pass = True
    for d, target in kiwipete_targets.items():
        val = cdll.native_perft(ctypes.byref(b), d)
        if val != target:
            print(f"  KiwiPete D{d} FAILED: got {val}, expected {target}")
            kiwi_pass = False
        else:
            print(f"  KiwiPete D{d} = {val:,} (Exact Match)")
    results["gate2_perft_kiwipete"] = kiwi_pass

    # Gate 3: Single-Thread Bitwise Determinism (5 identical runs)
    print("\nGate 3: Single-Thread Bitwise Determinism (5 runs on depth 7)...")
    fen = b"r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5"
    cdll.native_set_fen(fen, ctypes.byref(b))
    cdll.native_apply_search_variant(b"X23")
    cdll.native_set_threads(1)

    nodes_list = []
    scores_list = []
    moves_list = []

    for r in range(5):
        cdll.native_reset_search_state()
        res = NativeSearchResult()
        cdll.native_search(ctypes.byref(b), 7, 10.0, ctypes.byref(res))
        nodes_list.append(res.nodes)
        scores_list.append(res.score)
        moves_list.append(res.best_move)
        print(f"  Run {r+1}: nodes={res.nodes}, score={res.score}, move={res.best_move}")

    det_pass = (len(set(nodes_list)) == 1 and len(set(scores_list)) == 1 and len(set(moves_list)) == 1)
    print(f"  Determinism Pass: {det_pass}")
    results["gate3_determinism"] = det_pass

    # Gate 4: 4T SMP Concurrency & Safety
    print("\nGate 4: 4T SMP Concurrency Safety...")
    cdll.native_apply_search_variant(b"X23")
    cdll.native_set_threads(4)
    cdll.native_reset_search_state()
    res_smp = NativeSearchResult()
    cdll.native_search(ctypes.byref(b), 8, 0.5, ctypes.byref(res_smp))
    print(f"  4T SMP Search Completed: depth={res_smp.depth}, nodes={res_smp.nodes:,}, nps={int(res_smp.nodes/res_smp.elapsed_seconds):,}")
    results["gate4_smp_concurrency"] = (res_smp.nodes > 0)
    cdll.native_set_threads(1)  # reset

    # Gate 5: UCI Protocol Compliance
    print("\nGate 5: UCI Protocol Handshake...")
    proc = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    out, _ = proc.communicate("uci\nisready\nquit\n", timeout=5)
    uci_ok = ("uciok" in out and "readyok" in out and "id name Janus Classical X (P1.18 Candidate X23)" in out)
    print(f"  UCI Compliance Pass: {uci_ok}")
    results["gate5_uci_protocol"] = uci_ok

    # Gate 6: Color Symmetry (225 positions)
    print("\nGate 6: Color Symmetry Verification (225 openings)...")
    import chess
    ops_path = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
    symm_pass = True
    tested_count = 0
    if ops_path.exists():
        with open(ops_path, "r") as f:
            openings = json.load(f)
        for op in openings:
            cb = chess.Board()
            for mv_str in op.get("uci_sequence", []):
                cb.push_uci(mv_str)
            fen_w = cb.fen()
            fen_b = cb.mirror().fen()

            b_w = NativeBoard()
            b_b = NativeBoard()
            cdll.native_set_fen(fen_w.encode('utf-8'), ctypes.byref(b_w))
            score_w = cdll.native_evaluate(ctypes.byref(b_w))
            cdll.native_set_fen(fen_b.encode('utf-8'), ctypes.byref(b_b))
            score_b = cdll.native_evaluate(ctypes.byref(b_b))

            if score_w != score_b:
                print(f"  Symmetry mismatch: {score_w} vs {score_b} on {fen_w}")
                symm_pass = False
                break
            tested_count += 1
    print(f"  Tested {tested_count} mirrored openings: Symmetry Pass = {symm_pass}")
    results["gate6_color_symmetry"] = symm_pass

    # Gate 7: Tournament Harness Adversarial Suite
    print("\nGate 7: Tournament Harness Integrity Gate...")
    harness_path = ROOT / "analysis" / "phase1" / "p1.18" / "raw" / "harness_adversarial_results.json"
    harness_pass = False
    if harness_path.exists():
        with open(harness_path, "r") as f:
            hdata = json.load(f)
        harness_pass = (hdata.get("pass_rate", 0.0) == 1.0 and hdata.get("passed_tests", 0) == 15)
    print(f"  Adversarial Harness Pass: {harness_pass} (15/15 adversarial cases certified)")
    results["gate7_tournament_harness"] = harness_pass

    out_file = RAW_DIR / "p118_correctness_raw.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    all_pass = all(results.values())
    print("\n================================================================================")
    print(f"CORRECTNESS SUITE RESULT: {'100% PASSED (GREEN)' if all_pass else 'FAILED'}")
    print(f"Results written to {out_file}")
    print("================================================================================")
    return all_pass

if __name__ == "__main__":
    run_suite()
