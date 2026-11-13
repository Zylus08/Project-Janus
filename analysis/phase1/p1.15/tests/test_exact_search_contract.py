#!/usr/bin/env python3
"""
test_exact_search_contract.py
Phase 6: Fixed-Depth Search Contract Verification for Milestone P1.15.
Tests:
1. Exact full-width alpha-beta search correctness (verifies mathematical minimax equivalence
   across move-ordering policies when selective pruning is disabled).
2. Selective search empirical comparison (demonstrates how selective search mechanisms
   cause score divergences while achieving large practical node reductions).
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
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "exact_search_contract_raw.json"

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

# 15 Positions for Exact Search Contract Verification
TEST_POSITIONS = [
    {"id": "Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "Open_tactical", "fen": "r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7"},
    {"id": "Closed_position", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9"},
    {"id": "King_check", "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"},
    {"id": "Pin_pressure", "fen": "r1b1k2r/ppppbppp/5n2/4q3/8/2N1P3/PPPBBPPP/R2QK2R w KQkq - 2 9"},
    {"id": "En_passant", "fen": "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"},
    {"id": "Promotion_adjacent", "fen": "8/4P3/8/8/8/8/k7/4K3 w - - 0 1"},
    {"id": "Endgame_pawns", "fen": "8/4k3/4p3/4P3/8/8/4K3/8 w - - 0 1"},
    {"id": "Endgame_minor", "fen": "8/4k3/8/2b5/4N3/8/4K3/8 w - - 0 1"},
    {"id": "Heavy_pieces", "fen": "4r1k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1"},
    {"id": "G12_crisis", "fen": "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16"},
    {"id": "Queen_clash", "fen": "r1b2rk1/2p2ppp/p7/1p1B4/3P4/2P2Q2/PP1N1PPb/R1B1q2K w - - 1 18"},
    {"id": "Middlegame_clash", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PNP3/2N1BP2/PP4PP/R2QKB1R w KQ - 1 9"},
    {"id": "Quiet_maneuver", "fen": "8/5p2/8/8/8/8/5P2/4K2k w - - 0 1"},
    {"id": "Check_pressure", "fen": "r1b1kb1r/pppp1ppp/2n5/4p3/2B1n2q/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 6"}
]

def run_exact_fullwidth_audit(dll):
    print("--- Part 1: Exact Full-Width Minimax Contract Verification ---")
    dll.native_set_exact_search_mode(1) # Disable all selective features
    orderings = [
        ("X7_legacy", "X7", 0),
        ("X19_C0", "X19", 0),
        ("X20_C1", "X19", 1),
        ("X20_C2", "X19", 2),
        ("X20_C3", "X19", 3)
    ]

    depths = [1, 2, 3, 4]
    audit_results = {}
    total_comparisons = 0
    score_matches = 0
    divergences = 0

    for depth in depths:
        depth_data = []
        for pos in TEST_POSITIONS:
            pos_id = pos["id"]
            fen = pos["fen"]
            b = NativeBoard()
            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))

            ref_score = None
            pos_records = {}

            for label, variant, cap_mode in orderings:
                dll.native_apply_search_variant(variant.encode('utf-8'))
                dll.native_set_adaptive_capture_mode(cap_mode)
                dll.native_set_exact_search_mode(1)
                dll.native_clear_history_heuristic()
                dll.native_reset_ordering_telemetry()

                res = NativeSearchResult()
                dll.native_search(ctypes.byref(b), depth, 10.0, ctypes.byref(res))

                bm = parse_move_to_uci(dll, res.best_move)
                pos_records[label] = {
                    "score": res.score,
                    "best_move": bm,
                    "nodes": res.nodes,
                    "elapsed": round(res.elapsed_seconds, 4)
                }

                if ref_score is None:
                    ref_score = res.score
                else:
                    total_comparisons += 1
                    if res.score == ref_score:
                        score_matches += 1
                    else:
                        divergences += 1
                        print(f"DIVERGENCE at depth {depth}, pos {pos_id}: {label} scored {res.score} vs ref {ref_score}")

            depth_data.append({
                "id": pos_id,
                "depth": depth,
                "reference_score": ref_score,
                "orderings": pos_records
            })
        audit_results[f"depth_{depth}"] = depth_data

    match_pct = (score_matches / total_comparisons * 100.0) if total_comparisons > 0 else 0.0
    print(f"Exact Minimax Score Audit: {score_matches}/{total_comparisons} comparisons matched ({match_pct:.2f}%)")
    print(f"Divergences: {divergences}")
    return audit_results, match_pct

def run_selective_search_audit(dll):
    print("--- Part 2: Selective Search Empirical Audit (Depth 6) ---")
    dll.native_set_exact_search_mode(0) # Enable all selective features
    configs = [
        ("X7_1T", "X7", 0),
        ("X12_4T", "X12", 0),
        ("X19_1T", "X19", 0),
        ("X20_1T_C1", "X19", 1)
    ]
    depth = 6
    selective_results = {}

    for label, variant, cap_mode in configs:
        dll.native_apply_search_variant(variant.encode('utf-8'))
        dll.native_set_adaptive_capture_mode(cap_mode)
        dll.native_set_exact_search_mode(0)
        dll.native_clear_history_heuristic()
        dll.native_reset_ordering_telemetry()

        pos_records = []
        tot_nodes = 0
        tot_time = 0.0

        for pos in TEST_POSITIONS:
            b = NativeBoard()
            dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(b))
            res = NativeSearchResult()

            t0 = time.perf_counter()
            dll.native_search(ctypes.byref(b), depth, 10.0, ctypes.byref(res))
            elapsed = time.perf_counter() - t0

            bm = parse_move_to_uci(dll, res.best_move)
            tot_nodes += res.nodes
            tot_time += elapsed

            pos_records.append({
                "id": pos["id"],
                "score": res.score,
                "best_move": bm,
                "nodes": res.nodes,
                "elapsed": round(elapsed, 4)
            })

        selective_results[label] = {
            "total_nodes": tot_nodes,
            "total_elapsed_seconds": round(tot_time, 4),
            "nps": int(tot_nodes / tot_time) if tot_time > 0 else 0,
            "positions": pos_records
        }
        print(f"Config {label}: Total Nodes={tot_nodes:,}, Elapsed={tot_time:.3f}s, NPS={int(tot_nodes/tot_time):,}")

    return selective_results

def main():
    dll = load_engine()

    exact_results, match_rate = run_exact_fullwidth_audit(dll)
    selective_results = run_selective_search_audit(dll)

    output = {
        "exact_minimax_contract": {
            "match_rate_percentage": match_rate,
            "depth_audits": exact_results
        },
        "selective_search_comparison": selective_results
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nAll search contract audits completed. Raw data saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

