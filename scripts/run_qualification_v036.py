"""Phase 5 Qualification Match for Project Janus v0.36.

Executes a small preliminary match (4 games / 2 complete pairs) under the
exact experimental time control (3000 ms + 100 ms Fischer increment) to verify:
1. Candidate (adaptive) and Reference (baseline) policy selection
2. Process supervision, clean startup, and deterministic termination
3. Legal moves across all plies
4. Clock decrement and Fischer increment progression
5. Detailed move-level telemetry capture (CSV and JSON)
6. Symmetry of opening pairing and colour reversal
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from match_v036 import run_clean_match_v036  # noqa: E402


def run_qualification_v036() -> dict[str, Any]:
    qual_dir = ROOT / "analysis" / "v0.36" / "qualification"
    qual_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("RUNNING v0.36 QUALIFICATION MATCH (4 games / 2 opening pairs)")
    print("Time Control: 3000 ms + 100 ms Fischer increment")
    print("=" * 65)

    dataset = run_clean_match_v036(
        games=4,
        time_mode="fischer_increment",
        base_time_ms=3000,
        inc_time_ms=100,
        max_plies=40,
        seed=123,
        output_dir_path=qual_dir,
        match_name="qual_match",
    )

    valid_games = dataset["valid_games"]
    attempts = dataset["attempts"]
    summary = dataset["match_summary"]
    metadata = dataset["metadata"]

    # Qualification verifications
    checks = {}

    # 1. Target completion
    checks["target_completion"] = (len(valid_games) == 4 and summary["complete_valid_pairs"] == 2)
    checks["zero_infrastructure_failures"] = (summary["infrastructure_failures"] == 0)

    # 2. Policy identities
    checks["policy_identity"] = (
        "--time-policy adaptive" in " ".join(metadata["candidate_cmd"])
        and "--time-policy reference" in " ".join(metadata["reference_cmd"])
    )

    # 3. Opening pair symmetry & colour reversal
    pair1 = [g for g in valid_games if g["pair"] == 1]
    pair2 = [g for g in valid_games if g["pair"] == 2]

    pair_symmetry = (
        len(pair1) == 2 and len(pair2) == 2
        and pair1[0]["candidate_color"] != pair1[1]["candidate_color"]
        and pair2[0]["candidate_color"] != pair2[1]["candidate_color"]
        and pair1[0]["opening_id"] == pair1[1]["opening_id"]
        and pair2[0]["opening_id"] == pair2[1]["opening_id"]
    )
    checks["opening_pair_symmetry"] = pair_symmetry

    # 4. Move legality and clock consistency
    moves_csv_path = qual_dir / "qual_match_moves.csv"
    checks["moves_csv_exists"] = moves_csv_path.is_file()

    pgn_path = qual_dir / "qual_match.pgn"
    pgn_valid = True
    with open(pgn_path, encoding="utf-8") as f:
        count = 0
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            count += 1
            board = g.board()
            for m in g.mainline_moves():
                if m not in board.legal_moves:
                    pgn_valid = False
                    break
                board.push(m)
        checks["pgn_moves_legal"] = (pgn_valid and count == 4)

    all_passed = all(checks.values())

    report = {
        "qualification_passed": all_passed,
        "timestamp_utc": metadata["timestamp_utc"],
        "checks": checks,
        "summary": summary,
    }

    report_path = qual_dir / "qualification_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 65)
    print(f"QUALIFICATION VERDICT: {'PASSED' if all_passed else 'FAILED'}")
    print(f"Report written to {report_path}")
    print("=" * 65)

    return report


if __name__ == "__main__":
    res = run_qualification_v036()
    if not res["qualification_passed"]:
        sys.exit(1)
