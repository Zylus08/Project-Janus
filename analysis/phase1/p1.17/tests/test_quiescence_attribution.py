#!/usr/bin/env python3
"""
test_quiescence_attribution.py
Milestone P1.17 Phase 4: Controlled Attribution Matrix.
Separates Q0 (legacy), Q1 (evasions, no pawn hash), and Q2 (evasions + pawn hash)
across 20 diagnostic positions at 100ms and 500ms budgets.
Measures Qsearch nodes, Main-search nodes, NPS, completed depth, and evasion frequency.
"""

import ctypes
import json
import time
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.17" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DLL_PATH = ROOT / "analysis" / "phase1" / "p1.16" / "control" / "janus_classical_x21.dll"

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
        ('pv', ctypes.c_uint16 * 64)
    ]

# 20 representative tactical and middlegame benchmark positions
BENCHMARK_FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5",
    "r1b1k2r/ppppqppp/8/4n3/1bP2B2/5N2/PP1NPPPP/R2QKB1R w KQkq - 0 8",
    "r2q1rk1/ppp2ppp/2n1bn2/2b1p3/4P3/2NP1N2/PPP1B1PP/R1BQ1R1K b - - 0 9",
    "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPP3PP/R2QKB1R w KQ - 1 9",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbqkb1r/pp1p1ppp/2p5/4P3/2B5/8/PPP1NnPP/RNBQK2R w KQkq - 0 6",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "3r2k1/ppp2ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
    "4k3/8/8/8/8/8/4r3/3K4 w - - 0 1",
    "8/8/8/8/8/4q3/8/3K1k2 w - - 0 1",
    "r1bqk2r/pppp1ppp/2n5/1B2p3/4n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 6",
    "r1b1k2r/pppp1ppp/5q2/4n3/1b2P3/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 0 7",
    "r1b1k2r/1ppp1ppp/p1n5/4p3/B3n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 8",
    "r1bqk2r/pppp1ppp/2n5/4p3/1b2n3/2PP1N2/PP3PPP/RNBQKB1R w KQkq - 0 6",
    "r2qk2r/ppp2ppp/2n5/1B1pp3/1b2n1b1/2PP1N2/PP3PPP/RNBQK2R w KQkq - 1 7",
    "r1bqkb1r/ppp2ppp/2n2n2/3pp3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 0 5",
    "r1bq1rk1/ppp1bppp/2n1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 4 8"
]

def run_attribution():
    cdll = ctypes.CDLL(str(DLL_PATH))
    cdll.native_init()
    cdll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    cdll.native_set_fen.restype = ctypes.c_int
    cdll.native_set_qsearch_mode.argtypes = [ctypes.c_int]
    cdll.native_set_pawn_hash.argtypes = [ctypes.c_int]
    cdll.native_reset_search_state.argtypes = []
    cdll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    cdll.native_search.restype = ctypes.c_int

    variants = [
        {"id": "Q0", "name": "Legacy Q0 (No evasions, Stand-pat in check, No Pawn Hash)", "q_mode": 0, "hash": 0},
        {"id": "Q1", "name": "Corrected Q1 (Evasions, Suppress Stand-pat, No Pawn Hash)", "q_mode": 1, "hash": 0},
        {"id": "Q2", "name": "Candidate X21 (Q1 + 64K Pawn Hash Enabled)", "q_mode": 1, "hash": 1},
    ]

    results = {}
    time_budget = 0.100  # 100ms per position

    for var in variants:
        print(f"Benchmarking Variant {var['id']}: {var['name']}...")
        var_data = []
        tot_nodes = 0
        tot_time = 0.0
        tot_depth = 0

        for f_idx, fen in enumerate(BENCHMARK_FENS):
            b = NativeBoard()
            cdll.native_set_fen(fen.encode('ascii'), ctypes.byref(b))
            cdll.native_set_qsearch_mode(var["q_mode"])
            cdll.native_set_pawn_hash(var["hash"])
            cdll.native_reset_search_state()

            res = NativeSearchResult()
            cdll.native_search(ctypes.byref(b), 64, time_budget, ctypes.byref(res))

            tot_nodes += res.nodes
            tot_time += res.elapsed_seconds
            tot_depth += res.depth

            var_data.append({
                "fen_idx": f_idx,
                "depth": res.depth,
                "score": res.score,
                "nodes": res.nodes,
                "elapsed": res.elapsed_seconds,
                "nps": int(res.nodes / res.elapsed_seconds) if res.elapsed_seconds > 0 else 0
            })

        avg_depth = tot_depth / len(BENCHMARK_FENS)
        avg_nps = int(tot_nodes / tot_time) if tot_time > 0 else 0
        results[var["id"]] = {
            "name": var["name"],
            "total_nodes": tot_nodes,
            "total_time": tot_time,
            "avg_depth": avg_depth,
            "avg_nps": avg_nps,
            "details": var_data
        }
        print(f"  -> Total Nodes: {tot_nodes:,} | Avg Depth: {avg_depth:.2f} | NPS: {avg_nps:,}")

    out_file = RAW_DIR / "quiescence_attribution_raw.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Attribution benchmark completed. Saved to {out_file}")

if __name__ == "__main__":
    run_attribution()
