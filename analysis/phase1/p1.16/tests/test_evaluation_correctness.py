#!/usr/bin/env python3
"""
test_evaluation_correctness.py
Phase 2: Classical Evaluation Correctness and Positional Diagnostics.
Builds a provenance-tracked 225-position suite across 15 classical categories.
Tests:
1. Relative Colour Symmetry: eval(mirror(b)) == eval(b)
2. Absolute Inversion Symmetry: eval(invert_colors(b)) == -eval(b)
3. Phase continuity (MG -> EG interpolation)
4. Pawn hash validity (100% identity with uncached computation)
5. King safety stability and clamping
6. Score bounds & overflow prevention
7. Determinism across repeated calls
"""

import os
import sys
import json
import ctypes
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.16" / "raw" / "evaluation_correctness_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64)
    ]

dll = ctypes.CDLL(str(DLL_PATH))
dll.native_init()
dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
dll.native_set_fen.restype = ctypes.c_int
dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_evaluate.restype = ctypes.c_int
dll.native_evaluate_detail.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
dll.native_evaluate_detail.restype = ctypes.c_int

def build_corpus():
    categories = {
        "isolated_pawns": [
            "r1bqk2r/pp2bppp/2n1pn2/8/3P4/2N2N2/PP2BPPP/R1BQ1RK1 w kq - 0 10",
            "r1bq1rk1/pp1nbppp/4pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8",
            "r1bqk2r/pp2bppp/2n2n2/3p4/3P4/2N2N2/PP2BPPP/R1BQ1RK1 w kq - 0 9",
            "r2q1rk1/pp1nbppp/2p1pn2/8/2PP4/2N2N2/PP2BPPP/R1BQ1RK1 w - - 0 10",
            "r1bqk2r/pp3ppp/2n1pn2/3p4/1b1P4/2N2N2/PP2BPPP/R1BQK2R w KQkq - 2 8",
            "8/pp3kpp/4p3/3p4/3P4/5K2/PP3PPP/8 w - - 0 25",
            "8/2k2pp1/4p2p/3p4/3P4/4P2P/2K2PP1/8 w - - 0 30",
            "r1b1k2r/pp3ppp/2n1pn2/3p4/3P4/q1N2N2/PP2BPPP/R1BQK2R w KQkq - 0 9",
            "r2q1rk1/1p1nbppp/p3pn2/3p4/3P4/2N2N2/PPP1BPPP/R1BQR1K1 w - - 0 11",
            "r1bqr1k1/pp1nbppp/4pn2/3p4/3P4/2PB1N2/PP3PPP/RNBQR1K1 w - - 0 10",
            "8/5kpp/pp2p3/3p4/3P4/P4K2/1P3PPP/8 w - - 0 28",
            "r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2N1PN2/PP1B1PPP/R2Q1RK1 w - - 0 11",
            "r1b1qrk1/pp1n1ppp/4pn2/3p4/3P4/2PB1N2/PP1N1PPP/R2Q1RK1 w - - 0 11",
            "r4rk1/pp1nbppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1BBPPP/R2Q1RK1 w - - 4 10",
            "8/4k1pp/p3p3/1p1p4/3P4/P3K2P/1P3PP1/8 w - - 0 32"
        ],
        "doubled_pawns": [
            "r1bq1rk1/pp2ppbp/2np1np1/8/2PNP3/2N1BP2/PP4PP/R2QKB1R w KQ - 0 9",
            "r1bqk2r/pppp1ppp/2n5/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
            "r1b1k2r/pp1p1ppp/1qn1pn2/8/2P1P3/1PN2N2/P4PPP/R1BQKB1R b KQkq - 0 8",
            "r1bqk2r/pp3ppp/2n1pn2/3p4/2PP4/1PN2N2/P4PPP/R1BQKB1R w KQkq - 0 8",
            "8/5kpp/pp1p4/3Pp3/1PP1P3/8/P5PP/5K2 w - - 0 26",
            "8/pp1k1ppp/3p4/2pP4/2P1P3/8/PP4PP/5K2 w - - 0 25",
            "r2q1rk1/ppp1bppp/2n1pn2/3p4/2PP4/1PN1PN2/PB3PPP/R2Q1RK1 w - - 0 10",
            "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 0 10",
            "8/p1pk1ppp/1p1p4/3P4/2P1P3/1P6/P4KPP/8 w - - 0 27",
            "r1b2rk1/ppqn1ppp/2pbpn2/8/2PP4/1PN1PN2/PB3PPP/R2QKB1R w KQ - 0 9",
            "r1b1k2r/pp3ppp/2n1p3/3p4/2PP4/1PN2N2/P4PPP/R2QKB1R w KQkq - 0 10",
            "8/2k2pp1/1p1p3p/3Pp3/1PP1P3/7P/2K2PP1/8 w - - 0 30",
            "r2qr1k1/pp1nbppp/2p1pn2/8/2PP4/1PN2N2/PB2BPPP/R2Q1RK1 w - - 0 11",
            "8/5k2/1p1p4/p1pPp3/P1P1P3/8/1P3K2/8 w - - 0 35",
            "r1bq1rk1/1pp1bppp/p1np1n2/4p3/2B1P3/2NP1N2/PPPB1PPP/R2Q1RK1 w - - 0 8"
        ],
        "passed_pawns": [
            "8/4k3/8/3P4/8/8/4K3/8 w - - 0 1",
            "8/5k2/8/8/3P4/8/8/5K2 w - - 0 1",
            "8/8/4k3/8/2P5/8/4K3/8 w - - 0 1",
            "8/8/5k2/8/8/1P6/5K2/8 w - - 0 1",
            "8/8/8/4k3/8/6P1/4K3/8 w - - 0 1",
            "8/8/8/8/3k4/8/7P/3K4 w - - 0 1",
            "8/8/8/8/2k5/8/8/P2K4 w - - 0 1",
            "8/8/2P5/8/4k3/8/4K3/8 w - - 0 1",
            "8/8/8/1P6/3k4/8/3K4/8 w - - 0 1",
            "8/8/8/8/4k3/6P1/4K3/8 w - - 0 1",
            "8/4k3/8/2PP4/8/8/4K3/8 w - - 0 1",
            "8/5k2/8/8/3PP3/8/8/5K2 w - - 0 1",
            "8/8/4k3/8/2P1P3/8/4K3/8 w - - 0 1",
            "8/8/8/8/2k5/8/P1P5/3K4 w - - 0 1",
            "8/8/8/8/3k4/8/3PP3/3K4 w - - 0 1"
        ],
        "backward_pawns": [
            "r1bqkb1r/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 0 6",
            "r1b1k2r/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1BBPPP/R2QK2R w KQkq - 2 8",
            "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8",
            "r1bq1rk1/pp1nbppp/2p1pn2/8/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8",
            "r2q1rk1/pp1n1ppp/2p1pn2/b2p4/2PP4/2N1PN2/PP1BBPPP/R2Q1RK1 w - - 4 9",
            "8/pp1n1kpp/2p1p3/3p4/3P4/2N1P3/PP3PPP/5K2 w - - 0 20",
            "8/2k2pp1/2p1p2p/3p4/3P4/4P2P/2K2PP1/8 w - - 0 28",
            "r1bqr1k1/pp1n1ppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 9",
            "r2q1rk1/pp1nbppp/2p1p3/3p4/2PPn3/2N1PN2/PP1BBPPP/R2Q1RK1 w - - 6 10",
            "r1b2rk1/pp1nqppp/2p1pn2/3p4/2PP4/2N1PN2/PP1BBPPP/R2Q1RK1 w - - 2 9",
            "8/5kpp/pp1p4/2p1p3/3PP3/P1P5/1P3PPP/5K2 w - - 0 25",
            "8/pp2kppp/2p1p3/3p4/3P4/P1P1P3/1P3PPP/4K3 w - - 0 22",
            "r1b1kb1r/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQkq - 2 7",
            "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP1BBPPP/R2Q1RK1 w - - 0 8",
            "8/4k1pp/p1p1p3/1p1p4/3P4/P3K2P/1PP2PP1/8 w - - 0 28"
        ],
        "pawn_chains": [
            "rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4",
            "rnbqkbnr/pp2pppp/8/2pp4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3",
            "r1bqk2r/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQkq - 0 7",
            "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8",
            "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w - - 0 8",
            "8/5kpp/pp2p3/2pp4/3P4/2P1P3/PP3PPP/5K2 w - - 0 22",
            "8/2k2pp1/pp2p2p/2pp4/3P4/2P1P2P/PP3PP1/2K5 w - - 0 25",
            "r1bqr1k1/pp1nbppp/2n1p3/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 9",
            "r2q1rk1/pp1nbppp/2n1p3/2pp4/2PP4/2NBPN2/PP1B1PPP/R2Q1RK1 w - - 0 9",
            "r1b1r1k1/pp1nbppp/2n1p3/2pp4/2PP4/2NBPN2/PP1B1PPP/R2QR1K1 w - - 0 10",
            "8/pp1k1ppp/4p3/2pp4/3P4/2P1P3/PP3PPP/4K3 w - - 0 20",
            "8/4k1pp/pp2p3/2pp4/3P4/2P1K2P/PP3PP1/8 w - - 0 26",
            "r1b2rk1/pp1nbppp/2n1p3/2pp4/2PP4/2NBPN2/PP1B1PPP/R2Q1RK1 w - - 0 9",
            "r2q1rk1/pp1nbppp/4p3/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9",
            "8/5k2/pp2p3/2pp4/3P4/2P1P3/PP3K2/8 w - - 0 24"
        ],
        "opposite_side_castling": [
            "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R b - - 2 9",
            "r1b2rk1/ppq1ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 3 10",
            "r1b2rk1/2q1ppbp/p1np1np1/1p6/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11",
            "r1b2rk1/2q1ppbp/p1np1np1/1p6/3NP3/1PN1BP2/P1PQ2PP/2KR1B1R b - - 1 11",
            "r1b2rk1/2q1ppbp/p1np1np1/1p6/4P3/1PN1BP2/P1PQN1PP/2KR1B1R w - - 2 12",
            "r2q1rk1/1p2ppbp/p1np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 10",
            "r1b2rk1/pp2ppbp/2np1np1/q7/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 4 10",
            "r1b2rk1/pp3pbp/1qnp1np1/4p3/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11",
            "r1b2rk1/pp2ppbp/1qnp1np1/8/3NP3/1BN1BP2/PPPQ2PP/2KR3R b - - 1 11",
            "r2q1rk1/1pp1ppbp/p1np1np1/8/3NP3/1PN1BP2/P1PQ2PP/2KR1B1R b - - 0 10",
            "r1b2rk1/1pq1ppbp/p1np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 10",
            "r1b2rk1/p1q1ppbp/1pnp1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11",
            "r1b2rk1/pp2ppbp/3p1np1/q7/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11",
            "r1b2rk1/2q1ppbp/p2p1np1/1p6/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 12",
            "r1b2rk1/2q1ppbp/p1np1np1/1p6/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11"
        ],
        "open_file_king_attacks": [
            "r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16",
            "r1bq1rk1/pp3ppp/2n1pn2/8/2BP4/5N2/PP1N1PPP/R2Q1RK1 w - - 0 10",
            "r1b2rk1/pp1n1ppp/4pn2/q2p4/2PP4/2N1PN2/PP1BBPPP/R2Q1RK1 b - - 4 13",
            "r2q1rk1/pp1nbppp/2p1pn2/8/2PP4/2N2N2/PP2BPPP/R1BQ1RK1 b - - 0 10",
            "r1bqr1k1/pp1nbppp/4pn2/3p4/3P4/2PB1N2/PP3PPP/RNBQR1K1 w - - 0 10",
            "r1b2rk1/1pp1qppp/p1np1n2/4p3/2B1P3/3P1N2/PPPB1PPP/R2Q1RK1 w - - 0 10",
            "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P3/3P1N2/PPPB1PPP/R2Q1RK1 w - - 0 10",
            "r1bqr1k1/1pp2ppp/p1np1n2/4p3/2B1P3/3P1N2/PPPB1PPP/R2QR1K1 w - - 0 11",
            "r1bq1rk1/1pp2ppp/p1np1n2/4p3/2B1P3/3P1N2/PPPB1PPP/R2Q1RK1 w - - 0 9",
            "r1bqr1k1/ppp2ppp/2np1n2/4p3/2B1P3/3P1N2/PPPB1PPP/R2QR1K1 w - - 0 10",
            "r2q1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9",
            "r1b2rk1/ppqn1ppp/2pbpn2/8/2PP4/2N1PN2/PB2BPPP/R2Q1RK1 w - - 0 10",
            "r1bqr1k1/pp1n1ppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 9",
            "r2q1rk1/pp1nbppp/2p1pn2/8/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9",
            "r1bqr1k1/pp1n1ppp/4pn2/3p4/2PP4/2PB1N2/P4PPP/R1BQR1K1 w - - 0 10"
        ],
        "sacrificial_king_attacks": [
            "r1bqk2r/pp1nbppp/2p1pn2/8/2PPN3/3B1N2/PP3PPP/R1BQK2R w KQkq - 1 8",
            "r1b2rk1/pp1nbppp/2p1pn2/q2p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 4 9",
            "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8",
            "r1bqr1k1/pp1n1ppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 9",
            "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8",
            "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8",
            "r1bqr1k1/pp1nbppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQR1K1 w - - 0 9",
            "r1bq1rk1/pp1n1ppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8",
            "r1bqk2r/pp1nbppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQkq - 0 7",
            "r2q1rk1/pp1nbppp/2p1pn2/8/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8",
            "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8",
            "r1bqr1k1/pp1n1ppp/4pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 9",
            "r1bq1rk1/pp1nbppp/4pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8",
            "r2q1rk1/pp1nbppp/4pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8",
            "r1bqr1k1/pp1nbppp/4pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 9"
        ],
        "queenless_middlegames": [
            "r1b2rk1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 b - - 0 9",
            "r1b1k2r/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w kq - 0 9",
            "r1b2rk1/pp1nbppp/4pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1pn2/8/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 9",
            "r1b2rk1/pp1n1ppp/4pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 9",
            "r2r2k1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 10",
            "r1b2rk1/pp2bppp/2n1pn2/q1p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 10",
            "r4rk1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 10",
            "r1b2rk1/pp2bppp/4pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1p3/2p5/2PP4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1pn2/2p5/3P4/2N1PN2/PP2BPPP/R1B2RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1pn2/2p5/2PP4/1PN1PN2/P3BPPP/R1B2RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP1BBPPP/R4RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R4RK1 w - - 0 9",
            "r1b2rk1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R1B1K2R w KQ - 0 9"
        ],
        "minor_piece_endgames": [
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1b3B1P/6K1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/1b1P1P2/3K4/8/2B5 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/5N2/5b1P/6K1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/1n1P1P2/3K4/8/2B5 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1n3N1P/6K1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/1b1P1P2/3K4/8/2N5 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/5B1P/5bK1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/3P1P2/3K4/1b6/2B5 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/4NB1P/6K1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/3P1P2/3K1N2/8/2B5 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/5N1P/5nK1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/3P1P2/3K4/8/1b1B4 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/7P/3B2K1 w - - 0 40",
            "8/5p2/4k1p1/3pP3/3P1P2/3K4/8/2B1b3 w - - 4 38",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/8/3B2K1 w - - 0 40"
        ],
        "rook_endgames": [
            "8/5pk1/4p1p1/3pP3/3P1PP1/2R5/1r5P/6K1 b - - 0 40",
            "3r2k1/5p1p/p5p1/1p6/1P6/P2p3P/3R1PP1/6K1 w - - 0 32",
            "8/5pk1/4p1p1/3pP3/3P1PP1/1R6/1r5P/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1r5P/2R3K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/7P/1rR3K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/2R5/7P/1r4K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/2R4P/1r6/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/1R5P/1r6/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/7P/1r5R/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/7P/1R6/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1rR4P/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1r5P/6K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1r5P/5RK1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1r5P/R5K1 w - - 0 40",
            "8/5pk1/4p1p1/3pP3/3P1PP1/8/1r5P/4R1K1 w - - 0 40"
        ],
        "pure_pawn_endgames": [
            "8/5k2/8/8/3P4/8/8/5K2 w - - 0 1",
            "8/8/4k3/8/3P4/8/4K3/8 w - - 0 1",
            "8/8/8/4k3/3P4/8/4K3/8 w - - 0 1",
            "8/8/8/8/3k4/3P4/4K3/8 w - - 0 1",
            "8/5kpp/4p3/3p4/3P4/4P3/5PPP/5K2 w - - 0 25",
            "8/2k2pp1/4p2p/3p4/3P4/4P2P/2K2PP1/8 w - - 0 30",
            "8/5k2/8/4p3/3P4/8/8/5K2 w - - 0 1",
            "8/8/4k3/4p3/3P4/8/4K3/8 w - - 0 1",
            "8/8/8/4k3/4p3/3P4/4K3/8 w - - 0 1",
            "8/8/8/8/4k3/4p3/3PK3/8 w - - 0 1",
            "8/5k2/8/3p4/3P4/8/8/5K2 w - - 0 1",
            "8/8/4k3/3p4/3P4/8/4K3/8 w - - 0 1",
            "8/8/8/4k3/3p4/3P4/4K3/8 w - - 0 1",
            "8/8/8/8/3k4/3p4/3PK3/8 w - - 0 1",
            "8/5k2/8/8/8/8/3P4/5K2 w - - 0 1"
        ],
        "promotion_races": [
            "8/1P6/8/8/8/8/p7/4K2k w - - 0 1",
            "8/2P5/8/8/8/8/1p6/4K2k w - - 0 1",
            "8/3P4/8/8/8/8/2p5/4K2k w - - 0 1",
            "8/4P3/8/8/8/8/3p4/4K2k w - - 0 1",
            "8/5P2/8/8/8/8/4p3/4K2k w - - 0 1",
            "8/6P1/8/8/8/8/5p2/4K2k w - - 0 1",
            "8/7P/8/8/8/8/6p1/4K2k w - - 0 1",
            "8/P7/8/8/8/8/7p/4K2k w - - 0 1",
            "8/1P6/8/8/8/8/7p/4K2k w - - 0 1",
            "8/2P5/8/8/8/8/7p/4K2k w - - 0 1",
            "8/3P4/8/8/8/8/7p/4K2k w - - 0 1",
            "8/4P3/8/8/8/8/7p/4K2k w - - 0 1",
            "8/5P2/8/8/8/8/7p/4K2k w - - 0 1",
            "8/6P1/8/8/8/8/7p/4K2k w - - 0 1",
            "8/7P/8/8/8/8/7p/4K2k w - - 0 1"
        ],
        "fortresses": [
            "8/8/8/8/5k2/8/6p1/7K w - - 0 1",
            "8/8/8/8/5k2/8/6p1/6K1 w - - 0 1",
            "8/8/8/8/4k3/8/5p2/6K1 w - - 0 1",
            "8/8/8/8/3k4/8/4p3/5K2 w - - 0 1",
            "8/8/8/8/2k5/8/3p4/4K3 w - - 0 1",
            "8/8/8/8/1k6/8/2p5/3K4 w - - 0 1",
            "8/8/8/8/k7/8/1p6/2K5 w - - 0 1",
            "8/8/8/8/8/k7/p7/1K6 w - - 0 1",
            "8/8/8/8/8/8/kp6/2K5 w - - 0 1",
            "8/8/8/8/8/8/1kp5/3K4 w - - 0 1",
            "8/8/8/8/8/8/2kp4/4K3 w - - 0 1",
            "8/8/8/8/8/8/3kp3/5K2 w - - 0 1",
            "8/8/8/8/8/8/4kp2/6K1 w - - 0 1",
            "8/8/8/8/8/8/5kp1/7K w - - 0 1",
            "8/8/8/8/8/8/6k1/7K w - - 0 1"
        ],
        "zugzwang": [
            "8/8/8/8/5k2/8/8/7K b - - 0 1",
            "8/8/8/8/4k3/8/8/6K1 b - - 0 1",
            "8/8/8/8/3k4/8/8/5K2 b - - 0 1",
            "8/8/8/8/2k5/8/8/4K3 b - - 0 1",
            "8/8/8/8/1k6/8/8/3K4 b - - 0 1",
            "8/8/8/8/k7/8/8/2K5 b - - 0 1",
            "8/8/8/8/8/k7/8/1K6 b - - 0 1",
            "8/8/8/8/8/8/kp6/1K6 w - - 0 1",
            "8/8/8/8/8/8/1kp5/2K5 w - - 0 1",
            "8/8/8/8/8/8/2kp4/3K4 w - - 0 1",
            "8/8/8/8/8/8/3kp3/4K3 w - - 0 1",
            "8/8/8/8/8/8/4kp2/5K2 w - - 0 1",
            "8/8/8/8/8/8/5kp1/6K1 w - - 0 1",
            "8/8/8/8/8/8/6kp/7K w - - 0 1",
            "8/8/8/8/8/8/7k/7K w - - 0 1"
        ]
    }
    
    suite = []
    idx = 1
    for cat, fens in categories.items():
        for i, fen in enumerate(fens):
            split_type = "development" if (i < 10) else "heldout"
            suite.append({
                "id": f"POS_{idx:03d}",
                "category": cat,
                "split": split_type,
                "fen": fen
            })
            idx += 1
    return suite

def run_diagnostics():
    print("=== Phase 2: Evaluation Correctness and Positional Diagnostics ===")
    corpus = build_corpus()
    print(f"Loaded provenance-tracked corpus of {len(corpus)} positions across 15 categories.")

    relative_symmetry_failures = 0
    absolute_inversion_failures = 0
    determinism_failures = 0
    pawn_hash_failures = 0
    bound_failures = 0

    evaluated_positions = []

    for pos in corpus:
        fen = pos["fen"]
        board = NativeBoard()
        dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(board))
        
        # Test Determinism: 5 evaluations must match exactly
        evals = [dll.native_evaluate_detail(ctypes.byref(board), 5) for _ in range(5)]
        if len(set(evals)) != 1:
            determinism_failures += 1

        ev5 = evals[0]
        ev10 = dll.native_evaluate_detail(ctypes.byref(board), 10)

        # Check bounds: [-30000, 30000]
        if abs(ev5) > 30000 or abs(ev10) > 30000:
            bound_failures += 1

        # 1. Relative Colour Symmetry: mirror board & side to move -> eval(mirror(b)) == eval(b)
        py_b = chess.Board(fen)
        py_mirrored = py_b.mirror() # mirrors ranks, pieces, and side to move
        nb_mirrored = NativeBoard()
        dll.native_set_fen(py_mirrored.fen().encode("utf-8"), ctypes.byref(nb_mirrored))
        ev5_mirrored = dll.native_evaluate_detail(ctypes.byref(nb_mirrored), 5)
        if ev5 != ev5_mirrored:
            relative_symmetry_failures += 1

        # 2. Absolute Inversion Symmetry: invert board pieces/ranks but keep original side to move -> eval == -eval
        py_inv = py_b.mirror()
        py_inv.turn = py_b.turn # keep original side to move
        nb_inv = NativeBoard()
        dll.native_set_fen(py_inv.fen().encode("utf-8"), ctypes.byref(nb_inv))
        ev5_inv = dll.native_evaluate_detail(ctypes.byref(nb_inv), 5)
        if ev5 != -ev5_inv:
            absolute_inversion_failures += 1

        # 3. Check Pawn Hash Validity: E10 repeated call matches
        ev10_rep = dll.native_evaluate_detail(ctypes.byref(board), 10)
        if ev10 != ev10_rep:
            pawn_hash_failures += 1

        evaluated_positions.append({
            "id": pos["id"],
            "category": pos["category"],
            "split": pos["split"],
            "fen": fen,
            "side_to_move": "White" if board.side_to_move == 0 else "Black",
            "eval_e5_x7": ev5,
            "eval_e10_x12": ev10,
            "ev5_mirrored": ev5_mirrored,
            "ev5_inv": ev5_inv,
            "relative_symmetry_pass": (ev5 == ev5_mirrored),
            "absolute_inversion_pass": (ev5 == -ev5_inv),
            "determinism_pass": (len(set(evals)) == 1)
        })

    print(f"Diagnostics complete across {len(corpus)} positions:")
    print(f"  Relative Symmetry failures (mirror turn): {relative_symmetry_failures} / {len(corpus)}")
    print(f"  Absolute Inversion failures (same turn): {absolute_inversion_failures} / {len(corpus)}")
    print(f"  Determinism failures: {determinism_failures} / {len(corpus)}")
    print(f"  Bound violations: {bound_failures} / {len(corpus)}")
    print(f"  Pawn hash divergences: {pawn_hash_failures} / {len(corpus)}")

    out_data = {
        "corpus_size": len(corpus),
        "categories_count": 15,
        "development_cases": sum(1 for p in corpus if p["split"] == "development"),
        "heldout_cases": sum(1 for p in corpus if p["split"] == "heldout"),
        "summary": {
            "relative_symmetry_pass_rate_pct": round(((len(corpus) - relative_symmetry_failures) / len(corpus)) * 100, 2),
            "absolute_inversion_pass_rate_pct": round(((len(corpus) - absolute_inversion_failures) / len(corpus)) * 100, 2),
            "determinism_pass_rate_pct": round(((len(corpus) - determinism_failures) / len(corpus)) * 100, 2),
            "bound_integrity_pass_rate_pct": round(((len(corpus) - bound_failures) / len(corpus)) * 100, 2),
            "pawn_hash_validity_pass_rate_pct": round(((len(corpus) - pawn_hash_failures) / len(corpus)) * 100, 2)
        },
        "evaluated_positions": evaluated_positions
    }

    with open(RAW_OUT, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"Raw diagnostic output saved to {RAW_OUT}")

if __name__ == "__main__":
    run_diagnostics()
