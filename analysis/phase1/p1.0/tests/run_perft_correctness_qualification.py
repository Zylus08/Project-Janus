#!/usr/bin/env python3
"""
Project Janus Phase 1 — Milestone P1.0
Correctness and Perft Qualification Pipeline.

Validates:
1. Standard Perft Suite against verified ground-truth reference counts.
2. Edge cases: En Passant, Castling, Promotions, Checks, Pins, Stalemate.
3. Draw Semantics: Threefold repetition, 50-move rule, Insufficient material.
4. Randomized Playout Stress Test: 100 games exercising state restoration & Zobrist hashing.
"""

import sys
import os
import json
import time
import random
import importlib.util
from pathlib import Path

# Add project root and native bridge
ROOT = Path(__file__).resolve().parents[4]
bridge_path = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge", bridge_path)
bridge_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_mod)

NativeEngineBridge = bridge_mod.NativeEngineBridge
UndoInfo = bridge_mod.UndoInfo

import chess

# Ground Truth Perft References (Chess Programming Wiki / Stockfish Reference)
PERFT_TEST_SUITE = [
    {
        "id": "PERFT_01_STARTPOS",
        "name": "Standard Initial Position",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "expected": {
            1: 20,
            2: 400,
            3: 8902,
            4: 197281,
            5: 4865609
        }
    },
    {
        "id": "PERFT_02_KIWIPETE",
        "name": "Kiwipete (Complex Tactically & Castling/EP)",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "expected": {
            1: 48,
            2: 2039,
            3: 97862,
            4: 4085603
        }
    },
    {
        "id": "PERFT_03_SILVER_SUITE",
        "name": "Silver Suite (Endgame & King Walks)",
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "expected": {
            1: 14,
            2: 191,
            3: 2812,
            4: 43238,
            5: 674624
        }
    },
    {
        "id": "PERFT_04_POSITION_4",
        "name": "Position 4 (Promotions & Pinned Pawns)",
        "fen": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "expected": {
            1: 6,
            2: 264,
            3: 9467,
            4: 422333
        }
    },
    {
        "id": "PERFT_05_POSITION_5",
        "name": "Position 5 (Tactical King & Checking)",
        "fen": "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "expected": {
            1: 44,
            2: 1486,
            3: 62379,
            4: 2103487
        }
    },
    {
        "id": "PERFT_06_POSITION_6",
        "name": "Position 6 (Discovered Checks & Pin Arrays)",
        "fen": "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
        "expected": {
            1: 46,
            2: 2079,
            3: 89890,
            4: 3894594
        }
    }
]

def run_perft_tests(engine):
    print("=" * 80)
    print("PHASE 3: PERFT CORRECTNESS SUITE")
    print("=" * 80)
    
    results = []
    passed_positions = 0
    all_depths_passed = True
    
    for item in PERFT_TEST_SUITE:
        pid = item["id"]
        name = item["name"]
        fen = item["fen"]
        expected_dict = item["expected"]
        
        pos_res = {
            "id": pid,
            "name": name,
            "fen": fen,
            "depths": []
        }
        
        pos_passed = True
        print(f"\n[{pid}] {name}")
        
        for depth, expected_nodes in expected_dict.items():
            engine.set_fen(fen)
            t0 = time.perf_counter()
            actual_nodes = engine.perft(depth)
            t1 = time.perf_counter()
            elapsed_sec = t1 - t0
            nps = int(actual_nodes / max(elapsed_sec, 0.0001))
            
            is_match = (actual_nodes == expected_nodes)
            if not is_match:
                pos_passed = False
                all_depths_passed = False
                
            status_str = "PASS" if is_match else f"FAIL (expected {expected_nodes:,})"
            print(f"  Depth {depth}: nodes={actual_nodes:,} ({status_str}) in {elapsed_sec:.4f}s ({nps:,} NPS)")
            
            pos_res["depths"].append({
                "depth": depth,
                "expected_nodes": expected_nodes,
                "actual_nodes": actual_nodes,
                "match": is_match,
                "elapsed_sec": round(elapsed_sec, 4),
                "nps": nps
            })
            
        if pos_passed:
            passed_positions += 1
            
        pos_res["passed"] = pos_passed
        results.append(pos_res)
        
    return results, all_depths_passed

def run_edge_case_and_draw_tests(engine):
    print("\n" + "=" * 80)
    print("PHASE 3: EDGE CASES & FIDE DRAW SEMANTICS")
    print("=" * 80)
    
    edge_results = []
    
    # 1. Stalemate Detection
    stalemate_fen = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    engine.set_fen(stalemate_fen)
    moves_sm = engine.get_legal_moves_uci()
    is_sm_check = engine.is_check()
    sm_pass = (len(moves_sm) == 0 and not is_sm_check)
    print(f"1. Stalemate Detection: {'PASS' if sm_pass else 'FAIL'} (Legal moves={len(moves_sm)}, InCheck={is_sm_check})")
    edge_results.append({"test": "Stalemate", "pass": sm_pass, "details": f"moves={len(moves_sm)}, in_check={is_sm_check}"})
    
    # 2. Checkmate Detection
    checkmate_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    engine.set_fen(checkmate_fen)
    moves_cm = engine.get_legal_moves_uci()
    is_cm_check = engine.is_check()
    cm_pass = (len(moves_cm) == 0 and is_cm_check)
    print(f"2. Checkmate Detection: {'PASS' if cm_pass else 'FAIL'} (Legal moves={len(moves_cm)}, InCheck={is_cm_check})")
    edge_results.append({"test": "Checkmate", "pass": cm_pass, "details": f"moves={len(moves_cm)}, in_check={is_cm_check}"})
    
    # 3. Pinned En Passant Horizontal Pin (Black Rook a5, White Pawn e5, Black Pawn d5, White King h5)
    # Both e5 and d5 vacate 5th rank upon e5xd6, exposing White King on h5 to Black Rook on a5.
    rank_pin_fen = "8/8/8/r2pP2K/8/8/8/8 w - d6 0 1"
    engine.set_fen(rank_pin_fen)
    moves_rpin = engine.get_legal_moves_uci()
    rpin_pass = ("e5d6" not in moves_rpin)
    print(f"3. Pinned En Passant Horizontal Pin: {'PASS' if rpin_pass else 'FAIL'} ('e5d6' in legal moves: {'e5d6' in moves_rpin})")
    edge_results.append({"test": "Pinned En Passant", "pass": rpin_pass, "details": f"'e5d6' in moves: {'e5d6' in moves_rpin}"})
    
    # 4. Castling While in Check (Black Rook on e2 checking White King on e1)
    castle_in_check_fen = "r3k2r/8/8/8/8/8/4r3/R3K2R w KQkq - 0 1"
    engine.set_fen(castle_in_check_fen)
    moves_cic = engine.get_legal_moves_uci()
    cic_pass = ("e1g1" not in moves_cic and "e1c1" not in moves_cic)
    print(f"4. Castling While in Check: {'PASS' if cic_pass else 'FAIL'} (Castling generated: {'e1g1' in moves_cic or 'e1c1' in moves_cic})")
    edge_results.append({"test": "Castling In Check", "pass": cic_pass, "details": f"castling generated: {'e1g1' in moves_cic or 'e1c1' in moves_cic}"})
    
    # 5. Castling Through Attacked Square:
    # 5a. Queenside transit c1 attacked by Black Bishop on f4
    castle_c1_attacked_fen = "r3k2r/8/8/8/5b2/8/8/R3K2R w KQkq - 0 1"
    engine.set_fen(castle_c1_attacked_fen)
    moves_c1 = engine.get_legal_moves_uci()
    c1_pass = ("e1c1" not in moves_c1 and "e1g1" in moves_c1)
    print(f"5a. Queenside Castling Blocked (c1 attacked): {'PASS' if c1_pass else 'FAIL'} (O-O-O: {'e1c1' in moves_c1}, O-O: {'e1g1' in moves_c1})")
    edge_results.append({"test": "Queenside Castling Blocked", "pass": c1_pass, "details": f"O-O-O: {'e1c1' in moves_c1}, O-O: {'e1g1' in moves_c1}"})

    # 5b. Kingside transit f1 attacked by Black Bishop on c4
    castle_f1_attacked_fen = "r3k2r/8/8/8/2b5/8/8/R3K2R w KQkq - 0 1"
    engine.set_fen(castle_f1_attacked_fen)
    moves_f1 = engine.get_legal_moves_uci()
    f1_pass = ("e1g1" not in moves_f1 and "e1c1" in moves_f1)
    print(f"5b. Kingside Castling Blocked (f1 attacked): {'PASS' if f1_pass else 'FAIL'} (O-O: {'e1g1' in moves_f1}, O-O-O: {'e1c1' in moves_f1})")
    edge_results.append({"test": "Kingside Castling Blocked", "pass": f1_pass, "details": f"O-O: {'e1g1' in moves_f1}, O-O-O: {'e1c1' in moves_f1}"})

    # 6. Fifty-Move Rule
    fifty_fen = "8/8/4k3/8/8/4K3/8/8 w - - 100 51"
    engine.set_fen(fifty_fen)
    is_50 = engine.can_claim_fifty_moves()
    print(f"6. Fifty-Move Rule (halfmove=100): {'PASS' if is_50 else 'FAIL'} (can_claim_fifty_moves={is_50})")
    edge_results.append({"test": "Fifty-Move Rule", "pass": is_50, "details": f"can_claim_fifty_moves={is_50}"})

    # 7. Insufficient Material (K vs K)
    insuf_fen = "8/8/4k3/8/8/4K3/8/8 w - - 0 1"
    engine.set_fen(insuf_fen)
    is_insuf = engine.is_insufficient_material()
    print(f"7. Insufficient Material (K vs K): {'PASS' if is_insuf else 'FAIL'} (is_insufficient_material={is_insuf})")
    edge_results.append({"test": "Insufficient Material", "pass": is_insuf, "details": f"is_insufficient_material={is_insuf}"})

    # 8. Threefold Repetition
    engine.reset_history()
    engine.set_fen(chess.STARTING_FEN)
    engine.push_history(engine.board.zobrist_key)
    moves_seq = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]
    for m_str in moves_seq:
        m = engine.parse_uci(m_str)
        ok, undo = engine.make_move(m)
        engine.push_history(engine.board.zobrist_key)
        
    is_rep3 = engine.is_repetition(3)
    print(f"8. Threefold Repetition Detection: {'PASS' if is_rep3 else 'FAIL'} (is_repetition(3)={is_rep3})")
    edge_results.append({"test": "Threefold Repetition", "pass": is_rep3, "details": f"is_repetition(3)={is_rep3}"})

    return edge_results

def run_randomized_playout_stress(engine, num_games=100):
    print("\n" + "=" * 80)
    print(f"PHASE 3: RANDOMIZED LEGAL PLAYOUT STRESS TEST ({num_games} GAMES)")
    print("=" * 80)
    
    random.seed(42)
    total_positions = 0
    mismatches = 0
    hash_mismatches = 0
    
    t0 = time.perf_counter()
    
    for g in range(num_games):
        engine.set_fen(chess.STARTING_FEN)
        py_b = chess.Board()
        
        for move_idx in range(60): # 60 plies per game
            legal_moves_uci = engine.get_legal_moves_uci()
            if len(legal_moves_uci) == 0:
                break
                
            m_uci = random.choice(legal_moves_uci)
            m = engine.parse_uci(m_uci)
            py_m = chess.Move.from_uci(m_uci)
            
            ok, undo = engine.make_move(m)
            total_positions += 1
            
            py_b.push(py_m)
            
            # Check FEN consistency
            native_fen = engine.get_fen()
            py_fen = py_b.fen()
            
            native_parts = native_fen.split()
            py_parts = py_fen.split()
            
            if native_parts[0] != py_parts[0] or native_parts[1] != py_parts[1]:
                mismatches += 1
                
            # Verify unmake move reversibility
            z_after = engine.board.zobrist_key
            engine.unmake_move(m, undo)
            
            restored_fen = engine.get_fen()
            py_b.pop()
            pre_py_fen = py_b.fen()
            if restored_fen.split()[0] != pre_py_fen.split()[0]:
                mismatches += 1
                
            # Re-make move to continue game
            engine.make_move(m)
            py_b.push(py_m)
            
            if engine.board.zobrist_key != z_after:
                hash_mismatches += 1
                
    t1 = time.perf_counter()
    stress_pass = (mismatches == 0 and hash_mismatches == 0)
    print(f"Playout Summary: {total_positions:,} positions across {num_games} games in {t1 - t0:.2f}s")
    print(f"Board State Mismatches : {mismatches}")
    print(f"Zobrist Hash Invariance : {hash_mismatches} mismatches")
    print(f"Status                 : {'PASS (100% Bit-Exact Invariance)' if stress_pass else 'FAIL'}")
    
    return {
        "num_games": num_games,
        "total_positions_exercised": total_positions,
        "board_state_mismatches": mismatches,
        "zobrist_hash_mismatches": hash_mismatches,
        "elapsed_sec": round(t1 - t0, 3),
        "passed": stress_pass
    }

def main():
    engine = NativeEngineBridge()
    
    perft_results, perft_pass = run_perft_tests(engine)
    edge_results = run_edge_case_and_draw_tests(engine)
    stress_results = run_randomized_playout_stress(engine, num_games=100)
    
    overall_qualification_passed = perft_pass and all(r["pass"] for r in edge_results) and stress_results["passed"]
    
    payload = {
        "metadata": {
            "milestone": "P1.0",
            "date": "2026-11-09",
            "engine": "Janus Classical Baseline C1 (Native N5 Frozen)",
            "overall_qualification_passed": overall_qualification_passed
        },
        "perft_suite": perft_results,
        "edge_cases": edge_results,
        "stress_test": stress_results
    }
    
    out_path = ROOT / "analysis" / "phase1" / "p1.0" / "tests" / "perft_qualification_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved qualification telemetry to {out_path}")
    
    print("\n" + "=" * 80)
    print(f"CORRECTNESS & PERFT QUALIFICATION VERDICT: {'QUALIFIED (PASS)' if overall_qualification_passed else 'CORRECTNESS REPAIR REQUIRED (FAIL)'}")
    print("=" * 80)
    
    if not overall_qualification_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
