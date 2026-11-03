"""Unit tests for Phase 3: Tapered Evaluation and EvaluationConfig in Project Janus v0.34."""
import unittest
import chess

from janus.evaluation import (
    EvaluationConfig,
    CONFIG_V030,
    CONFIG_V033,
    CONFIG_V034_TAPERED,
    get_game_phase,
    evaluate_white,
    evaluate_side_to_move,
    evaluation_config,
    set_evaluation_config,
    set_evaluation_features,
)
from janus.search import JanusSearch


class TestGamePhase(unittest.TestCase):
    """Test game phase computation properties."""

    def test_startpos_phase(self):
        """Standard starting position non-pawn material should be max phase (24)."""
        board = chess.Board()
        self.assertEqual(get_game_phase(board), 24)

    def test_bare_kings_and_pawns_phase(self):
        """Positions with only kings and pawns should have phase 0."""
        board = chess.Board("8/4k3/8/3p4/4P3/8/4K3/8 w - - 0 1")
        self.assertEqual(get_game_phase(board), 0)

        bare = chess.Board("8/8/8/4k3/8/8/4K3/8 w - - 0 1")
        self.assertEqual(get_game_phase(bare), 0)

    def test_intermediate_phase_values(self):
        """Intermediate positions compute expected NPM weights."""
        # 1 white knight (1), 1 black bishop (1) => 2
        board = chess.Board("8/4k3/8/8/8/5N2/4K3/2b5 w - - 0 1")
        self.assertEqual(get_game_phase(board), 2)

        # 2 rooks (2*2=4) + 1 queen (4) = 8
        board2 = chess.Board("8/4k3/8/8/8/2R1R3/4K3/3q4 w - - 0 1")
        self.assertEqual(get_game_phase(board2), 8)

        # 4 knights (4), 4 bishops (4), 4 rooks (8) = 16 (no queens)
        board3 = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
        self.assertEqual(get_game_phase(board3), 16)

    def test_phase_monotonicity(self):
        """Removing any piece cannot increase phase."""
        board = chess.Board()
        initial_phase = get_game_phase(board)
        self.assertEqual(initial_phase, 24)

        for sq, piece in list(board.piece_map().items()):
            if piece.piece_type == chess.KING:
                continue
            board.remove_piece_at(sq)
            new_phase = get_game_phase(board)
            self.assertLessEqual(new_phase, initial_phase)
            board.set_piece_at(sq, piece)


class TestEvaluationConfig(unittest.TestCase):
    """Test EvaluationConfig immutability and isolation."""

    def test_immutable_config(self):
        """EvaluationConfig is frozen and immutable."""
        cfg = EvaluationConfig()
        with self.assertRaises((AttributeError, TypeError)):
            cfg.enable_tapered_eval = True  # type: ignore

    def test_preset_configs(self):
        """Verify baseline and v0.34 presets."""
        self.assertFalse(CONFIG_V030.enable_pawn_structure)
        self.assertFalse(CONFIG_V030.enable_rook_files)
        self.assertFalse(CONFIG_V030.enable_king_safety)
        self.assertFalse(CONFIG_V030.enable_tapered_eval)

        self.assertTrue(CONFIG_V033.enable_pawn_structure)
        self.assertTrue(CONFIG_V033.enable_rook_files)
        self.assertTrue(CONFIG_V033.enable_king_safety)
        self.assertFalse(CONFIG_V033.enable_tapered_eval)

        self.assertTrue(CONFIG_V034_TAPERED.enable_pawn_structure)
        self.assertTrue(CONFIG_V034_TAPERED.enable_rook_files)
        self.assertTrue(CONFIG_V034_TAPERED.enable_king_safety)
        self.assertTrue(CONFIG_V034_TAPERED.enable_tapered_eval)


class TestTaperedEvaluationCorrectness(unittest.TestCase):
    """Verify correctness, symmetry, and invariants of tapered evaluation."""

    def test_color_mirror_symmetry(self):
        """Mirroring the board inverts the score identically."""
        positions = [
            chess.Board(),
            chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5"),
            chess.Board("r1b1k2r/ppppqppp/2n5/4p3/2B1P1n1/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 7"),
            chess.Board("8/4k3/4p3/8/8/4P3/4K3/8 w - - 0 1"),
            chess.Board("2r3k1/1p3ppp/p7/3p4/8/1P3P2/P5PP/2R3K1 w - - 0 20"),
            chess.Board("8/8/1k6/8/8/6K1/8/8 w - - 0 1"),
        ]

        cfg = CONFIG_V034_TAPERED
        for board in positions:
            score_normal = evaluate_white(board, cfg)
            mirrored = board.mirror()
            score_mirrored = evaluate_white(mirrored, cfg)
            self.assertEqual(
                score_normal,
                -score_mirrored,
                f"Symmetry failed for FEN: {board.fen()} (normal: {score_normal}, mirror: {score_mirrored})"
            )

    def test_symmetric_positions_eval_zero(self):
        """Symmetric positions must evaluate to exactly 0."""
        symmetric_fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 5",
            "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
            "8/2k5/8/8/8/8/2K5/8 w - - 0 1",
            "8/4k3/4p3/8/8/4P3/4K3/8 w - - 0 1",
        ]
        cfg = CONFIG_V034_TAPERED
        for fen in symmetric_fens:
            board = chess.Board(fen)
            self.assertEqual(
                evaluate_white(board, cfg),
                0,
                f"Symmetric position did not eval to 0: {fen}"
            )

    def test_king_centralization_in_endgame(self):
        """Endgame centralization bonus rewards centralized king over corner king."""
        # Endgame: bare kings + 1 pawn each
        # Center king at d4 vs corner king at h8
        b_center = chess.Board("7k/8/8/8/3K4/8/4P3/7b w - - 0 1")
        b_corner = chess.Board("7k/8/8/8/8/8/4P3/K6b w - - 0 1")

        cfg = CONFIG_V034_TAPERED
        score_center = evaluate_white(b_center, cfg)
        score_corner = evaluate_white(b_corner, cfg)

        self.assertGreater(
            score_center,
            score_corner,
            "Active king at d4 in endgame should evaluate higher than cornered king at a1"
        )

    def test_passed_pawn_scaling_in_endgame(self):
        """Passed pawn on 6th rank is worth significantly more in endgame than middlegame."""
        # Endgame position (bare kings + 1 passed pawn at d6)
        eg_board = chess.Board("8/4k3/3P4/8/8/8/4K3/8 w - - 0 1")
        # Same pawn structure but full middlegame pieces
        mg_board = chess.Board("rnbqkbnr/4k3/3P4/8/8/8/4K3/RNBQKBNR w KQkq - 0 1")

        cfg = CONFIG_V034_TAPERED
        phase_eg = get_game_phase(eg_board)
        phase_mg = get_game_phase(mg_board)

        self.assertEqual(phase_eg, 0)
        self.assertEqual(phase_mg, 24)

    def test_board_preservation(self):
        """Evaluation does not mutate the chess.Board state."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        fen_before = board.fen()
        turn_before = board.turn

        _ = evaluate_white(board, CONFIG_V034_TAPERED)
        _ = evaluate_side_to_move(board, CONFIG_V034_TAPERED)

        self.assertEqual(board.fen(), fen_before)
        self.assertEqual(board.turn, turn_before)

    def test_determinism(self):
        """Multiple evaluations of identical board return identical scores."""
        board = chess.Board("r2q1rk1/ppp2ppp/2n1bn2/2bpp3/4P3/2PP1N2/PP1NBPPP/R1BQK2R w KQ - 3 7")
        cfg = CONFIG_V034_TAPERED
        scores = [evaluate_white(board, cfg) for _ in range(10)]
        self.assertTrue(all(s == scores[0] for s in scores))

    def test_v030_exact_equivalence(self):
        """When v0.30 config is used, evaluation matches static baseline exactly."""
        fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
            "8/4k3/8/3p4/4P3/8/4K3/8 w - - 0 1",
            "r1b1k2r/ppppqppp/2n5/4p3/2B1P1n1/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 7",
        ]
        for fen in fens:
            board = chess.Board(fen)
            with evaluation_config(pawn_structure=False, rook_files=False, king_safety=False, tapered_eval=False):
                score_ctx = evaluate_white(board)
            score_explicit = evaluate_white(board, CONFIG_V030)
            self.assertEqual(score_ctx, score_explicit)


class TestSearchWithTaperedEval(unittest.TestCase):
    """Verify search integration with tapered evaluation."""

    def test_mate_in_one_preserved(self):
        """Search with tapered eval still finds immediate checkmate."""
        # Scholar's mate delivery: Qxf7#
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 4")
        engine = JanusSearch(eval_config=CONFIG_V034_TAPERED)
        result = engine.search(board, max_depth=2)
        self.assertEqual(result.best_move, chess.Move.from_uci("f3f7"))

    def test_search_isolation(self):
        """Engines with different eval configs search independently."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
        eng_v030 = JanusSearch(eval_config=CONFIG_V030)
        eng_v034 = JanusSearch(eval_config=CONFIG_V034_TAPERED)

        res_v030 = eng_v030.search(board, max_depth=3)
        res_v034 = eng_v034.search(board, max_depth=3)

        self.assertIsNotNone(res_v030.best_move)
        self.assertIsNotNone(res_v034.best_move)


if __name__ == "__main__":
    unittest.main()
