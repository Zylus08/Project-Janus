import os
import sys
import json
import chess
import chess.pgn
import random

from halfkp import get_halfkp_features, HalfKPAccumulator, flip_square

def run_halfkp_test_suite():
    repo_root = r"E:\ChessXML\project-janus-phase1"
    print("=== PHASE 2: HALFKP-40960 COMPREHENSIVE TEST SUITE ===")
    
    test_cases = [
        ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
        ("castling_test_white", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"),
        ("castling_test_black", "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1"),
        ("en_passant_white", "8/8/8/3Pp3/8/8/8/4K2k w - e6 0 1"),
        ("en_passant_black", "4k2K/8/8/8/3pP3/8/8/8 b - e3 0 1"),
        ("promotion_white", "8/4P3/8/8/8/8/8/4K2k w - - 0 1"),
        ("promotion_black", "4K2k/8/8/8/8/8/4p3/8 b - - 0 1"),
        ("endgame_kpk", "8/8/8/8/4k3/8/4P3/4K3 w - - 0 1"),
        ("endgame_kqk", "8/8/8/3k4/8/8/4Q3/4K3 w - - 0 1"),
        ("tactical_pins", "r1bqk2r/pppp1ppp/2n5/4p3/1bB1n3/2NP1N2/PPP2PPP/R1BQK2R w KQkq - 0 6"),
        ("check_evasion", "7k/8/8/8/8/8/4q3/3K4 w - - 0 1")
    ]
    
    suite_results = []
    
    for name, fen in test_cases:
        board = chess.Board(fen)
        assert board.is_valid(), f"Board {name} is not valid!"
        wf, bf = get_halfkp_features(board)
        
        # Verify range
        assert all(0 <= idx < 40960 for idx in wf), f"White feature out of range in {name}"
        assert all(0 <= idx < 40960 for idx in bf), f"Black feature out of range in {name}"
        
        # Verify no duplicates
        assert len(wf) == len(set(wf)), f"Duplicate white features in {name}"
        assert len(bf) == len(set(bf)), f"Duplicate black features in {name}"
        
        # Active piece count should match non-king pieces
        non_kings = sum(1 for sq in chess.SQUARES if board.piece_at(sq) and board.piece_at(sq).piece_type != chess.KING)
        assert len(wf) == non_kings, f"Active feature count mismatch in {name}: got {len(wf)}, expected {non_kings}"
        assert len(bf) == non_kings, f"Active feature count mismatch in {name}: got {len(bf)}, expected {non_kings}"
        
        suite_results.append({
            "name": name,
            "fen": fen,
            "non_kings": non_kings,
            "white_active_features": len(wf),
            "black_active_features": len(bf),
            "status": "PASS"
        })
        print(f"[{name}] Non-kings: {non_kings}, Feature count: {len(wf)} -> PASS")
        
    # 2. Incremental Move Updates vs Fresh Recompute Oracle
    print("\nTesting Incremental Updates across all legal moves...")
    total_moves_tested = 0
    incremental_mismatches = 0
    refreshes_white = 0
    refreshes_black = 0
    
    random.seed(42)
    
    for name, fen in test_cases:
        board = chess.Board(fen)
        acc = HalfKPAccumulator()
        acc.refresh(board)
        
        for move in board.legal_moves:
            acc_copy = HalfKPAccumulator()
            acc_copy.white_indices = set(acc.white_indices)
            acc_copy.black_indices = set(acc.black_indices)
            acc_copy.white_king_sq = acc.white_king_sq
            acc_copy.black_king_sq = acc.black_king_sq
            
            w_ref, b_ref = acc_copy.apply_move(board, move)
            if w_ref: refreshes_white += 1
            if b_ref: refreshes_black += 1
            
            board_next = board.copy(stack=False)
            board_next.push(move)
            wf_expected, bf_expected = get_halfkp_features(board_next)
            
            if acc_copy.white_indices != set(wf_expected):
                print(f"MISMATCH White in {name} move {move}!")
                print(f"Diff: {acc_copy.white_indices.symmetric_difference(set(wf_expected))}")
                incremental_mismatches += 1
                
            if acc_copy.black_indices != set(bf_expected):
                print(f"MISMATCH Black in {name} move {move}!")
                print(f"Diff: {acc_copy.black_indices.symmetric_difference(set(bf_expected))}")
                incremental_mismatches += 1
                
            total_moves_tested += 1
            
    # Random walk from startpos for 200 plies x 20 games
    print("Testing 20 random-walk games (up to 100 plies each)...")
    for g in range(20):
        b = chess.Board()
        acc = HalfKPAccumulator()
        acc.refresh(b)
        
        for ply in range(100):
            if b.is_game_over():
                break
            legal = list(b.legal_moves)
            move = random.choice(legal)
            
            w_ref, b_ref = acc.apply_move(b, move)
            if w_ref: refreshes_white += 1
            if b_ref: refreshes_black += 1
            
            b.push(move)
            
            wf_exp, bf_exp = get_halfkp_features(b)
            if acc.white_indices != set(wf_exp) or acc.black_indices != set(bf_exp):
                print(f"Game {g} Ply {ply} Move {move} Mismatch!")
                incremental_mismatches += 1
                break
            total_moves_tested += 1
            
    print(f"\nTotal Moves Tested: {total_moves_tested}")
    print(f"Incremental Mismatches: {incremental_mismatches}")
    print(f"White King Refreshes: {refreshes_white}")
    print(f"Black King Refreshes: {refreshes_black}")
    
    assert incremental_mismatches == 0, f"Found {incremental_mismatches} mismatches!"
    
    # 3. Color Skew-Symmetry Test
    sym_board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    wf_sym, bf_sym = get_halfkp_features(sym_board)
    assert sorted(wf_sym) == sorted(bf_sym), "Startpos White and Black features do not match symmetrically!"
    print("Color Skew-Symmetry on Startpos: EXACT PASS")
    
    out_record = {
        "test_cases": suite_results,
        "total_moves_tested": total_moves_tested,
        "incremental_mismatches": incremental_mismatches,
        "refreshes_white": refreshes_white,
        "refreshes_black": refreshes_black,
        "color_symmetry_startpos": "PASS",
        "oracle_parity": "100.000%"
    }
    
    out_json = os.path.join(repo_root, "analysis/phase2/p2.3/raw/halfkp_feature_audit.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out_record, f, indent=2)
    print(f"HalfKP verification report written to {out_json}")

if __name__ == "__main__":
    run_halfkp_test_suite()
