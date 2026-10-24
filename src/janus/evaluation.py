"""A transparent, modular evaluation function with configurable positional terms.

Scores are returned from White's point of view in centipawns.
Individual evaluation features can be independently enabled or disabled for ablation.
When all candidate features are disabled (default), behavior is 100% identical to the v0.30 baseline.
"""
from __future__ import annotations

import contextlib
from typing import Generator

import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 335,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def _compute_center_bonus(square: chess.Square) -> int:
    """Small bonus for occupying/approaching the center."""
    file_distance = abs(chess.square_file(square) - 3.5)
    rank_distance = abs(chess.square_rank(square) - 3.5)
    return int(14 - 4 * (file_distance + rank_distance))


CENTER_BONUS: tuple[int, ...] = tuple(
    _compute_center_bonus(sq) for sq in chess.SQUARES
)
WHITE_PAWN_RANK_BONUS: tuple[int, ...] = tuple(
    chess.square_rank(sq) * 5 for sq in chess.SQUARES
)
BLACK_PAWN_RANK_BONUS: tuple[int, ...] = tuple(
    (7 - chess.square_rank(sq)) * 5 for sq in chess.SQUARES
)


def _center_bonus(square: chess.Square) -> int:
    """Small bonus for occupying/approaching the center."""
    return CENTER_BONUS[square]


# Precomputed piece-square tables combining base piece values and positional bonuses
WHITE_PAWN_TABLE: tuple[int, ...] = tuple(
    PIECE_VALUES[chess.PAWN] + WHITE_PAWN_RANK_BONUS[sq] for sq in chess.SQUARES
)
BLACK_PAWN_TABLE: tuple[int, ...] = tuple(
    PIECE_VALUES[chess.PAWN] + BLACK_PAWN_RANK_BONUS[sq] for sq in chess.SQUARES
)
KNIGHT_TABLE: tuple[int, ...] = tuple(
    PIECE_VALUES[chess.KNIGHT] + CENTER_BONUS[sq] for sq in chess.SQUARES
)
BISHOP_TABLE: tuple[int, ...] = tuple(
    PIECE_VALUES[chess.BISHOP] + CENTER_BONUS[sq] for sq in chess.SQUARES
)
ROOK_VALUE: int = PIECE_VALUES[chess.ROOK]
QUEEN_VALUE: int = PIECE_VALUES[chess.QUEEN]

# ---------------------------------------------------------------------------
# Precomputed Bitmasks for Positional Evaluation
# ---------------------------------------------------------------------------
FILE_MASKS: tuple[int, ...] = tuple(
    sum(1 << chess.square(f, r) for r in range(8)) for f in range(8)
)
ADJACENT_FILE_MASKS: tuple[int, ...] = tuple(
    ((FILE_MASKS[f - 1] if f > 0 else 0) | (FILE_MASKS[f + 1] if f < 7 else 0))
    for f in range(8)
)


def _compute_passed_pawn_mask(sq: chess.Square, color: chess.Color) -> int:
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    mask = 0
    ranks = range(r + 1, 8) if color == chess.WHITE else range(0, r)
    for test_r in ranks:
        mask |= (1 << chess.square(f, test_r))
        if f > 0:
            mask |= (1 << chess.square(f - 1, test_r))
        if f < 7:
            mask |= (1 << chess.square(f + 1, test_r))
    return mask


WHITE_PASSED_PAWN_MASKS: tuple[int, ...] = tuple(
    _compute_passed_pawn_mask(sq, chess.WHITE) for sq in chess.SQUARES
)
BLACK_PASSED_PAWN_MASKS: tuple[int, ...] = tuple(
    _compute_passed_pawn_mask(sq, chess.BLACK) for sq in chess.SQUARES
)

# Tunable scoring constants (in centipawns)
DOUBLED_PAWN_PENALTY: int = 10
ISOLATED_PAWN_PENALTY: int = 12
PASSED_PAWN_RANK_BONUS: tuple[int, ...] = (0, 0, 0, 5, 10, 20, 40, 70)

ROOK_OPEN_FILE_BONUS: int = 18
ROOK_SEMI_OPEN_FILE_BONUS: int = 10

KING_SHIELD_BONUS: int = 8
KING_OPEN_FILE_PENALTY: int = 12

# ---------------------------------------------------------------------------
# Feature Flags (Default False preserves exact historical baseline)
# ---------------------------------------------------------------------------
ENABLE_PAWN_STRUCTURE: bool = False
ENABLE_ROOK_FILES: bool = False
ENABLE_KING_SAFETY: bool = False


def set_evaluation_features(
    *,
    pawn_structure: bool | None = None,
    rook_files: bool | None = None,
    king_safety: bool | None = None,
) -> None:
    """Globally toggle evaluation candidate features."""
    global ENABLE_PAWN_STRUCTURE, ENABLE_ROOK_FILES, ENABLE_KING_SAFETY
    if pawn_structure is not None:
        ENABLE_PAWN_STRUCTURE = pawn_structure
    if rook_files is not None:
        ENABLE_ROOK_FILES = rook_files
    if king_safety is not None:
        ENABLE_KING_SAFETY = king_safety


@contextlib.contextmanager
def evaluation_config(
    *,
    pawn_structure: bool | None = None,
    rook_files: bool | None = None,
    king_safety: bool | None = None,
) -> Generator[None, None, None]:
    """Context manager to temporarily enable or disable evaluation features."""
    global ENABLE_PAWN_STRUCTURE, ENABLE_ROOK_FILES, ENABLE_KING_SAFETY
    old_pawn = ENABLE_PAWN_STRUCTURE
    old_rook = ENABLE_ROOK_FILES
    old_king = ENABLE_KING_SAFETY
    try:
        if pawn_structure is not None:
            ENABLE_PAWN_STRUCTURE = pawn_structure
        if rook_files is not None:
            ENABLE_ROOK_FILES = rook_files
        if king_safety is not None:
            ENABLE_KING_SAFETY = king_safety
        yield
    finally:
        ENABLE_PAWN_STRUCTURE = old_pawn
        ENABLE_ROOK_FILES = old_rook
        ENABLE_KING_SAFETY = old_king


def evaluate_white(board: chess.Board) -> int:
    """Evaluate a non-terminal position from White's perspective."""
    score = 0
    occ_w = board.occupied_co[chess.WHITE]
    occ_b = board.occupied_co[chess.BLACK]

    # Pawns
    for square in chess.scan_forward(board.pawns & occ_w):
        score += WHITE_PAWN_TABLE[square]
    for square in chess.scan_forward(board.pawns & occ_b):
        score -= BLACK_PAWN_TABLE[square]

    # Knights
    for square in chess.scan_forward(board.knights & occ_w):
        score += KNIGHT_TABLE[square]
    for square in chess.scan_forward(board.knights & occ_b):
        score -= KNIGHT_TABLE[square]

    # Bishops
    w_bishops = board.bishops & occ_w
    w_bishop_cnt = w_bishops.bit_count()
    for square in chess.scan_forward(w_bishops):
        score += BISHOP_TABLE[square]
    if w_bishop_cnt >= 2:
        score += 25

    b_bishops = board.bishops & occ_b
    b_bishop_cnt = b_bishops.bit_count()
    for square in chess.scan_forward(b_bishops):
        score -= BISHOP_TABLE[square]
    if b_bishop_cnt >= 2:
        score -= 25

    # Rooks (flat value, no square-dependent bonus in baseline)
    score += (board.rooks & occ_w).bit_count() * ROOK_VALUE
    score -= (board.rooks & occ_b).bit_count() * ROOK_VALUE

    # Queens (flat value, no square-dependent bonus)
    score += (board.queens & occ_w).bit_count() * QUEEN_VALUE
    score -= (board.queens & occ_b).bit_count() * QUEEN_VALUE

    # Encourage castling rights as a small proxy for king safety / flexibility.
    score += 8 * (
        int(board.has_kingside_castling_rights(chess.WHITE))
        + int(board.has_queenside_castling_rights(chess.WHITE))
        - int(board.has_kingside_castling_rights(chess.BLACK))
        - int(board.has_queenside_castling_rights(chess.BLACK))
    )

    # -----------------------------------------------------------------------
    # Isolated Candidate Feature 1: Pawn Structure
    # -----------------------------------------------------------------------
    if ENABLE_PAWN_STRUCTURE:
        w_pawns = board.pawns & occ_w
        b_pawns = board.pawns & occ_b

        # File-based terms: doubled and isolated pawns
        for f in range(8):
            f_mask = FILE_MASKS[f]
            adj_mask = ADJACENT_FILE_MASKS[f]

            w_cnt = (w_pawns & f_mask).bit_count()
            if w_cnt > 1:
                score -= (w_cnt - 1) * DOUBLED_PAWN_PENALTY
            if w_cnt > 0 and not (w_pawns & adj_mask):
                score -= w_cnt * ISOLATED_PAWN_PENALTY

            b_cnt = (b_pawns & f_mask).bit_count()
            if b_cnt > 1:
                score += (b_cnt - 1) * DOUBLED_PAWN_PENALTY
            if b_cnt > 0 and not (b_pawns & adj_mask):
                score += b_cnt * ISOLATED_PAWN_PENALTY

        # Passed pawns
        for square in chess.scan_forward(w_pawns):
            if not (b_pawns & WHITE_PASSED_PAWN_MASKS[square]):
                score += PASSED_PAWN_RANK_BONUS[chess.square_rank(square)]
        for square in chess.scan_forward(b_pawns):
            if not (w_pawns & BLACK_PASSED_PAWN_MASKS[square]):
                score -= PASSED_PAWN_RANK_BONUS[7 - chess.square_rank(square)]

    # -----------------------------------------------------------------------
    # Isolated Candidate Feature 2: Rook Open & Semi-Open Files
    # -----------------------------------------------------------------------
    if ENABLE_ROOK_FILES:
        w_pawns = board.pawns & occ_w
        b_pawns = board.pawns & occ_b
        all_pawns = board.pawns

        for square in chess.scan_forward(board.rooks & occ_w):
            f_mask = FILE_MASKS[chess.square_file(square)]
            if not (all_pawns & f_mask):
                score += ROOK_OPEN_FILE_BONUS
            elif not (w_pawns & f_mask):
                score += ROOK_SEMI_OPEN_FILE_BONUS

        for square in chess.scan_forward(board.rooks & occ_b):
            f_mask = FILE_MASKS[chess.square_file(square)]
            if not (all_pawns & f_mask):
                score -= ROOK_OPEN_FILE_BONUS
            elif not (b_pawns & f_mask):
                score -= ROOK_SEMI_OPEN_FILE_BONUS

    # -----------------------------------------------------------------------
    # Isolated Candidate Feature 3: King Safety & Pawn Shield
    # -----------------------------------------------------------------------
    if ENABLE_KING_SAFETY:
        w_pawns = board.pawns & occ_w
        b_pawns = board.pawns & occ_b

        w_king = board.king(chess.WHITE)
        if w_king is not None:
            if w_king in (chess.G1, chess.H1):
                f_pawn = bool(w_pawns & ((1 << chess.F2) | (1 << chess.F3)))
                g_pawn = bool(w_pawns & ((1 << chess.G2) | (1 << chess.G3)))
                h_pawn = bool(w_pawns & ((1 << chess.H2) | (1 << chess.H3)))
                score += (f_pawn + g_pawn + h_pawn) * KING_SHIELD_BONUS
                if not g_pawn:
                    score -= KING_OPEN_FILE_PENALTY
                if not h_pawn:
                    score -= KING_OPEN_FILE_PENALTY
            elif w_king in (chess.B1, chess.C1):
                a_pawn = bool(w_pawns & ((1 << chess.A2) | (1 << chess.A3)))
                b_pawn = bool(w_pawns & ((1 << chess.B2) | (1 << chess.B3)))
                c_pawn = bool(w_pawns & ((1 << chess.C2) | (1 << chess.C3)))
                score += (a_pawn + b_pawn + c_pawn) * KING_SHIELD_BONUS
                if not b_pawn:
                    score -= KING_OPEN_FILE_PENALTY
                if not c_pawn:
                    score -= KING_OPEN_FILE_PENALTY

        b_king = board.king(chess.BLACK)
        if b_king is not None:
            if b_king in (chess.G8, chess.H8):
                f_pawn = bool(b_pawns & ((1 << chess.F7) | (1 << chess.F6)))
                g_pawn = bool(b_pawns & ((1 << chess.G7) | (1 << chess.G6)))
                h_pawn = bool(b_pawns & ((1 << chess.H7) | (1 << chess.H6)))
                score -= (f_pawn + g_pawn + h_pawn) * KING_SHIELD_BONUS
                if not g_pawn:
                    score += KING_OPEN_FILE_PENALTY
                if not h_pawn:
                    score += KING_OPEN_FILE_PENALTY
            elif b_king in (chess.B8, chess.C8):
                a_pawn = bool(b_pawns & ((1 << chess.A7) | (1 << chess.A6)))
                b_pawn = bool(b_pawns & ((1 << chess.B7) | (1 << chess.B6)))
                c_pawn = bool(b_pawns & ((1 << chess.C7) | (1 << chess.C6)))
                score -= (a_pawn + b_pawn + c_pawn) * KING_SHIELD_BONUS
                if not b_pawn:
                    score += KING_OPEN_FILE_PENALTY
                if not c_pawn:
                    score += KING_OPEN_FILE_PENALTY

    return score


def evaluate_side_to_move(board: chess.Board) -> int:
    """Return evaluation from the current player's point of view."""
    score = evaluate_white(board)
    return score if board.turn == chess.WHITE else -score
