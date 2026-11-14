#!/usr/bin/env python3
"""
generate_manifests.py
Generates authoritative experiment_manifest.json and sha256_manifest.json for Milestone P1.16.
"""

import os
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P116_DIR = ROOT / "analysis" / "phase1" / "p1.16"

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def build_manifests():
    print("Building Milestone P1.16 Authoritative Manifests...")

    # 1. SHA-256 Manifest
    files_manifest = []
    for root, dirs, files in os.walk(P116_DIR):
        for fname in sorted(files):
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

    master_report = ROOT / "docs" / "phase1" / "p1.16_report.md"
    if master_report.exists():
        files_manifest.append({
            "path": master_report.relative_to(ROOT).as_posix(),
            "size_bytes": master_report.stat().st_size,
            "sha256": compute_sha256(master_report)
        })

    # Save sha256_manifest.json
    sha256_file = P116_DIR / "sha256_manifest.json"
    with open(sha256_file, "w") as f:
        json.dump({
            "milestone": "P1.16",
            "title": "Classical Evaluation Integrity, Tactical Quiescence Search & Evidence-Based Strength Recovery",
            "total_files": len(files_manifest),
            "files": files_manifest
        }, f, indent=2)
    print(f"SHA-256 Manifest saved: {sha256_file} ({len(files_manifest)} files)")

    # 2. Experiment Manifest
    # Load tournament results if available
    raw_tournaments_file = P116_DIR / "raw" / "p116_tournaments_raw.json"
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
                    "paired_ci_95": m_val.get("paired_ci_95") or m_val.get("ci_95"),
                    "one_sided_p_value": m_val.get("one_sided_p_value")
                }

    exp_manifest = {
        "milestone": "P1.16",
        "title": "Classical Evaluation Integrity, Tactical Quiescence Search & Evidence-Based Strength Recovery",
        "date": "2026-11-14",
        "charter": "Strictly Non-ML Classical Computer Chess Architecture (Zero NNUE, Zero Learned Parameters, Zero SPSA/Texel Tuning)",
        "development_branch": "phase1/classical-janus",
        "parent_commit": "2226c0c",
        "baselines_and_references": {
            "baseline_1t": {
                "name": "Janus Classical X7",
                "commit": "b34e342",
                "sha256": "86392A2FE44C09B167664B29DA928D1FE25CE0E0B19BD8CE4751433F62D38B28",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe"
            },
            "baseline_4t": {
                "name": "Janus Classical X12",
                "commit": "78ca3d5",
                "sha256": "00B4F5FE9CE137E749845B0A80509E2B2B498C0B29E3065DE78CCFE573F4B52F",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe"
            },
            "leading_reference": {
                "name": "Janus Classical X19",
                "commit": "bcfdecd",
                "sha256": "CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629",
                "path": "analysis/phase1/p1.14/control/janus_classical_x19.exe"
            },
            "candidate": {
                "name": "Janus Classical X21 (X21-S / X21-P)",
                "executable_sha256": compute_sha256(P116_DIR / "control" / "janus_classical_x21.exe"),
                "dll_sha256": compute_sha256(P116_DIR / "control" / "janus_classical_x21.dll"),
                "source_sha256": compute_sha256(P116_DIR / "control" / "janus_classical_x21.cpp")
            }
        },
        "phase_results_summary": {
            "phase0_reconciliation": "Verified all 420 P1.15 games, confirmed Game 12 mate blindness forensics",
            "phase1_eval_ledger": "Authoritative inventory of E0-E15 terms, additive trace verified within 1 cp",
            "phase2_eval_correctness": "225/225 (100.0%) mirror symmetry, 225/225 (100.0%) absolute inversion on E5",
            "phase3_quiescence_audit": "Discovered legacy stand-pat under check defect and mate blindness (-89 cp)",
            "phase4_quiescence_repairs": "100.0% pass rate (40/40) on verification suite, mate/stalemate resolved",
            "phase5_selective_checking": "Q1 authoritatively selected; quiet checks rejected due to -27.8% NPS penalty",
            "phase6_targeted_eval": "64K thread-local pawn hash table integrated on 1T (+52.1% search NPS)",
            "phase7_factorial_ablation": "B4 (X21-S) and B6 (X21-P) achieved deepest search trees and 100% mate rate",
            "phase8_search_economics": "Micro-benchmarked component latencies, verified EBF 2.45x, resolved G12",
            "phase9_systems_correctness": "Perft 100% exact match, bitwise single-thread determinism, SMP safe, UCI compliant"
        },
        "tournaments": tournaments_summary
    }

    exp_file = P116_DIR / "experiment_manifest.json"
    with open(exp_file, "w") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Experiment Manifest saved: {exp_file}")

if __name__ == "__main__":
    build_manifests()
