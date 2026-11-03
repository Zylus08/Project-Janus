"""Unit tests for iteration-level search telemetry and publication invariance (v0.45)."""
import json
import tempfile
from pathlib import Path
import unittest
import chess

from janus.search import JanusSearch


class TestIterationTelemetry(unittest.TestCase):
    def setUp(self):
        self.board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5")

    def test_default_diagnostics_disabled(self):
        """Verify that diagnostic_iterations is False by default and produces empty iteration_records."""
        engine = JanusSearch(diagnostic_iterations=False)
        self.assertFalse(engine.diagnostic_iterations)
        res = engine.search(self.board.copy(), max_depth=3)
        self.assertEqual(len(res.iteration_records), 0)

    def test_deterministic_equivalence(self):
        """Verify search produces identical moves, scores, and nodes regardless of diagnostic_iterations."""
        engine_base = JanusSearch(diagnostic_iterations=False)
        res_base = engine_base.search(self.board.copy(), max_depth=3)

        engine_diag = JanusSearch(diagnostic_iterations=True)
        res_diag = engine_diag.search(self.board.copy(), max_depth=3)

        self.assertEqual(res_base.best_move, res_diag.best_move)
        self.assertEqual(res_base.score, res_diag.score)
        self.assertEqual(res_base.nodes, res_diag.nodes)
        self.assertEqual(res_base.depth, res_diag.depth)

    def test_iteration_records_schema_and_completion(self):
        """Verify schema of completed iteration telemetry records."""
        engine = JanusSearch(diagnostic_iterations=True)
        res = engine.search(self.board.copy(), max_depth=3)

        self.assertEqual(len(res.iteration_records), 3)
        required_keys = {
            "iteration_depth", "iteration_start_time", "iteration_end_time",
            "iteration_elapsed_s", "nodes_consumed", "cumulative_nodes", "nps",
            "best_move", "pv", "score", "aspiration_retries", "completed",
            "aborted", "abort_reason", "published", "prev_completed_depth", "rfp_enabled"
        }
        for idx, rec in enumerate(res.iteration_records, 1):
            self.assertTrue(required_keys.issubset(rec.keys()))
            self.assertEqual(rec["iteration_depth"], idx)
            self.assertTrue(rec["completed"])
            self.assertFalse(rec["aborted"])
            self.assertIsNone(rec["abort_reason"])
            self.assertTrue(rec["published"])
            self.assertEqual(rec["prev_completed_depth"], idx - 1)

    def test_interrupted_iteration_invariance(self):
        """Verify that an interrupted iteration does not overwrite the published move/score of completed iteration."""
        engine = JanusSearch(diagnostic_iterations=True)
        # Search with tight time limit that allows depth 1/2 but aborts depth 3/4
        res = engine.search(self.board.copy(), max_depth=6, time_limit=0.030)

        # There must be at least one completed iteration and one aborted record
        completed_records = [r for r in res.iteration_records if r["completed"]]
        aborted_records = [r for r in res.iteration_records if r["aborted"]]

        self.assertGreater(len(completed_records), 0)
        self.assertGreater(len(aborted_records), 0)

        last_completed = completed_records[-1]
        aborted = aborted_records[0]

        # The published depth and move must match the LAST COMPLETED iteration
        self.assertEqual(res.depth, last_completed["iteration_depth"])
        self.assertEqual(res.best_move.uci() if res.best_move else None, last_completed["best_move"])
        self.assertEqual(res.score, last_completed["score"])

        # Aborted record must reflect non-published status
        self.assertFalse(aborted["completed"])
        self.assertTrue(aborted["aborted"])
        self.assertIn(aborted["abort_reason"], ("timeout", "stop_event"))
        self.assertFalse(aborted["published"])
        self.assertEqual(aborted["prev_completed_depth"], last_completed["iteration_depth"])

    def test_telemetry_flush_to_jsonl(self):
        """Verify flush_iteration_telemetry exports valid JSONL lines and empties internal queue."""
        engine = JanusSearch(diagnostic_iterations=True)
        engine.search(self.board.copy(), max_depth=3)
        self.assertGreater(len(engine.iteration_records), 0)
        initial_count = len(engine.iteration_records)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "iteration_telemetry.jsonl"
            flushed = engine.flush_iteration_telemetry(str(out_file))
            self.assertEqual(flushed, initial_count)
            self.assertEqual(len(engine.iteration_records), 0)

            lines = out_file.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), initial_count)
            first_obj = json.loads(lines[0])
            self.assertIn("iteration_depth", first_obj)
            self.assertIn("nodes_consumed", first_obj)

    def test_concurrent_rfp_and_iteration_telemetry(self):
        """Verify both diagnostic_rfp and diagnostic_iterations operate concurrently without error."""
        engine = JanusSearch(enable_rfp=True, diagnostic_rfp=True, diagnostic_iterations=True)
        res = engine.search(self.board.copy(), max_depth=3)
        self.assertGreater(len(res.rfp_events), 0)
        self.assertGreater(len(res.iteration_records), 0)


if __name__ == "__main__":
    unittest.main()

