#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 13: Manifest Generator
Generates sha256_manifest.json and experiment_manifest.json for Milestone P1.9.
"""

import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P19_DIR = ROOT / "analysis" / "phase1" / "p1.9"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== PROJECT JANUS P1.9: GENERATING MANIFESTS ===")

    # 1. SHA-256 Manifest
    files_to_hash = [
        # Frozen Baselines
        ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe",
        ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe",
        ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe",
        ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe",
        Path("E:/ChessXML/tools/stockfish/stockfish.exe"),
        # Candidate X14
        P19_DIR / "control" / "janus_classical_x14.exe",
        P19_DIR / "control" / "janus_classical_x14.dll",
        P19_DIR / "control" / "janus_classical_x14.cpp",
        ROOT / "engine" / "classical_x" / "janus_classical_x.cpp",
        # Key Reports
        P19_DIR / "P18_EVIDENCE_AND_PROMOTION_AUDIT.md",
        P19_DIR / "GENERALIZED_CHESS_FAILURE_ATLAS.md",
        P19_DIR / "EVALUATION_CORRECTNESS_AND_GENERALIZATION.md",
        P19_DIR / "SYZYGY_IMPLEMENTATION_AND_VALIDATION.md",
        P19_DIR / "ENDGAME_CONVERSION_STUDY.md",
        P19_DIR / "EVALUATION_AND_CACHE_PERFORMANCE.md",
        P19_DIR / "P19_SEARCH_EVALUATION_FACTORIAL.md",
        P19_DIR / "TIME_CONTROL_GENERALIZATION.md",
        P19_DIR / "X14_CANDIDATE_SELECTION.md",
        P19_DIR / "X14_INDEPENDENT_STRENGTH.md",
        P19_DIR / "MATCHED_STOCKFISH19_PROGRESS.md",
        P19_DIR / "FINAL_RESEARCH_DECISION.md",
        P19_DIR / "NEXT_CLASSICAL_PRIORITY.md",
        ROOT / "docs" / "phase1" / "p1.9_report.md",
        # Raw Data
        P19_DIR / "raw" / "p18_reconciliation_summary.json",
        P19_DIR / "raw" / "generalized_failure_atlas_raw.json",
        P19_DIR / "raw" / "eval_ablation_matrix_raw.json",
        P19_DIR / "raw" / "syzygy_validation_raw.json",
        P19_DIR / "raw" / "endgame_conversion_raw.json",
        P19_DIR / "raw" / "cache_performance_raw.json",
        P19_DIR / "raw" / "search_eval_factorial_raw.json",
        P19_DIR / "raw" / "time_control_generalization_raw.json",
        P19_DIR / "raw" / "x14_internal_strength_raw.json",
        P19_DIR / "raw" / "x14_vs_sf19_raw.json",
        # PGNs
        P19_DIR / "pgn" / "x14_1t_vs_x7_1t.pgn",
        P19_DIR / "pgn" / "x14_4t_vs_x12_4t.pgn",
        P19_DIR / "pgn" / "x14_4t_vs_x12_4t_slow.pgn",
        P19_DIR / "pgn" / "x14_4t_vs_sf19_4t.pgn",
        # Corpus
        P19_DIR / "corpus" / "generalized_failure_atlas_240.json"
    ]

    sha_manifest = {
        "milestone": "Phase 1, Milestone P1.9",
        "description": "Cryptographic SHA-256 Checksums for P1.9 Artifacts",
        "artifacts": {}
    }

    for p in files_to_hash:
        if p.exists():
            rel_path = p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix()
            sha_manifest["artifacts"][rel_path] = {
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size
            }
            print(f"Hashed: {rel_path} ({p.stat().st_size:,} bytes)")
        else:
            print(f"WARNING: File not found: {p}")

    sha_path = P19_DIR / "sha256_manifest.json"
    with open(sha_path, "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"Saved SHA-256 manifest to {sha_path}")

    # 2. Experiment Manifest
    exp_manifest = {
        "milestone": "P1.9",
        "title": "Endgame Oracle Integration, Classical Evaluation Reliability & Independent Strength Requalification",
        "repository": "project-janus-phase1",
        "branch": "phase1/classical-janus",
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
            "experimental_predecessor": {
                "name": "Janus Classical X13",
                "commit": "3afcf6f",
                "sha256": "a980cc08cd7cc99ae54a75c21f38dc9d65e568107a7fb79a31dd49fbe2533a29",
                "promotion_status": "REVOKED_IN_PHASE_0"
            },
            "candidate_evaluated": {
                "name": "Janus Classical X14",
                "threads": 4,
                "sha256_exe": sha_manifest["artifacts"]["analysis/phase1/p1.9/control/janus_classical_x14.exe"]["sha256"],
                "promotion_status": "CATEGORY_B_RESEARCH_IMPROVEMENT_PARITY"
            },
            "external_reference": {
                "name": "Stockfish 19",
                "commit": "edb0d9d",
                "sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0",
                "nnue": "nn-1a298aa575a0.nnue"
            }
        },
        "phases_completed": {
            "phase_0": "P1.8 Scientific and Promotion Audit (Promotion revoked, X12 restored, X7 retained)",
            "phase_1": "Generalized Chess Failure Atlas (240 positions, F7 Multi-Cause: 63.4%)",
            "phase_2": "Handcrafted Evaluation Failure Repair (Refined E11, +0.08 plies depth, +141K NPS)",
            "phase_3": "Syzygy Tablebase Integration (Ronald de Man Fathom, 12/12 test cases, zero fallback drag)",
            "phase_4": "Endgame Conversion Study (20 theoretical positions, 75% conversion rate)",
            "phase_5": "Evaluation and Cache Hierarchy Performance (512 KB 16K table, 25% of 2.0 MB L2, 4.76 ns/probe)",
            "phase_6": "Search-Evaluation Interaction Factorial Matrix (7 configs x 12 positions x 2 time controls)",
            "phase_7": "Time-Control Generalization & Reversal Audit (100ms to 5000ms series, reversal resolved)",
            "phase_8": "Candidate Selection & Freeze (Janus Classical X14 staged)",
            "phase_9": "Independent Strength Qualification Tournaments (Matches A, B, C)",
            "phase_10": "Matched Unrestricted Stockfish 19 Benchmark (Match SF)",
            "phase_11": "Final Research & Promotion Decision (Category B, X12 & X7 retained)",
            "phase_12": "Next Classical Research Priorities (P1.10 SPSA & History-directed search roadmap)",
            "phase_13": "Final Deliverables, Manifests & Local Git Commit"
        },
        "tournament_summary": {
            "match_a_1t_vs_x7": {
                "score": "80.5 / 200 (40.25%)",
                "elo": -68.6,
                "p_value": 0.001424,
                "statistically_significant": True,
                "verdict": "Single-thread X7 superior; X7 retained"
            },
            "match_b_4t_vs_x12": {
                "score": "97.5 / 200 (48.75%)",
                "elo": -8.7,
                "p_value": 0.651807,
                "statistically_significant": False,
                "verdict": "Statistical parity with X12; X12 retained"
            },
            "match_c_4t_vs_x12_slow": {
                "score": "50.5 / 100 (50.50%)",
                "elo": 3.5,
                "p_value": 0.898126,
                "statistically_significant": False,
                "verdict": "Parity confirmed; reversal eliminated"
            },
            "match_sf_4t_vs_sf19": {
                "score": "0.0 / 40 (0.00%)",
                "score_interval_95": [0.0, 0.0876],
                "verdict": "External NNUE qualitative gap documented"
            }
        }
    }

    exp_path = P19_DIR / "experiment_manifest.json"
    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Saved experiment manifest to {exp_path}")
    print("=== MANIFEST GENERATION COMPLETE ===")

if __name__ == "__main__":
    main()
