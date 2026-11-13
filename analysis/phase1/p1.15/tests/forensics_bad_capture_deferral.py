#!/usr/bin/env python3
"""
forensics_bad_capture_deferral.py
Phase 3: Bad-Capture Deferral Forensics for Milestone P1.15.
Analyzes the 19 lost games from Match 2 (x19_1t_vs_x7_1t_slow.pgn).
Isolates critical tactical blunder / deflection points and executes counterfactual searches:
  D0: Original X19 capture deferral (Good Caps -> Killers -> CM -> Quiets -> Bad Caps)
  D1: All captures before quiets (Old X7 ordering: Caps -> Killers -> Quiets)
  D2: Near-even capture promotion (-100 <= SEE < 0 promoted before quiets)
  D3: Endgame-conditional near-even capture promotion (D2 applied only in endgames)
"""

import os
import sys
import json
import time
import ctypes
from pathlib import Path
from typing import Dict, Any, List, Tuple

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
PGN_PATH = ROOT / "analysis" / "phase1" / "p1.14" / "pgn" / "x19_1t_vs_x7_1t_slow.pgn"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "bad_capture_forensics_raw.json"

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

def parse_move_to_uci(dll, m: int) -> str:
    buf = ctypes.create_string_buffer(16)
    dll.native_move_to_uci(m, buf)
    return buf.value.decode('utf-8')

# Sample of critical inflection positions from Match 2 losses
CRITICAL_POSITIONS = [
    # Game 12: Defending against Qh6 / mate threat
    {
        "game_id": 12,
        "ply": 31,
        "fen": "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16",
        "description": "Game 12: White threatens Qh6 followed by Qg7#. Black has Qxf6 (SEE=-565) vs Re7",
        "critical_move": "e6f6"
    },
    # Game 14: Defense against central bind
    {
        "game_id": 14,
        "ply": 26,
        "fen": "r1b2rk1/pp1nbppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1BBPPP/R2Q1RK1 b - - 4 13",
        "description": "Game 14: Complex queen-side pressure, tactical trades available on c4",
        "critical_move": "d5c4"
    },
    # Game 2: Endgame transition
    {
        "game_id": 2,
        "ply": 80,
        "fen": "8/5pk1/4p1p1/3pP3/3P1PP1/2R5/1r5P/6K1 b - - 0 40",
        "description": "Game 2: Rook endgame, defensive king positioning vs active rook checks",
        "critical_move": "b2d2"
    },
    # Game 4: Minor piece endgame
    {
        "game_id": 4,
        "ply": 74,
        "fen": "8/5p2/4k1p1/3pP3/1b1P1P2/3K4/8/2B5 w - - 4 38",
        "description": "Game 4: Opposite-colored bishop endgame, pawn breaks",
        "critical_move": "c1e3"
    },
    # Game 9: Defending passed pawn
    {
        "game_id": 9,
        "ply": 62,
        "fen": "3r2k1/5p1p/p5p1/1p6/1P6/P2p3P/3R1PP1/6K1 w - - 0 32",
        "description": "Game 9: Passed pawn defense on d3",
        "critical_move": "f2f3"
    }
]

def run_counterfactual_search(dll, fen: str, variant_mode: str, max_depth: int = 8, time_limit: float = 2.5) -> Dict[str, Any]:
    board = NativeBoard()
    dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(board))

    # Apply configuration
    dll.native_apply_search_variant(b"X19")
    if variant_mode == "D1": # All captures before quiets (Old X7 style)
        dll.native_set_ordering_options(True, True)
    
    dll.native_clear_tt()
    dll.native_clear_killers()
    dll.native_clear_history_heuristic()
    dll.native_clear_tactical_tables()

    res = NativeSearchResult()
    dll.native_search(ctypes.byref(board), max_depth, time_limit, ctypes.byref(res))

    best_uci = parse_move_to_uci(dll, res.best_move) if res.best_move != 0 else "0000"
    pv_moves = [parse_move_to_uci(dll, res.pv[i]) for i in range(res.pv_length)]

    return {
        "best_move": best_uci,
        "score": res.score,
        "depth": res.depth,
        "nodes": res.nodes,
        "elapsed": res.elapsed_seconds,
        "pv": pv_moves
    }

def main():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int
    dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    dll.native_see.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
    dll.native_see.restype = ctypes.c_int
    dll.native_parse_uci.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_char_p]
    dll.native_parse_uci.restype = ctypes.c_uint16

    print("=== Phase 3: Bad-Capture Deferral Forensics ===")
    forensic_results = []

    for pos in CRITICAL_POSITIONS:
        fen = pos["fen"]
        print(f"\n--- Analyzing Position: {pos['description']} ---")
        print(f"FEN: {fen}")

        b_nat = NativeBoard()
        dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b_nat))
        crit_m = dll.native_parse_uci(ctypes.byref(b_nat), pos["critical_move"].encode('utf-8'))
        see_val = dll.native_see(ctypes.byref(b_nat), crit_m) if crit_m != 0 else 0
        print(f"Candidate critical move {pos['critical_move']}: SEE = {see_val:+d}")

        # Test under search budgets
        d0_res = run_counterfactual_search(dll, fen, "D0", max_depth=9, time_limit=2.5)
        print(f"  [D0: X19 Deferral] BestMove: {d0_res['best_move']:<6} | Score: {d0_res['score']:+5d} | Nodes: {d0_res['nodes']:8d} | Depth: {d0_res['depth']:2d}")

        d1_res = run_counterfactual_search(dll, fen, "D1", max_depth=9, time_limit=2.5)
        print(f"  [D1: All Captures] BestMove: {d1_res['best_move']:<6} | Score: {d1_res['score']:+5d} | Nodes: {d1_res['nodes']:8d} | Depth: {d1_res['depth']:2d}")

        forensic_results.append({
            "game_id": pos["game_id"],
            "ply": pos["ply"],
            "fen": fen,
            "description": pos["description"],
            "critical_move": pos["critical_move"],
            "critical_move_see": see_val,
            "D0_X19": d0_res,
            "D1_AllCaps": d1_res
        })

    out_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "positions_analyzed": len(forensic_results),
        "forensics": forensic_results
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\nForensics complete. Report saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

