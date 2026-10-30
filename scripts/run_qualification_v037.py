"""Project Janus v0.37 - Pilot Qualification Runner and Integrity Checker.

Validates that all three experimental arms (Arm A, Arm B, Arm C) operate reliably
under 3000 ms + 100 ms Fischer increment time control with supervised subprocesses.
Executes 6 qualification games (2 games per comparison: B vs C, A vs B, A vs C),
verifies legal moves, clock accounting, telemetry emission, and clean process teardown.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from match_v037 import COMPARISONS, ARM_CONFIGS, run_paired_match_v037


def run_qualification_v037(out_dir_path: str = "analysis/v0.37/qualification") -> dict[str, Any]:
    out_dir = ROOT / out_dir_path
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("STARTING V0.37 QUALIFICATION PILOT (6 GAMES ACROSS 3 COMPARISONS)")
    print("=" * 65)

    qualification_results: dict[str, Any] = {}
    all_passed = True
    total_valid = 0
    total_failures = 0

    for comp_key in ["b_vs_c", "a_vs_b", "a_vs_c"]:
        sub_dir = out_dir / comp_key
        sub_dir.mkdir(parents=True, exist_ok=True)
        res = run_paired_match_v037(
            comparison_key=comp_key,
            output_dir_path=sub_dir,
            games=2,  # 1 pair = 2 colour-reversed games
            seed=42,
        )
        summary = res["match_summary"]
        total_valid += summary["valid_games"]
        total_failures += summary["infrastructure_failures"]

        # Check validity for this comparison
        comp_valid = (
            summary["valid_games"] == 2
            and summary["infrastructure_failures"] == 0
            and summary["complete_pairs"] == 1
        )
        qualification_results[comp_key] = {
            "comparison": comp_key,
            "title": COMPARISONS[comp_key]["title"],
            "candidate_arm": COMPARISONS[comp_key]["cand_arm"],
            "base_arm": COMPARISONS[comp_key]["base_arm"],
            "valid_games": summary["valid_games"],
            "infrastructure_failures": summary["infrastructure_failures"],
            "passed": comp_valid,
        }
        if not comp_valid:
            all_passed = False

    report = {
        "milestone": "v0.37",
        "qualification_type": "three_arm_fischer_pilot",
        "target_games": 6,
        "valid_games": total_valid,
        "infrastructure_failures": total_failures,
        "qualification_passed": all_passed,
        "comparisons": qualification_results,
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
    report = run_qualification_v037()
    sys.exit(0 if report["qualification_passed"] else 1)
