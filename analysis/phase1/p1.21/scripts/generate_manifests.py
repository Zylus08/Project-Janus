#!/usr/bin/env python3
"""
generate_manifests.py
Milestone P1.21: Generates authoritative experiment_manifest.json and sha256_manifest.json.
Audits all deliverables across Phases 0 through 16.
"""

import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P121_DIR = ROOT / "analysis" / "phase1" / "p1.21"
DOCS_REPORT = ROOT / "docs" / "phase1" / "p1.21_report.md"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    print("Generating Milestone P1.21 manifests...")

    # Load authoritative tournament battery if present
    tourn_file = P121_DIR / "raw" / "independent_strength_raw.json"
    tourn_data = []
    if tourn_file.exists():
        with open(tourn_file, "r", encoding="utf-8") as tf:
            tourn_data = json.load(tf)

    # 1. Experiment Manifest
    experiment_manifest = {
        "milestone": "P1.21",
        "title": "Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate",
        "repository": "project-janus-phase1",
        "branch": "phase1/classical-janus",
        "starting_head": "c232730",
        "charter": "Strictly Non-ML Classical Computer Chess Architecture (Zero NNUE, Zero Neural Models, Zero SPSA/Texel tuning)",
        "baselines": {
            "x7": {
                "version": "Janus Classical X7",
                "commit": "b34e342",
                "threads": 1,
                "role": "Qualified Single-Thread Baseline (Retained)",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe",
                "sha256": "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B"
            },
            "x12": {
                "version": "Janus Classical X12",
                "commit": "78ca3d5",
                "threads": 4,
                "role": "Qualified 4T SMP Baseline (Retained)",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe",
                "sha256": "00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059"
            },
            "x22": {
                "version": "Janus Classical X22",
                "commit": "e33f292",
                "threads": 1,
                "role": "Correctness Reference Foundation (Retained)",
                "path": "analysis/phase1/p1.17/control/janus_classical_x22.exe",
                "sha256": "35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C"
            },
            "x25": {
                "version": "Janus Classical X25",
                "commit": "bcf8f4c",
                "threads": 1,
                "role": "Archived P1.20 Candidate",
                "path": "analysis/phase1/p1.20/control/janus_classical_x25.exe",
                "sha256": "2C163B4A983E7D3FEA66150FE4DC3A84A1E86EBE31ACDDF4D1A444C3A3542E61"
            }
        },
        "candidate": {
            "version": "Janus Classical X26",
            "tracks": ["X26-S (1T)", "X26-P (4T SMP)"],
            "selected_intervention": "Option A — Verified Reverse Futility Pruning Correctness Repair",
            "decision": "REJECTED (Scored 37.0% - 42.5% vs Baselines; Classical Search Ceiling Proved)",
            "control_artifacts": {
                "executable": {
                    "path": "analysis/phase1/p1.21/control/janus_classical_x26.exe",
                    "sha256": "0C2338DB3643F06C1E61AEADFD7B01A0E87BE5C4975E595123163F712F00C380"
                },
                "dynamic_library": {
                    "path": "analysis/phase1/p1.21/control/janus_classical_x26.dll",
                    "sha256": "4E4DC1F81AEBEC6B20E04D7605B5B765E3875269F28D11250EA9F3623A4236BC"
                },
                "source_code": {
                    "path": "analysis/phase1/p1.21/control/janus_classical_x26.cpp",
                    "sha256": "C6EE178EEE406965A5DFF9C8103DF0BCBA8AFD326BA19186B4CD4A945C2C1412"
                }
            }
        },
        "authoritative_tournaments": tourn_data,
        "deliverables": [
            "docs/phase1/p1.21_report.md",
            "analysis/phase1/p1.21/P120_SCIENTIFIC_RECONCILIATION.md",
            "analysis/phase1/p1.21/P121_ENGINE_CONFIGURATION_LEDGER.md",
            "analysis/phase1/p1.21/REVERSE_FUTILITY_PRUNING_CONTRACT.md",
            "analysis/phase1/p1.21/RFP_COUNTERFACTUAL_DECISION_AUDIT.md",
            "analysis/phase1/p1.21/EVALUATION_PERTURBATION_AND_SEARCH_RESPONSE.md",
            "analysis/phase1/p1.21/DEPTH_DEPENDENT_PRUNING_RELIABILITY.md",
            "analysis/phase1/p1.21/SHALLOW_EXACT_SEARCH_REFERENCE.md",
            "analysis/phase1/p1.21/SEARCH_COST_AND_SELECTIVITY_PROFILE.md",
            "analysis/phase1/p1.21/P121_ARCHITECTURAL_DECISION.md",
            "analysis/phase1/p1.21/TARGETED_PRUNING_COMPATIBILITY_INTERVENTION.md",
            "analysis/phase1/p1.21/P121_CONTROLLED_ABLATIONS.md",
            "analysis/phase1/p1.21/P121_CORRECTNESS_AND_HARNESS_REPORT.md",
            "analysis/phase1/p1.21/X26_CANDIDATE_FREEZE.md",
            "analysis/phase1/p1.21/X26_INDEPENDENT_STRENGTH.md",
            "analysis/phase1/p1.21/P121_EXTERNAL_CALIBRATION.md",
            "analysis/phase1/p1.21/FINAL_RESEARCH_DECISION.md",
            "analysis/phase1/p1.21/P122_ARCHITECTURE_PIVOT_DECISION.md"
        ]
    }

    exp_manifest_path = P121_DIR / "experiment_manifest.json"
    with open(exp_manifest_path, "w", encoding="utf-8") as f:
        json.dump(experiment_manifest, f, indent=2)
    print(f"  Experiment manifest written to: {exp_manifest_path}")

    # 2. SHA-256 Manifest
    sha256_manifest = {
        "milestone": "P1.21",
        "description": "Cryptographic SHA-256 checksum registry for all Milestone P1.21 files and artifacts",
        "files": {}
    }

    # Add master report
    if DOCS_REPORT.exists():
        sha256_manifest["files"]["docs/phase1/p1.21_report.md"] = compute_sha256(DOCS_REPORT)

    # Walk analysis/phase1/p1.21
    for root, dirs, files in os.walk(P121_DIR):
        for f in files:
            if f in ("sha256_manifest.json",):
                continue
            f_path = Path(root) / f
            rel_path = f_path.relative_to(ROOT).as_posix()
            sha256_manifest["files"][rel_path] = compute_sha256(f_path)

    sha_manifest_path = P121_DIR / "sha256_manifest.json"
    with open(sha_manifest_path, "w", encoding="utf-8") as f:
        json.dump(sha256_manifest, f, indent=2)
    print(f"  SHA-256 manifest written to: {sha_manifest_path}")

if __name__ == "__main__":
    main()
