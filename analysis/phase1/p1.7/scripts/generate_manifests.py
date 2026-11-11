#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Manifest Generator: Produces sha256_manifest.json and experiment_manifest.json
"""

import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P17_DIR = ROOT / "analysis" / "phase1" / "p1.7"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print(f"Generating SHA-256 and experiment manifests for Milestone P1.7...")
    sha_manifest = {}
    
    # Files to include in sha256 manifest
    for p in sorted(P17_DIR.rglob("*")):
        if p.is_file():
            # Skip transient build artifacts
            if p.suffix in [".obj", ".exp", ".lib", ".bat", ".tmp"]:
                continue
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            sha_manifest[rel] = sha256_file(p)

    # Also include the engine source and compiled binary
    engine_cpp = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
    engine_exe = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
    engine_dll = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
    if engine_cpp.exists(): sha_manifest["engine/classical_x/janus_classical_x.cpp"] = sha256_file(engine_cpp)
    if engine_exe.exists(): sha_manifest["engine/classical_x/janus_classical_x.exe"] = sha256_file(engine_exe)
    if engine_dll.exists(): sha_manifest["engine/classical_x/janus_classical_x.dll"] = sha256_file(engine_dll)

    sha_path = P17_DIR / "sha256_manifest.json"
    with open(sha_path, "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"Wrote SHA-256 manifest to {sha_path} ({len(sha_manifest)} entries)")

    experiment_manifest = {
        "milestone": "P1.7",
        "title": "Parallel Search Recovery, Transposition-Table Cooperation & Useful Search Efficiency",
        "branch": "phase1/classical-janus",
        "parent_commit": "37d0ade",
        "candidate": "Janus Classical X12",
        "baselines": {
            "single_thread_production": "Janus Classical X7 (b34e342)",
            "multithread_predecessor": "Janus Classical X11 (54559ce)"
        },
        "external_reference": {
            "engine": "Stockfish 19",
            "weights": "nn-1a298aa575a0.nnue",
            "threads": 4,
            "hash_mb": 32
        },
        "governing_constraints": {
            "strictly_non_ml": True,
            "zero_nnue": True,
            "zero_learned_weights": True,
            "zero_spsa_tuning": True,
            "remote_git_push": False
        },
        "key_experiments": {
            "phase0_concurrency_audit": "analysis/phase1/p1.7/P16_EVIDENCE_AND_CONCURRENCY_AUDIT.md",
            "phase1_thread_forensics": "analysis/phase1/p1.7/THREAD_LEVEL_SEARCH_FORENSICS.md",
            "phase2_tt_isolation": "analysis/phase1/p1.7/TRANSPOSITION_TABLE_COOPERATION.md",
            "phase3_worker_cooperation": "analysis/phase1/p1.7/WORKER_SEARCH_COOPERATION.md",
            "phase4_root_clock_audit": "analysis/phase1/p1.7/PARALLEL_ROOT_AND_CLOCK_AUDIT.md",
            "phase5_concurrency_correctness": "analysis/phase1/p1.7/P17_CONCURRENCY_CORRECTNESS.md",
            "phase6_useful_computation": "analysis/phase1/p1.7/USEFUL_COMPUTATION_BENCHMARK.md",
            "phase7_factorial_ablation": "analysis/phase1/p1.7/P17_MULTITHREAD_FACTORIAL.md",
            "phase8_internal_tournaments": "analysis/phase1/p1.7/X12_INTERNAL_STRENGTH.md",
            "phase9_stockfish_benchmark": "analysis/phase1/p1.7/MATCHED_STOCKFISH19_MULTICORE.md",
            "phase10_promotion_decision": "analysis/phase1/p1.7/FINAL_RESEARCH_DECISION.md",
            "phase11_next_priorities": "analysis/phase1/p1.7/NEXT_CLASSICAL_PRIORITY.md"
        },
        "tournament_results": {
            "match_a_x12_4t_vs_x11_4t": {
                "games": 200,
                "score": "93W - 50D - 57L (59.00%)",
                "elo_delta": "+63.2 Elo",
                "paired_t_statistic": 3.1532,
                "df": 99,
                "p_value": 0.002138,
                "significant": True
            },
            "match_b_x12_4t_vs_x7_1t": {
                "games": 40,
                "score": "15W - 11D - 14L (51.25%)",
                "elo_delta": "+8.7 Elo",
                "paired_t_statistic": 0.1951,
                "df": 19,
                "p_value": 0.847398,
                "significant": False
            },
            "match_c_x12_1t_vs_x7_1t": {
                "games": 40,
                "score": "15W - 8D - 17L (47.50%)",
                "elo_delta": "-17.4 Elo",
                "paired_t_statistic": -0.3258,
                "df": 19,
                "p_value": 0.748138,
                "significant": False
            },
            "match_sf_x12_4t_vs_sf19_4t": {
                "games": 40,
                "score": "0W - 0D - 40L (0.00%)",
                "elo_delta": "-800.0 Elo",
                "ci_upper_elo": -407.0
            }
        },
        "final_adjudication": {
            "category": "Category A — Parallel Strength Advancement Qualified",
            "promoted_parallel_baseline": "Janus Classical X12",
            "retained_single_thread_production_anchor": "Janus Classical X7"
        }
    }

    exp_path = P17_DIR / "experiment_manifest.json"
    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(experiment_manifest, f, indent=2)
    print(f"Wrote experiment manifest to {exp_path}")

if __name__ == "__main__":
    main()

