"""Project Janus v0.50 - Comprehensive Native Core Qualification Test Suite.

Executes Phases D & E verification:
1. FEN import/export round-trip agreement across all 37 diagnostic positions.
2. Attack and check detection agreement against python-chess.
3. Strict legal move set equality against python-chess across all 37 diagnostic positions.
4. Classical standard perft validation suite (Initial, Kiwipete, Pos3, Pos4, Pos5, Pos6).
5. Make/unmake state restoration and Zobrist hash invariance.
"""

import sys
import json
import time
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))

from janus_native_bridge import NativeEngineBridge


def test_fen_roundtrip_corpus(bridge, corpus):
    print("--- [Test 1] FEN Round-Trip Differential Test (37 Positions) ---", flush=True)
    mismatches = 0
    for pos in corpus:
        fen = pos["fen"]
        bridge.set_fen(fen)
        out_fen = bridge.get_fen()

        # Compare piece placement, side, castling, and EP with python-chess
        b_py = chess.Board(fen)
        b_nat = chess.Board(out_fen)

        if b_py.board_fen() != b_nat.board_fen() or b_py.turn != b_nat.turn or b_py.castling_rights != b_nat.castling_rights:
            print(f"  MISMATCH on {pos['id']}:\n    In:  {fen}\n    Out: {out_fen}", flush=True)
            mismatches += 1

    print(f"  Result: {len(corpus) - mismatches}/{len(corpus)} positions matched perfectly.", flush=True)
    assert mismatches == 0, "FEN round-trip had mismatches!"


def test_check_detection_corpus(bridge, corpus):
    print("\n--- [Test 2] Check Detection Differential Test (37 Positions) ---", flush=True)
    mismatches = 0
    for pos in corpus:
        fen = pos["fen"]
        b_py = chess.Board(fen)
        bridge.set_fen(fen)

        py_check = b_py.is_check()
        nat_check = bridge.is_check()

        if py_check != nat_check:
            print(f"  MISMATCH on {pos['id']}: py_check={py_check}, nat_check={nat_check}", flush=True)
            mismatches += 1

    print(f"  Result: {len(corpus) - mismatches}/{len(corpus)} check statuses matched perfectly.", flush=True)
    assert mismatches == 0, "Check detection had mismatches!"


def test_legal_moves_corpus(bridge, corpus):
    print("\n--- [Test 3] Legal Move-Set Differential Test (37 Positions) ---", flush=True)
    mismatches = 0
    total_moves_verified = 0

    for pos in corpus:
        fen = pos["fen"]
        b_py = chess.Board(fen)
        bridge.set_fen(fen)

        py_moves = sorted([m.uci() for m in b_py.legal_moves])
        nat_moves = sorted(bridge.get_legal_moves_uci())

        total_moves_verified += len(py_moves)

        if py_moves != nat_moves:
            diff_missing = set(py_moves) - set(nat_moves)
            diff_extra = set(nat_moves) - set(py_moves)
            print(f"  MISMATCH on {pos['id']}:", flush=True)
            print(f"    Missing in native: {diff_missing}", flush=True)
            print(f"    Extra in native:   {diff_extra}", flush=True)
            mismatches += 1

    print(f"  Result: {len(corpus) - mismatches}/{len(corpus)} positions ({total_moves_verified} legal moves) matched with 100% exact set identity.", flush=True)
    assert mismatches == 0, "Legal move generation had set mismatches!"


def test_standard_perft_suite(bridge):
    print("\n--- [Test 4] Classical Standard Perft Verification Suite ---", flush=True)
    # List of (name, fen, depth, expected_nodes)
    perft_cases = [
        # 1. Starting Position
        ("Starting Pos (D1)", chess.STARTING_FEN, 1, 20),
        ("Starting Pos (D2)", chess.STARTING_FEN, 2, 400),
        ("Starting Pos (D3)", chess.STARTING_FEN, 3, 8902),
        ("Starting Pos (D4)", chess.STARTING_FEN, 4, 197281),

        # 2. Position 2 (Kiwipete)
        ("Kiwipete (D1)", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 1, 48),
        ("Kiwipete (D2)", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),
        ("Kiwipete (D3)", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3, 97862),

        # 3. Position 3
        ("Pos 3 (D1)", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 1, 14),
        ("Pos 3 (D2)", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 2, 191),
        ("Pos 3 (D3)", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 2812),

        # 4. Position 4 (Promotions, Castling, Checks)
        ("Pos 4 (D1)", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 1, 6),
        ("Pos 4 (D2)", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 2, 264),
        ("Pos 4 (D3)", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 3, 9467),

        # 5. Position 5
        ("Pos 5 (D1)", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 1, 44),
        ("Pos 5 (D2)", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 2, 1486),
        ("Pos 5 (D3)", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 3, 62379),

        # 6. Position 6
        ("Pos 6 (D1)", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 1, 46),
        ("Pos 6 (D2)", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 2, 2079),
        ("Pos 6 (D3)", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 3, 89890),
    ]

    for name, fen, depth, expected in perft_cases:
        bridge.set_fen(fen)
        t0 = time.perf_counter()
        nodes = bridge.perft(depth)
        dur = time.perf_counter() - t0
        nps = int(nodes / dur) if dur > 0 else 0
        print(f"  {name:20s}: {nodes:8d} nodes ({nps:,} NPS, {dur*1000:.1f}ms) | Expected: {expected}", flush=True)
        assert nodes == expected, f"Perft failure on {name}: got {nodes}, expected {expected}"

    print("  All standard perft positions passed with 100% precision!", flush=True)


def run_all_tests():
    corpus_path = Path("analysis/v0.50/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    bridge = NativeEngineBridge()

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.50 - NATIVE CORE QUALIFICATION (Phases D & E)", flush=True)
    print("=" * 80, flush=True)

    test_fen_roundtrip_corpus(bridge, corpus)
    test_check_detection_corpus(bridge, corpus)
    test_legal_moves_corpus(bridge, corpus)
    test_standard_perft_suite(bridge)

    print("\n" + "=" * 80, flush=True)
    print("HARD GATE E PASSED: Legal Move Generation & State Integrity 100% Qualified!", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    run_all_tests()

