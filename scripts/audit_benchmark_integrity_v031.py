"""Project Janus v0.31 - Benchmark Integrity Audit and Analysis Tool.

Provides schema validation, invariant verification, and rigorous statistical analysis
for benchmark runs across Project Janus milestones (v0.28, v0.29, v0.30, v0.31).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from typing import Any


def calculate_median_and_iqr(vals: list[float]) -> tuple[float, float]:
    """Calculate median and interquartile range (Q3 - Q1)."""
    if not vals:
        return 0.0, 0.0
    sorted_vals = sorted(vals)
    med = float(statistics.median(sorted_vals))
    if len(sorted_vals) >= 4:
        q = statistics.quantiles(sorted_vals, n=4)
        iqr = float(q[2] - q[0])
    else:
        iqr = 0.0
    return med, iqr


def calculate_speedup_pct(base_time: float, cand_time: float) -> float:
    """Calculate speedup percentage using standard formula: 100 * (1 - T_cand / T_base).

    Positive values indicate candidate is faster.
    Negative values indicate candidate is slower.
    """
    if base_time <= 0:
        return 0.0
    return float((base_time - cand_time) / base_time * 100.0)


class BenchmarkValidationError(ValueError):
    """Raised when benchmark data fails structural or schema validation."""
    pass


class BenchmarkDataAuditor:
    """Audits benchmark integrity, invariants, and statistical metrics."""

    REQUIRED_METADATA_KEYS = ["timestamp_utc", "reps", "depths"]
    REQUIRED_RUN_KEYS = [
        "rep",
        "depth",
        "position_id",
        "arm",
        "elapsed_s",
        "nodes",
        "nps",
        "best_move",
        "score",
        "pv",
        "pv_legal",
    ]

    def __init__(self, benchmark_path: str):
        self.benchmark_path = benchmark_path
        with open(benchmark_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.validate_schema()

    def validate_schema(self) -> None:
        """Validate structural schema and basic data integrity."""
        if not isinstance(self.data, dict):
            raise BenchmarkValidationError("Top-level JSON structure must be an object")

        if "metadata" not in self.data or "runs" not in self.data:
            raise BenchmarkValidationError("Benchmark file must contain 'metadata' and 'runs'")

        for k in self.REQUIRED_METADATA_KEYS:
            if k not in self.data["metadata"]:
                raise BenchmarkValidationError(f"Metadata missing required key: {k}")

        runs = self.data["runs"]
        if not isinstance(runs, list) or len(runs) == 0:
            raise BenchmarkValidationError("'runs' must be a non-empty list")

        for idx, r in enumerate(runs):
            for k in self.REQUIRED_RUN_KEYS:
                if k not in r:
                    raise BenchmarkValidationError(f"Run {idx} missing required key: {k}")
            if r["arm"] not in ("baseline", "candidate"):
                raise BenchmarkValidationError(f"Run {idx} has invalid arm: {r['arm']}")
            if r["elapsed_s"] < 0:
                raise BenchmarkValidationError(f"Run {idx} has negative elapsed_s: {r['elapsed_s']}")
            if r["nodes"] < 0:
                raise BenchmarkValidationError(f"Run {idx} has negative nodes: {r['nodes']}")

    def pair_runs(self) -> dict[tuple[int, int, str], dict[str, dict[str, Any]]]:
        """Pair baseline and candidate runs by (rep, depth, position_id)."""
        pairs: dict[tuple[int, int, str], dict[str, dict[str, Any]]] = {}
        for r in self.data["runs"]:
            key = (r["rep"], r["depth"], r["position_id"])
            if key not in pairs:
                pairs[key] = {}
            pairs[key][r["arm"]] = r

        for key, p in pairs.items():
            if "baseline" not in p:
                raise BenchmarkValidationError(f"Missing baseline run for pair {key}")
            if "candidate" not in p:
                raise BenchmarkValidationError(f"Missing candidate run for pair {key}")

        return pairs

    def audit_invariants(self) -> dict[str, Any]:
        """Verify search correctness, node parity, score parity, move parity, and PV legality."""
        pairs = self.pair_runs()
        total_pairs = len(pairs)
        node_matches = 0
        move_matches = 0
        score_matches = 0
        pv_legal_count = 0
        mismatches: list[dict[str, Any]] = []

        for key, p in pairs.items():
            base = p["baseline"]
            cand = p["candidate"]
            rep, depth, pid = key

            n_match = base["nodes"] == cand["nodes"]
            m_match = base["best_move"] == cand["best_move"]
            s_match = base["score"] == cand["score"]
            pv_ok = bool(base.get("pv_legal", False)) and bool(cand.get("pv_legal", False))

            if n_match:
                node_matches += 1
            if m_match:
                move_matches += 1
            if s_match:
                score_matches += 1
            if pv_ok:
                pv_legal_count += 1

            if not (n_match and m_match and s_match and pv_ok):
                mismatches.append({
                    "rep": rep,
                    "depth": depth,
                    "position_id": pid,
                    "node_match": n_match,
                    "move_match": m_match,
                    "score_match": s_match,
                    "pv_legal": pv_ok,
                    "base_nodes": base["nodes"],
                    "cand_nodes": cand["nodes"],
                    "base_move": base["best_move"],
                    "cand_move": cand["best_move"],
                    "base_score": base["score"],
                    "cand_score": cand["score"],
                })

        return {
            "total_pairs": total_pairs,
            "node_parity_rate": node_matches / total_pairs if total_pairs else 0.0,
            "best_move_parity_rate": move_matches / total_pairs if total_pairs else 0.0,
            "score_parity_rate": score_matches / total_pairs if total_pairs else 0.0,
            "pv_legality_rate": pv_legal_count / total_pairs if total_pairs else 0.0,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }

    def compute_statistical_summary(self) -> dict[str, Any]:
        """Compute per-position, suite-level, and pooled statistics with explicit definitions."""
        pairs = self.pair_runs()
        invariants = self.audit_invariants()

        # Group by position and depth
        by_pos_depth: dict[str, dict[str, Any]] = {}
        depths = sorted(list(set(k[1] for k in pairs.keys())))
        reps = sorted(list(set(k[0] for k in pairs.keys())))
        positions = sorted(list(set(k[2] for k in pairs.keys())))

        for key, p in pairs.items():
            rep, depth, pid = key
            base = p["baseline"]
            cand = p["candidate"]

            pos_key = f"D{depth}_{pid}"
            if pos_key not in by_pos_depth:
                by_pos_depth[pos_key] = {
                    "depth": depth,
                    "position_id": pid,
                    "nodes": base["nodes"],
                    "base_times": [],
                    "cand_times": [],
                    "paired_speedups": [],
                    "paired_diffs_s": [],
                    "base_nps": [],
                    "cand_nps": [],
                }

            b_t = base["elapsed_s"]
            c_t = cand["elapsed_s"]
            sp = calculate_speedup_pct(b_t, c_t)
            diff = b_t - c_t

            by_pos_depth[pos_key]["base_times"].append(b_t)
            by_pos_depth[pos_key]["cand_times"].append(c_t)
            by_pos_depth[pos_key]["paired_speedups"].append(sp)
            by_pos_depth[pos_key]["paired_diffs_s"].append(diff)
            by_pos_depth[pos_key]["base_nps"].append(base["nps"])
            by_pos_depth[pos_key]["cand_nps"].append(cand["nps"])

        # Per-position summaries
        position_summaries = {}
        for pos_key, v in by_pos_depth.items():
            b_med, b_iqr = calculate_median_and_iqr(v["base_times"])
            c_med, c_iqr = calculate_median_and_iqr(v["cand_times"])
            ratio_of_medians_sp = calculate_speedup_pct(b_med, c_med)

            sp_med, sp_iqr = calculate_median_and_iqr(v["paired_speedups"])
            diff_med, diff_iqr = calculate_median_and_iqr(v["paired_diffs_s"])
            bnps_med, _ = calculate_median_and_iqr(v["base_nps"])
            cnps_med, _ = calculate_median_and_iqr(v["cand_nps"])

            position_summaries[pos_key] = {
                "depth": v["depth"],
                "position_id": v["position_id"],
                "nodes": v["nodes"],
                "baseline_time_median_s": b_med,
                "baseline_time_iqr_s": b_iqr,
                "candidate_time_median_s": c_med,
                "candidate_time_iqr_s": c_iqr,
                "speedup_ratio_of_medians_pct": ratio_of_medians_sp,
                "speedup_paired_median_pct": sp_med,
                "speedup_paired_iqr_pct": sp_iqr,
                "time_saved_median_s": diff_med,
                "time_saved_iqr_s": diff_iqr,
                "baseline_nps_median": bnps_med,
                "candidate_nps_median": cnps_med,
            }

        # Suite Total Summaries (Sum of positions per rep, matching v0.28/v0.29 convention)
        suite_summaries = {}
        for depth in depths:
            base_suite_times = []
            cand_suite_times = []
            suite_speedups = []
            suite_diffs = []
            suite_nodes = 0

            for rep in reps:
                b_sum = sum(pairs[(rep, depth, p)]["baseline"]["elapsed_s"] for p in positions)
                c_sum = sum(pairs[(rep, depth, p)]["candidate"]["elapsed_s"] for p in positions)
                sp = calculate_speedup_pct(b_sum, c_sum)
                diff = b_sum - c_sum

                base_suite_times.append(b_sum)
                cand_suite_times.append(c_sum)
                suite_speedups.append(sp)
                suite_diffs.append(diff)
                suite_nodes = sum(pairs[(rep, depth, p)]["baseline"]["nodes"] for p in positions)

            b_med, b_iqr = calculate_median_and_iqr(base_suite_times)
            c_med, c_iqr = calculate_median_and_iqr(cand_suite_times)
            ratio_of_med_sp = calculate_speedup_pct(b_med, c_med)
            paired_sp_med, paired_sp_iqr = calculate_median_and_iqr(suite_speedups)
            diff_med, diff_iqr = calculate_median_and_iqr(suite_diffs)

            suite_summaries[f"depth_{depth}"] = {
                "depth": depth,
                "total_suite_nodes": suite_nodes,
                "baseline_suite_time_median_s": b_med,
                "baseline_suite_time_iqr_s": b_iqr,
                "candidate_suite_time_median_s": c_med,
                "candidate_suite_time_iqr_s": c_iqr,
                "suite_speedup_ratio_of_medians_pct": ratio_of_med_sp,
                "suite_speedup_paired_median_pct": paired_sp_med,
                "suite_speedup_paired_iqr_pct": paired_sp_iqr,
                "suite_time_saved_median_s": diff_med,
                "baseline_suite_nps": suite_nodes / b_med if b_med > 0 else 0.0,
                "candidate_suite_nps": suite_nodes / c_med if c_med > 0 else 0.0,
            }

        # Unweighted Pooled Summary (to diagnose the pooling anomaly)
        pooled_summaries = {}
        for depth in depths:
            b_pooled = [pairs[(r, depth, p)]["baseline"]["elapsed_s"] for r in reps for p in positions]
            c_pooled = [pairs[(r, depth, p)]["candidate"]["elapsed_s"] for r in reps for p in positions]
            sp_pooled = [
                calculate_speedup_pct(
                    pairs[(r, depth, p)]["baseline"]["elapsed_s"],
                    pairs[(r, depth, p)]["candidate"]["elapsed_s"],
                )
                for r in reps for p in positions
            ]

            b_med, b_iqr = calculate_median_and_iqr(b_pooled)
            c_med, c_iqr = calculate_median_and_iqr(c_pooled)
            sp_med, sp_iqr = calculate_median_and_iqr(sp_pooled)

            pooled_summaries[f"depth_{depth}"] = {
                "sample_count": len(b_pooled),
                "pooled_baseline_median_s": b_med,
                "pooled_candidate_median_s": c_med,
                "pooled_speedup_median_pct": sp_med,
                "pooled_speedup_iqr_pct": sp_iqr,
            }

        return {
            "invariants": invariants,
            "positions": position_summaries,
            "suite_totals": suite_summaries,
            "unweighted_pooled": pooled_summaries,
        }


def format_audit_table(summary: dict[str, Any]) -> str:
    """Format audit results as a clear text/markdown table."""
    lines = []
    lines.append("=" * 110)
    lines.append(
        f"{'Position':<18} | {'Depth':<5} | {'Nodes':>6} | "
        f"{'Base Med (s)':>12} | {'Cand Med (s)':>12} | "
        f"{'RatioOfMed (%)':>14} | {'PairedMed (%)':>14} | {'Time Saved':>10}"
    )
    lines.append("-" * 110)

    for k, v in summary["positions"].items():
        lines.append(
            f"{v['position_id']:<18} | D{v['depth']:<4} | {v['nodes']:>6} | "
            f"{v['baseline_time_median_s']:>12.4f} | {v['candidate_time_median_s']:>12.4f} | "
            f"{v['speedup_ratio_of_medians_pct']:>+13.1f}% | "
            f"{v['speedup_paired_median_pct']:>+13.1f}% | "
            f"{v['time_saved_median_s']:>+9.4f}s"
        )

    lines.append("=" * 110)
    lines.append("\nSUITE TOTALS (Workload-Weighted Sum Across All Positions Per Repetition):")
    lines.append("-" * 110)
    lines.append(
        f"{'Depth':<8} | {'Nodes':>6} | "
        f"{'Base Suite Med':>15} | {'Cand Suite Med':>15} | "
        f"{'Suite RatioMed%':>15} | {'Suite PairedMed%':>16} | {'Time Saved':>10}"
    )
    lines.append("-" * 110)
    for k, v in summary["suite_totals"].items():
        lines.append(
            f"Depth {v['depth']:<2} | {v['total_suite_nodes']:>6} | "
            f"{v['baseline_suite_time_median_s']:>14.3f}s | {v['candidate_suite_time_median_s']:>14.3f}s | "
            f"{v['suite_speedup_ratio_of_medians_pct']:>+14.1f}% | "
            f"{v['suite_speedup_paired_median_pct']:>+15.1f}% | "
            f"{v['suite_time_saved_median_s']:>+9.3f}s"
        )
    lines.append("=" * 110)

    inv = summary["invariants"]
    lines.append(
        f"\nINVARIANTS: Node Parity = {inv['node_parity_rate']*100:.1f}%, "
        f"Move Parity = {inv['best_move_parity_rate']*100:.1f}%, "
        f"Score Parity = {inv['score_parity_rate']*100:.1f}%, "
        f"PV Legality = {inv['pv_legality_rate']*100:.1f}%"
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit Project Janus benchmark integrity")
    parser.add_argument("benchmark_path", help="Path to benchmark JSON file")
    parser.add_argument("--output", help="Optional path to save summary JSON")
    args = parser.parse_args()

    auditor = BenchmarkDataAuditor(args.benchmark_path)
    summary = auditor.compute_statistical_summary()
    print(format_audit_table(summary))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSaved audit summary to {args.output}")


if __name__ == "__main__":
    main()
