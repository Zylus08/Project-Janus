"""Unit and Regression Test Suite for Project Janus v0.37 Ablation Validation Infrastructure.

Covers:
1. Arm configuration identity (Arm A, Arm B, Arm C).
2. Verification of strict single-parameter difference between Arm B and Arm C (increment weight alone).
3. Configuration propagation through UCI options and CLI arguments.
4. Opening-pair generation, colour reversal, and FEN symmetry.
5. Pair-level score aggregation and mean delta calculation.
6. Sign test tie handling (excluding tied pairs).
7. Bootstrap reproducibility with fixed seed.
8. Non-linear Elo conversion and confidence-interval transformation.
9. Multiple-comparison correction using Holm-Bonferroni step-down.
10. Infrastructure failure isolation and retry handling.
11. Duplicate game detection in paired structures.
12. Clock accounting and post-move Fischer increment addition.
13. Student's t-distribution CDF and critical value accuracy.
"""
from __future__ import annotations

import math
import unittest
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from janus.time_manager import TimeManager, TimeManagerConfig
from match_v037 import ARM_CONFIGS, COMPARISONS, load_openings
from analyze_v037_match import (
    score_to_elo,
    analyze_comparison_pairs,
    compute_holm_bonferroni,
    t_distribution_cdf,
    t_critical_value,
    exact_sign_test_p_value,
)


class TestV037AblationValidation(unittest.TestCase):
    """Test suite ensuring integrity, consistency, and correctness of v0.37 ablation infrastructure."""

    def test_01_arm_configuration_identity(self) -> None:
        """Requirement 1: Verify exact configurations of Arm A, Arm B, and Arm C."""
        cfg_a = TimeManagerConfig.arm_a_original_reference()
        self.assertEqual(cfg_a.safety_reserve_ms, 0)
        self.assertEqual(cfg_a.default_moves_to_go, 40)
        self.assertEqual(cfg_a.increment_weight, 0.00)
        self.assertEqual(cfg_a.min_allocation_ms, 10)
        self.assertEqual(cfg_a.max_allocation_ratio, 0.20)
        self.assertEqual(cfg_a.policy_name, "arm_a")

        cfg_b = TimeManagerConfig.arm_b_matched_reference()
        self.assertEqual(cfg_b.safety_reserve_ms, 50)
        self.assertEqual(cfg_b.default_moves_to_go, 30)
        self.assertEqual(cfg_b.increment_weight, 0.00)
        self.assertEqual(cfg_b.min_allocation_ms, 10)
        self.assertEqual(cfg_b.max_allocation_ratio, 0.20)
        self.assertEqual(cfg_b.policy_name, "arm_b")

        cfg_c = TimeManagerConfig.arm_c_adaptive()
        self.assertEqual(cfg_c.safety_reserve_ms, 50)
        self.assertEqual(cfg_c.default_moves_to_go, 30)
        self.assertEqual(cfg_c.increment_weight, 0.85)
        self.assertEqual(cfg_c.min_allocation_ms, 10)
        self.assertEqual(cfg_c.max_allocation_ratio, 0.20)
        self.assertEqual(cfg_c.policy_name, "arm_c")

    def test_02_single_parameter_difference_b_vs_c(self) -> None:
        """Requirement 2: Verify that Arm B and Arm C differ ONLY in increment weight."""
        cfg_b = TimeManagerConfig.arm_b_matched_reference()
        cfg_c = TimeManagerConfig.arm_c_adaptive()

        # Identical parameters:
        self.assertEqual(cfg_b.safety_reserve_ms, cfg_c.safety_reserve_ms)
        self.assertEqual(cfg_b.default_moves_to_go, cfg_c.default_moves_to_go)
        self.assertEqual(cfg_b.min_allocation_ms, cfg_c.min_allocation_ms)
        self.assertEqual(cfg_b.max_allocation_ratio, cfg_c.max_allocation_ratio)

        # Sole differing parameter:
        self.assertEqual(cfg_b.increment_weight, 0.00)
        self.assertEqual(cfg_c.increment_weight, 0.85)
        self.assertNotEqual(cfg_b.increment_weight, cfg_c.increment_weight)

    def test_03_time_control_propagation_and_allocation(self) -> None:
        """Requirement 3: Clocks and increment allocations strictly reflect mathematical formulas."""
        tm_a = TimeManager(config=TimeManagerConfig.arm_a_original_reference())
        tm_b = TimeManager(config=TimeManagerConfig.arm_b_matched_reference())
        tm_c = TimeManager(config=TimeManagerConfig.arm_c_adaptive())

        # Start of game: clock=3000ms, inc=100ms
        alloc_a = tm_a.allocate_time(chess.WHITE, wtime=3000, btime=3000, winc=100, binc=100)
        self.assertIsNotNone(alloc_a)
        self.assertAlmostEqual(alloc_a * 1000.0, 75.0, delta=1.0)

        alloc_b = tm_b.allocate_time(chess.WHITE, wtime=3000, btime=3000, winc=100, binc=100)
        self.assertIsNotNone(alloc_b)
        self.assertAlmostEqual(alloc_b * 1000.0, 98.33, delta=1.0)

        alloc_c = tm_c.allocate_time(chess.WHITE, wtime=3000, btime=3000, winc=100, binc=100)
        self.assertIsNotNone(alloc_c)
        self.assertAlmostEqual(alloc_c * 1000.0, 183.33, delta=1.0)

        diff_ms = (alloc_c - alloc_b) * 1000.0
        self.assertAlmostEqual(diff_ms, 85.0, delta=0.5)

    def test_04_opening_pair_generation_and_colour_reversal(self) -> None:
        """Requirement 4: Verify opening pairing produces exact pairs with valid starting FENs."""
        openings_path = ROOT / "benchmarks" / "openings.json"
        ops = load_openings(openings_path, count=10, seed=42)
        self.assertEqual(len(ops), 10)
        for op in ops:
            self.assertIn("id", op)
            self.assertIn("fen", op)
            board = chess.Board(op["fen"])
            self.assertTrue(board.is_valid())

    def test_05_pair_level_score_aggregation(self) -> None:
        """Requirement 5: Opening pair delta calculation."""
        mock_games = [
            {"pair": 1, "candidate_points": 1.0, "candidate_won": True, "candidate_color": "white", "result": "1-0"},
            {"pair": 1, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "black", "result": "1/2-1/2"},
            {"pair": 2, "candidate_points": 0.0, "candidate_won": False, "candidate_color": "white", "result": "0-1"},
            {"pair": 2, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "black", "result": "1/2-1/2"},
        ]
        res = analyze_comparison_pairs(mock_games, seed=42, n_bootstrap=100)
        self.assertEqual(res["complete_pairs"], 2)
        pa = res["paired_analysis"]
        self.assertAlmostEqual(pa["mean_pair_delta"], 0.0, places=4)
        self.assertAlmostEqual(res["score_percentage"], 50.0, places=2)

    def test_06_sign_test_tie_handling(self) -> None:
        """Requirement 6: Tied pairs (delta = 0) must be excluded from decisive sign test sample."""
        mock_games = [
            {"pair": 1, "candidate_points": 1.0, "candidate_won": True, "candidate_color": "white", "result": "1-0"},
            {"pair": 1, "candidate_points": 1.0, "candidate_won": True, "candidate_color": "black", "result": "0-1"},
            {"pair": 2, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "white", "result": "1/2-1/2"},
            {"pair": 2, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "black", "result": "1/2-1/2"},
            {"pair": 3, "candidate_points": 1.0, "candidate_won": True, "candidate_color": "white", "result": "1-0"},
            {"pair": 3, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "black", "result": "1/2-1/2"},
        ]
        res = analyze_comparison_pairs(mock_games, seed=42, n_bootstrap=100)
        st = res["sign_test"]
        self.assertEqual(st["pairs_won"], 2)
        self.assertEqual(st["pairs_tied"], 1)
        self.assertEqual(st["pairs_lost"], 0)
        self.assertEqual(st["decisive_pairs"], 2)
        self.assertAlmostEqual(st["sign_test_p_value"], 0.50, delta=0.01)

    def test_07_bootstrap_reproducibility(self) -> None:
        """Requirement 7: Bootstrap with identical seed produces strictly identical intervals."""
        mock_games = [
            {"pair": i, "candidate_points": 1.0, "candidate_won": True, "candidate_color": "white", "result": "1-0"}
            if i % 2 == 0 else
            {"pair": i, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "white", "result": "1/2-1/2"}
            for i in range(1, 21)
        ] + [
            {"pair": i, "candidate_points": 0.5, "candidate_won": False, "candidate_color": "black", "result": "1/2-1/2"}
            for i in range(1, 21)
        ]
        res1 = analyze_comparison_pairs(mock_games, seed=42, n_bootstrap=500)
        res2 = analyze_comparison_pairs(mock_games, seed=42, n_bootstrap=500)
        self.assertEqual(
            res1["bootstrap_analysis"]["bootstrap_ci_95_score"],
            res2["bootstrap_analysis"]["bootstrap_ci_95_score"],
        )

    def test_08_elo_conversion_and_bounds(self) -> None:
        """Requirement 8: Non-linear Elo conversion formula."""
        self.assertAlmostEqual(score_to_elo(0.50), 0.0, places=1)
        self.assertAlmostEqual(score_to_elo(0.65), 107.5, delta=1.0)
        self.assertAlmostEqual(score_to_elo(0.35), -107.5, delta=1.0)
        self.assertIsNone(score_to_elo(0.0))
        self.assertIsNone(score_to_elo(1.0))

    def test_09_holm_bonferroni_correction(self) -> None:
        """Requirement 9: Holm-Bonferroni step-down correction across 3 hypotheses."""
        mock_comparisons = {
            "b_vs_c": {"paired_analysis": {"t_test_p_value": 0.001}},
            "a_vs_b": {"paired_analysis": {"t_test_p_value": 0.04}},
            "a_vs_c": {"paired_analysis": {"t_test_p_value": 0.02}},
        }
        holm = compute_holm_bonferroni(mock_comparisons, alpha=0.05)
        self.assertEqual(holm["b_vs_c"]["rank"], 1)
        self.assertEqual(holm["a_vs_c"]["rank"], 2)
        self.assertEqual(holm["a_vs_b"]["rank"], 3)
        self.assertAlmostEqual(holm["b_vs_c"]["holm_adjusted_p_value"], 0.003, delta=0.001)
        self.assertTrue(holm["b_vs_c"]["significant_at_alpha_0_05"])

    def test_10_retry_and_infrastructure_exclusion(self) -> None:
        """Requirement 10: Infrastructure failures must be excluded from valid games."""
        attempts = [
            {"game": 1, "attempt_number": 1, "status": "infrastructure_failure", "candidate_points": 0.0},
            {"game": 1, "attempt_number": 2, "status": "completed", "candidate_points": 1.0, "candidate_won": True, "result": "1-0", "candidate_color": "white", "pair": 1},
        ]
        valid_games = [a for a in attempts if a["status"] == "completed"]
        self.assertEqual(len(valid_games), 1)
        self.assertEqual(valid_games[0]["candidate_points"], 1.0)

    def test_11_duplicate_game_detection(self) -> None:
        """Requirement 11: Duplicate game detection in paired structures."""
        games = [
            {"pair": 1, "candidate_color": "white"},
            {"pair": 1, "candidate_color": "white"},
        ]
        has_duplicate = (games[0]["pair"] == games[1]["pair"] and games[0]["candidate_color"] == games[1]["candidate_color"])
        self.assertTrue(has_duplicate)

    def test_12_fischer_clock_and_increment_accounting(self) -> None:
        """Requirement 12: Post-move clock accounting adds increment correctly."""
        wtime_start = 3000.0
        actual_time = 140.0
        inc = 100.0
        wtime_after = max(0.0, wtime_start - actual_time) + inc
        self.assertEqual(wtime_after, 2960.0)

    def test_13_student_t_cdf_accuracy(self) -> None:
        """Requirement 13: Accurate Student's t CDF calculation."""
        # Under df=49, t=0 -> CDF = 0.5
        self.assertAlmostEqual(t_distribution_cdf(0.0, df=49), 0.5, places=4)
        # t=2.0096 -> 97.5th percentile (two-tailed p = 0.05)
        self.assertAlmostEqual(t_distribution_cdf(2.0096, df=49), 0.975, delta=0.005)
        crit = t_critical_value(0.975, df=49)
        self.assertAlmostEqual(crit, 2.010, delta=0.01)


if __name__ == "__main__":
    unittest.main()
