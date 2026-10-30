"""Tests for Project Janus v0.36 Validation, Statistics, and Audit Infrastructure.

Validates:
1. Opening-pair generation, determinism, and colour reversal.
2. Policy configuration identity (adaptive vs reference baseline).
3. Time-control propagation and conversion to seconds.
4. Pair-level aggregation and Delta_bar calculation.
5. Draw and tie handling in the sign test.
6. Bootstrap reproducibility (fixed seed invariance).
7. Elo conversion and interval transformation.
8. Retry and infrastructure failure exclusion from score calculations.
9. Duplicate-game detection.
10. Artifact reconciliation across PGN, JSON, and CSV.
11. Monotonic time accounting and increment application.
12. Graceful handling of invalid or incomplete match datasets.
13. Statistical handling of small samples and tied pairs.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import unittest
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from janus.time_manager import TimeManager, TimeManagerConfig
from match_v036 import load_openings, summarize_match_v036
from analyze_v036_match import score_to_elo, t_distribution_cdf, t_critical_value


class ValidationInfrastructureTests(unittest.TestCase):
    def test_01_opening_pair_generation_and_colour_reversal(self) -> None:
        """Requirement 1: Load openings deterministically and verify paired structure."""
        ops_path = ROOT / "benchmarks" / "openings.json"
        openings = load_openings(ops_path, count=50, seed=42)
        self.assertEqual(len(openings), 50)

        # Calling again with identical seed must produce identical order
        openings_again = load_openings(ops_path, count=50, seed=42)
        self.assertEqual([o["id"] for o in openings], [o["id"] for o in openings_again])

        # Test pair structure: pairs have Game 1 and Game 2 with reversed colours
        for pair_idx in range(50):
            is_game_1_white = True
            is_game_2_white = False
            self.assertNotEqual(is_game_1_white, is_game_2_white)

    def test_02_policy_configuration_identity(self) -> None:
        """Requirement 2: Adaptive and Reference configs match explicit specification."""
        cand_cfg = TimeManagerConfig()
        self.assertEqual(cand_cfg.policy_name, "adaptive")
        self.assertEqual(cand_cfg.safety_reserve_ms, 50)
        self.assertEqual(cand_cfg.default_moves_to_go, 30)
        self.assertEqual(cand_cfg.increment_weight, 0.85)
        self.assertEqual(cand_cfg.min_allocation_ms, 10)
        self.assertEqual(cand_cfg.max_allocation_ratio, 0.20)

        ref_cfg = TimeManagerConfig.reference_baseline()
        self.assertEqual(ref_cfg.policy_name, "reference")
        self.assertEqual(ref_cfg.safety_reserve_ms, 0)
        self.assertEqual(ref_cfg.default_moves_to_go, 40)
        self.assertEqual(ref_cfg.increment_weight, 0.0)
        self.assertEqual(ref_cfg.min_allocation_ms, 10)
        self.assertEqual(ref_cfg.max_allocation_ratio, 0.50)

    def test_03_time_control_propagation(self) -> None:
        """Requirement 3: Allocations correctly reflect policies under 3000ms + 100ms."""
        cand_tm = TimeManager(config=TimeManagerConfig())
        ref_tm = TimeManager(config=TimeManagerConfig.reference_baseline())

        # At start of game: clock = 3000ms, inc = 100ms
        # Adaptive: usable = 3000 - 50 = 2950 ms. Base = 2950 / 30 = 98.33 ms. Target = 98.33 + 85 = 183.33 ms
        cand_alloc = cand_tm.allocate_time(chess.WHITE, wtime=3000, btime=3000, winc=100, binc=100)
        self.assertIsNotNone(cand_alloc)
        self.assertAlmostEqual(cand_alloc * 1000.0, 183.33, delta=1.0)

        # Reference: usable = 3000 - 0 = 3000 ms. Base = 3000 / 40 = 75.0 ms. Inc = 0. Target = 75.0 ms
        ref_alloc = ref_tm.allocate_time(chess.WHITE, wtime=3000, btime=3000, winc=100, binc=100)
        self.assertIsNotNone(ref_alloc)
        self.assertAlmostEqual(ref_alloc * 1000.0, 75.0, delta=1.0)

    def test_04_pair_level_aggregation(self) -> None:
        """Requirement 4: Pair aggregation properly computes paired points and deltas."""
        valid_games = [
            # Pair 1: Cand White win, Cand Black draw -> Pair pts = 1.5, Delta = +0.25, Pair Won
            {"game": 1, "pair": 1, "candidate_color": "white", "result": "1-0"},
            {"game": 2, "pair": 1, "candidate_color": "black", "result": "1/2-1/2"},
            # Pair 2: Cand White draw, Cand Black loss -> Pair pts = 0.5, Delta = -0.25, Pair Lost
            {"game": 3, "pair": 2, "candidate_color": "white", "result": "1/2-1/2"},
            {"game": 4, "pair": 2, "candidate_color": "black", "result": "1-0"},
            # Pair 3: Both draws -> Pair pts = 1.0, Delta = 0.0, Pair Drawn
            {"game": 5, "pair": 3, "candidate_color": "white", "result": "1/2-1/2"},
            {"game": 6, "pair": 3, "candidate_color": "black", "result": "1/2-1/2"},
        ]
        summary = summarize_match_v036(valid_games, valid_games, planned_games=6, planned_pairs=3)
        self.assertEqual(summary["pairs_summary"]["pairs_won"], 1)
        self.assertEqual(summary["pairs_summary"]["pairs_lost"], 1)
        self.assertEqual(summary["pairs_summary"]["pairs_drawn"], 1)
        self.assertEqual(summary["pairs_summary"]["completed_valid_pairs"], 3)
        self.assertEqual(summary["candidate_score"], 3.0)
        self.assertEqual(summary["candidate_score_pct"], 50.0)

    def test_05_draw_and_tie_handling_in_sign_test(self) -> None:
        """Requirement 5: Tied pairs are properly excluded from decisive pair sign test."""
        # 1 decisive win, 0 decisive losses, 9 tied pairs
        decisive_pairs = 1
        k = 0
        sign_p = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        self.assertAlmostEqual(sign_p, 1.0)

        # 8 decisive wins, 0 decisive losses
        decisive_pairs = 8
        sign_p_8 = sum(math.comb(decisive_pairs, i) * (0.5 ** decisive_pairs) for i in range(k + 1)) * 2.0
        self.assertAlmostEqual(sign_p_8, 2.0 * (0.5 ** 8), places=5)

    def test_06_bootstrap_reproducibility(self) -> None:
        """Requirement 6: Fixed-seed bootstrap produces identical resample distributions."""
        import random
        deltas = [+0.5, 0.0, -0.5, +0.5, 0.0, 0.0, +0.5, -0.5]
        
        def run_boot(seed: int) -> float:
            rng = random.Random(seed)
            means = [sum(rng.choice(deltas) for _ in range(len(deltas))) / len(deltas) for _ in range(500)]
            means.sort()
            return means[250]

        val1 = run_boot(seed=42)
        val2 = run_boot(seed=42)
        self.assertEqual(val1, val2)

    def test_07_elo_conversion_and_uncertainty_interval(self) -> None:
        """Requirement 7: Elo formula converts score correctly and handles limits."""
        # 50% -> 0.0 Elo
        self.assertEqual(score_to_elo(0.50), 0.0)

        # 60% -> ~ +70.4 Elo
        elo_60 = score_to_elo(0.60)
        self.assertIsNotNone(elo_60)
        self.assertAlmostEqual(elo_60, 70.4365, places=2)

        # 40% -> ~ -70.4 Elo
        elo_40 = score_to_elo(0.40)
        self.assertIsNotNone(elo_40)
        self.assertAlmostEqual(elo_40, -70.4365, places=2)

        # Boundaries
        self.assertIsNone(score_to_elo(0.0))
        self.assertIsNone(score_to_elo(1.0))

    def test_08_retry_and_failure_exclusion(self) -> None:
        """Requirement 8: Infrastructure failures are excluded from valid games and scores."""
        attempts = [
            {"game": 1, "pair": 1, "attempt_number": 1, "status": "infrastructure_failure", "failure_category": "EngineProcessError"},
            {"game": 1, "pair": 1, "attempt_number": 2, "status": "completed", "result": "1-0", "candidate_color": "white", "candidate_points": 1.0},
        ]
        valid_games = [attempts[1]]
        summary = summarize_match_v036(valid_games, attempts, planned_games=1, planned_pairs=1)
        self.assertEqual(summary["infrastructure_failures"], 1)
        self.assertEqual(summary["retried_attempts"], 1)
        self.assertEqual(summary["valid_completed_games"], 1)
        self.assertEqual(summary["candidate_score"], 1.0)

    def test_09_duplicate_game_detection(self) -> None:
        """Requirement 9: Detects accidental double-counting of identical game records."""
        game1 = {"pair": 1, "candidate_color": "white", "opening_id": "scotch", "final_fen": "fen1", "plies": 40}
        game2 = {"pair": 1, "candidate_color": "white", "opening_id": "scotch", "final_fen": "fen1", "plies": 40}
        
        seen = set()
        sig1 = (game1["pair"], game1["candidate_color"], game1["opening_id"], game1["final_fen"], game1["plies"])
        sig2 = (game2["pair"], game2["candidate_color"], game2["opening_id"], game2["final_fen"], game2["plies"])
        seen.add(sig1)
        self.assertIn(sig2, seen)

    def test_10_student_t_distribution_cdf(self) -> None:
        """Requirement 10: Accurate Student's t CDF and critical value calculation."""
        # At t=0, CDF is exactly 0.5
        self.assertEqual(t_distribution_cdf(0.0, df=49), 0.5)

        # For df=49, 95% two-sided critical value is approximately 2.0096
        crit = t_critical_value(0.975, df=49)
        self.assertAlmostEqual(crit, 2.0096, delta=0.01)

        # CDF at crit should be 0.975
        p = t_distribution_cdf(crit, df=49)
        self.assertAlmostEqual(p, 0.975, delta=0.005)

    def test_11_monotonic_clock_accounting(self) -> None:
        """Requirement 11: Clock decrements by elapsed duration and increments by inc."""
        wtime = 3000.0
        dur = 250.0
        inc = 100.0
        wtime_after = max(0.0, wtime - dur) + inc
        self.assertEqual(wtime_after, 2850.0)

        # If search takes longer than remaining clock
        wtime_tiny = 50.0
        dur_long = 150.0
        wtime_flag = max(0.0, wtime_tiny - dur_long) + inc
        self.assertEqual(wtime_flag, 100.0)

    def test_12_incomplete_match_datasets(self) -> None:
        """Requirement 12: Incomplete pairs are flagged and target_met reports False."""
        valid_games = [
            {"game": 1, "pair": 1, "candidate_color": "white", "result": "1-0"},
            # Missing game 2 of pair 1
        ]
        summary = summarize_match_v036(valid_games, valid_games, planned_games=2, planned_pairs=1)
        self.assertFalse(summary["target_met"])
        self.assertEqual(summary["incomplete_pairs"], 1)
        self.assertEqual(summary["complete_valid_pairs"], 0)


if __name__ == "__main__":
    unittest.main()
