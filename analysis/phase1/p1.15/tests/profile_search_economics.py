#!/usr/bin/env python3
"""
profile_search_economics.py
Phase 8: Search Efficiency & Computational Cost Profiler for Milestone P1.15.
Measures:
- Node counts, wall-clock latency, and full-search NPS.
- First-move beta-cutoff frequency (BF1).
- MovePicker staging and scoring overhead.
- SEE call count and SEE execution latency.
- History lookup and update costs.
- Memory footprint breakdown.
- TT hit rates and cutoff rates.
"""

import os
import sys
import json
import time
import ctypes
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "search_economics_raw.json"

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

# Representative diagnostic positions
DIAGNOSTIC_POSITIONS = [
    {"id": "Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "Open_tactical", "fen": "r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"},
    {"id": "Closed_position", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9"},
    {"id": "King_check", "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"},
    {"id": "Pinned_pieces", "fen": "r1b1k2r/ppppbppp/5n2/4q3/8/2N1P3/PPPBBPPP/R2QK2R w KQkq - 2 9"},
    {"id": "En_passant", "fen": "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"},
    {"id": "Heavy_pieces", "fen": "4r1k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1"},
    {"id": "Minor_endgame", "fen": "8/4k3/8/2b5/4N3/8/4K3/8 w - - 0 1"},
    {"id": "Pawn_endgame", "fen": "8/4k3/4p3/4P3/8/8/4K3/8 w - - 0 1"},
    {"id": "G12_crisis", "fen": "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16"}
]

def profile_see_microbenchmark(dll, iterations: int = 100000):
    b = NativeBoard()
    fen = b"r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"
    dll.native_set_fen(fen, ctypes.byref(b))

    moves = (ctypes.c_uint16 * 256)()
    n_moves = dll.native_generate_captures(ctypes.byref(b), moves)

    t0 = time.perf_counter()
    for _ in range(iterations):
        for i in range(n_moves):
            dll.native_see(ctypes.byref(b), moves[i])
    elapsed = time.perf_counter() - t0

    total_see_calls = iterations * n_moves
    ns_per_call = (elapsed / total_see_calls) * 1e9 if total_see_calls > 0 else 0
    return {
        "total_calls": total_see_calls,
        "elapsed_seconds": round(elapsed, 4),
        "ns_per_see_call": round(ns_per_call, 2),
        "calls_per_second": int(total_see_calls / elapsed) if elapsed > 0 else 0
    }

def profile_movepicker_microbenchmark(dll, iterations: int = 50000):
    b = NativeBoard()
    fen = b"r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"
    dll.native_set_fen(fen, ctypes.byref(b))

    out_moves = (ctypes.c_uint16 * 256)()
    out_stages = (ctypes.c_int * 256)()

    t0 = time.perf_counter()
    total_yielded = 0
    for _ in range(iterations):
        cnt = dll.native_test_movepicker(ctypes.byref(b), 0, 0, 6, out_moves, out_stages)
        total_yielded += cnt
    elapsed = time.perf_counter() - t0

    ns_per_init_and_drain = (elapsed / iterations) * 1e9
    ns_per_move_yield = (elapsed / total_yielded) * 1e9 if total_yielded > 0 else 0

    return {
        "iterations": iterations,
        "total_moves_yielded": total_yielded,
        "elapsed_seconds": round(elapsed, 4),
        "ns_per_full_picker": round(ns_per_init_and_drain, 2),
        "ns_per_move_yield": round(ns_per_move_yield, 2)
    }

def profile_search_economics(dll):
    configurations = [
        ("X7_Baseline", "X7", 0, 0),
        ("X19_Frozen", "X19", 0, 0),
        ("X20_AdaptiveC1", "X20", 1, 0),
        ("X20_HistoryH2", "X19", 0, 2),
        ("X20_Integrated", "X20", 1, 2)
    ]

    results = {}
    fixed_depth = 6

    for label, variant, cap_mode, hist_mode in configurations:
        dll.native_apply_search_variant(variant.encode('utf-8'))
        dll.native_set_adaptive_capture_mode(cap_mode)
        dll.native_set_history_mode(hist_mode)
        dll.native_set_exact_search_mode(0)
        dll.native_clear_history_heuristic()
        dll.native_reset_ordering_telemetry()
        dll.native_reset_p11_telemetry()

        tot_nodes = 0
        tot_time = 0.0

        for pos in DIAGNOSTIC_POSITIONS:
            b = NativeBoard()
            dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(b))
            res = NativeSearchResult()

            t0 = time.perf_counter()
            dll.native_search(ctypes.byref(b), fixed_depth, 10.0, ctypes.byref(res))
            elapsed = time.perf_counter() - t0

            tot_nodes += res.nodes
            tot_time += elapsed

        telemetry_arr = (ctypes.c_uint64 * 12)()
        dll.native_get_ordering_telemetry(telemetry_arr)

        tot_cutoffs = telemetry_arr[0]
        m1_cutoffs = telemetry_arr[2]
        tt_cutoffs = telemetry_arr[6]
        k1_cutoffs = telemetry_arr[7]
        k2_cutoffs = telemetry_arr[8]
        hist_cutoffs = telemetry_arr[9]
        cap_cutoffs = telemetry_arr[10]

        bf1_rate = (m1_cutoffs / tot_cutoffs * 100.0) if tot_cutoffs > 0 else 0.0

        results[label] = {
            "fixed_depth": fixed_depth,
            "total_nodes": tot_nodes,
            "total_elapsed_seconds": round(tot_time, 4),
            "nps": int(tot_nodes / tot_time) if tot_time > 0 else 0,
            "total_cutoffs": tot_cutoffs,
            "first_move_cutoffs": m1_cutoffs,
            "bf1_percentage": round(bf1_rate, 2),
            "tt_cutoffs": tt_cutoffs,
            "killer_cutoffs": k1_cutoffs + k2_cutoffs,
            "history_cutoffs": hist_cutoffs,
            "capture_cutoffs": cap_cutoffs
        }
        print(f"[{label}] Nodes={tot_nodes:,}, Time={tot_time:.4f}s, NPS={int(tot_nodes/tot_time):,}, BF1={bf1_rate:.2f}%")

    return results

def get_memory_footprint() -> Dict[str, Any]:
    # Memory footprint analysis based on struct definitions in C++
    tt_entries = 1048576 # 1M entries
    tt_entry_size = 16 # bytes
    tt_total_bytes = tt_entries * tt_entry_size # 16 MB

    hist_entries = 2 * 64 * 64
    hist_bytes = hist_entries * 4 # 32 KB

    conthist1_bytes = 6 * 64 * 6 * 64 * 2 # 288 KB
    conthist2_bytes = 6 * 64 * 6 * 64 * 2 # 288 KB

    pawn_hash_entries = 16384 # 16K entries
    pawn_hash_bytes = pawn_hash_entries * 16 # 256 KB

    total_bytes = tt_total_bytes + hist_bytes + conthist1_bytes + conthist2_bytes + pawn_hash_bytes

    return {
        "transposition_table_mb": round(tt_total_bytes / (1024 * 1024), 2),
        "history_table_kb": round(hist_bytes / 1024, 2),
        "continuation_history_kb": round((conthist1_bytes + conthist2_bytes) / 1024, 2),
        "pawn_hash_table_kb": round(pawn_hash_bytes / 1024, 2),
        "total_static_memory_mb": round(total_bytes / (1024 * 1024), 2)
    }

def main():
    dll = load_engine()
    print("--- Phase 8: Search Efficiency & Economics Benchmark ---")

    see_bench = profile_see_microbenchmark(dll)
    mp_bench = profile_movepicker_microbenchmark(dll)
    search_econ = profile_search_economics(dll)
    mem_footprint = get_memory_footprint()

    output = {
        "see_microbenchmark": see_bench,
        "movepicker_microbenchmark": mp_bench,
        "search_economics": search_econ,
        "memory_footprint": mem_footprint
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nAll search economics benchmarks completed. Raw data saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

