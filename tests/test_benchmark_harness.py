import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import benchmark  # noqa: E402


class BenchmarkHarnessTests(unittest.TestCase):
    def test_positions_load_and_are_valid(self):
        positions = benchmark.load_positions(ROOT / "benchmarks" / "positions.json")
        self.assertGreaterEqual(len(positions), 5)

    def test_duplicate_ids_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "positions.json"
            row = {
                "id": "same", "category": "test", "description": "test",
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            }
            path.write_text(json.dumps([row, row]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                benchmark.load_positions(path)

    def test_smoke_benchmark_returns_legal_moves_or_terminal_none(self):
        positions = benchmark.load_positions(ROOT / "benchmarks" / "positions.json")
        report = benchmark.run_benchmark(positions[:2] + [positions[3], positions[5]], depth=1, time_limit=None)
        self.assertEqual(report["summary"]["positions"], 4)
        for row in report["results"]:
            self.assertTrue(row["legal_best_move"])
        terminal = next(row for row in report["results"] if row["id"] == "stalemate")
        self.assertEqual(terminal["best_move_uci"], "")
        self.assertEqual(terminal["completed_depth"], 0)


if __name__ == "__main__":
    unittest.main()
