"""Correctness and invariant tests for v0.28 evaluation optimisation."""
import unittest
import chess
from janus.evaluation import (
    evaluate_white,
    evaluate_side_to_move,
    PIECE_VALUES,
    CENTER_BONUS,
    WHITE_PAWN_RANK_BONUS,
    BLACK_PAWN_RANK_BONUS,
    WHITE_PAWN_TABLE,
    BLACK_PAWN_TABLE,
    KNIGHT_TABLE,
    BISHOP_TABLE,
    ROOK_VALUE,
    QUEEN_VALUE,
)


def _reference_evaluate_white(board: chess.Board) -> int:
    """Historical v0.27 unoptimised reference evaluation."""
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

    if board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count() >= 2:
        score += 25
    if board.pieces_mask(chess.BISHOP, chess.BLACK).bit_count() >= 2:
        score -= 25

    score += 8 * (
        int(board.has_kingside_castling_rights(chess.WHITE))
        + int(board.has_queenside_castling_rights(chess.WHITE))
    )
    score -= 8 * (
        int(board.has_kingside_castling_rights(chess.BLACK))
        + int(board.has_queenside_castling_rights(chess.BLACK))
    )
    return score


class TestEvaluationOptimizationV028(unittest.TestCase):
    def test_precomputed_tables_match_formulas(self):
        """Verify that precomputed tables exactly match the underlying formula definitions."""
        self.assertEqual(ROOK_VALUE, PIECE_VALUES[chess.ROOK])
        self.assertEqual(QUEEN_VALUE, PIECE_VALUES[chess.QUEEN])

        for sq in chess.SQUARES:
            self.assertEqual(
                WHITE_PAWN_TABLE[sq],
                PIECE_VALUES[chess.PAWN] + WHITE_PAWN_RANK_BONUS[sq],
            )
            self.assertEqual(
                BLACK_PAWN_TABLE[sq],
                PIECE_VALUES[chess.PAWN] + BLACK_PAWN_RANK_BONUS[sq],
            )
            self.assertEqual(
                KNIGHT_TABLE[sq],
                PIECE_VALUES[chess.KNIGHT] + CENTER_BONUS[sq],
            )
            self.assertEqual(
                BISHOP_TABLE[sq],
                PIECE_VALUES[chess.BISHOP] + CENTER_BONUS[sq],
            )

    def test_reference_equivalence_standard_positions(self):
        """Verify exact equivalence across diverse benchmark and tactical positions."""
        test_fens = [
            chess.STARTING_FEN,
            # Open game
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
            # Endgame with rook up
            "4k3/8/8/8/8/8/4N3/4K2R w K - 0 1",
            # Mate in one
            "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
            # Promotion tactic
            "8/P7/8/8/8/8/k7/7K w - - 0 1",
            # Stalemate
            "k7/8/1K6/8/8/8/8/8 b - - 0 1",
            # Complex middlegame with bishops and castling
            "r3k2r/pbpp1ppp/1pn1pq2/8/2B1P3/3P1N2/PPP2PPP/R2QK2R w KQkq - 0 9",
            # Bishop pair vs knight pair
            "r1bqk2r/pppp1ppp/8/4n3/2B1P1b1/2N2N2/PPP2PPP/R2QK2R w KQkq - 0 8",
            # Imbalanced pawn structure
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
            # Many rooks and queens
            "2r1r1k1/5ppp/8/8/8/8/5PPP/2R1R1K1 w - - 0 1",
            # Empty board except kings
            "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
        ]
        for fen in test_fens:
            board = chess.Board(fen)
            expected = _reference_evaluate_white(board)
            actual = evaluate_white(board)
            self.assertEqual(
                actual,
                expected,
                f"Mismatch on FEN {fen}: actual={actual}, expected={expected}",
            )
            self.assertEqual(
                evaluate_side_to_move(board),
                expected if board.turn == chess.WHITE else -expected,
            )

    def test_bishop_pair_bonus_invariants(self):
        """Test bishop pair bonus behavior on 0, 1, 2, and 3 bishops."""
        # 0 bishops each
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # 1 white bishop
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # 2 white bishops (+25 bonus)
        board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # 1 black bishop
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # 2 black bishops (-25 bonus, cancels white's +25)
        board.set_piece_at(chess.F8, chess.Piece(chess.BISHOP, chess.BLACK))
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

    def test_castling_rights_bonus_invariants(self):
        """Test castling rights combinations."""
        # All castling rights
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # White kingside only
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w K - 0 1")
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # Black queenside only
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w q - 0 1")
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))

        # No castling rights
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
        self.assertEqual(evaluate_white(board), _reference_evaluate_white(board))


if __name__ == "__main__":
    unittest.main()
