"""Unit tests for RFP diagnostic telemetry instrumentation (v0.44)."""
import json
import tempfile
from pathlib import Path
import unittest
import chess

from janus.search import JanusSearch


class TestRfpTelemetry(unittest.TestCase):
    def setUp(self):
        self.board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5")

    def test_default_diagnostics_disabled(self):
        """Verify that diagnostic_rfp is False by default and produces empty rfp_events."""
        engine = JanusSearch(enable_rfp=False)
        self.assertFalse(engine.diagnostic_rfp)
        res = engine.search(self.board.copy(), max_depth=3)
        self.assertEqual(len(res.rfp_events), 0)

    def test_deterministic_equivalence_when_disabled(self):
        """Verify search produces identical moves, scores, and nodes regardless of diagnostic_rfp."""
        engine_base = JanusSearch(enable_rfp=True, diagnostic_rfp=False)
        res_base = engine_base.search(self.board.copy(), max_depth=3)

        engine_diag = JanusSearch(enable_rfp=True, diagnostic_rfp=True)
        res_diag = engine_diag.search(self.board.copy(), max_depth=3)

        self.assertEqual(res_base.best_move, res_diag.best_move)
        self.assertEqual(res_base.score, res_diag.score)
        self.assertEqual(res_base.nodes, res_diag.nodes)
        self.assertEqual(res_base.depth, res_diag.depth)

    def test_telemetry_records_events_when_enabled(self):
        """Verify that RFP diagnostic telemetry captures expected event schema."""
        engine = JanusSearch(enable_rfp=True, diagnostic_rfp=True)
        res = engine.search(self.board.copy(), max_depth=3)

        self.assertGreater(len(res.rfp_events), 0)
        required_keys = {
            "fen", "ply", "depth", "static_eval", "beta",
            "alpha", "margin", "cutoff", "reason", "best_move", "rfp_enabled"
        }
        for ev in res.rfp_events:
            self.assertTrue(required_keys.issubset(ev.keys()))
            self.assertIn(ev["depth"], (1, 2))
            self.assertGreater(ev["ply"], 0)
            self.assertIsInstance(ev["cutoff"], bool)
            self.assertIsInstance(ev["margin"], int)
            self.assertTrue(ev["rfp_enabled"])

    def test_passive_rfp_probe_without_pruning(self):
        """Verify that diagnostic_rfp=True with enable_rfp=False acts as a passive counterfactual probe."""
        engine_k0 = JanusSearch(enable_rfp=False, diagnostic_rfp=False)
        res_k0 = engine_k0.search(self.board.copy(), max_depth=3)

        engine_probe = JanusSearch(enable_rfp=False, diagnostic_rfp=True)
        res_probe = engine_probe.search(self.board.copy(), max_depth=3)

        # Move, score, and nodes must exactly match K0 baseline
        self.assertEqual(res_k0.best_move, res_probe.best_move)
        self.assertEqual(res_k0.score, res_probe.score)
        self.assertEqual(res_k0.nodes, res_probe.nodes)
        # But rfp_events are collected
        self.assertGreater(len(res_probe.rfp_events), 0)
        for ev in res_probe.rfp_events:
            self.assertFalse(ev["rfp_enabled"])

    def test_telemetry_flush_to_jsonl(self):
        """Verify flush_rfp_telemetry correctly writes JSONL records and clears internal buffer."""
        engine = JanusSearch(enable_rfp=True, diagnostic_rfp=True)
        engine.search(self.board.copy(), max_depth=3)
        self.assertGreater(len(engine.rfp_events), 0)
        initial_count = len(engine.rfp_events)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "telemetry_test.jsonl"
            flushed = engine.flush_rfp_telemetry(str(out_file))
            self.assertEqual(flushed, initial_count)
            self.assertEqual(len(engine.rfp_events), 0)

            # Read back and verify lines
            lines = out_file.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), initial_count)
            first_obj = json.loads(lines[0])
            self.assertIn("fen", first_obj)
            self.assertIn("cutoff", first_obj)


if __name__ == "__main__":
    unittest.main()

