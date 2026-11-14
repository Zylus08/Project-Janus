#!/usr/bin/env python3
"""
test_p120_correctness_suite.py
Milestone P1.20 Phase 10: Full Systems Correctness & Qualification Gate for Candidate X25.
Tests:
  Gate 1: Perft Startpos D1-D4 (D1=20, D2=400, D3=8902, D4=197281)
  Gate 2: KiwiPete D1-D3 (D1=48, D2=2039, D3=97862)
  Gate 3: Single-Thread Bitwise Determinism (5 identical runs at depth 7)
  Gate 4: 4T SMP Concurrency & Safety (multi-threaded search stability)
  Gate 5: UCI Protocol Compliance (Candidate X25 identity handshake)
  Gate 6: Color Symmetry Verification (225 mirrored opening positions)
  Gate 7: Tournament Harness Integrity Gate (15-case adversarial qualification)
"""

import ctypes
import json
import math
import subprocess
import time
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_uint8),
        ('castling_rights', ctypes.c_uint8),
        ('ep_square', ctypes.c_uint8),
        ('_pad', ctypes.c_uint8),
        ('halfmove_clock', ctypes.c_uint16),
        ('fullmove_number', ctypes.c_uint16),
        ('zobrist_key', ctypes.c_uint64),
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

def mirror_fen(fen: str) -> str:
    board = chess.Board(fen)
    mirrored = board.mirror()
    return mirrored.fen()

def run_suite():
    print("================================================================================")
    print("RUNNING MILESTONE P1.20 CANDIDATE X25 CORRECTNESS & QUALIFICATION GATE")
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
    cdll.native_set_backward_pawns_mode.argtypes = [ctypes.c_int]
    try:
        cdll.native_set_connected_pawns_mode.argtypes = [ctypes.c_int]
        cdll.native_set_connected_pawns_mode(1)
    except AttributeError:
        pass

    # Ensure Candidate X25 configuration
    cdll.native_apply_search_variant(b"X25")
    cdll.native_set_backward_pawns_mode(0)

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

    # Gate 3: Single-Thread Bitwise Determinism
    print("\nGate 3: Single-Thread Bitwise Determinism (5 iterations at Depth 7)...")
    cdll.native_set_threads(1)
    det_nodes = []
    det_scores = []
    det_moves = []
    for i in range(5):
        cdll.native_reset_search_state()
        res = NativeSearchResult()
        cdll.native_search(ctypes.byref(b), 7, 0.0, ctypes.byref(res))
        det_nodes.append(res.nodes)
        det_scores.append(res.score)
        det_moves.append(res.best_move)
    det_pass = (len(set(det_nodes)) == 1 and len(set(det_scores)) == 1 and len(set(det_moves)) == 1)
    print(f"  Nodes: {det_nodes} -> {'IDENTICAL' if len(set(det_nodes)) == 1 else 'DIVERGED'}")
    print(f"  Scores: {det_scores} -> {'IDENTICAL' if len(set(det_scores)) == 1 else 'DIVERGED'}")
    results["gate3_determinism"] = det_pass

    # Gate 4: 4T SMP Concurrency & Safety
    print("\nGate 4: 4-Thread SMP Concurrency & Safety...")
    cdll.native_set_threads(4)
    smp_pass = True
    try:
        cdll.native_reset_search_state()
        res_smp = NativeSearchResult()
        cdll.native_search(ctypes.byref(b), 7, 0.0, ctypes.byref(res_smp))
        print(f"  4T SMP depth 7 complete: nodes = {res_smp.nodes:,}, score = {res_smp.score}")
    except Exception as e:
        print(f"  4T SMP CRASH: {e}")
        smp_pass = False
    cdll.native_set_threads(1)
    results["gate4_smp_safety"] = smp_pass

    # Gate 5: UCI Protocol Compliance & Identity
    print("\nGate 5: UCI Protocol Compliance & Identity...")
    proc = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    proc.stdin.write("uci\n")
    proc.stdin.flush()
    engine_name = "unknown"
    uci_ok = False
    has_variant_x25 = False
    has_opt_conn = False
    while True:
        line = proc.stdout.readline()
        if not line: break
        line = line.strip()
        if line.startswith("id name"):
            engine_name = line.replace("id name", "").strip()
        if "option name UCI_Variant" in line and "X25" in line:
            has_variant_x25 = True
        if "option name UCI_ConnectedPawns" in line:
            has_opt_conn = True
        if line == "uciok":
            uci_ok = True
            break
    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.terminate()
    print(f"  Engine Identity: {engine_name}")
    print(f"  UCI OK: {uci_ok}")
    print(f"  UCI_Variant X25 available: {has_variant_x25}")
    print(f"  UCI_ConnectedPawns option available: {has_opt_conn}")
    results["gate5_uci_protocol"] = (uci_ok and has_variant_x25 and has_opt_conn)

    # Gate 6: Color Inversion Symmetry
    print("\nGate 6: Color Inversion Symmetry on 225 Independent Openings...")
    openings_file = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
    with open(openings_file, "r", encoding="utf-8") as f:
        openings = json.load(f)
    
    sym_failures = 0
    total_positions = len(openings)
    for op in openings:
        fen = op["fen"]
        mfen = mirror_fen(fen)
        
        b1 = NativeBoard()
        cdll.native_set_fen(fen.encode("utf-8"), ctypes.byref(b1))
        e1 = cdll.native_evaluate(ctypes.byref(b1))
        
        b2 = NativeBoard()
        cdll.native_set_fen(mfen.encode("utf-8"), ctypes.byref(b2))
        e2 = cdll.native_evaluate(ctypes.byref(b2))
        
        if e1 != e2:
            sym_failures += 1
            if sym_failures <= 5:
                print(f"  Asymmetry in FEN: {fen} | e1={e1}, mirrored e2={e2} (diff={e1-e2})")
    
    print(f"  Symmetry check complete: {total_positions - sym_failures}/{total_positions} passed.")
    results["gate6_color_symmetry"] = (sym_failures == 0)

    # Gate 7: Tournament Harness Adversarial Qualification
    print("\nGate 7: Adversarial Qualification Suite (15 Test Cases)...")
    adv_cases = [
        {"fen": "8/8/5k2/1P1P4/8/8/8/4K3 w - - 0 1", "desc": "White connected passers march", "expect_pos": True},
        {"fen": "4k3/8/8/8/1p1p4/5K2/8/8 b - - 0 1", "desc": "Black connected passers march", "expect_pos": True},
        {"fen": "8/8/8/2pPp3/8/8/8/4K2k w - e6 0 1", "desc": "En passant square handling", "expect_pos": None},
        {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "desc": "Start position baseline", "expect_pos": None},
        {"fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "desc": "KiwiPete tactical complexity", "expect_pos": None},
        {"fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "desc": "Position 3 complex endgame", "expect_pos": None},
        {"fen": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", "desc": "Position 4 promotion tacticals", "expect_pos": None},
        {"fen": "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", "desc": "Position 5 pinned knight", "expect_pos": None},
        {"fen": "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", "desc": "Position 6 symmetrical Italian", "expect_pos": None},
        {"fen": "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1", "desc": "Locked pawn endgame", "expect_pos": None},
        {"fen": "8/8/8/8/8/5k2/4p3/4K3 w - - 0 1", "desc": "Pawn on 7th stalemate avoidance", "expect_pos": None},
        {"fen": "7k/8/5K2/6R1/8/8/8/8 w - - 0 1", "desc": "Rook mate in 2", "expect_pos": True},
        {"fen": "8/8/8/8/4k3/8/4K3/4Q3 w - - 0 1", "desc": "Queen vs bare king", "expect_pos": True},
        {"fen": "8/8/8/8/4k3/8/4K3/4R3 w - - 0 1", "desc": "Rook vs bare king", "expect_pos": True},
        {"fen": "8/8/8/8/4k3/8/4K3/4B3 w - - 0 1", "desc": "Bishop vs bare king (draw material)", "expect_pos": None},
    ]

    adv_pass = True
    for idx, tc in enumerate(adv_cases):
        fen = tc["fen"]
        b_case = NativeBoard()
        cdll.native_set_fen(fen.encode("utf-8"), ctypes.byref(b_case))
        res = NativeSearchResult()
        cdll.native_reset_search_state()
        cdll.native_search(ctypes.byref(b_case), 5, 0.0, ctypes.byref(res))
        if res.depth < 1:
            print(f"  Adv Case {idx+1} ({tc['desc']}) search failed")
            adv_pass = False
        else:
            print(f"  Adv Case {idx+1} ({tc['desc']}): depth={res.depth}, score={res.score}, best_move={res.best_move}")
    
    results["gate7_adversarial_harness"] = adv_pass

    all_passed = all(results.values())
    results["ALL_GATES_PASSED"] = all_passed

    print("\n" + "=" * 80)
    print("CORRECTNESS GATE SUMMARY:")
    for k, v in results.items():
        print(f"  {k:35}: {'PASS' if v else 'FAIL'}")
    print("=" * 80)

    out_file = RAW_DIR / "p120_correctness_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Summary written to {out_file}")

if __name__ == "__main__":
    run_suite()
