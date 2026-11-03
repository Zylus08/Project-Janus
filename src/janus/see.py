"""Static Exchange Evaluation (SEE) for Project Janus.

Estimates the material outcome of a capture or sequence of recaptures on a target
square under optimal minimax play (both sides only make profitable recaptures).

Piece values match the centipawn evaluation convention in janus.evaluation:
- Pawn: 100
- Knight: 320
- Bishop: 335
- Rook: 500
- Queen: 900
- King: 20_000 (sentinel)
"""
from __future__ import annotations

import chess

SEE_PIECE_VALUES: dict[chess.PieceType, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 335,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}

_ATTACKER_ORDER = (
    chess.PAWN,
    chess.KNIGHT,
    chess.BISHOP,
    chess.ROOK,
    chess.QUEEN,
    chess.KING,
)


def static_exchange_evaluation(
    board: chess.Board,
    move: chess.Move,
    check_legality: bool = True,
) -> int:
    """Compute the Static Exchange Evaluation (SEE) score of a move in centipawns.

    Returns the expected material net gain for the side making `move`.
    - Positive score: Profitable exchange (e.g. +100 for winning a pawn).
    - Zero score: Equal exchange or safe quiet move.
    - Negative score: Material loss (e.g. -800 for hanging a queen).

    Args:
        board: Current chess.Board (never mutated).
        move: The candidate chess.Move to evaluate.
        check_legality: If True, validates that move is legal in board.
                        Raises ValueError if move is illegal or invalid.

    Returns:
        Material balance change from perspective of side making `move`.
    """
    if move is None or not isinstance(move, chess.Move):
        raise ValueError(f"Invalid move input: {move!r}")

    if check_legality:
        if not board.is_legal(move):
            raise ValueError(f"Illegal move {move} in position: {board.fen()}")

    from_sq = move.from_square
    to_sq = move.to_square
    side = board.turn
    opp = not side

    # Determine initial victim value
    if board.is_en_passant(move):
        victim_val = SEE_PIECE_VALUES[chess.PAWN]
        ep_captured_sq: int | None = chess.square(
            chess.square_file(to_sq), chess.square_rank(from_sq)
        )
    else:
        victim_piece = board.piece_at(to_sq)
        victim_val = SEE_PIECE_VALUES[victim_piece.piece_type] if victim_piece else 0
        ep_captured_sq = None

    # Initial moving piece
    moving_piece = board.piece_at(from_sq)
    if moving_piece is None:
        return 0

    moving_type = moving_piece.piece_type
    promo_bonus = 0
    if move.promotion:
        promo_bonus = (
            SEE_PIECE_VALUES[move.promotion] - SEE_PIECE_VALUES[chess.PAWN]
        )
        piece_on_target = move.promotion
    else:
        piece_on_target = moving_type

    gain = [0] * 32
    gain[0] = victim_val + promo_bonus

    # Occupancy tracking: remove moving piece and ep pawn, set target square
    occupied = board.occupied ^ (1 << from_sq)
    if ep_captured_sq is not None:
        occupied ^= (1 << ep_captured_sq)
    occupied |= (1 << to_sq)

    active_mask = board.occupied & ~(1 << from_sq)
    if ep_captured_sq is not None:
        active_mask &= ~(1 << ep_captured_sq)

    cur_side = opp
    cur_piece_type = piece_on_target
    d = 0

    while True:
        # Find least valuable legal attacker for cur_side on to_sq
        attackers = (
            board.attackers_mask(cur_side, to_sq, occupied=occupied) & active_mask
        )
        if not attackers:
            break

        best_attacker_sq = None
        best_attacker_type = None

        for pt in _ATTACKER_ORDER:
            cand_mask = attackers & board.pieces_mask(pt, cur_side)
            for sq in chess.scan_forward(cand_mask):
                if pt == chess.KING:
                    # King can only recapture if to_sq is not defended by opponent
                    temp_occ = occupied ^ (1 << to_sq)
                    if (
                        board.attackers_mask(
                            not cur_side, to_sq, occupied=temp_occ
                        )
                        & active_mask
                    ):
                        continue
                    best_attacker_sq = sq
                    best_attacker_type = pt
                    break
                else:
                    # Verify absolute pin against king
                    if not (board.pin_mask(cur_side, sq) & (1 << to_sq)):
                        continue
                    best_attacker_sq = sq
                    best_attacker_type = pt
                    break

            if best_attacker_sq is not None:
                break

        if best_attacker_sq is None:
            break

        d += 1
        gain[d] = SEE_PIECE_VALUES[cur_piece_type] - gain[d - 1]

        # Pawn promotion upon recapture on rank 8 or rank 1
        if best_attacker_type == chess.PAWN and chess.square_rank(to_sq) in (0, 7):
            gain[d] += (
                SEE_PIECE_VALUES[chess.QUEEN] - SEE_PIECE_VALUES[chess.PAWN]
            )
            cur_piece_type = chess.QUEEN
        else:
            cur_piece_type = best_attacker_type

        occupied ^= (1 << best_attacker_sq)
        active_mask ^= (1 << best_attacker_sq)
        cur_side = not cur_side

    # Minimax backward pass: both sides only choose to recapture if profitable
    while d > 0:
        gain[d - 1] = -max(-gain[d - 1], gain[d])
        d -= 1

    return gain[0]


see = static_exchange_evaluation
