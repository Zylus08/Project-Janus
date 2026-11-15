#!/usr/bin/env python3
"""
build_engine_configuration_ledger.py
Generates machine-readable engine configuration ledger for X7, X12, X22, X24, X25, and active engine.
Computes source and binary SHA-256 hashes, records compile flags, evaluation features, and search constants.
"""

import os
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "engine_configuration_ledger.json"

def sha256_file(p: Path) -> str:
    if not p.exists():
        return "NOT_FOUND"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    ledger = {
        "milestone": "P1.21",
        "description": "Frozen Engine Reconstruction & Machine-Readable Configuration Ledger",
        "engines": {
            "x7": {
                "designation": "Janus Classical X7 (Single-Thread Strength Baseline)",
                "commit": "b34e342",
                "role": "Frozen Qualified 1T Strength Control",
                "binary_path": "analysis/phase1/p1.3/control/janus_classical_x7.exe",
                "binary_sha256": sha256_file(ROOT / "analysis/phase1/p1.3/control/janus_classical_x7.exe"),
                "binary_bytes": (ROOT / "analysis/phase1/p1.3/control/janus_classical_x7.exe").stat().st_size,
                "compiler": "MSVC cl.exe (VS 2022 BuildTools)",
                "compile_flags": "/O2 /Ot /Oi /std:c++17 /EHsc",
                "threads": 1,
                "eval_function": "Classical Handcrafted (PST, Mobility, Basic Pawns, King Safety)",
                "eval_toggles": {
                    "backward_pawns": False,
                    "connected_passers_v2": False,
                    "king_file_exposure": False,
                    "true_outposts": False
                },
                "qsearch": "Legacy Q0 (Stand-pat check defect present)",
                "rfp": "Enabled (margin = 120 * depth)",
                "null_move": "Enabled (R=3)",
                "lmr": "Enabled (Legacy table)",
                "lmp": "Disabled",
                "tt_size": "Standard (16-byte entries, XOR hash)",
                "pawn_hash": "Disabled (Computed dynamically in eval)",
                "time_mgmt": "Standard Fischer increment allocation"
            },
            "x12": {
                "designation": "Janus Classical X12 (Four-Thread SMP Strength Baseline)",
                "commit": "78ca3d5",
                "role": "Frozen Qualified 4T SMP Strength Control",
                "binary_path": "analysis/phase1/p1.7/control/janus_classical_x12.exe",
                "binary_sha256": sha256_file(ROOT / "analysis/phase1/p1.7/control/janus_classical_x12.exe"),
                "binary_bytes": (ROOT / "analysis/phase1/p1.7/control/janus_classical_x12.exe").stat().st_size,
                "compiler": "MSVC cl.exe (VS 2022 BuildTools)",
                "compile_flags": "/O2 /Ot /Oi /std:c++17 /EHsc",
                "threads": 4,
                "eval_function": "Classical Handcrafted E10 Enhanced",
                "eval_toggles": {
                    "backward_pawns": False,
                    "connected_passers_v2": False,
                    "king_file_exposure": False,
                    "true_outposts": False
                },
                "qsearch": "Legacy Q0 (Stand-pat check defect present)",
                "rfp": "Enabled (margin = 90 * depth)",
                "null_move": "Enabled (R=3)",
                "lmr": "Enabled (SMP calibrated)",
                "lmp": "Enabled (Conservative quadratic LMP)",
                "tt_size": "Shared SMP lockless / XOR verified",
                "pawn_hash": "Disabled",
                "time_mgmt": "Dynamic SMP time management"
            },
            "x22": {
                "designation": "Janus Classical X22 (Correctness-Preserving Research Reference)",
                "commit": "e33f292",
                "role": "Authoritative Research Reference Foundation",
                "binary_path": "analysis/phase1/p1.17/control/janus_classical_x22.exe",
                "binary_sha256": sha256_file(ROOT / "analysis/phase1/p1.17/control/janus_classical_x22.exe"),
                "binary_bytes": (ROOT / "analysis/phase1/p1.17/control/janus_classical_x22.exe").stat().st_size,
                "source_path": "analysis/phase1/p1.17/control/janus_classical_x22.cpp",
                "source_sha256": sha256_file(ROOT / "analysis/phase1/p1.17/control/janus_classical_x22.cpp"),
                "source_lines": 5913,
                "compiler": "MSVC cl.exe (VS 2022 BuildTools)",
                "compile_flags": "/O2 /Ot /Oi /std:c++17 /EHsc",
                "threads": 1,
                "eval_function": "Handcrafted E5 (1T) / E10 (4T) with True Outposts & 64K Pawn Table",
                "eval_toggles": {
                    "backward_pawns": False,
                    "connected_passers_v2": False,
                    "king_file_exposure": False,
                    "true_outposts": True
                },
                "qsearch": "Corrected Q1 (Legal check evasions, stand-pat suppressed in check, SEE capture pruning)",
                "rfp": "Enabled (margin: 1T=120*depth, 4T=90*depth)",
                "null_move": "Enabled (R=3)",
                "lmr": "Calibrated L3 table with endgame pawn protection",
                "lmp": "Disabled for 1T; quadratic for 4T",
                "tt_size": "16-byte aligned entries with XOR key verification",
                "pawn_hash": "64K entry direct-mapped pawn transposition table (+13.58% speedup)",
                "time_mgmt": "Standard (1T) / Dynamic (4T)"
            },
            "x24": {
                "designation": "Janus Classical X24 (P1.19 Candidate: Track A Backward Pawns Isolated)",
                "commit": "bcf8f4c",
                "role": "Archived Research Candidate (Rejected)",
                "binary_path": "analysis/phase1/p1.19/control/janus_classical_x24.exe",
                "binary_sha256": sha256_file(ROOT / "analysis/phase1/p1.19/control/janus_classical_x24.exe"),
                "binary_bytes": (ROOT / "analysis/phase1/p1.19/control/janus_classical_x24.exe").stat().st_size,
                "source_path": "analysis/phase1/p1.19/control/janus_classical_x24.cpp",
                "source_sha256": sha256_file(ROOT / "analysis/phase1/p1.19/control/janus_classical_x24.cpp"),
                "source_lines": 6068,
                "compiler": "MSVC cl.exe (VS 2022 BuildTools)",
                "compile_flags": "/O2 /Ot /Oi /std:c++17 /EHsc",
                "threads": 1,
                "eval_function": "Handcrafted E5/E10 + Isolated Backward Pawn Penalty (-10 mg / -15 eg)",
                "eval_toggles": {
                    "backward_pawns": True,
                    "connected_passers_v2": False,
                    "king_file_exposure": False,
                    "true_outposts": True
                },
                "qsearch": "Corrected Q1 (Identical to X22)",
                "rfp": "Enabled (Identical to X22: 120*depth for 1T, 90*depth for 4T)",
                "null_move": "Enabled (Identical to X22: R=3)",
                "lmr": "Calibrated L3 (Identical to X22)",
                "lmp": "Identical to X22",
                "tt_size": "Identical to X22",
                "pawn_hash": "64K entry direct-mapped pawn hash (Identical to X22)",
                "time_mgmt": "Identical to X22"
            },
            "x25": {
                "designation": "Janus Classical X25 (P1.20 Candidate: Option B Connected Passed Pawns)",
                "commit": "c232730",
                "role": "Certified Dynamic Evaluation Candidate",
                "binary_path": "analysis/phase1/p1.20/control/janus_classical_x25.exe",
                "binary_sha256": sha256_file(ROOT / "analysis/phase1/p1.20/control/janus_classical_x25.exe"),
                "binary_bytes": (ROOT / "analysis/phase1/p1.20/control/janus_classical_x25.exe").stat().st_size,
                "source_path": "analysis/phase1/p1.20/control/janus_classical_x25.cpp",
                "source_sha256": sha256_file(ROOT / "analysis/phase1/p1.20/control/janus_classical_x25.cpp"),
                "source_lines": 6181,
                "compiler": "MSVC cl.exe (VS 2022 BuildTools)",
                "compile_flags": "/O2 /Ot /Oi /std:c++17 /EHsc",
                "threads": 1,
                "eval_function": "Handcrafted E5/E10 + Option B Connected/Supported Passers (+30/+55 advanced, +20/+35 base)",
                "eval_toggles": {
                    "backward_pawns": False,
                    "connected_passers_v2": True,
                    "king_file_exposure": False,
                    "true_outposts": True
                },
                "qsearch": "Corrected Q1 (Identical to X22)",
                "rfp": "Enabled (Identical to X22: 120*depth for 1T, 90*depth for 4T)",
                "null_move": "Enabled (Identical to X22: R=3)",
                "lmr": "Calibrated L3 (Identical to X22)",
                "lmp": "Identical to X22",
                "tt_size": "Identical to X22",
                "pawn_hash": "64K entry direct-mapped pawn hash (Identical to X22)",
                "time_mgmt": "Identical to X22"
            }
        },
        "search_and_pruning_invariants": {
            "x22_x24_x25_search_parity": "100% Bitwise Identical Search Engine Code",
            "differing_subsystems": "Positional evaluation terms and UCI option wrappers ONLY",
            "rfp_formula": "if (depth <= 3 && !in_check && static_eval - rfp_margin_per_depth * depth >= beta) return static_eval - rfp_margin_per_depth * depth;",
            "rfp_margins": {
                "1_thread": "120 cp per depth (depth 1 = 120, depth 2 = 240, depth 3 = 360)",
                "4_thread": "90 cp per depth (depth 1 = 90, depth 2 = 180, depth 3 = 270)"
            },
            "null_move_formula": "if (depth >= 3 && !in_check && non_pawn_material(us) > 0 && static_eval >= beta) { search with R=3 }",
            "lmr_formula": "if (depth >= 3 && move_count >= 4 && !is_capture && !in_check && !gives_check) { reduction = lmr_table[depth][move_count] }"
        }
    }
    
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    print(f"Machine-readable ledger written to {OUT_RAW}")

if __name__ == "__main__":
    main()
