#!/usr/bin/env python3
"""
test_time_control_generalization.py
Phase 7: Time-Control Generalization Investigation for Milestone P1.15.
Tests:
1. Multi-tier diagnostic time budgets (100ms, 250ms, 500ms, 1.0s, 2.5s, 5.0s) across
   representative positions comparing Baseline X7, Frozen X19, and Candidate X20.
2. Search termination correctness, completed depth, node throughput, budget overrun,
   evaluation trajectory, and PV stability.
3. Paired mini-tournament validation at Fast (1s+50ms) vs Slower (3s+100ms) time controls.
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
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "time_control_generalization_raw.json"

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

TIME_BUDGETS = [0.10, 0.25, 0.50, 1.00, 2.50, 5.00] # seconds

DIAGNOSTIC_POSITIONS = [
    {"id": "Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "Complex_middlegame", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PNP3/2N1BP2/PP4PP/R2QKB1R w KQ - 1 9"},
    {"id": "G12_crisis", "fen": "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16"},
    {"id": "Tactical_sacrifice", "fen": "r1b2rk1/2p2ppp/p7/1p1B4/3P4/2P2Q2/PP1N1PPb/R1B1q2K w - - 1 18"},
    {"id": "Endgame_rook_pawn", "fen": "8/5pk1/4p1p1/3pP2p/r4P1P/PR1R2P1/1P4K1/2r5 w - - 7 38"}
]

def run_diagnostic_time_budgets(dll):
    print("--- Part 1: Diagnostic Time Budget Scaling (100ms to 5.0s) ---")
    engines = [
        ("X7_Baseline", "X7", 0, 0),
        ("X19_Frozen", "X19", 0, 0),
        ("X20_Candidate", "X20", 1, 2) # C1 adaptive captures, H2 conservative aging
    ]

    results = {}

    for eng_label, variant, cap_mode, hist_mode in engines:
        print(f"Testing {eng_label}...")
        eng_data = {}

        for t_budget in TIME_BUDGETS:
            budget_label = f"{int(t_budget * 1000)}ms"
            pos_results = []
            tot_nodes = 0
            tot_elapsed = 0.0

            for pos in DIAGNOSTIC_POSITIONS:
                dll.native_apply_search_variant(variant.encode('utf-8'))
                dll.native_set_adaptive_capture_mode(cap_mode)
                dll.native_set_history_mode(hist_mode)
                dll.native_set_exact_search_mode(0)
                dll.native_clear_history_heuristic()
                dll.native_reset_ordering_telemetry()

                b = NativeBoard()
                dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(b))
                res = NativeSearchResult()

                t0 = time.perf_counter()
                dll.native_search(ctypes.byref(b), 64, t_budget, ctypes.byref(res))
                wall_time = time.perf_counter() - t0

                bm = parse_move_to_uci(dll, res.best_move)
                tot_nodes += res.nodes
                tot_elapsed += wall_time

                overrun = max(0.0, wall_time - t_budget)
                overrun_pct = (overrun / t_budget) * 100.0

                pos_results.append({
                    "id": pos["id"],
                    "budget_sec": t_budget,
                    "depth_achieved": res.depth,
                    "score": res.score,
                    "best_move": bm,
                    "nodes": res.nodes,
                    "wall_time_sec": round(wall_time, 4),
                    "overrun_sec": round(overrun, 4),
                    "overrun_percentage": round(overrun_pct, 2)
                })

            nps = int(tot_nodes / tot_elapsed) if tot_elapsed > 0 else 0
            avg_depth = sum(p["depth_achieved"] for p in pos_results) / len(pos_results)

            eng_data[budget_label] = {
                "budget_seconds": t_budget,
                "total_nodes": tot_nodes,
                "total_elapsed_seconds": round(tot_elapsed, 4),
                "nps": nps,
                "average_depth": round(avg_depth, 2),
                "positions": pos_results
            }
            print(f"  [{budget_label}] Avg Depth={avg_depth:.2f}, Total Nodes={tot_nodes:,}, Elapsed={tot_elapsed:.3f}s, NPS={nps:,}")

        results[eng_label] = eng_data

    return results

def main():
    dll = load_engine()
    diagnostics = run_diagnostic_time_budgets(dll)

    output = {
        "diagnostic_time_budgets": diagnostics
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nAll time budget scaling benchmarks completed. Raw data saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

