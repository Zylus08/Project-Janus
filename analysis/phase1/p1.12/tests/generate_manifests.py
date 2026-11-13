#!/usr/bin/env python3
"""
Generate experiment_manifest.json and sha256_manifest.json for Milestone P1.12.
"""

import os
import json
import hashlib
import time
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P112_DIR = ROOT / "analysis" / "phase1" / "p1.12"
DOCS_REPORT = ROOT / "docs" / "phase1" / "p1.12_report.md"
ENGINE_CPP = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
ENGINE_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"

def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    # 1. SHA-256 Manifest
    sha_manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "milestone": "P1.12",
        "description": "Cryptographic SHA-256 digest catalog for all Milestone P1.12 deliverables and binaries",
        "files": {}
    }

    # Collect files in p1.12
    files_to_hash = [DOCS_REPORT, ENGINE_CPP, ENGINE_EXE]
    for p in P112_DIR.rglob("*"):
        if p.is_file() and not p.name.endswith(".manifest.json") and not p.name.endswith(".obj") and not p.name.endswith(".lib") and not p.name.endswith(".exp"):
            files_to_hash.append(p)

    # External reference tools
    sf11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")
    sf19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")
    if sf11.exists(): files_to_hash.append(sf11)
    if sf19.exists(): files_to_hash.append(sf19)

    for fpath in sorted(set(files_to_hash)):
        rel = str(fpath.relative_to(ROOT)) if fpath.is_relative_to(ROOT) else str(fpath)
        sha_manifest["files"][rel] = {
            "sha256": get_sha256(fpath),
            "size_bytes": fpath.stat().st_size
        }

    sha_path = P112_DIR / "sha256_manifest.json"
    with open(sha_path, "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"SHA-256 manifest written to: {sha_path} ({len(sha_manifest['files'])} files)")

    # 2. Experiment Manifest
    exp_manifest = {
        "milestone": "P1.12",
        "title": "Classical Baseline Reboot, Search Decision Reliability & Competitive Calibration",
        "date": "2026-11-13",
        "authoritative_baselines": {
            "single_thread": {
                "name": "Janus Classical X7",
                "commit": "b34e342",
                "sha256": "86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe"
            },
            "four_thread": {
                "name": "Janus Classical X12",
                "commit": "78ca3d5",
                "sha256": "00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe"
            }
        },
        "frozen_candidate": {
            "name": "Janus Classical X17",
            "sha256": "04c17f68ef4fc327bf3443b60b61ac23a40c6e985c1af5caedb5c42b42ac684a",
            "binary_path": "analysis/phase1/p1.12/control/janus_classical_x17.exe",
            "source_path": "analysis/phase1/p1.12/control/janus_classical_x17.cpp",
            "status": "Archived Research Platform (Statistical Parity Certified)"
        },
        "external_benchmarks": {
            "tier_2": {
                "name": "Stockfish 11 64",
                "tag": "sf_11",
                "commit": "c3483fa9a7d7c0ffa9fcc32b467ca844cfb63790",
                "sha256": "b004c03bd71bb84e8bc1832c580e72a7e883f121e1834ea6da2802d1575e8048",
                "role": "Historical Classical Non-NNUE Peak Ceiling"
            },
            "tier_3": {
                "name": "Stockfish 19",
                "commit": "edb0d9df8bc7c570f72365ee3d12d0985a72dfca",
                "sha256": "660eb009241b9c97ebfbcf9f4d2f8cb20d43f0545f1b138fe9738c642646399e",
                "role": "Modern Super-GM NNUE Domain Ceiling"
            }
        },
        "tournament_matches": {
            "match1": {
                "description": "Janus Classical X17-S (1T) vs Janus Classical X7 (1T)",
                "time_control": "1.0s + 50ms",
                "games": 100,
                "score": "33W - 37D - 30L (51.5%)",
                "elo_delta": "+10.4 [-57.3, +78.1]",
                "pgn": "analysis/phase1/p1.12/pgn/x17_1t_vs_x7_1t.pgn"
            },
            "match2": {
                "description": "Janus Classical X17-S (1T) vs Janus Classical X7 (1T) Slow TC",
                "time_control": "2.5s + 100ms",
                "games": 50,
                "score": "15W - 20D - 15L (50.0%)",
                "elo_delta": "0.0 [-95.1, +95.1]",
                "pgn": "analysis/phase1/p1.12/pgn/x17_1t_vs_x7_1t_slow.pgn"
            },
            "match3": {
                "description": "Janus Classical X17-P (4T) vs Janus Classical X12 (4T)",
                "time_control": "1.0s + 50ms",
                "games": 100,
                "score": "33W - 34D - 33L (50.0%)",
                "elo_delta": "0.0 [-67.7, +67.7]",
                "pgn": "analysis/phase1/p1.12/pgn/x17_4t_vs_x12_4t.pgn"
            },
            "match4": {
                "description": "Janus Classical X17-S (1T) vs Stockfish 11 (1T)",
                "time_control": "1.5s + 50ms",
                "games": 40,
                "score": "0W - 0D - 40L (0.0%)",
                "elo_delta": "Unbounded (< -800)",
                "pgn": "analysis/phase1/p1.12/pgn/x17_1t_vs_sf11_1t.pgn"
            },
            "match5": {
                "description": "Janus Classical X17-P (4T) vs Stockfish 11 (4T)",
                "time_control": "1.5s + 50ms",
                "games": 40,
                "score": "0W - 0D - 40L (0.0%)",
                "elo_delta": "Unbounded (< -800)",
                "pgn": "analysis/phase1/p1.12/pgn/x17_4t_vs_sf11_4t.pgn"
            },
            "match6": {
                "description": "Janus Classical X17-S (1T) vs Stockfish 19 (1T)",
                "time_control": "1.5s + 50ms",
                "games": 40,
                "score": "0W - 4D - 36L (5.0%)",
                "elo_delta": "-511.5 [-741.4, -281.6]",
                "pgn": "analysis/phase1/p1.12/pgn/x17_1t_vs_sf19_1t.pgn"
            },
            "match7": {
                "description": "Janus Classical X17-P (4T) vs Stockfish 19 (4T)",
                "time_control": "1.5s + 50ms",
                "games": 40,
                "score": "0W - 0D - 40L (0.0%)",
                "elo_delta": "Unbounded (< -800)",
                "pgn": "analysis/phase1/p1.12/pgn/x17_4t_vs_sf19_4t.pgn"
            }
        },
        "final_decision": "CATEGORY D: BASELINE REBOOT (Janus Classical X7 and X12 Retained as Authoritative Baselines)"
    }

    exp_path = P112_DIR / "experiment_manifest.json"
    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Experiment manifest written to: {exp_path}")

if __name__ == "__main__":
    main()

