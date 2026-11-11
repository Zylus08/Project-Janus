#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.8
Manifest Generator: Produces sha256_manifest.json and experiment_manifest.json
"""

import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P18_DIR = ROOT / "analysis" / "phase1" / "p1.8"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("Generating SHA-256 and experiment manifests for Milestone P1.8...")
    sha_manifest = {}

    # Files to include in sha256 manifest
    for p in sorted(P18_DIR.rglob("*")):
        if p.is_file():
            # Skip transient build artifacts
            if p.suffix in [".obj", ".exp", ".lib", ".bat", ".tmp"]:
                continue
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            sha_manifest[rel] = sha256_file(p)

    # Engine source and binaries
    engine_cpp = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
    engine_exe = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
    engine_dll = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
    if engine_cpp.exists(): sha_manifest["engine/classical_x/janus_classical_x.cpp"] = sha256_file(engine_cpp)
    if engine_exe.exists(): sha_manifest["engine/classical_x/janus_classical_x.exe"] = sha256_file(engine_exe)
    if engine_dll.exists(): sha_manifest["engine/classical_x/janus_classical_x.dll"] = sha256_file(engine_dll)

    sha_path = P18_DIR / "sha256_manifest.json"
    with open(sha_path, "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"Wrote SHA-256 manifest to {sha_path} ({len(sha_manifest)} entries)")

    experiment_manifest = {
        "milestone": "P1.8",
        "title": "Classical Evaluation Generalization, Search–Evaluation Co-Design & Endgame Reliability",
        "branch": "phase1/classical-janus",
        "parent_commit": "d058e19",
        "candidate": "Janus Classical X13",
        "baselines": {
            "single_thread_production": "Janus Classical X7 (b34e342) [RETAINED]",
            "multithread_predecessor": "Janus Classical X12 (78ca3d5) [SUPERSEDED]"
        },
        "external_reference": {
            "engine": "Stockfish 19",
            "weights": "nn-1a298aa575a0.nnue",
            "threads": 4,
            "hash_mb": 32,
            "syzygy": "disabled"
        },
        "governing_constraints": {
            "strictly_non_ml": True,
            "zero_nnue": True,
            "zero_learned_weights": True,
            "zero_spsa_tuning": True,
            "tablebases_isolated": True,
            "remote_git_push": False
        },
        "deliverables": {
            "phase0_reconciliation": "analysis/phase1/p1.8/P17_EVIDENCE_AND_ARCHITECTURE_RECONCILIATION.md",
            "phase1_failure_taxonomy": "analysis/phase1/p1.8/CHESS_FAILURE_TAXONOMY.md",
            "phase2_eval_audit": "analysis/phase1/p1.8/X10_EVALUATION_TRANSFER_AUDIT.md",
            "phase3_position_eval": "analysis/phase1/p1.8/POSITION_DEPENDENT_EVALUATION.md",
            "phase4_cost_model": "analysis/phase1/p1.8/CLASSICAL_EVALUATION_COST_MODEL.md",
            "phase5_syzygy_feasibility": "analysis/phase1/p1.8/SYZYGY_FEASIBILITY_AND_CORRECTNESS.md",
            "phase6_search_eval_factorial": "analysis/phase1/p1.8/P18_SEARCH_EVALUATION_FACTORIAL.md",
            "phase7_candidate_selection": "analysis/phase1/p1.8/X13_CANDIDATE_SELECTION.md",
            "phase8_correctness_report": "analysis/phase1/p1.8/P18_CORRECTNESS_REPORT.md",
            "phase9_internal_strength": "analysis/phase1/p1.8/X13_INTERNAL_STRENGTH.md",
            "phase10_stockfish_progress": "analysis/phase1/p1.8/MATCHED_STOCKFISH19_PROGRESS.md",
            "phase11_research_decision": "analysis/phase1/p1.8/FINAL_RESEARCH_DECISION.md",
            "phase12_next_priorities": "analysis/phase1/p1.8/NEXT_CLASSICAL_PRIORITY.md",
            "milestone_report": "docs/phase1/p1.8_report.md"
        },
        "tournament_results": {
            "match_a_x13_1t_vs_x7_1t": {
                "games": 200,
                "score": "59W - 67D - 74L (46.25%)",
                "elo_delta": -26.1,
                "elo_ci_95": [-74.2, 22.0],
                "paired_t_statistic": -1.2405,
                "df": 99,
                "p_value": 0.21772,
                "significant": False
            },
            "match_b_x13_4t_vs_x12_4t": {
                "games": 200,
                "score": "67W - 78D - 55L (53.00%)",
                "elo_delta": 20.9,
                "elo_ci_95": [-27.2, 69.0],
                "paired_t_statistic": 1.241,
                "df": 99,
                "p_value": 0.217522,
                "significant": False,
                "decisive_game_margin": "+12 wins"
            },
            "match_c_x13_4t_vs_x12_4t_slow": {
                "games": 40,
                "score": "13W - 7D - 20L (41.25%)",
                "elo_delta": -61.4,
                "elo_ci_95": [-169.1, 46.2],
                "paired_t_statistic": -1.1285,
                "df": 19,
                "p_value": 0.273142,
                "significant": False
            },
            "match_sf_x13_4t_vs_sf19_4t": {
                "games": 40,
                "score": "0W - 2D - 38L (2.50%)",
                "elo_delta": -636.4,
                "elo_ci_95": [-940.8, -332.1],
                "wilson_score_interval_95": [0.0044, 0.1288],
                "paired_t_statistic": -27.6064,
                "df": 19,
                "p_value": 0.0,
                "significant": True,
                "breakthrough": "First project points scored against unrestricted Stockfish 19 (2 draws as Black)"
            }
        },
        "promotion_adjudication": {
            "single_thread_baseline": "Janus Classical X7 (Retained)",
            "multithread_baseline": "Janus Classical X13 (Promoted)"
        }
    }

    exp_path = P18_DIR / "experiment_manifest.json"
    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(experiment_manifest, f, indent=2)
    print(f"Wrote Experiment manifest to {exp_path}")

if __name__ == "__main__":
    main()
