import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match

class MatchSummaryTests(unittest.TestCase):
    def test_results_count_from_janus_perspective(self):
        rows = [
            {"result": "1-0", "janus_color": "white"},
            {"result": "0-1", "janus_color": "black"},
            {"result": "1/2-1/2", "janus_color": "white"},
            {"result": "0-1", "janus_color": "white"},
            {"result": "*", "janus_color": "black"},
        ]
        result = match.summarize(rows)
        self.assertEqual((result["janus_wins"], result["draws"], result["janus_losses"]), (2, 1, 1))
        self.assertEqual(result["unfinished_games"], 1)
        self.assertEqual(result["janus_score_points"], 2.5)
        self.assertEqual(result["janus_score_percentage"], 62.5)

    def test_all_unfinished_has_no_percentage(self):
        result = match.summarize([{"result": "*", "janus_color": "white"}])
        self.assertIsNone(result["janus_score_percentage"])

if __name__ == "__main__":
    unittest.main()
