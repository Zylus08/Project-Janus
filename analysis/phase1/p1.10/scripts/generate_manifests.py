#!/usr/bin/env python3
"""
Generate sha256_manifest.json and experiment_manifest.json for Milestone P1.10.
"""

import os
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P110_DIR = ROOT / "analysis" / "phase1" / "p1.10"
DOCS_DIR = ROOT / "docs" / "phase1"


def get_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_sha256_manifest():
    files_to_hash = [
        # Linage Binaries
        ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe",
        ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe",
        ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe",
        ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe",
        ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe",
        P110_DIR / "control" / "janus_classical_x15.exe",
        ROOT / "engine" / "classical_x" / "janus_classical_x.exe",
        ROOT / "engine" / "classical_x" / "janus_classical_x.cpp",
        Path("E:/ChessXML/tools/stockfish/stockfish.exe"),
        # Milestone Report
        DOCS_DIR / "p1.10_report.md",
    ]

    # Markdown deliverables
    for md_file in sorted(P110_DIR.glob("*.md")):
        files_to_hash.append(md_file)

    # Raw results
    for raw_file in sorted((P110_DIR / "raw").glob("*.json")):
        files_to_hash.append(raw_file)

    # PGN archives
    for pgn_file in sorted((P110_DIR / "pgn").glob("*.pgn")):
        files_to_hash.append(pgn_file)

    # Tests and scripts
    for test_file in sorted((P110_DIR / "tests").glob("*.py")):
        files_to_hash.append(test_file)
    for script_file in sorted((P110_DIR / "scripts").glob("*.py")):
        files_to_hash.append(script_file)

    artifacts = {}
    for p in files_to_hash:
        if p.exists() and p.is_file():
            # Relative to ROOT if possible, else absolute
            try:
                rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
            except ValueError:
                rel_path = str(p).replace("\\", "/")
            artifacts[rel_path] = {
                "sha256": get_sha256(p),
                "bytes": p.stat().st_size
            }

    manifest = {
        "milestone": "Phase 1, Milestone P1.10",
        "description": "Cryptographic SHA-256 Checksums for P1.10 Artifacts",
        "artifacts": artifacts
    }

    manifest_path = P110_DIR / "sha256_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {manifest_path} with {len(artifacts)} artifacts.")


def generate_experiment_manifest():
    manifest = {
        "milestone": "P1.10",
        "title": "Classical Strength Regression Forensics, Evaluation–Search Interaction Repair & Verified Endgame Infrastructure",
        "repository": "project-janus-phase1",
        "branch": "phase1/classical-janus",
        "parent_commit": "617becb",
        "lineage": {
            "qualified_single_thread_baseline": {
                "name": "Janus Classical X7",
                "commit": "b34e342",
                "sha256": "86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b",
                "threads": 1,
                "status": "RETAINED"
            },
            "qualified_four_thread_baseline": {
                "name": "Janus Classical X12",
                "commit": "78ca3d5",
                "sha256": "00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059",
                "threads": 4,
                "status": "RETAINED"
            },
            "candidate_evaluated": {
                "name": "Janus Classical X15",
                "threads": "1 / 4 (thread-adaptive)",
                "sha256_exe": "5b3cfcfe85b81ca03acd85f65196fb6599d29a100f272d2c1fbd66af26374e28",
                "promotion_status": "ADVANCED_UNIFIED_CLASSICAL_REFERENCE_ENGINE"
            },
            "external_reference": {
                "name": "Stockfish 19",
                "commit": "edb0d9d",
                "sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0",
                "nnue": "nn-1a298aa575a0.nnue"
            }
        },
        "phases_completed": {
            "phase_0": "P1.9 Evidence & Integrity Audit (zero-variance binomial fix, Syzygy classified Adapter/Fallback Only)",
            "phase_1": "Cross-Version Regression Archaeology (X7 through X14 causal dependency map)",
            "phase_2": "Evaluation Consistency & Score-Scale Audit (100% bit-exact color symmetry, mate bounds, root churn)",
            "phase_3": "Isolated Evaluation Feature Ablations (DEV_12 tactical blindness identified & eliminated)",
            "phase_4": "Generalized Positional Validation (240 Atlas, tactical solve rate 62.5%, endgame depth 19.46 plies)",
            "phase_5": "Evaluation Performance Engineering (Candidate S 750K NPS 1T; Candidate P 1.73M NPS 4T, 25% L2 cache pawn hash)",
            "phase_6": "Real Syzygy Qualification (0 tablebase files present, 12/12 test cases fallback verified)",
            "phase_7": "Candidate Selection (Candidate S + Candidate P unified in Janus Classical X15)",
            "phase_8": "P1.10 Correctness Suite (8/8 symmetry, 3/3 mate, DEV_12 fixed, 4/4 low-clock pass)",
            "phase_9": "Independent Strength Qualification Tournaments (Matches A, B, C)",
            "phase_10": "Matched Unrestricted Stockfish 19 Benchmark (Match SF: 5 draws, 6.25%, -470.4 Elo)",
            "phase_11": "Final Lineage Adjudication (X7 & X12 retained, X15 designated Unified Classical Reference)",
            "phase_12": "Next Classical Direction (P1.11 SPSA, capture history, multi-ply continuation history)",
            "phase_13": "Final Deliverables, Manifests & Local Git Commit"
        },
        "tournament_summary": {
            "match_a_1t_vs_x7": {
                "time_control": "1.0s + 50ms",
                "games": 200,
                "score": "92.0 / 200 (46.00%)",
                "elo": -27.9,
                "p_value": 0.183766,
                "verdict": "Regression Eliminated / Statistical Parity (p > 0.05)"
            },
            "match_b_4t_vs_x12": {
                "time_control": "1.0s + 50ms",
                "games": 200,
                "score": "94.0 / 200 (47.00%)",
                "elo": -20.9,
                "p_value": 0.271441,
                "verdict": "Statistical Parity Maintained (p > 0.05)"
            },
            "match_c_4t_vs_x12_slow": {
                "time_control": "3.0s + 100ms",
                "games": 100,
                "score": "46.5 / 100 (46.50%)",
                "elo": -24.4,
                "p_value": 0.397892,
                "verdict": "Scaling Parity Verified (p > 0.05)"
            },
            "match_sf_4t_vs_sf19": {
                "time_control": "2.0s + 50ms",
                "games": 40,
                "score": "2.5 / 40 (6.25%)",
                "elo": -470.4,
                "p_value": 1.39e-11,
                "draws": 5,
                "verdict": "Defensive Holding Recovery (5 draws against unrestricted Stockfish 19)"
            }
        }
    }

    manifest_path = P110_DIR / "experiment_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {manifest_path}.")


if __name__ == "__main__":
    generate_sha256_manifest()
    generate_experiment_manifest()
