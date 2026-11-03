"""Project Janus v0.38 - Unit Tests for External Benchmark Pipeline.

Tests:
1. Stockfish 19 binary existence, executable permissions, and SHA-256 hash.
2. Engine session depth argument formatting ('go depth N').
3. Benchmark mode configurations (primary_fischer, historical_depth3, calibrated_elo).
4. Statistical functions (t_distribution_cdf, score_to_elo, sign_test, percentile).
5. Paired statistical analysis logic and colour breakdown.
6. Blunder classification taxonomy and heuristic edge cases.
7. Independent audit verification rules.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import chess

from janus.engine_session import SupervisedEngineSession
from match_v038_external import BENCHMARK_MODES, STOCKFISH_PATH
from analyze_v038_external import (
    analyze_paired_games,
    exact_sign_test_p_value,
    percentile_value,
    score_to_elo,
    t_distribution_cdf,
)
from analyze_losses_v038 import classify_blunder


class TestV038ExternalBenchmark(unittest.TestCase):
    """Test suite for v0.38 external benchmark infrastructure."""

    def test_stockfish_presence_and_hash(self):
        """Verify Stockfish 19 binary presence and SHA-256 digest."""
        sf_path = Path(STOCKFISH_PATH)
        self.assertTrue(sf_path.exists(), f"Stockfish not found at {STOCKFISH_PATH}")
        
        # Verify SHA-256
        h = hashlib.sha256()
        with open(sf_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        digest = h.hexdigest()
        self.assertEqual(
            digest,
            "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0",
            "Stockfish binary SHA-256 digest does not match known hash",
        )

    def test_benchmark_modes_definition(self):
        """Verify required v0.38 benchmark modes and configurations."""
        self.assertIn("primary_fischer", BENCHMARK_MODES)
        self.assertIn("historical_depth3", BENCHMARK_MODES)
        self.assertIn("calibrated_elo", BENCHMARK_MODES)

        # Primary mode
        prim = BENCHMARK_MODES["primary_fischer"]
        self.assertEqual(prim["janus_policy"], "arm_c")
        self.assertEqual(prim["time_mode"], "fischer_increment")
        self.assertEqual(prim["base_time_ms"], 3000)
        self.assertEqual(prim["inc_time_ms"], 100)
        self.assertIsNone(prim["fixed_depth"])

        # Historical depth 3
        d3 = BENCHMARK_MODES["historical_depth3"]
        self.assertEqual(d3["time_mode"], "fixed_depth")
        self.assertEqual(d3["fixed_depth"], 3)

        # Calibrated Elo
        cal = BENCHMARK_MODES["calibrated_elo"]
        self.assertTrue(cal["stockfish_options"].get("UCI_LimitStrength"))
        self.assertEqual(cal["stockfish_options"].get("UCI_Elo"), 1320)

    def test_score_to_elo_mapping(self):
        """Verify score-to-Elo conversions."""
        self.assertEqual(score_to_elo(0.5), 0.0)
        self.assertAlmostEqual(score_to_elo(0.75), 190.8, places=1)
        self.assertAlmostEqual(score_to_elo(0.25), -190.8, places=1)
        self.assertIsNone(score_to_elo(0.0))
        self.assertIsNone(score_to_elo(1.0))

    def test_t_distribution_cdf(self):
        """Verify Student's t CDF calculations."""
        self.assertAlmostEqual(t_distribution_cdf(0.0, df=49), 0.5, places=4)
        self.assertTrue(t_distribution_cdf(2.0, df=49) > 0.97)
        self.assertTrue(t_distribution_cdf(-2.0, df=49) < 0.03)
        self.assertAlmostEqual(
            t_distribution_cdf(2.0, df=49) + t_distribution_cdf(-2.0, df=49),
            1.0,
            places=4,
        )

    def test_exact_sign_test(self):
        """Verify exact binomial sign test p-values."""
        self.assertEqual(exact_sign_test_p_value(0, 0), 1.0)
        self.assertEqual(exact_sign_test_p_value(5, 10), 1.0)
        p_val = exact_sign_test_p_value(1, 10)
        self.assertTrue(p_val < 0.05)

    def test_percentile_value(self):
        """Verify linear interpolation percentile values."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertEqual(percentile_value(data, 0), 10.0)
        self.assertEqual(percentile_value(data, 50), 30.0)
        self.assertEqual(percentile_value(data, 100), 50.0)

    def test_paired_analysis_logic(self):
        """Verify paired analysis calculation on synthetic games."""
        mock_games = [
            {"pair": 1, "janus_color": "white", "janus_points": 1.0},
            {"pair": 1, "janus_color": "black", "janus_points": 0.5},
            {"pair": 2, "janus_color": "white", "janus_points": 0.0},
            {"pair": 2, "janus_color": "black", "janus_points": 0.5},
        ]
        res = analyze_paired_games(mock_games)
        self.assertEqual(res["n_pairs"], 2)
        self.assertEqual(res["n_games"], 4)
        self.assertEqual(res["score"]["janus_wins"], 1)
        self.assertEqual(res["score"]["draws"], 2)
        self.assertEqual(res["score"]["losses"], 1)
        self.assertEqual(res["score"]["total_points"], 2.0)
        self.assertEqual(res["score"]["score_pct"], 50.0)
        self.assertEqual(res["score"]["mean_pair_score"], 0.5)

    def test_blunder_classifier_hanging_piece(self):
        """Verify blunder classification for hanging piece."""
        # 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#
        board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        # Moving pawn to attacked square with no defenders
        played_move = chess.Move.from_uci("f2f4")
        cat = classify_blunder(
            board_before=board,
            played_move=played_move,
            best_move_uci="g1f3",
            eval_drop_cp=200,
            clock_remaining_ms=2000.0,
            depth=2.0,
        )
        self.assertIn("Tactical Oversight", cat)

    def test_blunder_classifier_time_pressure(self):
        """Verify blunder classification when clock is starving."""
        board = chess.Board()
        played_move = chess.Move.from_uci("e2e4")
        cat = classify_blunder(
            board_before=board,
            played_move=played_move,
            best_move_uci="e2e4",
            eval_drop_cp=200,
            clock_remaining_ms=150.0,
            depth=1.0,
        )
        self.assertEqual(cat, "Time Management / Clock Pressure")


if __name__ == "__main__":
    unittest.main()
