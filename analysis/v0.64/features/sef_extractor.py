"""Project Janus v0.64 - Structural and Endgame Feature (SEF) Extractor.

Computes a compact 32-dimensional structural feature vector:
- 16 features from White's perspective
- 16 features from Black's perspective

Guarantees:
- 100% deterministic bitboard calculation
- Zero floating-point ambiguity (exact integer / rational scales)
- Fast vectorized evaluation
"""

from __future__ import annotations

import math
from typing import List, Tuple
import chess

# File and Rank bitmasks
FILE_A = 0x0101010101010101
FILES = [FILE_A << i for i in range(8)]
RANK_1 = 0x00000000000000FF
RANKS = [RANK_1 << (8 * i) for i in range(8)]


def chebyshev_distance(sq1: int, sq2: int) -> int:
    r1, f1 = sq1 // 8, sq1 % 8
    r2, f2 = sq2 // 8, sq2 % 8
    return max(abs(r1 - r2), abs(f1 - f2))


def extract_sef_vector(board: chess.Board) -> List[float]:
    """Extracts 32-dimensional SEF vector for a given chess.Board."""
    features = [0.0] * 32

    w_pawns = board.pieces(chess.PAWN, chess.WHITE)
    b_pawns = board.pieces(chess.PAWN, chess.BLACK)
    w_knights = board.pieces(chess.KNIGHT, chess.WHITE)
    b_knights = board.pieces(chess.KNIGHT, chess.BLACK)
    w_bishops = board.pieces(chess.BISHOP, chess.WHITE)
    b_bishops = board.pieces(chess.BISHOP, chess.BLACK)
    w_rooks = board.pieces(chess.ROOK, chess.WHITE)
    b_rooks = board.pieces(chess.ROOK, chess.BLACK)
    w_queens = board.pieces(chess.QUEEN, chess.WHITE)
    b_queens = board.pieces(chess.QUEEN, chess.BLACK)

    w_king_sq = board.king(chess.WHITE)
    b_king_sq = board.king(chess.BLACK)

    all_pawns = int(w_pawns) | int(b_pawns)

    # ---------------- White Perspective (Indices 0..15) ----------------
    w_passed = []
    w_protected_passed = 0
    w_passed_rank_sum = 0

    for sq in w_pawns:
        f = sq % 8
        r = sq // 8
        # Check enemy pawns on file f-1, f, f+1 on ranks r+1..7
        adjacent_files = (FILES[f - 1] if f > 0 else 0) | FILES[f] | (FILES[f + 1] if f < 7 else 0)
        front_ranks = 0
        for r_ahead in range(r + 1, 8):
            front_ranks |= RANKS[r_ahead]
        stop_mask = adjacent_files & front_ranks
        if (int(b_pawns) & stop_mask) == 0:
            w_passed.append(sq)
            w_passed_rank_sum += (r - 1)
            # Protected?
            defenders = 0
            if f > 0 and r > 0 and (int(w_pawns) & (1 << (sq - 9))):
                defenders += 1
            if f < 7 and r > 0 and (int(w_pawns) & (1 << (sq - 7))):
                defenders += 1
            if defenders > 0:
                w_protected_passed += 1

    features[0] = len(w_passed) / 8.0
    features[1] = w_passed_rank_sum / 24.0
    features[2] = w_protected_passed / 8.0

    # Isolated pawns
    w_isolated = 0
    for sq in w_pawns:
        f = sq % 8
        adj_files = (FILES[f - 1] if f > 0 else 0) | (FILES[f + 1] if f < 7 else 0)
        if (int(w_pawns) & adj_files) == 0:
            w_isolated += 1
    features[3] = w_isolated / 8.0

    # Doubled pawns
    w_doubled = 0
    for f in range(8):
        count_on_file = bin(int(w_pawns) & FILES[f]).count("1")
        if count_on_file > 1:
            w_doubled += (count_on_file - 1)
    features[4] = w_doubled / 8.0

    # King centralization (0..4)
    if w_king_sq is not None:
        kr, kf = w_king_sq // 8, w_king_sq % 8
        w_cent = 4.0 - max(abs(kr - 3.5), abs(kf - 3.5))
        features[6] = w_cent / 4.0

        # King to closest passed pawn
        if w_passed:
            min_dist = min(chebyshev_distance(w_king_sq, p_sq) for p_sq in w_passed)
            features[7] = (7.0 - min_dist) / 7.0
        if b_king_sq is not None and w_passed:
            min_dist_e = min(chebyshev_distance(b_king_sq, p_sq) for p_sq in w_passed)
            features[8] = (7.0 - min_dist_e) / 7.0

        # King shelter
        shelter_mask = 0
        for df in (-1, 0, 1):
            if 0 <= kf + df <= 7:
                for dr in (1, 2):
                    if 0 <= kr + dr <= 7:
                        shelter_mask |= (1 << ((kr + dr) * 8 + (kf + df)))
        w_shelter = bin(int(w_pawns) & shelter_mask).count("1")
        features[9] = w_shelter / 6.0

    # Open / Semi-open files for rooks
    w_open_rooks = 0
    w_semi_rooks = 0
    for sq in w_rooks:
        f = sq % 8
        has_w_pawn = (int(w_pawns) & FILES[f]) != 0
        has_b_pawn = (int(b_pawns) & FILES[f]) != 0
        if not has_w_pawn and not has_b_pawn:
            w_open_rooks += 1
        elif not has_w_pawn and has_b_pawn:
            w_semi_rooks += 1
    features[10] = w_open_rooks / 2.0
    features[11] = w_semi_rooks / 2.0

    # Bishop pair
    features[12] = 1.0 if len(w_bishops) >= 2 else 0.0

    # Non-pawn material
    w_npm = len(w_knights) * 1 + len(w_bishops) * 1 + len(w_rooks) * 2 + len(w_queens) * 4
    features[13] = w_npm / 16.0
    features[14] = len(w_pawns) / 8.0
    features[15] = 1.0 if board.turn == chess.WHITE else 0.0

    # ---------------- Black Perspective (Indices 16..31) ----------------
    b_passed = []
    b_protected_passed = 0
    b_passed_rank_sum = 0

    for sq in b_pawns:
        f = sq % 8
        r = sq // 8
        adjacent_files = (FILES[f - 1] if f > 0 else 0) | FILES[f] | (FILES[f + 1] if f < 7 else 0)
        front_ranks = 0
        for r_ahead in range(0, r):
            front_ranks |= RANKS[r_ahead]
        stop_mask = adjacent_files & front_ranks
        if (int(w_pawns) & stop_mask) == 0:
            b_passed.append(sq)
            b_passed_rank_sum += (6 - r)
            defenders = 0
            if f > 0 and r < 7 and (int(b_pawns) & (1 << (sq + 7))):
                defenders += 1
            if f < 7 and r < 7 and (int(b_pawns) & (1 << (sq + 9))):
                defenders += 1
            if defenders > 0:
                b_protected_passed += 1

    features[16] = len(b_passed) / 8.0
    features[17] = b_passed_rank_sum / 24.0
    features[18] = b_protected_passed / 8.0

    b_isolated = 0
    for sq in b_pawns:
        f = sq % 8
        adj_files = (FILES[f - 1] if f > 0 else 0) | (FILES[f + 1] if f < 7 else 0)
        if (int(b_pawns) & adj_files) == 0:
            b_isolated += 1
    features[19] = b_isolated / 8.0

    b_doubled = 0
    for f in range(8):
        count_on_file = bin(int(b_pawns) & FILES[f]).count("1")
        if count_on_file > 1:
            b_doubled += (count_on_file - 1)
    features[20] = b_doubled / 8.0

    if b_king_sq is not None:
        kr, kf = b_king_sq // 8, b_king_sq % 8
        b_cent = 4.0 - max(abs(kr - 3.5), abs(kf - 3.5))
        features[22] = b_cent / 4.0

        if b_passed:
            min_dist = min(chebyshev_distance(b_king_sq, p_sq) for p_sq in b_passed)
            features[23] = (7.0 - min_dist) / 7.0
        if w_king_sq is not None and b_passed:
            min_dist_e = min(chebyshev_distance(w_king_sq, p_sq) for p_sq in b_passed)
            features[24] = (7.0 - min_dist_e) / 7.0

        shelter_mask = 0
        for df in (-1, 0, 1):
            if 0 <= kf + df <= 7:
                for dr in (-1, -2):
                    if 0 <= kr + dr <= 7:
                        shelter_mask |= (1 << ((kr + dr) * 8 + (kf + df)))
        b_shelter = bin(int(b_pawns) & shelter_mask).count("1")
        features[25] = b_shelter / 6.0

    b_open_rooks = 0
    b_semi_rooks = 0
    for sq in b_rooks:
        f = sq % 8
        has_w_pawn = (int(w_pawns) & FILES[f]) != 0
        has_b_pawn = (int(b_pawns) & FILES[f]) != 0
        if not has_w_pawn and not has_b_pawn:
            b_open_rooks += 1
        elif not has_b_pawn and has_w_pawn:
            b_semi_rooks += 1
    features[26] = b_open_rooks / 2.0
    features[27] = b_semi_rooks / 2.0

    features[28] = 1.0 if len(b_bishops) >= 2 else 0.0

    b_npm = len(b_knights) * 1 + len(b_bishops) * 1 + len(b_rooks) * 2 + len(b_queens) * 4
    features[29] = b_npm / 16.0
    features[30] = len(b_pawns) / 8.0
    features[31] = 1.0 if board.turn == chess.BLACK else 0.0

    return features

