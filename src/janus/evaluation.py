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


def evaluate_white(board: chess.Board) -> int:
    """Evaluate a non-terminal position from White's perspective."""
    score = 0
    for piece_type, value in PIECE_VALUES.items():
        w_mask = board.pieces_mask(piece_type, chess.WHITE)
        for square in chess.scan_forward(w_mask):
            score += value
            if piece_type in (chess.KNIGHT, chess.BISHOP):
                score += CENTER_BONUS[square]
            elif piece_type == chess.PAWN:
                score += WHITE_PAWN_RANK_BONUS[square]

        b_mask = board.pieces_mask(piece_type, chess.BLACK)
        for square in chess.scan_forward(b_mask):
            score -= value
            if piece_type in (chess.KNIGHT, chess.BISHOP):
                score -= CENTER_BONUS[square]
            elif piece_type == chess.PAWN:
                score -= BLACK_PAWN_RANK_BONUS[square]

    # Bishop pair: a modest positional signal.
    if board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count() >= 2:
        score += 25
    if board.pieces_mask(chess.BISHOP, chess.BLACK).bit_count() >= 2:
        score -= 25

    # Encourage castling rights as a small proxy for king safety / flexibility.
    score += 8 * (
        int(board.has_kingside_castling_rights(chess.WHITE))
        + int(board.has_queenside_castling_rights(chess.WHITE))
    )
    score -= 8 * (
        int(board.has_kingside_castling_rights(chess.BLACK))
        + int(board.has_queenside_castling_rights(chess.BLACK))
    )
    return score


def evaluate_side_to_move(board: chess.Board) -> int:
    """Return evaluation from the current player's point of view."""
    score = evaluate_white(board)
    return score if board.turn == chess.WHITE else -score
