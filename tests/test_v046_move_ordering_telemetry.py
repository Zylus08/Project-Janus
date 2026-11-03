"""Tests for v0.46 move-ordering diagnostic telemetry using standard unittest."""
import unittest
import tempfile
import os
import json
import chess
from janus.search import JanusSearch, SearchResult


class TestV046MoveOrderingTelemetry(unittest.TestCase):
    def test_ordering_telemetry_disabled_by_default(self):
        """Verify that ordering telemetry is disabled by default and produces empty stats."""
        searcher = JanusSearch()
        self.assertFalse(searcher.diagnostic_ordering)
        board = chess.Board()
        res = searcher.search(board, max_depth=3)
        self.assertIsInstance(res, SearchResult)
        self.assertEqual(res.ordering_stats, {})
        self.assertEqual(res.ordering_events, [])

    def test_ordering_telemetry_enabled(self):
        """Verify that diagnostic_ordering=True collects cutoffs and ordering metrics."""
        searcher = JanusSearch(diagnostic_ordering=True)
        board = chess.Board()
        res = searcher.search(board, max_depth=3)
        self.assertIsInstance(res, SearchResult)
        stats = res.ordering_stats
        self.assertNotEqual(stats, {})
        self.assertIn("total_cutoffs", stats)
        self.assertIn("first_move_cutoffs", stats)
        self.assertIn("late_move_cutoffs", stats)
        self.assertIn("first_move_cutoff_rate", stats)
        self.assertIn("total_ordering_time_s", stats)
        self.assertEqual(stats["total_cutoffs"], stats["first_move_cutoffs"] + stats["late_move_cutoffs"])
        self.assertTrue(0.0 <= stats["first_move_cutoff_rate"] <= 1.0)
        self.assertEqual(len(res.ordering_events), stats["total_cutoffs"])
        if res.ordering_events:
            evt = res.ordering_events[0]
            self.assertIn("depth", evt)
            self.assertIn("ply", evt)
            self.assertIn("legal_moves", evt)
            self.assertIn("searched_moves", evt)
            self.assertIn("cutoff_index", evt)
            self.assertIn("is_first_move", evt)
            self.assertIn("move", evt)

    def test_ordering_telemetry_invariance(self):
        """Verify that enabling diagnostic_ordering produces identical search results (best_move, score)."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
        
        searcher_clean = JanusSearch(diagnostic_ordering=False)
        res_clean = searcher_clean.search(board, max_depth=3)
        
        searcher_diag = JanusSearch(diagnostic_ordering=True)
        res_diag = searcher_diag.search(board, max_depth=3)
        
        self.assertEqual(res_clean.best_move, res_diag.best_move)
        self.assertEqual(res_clean.score, res_diag.score)
        self.assertEqual(res_clean.nodes, res_diag.nodes)

    def test_flush_ordering_telemetry(self):
        """Verify flushing ordering events to JSONL."""
        searcher = JanusSearch(diagnostic_ordering=True)
        board = chess.Board()
        searcher.search(board, max_depth=3)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = os.path.join(tmp_dir, "ordering_telemetry.jsonl")
            count = searcher.flush_ordering_telemetry(out_file)
            self.assertGreater(count, 0)
            self.assertTrue(os.path.exists(out_file))
            self.assertEqual(len(searcher.ordering_events), 0)
            
            with open(out_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            self.assertEqual(len(lines), count)
            first_obj = json.loads(lines[0])
            self.assertIn("move", first_obj)
            self.assertIn("cutoff_index", first_obj)


if __name__ == "__main__":
    unittest.main()
