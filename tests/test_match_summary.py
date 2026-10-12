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

    def test_results_color_breakdown(self):
        rows = [
            {"result": "1-0", "janus_color": "white"},
            {"result": "0-1", "janus_color": "black"},
            {"result": "1/2-1/2", "janus_color": "white"},
            {"result": "0-1", "janus_color": "white"},
            {"result": "*", "janus_color": "black"},
        ]
        result = match.summarize(rows)
        self.assertIn("by_color", result)
        white_stats = result["by_color"]["white"]
        black_stats = result["by_color"]["black"]
        self.assertEqual((white_stats["wins"], white_stats["draws"], white_stats["losses"], white_stats["unfinished"]), (1, 1, 1, 0))
        self.assertEqual((black_stats["wins"], black_stats["draws"], black_stats["losses"], black_stats["unfinished"]), (1, 0, 0, 1))

    def test_write_reports_handles_empty_and_partial_rows(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            json_empty = tmppath / "empty.json"
            csv_empty = tmppath / "empty.csv"
            # Must not raise IndexError when rows is empty
            match.write_reports(json_empty, csv_empty, [], {"meta": "val"}, 1.5)
            self.assertTrue(json_empty.exists())
            self.assertTrue(csv_empty.exists())

            json_partial = tmppath / "partial.json"
            csv_partial = tmppath / "partial.csv"
            rows = [{"game": 1, "janus_color": "white", "white": "Janus", "black": "Stockfish",
                     "result": "0-1", "termination": "checkmate", "plies": 40, "depth": 3}]
            match.write_reports(json_partial, csv_partial, rows, {"meta": "val"}, 2.5)
            self.assertTrue(json_partial.exists())
            self.assertTrue(csv_partial.exists())

if __name__ == "__main__":
    unittest.main()
