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


def _center_bonus(square: chess.Square) -> int:
    """Small bonus for occupying/approaching the center."""
    file_distance = abs(chess.square_file(square) - 3.5)
    rank_distance = abs(chess.square_rank(square) - 3.5)
    return int(14 - 4 * (file_distance + rank_distance))


def evaluate_white(board: chess.Board) -> int:
    """Evaluate a non-terminal position from White's perspective."""
    if board.is_checkmate():
        # The side to move has been checkmated.
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material() or board.is_fivefold_repetition():
        return 0

    score = 0
    for piece_type, value in PIECE_VALUES.items():
        for square in board.pieces(piece_type, chess.WHITE):
            score += value
            if piece_type in (chess.KNIGHT, chess.BISHOP):
                score += _center_bonus(square)
            elif piece_type == chess.PAWN:
                score += chess.square_rank(square) * 5
        for square in board.pieces(piece_type, chess.BLACK):
            score -= value
            if piece_type in (chess.KNIGHT, chess.BISHOP):
                score -= _center_bonus(square)
            elif piece_type == chess.PAWN:
                score -= (7 - chess.square_rank(square)) * 5

    # Bishop pair: a modest positional signal.
    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += 25
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
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
