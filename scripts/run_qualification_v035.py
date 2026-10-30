"""Phase 7 Smoke Match Qualification Script for Project Janus v0.35.

Executes short qualification matches across all three modes:
1. Fixed Movetime (100ms)
2. Clock-Only Sudden Death (3000ms)
3. Fischer Increment (3000ms + 100ms)

Validates:
- Move legality for every played move
- Clock decrements and increment applications
- Process cleanup and zero orphaned processes
- Integrity of raw attempt logs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from match_v035 import run_clean_match  # noqa: E402


def run_qualification() -> dict[str, Any]:
    qual_dir = ROOT / "analysis" / "v0.35" / "qualification"
    qual_dir.mkdir(parents=True, exist_ok=True)

    qualification_summary = {}

    # 1. Fixed Movetime Qualification (2 games = 1 pair, 100ms)
    print("\n" + "=" * 60)
    print("RUNNING QUALIFICATION MATCH 1/3: Fixed Movetime (100ms)")
    print("=" * 60)
    res_fixed = run_clean_match(
        games=2,
        time_mode="fixed_movetime",
        base_time_ms=100,
        inc_time_ms=0,
        max_plies=40,
        seed=101,
        output_dir_path=qual_dir / "fixed_movetime",
        match_name="qual_fixed_movetime",
    )
    qualification_summary["fixed_movetime"] = {
        "valid_games": len(res_fixed["valid_games"]),
        "attempts": len(res_fixed["attempts"]),
        "target_met": res_fixed["match_summary"]["target_met"],
        "infra_failures": res_fixed["match_summary"]["infrastructure_failures"],
    }

    # 2. Clock-Only Qualification (2 games = 1 pair, 3000ms sudden death)
    print("\n" + "=" * 60)
    print("RUNNING QUALIFICATION MATCH 2/3: Clock-Only (3000ms)")
    print("=" * 60)
    res_clock = run_clean_match(
        games=2,
        time_mode="clock_only",
        base_time_ms=3000,
        inc_time_ms=0,
        max_plies=40,
        seed=202,
        output_dir_path=qual_dir / "clock_only",
        match_name="qual_clock_only",
    )
    qualification_summary["clock_only"] = {
        "valid_games": len(res_clock["valid_games"]),
        "attempts": len(res_clock["attempts"]),
        "target_met": res_clock["match_summary"]["target_met"],
        "infra_failures": res_clock["match_summary"]["infrastructure_failures"],
    }

    # 3. Fischer Increment Qualification (2 games = 1 pair, 3000ms + 100ms)
    print("\n" + "=" * 60)
    print("RUNNING QUALIFICATION MATCH 3/3: Fischer Increment (3000ms + 100ms)")
    print("=" * 60)
    res_fischer = run_clean_match(
        games=2,
        time_mode="fischer_increment",
        base_time_ms=3000,
        inc_time_ms=100,
        max_plies=40,
        seed=303,
        output_dir_path=qual_dir / "fischer_increment",
        match_name="qual_fischer_increment",
    )
    qualification_summary["fischer_increment"] = {
        "valid_games": len(res_fischer["valid_games"]),
        "attempts": len(res_fischer["attempts"]),
        "target_met": res_fischer["match_summary"]["target_met"],
        "infra_failures": res_fischer["match_summary"]["infrastructure_failures"],
    }

    # Verification checks
    all_passed = (
        qualification_summary["fixed_movetime"]["target_met"]
        and qualification_summary["clock_only"]["target_met"]
        and qualification_summary["fischer_increment"]["target_met"]
        and qualification_summary["fixed_movetime"]["infra_failures"] == 0
        and qualification_summary["clock_only"]["infra_failures"] == 0
        and qualification_summary["fischer_increment"]["infra_failures"] == 0
    )

    report = {
        "qualification_passed": all_passed,
        "modes_tested": ["fixed_movetime", "clock_only", "fischer_increment"],
        "summary": qualification_summary,
    }

    report_path = qual_dir / "qualification_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nQualification report saved to {report_path}")
    print(f"Overall qualification passed: {all_passed}")

    return report


if __name__ == "__main__":
    res = run_qualification()
    if not res["qualification_passed"]:
        sys.exit(1)
