"""Comprehensive baseline evaluation invariant tests for Project Janus v0.33."""
import json
import unittest
from pathlib import Path

import chess
from janus.evaluation import evaluate_white, evaluate_side_to_move, PIECE_VALUES


class TestEvaluationInvariantsV033(unittest.TestCase):
    """Test suite covering fundamental mathematical and structural invariants of evaluation."""

    def setUp(self):
        self.suite_path = Path(__file__).resolve().parents[1] / "benchmarks/evaluation_positions.json"
        self.positions = []
        if self.suite_path.is_file():
            data = json.loads(self.suite_path.read_text(encoding="utf-8"))
            self.positions = data.get("positions", [])

    def test_01_board_state_preservation(self):
        """Evaluation must NEVER mutate board state, castling rights, turn, or FEN."""
        fens = [
            chess.STARTING_FEN,
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
            "r1b1k2r/pppp1ppp/2n5/4p3/4n3/3P1N2/PPP1KPPP/RNBQ1B1R b kq - 0 6",
            "4k3/8/8/4K3/4P3/8/8/8 w - - 0 1",
            "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
            "8/1P5k/8/8/8/8/K5p1/8 w - - 0 1",
        ]
        for fen in fens:
            board = chess.Board(fen)
            fen_before = board.fen()
            turn_before = board.turn
            castling_before = board.castling_rights
            ep_before = board.ep_square
            moves_before = list(board.legal_moves)

            score_w = evaluate_white(board)
            score_stm = evaluate_side_to_move(board)

            self.assertEqual(board.fen(), fen_before, f"FEN mutated on {fen}")
            self.assertEqual(board.turn, turn_before)
            self.assertEqual(board.castling_rights, castling_before)
            self.assertEqual(board.ep_square, ep_before)
            self.assertEqual(list(board.legal_moves), moves_before)
            self.assertIsInstance(score_w, int)
            self.assertIsInstance(score_stm, int)

    def test_02_evaluation_call_stability(self):
        """Repeated calls to evaluation on the same position must yield identical output (deterministic, no cache leak)."""
        board = chess.Board("r1bq1rk1/pp3ppp/2n1pn2/8/3P4/2NB1N2/PP3PPP/R2Q1RK1 w - - 0 12")
        scores_w = [evaluate_white(board) for _ in range(50)]
        scores_stm = [evaluate_side_to_move(board) for _ in range(50)]
        self.assertEqual(len(set(scores_w)), 1)
        self.assertEqual(len(set(scores_stm)), 1)

    def test_03_color_symmetry_under_board_mirroring(self):
        """For any position B, mirroring colors and ranks must exactly negate evaluate_white and preserve evaluate_side_to_move."""
        for pos in self.positions:
            fen = pos["fen"]
            board = chess.Board(fen)
            mirrored = board.mirror()

            score_w = evaluate_white(board)
            mirrored_w = evaluate_white(mirrored)
            self.assertEqual(
                score_w,
                -mirrored_w,
                f"Symmetry failed on {pos['id']} ({fen}): original={score_w}, mirror={mirrored_w}",
            )

            score_stm = evaluate_side_to_move(board)
            mirrored_stm = evaluate_side_to_move(mirrored)
            self.assertEqual(
                score_stm,
                mirrored_stm,
                f"STM symmetry failed on {pos['id']} ({fen}): original={score_stm}, mirror={mirrored_stm}",
            )

    def test_04_side_to_move_perspective_relation(self):
        """evaluate_side_to_move(board) must equal evaluate_white(board) for White and -evaluate_white(board) for Black."""
        for pos in self.positions:
            board = chess.Board(pos["fen"])
            w = evaluate_white(board)
            stm = evaluate_side_to_move(board)
            expected = w if board.turn == chess.WHITE else -w
            self.assertEqual(stm, expected, f"STM perspective mismatch on {pos['id']}")

    def test_05_material_advantage_monotonicity(self):
        """Adding a piece for White must strictly increase evaluate_white."""
        base_board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        base_score = evaluate_white(base_board)

        # Add pawn
        pawn_board = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
        self.assertGreater(evaluate_white(pawn_board), base_score)

        # Add knight > pawn
        knight_board = chess.Board("4k3/8/8/8/8/8/4N3/4K3 w - - 0 1")
        self.assertGreater(evaluate_white(knight_board), evaluate_white(pawn_board))

        # Add rook > minor
        rook_board = chess.Board("4k3/8/8/8/8/8/4R3/4K3 w - - 0 1")
        self.assertGreater(evaluate_white(rook_board), evaluate_white(knight_board))

        # Add queen > rook
        queen_board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
        self.assertGreater(evaluate_white(queen_board), evaluate_white(rook_board))

    def test_06_unusual_material_robustness(self):
        """Evaluation must handle extreme promotions, zero pieces, or 9 queens without crashing."""
        unusual_fens = [
            # 9 White Queens
            "4k3/8/8/8/QQQQQQQQ/8/8/4K2Q w - - 0 1",
            # Multiple light-squared bishops
            "4k3/8/8/8/8/8/2B1B1B1/4K3 w - - 0 1",
            # Bare kings
            "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
            # Full pawn walls
            "4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 1",
        ]
        for fen in unusual_fens:
            board = chess.Board(fen)
            score_w = evaluate_white(board)
            self.assertIsInstance(score_w, int)

    def test_07_curated_suite_expected_properties(self):
        """Curated evaluation positions must satisfy qualitative expectations."""
        for pos in self.positions:
            pid = pos["id"]
            fen = pos["fen"]
            prop = pos["expected_property"]
            board = chess.Board(fen)
            score_w = evaluate_white(board)

            if prop == "near_zero":
                self.assertLessEqual(abs(score_w), 40, f"{pid} expected near zero, got {score_w}")
            elif prop == "large_white_advantage":
                self.assertGreater(score_w, 800, f"{pid} expected >800, got {score_w}")
            elif prop == "moderate_white_advantage":
                self.assertGreater(score_w, 400, f"{pid} expected >400, got {score_w}")
            elif prop == "moderate_black_advantage":
                self.assertLess(score_w, -250, f"{pid} expected <-250, got {score_w}")


if __name__ == "__main__":
    unittest.main()
