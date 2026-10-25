"""Validation test suite for Project Janus v0.34 experimental match and benchmark artifacts."""
import json
from pathlib import Path
import unittest

import chess
import chess.pgn


ROOT = Path(__file__).resolve().parents[1]
MATCH_DIR = ROOT / "analysis" / "v0.34" / "match"
CALIB_DIR = ROOT / "analysis" / "v0.34" / "calibration"
ABLATION_DIR = ROOT / "analysis" / "v0.34" / "ablation"


class TestPilotValidation(unittest.TestCase):
    """Verify pilot match artifacts and execution properties."""

    def setUp(self):
        self.json_path = MATCH_DIR / "v034_pilot_500ms.json"
        self.csv_path = MATCH_DIR / "v034_pilot_500ms.csv"
        self.pgn_path = MATCH_DIR / "v034_pilot_500ms.pgn"

    def test_pilot_artifacts_exist(self):
        self.assertTrue(self.json_path.is_file(), "Pilot JSON missing")
        self.assertTrue(self.csv_path.is_file(), "Pilot CSV missing")
        self.assertTrue(self.pgn_path.is_file(), "Pilot PGN missing")

    def test_pilot_game_integrity(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        summary = data.get("summary", {})
        games = data.get("games", [])

        self.assertEqual(meta.get("baseline_name"), "Janus-v0.30")
        self.assertEqual(meta.get("candidate_name"), "Janus-v0.34")
        self.assertEqual(meta.get("movetime_ms"), 500)
        self.assertEqual(len(games), 2)
        self.assertEqual(summary.get("total_completed"), 2)

        # Alternating colors within pair
        self.assertEqual(games[0]["candidate_color"], "white")
        self.assertEqual(games[1]["candidate_color"], "black")
        self.assertEqual(games[0]["pair"], 1)
        self.assertEqual(games[1]["pair"], 1)

    def test_pilot_movetime_compliance(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for g in data.get("games", []):
            cand_t = g.get("avg_cand_move_time")
            base_t = g.get("avg_base_move_time")
            self.assertIsNotNone(cand_t)
            self.assertIsNotNone(base_t)
            # Both engines should average within 50ms of 0.500s
            self.assertAlmostEqual(cand_t, 0.500, delta=0.05)
            self.assertAlmostEqual(base_t, 0.500, delta=0.05)


class TestAblationArtifacts(unittest.TestCase):
    """Verify ablation study results and metrics."""

    def test_ablation_results_completeness(self):
        ablation_file = ABLATION_DIR / "ablation_results.json"
        self.assertTrue(ablation_file.is_file(), "Ablation results missing")

        with open(ablation_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        micro = data.get("microbenchmark", {})
        expected_configs = [
            "A_v030_baseline",
            "B_v033_pawn_structure",
            "C_v033_all_features",
            "D_v034_tapered",
            "E_calibrated_static",
            "F_v034_tapered_calibrated",
        ]
        for cfg in expected_configs:
            self.assertIn(cfg, micro)
            self.assertGreater(micro[cfg]["evals_per_sec"], 20000)

        search = data.get("search_ablation", {})
        self.assertIn("depth_4", search)
        self.assertIn("depth_5", search)
        for cfg in expected_configs:
            self.assertIn(cfg, search["depth_4"])
            self.assertIn(cfg, search["depth_5"])


class TestCalibrationArtifacts(unittest.TestCase):
    """Verify weight calibration and dataset artifacts."""

    def test_calibration_summary(self):
        summary_file = CALIB_DIR / "dataset_summary.json"
        self.assertTrue(summary_file.is_file(), "Dataset summary missing")

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        self.assertGreaterEqual(summary["total_samples"], 1000)
        self.assertGreater(summary["train_samples"], 500)
        self.assertGreater(summary["val_samples"], 150)
        self.assertGreater(summary["test_samples"], 150)

    def test_calibration_results(self):
        results_file = CALIB_DIR / "calibration_results.json"
        self.assertTrue(results_file.is_file(), "Calibration results missing")

        with open(results_file, "r", encoding="utf-8") as f:
            res = json.load(f)

        comp = res.get("out_of_sample_comparison", {})
        self.assertIn("test_mse_change", comp)
        self.assertIn("val_mse_change", comp)
        self.assertIn("generalization_verdict", comp)


if __name__ == "__main__":
    unittest.main()
