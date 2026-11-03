"""Unit tests for v0.31 benchmark integrity auditor and statistical methodology."""
import copy
import math
import unittest

from scripts.audit_benchmark_integrity_v031 import (
    BenchmarkDataAuditor,
    BenchmarkValidationError,
    calculate_median_and_iqr,
    calculate_speedup_pct,
)


class TestBenchmarkIntegrityAuditor(unittest.TestCase):
    """Test suite for benchmark integrity validation and arithmetic correctness."""

    def test_speedup_formula_direction(self):
        """Speedup = 100 * (1 - T_cand / T_base). Positive is faster, negative is slower."""
        # Baseline faster than candidate -> negative speedup (slowdown)
        # e.g., v0.30 white_up_rook D4 marginal medians: base=0.2491, cand=0.3254
        sp_slowdown = calculate_speedup_pct(0.2491, 0.3254)
        self.assertAlmostEqual(sp_slowdown, -30.63, delta=0.1)
        self.assertLess(sp_slowdown, 0.0)

        # Candidate faster than baseline -> positive speedup
        sp_speedup = calculate_speedup_pct(1.0, 0.8)
        self.assertAlmostEqual(sp_speedup, 20.0, delta=0.01)
        self.assertGreater(sp_speedup, 0.0)

        # Baseline zero or negative -> safe return 0.0
        self.assertEqual(calculate_speedup_pct(0.0, 0.5), 0.0)
        self.assertEqual(calculate_speedup_pct(-1.0, 0.5), 0.0)

    def test_ratio_of_medians_vs_median_of_paired_speedups(self):
        """Demonstrate that marginal medians and paired speedups can diverge."""
        # Synthetic 5-run paired experiment matching the exact white_up_rook D4 phenomenon
        base_runs = [0.108, 0.361, 0.367, 0.163, 0.249]
        cand_runs = [0.079, 0.325, 0.371, 0.153, 0.337]

        b_med, _ = calculate_median_and_iqr(base_runs)
        c_med, _ = calculate_median_and_iqr(cand_runs)
        self.assertAlmostEqual(b_med, 0.249, places=3)
        self.assertAlmostEqual(c_med, 0.325, places=3)

        # Ratio of medians is NEGATIVE (-30.5%)
        ratio_of_med = calculate_speedup_pct(b_med, c_med)
        self.assertLess(ratio_of_med, -30.0)

        # Paired speedups: 3 out of 5 runs were positive
        paired_sps = [calculate_speedup_pct(b, c) for b, c in zip(base_runs, cand_runs)]
        paired_med, _ = calculate_median_and_iqr(paired_sps)
        # Median of paired speedups is POSITIVE (+6.1%)
        self.assertGreater(paired_med, 5.0)

        # Demonstrates why reporting paired_med next to b_med and c_med without clear labeling is confusing
        self.assertNotEqual(math.copysign(1, ratio_of_med), math.copysign(1, paired_med))

    def _get_valid_payload(self) -> dict:
        return {
            "metadata": {
                "timestamp_utc": "2026-10-20T12:00:00Z",
                "reps": 1,
                "depths": [4],
            },
            "runs": [
                {
                    "rep": 1,
                    "depth": 4,
                    "position_id": "startpos",
                    "arm": "baseline",
                    "elapsed_s": 0.20,
                    "nodes": 2552,
                    "nps": 12760,
                    "best_move": "g1f3",
                    "score": 0,
                    "pv": ["g1f3", "g8f6"],
                    "pv_legal": True,
                },
                {
                    "rep": 1,
                    "depth": 4,
                    "position_id": "startpos",
                    "arm": "candidate",
                    "elapsed_s": 0.16,
                    "nodes": 2552,
                    "nps": 15950,
                    "best_move": "g1f3",
                    "score": 0,
                    "pv": ["g1f3", "g8f6"],
                    "pv_legal": True,
                },
            ],
        }

    def test_schema_validation_success(self):
        """Valid payload passes schema validation cleanly."""
        payload = self._get_valid_payload()
        import tempfile, json
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump(payload, f)
            temp_path = f.name

        auditor = BenchmarkDataAuditor(temp_path)
        summary = auditor.compute_statistical_summary()
        self.assertEqual(summary["invariants"]["node_parity_rate"], 1.0)
        self.assertEqual(summary["invariants"]["best_move_parity_rate"], 1.0)

    def test_schema_validation_rejects_missing_keys(self):
        """Auditor rejects payloads missing required metadata or run keys."""
        import tempfile, json

        # Missing metadata
        bad1 = {"runs": []}
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump(bad1, f)
            p1 = f.name
        with self.assertRaises(BenchmarkValidationError):
            BenchmarkDataAuditor(p1)

        # Missing run key
        bad2 = self._get_valid_payload()
        del bad2["runs"][0]["pv_legal"]
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump(bad2, f)
            p2 = f.name
        with self.assertRaises(BenchmarkValidationError):
            BenchmarkDataAuditor(p2)

        # Negative elapsed_s
        bad3 = self._get_valid_payload()
        bad3["runs"][0]["elapsed_s"] = -0.5
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump(bad3, f)
            p3 = f.name
        with self.assertRaises(BenchmarkValidationError):
            BenchmarkDataAuditor(p3)

    def test_schema_validation_rejects_unpaired_runs(self):
        """Auditor raises error when an arm is missing for a pair."""
        import tempfile, json
        payload = self._get_valid_payload()
        # Remove candidate run
        payload["runs"] = [payload["runs"][0]]
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump(payload, f)
            p = f.name
        auditor = BenchmarkDataAuditor(p)
        with self.assertRaises(BenchmarkValidationError):
            auditor.pair_runs()

    def test_invariant_mismatch_detection(self):
        """Auditor accurately identifies node and move mismatches."""
        import tempfile, json
        payload = self._get_valid_payload()
        # Modify candidate nodes and best move
        payload["runs"][1]["nodes"] = 2550
        payload["runs"][1]["best_move"] = "e2e4"
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump(payload, f)
            p = f.name

        auditor = BenchmarkDataAuditor(p)
        invariants = auditor.audit_invariants()
        self.assertEqual(invariants["node_parity_rate"], 0.0)
        self.assertEqual(invariants["best_move_parity_rate"], 0.0)
        self.assertEqual(invariants["mismatch_count"], 1)


if __name__ == "__main__":
    unittest.main()
