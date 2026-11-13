#!/usr/bin/env python3
"""
test_history_normalization.py
Phase 5: History Score Reliability Investigation for Milestone P1.15.
Tests:
1. Reconstruction and validation of the P1.14 44.7% zero-history claim.
2. Distribution, sparsity, and saturation of history scores across 8,192 cells.
3. Comparative evaluation of H0, H1, H2, H3 across 20 diagnostic positions at depth 6:
   - First-move cutoff efficiency (BF1 rate).
   - History cutoff contributions.
   - Total nodes, elapsed time, and NPS.
   - Score stability and bestmove preservation.
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
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "history_normalization_raw.json"

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

BENCHMARK_POSITIONS = [
    {"id": "G12_crisis", "fen": "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16"},
    {"id": "Tactical_pin_defense", "fen": "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N5/PP2PPPP/R2QKB1R w KQkq - 0 9"},
    {"id": "Minor_exchange_center", "fen": "r1bqk2r/pp2bppp/2n5/1Bpp4/3P4/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 8"},
    {"id": "Open_file_clash", "fen": "r3k2r/pppq1ppp/2n1bn2/3p4/3P4/2N1BN2/PPPQ1PPP/R3K2R w KQkq - 0 9"},
    {"id": "Complex_middlegame_1", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PNP3/2N1BP2/PP4PP/R2QKB1R w KQ - 1 9"},
    {"id": "Complex_middlegame_2", "fen": "r2q1rk1/1b1nbppp/ppn1p3/2ppP3/3P4/2PB1N2/PP1N1PPP/R1BQR1K1 w - - 2 12"},
    {"id": "Attacking_crisis_1", "fen": "r1b2rk1/pp1n1ppp/2p1p3/q2p2B1/2PP4/P1PBPN2/5PPP/R2Q1RK1 w - - 3 11"},
    {"id": "Attacking_crisis_2", "fen": "2r2rk1/1bq1bppp/pp1p1n2/4p3/P1PNP3/1PN1BP2/6PP/2RQR1K1 w - - 0 17"},
    {"id": "Endgame_rook_pawn", "fen": "8/5pk1/4p1p1/3pP2p/r4P1P/PR1R2P1/1P4K1/2r5 w - - 7 38"},
    {"id": "Endgame_minor_piece", "fen": "8/5k2/4p1p1/3pP3/2b2P1P/4B1P1/1b4K1/8 w - - 0 42"},
    {"id": "Endgame_queen_pawn", "fen": "8/5qk1/4p1p1/3pP3/5P1P/6P1/1Q4K1/8 w - - 0 45"},
    {"id": "Endgame_pawn_race", "fen": "8/5k2/4p3/3pP3/5P2/8/4K3/8 w - - 0 50"},
    {"id": "Endgame_tactical_break", "fen": "8/2p5/3k4/1p1p4/1P1P4/2K5/8/8 w - - 0 1"},
    {"id": "Endgame_bishop_opposite", "fen": "8/4k3/4b3/8/8/4B3/4K3/8 w - - 0 1"},
    {"id": "Tactical_queen_sac", "fen": "r1b2rk1/2p2ppp/p7/1p1B4/3P4/2P2Q2/PP1N1PPb/R1B1q2K w - - 1 18"},
    {"id": "Defensive_desperado", "fen": "r4rk1/1pp2ppp/p1np4/4p3/2B1P1b1/2NP1N2/PPP2qPP/R2Q3K w - - 0 13"},
    {"id": "Counter_sacrifice", "fen": "r1bq1rk1/ppp2ppp/2n5/3p4/3Pn3/2BB1N2/PPP2PPP/R2QK2R w KQ - 0 10"},
    {"id": "Check_pressure", "fen": "r1b1k2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"},
    {"id": "Quiet_maneuver", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9"},
    {"id": "Starting_pos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}
]

def sample_history_table(dll) -> Dict[str, Any]:
    scores = []
    zeros = 0
    positives = 0
    negatives = 0
    saturated = 0

    for s in range(2):
        for f in range(64):
            for t in range(64):
                val = dll.native_get_history_score(s, f, t)
                scores.append(val)
                if val == 0:
                    zeros += 1
                elif val > 0:
                    positives += 1
                    if val >= 16384:
                        saturated += 1
                else:
                    negatives += 1
                    if val <= -16384:
                        saturated += 1

    total = len(scores)
    scores.sort()
    mean = sum(scores) / total if total > 0 else 0
    min_v = min(scores)
    max_v = max(scores)
    median = scores[total // 2] if total > 0 else 0

    return {
        "total_cells": total,
        "zero_cells": zeros,
        "zero_percentage": round((zeros / total) * 100.0, 2),
        "positive_cells": positives,
        "negative_cells": negatives,
        "saturated_cells": saturated,
        "min": min_v,
        "max": max_v,
        "mean": round(mean, 2),
        "median": median
    }

def run_history_mode_benchmark(dll, mode: int, depth: int = 6) -> Dict[str, Any]:
    dll.native_set_history_mode(mode)
    dll.native_clear_history_heuristic()
    dll.native_reset_ordering_telemetry()

    positions_data = []
    total_nodes = 0
    total_time = 0.0

    for pos in BENCHMARK_POSITIONS:
        b = NativeBoard()
        dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(b))
        res = NativeSearchResult()

        t0 = time.perf_counter()
        dll.native_search(ctypes.byref(b), depth, 10.0, ctypes.byref(res))
        elapsed = time.perf_counter() - t0

        bm = parse_move_to_uci(dll, res.best_move)
        total_nodes += res.nodes
        total_time += elapsed

        positions_data.append({
            "id": pos["id"],
            "best_move": bm,
            "score": res.score,
            "nodes": res.nodes,
            "elapsed": round(elapsed, 4)
        })

    # Telemetry
    telemetry_arr = (ctypes.c_uint64 * 12)()
    dll.native_get_ordering_telemetry(telemetry_arr)

    tot_cutoffs = telemetry_arr[0]
    sum_index = telemetry_arr[1]
    m1_cutoffs = telemetry_arr[2]
    m2_cutoffs = telemetry_arr[3]
    m3_cutoffs = telemetry_arr[4]
    m4p_cutoffs = telemetry_arr[5]
    tt_cutoffs = telemetry_arr[6]
    k1_cutoffs = telemetry_arr[7]
    k2_cutoffs = telemetry_arr[8]
    hist_cutoffs = telemetry_arr[9]
    cap_cutoffs = telemetry_arr[10]
    quiet_cutoffs = telemetry_arr[11]

    bf1_rate = (m1_cutoffs / tot_cutoffs * 100.0) if tot_cutoffs > 0 else 0.0
    avg_cutoff_idx = (sum_index / tot_cutoffs) if tot_cutoffs > 0 else 0.0

    table_stats = sample_history_table(dll)

    return {
        "mode": mode,
        "depth": depth,
        "total_nodes": total_nodes,
        "total_elapsed_seconds": round(total_time, 4),
        "nps": int(total_nodes / total_time) if total_time > 0 else 0,
        "telemetry": {
            "total_cutoffs": tot_cutoffs,
            "first_move_cutoffs": m1_cutoffs,
            "bf1_percentage": round(bf1_rate, 2),
            "average_cutoff_index": round(avg_cutoff_idx, 3),
            "tt_cutoffs": tt_cutoffs,
            "killer1_cutoffs": k1_cutoffs,
            "killer2_cutoffs": k2_cutoffs,
            "history_cutoffs": hist_cutoffs,
            "capture_cutoffs": cap_cutoffs,
            "quiet_cutoffs": quiet_cutoffs
        },
        "history_distribution": table_stats,
        "positions": positions_data
    }

def main():
    dll = load_engine()

    print("--- Phase 5: History Reliability & Normalization Benchmark ---")
    modes = [0, 1, 2, 3] # H0, H1, H2, H3
    mode_names = ["H0_frozen", "H1_decay_half", "H2_conservative_decay", "H3_insearch_gravity"]
    results = {}

    for mode, name in zip(modes, mode_names):
        print(f"Running mode {name} (mode={mode})...")
        res = run_history_mode_benchmark(dll, mode, depth=6)
        results[name] = res
        t = res["telemetry"]
        h = res["history_distribution"]
        print(f"  Nodes: {res['total_nodes']:,} | Time: {res['total_elapsed_seconds']}s | NPS: {res['nps']:,}")
        print(f"  BF1 Rate: {t['bf1_percentage']}% | Avg Cutoff Index: {t['average_cutoff_index']}")
        print(f"  Hist Cutoffs: {t['history_cutoffs']} | Zero Cells: {h['zero_percentage']}% | Max: {h['max']} | Min: {h['min']}")

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll history benchmarks completed. Raw data saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

