"""Unit test verifying independent replication of Milestone v0.32 match data and statistics."""
import unittest
from pathlib import Path

from scripts.audit_v032_replication import audit_v032_data


class TestV032AuditReplication(unittest.TestCase):
    """Rigorous verification of v0.32 match dataset and statistical reproduction."""

    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parents[1]
        json_path = base / "analysis/v0.32/match/v032_match_500ms.json"
        csv_path = base / "analysis/v0.32/match/v032_match_500ms.csv"
        pgn_path = base / "analysis/v0.32/match/v032_match_500ms.pgn"
        summary_path = base / "analysis/v0.32/match/v032_match_summary.json"

        cls.audit = audit_v032_data(json_path, csv_path, pgn_path, summary_path)

    def test_complete_match_record(self):
        self.assertEqual(self.audit["num_games_json"], 100)
        self.assertEqual(self.audit["num_games_csv"], 100)
        self.assertEqual(self.audit["num_games_pgn"], 100)
        self.assertTrue(self.audit["game_ids_contiguous"])
        self.assertEqual(self.audit["pairs_count"], 50)
        self.assertEqual(len(self.audit["pair_integrity_errors"]), 0)
        self.assertEqual(len(self.audit["csv_mismatches"]), 0)
        self.assertEqual(len(self.audit["pgn_mismatches"]), 0)
        self.assertEqual(len(self.audit["discrepancies_with_reported_summary"]), 0)

    def test_game_and_color_totals(self):
        t = self.audit["tallies_calculated"]
        self.assertEqual(t["candidate_wins"], 23)
        self.assertEqual(t["draws"], 48)
        self.assertEqual(t["candidate_losses"], 29)
        self.assertEqual(t["candidate_points"], 47.0)
        self.assertEqual(t["candidate_score_pct"], 47.0)

        w = t["by_color"]["white"]
        b = t["by_color"]["black"]
        self.assertEqual(w["games"], 50)
        self.assertEqual(b["games"], 50)
        self.assertEqual(w["points"], 23.5)
        self.assertEqual(b["points"], 23.5)
        self.assertEqual(w["score_pct"], 47.0)
        self.assertEqual(b["score_pct"], 47.0)

    def test_pair_outcomes(self):
        p = self.audit["pair_outcomes_calculated"]
        self.assertEqual(p["won"], 15)
        self.assertEqual(p["drawn"], 16)
        self.assertEqual(p["lost"], 19)

    def test_statistical_estimates(self):
        s = self.audit["statistical_recomputation"]
        self.assertAlmostEqual(s["observed_score_pct"], 47.0, places=2)
        self.assertEqual(s["wald_ci_95"], [39.92, 54.08])
        self.assertAlmostEqual(s["delta_elo"], -20.87, places=1)
        self.assertEqual(s["pair_bootstrap_ci_95_seed42_2k"], [40.0, 54.5])
        self.assertGreaterEqual(s["sign_test_two_tailed_p_value"], 0.5)


if __name__ == "__main__":
    unittest.main()
