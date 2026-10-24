"""Unit tests validating Project Janus v0.33 match dataset, pairing, and statistical analysis."""
import json
import unittest
from pathlib import Path


class TestMatchV033Validation(unittest.TestCase):
    """Integrity and statistical reconciliation tests for v0.33 100-game match data."""

    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parents[1]
        cls.json_path = base / "analysis/v0.33/match/v033_match_500ms.json"
        cls.report_path = base / "analysis/v0.33/match/v033_analysis_report.json"
        with open(cls.json_path, "r", encoding="utf-8") as f:
            cls.data = json.load(f)
        with open(cls.report_path, "r", encoding="utf-8") as f:
            cls.report = json.load(f)

    def test_complete_match_inventory(self):
        games = self.data["games"]
        self.assertEqual(len(games), 100)
        self.assertEqual(self.data["summary"]["completed_games"], 100)
        self.assertEqual(self.data["metadata"]["candidate_name"], "Janus-v0.33")
        self.assertEqual(self.data["metadata"]["baseline_name"], "Janus-v0.30")
        self.assertEqual(self.data["metadata"]["movetime_ms"], 500)

        # Monotonic sequential game IDs
        game_ids = [g["game"] for g in games]
        self.assertEqual(game_ids, list(range(1, 101)))

    def test_paired_opening_integrity(self):
        games = self.data["games"]
        pairs = {}
        for g in games:
            pairs.setdefault(g["pair"], []).append(g)

        self.assertEqual(len(pairs), 50)
        for p_id, p_games in pairs.items():
            self.assertEqual(len(p_games), 2, f"Pair {p_id} does not have exactly 2 games")
            g1, g2 = p_games[0], p_games[1]
            self.assertEqual(g1["start_fen"], g2["start_fen"], f"Pair {p_id} FEN mismatch")
            self.assertEqual(g1["opening_id"], g2["opening_id"])
            colors = {g1["candidate_color"], g2["candidate_color"]}
            self.assertEqual(colors, {"white", "black"}, f"Pair {p_id} color imbalance")

    def test_score_and_pair_reconciliation(self):
        s = self.data["summary"]
        self.assertEqual(s["candidate_wins"], 33)
        self.assertEqual(s["draws"], 38)
        self.assertEqual(s["candidate_losses"], 29)
        self.assertEqual(s["candidate_points"], 52.0)
        self.assertEqual(s["candidate_score_pct"], 52.0)
        self.assertEqual(s["delta_elo"], 13.9)

        self.assertEqual(s["pairs_won"], 17)
        self.assertEqual(s["pairs_drawn"], 21)
        self.assertEqual(s["pairs_lost"], 12)

    def test_color_breakdown(self):
        col = self.data["summary"]["by_color"]
        w = col["white"]
        b = col["black"]
        self.assertEqual(w["games"], 50)
        self.assertEqual(b["games"], 50)
        self.assertEqual(w["wins"], 24)
        self.assertEqual(w["draws"], 16)
        self.assertEqual(w["losses"], 10)
        self.assertEqual(w["score_pts"], 32.0)
        self.assertEqual(w["score_pct"], 64.0)

        self.assertEqual(b["wins"], 9)
        self.assertEqual(b["draws"], 22)
        self.assertEqual(b["losses"], 19)
        self.assertEqual(b["score_pts"], 20.0)
        self.assertEqual(b["score_pct"], 40.0)

    def test_statistical_estimates_invariants(self):
        stat = self.report["elo_statistics"]
        self.assertEqual(stat["delta_elo"], 13.9)
        self.assertAlmostEqual(stat["elo_se"], 27.5, delta=0.5)
        # CI covers 0.0 (parity)
        self.assertLess(stat["elo_ci_95"][0], 0.0)
        self.assertGreater(stat["elo_ci_95"][1], 0.0)


if __name__ == "__main__":
    unittest.main()
