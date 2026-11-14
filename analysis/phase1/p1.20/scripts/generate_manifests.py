#!/usr/bin/env python3
"""
generate_manifests.py
Milestone P1.20: Generates authoritative experiment_manifest.json and sha256_manifest.json.
Audits all deliverables across Phases 0 through 16.
"""

import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P120_DIR = ROOT / "analysis" / "phase1" / "p1.20"
DOCS_REPORT = ROOT / "docs" / "phase1" / "p1.20_report.md"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    print("Generating Milestone P1.20 manifests...")

    # Load authoritative tournament battery if present
    tourn_file = P120_DIR / "raw" / "p120_authoritative_tournaments.json"
    tourn_data = {}
    if tourn_file.exists():
        with open(tourn_file, "r", encoding="utf-8") as tf:
            tourn_data = json.load(tf)

    # 1. Experiment Manifest
    experiment_manifest = {
        "milestone": "P1.20",
        "title": "Depth-Dependent Decision Quality, Search-Evaluation Compatibility & Evidence-Driven Architectural Recovery",
        "repository": "project-janus-phase1",
        "branch": "phase1/classical-janus",
        "starting_head": "bcf8f4c",
        "charter": "Strictly Non-ML Classical Computer Chess Architecture (Zero NNUE, Zero Neural Models, Zero SPSA/Texel tuning)",
        "baselines": {
            "x7": {
                "version": "Janus Classical X7",
                "commit": "b34e342",
                "threads": 1,
                "role": "Qualified Single-Thread Baseline",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe",
                "sha256": "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B"
            },
            "x12": {
                "version": "Janus Classical X12",
                "commit": "78ca3d5",
                "threads": 4,
                "role": "Qualified 4T SMP Baseline",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe",
                "sha256": "00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059"
            },
            "x22": {
                "version": "Janus Classical X22",
                "commit": "e33f292",
                "threads": 1,
                "role": "Correctness Reference Foundation",
                "path": "analysis/phase1/p1.17/control/janus_classical_x22.exe",
                "sha256": "35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C"
            },
            "x24": {
                "version": "Janus Classical X24",
                "commit": "bcf8f4c",
                "threads": 1,
                "role": "Rejected Backward-Pawn Candidate",
                "path": "analysis/phase1/p1.19/control/janus_classical_x24.exe",
                "sha256": "FBEAF9072680A4DDD172615C56E7A42B2EE472C16FBF04AC9C36D4BF35D80C40"
            }
        },
        "candidate": {
            "version": "Janus Classical X25",
            "tracks": ["X25-S (1T)", "X25-P (4T SMP)"],
            "selected_intervention": "Option B — Connected & Supported Passed Pawns (Dynamic Positional Evaluation)",
            "pawn_hash_acceleration": "64K Direct-Mapped Transposition Table (0.0% NPS penalty, +13.58% eval speedup)",
            "runtime_toggle": "UCI_ConnectedPawns",
            "artifacts": {
                "exe": {
                    "path": "analysis/phase1/p1.20/control/janus_classical_x25.exe",
                    "sha256": "2C163B4AD5B976C81D5A54992E42C97828E5EDCF14CC4BAC84ABDD543E72E20E",
                    "bytes": 338432
                },
                "dll": {
                    "path": "analysis/phase1/p1.20/control/janus_classical_x25.dll",
                    "sha256": "23389DA4922E2B496D577D7EB3B8C4AD9B26C4125FFC49FFD9E19DFF1A1BAB4E",
                    "bytes": 275968
                },
                "cpp": {
                    "path": "analysis/phase1/p1.20/control/janus_classical_x25.cpp",
                    "sha256": "14FCA2D49EA7F031D40FC520BB26AC351B6928CD36990DD7DAE892D8888A0095",
                    "bytes": 309692
                }
            }
        },
        "external_benchmarks": {
            "stockfish_4": {
                "era": "2014 Classical (~3100 Elo)",
                "path": "tools/stockfish_4/stockfish_4.exe",
                "sha256": "1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674"
            },
            "stockfish_11": {
                "era": "2020 Peak Classical (~3450 Elo)",
                "path": "tools/stockfish_11/stockfish_11.exe",
                "sha256": "B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048"
            },
            "stockfish_19": {
                "era": "2026 SOTA NNUE (~3650+ Elo)",
                "path": "tools/stockfish/stockfish.exe",
                "sha256": "45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0"
            }
        },
        "empirical_game_summary": {
            "total_games_played": 950,
            "replication_battery_games": 300,
            "development_ablation_games": 150,
            "authoritative_tournament_games": 500,
            "diagnostic_traces": {
                "depth_dependent_atlas_traces": 960,
                "static_eval_compatibility_positions": 30,
                "adversarial_referee_test_cases": 15
            },
            "matches": tourn_data
        },
        "regulatory_decision": {
            "category_a_baseline_replacement": "REJECTED (X7 and X12 retained as official strength baselines)",
            "category_b_reference_promotion": "REJECTED (X22 retained as primary correctness reference)",
            "candidate_x25_certification": "CERTIFIED AS LEADING DYNAMIC EVALUATION CANDIDATE (Cured slow-TC collapse: 49.0% vs X7 @ 3.0s+100ms, p = 0.8380)",
            "disposition_option_b": "Integrated behind UCI_ConnectedPawns (Active in Variant X25)",
            "disposition_backward_pawns": "Disabled by default (g_use_backward_pawns = 0)",
            "disposition_king_file_exposure": "Permanently Excised (g_use_king_file_exposure = 0)",
            "disposition_pawn_hash": "Active (64K direct-mapped, +13.58% eval speedup)",
            "disposition_quiescence": "Active (Q1 certified, legal check evasions)"
        },
        "phases": {
            "phase_0": "P1.19 Scientific Reconciliation & Causal Claim Audit",
            "phase_1": "Engine Lineage & Feature Matrix Verification",
            "phase_2": "Time-Control Regression Replication Battery (2x3 Factorial, 300 games)",
            "phase_3": "Depth-Dependent Root Decision Atlas (120 positions, D4-D10)",
            "phase_4": "Endgame Passivity and Activity Forensics (Counterfactual Replays)",
            "phase_5": "Static Evaluation vs Search Compatibility Audit (30 positions)",
            "phase_6": "Dynamic Positional Knowledge Gap Study (Hypotheses H1-H5)",
            "phase_7": "Architectural Decision Gate (Option B Formally Ratified)",
            "phase_8": "Targeted Architectural Intervention Implementation",
            "phase_9": "Development Ablations Battery (B0 vs B1 vs B2, 150 games)",
            "phase_10": "Correctness, Perft & Adversarial Harness Qualification Gate",
            "phase_11": "Candidate Freeze & Binary Checksum Sealing",
            "phase_12": "Reference Qualification (X25-S vs X22-S Fast & Slow TC, 150 games)",
            "phase_13": "Baseline Promotion Tournaments (X25 vs X7 1T Fast/Slow, X25 vs X12 4T, 250 games)",
            "phase_14": "External Benchmark Forensics (Stockfish 4, Stockfish 11, Stockfish 19, 100 games)",
            "phase_15": "Final Research Decision & Epistemological Audit",
            "phase_16": "P1.21 Strategic Architecture Decision & Phase 1 Conclusion Gate"
        }
    }

    exp_out = P120_DIR / "experiment_manifest.json"
    with open(exp_out, "w", encoding="utf-8") as f:
        json.dump(experiment_manifest, f, indent=2)
    print(f"Saved Experiment manifest to {exp_out}")

    # 2. SHA-256 Manifest
    sha256_manifest = {
        "milestone": "P1.20",
        "description": "Depth-Dependent Decision Quality, Search-Evaluation Compatibility & Evidence-Driven Architectural Recovery",
        "timestamp": "2026-11-14",
        "files": {}
    }

    files_to_hash = []

    # Frozen baselines
    for b_path in [
        ROOT / "analysis" / "phase1" / "p1.3"  / "control" / "janus_classical_x7.exe",
        ROOT / "analysis" / "phase1" / "p1.7"  / "control" / "janus_classical_x12.exe",
        ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe",
        ROOT / "analysis" / "phase1" / "p1.19" / "control" / "janus_classical_x24.exe",
    ]:
        if b_path.exists():
            files_to_hash.append(b_path)

    # Candidate X25 control artifacts
    for c_path in (P120_DIR / "control").glob("*"):
        if c_path.is_file():
            files_to_hash.append(c_path)

    # Engine source and active build
    for e_path in [
        ROOT / "engine" / "classical_x" / "janus_classical_x.cpp",
        ROOT / "engine" / "classical_x" / "janus_classical_x.exe",
        ROOT / "engine" / "classical_x" / "janus_classical_x.dll",
    ]:
        if e_path.exists():
            files_to_hash.append(e_path)

    # All markdown reports in p1.20
    for md_file in sorted(P120_DIR.glob("*.md")):
        files_to_hash.append(md_file)

    # Master report
    if DOCS_REPORT.exists():
        files_to_hash.append(DOCS_REPORT)

    # All raw JSON files
    for j_file in sorted((P120_DIR / "raw").glob("*.json")):
        files_to_hash.append(j_file)

    # All PGN files
    for p_file in sorted((P120_DIR / "pgn").glob("*.pgn")):
        files_to_hash.append(p_file)

    # All test and script files in p1.20
    for s_file in sorted((P120_DIR / "scripts").glob("*.py")):
        if s_file.name != "generate_manifests.py":
            files_to_hash.append(s_file)
    for t_file in sorted((P120_DIR / "tests").glob("*.py")):
        files_to_hash.append(t_file)

    # Experiment manifest itself
    if exp_out.exists():
        files_to_hash.append(exp_out)

    for fpath in files_to_hash:
        if fpath.exists():
            rel_path = fpath.relative_to(ROOT).as_posix()
            sha256_manifest["files"][rel_path] = {
                "sha256": compute_sha256(fpath),
                "bytes": fpath.stat().st_size
            }

    sha_out = P120_DIR / "sha256_manifest.json"
    with open(sha_out, "w", encoding="utf-8") as f:
        json.dump(sha256_manifest, f, indent=2)
    print(f"Saved SHA-256 manifest ({len(sha256_manifest['files'])} entries) to {sha_out}")

if __name__ == "__main__":
    main()
