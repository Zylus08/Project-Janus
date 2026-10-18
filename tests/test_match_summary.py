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
            rows = [{"game": 1, "pair": 1, "opening_id": "open_game", "janus_color": "white",
                     "white": "Janus", "black": "Stockfish", "result": "0-1",
                     "termination": "checkmate", "plies": 40, "depth": 3,
                     "start_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}]
            match.write_reports(json_partial, csv_partial, rows, {"meta": "val"}, 2.5)
            self.assertTrue(json_partial.exists())
            self.assertTrue(csv_partial.exists())

    def test_load_openings_deterministic_and_paired(self):
        openings_path = ROOT / "benchmarks" / "openings.json"
        self.assertTrue(openings_path.exists(), "benchmarks/openings.json must exist")
        # Same seed must yield identical sequence
        ops1 = match.load_openings(openings_path, count=10, seed=42)
        ops2 = match.load_openings(openings_path, count=10, seed=42)
        self.assertEqual(len(ops1), 10)
        self.assertEqual([o["id"] for o in ops1], [o["id"] for o in ops2])

        # Different seed yields different sequence
        ops3 = match.load_openings(openings_path, count=10, seed=999)
        self.assertNotEqual([o["id"] for o in ops1], [o["id"] for o in ops3])

        # Missing path falls back safely to startpos
        fallback = match.load_openings(Path("nonexistent.json"), count=4)
        self.assertEqual(len(fallback), 4)
        self.assertEqual(fallback[0]["id"], "startpos")

    def test_paired_openings_color_balance(self):
        games_count = 6
        pairs_count = games_count // 2
        openings_path = ROOT / "benchmarks" / "openings.json"
        openings = match.load_openings(openings_path, count=pairs_count, seed=42)

        assigned_colors = []
        assigned_openings = []
        for i in range(games_count):
            pair_idx = i // 2
            color = "white" if i % 2 == 0 else "black"
            assigned_colors.append(color)
            assigned_openings.append(openings[pair_idx]["id"])

        # Exact color balance
        self.assertEqual(assigned_colors.count("white"), games_count // 2)
        self.assertEqual(assigned_colors.count("black"), games_count // 2)

        # Each pair shares the exact same opening
        for p in range(pairs_count):
            g1_op = assigned_openings[2 * p]
            g2_op = assigned_openings[2 * p + 1]
            self.assertEqual(g1_op, g2_op)
            self.assertEqual(assigned_colors[2 * p], "white")
            self.assertEqual(assigned_colors[2 * p + 1], "black")

    def test_report_metadata_completeness(self):
        import json, tempfile
        metadata = {
            "janus_command": ["python", "-m", "janus.uci"],
            "stockfish_command": ["stockfish.exe"],
            "stockfish_threads": 1,
            "stockfish_hash_mb": 128,
            "stockfish_skill": 5,
            "stockfish_elo": None,
            "depth_each_move": 3,
            "max_plies_per_game": 240,
            "openings_path": "benchmarks/openings.json",
            "seed": 42,
            "pairs_count": 25,
            "timestamp_utc": "2026-10-13T00:00:00Z",
            "python_version": "3.12.8",
            "method": "paired opening positions with alternating colours",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test_report.json"
            csv_file = Path(tmpdir) / "test_report.csv"
            match.write_reports(json_file, csv_file, [], metadata, 10.0)
            data = json.loads(json_file.read_text(encoding="utf-8"))
            self.assertIn("metadata", data)
            meta = data["metadata"]
            for key in ["stockfish_threads", "stockfish_hash_mb", "stockfish_skill", "depth_each_move", "seed", "pairs_count"]:
                self.assertIn(key, meta)
                self.assertEqual(meta[key], metadata[key])

    def test_paired_statistical_analysis(self):
        import analyze_v025_match
        import json, tempfile
        # Build synthetic 4-game (2-pair) match JSON
        test_data = {
            "metadata": {
                "engine1_name": "Janus-Baseline",
                "engine2_name": "Janus-SEE",
            },
            "games": [
                {"game": 1, "pair": 1, "opening_id": "scotch", "janus_color": "white", "result": "1-0", "duration_seconds": 5.0, "termination": "checkmate"},
                {"game": 2, "pair": 1, "opening_id": "scotch", "janus_color": "black", "result": "1/2-1/2", "duration_seconds": 6.0, "termination": "threefold repetition"},
                {"game": 3, "pair": 2, "opening_id": "italian", "janus_color": "white", "result": "0-1", "duration_seconds": 4.0, "termination": "checkmate"},
                {"game": 4, "pair": 2, "opening_id": "italian", "janus_color": "black", "result": "1-0", "duration_seconds": 4.5, "termination": "checkmate"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test_match.json"
            json_file.write_text(json.dumps(test_data), encoding="utf-8")
            summary = analyze_v025_match.analyze_match(json_file)
            self.assertEqual(summary["match"]["total_games"], 4)
            self.assertEqual(summary["paired_analysis"]["sample_size_pairs"], 2)
            self.assertEqual(summary["paired_analysis"]["treatment_pairs_won"], 1)
            self.assertEqual(summary["paired_analysis"]["treatment_pairs_lost"], 1)
            self.assertEqual(summary["paired_analysis"]["treatment_pairs_tied"], 0)
            self.assertIn("p_value_two_sided", summary["paired_analysis"])
            self.assertIn("paired_bootstrap_95_ci_pct", summary["paired_analysis"])

    def test_paired_statistical_analysis_v026(self):
        import analyze_v026_match
        import json, tempfile
        test_data = {
            "metadata": {
                "engine1_name": "Janus-Baseline",
                "engine2_name": "Janus-SEE-Ordering",
            },
            "games": [
                {"game": 1, "pair": 1, "opening_id": "scotch", "janus_color": "white", "result": "1-0", "duration_seconds": 5.0, "termination": "checkmate"},
                {"game": 2, "pair": 1, "opening_id": "scotch", "janus_color": "black", "result": "1/2-1/2", "duration_seconds": 6.0, "termination": "threefold repetition"},
                {"game": 3, "pair": 2, "opening_id": "italian", "janus_color": "white", "result": "0-1", "duration_seconds": 4.0, "termination": "checkmate"},
                {"game": 4, "pair": 2, "opening_id": "italian", "janus_color": "black", "result": "1-0", "duration_seconds": 4.5, "termination": "checkmate"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test_match.json"
            json_file.write_text(json.dumps(test_data), encoding="utf-8")
            summary = analyze_v026_match.analyze_match(json_file)
            self.assertEqual(summary["match"]["total_games"], 4)
            self.assertEqual(summary["paired_analysis"]["sample_size_pairs"], 2)
            self.assertEqual(summary["paired_analysis"]["treatment_pairs_won"], 1)
            self.assertEqual(summary["paired_analysis"]["treatment_pairs_lost"], 1)
            self.assertEqual(summary["paired_analysis"]["treatment_pairs_tied"], 0)
            self.assertIn("p_value_two_sided", summary["paired_analysis"])
            self.assertIn("paired_bootstrap_95_ci_pct", summary["paired_analysis"])

if __name__ == "__main__":
    unittest.main()
