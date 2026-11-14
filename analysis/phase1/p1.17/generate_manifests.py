#!/usr/bin/env python3
"""
generate_manifests.py
Generates authoritative experiment_manifest.json and sha256_manifest.json for Milestone P1.17.
"""

import os
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P117_DIR = ROOT / "analysis" / "phase1" / "p1.17"

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def build_manifests():
    print("Building Milestone P1.17 Authoritative Manifests...")

    # 1. SHA-256 Manifest
    files_manifest = []
    for root, dirs, files in os.walk(P117_DIR):
        for fname in sorted(files):
            # Skip existing manifest files if they exist to avoid self-referential hash instability
            if fname in ["sha256_manifest.json", "experiment_manifest.json"]:
                continue
            fpath = Path(root) / fname
            rel_path = fpath.relative_to(ROOT).as_posix()
            f_size = fpath.stat().st_size
            f_hash = compute_sha256(fpath)
            files_manifest.append({
                "path": rel_path,
                "size_bytes": f_size,
                "sha256": f_hash
            })

    # Also add engine/classical_x developmental source and binaries and master report
    engine_dir = ROOT / "engine" / "classical_x"
    for fname in ["janus_classical_x.cpp", "janus_classical_x.exe", "janus_classical_x.dll"]:
        fpath = engine_dir / fname
        if fpath.exists():
            files_manifest.append({
                "path": fpath.relative_to(ROOT).as_posix(),
                "size_bytes": fpath.stat().st_size,
                "sha256": compute_sha256(fpath)
            })

    master_report = ROOT / "docs" / "phase1" / "p1.17_report.md"
    if master_report.exists():
        files_manifest.append({
            "path": master_report.relative_to(ROOT).as_posix(),
            "size_bytes": master_report.stat().st_size,
            "sha256": compute_sha256(master_report)
        })

    # Save sha256_manifest.json
    sha256_file = P117_DIR / "sha256_manifest.json"
    with open(sha256_file, "w") as f:
        json.dump({
            "milestone": "P1.17",
            "title": "External Benchmark Forensics, Quiescence Strength Attribution & Targeted Classical Evaluation Recovery",
            "total_files": len(files_manifest),
            "files": files_manifest
        }, f, indent=2)
    print(f"SHA-256 Manifest saved: {sha256_file} ({len(files_manifest)} files)")

    # 2. Experiment Manifest
    raw_tournaments_file = P117_DIR / "raw" / "p117_tournaments_raw.json"
    tournaments_summary = {}
    if raw_tournaments_file.exists():
        with open(raw_tournaments_file, "r") as f:
            t_data = json.load(f)
            for m_key, m_val in t_data.items():
                tournaments_summary[m_key] = {
                    "match_id": m_val.get("match_id"),
                    "candidate": m_val.get("candidate"),
                    "opponent": m_val.get("opponent"),
                    "games_played": m_val.get("games_played"),
                    "cand_wins": m_val.get("cand_wins"),
                    "draws": m_val.get("draws"),
                    "cand_losses": m_val.get("cand_losses"),
                    "cand_points": m_val.get("cand_points"),
                    "cand_score_pct": m_val.get("cand_score_pct"),
                    "elo_difference": m_val.get("elo_difference"),
                    "paired_ci_95": m_val.get("paired_ci_95"),
                    "one_sided_p_value": m_val.get("one_sided_p_value")
                }

    exp_manifest = {
        "milestone": "P1.17",
        "title": "External Benchmark Forensics, Quiescence Strength Attribution & Targeted Classical Evaluation Recovery",
        "date": "2026-11-14",
        "charter": "Strictly Non-ML Classical Computer Chess Architecture (Zero NNUE, Zero Learned Parameters, Zero SPSA/Texel Tuning)",
        "development_branch": "phase1/classical-janus",
        "parent_commit": "abd99c5",
        "baselines_and_references": {
            "baseline_1t": {
                "name": "Janus Classical X7",
                "commit": "b34e342",
                "sha256": "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe"
            },
            "baseline_4t": {
                "name": "Janus Classical X12",
                "commit": "78ca3d5",
                "sha256": "00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe"
            },
            "previous_reference": {
                "name": "Janus Classical X21",
                "commit": "abd99c5",
                "sha256": "AD1E1F0598D0CA016267CA4F03DC771346CEE9D0D563A36AB6B6590D7F4731FD",
                "path": "analysis/phase1/p1.16/control/janus_classical_x21.exe"
            },
            "candidate_and_new_reference": {
                "name": "Janus Classical X22 (X22-S / X22-P)",
                "executable_sha256": compute_sha256(P117_DIR / "control" / "janus_classical_x22.exe"),
                "dll_sha256": compute_sha256(P117_DIR / "control" / "janus_classical_x22.dll"),
                "source_sha256": compute_sha256(P117_DIR / "control" / "janus_classical_x22.cpp")
            }
        },
        "phase_results_summary": {
            "phase0_reconciliation": "Verified all 420 P1.16 games, confirmed exact provenance and parent commit abd99c5",
            "phase1_harness_audit": "Discovered UCI perspective inversion bug in P1.16 harness; 25/29 wins were inverted losses; P1.16 external results INVALID",
            "phase2_external_replication": "120 games replicated with corrected harness: Janus engines score 0.0%-2.5% vs SF (0 real wins)",
            "phase3_quiescence_forensics": "Proved leaf checkmate blindness in legacy Q0 (-84 cp) vs true mate evaluation in Q1 (-29,000 cp)",
            "phase4_strength_attribution": "Benchmarked Q0 vs Q1 vs Q2: Q1 incurs -0.50 ply search tree cost for tactical truthfulness; pawn hash recovers +10.6% NPS",
            "phase5_paradox_resolution": "Accepted hypotheses H1-H4: truthfulness exposed primitive classical evaluation gaps (pseudo-outposts)",
            "phase6_eval_gap_ledger": "Identified omission of enemy pawn immunity on outposts and lack of bishop central outposts",
            "phase7_targeted_intervention": "Implemented True Outposts with Enemy Pawn Immunity (+28 mg / +18 eg) and bishop central outposts with 100% color symmetry",
            "phase8_search_compatibility": "Audited LMR, RFP, NMP compatibility; verified no pruning instability",
            "phase9_pawn_hash_parallel": "16K thread-local table verified in 4T SMP; 86.2% hit rate, 12.4 ns latency, 0 collisions",
            "phase10_correctness_suite": "100% Perft match, bitwise determinism, 4T SMP concurrency (6.19M NPS), UCI protocol compliance",
            "phase11_candidate_freeze": "Frozen Janus Classical X22 binaries and C++17 source",
            "phase12_independent_tournaments": "Match 1: 50.0% vs X7 (parity); Match 2: 55.0% vs X7 slow (+34.9 Elo); Match 3: 47.5% vs X12 (4T); Match 4: 60.0% vs X21 (+70.4 Elo)",
            "phase13_matched_external": "Matches 5-7 vs SF4, SF11, SF19: 1.0/120 (0.83%, 0 real wins), confirming independent replication",
            "phase14_research_decision": "Formally adjudicated Category B. Baselines X7 and X12 retained. X22 elevated to New Leading Research Reference Engine",
            "phase15_architectural_direction": "Defined roadmap for P1.18: advanced pawn structure in pawn hash, 3x3 king attack zones, calibrated search pruning"
        },
        "tournaments": tournaments_summary
    }

    exp_file = P117_DIR / "experiment_manifest.json"
    with open(exp_file, "w") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Experiment Manifest saved: {exp_file}")

if __name__ == "__main__":
    build_manifests()
