#!/usr/bin/env python3
"""
test_adaptive_capture_ordering.py
Phase 4: Adaptive Capture Ordering Investigation for Milestone P1.15.
Tests:
1. Completeness and legality across 19 stratified classes and 1,000 random positions under C0, C1, C2, C3.
2. Classification overhead benchmarking (time per position / move to stage captures).
3. Search tree diagnostics across 20 tactical and endgame positions comparing C0, C1, C2, C3.
4. Game 12 crisis position resolution.
"""

import os
import sys
import json
import time
import random
import ctypes
from pathlib import Path
from typing import Dict, Any, List

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "adaptive_capture_ordering_raw.json"

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

def load_engine():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_search.argtypes = [
        ctypes.POINTER(NativeBoard),
        ctypes.c_int,
        ctypes.c_double,
        ctypes.POINTER(NativeSearchResult)
    ]
    dll.native_search.restype = ctypes.c_int
    return dll

def parse_move_to_uci(dll, m: int) -> str:
    buf = ctypes.create_string_buffer(16)
    dll.native_move_to_uci(m, buf)
    return buf.value.decode('utf-8')

# 19 Stratified Test Positions
STRATIFIED_POSITIONS = [
    {"class": "Starting position", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"class": "Open tactical middlegames", "fen": "r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"},
    {"class": "Closed positions", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9"},
    {"class": "King in check", "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"},
    {"class": "Double check", "fen": "r1b1k2r/pppp1Npp/8/4p3/2Bn4/8/PPPP2PP/RNB1b1KR b kq - 1 9"},
    {"class": "Pinned pieces", "fen": "r1b1k2r/ppppbppp/5n2/4q3/8/2N1P3/PPPBBPPP/R2QK2R w KQkq - 2 9"},
    {"class": "Castling", "fen": "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"},
    {"class": "En passant available", "fen": "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"},
    {"class": "Pawn promotion on board", "fen": "8/4P3/8/8/8/8/k7/4K3 w - - 0 1"},
    {"class": "Underpromotion tactics", "fen": "8/1P6/8/8/8/8/k7/4K3 w - - 0 1"},
    {"class": "Check evasions", "fen": "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"},
    {"class": "Stalemate-adjacent", "fen": "k7/8/1K6/8/8/8/8/8 b - - 0 1"},
    {"class": "Zugzwang positions", "fen": "8/8/p1p5/1p5p/1P5p/8/PPP2K1k/4B3 w - - 0 1"},
    {"class": "Heavy piece endgames", "fen": "4r1k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1"},
    {"class": "Minor piece endgames", "fen": "8/4k3/8/2b5/4N3/8/4K3/8 w - - 0 1"},
    {"class": "Pawn-only endgames", "fen": "8/4k3/4p3/4P3/8/8/4K3/8 w - - 0 1"},
    {"class": "Severely unbalanced material", "fen": "rnbqkbnr/8/8/8/8/8/8/4K3 w kq - 0 1"},
    {"class": "Quiet positions with few captures", "fen": "8/5p2/8/8/8/8/5P2/4K2k w - - 0 1"},
    {"class": "Positions with massive legal branching", "fen": "r1b1kb1r/pppp1ppp/2n5/4p3/2B1n2q/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 6"}
]

# 20 Benchmark Positions for Search Tree Diagnostics (Tactics + Endgames + Game 12)
BENCHMARK_POSITIONS = [
    # Game 12 Inflection Position (Mate Defense)
    {"id": "G12_inflection", "fen": "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16", "type": "crisis"},
    # Tactical Defenses & Near-Even Sacrifices
    {"id": "Tactical_pin_defense", "fen": "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N5/PP2PPPP/R2QKB1R w KQkq - 0 9", "type": "tactical"},
    {"id": "Minor_exchange_center", "fen": "r1bqk2r/pp2bppp/2n5/1Bpp4/3P4/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 8", "type": "tactical"},
    {"id": "Open_file_clash", "fen": "r3k2r/pppq1ppp/2n1bn2/3p4/3P4/2N1BN2/PPPQ1PPP/R3K2R w KQkq - 0 9", "type": "middlegame"},
    {"id": "Complex_middlegame_1", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PNP3/2N1BP2/PP4PP/R2QKB1R w KQ - 1 9", "type": "middlegame"},
    {"id": "Complex_middlegame_2", "fen": "r2q1rk1/1b1nbppp/ppn1p3/2ppP3/3P4/2PB1N2/PP1N1PPP/R1BQR1K1 w - - 2 12", "type": "middlegame"},
    {"id": "Attacking_crisis_1", "fen": "r1b2rk1/pp1n1ppp/2p1p3/q2p2B1/2PP4/P1PBPN2/5PPP/R2Q1RK1 w - - 3 11", "type": "tactical"},
    {"id": "Attacking_crisis_2", "fen": "2r2rk1/1bq1bppp/pp1p1n2/4p3/P1PNP3/1PN1BP2/6PP/2RQR1K1 w - - 0 17", "type": "tactical"},
    # Endgames
    {"id": "Endgame_rook_pawn", "fen": "8/5pk1/4p1p1/3pP2p/r4P1P/PR1R2P1/1P4K1/2r5 w - - 7 38", "type": "endgame"},
    {"id": "Endgame_minor_piece", "fen": "8/5k2/4p1p1/3pP3/2b2P1P/4B1P1/1b4K1/8 w - - 0 42", "type": "endgame"},
    {"id": "Endgame_queen_pawn", "fen": "8/5qk1/4p1p1/3pP3/5P1P/6P1/1Q4K1/8 w - - 0 45", "type": "endgame"},
    {"id": "Endgame_pawn_race", "fen": "8/5k2/4p3/3pP3/5P2/8/4K3/8 w - - 0 50", "type": "endgame"},
    {"id": "Endgame_tactical_break", "fen": "8/2p5/3k4/1p1p4/1P1P4/2K5/8/8 w - - 0 1", "type": "endgame"},
    {"id": "Endgame_bishop_opposite", "fen": "8/4k3/4b3/8/8/4B3/4K3/8 w - - 0 1", "type": "endgame"},
    {"id": "Tactical_queen_sac", "fen": "r1b2rk1/2p2ppp/p7/1p1B4/3P4/2P2Q2/PP1N1PPb/R1B1q2K w - - 1 18", "type": "tactical"},
    {"id": "Defensive_desperado", "fen": "r4rk1/1pp2ppp/p1np4/4p3/2B1P1b1/2NP1N2/PPP2qPP/R2Q3K w - - 0 13", "type": "tactical"},
    {"id": "Counter_sacrifice", "fen": "r1bq1rk1/ppp2ppp/2n5/3p4/3Pn3/2BB1N2/PPP2PPP/R2QK2R w KQ - 0 10", "type": "tactical"},
    {"id": "Check_pressure", "fen": "r1b1k2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6", "type": "tactical"},
    {"id": "Quiet_maneuver", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9", "type": "quiet"},
    {"id": "Starting_pos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "type": "standard"}
]

def generate_random_positions(n: int = 1000, seed: int = 42) -> List[str]:
    random.seed(seed)
    fens = []
    board = chess.Board()
    attempts = 0
    max_attempts = n * 50
    while len(fens) < n and attempts < max_attempts:
        attempts += 1
        board.reset()
        num_plies = random.randint(4, 80)
        for _ in range(num_plies):
            if board.is_game_over():
                break
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(random.choice(moves))
        if not board.is_game_over():
            fen = board.fen()
            if fen not in fens:
                fens.append(fen)
    return fens

def test_completeness_and_legality(dll):
    print("--- Part 1: Exhaustive Completeness & Legality Audit ---")
    modes = [0, 1, 2, 3] # C0, C1, C2, C3
    results = {}

    random_fens = generate_random_positions(n=1000, seed=12345)
    all_positions = [(p["class"], p["fen"]) for p in STRATIFIED_POSITIONS] + [(f"Random_{i}", f) for i, f in enumerate(random_fens)]

    for mode in modes:
        dll.native_set_adaptive_capture_mode(mode)
        total_positions = 0
        total_legal_moves = 0
        total_yielded_moves = 0
        omissions = 0
        duplicates = 0
        illegal_moves = 0

        b = NativeBoard()
        out_moves = (ctypes.c_uint16 * 256)()
        out_stages = (ctypes.c_int * 256)()

        for name, fen in all_positions:
            total_positions += 1
            py_board = chess.Board(fen)
            py_legal = {m.uci() for m in py_board.legal_moves}
            total_legal_moves += len(py_legal)

            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
            count = dll.native_test_movepicker(ctypes.byref(b), 0, 0, 6, out_moves, out_stages)

            yielded_uci = []
            seen = set()
            for i in range(count):
                m_uci = parse_move_to_uci(dll, out_moves[i])
                total_yielded_moves += 1
                if m_uci in seen:
                    duplicates += 1
                seen.add(m_uci)
                yielded_uci.append(m_uci)
                if m_uci not in py_legal:
                    illegal_moves += 1

            for lm in py_legal:
                if lm not in seen:
                    omissions += 1

        results[f"C{mode}"] = {
            "positions_tested": total_positions,
            "total_legal_moves": total_legal_moves,
            "total_yielded_moves": total_yielded_moves,
            "omissions": omissions,
            "duplicates": duplicates,
            "illegal_moves": illegal_moves,
            "perfect_match": (omissions == 0 and duplicates == 0 and illegal_moves == 0)
        }
        print(f"Mode C{mode}: Positions={total_positions}, Legal={total_legal_moves}, Yielded={total_yielded_moves}, Omissions={omissions}, Duplicates={duplicates}, Illegal={illegal_moves}")
    return results

def benchmark_classification_overhead(dll):
    print("--- Part 2: Classification Overhead Benchmarking ---")
    modes = [0, 1, 2, 3]
    b = NativeBoard()
    out_moves = (ctypes.c_uint16 * 256)()
    out_stages = (ctypes.c_int * 256)()

    # Warmup
    dll.native_set_fen(STRATIFIED_POSITIONS[1]["fen"].encode('utf-8'), ctypes.byref(b))
    for _ in range(1000):
        dll.native_test_movepicker(ctypes.byref(b), 0, 0, 6, out_moves, out_stages)

    overhead = {}
    test_positions = [p["fen"] for p in STRATIFIED_POSITIONS]

    for mode in modes:
        dll.native_set_adaptive_capture_mode(mode)
        iterations = 50000
        t0 = time.perf_counter()
        pos_idx = 0
        n_pos = len(test_positions)
        total_moves = 0
        for _ in range(iterations):
            fen = test_positions[pos_idx]
            pos_idx = (pos_idx + 1) % n_pos
            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
            cnt = dll.native_test_movepicker(ctypes.byref(b), 0, 0, 6, out_moves, out_stages)
            total_moves += cnt
        elapsed = time.perf_counter() - t0
        ns_per_pos = (elapsed / iterations) * 1e9
        ns_per_move = (elapsed / total_moves) * 1e9 if total_moves > 0 else 0
        overhead[f"C{mode}"] = {
            "iterations": iterations,
            "elapsed_seconds": elapsed,
            "ns_per_position": round(ns_per_pos, 2),
            "ns_per_move": round(ns_per_move, 2)
        }
        print(f"Mode C{mode}: {iterations} calls in {elapsed:.3f}s ({ns_per_pos:.1f} ns/pos, {ns_per_move:.1f} ns/move)")
    return overhead

def run_search_diagnostics(dll):
    print("--- Part 3: Search Tree Diagnostics on 20 Positions ---")
    modes = [0, 1, 2, 3]
    diagnostics = {}
    fixed_depth = 6

    for mode in modes:
        dll.native_set_adaptive_capture_mode(mode)
        mode_data = []
        total_nodes = 0
        total_time = 0.0

        for item in BENCHMARK_POSITIONS:
            pid = item["id"]
            fen = item["fen"]
            ptype = item["type"]

            b = NativeBoard()
            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
            dll.native_reset_ordering_telemetry()
            dll.native_reset_p11_telemetry()

            res = NativeSearchResult()
            t0 = time.perf_counter()
            dll.native_search(ctypes.byref(b), fixed_depth, 10.0, ctypes.byref(res))
            elapsed = time.perf_counter() - t0

            bm = parse_move_to_uci(dll, res.best_move)
            total_nodes += res.nodes
            total_time += elapsed

            mode_data.append({
                "id": pid,
                "type": ptype,
                "best_move": bm,
                "score": res.score,
                "nodes": res.nodes,
                "elapsed": round(elapsed, 4)
            })

        diagnostics[f"C{mode}"] = {
            "fixed_depth": fixed_depth,
            "total_nodes": total_nodes,
            "total_elapsed_seconds": round(total_time, 4),
            "nps": int(total_nodes / total_time) if total_time > 0 else 0,
            "positions": mode_data
        }
        print(f"Mode C{mode}: Total Nodes={total_nodes:,}, Elapsed={total_time:.3f}s, NPS={int(total_nodes/total_time):,}")
    return diagnostics

def run_game12_crisis_forensics(dll):
    print("--- Part 4: Game 12 Inflection Forensics (Depths 1-8) ---")
    fen = "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16"
    modes = [0, 1, 2, 3]
    crisis_data = {}

    for mode in modes:
        dll.native_set_adaptive_capture_mode(mode)
        mode_depths = []
        for d in range(1, 9):
            b = NativeBoard()
            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
            dll.native_reset_ordering_telemetry()
            res = NativeSearchResult()
            dll.native_search(ctypes.byref(b), d, 10.0, ctypes.byref(res))
            bm = parse_move_to_uci(dll, res.best_move)
            mode_depths.append({
                "depth": d,
                "best_move": bm,
                "score": res.score,
                "nodes": res.nodes,
                "elapsed": round(res.elapsed_seconds, 4)
            })
            print(f"Mode C{mode} Depth {d}: bestmove={bm}, score={res.score}, nodes={res.nodes}")
        crisis_data[f"C{mode}"] = mode_depths
    return crisis_data

def main():
    dll = load_engine()

    completeness = test_completeness_and_legality(dll)
    overhead = benchmark_classification_overhead(dll)
    diagnostics = run_search_diagnostics(dll)
    g12_crisis = run_game12_crisis_forensics(dll)

    output = {
        "completeness_and_legality": completeness,
        "classification_overhead": overhead,
        "search_diagnostics_d6": diagnostics,
        "game12_crisis_forensics": g12_crisis
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nAll tests completed successfully. Raw data saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

