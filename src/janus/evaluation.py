"""A transparent, modular, phase-aware evaluation function with configurable terms.

Scores are returned from White's point of view in centipawns.
Evaluation features can be configured via an immutable EvaluationConfig or module-level flags.
When all candidate features are disabled (default), behavior is 100% identical to the v0.30 baseline.
"""
from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Generator

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


def _compute_king_center_bonus(square: chess.Square) -> int:
    """Endgame bonus for king centralisation (active king in endgame)."""
    file_dist = abs(chess.square_file(square) - 3.5)
    rank_dist = abs(chess.square_rank(square) - 3.5)
    return int(12 - 3 * (file_dist + rank_dist))


KING_CENTER_BONUS: tuple[int, ...] = tuple(
    _compute_king_center_bonus(sq) for sq in chess.SQUARES
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
# Game Phase Calculation
# ---------------------------------------------------------------------------
def get_game_phase(board: chess.Board) -> int:
    """Calculate game phase in [0, 24] based on remaining non-pawn material.
    
    24 = Pure Middlegame / Opening
    0 = Pure Endgame (bare kings/pawns)
    """
    npm = (
        board.knights.bit_count()
        + board.bishops.bit_count()
        + (board.rooks.bit_count() << 1)
        + (board.queens.bit_count() << 2)
    )
    return max(0, min(24, npm))


# ---------------------------------------------------------------------------
# Evaluation Configuration Object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EvaluationConfig:
    """Immutable, thread-safe configuration for position evaluation."""
    enable_pawn_structure: bool = False
    enable_rook_files: bool = False
    enable_king_safety: bool = False
    enable_tapered_eval: bool = False

    # Base piece values (centipawns)
    pawn_value: int = 100
    knight_value: int = 320
    bishop_value: int = 335
    rook_value: int = 500
    queen_value: int = 900

    # Positional weights
    bishop_pair_bonus: int = 25
    castling_right_bonus: int = 8

    # Pawn structure (Middlegame & Endgame)
    doubled_pawn_penalty_mg: int = 10
    doubled_pawn_penalty_eg: int = 15
    isolated_pawn_penalty_mg: int = 12
    isolated_pawn_penalty_eg: int = 18
    passed_pawn_bonus_mg: tuple[int, ...] = (0, 0, 0, 5, 10, 20, 35, 60)
    passed_pawn_bonus_eg: tuple[int, ...] = (0, 0, 0, 10, 25, 50, 85, 130)

    # Rook file weights (Middlegame & Endgame)
    rook_open_file_bonus_mg: int = 18
    rook_open_file_bonus_eg: int = 20
    rook_semi_open_file_bonus_mg: int = 10
    rook_semi_open_file_bonus_eg: int = 12

    # King safety weights (Middlegame)
    king_shield_bonus_mg: int = 8
    king_open_file_penalty_mg: int = 12

    # King centralization weight (Endgame)
    king_center_bonus_eg: int = 12

    def __post_init__(self) -> None:
        if not isinstance(self.passed_pawn_bonus_mg, tuple):
            object.__setattr__(self, "passed_pawn_bonus_mg", tuple(self.passed_pawn_bonus_mg))
        if not isinstance(self.passed_pawn_bonus_eg, tuple):
            object.__setattr__(self, "passed_pawn_bonus_eg", tuple(self.passed_pawn_bonus_eg))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationConfig:
        clean = dict(data)
        for k in ("passed_pawn_bonus_mg", "passed_pawn_bonus_eg"):
            if k in clean and isinstance(clean[k], list):
                clean[k] = tuple(clean[k])
        return cls(**clean)

    def save_json(self, path: Path | str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, path: Path | str) -> EvaluationConfig:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# Presets for reproducible milestone experiments
CONFIG_V030 = EvaluationConfig()
CONFIG_V033 = EvaluationConfig(
    enable_pawn_structure=True,
    enable_rook_files=True,
    enable_king_safety=True,
    enable_tapered_eval=False,
)
CONFIG_V034_TAPERED = EvaluationConfig(
    enable_pawn_structure=True,
    enable_rook_files=True,
    enable_king_safety=True,
    enable_tapered_eval=True,
)

# Active module-level defaults
DEFAULT_CONFIG: EvaluationConfig = CONFIG_V030

ENABLE_PAWN_STRUCTURE: bool = False
ENABLE_ROOK_FILES: bool = False
ENABLE_KING_SAFETY: bool = False
ENABLE_TAPERED_EVAL: bool = False


def set_evaluation_features(
    *,
    pawn_structure: bool | None = None,
    rook_files: bool | None = None,
    king_safety: bool | None = None,
    tapered_eval: bool | None = None,
) -> None:
    """Globally toggle evaluation candidate features and update DEFAULT_CONFIG."""
    global ENABLE_PAWN_STRUCTURE, ENABLE_ROOK_FILES, ENABLE_KING_SAFETY, ENABLE_TAPERED_EVAL, DEFAULT_CONFIG
    if pawn_structure is not None:
        ENABLE_PAWN_STRUCTURE = pawn_structure
    if rook_files is not None:
        ENABLE_ROOK_FILES = rook_files
    if king_safety is not None:
        ENABLE_KING_SAFETY = king_safety
    if tapered_eval is not None:
        ENABLE_TAPERED_EVAL = tapered_eval

    DEFAULT_CONFIG = EvaluationConfig(
        enable_pawn_structure=ENABLE_PAWN_STRUCTURE,
        enable_rook_files=ENABLE_ROOK_FILES,
        enable_king_safety=ENABLE_KING_SAFETY,
        enable_tapered_eval=ENABLE_TAPERED_EVAL,
    )


def set_evaluation_config(config: EvaluationConfig) -> None:
    """Set global active configuration preset."""
    global DEFAULT_CONFIG, ENABLE_PAWN_STRUCTURE, ENABLE_ROOK_FILES, ENABLE_KING_SAFETY, ENABLE_TAPERED_EVAL
    DEFAULT_CONFIG = config
    ENABLE_PAWN_STRUCTURE = config.enable_pawn_structure
    ENABLE_ROOK_FILES = config.enable_rook_files
    ENABLE_KING_SAFETY = config.enable_king_safety
    ENABLE_TAPERED_EVAL = config.enable_tapered_eval


@contextlib.contextmanager
def evaluation_config(
    *,
    pawn_structure: bool | None = None,
    rook_files: bool | None = None,
    king_safety: bool | None = None,
    tapered_eval: bool | None = None,
    config: EvaluationConfig | None = None,
) -> Generator[None, None, None]:
    """Context manager to temporarily enable or disable evaluation features."""
    global DEFAULT_CONFIG, ENABLE_PAWN_STRUCTURE, ENABLE_ROOK_FILES, ENABLE_KING_SAFETY, ENABLE_TAPERED_EVAL
    old_pawn = ENABLE_PAWN_STRUCTURE
    old_rook = ENABLE_ROOK_FILES
    old_king = ENABLE_KING_SAFETY
    old_taper = ENABLE_TAPERED_EVAL
    old_cfg = DEFAULT_CONFIG
    try:
        if config is not None:
            set_evaluation_config(config)
        else:
            set_evaluation_features(
                pawn_structure=pawn_structure,
                rook_files=rook_files,
                king_safety=king_safety,
                tapered_eval=tapered_eval,
            )
        yield
    finally:
        ENABLE_PAWN_STRUCTURE = old_pawn
        ENABLE_ROOK_FILES = old_rook
        ENABLE_KING_SAFETY = old_king
        ENABLE_TAPERED_EVAL = old_taper
        DEFAULT_CONFIG = old_cfg


def evaluate_white(board: chess.Board, config: EvaluationConfig | None = None) -> int:
    """Evaluate a non-terminal position from White's perspective."""
    cfg = config if config is not None else DEFAULT_CONFIG

    if not cfg.enable_tapered_eval:
        return _evaluate_white_static(board, cfg)
    return _evaluate_white_tapered(board, cfg)


def _evaluate_white_static(board: chess.Board, cfg: EvaluationConfig) -> int:
    """Original non-tapered static evaluation function."""
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
        score += cfg.bishop_pair_bonus

    b_bishops = board.bishops & occ_b
    b_bishop_cnt = b_bishops.bit_count()
    for square in chess.scan_forward(b_bishops):
        score -= BISHOP_TABLE[square]
    if b_bishop_cnt >= 2:
        score -= cfg.bishop_pair_bonus

    # Rooks (flat value in baseline)
    score += (board.rooks & occ_w).bit_count() * ROOK_VALUE
    score -= (board.rooks & occ_b).bit_count() * ROOK_VALUE

    # Queens (flat value)
    score += (board.queens & occ_w).bit_count() * QUEEN_VALUE
    score -= (board.queens & occ_b).bit_count() * QUEEN_VALUE

    # Castling rights bonus
    score += cfg.castling_right_bonus * (
        int(board.has_kingside_castling_rights(chess.WHITE))
        + int(board.has_queenside_castling_rights(chess.WHITE))
        - int(board.has_kingside_castling_rights(chess.BLACK))
        - int(board.has_queenside_castling_rights(chess.BLACK))
    )

    # Pawn Structure
    if cfg.enable_pawn_structure:
        w_pawns = board.pawns & occ_w
        b_pawns = board.pawns & occ_b

        for f in range(8):
            f_mask = FILE_MASKS[f]
            adj_mask = ADJACENT_FILE_MASKS[f]

            w_cnt = (w_pawns & f_mask).bit_count()
            if w_cnt > 1:
                score -= (w_cnt - 1) * cfg.doubled_pawn_penalty_mg
            if w_cnt > 0 and not (w_pawns & adj_mask):
                score -= w_cnt * cfg.isolated_pawn_penalty_mg

            b_cnt = (b_pawns & f_mask).bit_count()
            if b_cnt > 1:
                score += (b_cnt - 1) * cfg.doubled_pawn_penalty_mg
            if b_cnt > 0 and not (b_pawns & adj_mask):
                score += b_cnt * cfg.isolated_pawn_penalty_mg

        for square in chess.scan_forward(w_pawns):
            if not (b_pawns & WHITE_PASSED_PAWN_MASKS[square]):
                score += cfg.passed_pawn_bonus_mg[chess.square_rank(square)]
        for square in chess.scan_forward(b_pawns):
            if not (w_pawns & BLACK_PASSED_PAWN_MASKS[square]):
                score -= cfg.passed_pawn_bonus_mg[7 - chess.square_rank(square)]

    # Rook Files
    if cfg.enable_rook_files:
        w_pawns = board.pawns & occ_w
        b_pawns = board.pawns & occ_b
        all_pawns = board.pawns

        for square in chess.scan_forward(board.rooks & occ_w):
            f_mask = FILE_MASKS[chess.square_file(square)]
            if not (all_pawns & f_mask):
                score += cfg.rook_open_file_bonus_mg
            elif not (w_pawns & f_mask):
                score += cfg.rook_semi_open_file_bonus_mg

        for square in chess.scan_forward(board.rooks & occ_b):
            f_mask = FILE_MASKS[chess.square_file(square)]
            if not (all_pawns & f_mask):
                score -= cfg.rook_open_file_bonus_mg
            elif not (b_pawns & f_mask):
                score -= cfg.rook_semi_open_file_bonus_mg

    # King Safety
    if cfg.enable_king_safety:
        w_pawns = board.pawns & occ_w
        b_pawns = board.pawns & occ_b

        w_king = board.king(chess.WHITE)
        if w_king is not None:
            if w_king in (chess.G1, chess.H1):
                f_pawn = bool(w_pawns & ((1 << chess.F2) | (1 << chess.F3)))
                g_pawn = bool(w_pawns & ((1 << chess.G2) | (1 << chess.G3)))
                h_pawn = bool(w_pawns & ((1 << chess.H2) | (1 << chess.H3)))
                score += (f_pawn + g_pawn + h_pawn) * cfg.king_shield_bonus_mg
                if not g_pawn:
                    score -= cfg.king_open_file_penalty_mg
                if not h_pawn:
                    score -= cfg.king_open_file_penalty_mg
            elif w_king in (chess.B1, chess.C1):
                a_pawn = bool(w_pawns & ((1 << chess.A2) | (1 << chess.A3)))
                b_pawn = bool(w_pawns & ((1 << chess.B2) | (1 << chess.B3)))
                c_pawn = bool(w_pawns & ((1 << chess.C2) | (1 << chess.C3)))
                score += (a_pawn + b_pawn + c_pawn) * cfg.king_shield_bonus_mg
                if not b_pawn:
                    score -= cfg.king_open_file_penalty_mg
                if not c_pawn:
                    score -= cfg.king_open_file_penalty_mg

        b_king = board.king(chess.BLACK)
        if b_king is not None:
            if b_king in (chess.G8, chess.H8):
                f_pawn = bool(b_pawns & ((1 << chess.F7) | (1 << chess.F6)))
                g_pawn = bool(b_pawns & ((1 << chess.G7) | (1 << chess.G6)))
                h_pawn = bool(b_pawns & ((1 << chess.H7) | (1 << chess.H6)))
                score -= (f_pawn + g_pawn + h_pawn) * cfg.king_shield_bonus_mg
                if not g_pawn:
                    score += cfg.king_open_file_penalty_mg
                if not h_pawn:
                    score += cfg.king_open_file_penalty_mg
            elif b_king in (chess.B8, chess.C8):
                a_pawn = bool(b_pawns & ((1 << chess.A7) | (1 << chess.A6)))
                b_pawn = bool(b_pawns & ((1 << chess.B7) | (1 << chess.B6)))
                c_pawn = bool(b_pawns & ((1 << chess.C7) | (1 << chess.C6)))
                score -= (a_pawn + b_pawn + c_pawn) * cfg.king_shield_bonus_mg
                if not b_pawn:
                    score += cfg.king_open_file_penalty_mg
                if not c_pawn:
                    score += cfg.king_open_file_penalty_mg

    return score


def _evaluate_white_tapered(board: chess.Board, cfg: EvaluationConfig) -> int:
    """Tapered middlegame and endgame evaluation smoothly blended by game phase."""
    occ_w = board.occupied_co[chess.WHITE]
    occ_b = board.occupied_co[chess.BLACK]

    mg_score = 0
    eg_score = 0

    # Pawns
    for square in chess.scan_forward(board.pawns & occ_w):
        mg_score += WHITE_PAWN_TABLE[square]
        eg_score += WHITE_PAWN_TABLE[square]
    for square in chess.scan_forward(board.pawns & occ_b):
        mg_score -= BLACK_PAWN_TABLE[square]
        eg_score -= BLACK_PAWN_TABLE[square]

    # Knights
    for square in chess.scan_forward(board.knights & occ_w):
        mg_score += KNIGHT_TABLE[square]
        eg_score += KNIGHT_TABLE[square]
    for square in chess.scan_forward(board.knights & occ_b):
        mg_score -= KNIGHT_TABLE[square]
        eg_score -= KNIGHT_TABLE[square]

    # Bishops
    w_bishops = board.bishops & occ_w
    w_bishop_cnt = w_bishops.bit_count()
    for square in chess.scan_forward(w_bishops):
        mg_score += BISHOP_TABLE[square]
        eg_score += BISHOP_TABLE[square]
    if w_bishop_cnt >= 2:
        mg_score += cfg.bishop_pair_bonus
        eg_score += cfg.bishop_pair_bonus

    b_bishops = board.bishops & occ_b
    b_bishop_cnt = b_bishops.bit_count()
    for square in chess.scan_forward(b_bishops):
        mg_score -= BISHOP_TABLE[square]
        eg_score -= BISHOP_TABLE[square]
    if b_bishop_cnt >= 2:
        mg_score -= cfg.bishop_pair_bonus
        eg_score -= cfg.bishop_pair_bonus

    # Rooks (flat material)
    w_rooks = (board.rooks & occ_w).bit_count()
    b_rooks = (board.rooks & occ_b).bit_count()
    mg_score += w_rooks * ROOK_VALUE - b_rooks * ROOK_VALUE
    eg_score += w_rooks * ROOK_VALUE - b_rooks * ROOK_VALUE

    # Queens (flat material)
    w_queens = (board.queens & occ_w).bit_count()
    b_queens = (board.queens & occ_b).bit_count()
    mg_score += w_queens * QUEEN_VALUE - b_queens * QUEEN_VALUE
    eg_score += w_queens * QUEEN_VALUE - b_queens * QUEEN_VALUE

    # Castling rights (Middlegame only)
    castling_diff = (
        int(board.has_kingside_castling_rights(chess.WHITE))
        + int(board.has_queenside_castling_rights(chess.WHITE))
        - int(board.has_kingside_castling_rights(chess.BLACK))
        - int(board.has_queenside_castling_rights(chess.BLACK))
    )
    mg_score += cfg.castling_right_bonus * castling_diff

    # Optional Positional Terms
    w_pawns = board.pawns & occ_w
    b_pawns = board.pawns & occ_b

    # 1. Pawn Structure (Phase-Differentiated)
    if cfg.enable_pawn_structure:
        for f in range(8):
            f_mask = FILE_MASKS[f]
            adj_mask = ADJACENT_FILE_MASKS[f]

            w_cnt = (w_pawns & f_mask).bit_count()
            if w_cnt > 1:
                mg_score -= (w_cnt - 1) * cfg.doubled_pawn_penalty_mg
                eg_score -= (w_cnt - 1) * cfg.doubled_pawn_penalty_eg
            if w_cnt > 0 and not (w_pawns & adj_mask):
                mg_score -= w_cnt * cfg.isolated_pawn_penalty_mg
                eg_score -= w_cnt * cfg.isolated_pawn_penalty_eg

            b_cnt = (b_pawns & f_mask).bit_count()
            if b_cnt > 1:
                mg_score += (b_cnt - 1) * cfg.doubled_pawn_penalty_mg
                eg_score += (b_cnt - 1) * cfg.doubled_pawn_penalty_eg
            if b_cnt > 0 and not (b_pawns & adj_mask):
                mg_score += b_cnt * cfg.isolated_pawn_penalty_mg
                eg_score += b_cnt * cfg.isolated_pawn_penalty_eg

        # Passed pawns (Enhanced bonus in Endgame)
        for square in chess.scan_forward(w_pawns):
            if not (b_pawns & WHITE_PASSED_PAWN_MASKS[square]):
                r = chess.square_rank(square)
                mg_score += cfg.passed_pawn_bonus_mg[r]
                eg_score += cfg.passed_pawn_bonus_eg[r]

        for square in chess.scan_forward(b_pawns):
            if not (w_pawns & BLACK_PASSED_PAWN_MASKS[square]):
                inv_r = 7 - chess.square_rank(square)
                mg_score -= cfg.passed_pawn_bonus_mg[inv_r]
                eg_score -= cfg.passed_pawn_bonus_eg[inv_r]

    # 2. Rook Files (Phase-Differentiated)
    if cfg.enable_rook_files:
        all_pawns = board.pawns
        for square in chess.scan_forward(board.rooks & occ_w):
            f_mask = FILE_MASKS[chess.square_file(square)]
            if not (all_pawns & f_mask):
                mg_score += cfg.rook_open_file_bonus_mg
                eg_score += cfg.rook_open_file_bonus_eg
            elif not (w_pawns & f_mask):
                mg_score += cfg.rook_semi_open_file_bonus_mg
                eg_score += cfg.rook_semi_open_file_bonus_eg

        for square in chess.scan_forward(board.rooks & occ_b):
            f_mask = FILE_MASKS[chess.square_file(square)]
            if not (all_pawns & f_mask):
                mg_score -= cfg.rook_open_file_bonus_mg
                eg_score -= cfg.rook_open_file_bonus_eg
            elif not (b_pawns & f_mask):
                mg_score -= cfg.rook_semi_open_file_bonus_mg
                eg_score -= cfg.rook_semi_open_file_bonus_eg

    # 3. King Evaluation (Middlegame Shield vs Endgame Centralization)
    w_king = board.king(chess.WHITE)
    b_king = board.king(chess.BLACK)

    # Middlegame: Castled King Shield & Exposure
    if cfg.enable_king_safety:
        if w_king is not None:
            if w_king in (chess.G1, chess.H1):
                f_pawn = bool(w_pawns & ((1 << chess.F2) | (1 << chess.F3)))
                g_pawn = bool(w_pawns & ((1 << chess.G2) | (1 << chess.G3)))
                h_pawn = bool(w_pawns & ((1 << chess.H2) | (1 << chess.H3)))
                mg_score += (f_pawn + g_pawn + h_pawn) * cfg.king_shield_bonus_mg
                if not g_pawn:
                    mg_score -= cfg.king_open_file_penalty_mg
                if not h_pawn:
                    mg_score -= cfg.king_open_file_penalty_mg
            elif w_king in (chess.B1, chess.C1):
                a_pawn = bool(w_pawns & ((1 << chess.A2) | (1 << chess.A3)))
                b_pawn = bool(w_pawns & ((1 << chess.B2) | (1 << chess.B3)))
                c_pawn = bool(w_pawns & ((1 << chess.C2) | (1 << chess.C3)))
                mg_score += (a_pawn + b_pawn + c_pawn) * cfg.king_shield_bonus_mg
                if not b_pawn:
                    mg_score -= cfg.king_open_file_penalty_mg
                if not c_pawn:
                    mg_score -= cfg.king_open_file_penalty_mg

        if b_king is not None:
            if b_king in (chess.G8, chess.H8):
                f_pawn = bool(b_pawns & ((1 << chess.F7) | (1 << chess.F6)))
                g_pawn = bool(b_pawns & ((1 << chess.G7) | (1 << chess.G6)))
                h_pawn = bool(b_pawns & ((1 << chess.H7) | (1 << chess.H6)))
                mg_score -= (f_pawn + g_pawn + h_pawn) * cfg.king_shield_bonus_mg
                if not g_pawn:
                    mg_score += cfg.king_open_file_penalty_mg
                if not h_pawn:
                    mg_score += cfg.king_open_file_penalty_mg
            elif b_king in (chess.B8, chess.C8):
                a_pawn = bool(b_pawns & ((1 << chess.A7) | (1 << chess.A6)))
                b_pawn = bool(b_pawns & ((1 << chess.B7) | (1 << chess.B6)))
                c_pawn = bool(b_pawns & ((1 << chess.C7) | (1 << chess.C6)))
                mg_score -= (a_pawn + b_pawn + c_pawn) * cfg.king_shield_bonus_mg
                if not b_pawn:
                    mg_score += cfg.king_open_file_penalty_mg
                if not c_pawn:
                    mg_score += cfg.king_open_file_penalty_mg

    # Endgame: King Centralization (Active King)
    if w_king is not None and b_king is not None:
        w_king_cent = KING_CENTER_BONUS[w_king]
        b_king_cent = KING_CENTER_BONUS[b_king]
        eg_score += (w_king_cent - b_king_cent) * cfg.king_center_bonus_eg // 12

    # Smooth Material-Based Phase Interpolation
    phase = get_game_phase(board)
    return (mg_score * phase + eg_score * (24 - phase) + 12) // 24


def evaluate_side_to_move(board: chess.Board, config: EvaluationConfig | None = None) -> int:
    """Return evaluation from the current player's point of view."""
    score = evaluate_white(board, config)
    return score if board.turn == chess.WHITE else -score
