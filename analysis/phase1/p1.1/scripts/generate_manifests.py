#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Manifest Generator: sha256_manifest.json and experiment_manifest.json.
"""

import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
P1_1_DIR = ROOT / "analysis" / "phase1" / "p1.1"

FILES_TO_HASH = [
    # Binaries & Source
    ROOT / "engine" / "classical_x" / "janus_classical_x.cpp",
    ROOT / "engine" / "classical_x" / "janus_classical_x.exe",
    ROOT / "engine" / "classical_x" / "janus_classical_x.dll",
    ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp",
    ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe",
    Path("E:/ChessXML/tools/stockfish/stockfish.exe"),
    
    # Reports
    P1_1_DIR / "BASELINE_RECONCILIATION.md",
    P1_1_DIR / "STAGED_MOVE_GENERATION_REPORT.md",
    P1_1_DIR / "QUIESCENCE_SEE_ABLATION.md",
    P1_1_DIR / "NULL_MOVE_PRUNING_REPORT.md",
    P1_1_DIR / "REVERSE_FUTILITY_PRUNING_REPORT.md",
    P1_1_DIR / "ASPIRATION_WINDOW_REPORT.md",
    P1_1_DIR / "SEARCH_INTEGRATION_MATRIX.md",
    P1_1_DIR / "SEARCH_CORRECTNESS_REPORT.md",
    P1_1_DIR / "CLASSICAL_STRENGTH_VALIDATION.md",
    P1_1_DIR / "STOCKFISH19_PROGRESS_CHECK.md",
    P1_1_DIR / "P1_2_PRIORITIZATION.md",
    ROOT / "docs" / "phase1" / "p1.1_report.md",
    
    # Raw JSON
    P1_1_DIR / "raw" / "staged_movegen_benchmark_raw.json",
    P1_1_DIR / "raw" / "quiescence_see_ablation_raw.json",
    P1_1_DIR / "raw" / "null_move_pruning_ablation_raw.json",
    P1_1_DIR / "raw" / "reverse_futility_pruning_raw.json",
    P1_1_DIR / "raw" / "aspiration_window_raw.json",
    P1_1_DIR / "raw" / "search_integration_matrix_raw.json",
    P1_1_DIR / "raw" / "search_correctness_raw.json",
    P1_1_DIR / "raw" / "janus_x_vs_c1_tournament_raw.json",
    P1_1_DIR / "raw" / "janus_x_vs_sf19_diagnostic_raw.json",
    
    # PGN
    P1_1_DIR / "pgn" / "janus_x_vs_sf19_diagnostic.pgn"
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    hashes = {}
    for p in FILES_TO_HASH:
        if p.exists():
            rel = str(p.relative_to(ROOT)) if ROOT in p.parents else str(p)
            hashes[rel] = {
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size
            }
        else:
            print(f"Warning: File not found: {p}")

    sha_path = P1_1_DIR / "sha256_manifest.json"
    with open(sha_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    print(f"Wrote sha256_manifest.json ({len(hashes)} files)")

    experiment_manifest = {
        "milestone": "Phase 1, Milestone P1.1",
        "program": "Classical Engine Supremacy Program",
        "worktree": "E:\\ChessXML\\project-janus-phase1",
        "branch": "phase1/classical-janus",
        "parent_commit": "bbadf8f / 7b526a0",
        "timestamp_iso": "2026-11-10T09:05:00Z",
        "system_environment": {
            "os": "Windows-11-10.0.26200-SP0",
            "processor": "Intel64 Family 6 Model 154 Stepping 3, GenuineIntel",
            "machine": "AMD64",
            "python_version": "3.13.2",
            "msvc_version": "MSVC 2022 v19.44 / BuildTools (x64)",
            "compiler_flags": "/O2 /Ot /Oi /std:c++17 /EHsc",
            "cpu_target": "x86-64-avx2"
        },
        "engine_lineages": {
            "frozen_production_baseline_c1": {
                "source": "analysis/v0.56/native/janus_native.cpp",
                "sha256": hashes.get("analysis\\v0.56\\native\\janus_native.cpp", {}).get("sha256", ""),
                "binary": "analysis/v0.56/native/janus_native_engine.exe",
                "binary_sha256": hashes.get("analysis\\v0.56\\native\\janus_native_engine.exe", {}).get("sha256", "")
            },
            "janus_classical_x_lineage_p1_1": {
                "source": "engine/classical_x/janus_classical_x.cpp",
                "sha256": hashes.get("engine\\classical_x\\janus_classical_x.cpp", {}).get("sha256", ""),
                "binary": "engine/classical_x/janus_classical_x.exe",
                "binary_sha256": hashes.get("engine\\classical_x\\janus_classical_x.exe", {}).get("sha256", ""),
                "dll": "engine/classical_x/janus_classical_x.dll",
                "dll_sha256": hashes.get("engine\\classical_x\\janus_classical_x.dll", {}).get("sha256", "")
            },
            "stockfish_reference": {
                "binary": "E:/ChessXML/tools/stockfish/stockfish.exe",
                "sha256": hashes.get("E:\\ChessXML\\tools\\stockfish\\stockfish.exe", {}).get("sha256", ""),
                "version": "Stockfish 19 (g++ 15.2.0, x86-64-avxvnni, NNUE nn-1a298aa575a0.nnue)"
            }
        },
        "search_modernization_summary": {
            "variant_matrix": {
                "X0": {"desc": "C1 Baseline Equivalent", "nodes_d7": 16342285, "speedup": 1.00, "ebf": 6.773, "avg_depth_250ms": 6.08},
                "X1": {"desc": "Staged Move Generation", "nodes_d7": 16343497, "speedup": 3.18, "ebf": 6.773, "avg_depth_250ms": 7.16},
                "X2": {"desc": "Quiescence SEE Filtering", "nodes_d7": 10739035, "speedup": 1.49, "ebf": 6.378, "avg_depth_250ms": 6.24},
                "X3": {"desc": "Null-Move Pruning (R=3)", "nodes_d7": 6279449, "speedup": 2.71, "ebf": 5.908, "avg_depth_250ms": 7.04},
                "X4": {"desc": "Reverse Futility Pruning", "nodes_d7": 9993931, "speedup": 1.62, "ebf": 6.313, "avg_depth_250ms": 6.68},
                "X5": {"desc": "Aspiration Windows (delta=25cp)", "nodes_d7": 14169939, "speedup": 1.13, "ebf": 6.636, "avg_depth_250ms": 6.16},
                "X6": {"desc": "Full Integrated Candidate", "nodes_d7": 2555062, "speedup": 10.52, "ebf": 5.196, "avg_depth_250ms": 9.44}
            },
            "net_node_reduction_pct": 84.36,
            "net_search_speedup": 10.52,
            "depth_expansion_plies": 3.36
        },
        "strength_validation_summary": {
            "janus_x_vs_c1_tournament": {
                "total_games": 100,
                "score": "87.0 / 100 (87.0%)",
                "wdl": "77W - 20D - 3L",
                "elo_diff": "+330.2 Elo",
                "elo_95ci": ["+230.4", "+430.1"],
                "qualification_status": "QUALIFIED (Target >= +250 Elo Met)"
            },
            "janus_x_vs_sf19_diagnostic": {
                "total_games": 20,
                "score": "1.5 / 20.0 (7.5%)",
                "wdl": "0W - 3D - 17L",
                "historical_baseline_c1": "0.0% (0W - 0D - 20L)",
                "survival_plies_avg": 64.8,
                "historical_c1_survival_plies": 51.2
            }
        },
        "perft_qualification": {
            "suite_positions": 6,
            "status": "QUALIFIED (100% Bit-Exact Match across 6 Depths)",
            "peak_nps": 23432457
        }
    }

    exp_path = P1_1_DIR / "experiment_manifest.json"
    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(experiment_manifest, f, indent=2)
    print(f"Wrote experiment_manifest.json")


if __name__ == "__main__":
    main()
