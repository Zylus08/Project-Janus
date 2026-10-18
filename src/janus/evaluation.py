"""A deliberately simple, transparent evaluation function.

Scores are returned from White's point of view in centipawns.
This is a baseline to replace/compare against learned evaluators later.
"""
from __future__ import annotations

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

    # Rooks (flat value, no square-dependent bonus)
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
    return score


def evaluate_side_to_move(board: chess.Board) -> int:
    """Return evaluation from the current player's point of view."""
    score = evaluate_white(board)
    return score if board.turn == chess.WHITE else -score
