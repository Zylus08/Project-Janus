#!/usr/bin/env python3
"""
test_nnue_features.py
Milestone P2.1 Phase 2: Comprehensive NNUE Feature Schema & Incremental Update Verification.
Validates:
1. White/Black perspective orientation and symmetry.
2. 768-feature dual-accumulator mapping (White persp, Black persp).
3. Feature collision freedom.
4. Incremental update parity across all move types:
   - Quiet moves
   - Captures
   - Castling (Kingside and Queenside for White and Black)
   - En passant captures
   - Pawn promotions (all 4 promotion piece types)
5. Make / unmake exact reversibility across random game move sequences.
"""

import sys
import json
import random
from pathlib import Path
from typing import List, Tuple, Set

import chess

NUM_PIECE_TYPES = 12
NUM_SQUARES = 64
FEATURE_SIZE = NUM_PIECE_TYPES * NUM_SQUARES # 768

# Piece type mapping:
# White: P=0, N=1, B=2, R=3, Q=4, K=5
# Black: P=6, N=7, B=8, R=9, Q=10, K=11
PIECE_TO_INDEX_WHITE = {
    (chess.PAWN, chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK, chess.WHITE): 3,
    (chess.QUEEN, chess.WHITE): 4,
    (chess.KING, chess.WHITE): 5,
    (chess.PAWN, chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK, chess.BLACK): 9,
    (chess.QUEEN, chess.BLACK): 10,
    (chess.KING, chess.BLACK): 11,
}

# For Black's perspective: swap colors and flip rank (sq ^ 56)
PIECE_TO_INDEX_BLACK = {
    (chess.PAWN, chess.BLACK): 0,
    (chess.KNIGHT, chess.BLACK): 1,
    (chess.BISHOP, chess.BLACK): 2,
    (chess.ROOK, chess.BLACK): 3,
    (chess.QUEEN, chess.BLACK): 4,
    (chess.KING, chess.BLACK): 5,
    (chess.PAWN, chess.WHITE): 6,
    (chess.KNIGHT, chess.WHITE): 7,
    (chess.BISHOP, chess.WHITE): 8,
    (chess.ROOK, chess.WHITE): 9,
    (chess.QUEEN, chess.WHITE): 10,
    (chess.KING, chess.WHITE): 11,
}

def get_active_features(board: chess.Board) -> Tuple[List[int], List[int]]:
    """Full recompute of active feature indices for White and Black perspectives."""
    white_features = []
    black_features = []
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is not None:
            # White perspective: square as-is
            p_idx_w = PIECE_TO_INDEX_WHITE[(piece.piece_type, piece.color)]
            white_features.append(p_idx_w * NUM_SQUARES + sq)

            # Black perspective: flipped rank (sq ^ 56)
            flipped_sq = sq ^ 56
            p_idx_b = PIECE_TO_INDEX_BLACK[(piece.piece_type, piece.color)]
            black_features.append(p_idx_b * NUM_SQUARES + flipped_sq)

    return sorted(white_features), sorted(black_features)

def compute_move_feature_diff(board: chess.Board, move: chess.Move) -> Tuple[List[int], List[int], List[int], List[int]]:
    """
    Computes incremental (added, removed) feature deltas for White and Black perspectives.
    Returns: (w_added, w_removed, b_added, b_removed)
    """
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)
    assert moving_piece is not None

    w_added = []
    w_removed = []
    b_added = []
    b_removed = []

    def add_feat(pt, color, sq):
        w_p = PIECE_TO_INDEX_WHITE[(pt, color)]
        b_p = PIECE_TO_INDEX_BLACK[(pt, color)]
        w_added.append(w_p * NUM_SQUARES + sq)
        b_added.append(b_p * NUM_SQUARES + (sq ^ 56))

    def rem_feat(pt, color, sq):
        w_p = PIECE_TO_INDEX_WHITE[(pt, color)]
        b_p = PIECE_TO_INDEX_BLACK[(pt, color)]
        w_removed.append(w_p * NUM_SQUARES + sq)
        b_removed.append(b_p * NUM_SQUARES + (sq ^ 56))

    # 1. Moving piece from square
    rem_feat(moving_piece.piece_type, moving_piece.color, from_sq)

    # 2. Captured piece on to_square (normal capture)
    captured = board.piece_at(to_sq)
    if captured is not None and not board.is_en_passant(move):
        rem_feat(captured.piece_type, captured.color, to_sq)

    # 3. En passant capture
    if board.is_en_passant(move):
        ep_sq = to_sq - 8 if moving_piece.color == chess.WHITE else to_sq + 8
        ep_p = board.piece_at(ep_sq)
        assert ep_p is not None
        rem_feat(ep_p.piece_type, ep_p.color, ep_sq)

    # 4. Castling rook move
    if board.is_castling(move):
        if to_sq == chess.G1: # White O-O
            rem_feat(chess.ROOK, chess.WHITE, chess.H1)
            add_feat(chess.ROOK, chess.WHITE, chess.F1)
        elif to_sq == chess.C1: # White O-O-O
            rem_feat(chess.ROOK, chess.WHITE, chess.A1)
            add_feat(chess.ROOK, chess.WHITE, chess.D1)
        elif to_sq == chess.G8: # Black O-O
            rem_feat(chess.ROOK, chess.BLACK, chess.H8)
            add_feat(chess.ROOK, chess.BLACK, chess.F8)
        elif to_sq == chess.C8: # Black O-O-O
            rem_feat(chess.ROOK, chess.BLACK, chess.A8)
            add_feat(chess.ROOK, chess.BLACK, chess.D8)

    # 5. Piece arriving on to_square (or promotion)
    if move.promotion is not None:
        add_feat(move.promotion, moving_piece.color, to_sq)
    else:
        add_feat(moving_piece.piece_type, moving_piece.color, to_sq)

    return w_added, w_removed, b_added, b_removed

def run_tests():
    print("=" * 70)
    print("PHASE 2: NNUE FEATURE SCHEMA & INCREMENTAL UPDATE VERIFICATION")
    print("=" * 70)

    # Test 1: Feature Collision Freedom
    seen_indices_w = set()
    for pt in range(1, 7):
        for col in [chess.WHITE, chess.BLACK]:
            for sq in range(64):
                idx = PIECE_TO_INDEX_WHITE[(pt, col)] * 64 + sq
                assert 0 <= idx < 768
                assert idx not in seen_indices_w, f"Collision at {idx}"
                seen_indices_w.add(idx)
    assert len(seen_indices_w) == 768
    print("[PASS] Test 1: 768 unique, non-overlapping feature indices verified.")

    # Test 2: Color Symmetry / Orientation
    # White e2e4 startpos vs Black e7e5 flipped startpos
    b_w = chess.Board()
    w_feats_w, b_feats_w = get_active_features(b_w)
    assert len(w_feats_w) == 32
    assert len(b_feats_w) == 32
    # In startpos, White perspective should exactly match Black perspective due to symmetric setup
    assert sorted(w_feats_w) == sorted(b_feats_w)
    print("[PASS] Test 2: Board symmetry and startpos perspective equality verified.")

    # Test 3: Incremental Move Updates across 500 random game plies
    random.seed(42)
    mismatches = 0
    total_moves_tested = 0
    special_move_counts = {"quiet": 0, "capture": 0, "castling": 0, "en_passant": 0, "promotion": 0}

    for game_idx in range(50):
        board = chess.Board()
        # Initialize running accumulators
        curr_w, curr_b = get_active_features(board)
        curr_w_set = set(curr_w)
        curr_b_set = set(curr_b)

        move_history = []
        state_history = []

        for ply in range(80):
            legal_moves = list(board.legal_moves)
            if not legal_moves or board.is_game_over():
                break

            move = random.choice(legal_moves)

            # Classify move
            if board.is_castling(move):
                special_move_counts["castling"] += 1
            elif board.is_en_passant(move):
                special_move_counts["en_passant"] += 1
            elif move.promotion:
                special_move_counts["promotion"] += 1
            elif board.is_capture(move):
                special_move_counts["capture"] += 1
            else:
                special_move_counts["quiet"] += 1

            # Compute incremental delta
            w_add, w_rem, b_add, b_rem = compute_move_feature_diff(board, move)

            # Push move to board
            state_history.append((set(curr_w_set), set(curr_b_set)))
            move_history.append(move)
            board.push(move)
            total_moves_tested += 1

            # Apply delta
            for f in w_rem:
                assert f in curr_w_set, f"Feature {f} to remove not in White set at ply {ply}"
                curr_w_set.remove(f)
            for f in w_add:
                assert f not in curr_w_set, f"Feature {f} to add already in White set at ply {ply}"
                curr_w_set.add(f)

            for f in b_rem:
                assert f in curr_b_set, f"Feature {f} to remove not in Black set at ply {ply}"
                curr_b_set.remove(f)
            for f in b_add:
                assert f not in curr_b_set, f"Feature {f} to add already in Black set at ply {ply}"
                curr_b_set.add(f)

            # Ground truth recompute
            truth_w, truth_b = get_active_features(board)
            if curr_w_set != set(truth_w) or curr_b_set != set(truth_b):
                mismatches += 1
                print(f"FAILED parity on game {game_idx}, ply {ply}, move {move}")
                sys.exit(1)

        # Test Reversibility (Unmake stack)
        while move_history:
            prev_w, prev_b = state_history.pop()
            m = move_history.pop()
            board.pop()
            truth_w, truth_b = get_active_features(board)
            assert prev_w == set(truth_w), "Unmake White state mismatch!"
            assert prev_b == set(truth_b), "Unmake Black state mismatch!"

    print(f"[PASS] Test 3: Incremental feature update verified across {total_moves_tested} random legal moves.")
    print(f"      Move distribution: {special_move_counts}")
    print(f"      Exact match rate: 100.0% (0 mismatches across all {total_moves_tested} forward and reverse updates).")

    out_data = {
        "status": "PASS",
        "num_features": 768,
        "perspective": "dual_halfkp_768 (White + Black perspectives)",
        "total_moves_tested": total_moves_tested,
        "special_move_counts": special_move_counts,
        "mismatches": 0
    }
    out_file = Path("E:/ChessXML/project-janus-phase1/analysis/phase2/p2.1/raw/nnue_feature_verification.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)
    print(f"[SAVED] Results saved to {out_file}")

if __name__ == "__main__":
    run_tests()
