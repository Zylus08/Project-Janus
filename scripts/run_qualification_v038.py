"""Project Janus v0.38 - External Benchmark Qualification Pilot Runner.

Executes a small qualification match against Stockfish 19 across all 3 benchmark modes:
1. Primary Fischer (2 games)
2. Historical Depth 3 (2 games)
3. Calibrated Elo 1320 (2 games)

Verifies engine lifecycles, UCI handshakes, option propagation, move legality,
and process cleanup before launching the full benchmark.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from match_v038_external import BENCHMARK_MODES, run_external_benchmark


def run_qualification_v038(out_dir_path: str = "analysis/v0.38/qualification") -> dict[str, Any]:
    out_dir = ROOT / out_dir_path
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("STARTING V0.38 EXTERNAL BENCHMARK QUALIFICATION PILOT (6 GAMES)")
    print("=" * 65)

    qualification_results: dict[str, Any] = {}
    all_passed = True
    total_valid = 0
    total_failures = 0

    for mode_key in ["primary_fischer", "historical_depth3", "calibrated_elo"]:
        sub_dir = out_dir / mode_key
        sub_dir.mkdir(parents=True, exist_ok=True)
        res = run_external_benchmark(
            mode_key=mode_key,
            output_dir_path=sub_dir,
            games=2,  # 1 pair = 2 colour-reversed games
            seed=42,
        )
        summary = res["match_summary"]
        total_valid += summary["valid_games"]
        total_failures += summary["infrastructure_failures"]

        comp_valid = (
            summary["valid_games"] == 2
            and summary["infrastructure_failures"] == 0
            and summary["complete_pairs"] == 1
        )
        qualification_results[mode_key] = {
            "mode": mode_key,
            "title": BENCHMARK_MODES[mode_key]["title"],
            "valid_games": summary["valid_games"],
            "infrastructure_failures": summary["infrastructure_failures"],
            "passed": comp_valid,
        }
        if not comp_valid:
            all_passed = False

    report = {
        "milestone": "v0.38",
        "qualification_type": "external_stockfish_pilot",
        "target_games": 6,
        "valid_games": total_valid,
        "infrastructure_failures": total_failures,
        "qualification_passed": all_passed,
        "modes": qualification_results,
    }

    report_path = out_dir / "qualification_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 65)
    print(f"QUALIFICATION STATUS: {'PASSED' if all_passed else 'FAILED'}")
    print(f"Total Valid Games: {total_valid}/6")
    print(f"Infrastructure Failures: {total_failures}")
    print(f"Report written to: {report_path}")
    print("=" * 65 + "\n")

    return report


if __name__ == "__main__":
    report = run_qualification_v038()
    sys.exit(0 if report["qualification_passed"] else 1)
