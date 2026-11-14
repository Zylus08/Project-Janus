#!/usr/bin/env python3
"""
generate_manifests.py
Generates sha256_manifest.json and experiment_manifest.json for Milestone P1.18.
"""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P118_DIR = ROOT / "analysis" / "phase1" / "p1.18"
DOCS_REPORT = ROOT / "docs" / "phase1" / "p1.18_report.md"

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    print("Generating SHA-256 Manifest for P1.18...")
    file_hashes = {}

    # Scan P1.18 directory
    for p in sorted(P118_DIR.rglob("*")):
        if p.is_file() and p.name not in ["sha256_manifest.json", "experiment_manifest.json"]:
            rel_path = p.relative_to(ROOT).as_posix()
            file_hashes[rel_path] = sha256_file(p)

    # Master report
    if DOCS_REPORT.exists():
        rel_path = DOCS_REPORT.relative_to(ROOT).as_posix()
        file_hashes[rel_path] = sha256_file(DOCS_REPORT)

    sha256_manifest_path = P118_DIR / "sha256_manifest.json"
    with open(sha256_manifest_path, "w") as f:
        json.dump(file_hashes, f, indent=2)
    print(f"Recorded {len(file_hashes)} file hashes in {sha256_manifest_path}")

    # Build experiment manifest
    print("Generating Experiment Manifest for P1.18...")
    tourn_raw_path = P118_DIR / "raw" / "p118_tournaments_raw.json"
    tourn_summary = {}
    if tourn_raw_path.exists():
        with open(tourn_raw_path, "r") as f:
            tdata = json.load(f)
            for mk, mv in tdata.items():
                tourn_summary[mk] = {
                    "match_name": mv["match_name"],
                    "cand": mv["cand"],
                    "ref": mv["ref"],
                    "total_games": mv["total_games"],
                    "score": mv["score"],
                    "win_rate": mv["win_rate"],
                    "wins": mv["wins"],
                    "draws": mv["draws"],
                    "losses": mv["losses"],
                    "paired_ci": [mv["ci_low"], mv["ci_high"]],
                    "p_value": mv["p_value"],
                    "elo": mv["elo"]
                }

    exp_manifest = {
        "milestone": "P1.18",
        "title": "Classical Pawn-Structure Intelligence, King-Safety Fidelity & Verified Competitive Strength",
        "governing_charter": "Strictly Non-ML Classical Computer Chess Architecture",
        "branch": "phase1/classical-janus",
        "parent_commit": "e33f292",
        "frozen_baselines": {
            "x7_single_thread": {
                "commit": "b34e342",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe",
                "sha256": "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B"
            },
            "x12_four_thread": {
                "commit": "78ca3d5",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe",
                "sha256": "00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059"
            },
            "x22_research_reference": {
                "commit": "e33f292",
                "path": "analysis/phase1/p1.17/control/janus_classical_x22.exe",
                "sha256": "35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C"
            }
        },
        "candidate": {
            "name": "Janus Classical Candidate X23",
            "tracks": {
                "track_s": "X23-S (Single-Thread 1T, E5 Classical Evaluation)",
                "track_p": "X23-P (Four-Thread 4T SMP, E10 Enhanced Evaluation)"
            },
            "features": [
                "Track A: Classical Backward Pawn Detection (-10 mg / -15 eg) with 64K Pawn Hash Caching",
                "Track B: Open and Semi-Open File King Exposure Penalty (-15 to -40 mg)",
                "True Outpost Semantics with Enemy Pawn Bitboard Ray Span Immunity",
                "Corrected Quiescence Search (Q1) with Legal In-Check Evasions",
                "Staged Capture Ordering & C1 Near-Even Capture Promotion"
            ],
            "binaries": {
                "exe": {
                    "path": "analysis/phase1/p1.18/control/janus_classical_x23.exe",
                    "sha256": file_hashes.get("analysis/phase1/p1.18/control/janus_classical_x23.exe", "")
                },
                "dll": {
                    "path": "analysis/phase1/p1.18/control/janus_classical_x23.dll",
                    "sha256": file_hashes.get("analysis/phase1/p1.18/control/janus_classical_x23.dll", "")
                },
                "cpp": {
                    "path": "analysis/phase1/p1.18/control/janus_classical_x23.cpp",
                    "sha256": file_hashes.get("analysis/phase1/p1.18/control/janus_classical_x23.cpp", "")
                }
            }
        },
        "correctness_qualification": {
            "total_gates": 7,
            "passed_gates": 7,
            "pass_rate": 1.0,
            "status": "PASSED (100% Green)"
        },
        "development_ablations": {
            "match_dev1_joint_x23": {"win_rate": 35.0, "elo": -107.5},
            "match_dev2_track_a_alone": {"win_rate": 52.5, "elo": +17.4, "finding": "Elo-positive (+17.4 Elo)"},
            "match_dev3_track_b_alone": {"win_rate": 37.5, "elo": -88.7, "finding": "Elo-negative (-88.7 Elo) due to defensive timidity"}
        },
        "tournaments_summary": tourn_summary,
        "adjudication": {
            "decision": "CATEGORY B — PRESERVED RESEARCH REFERENCE (NOT PROMOTED)",
            "reason": "Candidate X23 did not satisfy paired CI lower bound > 50.0% against Qualified Baselines X7 (44.0%, CI_low=37.1%) and X12 (48.0%, CI_low=40.7%). Track B caused significant Elo drag that suppressed the gains of Track A.",
            "next_direction": "Milestone P1.19 Candidate X24 will isolate Track A alone (backward pawns + pawn hash + true outposts), removing Track B entirely to capture the +17.4 Elo gain."
        }
    }

    exp_manifest_path = P118_DIR / "experiment_manifest.json"
    with open(exp_manifest_path, "w") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Saved Experiment Manifest to {exp_manifest_path}")

if __name__ == "__main__":
    main()
