#!/usr/bin/env python3
"""
audit_r1_selectivity_gate.py
Milestone P1.22 Phase 10: Safe Selectivity Research Gate.
Evaluates the cumulative selectivity ladder:
- S0: Pure PVS + TT + Qsearch (Zero heuristic pruning)
- S1: S0 + Null-Move Pruning (NMP)
- S2: S1 + Reverse Futility Pruning (RFP)
- S3: S2 + Late Move Reductions (LMR)
- S4: S3 + Late Move Pruning (LMP) — Full Production R1.0 Core
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
OUT_JSON = ROOT / "analysis" / "phase1" / "p1.22" / "raw" / "r1_selectivity_gate_raw.json"
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

lib = ctypes.CDLL(str(DLL_PATH))

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", ctypes.c_uint64 * 6 * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]

class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ("best_move", ctypes.c_uint16),
        ("score", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("nodes", ctypes.c_uint64),
        ("elapsed_seconds", ctypes.c_double),
        ("pv_length", ctypes.c_int),
        ("pv", ctypes.c_uint16 * 128),
    ]

lib.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
lib.native_set_fen.restype = ctypes.c_int

lib.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
lib.native_move_to_uci.restype = None

lib.native_r1_set_config.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
]
lib.native_r1_set_config.restype = None

lib.native_r1_clear_tt.argtypes = []
lib.native_r1_clear_tt.restype = None

lib.native_r1_search.argtypes = [
    ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)
]
lib.native_r1_search.restype = None

def board_from_fen(fen: str) -> NativeBoard:
    nb = NativeBoard()
    lib.native_set_fen(fen.encode("utf-8"), ctypes.byref(nb))
    return nb

def move_to_uci(m: int) -> str:
    buf = ctypes.create_string_buffer(16)
    lib.native_move_to_uci(ctypes.c_uint16(m), buf)
    return buf.value.decode("utf-8")

SELECTIVITY_LEVELS = [
    ("S0", "Pure PVS + Qsearch", (0, 1, 1, 1, 1, 0, 0, 0, 0)),
    ("S1", "+ Null-Move Pruning (NMP)", (0, 1, 1, 1, 1, 1, 0, 0, 0)),
    ("S2", "+ Reverse Futility Pruning (RFP)", (0, 1, 1, 1, 1, 1, 1, 0, 0)),
    ("S3", "+ Late Move Reductions (LMR)", (0, 1, 1, 1, 1, 1, 1, 1, 0)),
    ("S4", "+ Late Move Pruning (LMP) [Full R1.0]", (0, 1, 1, 1, 1, 1, 1, 1, 1)),
]

TEST_POSITIONS = [
    ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 6),
    ("Semi-Slav", "rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5", 6),
    ("Tactical Queen", "r1b1k2r/pppp1ppp/8/8/1B1qn3/8/PPP2PPP/RN1QKB1R w KQkq - 0 1", 6),
    ("Scheveningen Sac", "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18", 6),
    ("Rook 4v3", "8/5pk1/7p/1R6/8/8/5rPP/6K1 b - - 0 1", 6),
]

def main():
    print("=" * 80)
    print("PHASE 10: SAFE SELECTIVITY RESEARCH GATE (S0 -> S1 -> S2 -> S3 -> S4)")
    print("=" * 80)

    results = []

    for name, fen, d in TEST_POSITIONS:
        print(f"\n--- Position: {name} (Depth {d}) ---")
        pos_entry = {"name": name, "fen": fen, "depth": d, "levels": {}}

        baseline_nodes = None

        for lvl_id, desc, cfg in SELECTIVITY_LEVELS:
            lib.native_r1_clear_tt()
            lib.native_r1_set_config(*cfg)

            nb = board_from_fen(fen)
            res = NativeSearchResult()

            t0 = time.perf_counter()
            lib.native_r1_search(ctypes.byref(nb), d, 5.0, ctypes.byref(res))
            wall_ms = (time.perf_counter() - t0) * 1000.0

            m_str = move_to_uci(res.best_move)
            if baseline_nodes is None:
                baseline_nodes = res.nodes

            node_ratio = round(res.nodes / baseline_nodes, 3) if baseline_nodes > 0 else 1.0
            reduction_pct = round((1.0 - node_ratio) * 100.0, 1)

            print(f"  {lvl_id:2} ({desc:35}) | Move: {m_str:5} | Score: {res.score:+5} cp | Nodes: {res.nodes:8,} ({node_ratio:5.3f}x, {reduction_pct:+5.1f}%) | Time: {wall_ms:5.1f} ms")

            pos_entry["levels"][lvl_id] = {
                "desc": desc,
                "bestmove": m_str,
                "score": res.score,
                "nodes": res.nodes,
                "wall_ms": round(wall_ms, 2),
                "ratio_vs_s0": node_ratio,
                "reduction_pct": reduction_pct
            }

        results.append(pos_entry)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Selectivity gate raw JSON saved to:\n  {OUT_JSON}")
    print("=" * 80)

if __name__ == "__main__":
    main()
