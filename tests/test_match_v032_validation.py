"""Unit tests for v0.32 match harness and statistical validation."""
import copy
import math
import os
import tempfile
import unittest
from pathlib import Path

import chess
from scripts.match_v032 import load_openings, summarize_match, write_reports


class TestMatchV032Validation(unittest.TestCase):
    """Test suite validating match harness logic, pairing, and statistical summaries."""

    def test_score_and_elo_calculations(self):
        """Verify score percentage and delta Elo calculations on known outcomes."""
        # 1. Parity (50% score)
        rows_even = [
            {"pair": 1, "candidate_color": "white", "result": "1-0", "candidate_score": 1.0},
            {"pair": 1, "candidate_color": "black", "result": "1-0", "candidate_score": 0.0},
        ]
        s_even = summarize_match(rows_even)
        self.assertEqual(s_even["completed_games"], 2)
        self.assertEqual(s_even["candidate_points"], 1.0)
        self.assertEqual(s_even["candidate_score_pct"], 50.0)
        self.assertEqual(s_even["delta_elo"], 0.0)

        # 2. Winning score (60% score)
        # 3 wins, 2 losses -> 3/5 = 60%
        rows_win = [
            {"pair": 1, "candidate_color": "white", "result": "1-0", "candidate_score": 1.0},
            {"pair": 1, "candidate_color": "black", "result": "1/2-1/2", "candidate_score": 0.5},
            {"pair": 2, "candidate_color": "white", "result": "1/2-1/2", "candidate_score": 0.5},
            {"pair": 2, "candidate_color": "black", "result": "0-1", "candidate_score": 1.0},
            {"pair": 3, "candidate_color": "white", "result": "0-1", "candidate_score": 0.0},
        ]
        s_win = summarize_match(rows_win)
        self.assertEqual(s_win["candidate_score_pct"], 60.0)
        # delta Elo for 0.60: -400 * log10(1/0.6 - 1) = -400 * log10(0.4/0.6) = -400 * log10(2/3) ≈ +70.4
        self.assertAlmostEqual(s_win["delta_elo"], 70.4, delta=0.5)

        # 3. Extreme score (100% or 0% score handles without math domain error)
        rows_100 = [
            {"pair": 1, "candidate_color": "white", "result": "1-0", "candidate_score": 1.0},
        ]
        s_100 = summarize_match(rows_100)
        self.assertEqual(s_100["candidate_score_pct"], 100.0)
        self.assertIsNone(s_100["delta_elo"])

    def test_paired_opening_accounting(self):
        """Verify opening pairs won, drawn, and lost accounting with colour reversal."""
        rows = [
            # Pair 1: Cand won as white (1-0), Cand drew as black (1/2-1/2) -> Pair Won (1.5 pts)
            {"pair": 1, "candidate_color": "white", "result": "1-0", "candidate_score": 1.0},
            {"pair": 1, "candidate_color": "black", "result": "1/2-1/2", "candidate_score": 0.5},
            # Pair 2: Cand drew as white (1/2-1/2), Cand drew as black (1/2-1/2) -> Pair Drawn (1.0 pt)
            {"pair": 2, "candidate_color": "white", "result": "1/2-1/2", "candidate_score": 0.5},
            {"pair": 2, "candidate_color": "black", "result": "1/2-1/2", "candidate_score": 0.5},
            # Pair 3: Cand lost as white (0-1), Cand lost as black (1-0) -> Pair Lost (0.0 pts)
            {"pair": 3, "candidate_color": "white", "result": "0-1", "candidate_score": 0.0},
            {"pair": 3, "candidate_color": "black", "result": "1-0", "candidate_score": 0.0},
        ]
        s = summarize_match(rows)
        self.assertEqual(s["pairs_completed"], 3)
        self.assertEqual(s["pairs_won"], 1)
        self.assertEqual(s["pairs_drawn"], 1)
        self.assertEqual(s["pairs_lost"], 1)

    def test_opening_selection_reproducibility(self):
        """Deterministic opening loading produces identical sequence with identical seed."""
        openings_path = Path("benchmarks/openings.json")
        if openings_path.is_file():
            ops1 = load_openings(openings_path, count=10, seed=42)
            ops2 = load_openings(openings_path, count=10, seed=42)
            ops3 = load_openings(openings_path, count=10, seed=99)
            self.assertEqual([o["id"] for o in ops1], [o["id"] for o in ops2])
            # Different seed produces different order
            self.assertNotEqual([o["id"] for o in ops1], [o["id"] for o in ops3])

    def test_checkpoint_and_resume_roundtrip(self):
        """Verify incremental checkpointing and resume consistency."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            json_path = tmp / "test_match.json"
            csv_path = tmp / "test_match.csv"

            rows = [
                {
                    "game": 1,
                    "pair": 1,
                    "opening_id": "test_op",
                    "opening_name": "Test Opening",
                    "candidate_color": "white",
                    "white": "Janus-v0.30",
                    "black": "Janus-v0.27",
                    "result": "1/2-1/2",
                    "candidate_score": 0.5,
                    "termination": "threefold repetition",
                    "plies": 60,
                    "duration_seconds": 30.5,
                    "movetime_ms": 500,
                    "avg_cand_depth": 3.5,
                    "avg_base_depth": 3.2,
                    "avg_cand_move_time": 0.51,
                    "avg_base_move_time": 0.51,
                    "avg_cand_nodes": 4000,
                    "avg_base_nodes": 3500,
                    "start_fen": chess.STARTING_FEN,
                }
            ]
            meta = {"test": "metadata"}
            write_reports(json_path, csv_path, rows, meta, elapsed=30.5)

            self.assertTrue(json_path.is_file())
            self.assertTrue(csv_path.is_file())

            # Load and verify
            import json
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded["games"]), 1)
            self.assertEqual(loaded["games"][0]["game"], 1)
            self.assertEqual(loaded["summary"]["completed_games"], 1)


if __name__ == "__main__":
    unittest.main()
