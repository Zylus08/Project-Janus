"""Unit tests for robust paired statistics and match data validation (Milestone v0.27).

Tests:
1. All-zero differences (zero variance): verifies studentised t is None (undefined),
   flags zero variance, computes exact Clopper-Pearson binomial upper bound.
2. Constant nonzero differences: verifies variance is zero, t is None.
3. Variable nonzero differences: verifies standard Student's t-test, p-value, parametric and bootstrap CIs.
4. Data validation - Missing pair: raises ValueError with discontinuous sequence message.
5. Data validation - Duplicate game ID: raises ValueError.
6. Data validation - Incomplete pair (only 1 game): raises ValueError.
7. Data validation - Unbalanced colors in pair: raises ValueError.
8. Data validation - Malformed result string: raises ValueError.
"""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_v027_match as stat_mod


class TestPairedStatisticsRobustness(unittest.TestCase):
    """Rigorous mathematical and integrity tests for paired statistics."""

    def test_01_all_zero_differences_zero_variance(self):
        """When all paired differences are 0, t-stat is undefined and Clopper-Pearson bound is calculated."""
        # 50 pairs all tied (treatment 1.0, control 1.0)
        pairs: dict[int, list[dict]] = {}
        for p in range(1, 51):
            pairs[p] = [
                {"game": 2 * p - 1, "pair": p, "janus_color": "white", "result": "1/2-1/2"},
                {"game": 2 * p, "pair": p, "janus_color": "black", "result": "1/2-1/2"},
            ]

        res = stat_mod.compute_paired_statistics(pairs)

        self.assertEqual(res["sample_size_pairs"], 50)
        self.assertEqual(res["treatment_pairs_won"], 0)
        self.assertEqual(res["treatment_pairs_tied"], 50)
        self.assertEqual(res["treatment_pairs_lost"], 0)
        self.assertEqual(res["mean_paired_difference_pct"], 0.0)
        self.assertEqual(res["sample_variance_pct2"], 0.0)
        self.assertEqual(res["standard_error_pct"], 0.0)

        # Mathematical verification: studentised t-statistic must NOT be reported as a standard t=0, p=1
        self.assertTrue(res["is_zero_variance"])
        self.assertTrue(res["all_zero_differences"])
        self.assertIsNone(res["t_statistic"])
        self.assertIsNone(res["p_value_two_sided"])
        self.assertIsNone(res["paired_t_95_ci_pct"])

        # Clopper-Pearson 95% upper bound for 0/50: 1 - 0.05^(1/50) = 5.816%
        self.assertAlmostEqual(res["clopper_pearson_95_upper_bound_diff_rate_pct"], 5.816, places=2)
        self.assertIn("mathematically undefined", res["statistical_interpretation_note"])

    def test_02_constant_nonzero_differences_zero_variance(self):
        """When all pairs have the same non-zero difference (e.g. +50%), variance is 0 and t-stat is undefined."""
        # Treatment wins game 1 (as Black, 0-1) and draws game 2 (as White, 1/2-1/2) in every pair => delta = +25%
        pairs: dict[int, list[dict]] = {}
        for p in range(1, 11):
            pairs[p] = [
                {"game": 2 * p - 1, "pair": p, "janus_color": "white", "result": "0-1"},  # treatment (black) wins
                {"game": 2 * p, "pair": p, "janus_color": "black", "result": "1/2-1/2"},  # draw
            ]

        res = stat_mod.compute_paired_statistics(pairs)
        self.assertEqual(res["sample_size_pairs"], 10)
        self.assertEqual(res["mean_paired_difference_pct"], 50.0)
        self.assertEqual(res["sample_variance_pct2"], 0.0)
        self.assertTrue(res["is_zero_variance"])
        self.assertFalse(res["all_zero_differences"])
        self.assertIsNone(res["t_statistic"])
        self.assertIsNone(res["p_value_two_sided"])

    def test_03_variable_differences_parametric_and_bootstrap(self):
        """When pairs exhibit variance, valid Student's t-test and bootstrap CIs are computed."""
        # 10 pairs: 3 treatment wins (+50%), 5 ties (0%), 2 treatment losses (-50%)
        pairs: dict[int, list[dict]] = {}
        for p in range(1, 11):
            if p <= 3:
                # treatment wins pair
                pairs[p] = [
                    {"game": 2 * p - 1, "pair": p, "janus_color": "white", "result": "0-1"},
                    {"game": 2 * p, "pair": p, "janus_color": "black", "result": "1/2-1/2"},
                ]
            elif p <= 8:
                # pair tied
                pairs[p] = [
                    {"game": 2 * p - 1, "pair": p, "janus_color": "white", "result": "1/2-1/2"},
                    {"game": 2 * p, "pair": p, "janus_color": "black", "result": "1/2-1/2"},
                ]
            else:
                # treatment loses pair
                pairs[p] = [
                    {"game": 2 * p - 1, "pair": p, "janus_color": "white", "result": "1-0"},
                    {"game": 2 * p, "pair": p, "janus_color": "black", "result": "1/2-1/2"},
                ]

        res = stat_mod.compute_paired_statistics(pairs)
        self.assertEqual(res["sample_size_pairs"], 10)
        self.assertFalse(res["is_zero_variance"])
        self.assertGreater(res["sample_variance_pct2"], 0.0)
        self.assertIsNotNone(res["t_statistic"])
        self.assertIsNotNone(res["p_value_two_sided"])
        self.assertIsNotNone(res["paired_t_95_ci_pct"])
        self.assertIsNotNone(res["paired_bootstrap_95_ci_pct"])
        self.assertGreaterEqual(res["p_value_two_sided"], 0.0)
        self.assertLessEqual(res["p_value_two_sided"], 1.0)

    def test_04_validation_rejects_missing_pairs(self):
        """Discontinuous pair sequence (e.g. pair 1, pair 3, missing pair 2) raises ValueError."""
        games = [
            {"game": 1, "pair": 1, "janus_color": "white", "result": "1/2-1/2"},
            {"game": 2, "pair": 1, "janus_color": "black", "result": "1/2-1/2"},
            {"game": 3, "pair": 3, "janus_color": "white", "result": "1/2-1/2"},
            {"game": 4, "pair": 3, "janus_color": "black", "result": "1/2-1/2"},
        ]
        with self.assertRaises(ValueError) as ctx:
            stat_mod.validate_match_data(games)
        self.assertIn("Missing pair", str(ctx.exception))

    def test_05_validation_rejects_duplicate_game_ids(self):
        """Duplicate game IDs raise ValueError."""
        games = [
            {"game": 1, "pair": 1, "janus_color": "white", "result": "1/2-1/2"},
            {"game": 1, "pair": 1, "janus_color": "black", "result": "1/2-1/2"},
        ]
        with self.assertRaises(ValueError) as ctx:
            stat_mod.validate_match_data(games)
        self.assertIn("Duplicate game ID", str(ctx.exception))

    def test_06_validation_rejects_incomplete_pair(self):
        """Pairs with fewer or greater than 2 games raise ValueError."""
        games = [
            {"game": 1, "pair": 1, "janus_color": "white", "result": "1/2-1/2"},
            {"game": 2, "pair": 1, "janus_color": "black", "result": "1/2-1/2"},
            {"game": 3, "pair": 2, "janus_color": "white", "result": "1/2-1/2"},
        ]
        with self.assertRaises(ValueError) as ctx:
            stat_mod.validate_match_data(games)
        self.assertIn("expected exactly 2", str(ctx.exception))

    def test_07_validation_rejects_unbalanced_colors_in_pair(self):
        """Pairs where colors are not exactly one White and one Black raise ValueError."""
        games = [
            {"game": 1, "pair": 1, "janus_color": "white", "result": "1/2-1/2"},
            {"game": 2, "pair": 1, "janus_color": "white", "result": "1/2-1/2"},
        ]
        with self.assertRaises(ValueError) as ctx:
            stat_mod.validate_match_data(games)
        self.assertIn("balanced color reversal", str(ctx.exception))

    def test_08_validation_rejects_malformed_result(self):
        """Malformed or incomplete game result raises ValueError."""
        games = [
            {"game": 1, "pair": 1, "janus_color": "white", "result": "*"},
            {"game": 2, "pair": 1, "janus_color": "black", "result": "1/2-1/2"},
        ]
        with self.assertRaises(ValueError) as ctx:
            stat_mod.validate_match_data(games)
        self.assertIn("malformed or incomplete result", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
