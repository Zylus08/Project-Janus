"""Phase 5 Reproducibility and Configuration Audit Tests for Project Janus v0.34.1."""
import dataclasses
import json
import unittest

import chess

from janus.evaluation import (
    EvaluationConfig,
    CONFIG_V030,
    CONFIG_V033,
    CONFIG_V034_TAPERED,
    evaluate_white,
    evaluate_side_to_move,
    _evaluate_white_static,
)
from janus.search import JanusSearch


class TestConfigurationReproducibility(unittest.TestCase):
    """Verify EvaluationConfig serialization, presets, immutability, and isolation."""

    def test_json_roundtrip(self):
        """Configuration JSON round-trip preserves every field."""
        cfg = CONFIG_V034_TAPERED
        cfg_dict = dataclasses.asdict(cfg)
        serialized = json.dumps(cfg_dict)
        deserialized_dict = json.loads(serialized)
        restored_cfg = EvaluationConfig(**deserialized_dict)
        self.assertEqual(cfg, restored_cfg)
        for key in cfg_dict:
            self.assertEqual(getattr(cfg, key), getattr(restored_cfg, key))

    def test_presets_match_documented_values(self):
        """Preset configurations match exact specification."""
        # v0.30 baseline: all positional and tapering disabled
        self.assertFalse(CONFIG_V030.enable_pawn_structure)
        self.assertFalse(CONFIG_V030.enable_rook_files)
        self.assertFalse(CONFIG_V030.enable_king_safety)
        self.assertFalse(CONFIG_V030.enable_tapered_eval)

        # v0.33 all features: positional enabled, tapering disabled
        self.assertTrue(CONFIG_V033.enable_pawn_structure)
        self.assertTrue(CONFIG_V033.enable_rook_files)
        self.assertTrue(CONFIG_V033.enable_king_safety)
        self.assertFalse(CONFIG_V033.enable_tapered_eval)

        # v0.34 candidate: all positional enabled, tapering enabled
        self.assertTrue(CONFIG_V034_TAPERED.enable_pawn_structure)
        self.assertTrue(CONFIG_V034_TAPERED.enable_rook_files)
        self.assertTrue(CONFIG_V034_TAPERED.enable_king_safety)
        self.assertTrue(CONFIG_V034_TAPERED.enable_tapered_eval)

    def test_config_immutability(self):
        """EvaluationConfig is frozen and cannot be mutated."""
        cfg = CONFIG_V034_TAPERED
        with self.assertRaises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
            cfg.enable_tapered_eval = False  # type: ignore

    def test_evaluation_determinism(self):
        """Evaluation returns identical scores across repeated calls."""
        board = chess.Board("r1b1k2r/ppppqppp/2n5/4p3/2B1P1n1/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 7")
        scores = [evaluate_white(board, CONFIG_V034_TAPERED) for _ in range(50)]
        self.assertTrue(all(s == scores[0] for s in scores))

    def test_board_non_mutation(self):
        """Evaluation does not alter board state or move stacks."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        fen_before = board.fen()
        _ = evaluate_white(board, CONFIG_V034_TAPERED)
        _ = evaluate_side_to_move(board, CONFIG_V034_TAPERED)
        self.assertEqual(board.fen(), fen_before)

    def test_side_to_move_perspective_consistency(self):
        """Side to move evaluation inverts white score correctly."""
        board_white = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
        board_black = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 4 5")

        s_white = evaluate_white(board_white, CONFIG_V034_TAPERED)
        self.assertEqual(evaluate_side_to_move(board_white, CONFIG_V034_TAPERED), s_white)

        s_black_w = evaluate_white(board_black, CONFIG_V034_TAPERED)
        self.assertEqual(evaluate_side_to_move(board_black, CONFIG_V034_TAPERED), -s_black_w)

    def test_color_mirror_symmetry(self):
        """Mirrored board inverts score identically."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 5")
        s = evaluate_white(board, CONFIG_V034_TAPERED)
        s_mirrored = evaluate_white(board.mirror(), CONFIG_V034_TAPERED)
        self.assertEqual(s, -s_mirrored)

    def test_tapering_disabled_matches_static(self):
        """When tapering is disabled, output matches _evaluate_white_static exactly."""
        fens = [
            chess.STARTING_FEN,
            "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
            "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",
            "2r3k1/1p3ppp/p7/3p4/8/1P3P2/P5PP/2R3K1 w - - 0 20",
        ]
        for fen in fens:
            b = chess.Board(fen)
            s_static = _evaluate_white_static(b, CONFIG_V033)
            s_eval = evaluate_white(b, CONFIG_V033)
            self.assertEqual(s_static, s_eval)

    def test_search_instance_isolation(self):
        """Multiple JanusSearch instances with different configs do not cross-pollute."""
        b = chess.Board("r1bqk2r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
        eng_base = JanusSearch(eval_config=CONFIG_V030)
        eng_taper = JanusSearch(eval_config=CONFIG_V034_TAPERED)

        res1 = eng_base.search(b, max_depth=3)
        res2 = eng_taper.search(b, max_depth=3)
        res3 = eng_base.search(b, max_depth=3)

        self.assertEqual(res1.score, res3.score)
        self.assertEqual(res1.best_move, res3.best_move)


if __name__ == "__main__":
    unittest.main()
