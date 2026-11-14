#!/usr/bin/env python3
"""
generate_manifests.py
Milestone P1.19: Generates authoritative experiment_manifest.json and sha256_manifest.json.
"""

import os
import json
import hashlib
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P119_DIR = ROOT / "analysis" / "phase1" / "p1.19"
DOCS_REPORT = ROOT / "docs" / "phase1" / "p1.19_report.md"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def generate_experiment_manifest():
    manifest = {
        "milestone": "P1.19",
        "title": "Backward-Pawn Evaluation Isolation, Pawn-Hash Integrity & Statistically Powered Classical Strength Qualification",
        "governing_charter": "Strictly Non-ML Classical Computer Chess Architecture",
        "branch": "phase1/classical-janus",
        "parent_commit": "bb87254",
        "frozen_baselines": {
            "x7_single_thread": {
                "commit": "b34e342",
                "path": "analysis/phase1/p1.3/control/janus_classical_x7.exe",
                "sha256": "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B"
            },
            "x12_four_thread": {
                "commit": "78ca3d5",
                "path": "analysis/phase1/p1.7/control/janus_classical_x12.exe",
                "sha256": "00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059"
            },
            "x22_research_reference": {
                "commit": "e33f292",
                "path": "analysis/phase1/p1.17/control/janus_classical_x22.exe",
                "sha256": "35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C"
            },
            "x23_rejected_candidate": {
                "commit": "bb87254",
                "path": "analysis/phase1/p1.18/control/janus_classical_x23.exe",
                "sha256": "39E875841B36AC82F464ABC7F31DB19D7CF5ABCD0F15B0A923B086A5BB393E39"
            }
        },
        "candidate": {
            "name": "Janus Classical Candidate X24",
            "tracks": {
                "track_s": "X24-S (Single-Thread 1T, E5 Combined Evaluation)",
                "track_p": "X24-P (Four-Thread 4T SMP, E10 Enhanced Evaluation)"
            },
            "features": [
                "Track A Isolated: Classical Backward Pawn Detection (-10 mg / -15 eg) with 64K Pawn Hash Caching",
                "Track B Excised: King File Exposure Penalty Permanently Disabled (0 mg / 0 eg)",
                "Corrected Quiescence Search (Q1) with Legal In-Check Evasions & Stand-Pat Suppression",
                "64K Direct-Mapped Pawn Table with 100% Cache Invariance and +13.58% Evaluation Acceleration"
            ],
            "artifacts": {
                "exe": {
                    "path": "analysis/phase1/p1.19/control/janus_classical_x24.exe",
                    "sha256": "D8BE5521B91A353C7C4D2E8BAD51AF008147B3FD11989C2055780CE4ED91981F"
                },
                "dll": {
                    "path": "analysis/phase1/p1.19/control/janus_classical_x24.dll",
                    "sha256": "B6EC9E806E20DC22664043557677796E11FCAFF800B42B4E4DBDC75C5BA899B1"
                },
                "cpp": {
                    "path": "analysis/phase1/p1.19/control/janus_classical_x24.cpp",
                    "sha256": "3A1A5C854C836AAEE9A5EC586983D0A46A2A28C588A986FC412915079023F9D8"
                }
            }
        },
        "external_benchmarks": {
            "stockfish_4": {
                "era": "2014 Classical",
                "path": "tools/stockfish_4/stockfish_4.exe",
                "sha256": "1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674"
            },
            "stockfish_11": {
                "era": "2020 Peak Classical",
                "path": "tools/stockfish_11/stockfish_11.exe",
                "sha256": "B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048"
            },
            "stockfish_19": {
                "era": "2026 SOTA NNUE",
                "path": "tools/stockfish/stockfish.exe",
                "sha256": "45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0"
            }
        },
        "tournament_summary": {
            "total_games": 570,
            "development_games": 100,
            "authoritative_tournament_games": 470,
            "matches": {
                "dev_match": {
                    "opponent": "Reference X22-S",
                    "tc": "0.5s + 20ms",
                    "score": "45.5 / 100",
                    "win_rate": 45.5,
                    "elo": -31.4,
                    "ci_95": [36.6, 54.4],
                    "p_value_two_sided": 0.3233
                },
                "match_1": {
                    "opponent": "Reference X22-S",
                    "tc": "1.0s + 50ms",
                    "score": "48.0 / 100",
                    "win_rate": 48.0,
                    "elo": -13.9,
                    "ci_95": [39.62, 56.38],
                    "p_value_two_sided": 0.6400,
                    "verdict": "Parity / Fail"
                },
                "match_2": {
                    "opponent": "Baseline X7 (1T)",
                    "tc": "1.0s + 50ms",
                    "score": "48.0 / 100",
                    "win_rate": 48.0,
                    "elo": -13.9,
                    "ci_95": [41.46, 54.54],
                    "p_value_two_sided": 0.5491,
                    "verdict": "Baseline Retained"
                },
                "match_3": {
                    "opponent": "Baseline X12 (4T)",
                    "tc": "1.0s + 50ms",
                    "score": "47.0 / 100",
                    "win_rate": 47.0,
                    "elo": -20.9,
                    "ci_95": [38.76, 55.24],
                    "p_value_two_sided": 0.4755,
                    "verdict": "Baseline Retained"
                },
                "match_4": {
                    "opponent": "Baseline X7 (Slow TC)",
                    "tc": "3.0s + 100ms",
                    "score": "18.5 / 50",
                    "win_rate": 37.0,
                    "elo": -92.5,
                    "ci_95": [26.75, 47.25],
                    "p_value_two_sided": 0.0129,
                    "verdict": "Statistically Significant Regression"
                },
                "match_5": {
                    "opponent": "Stockfish 4",
                    "tc": "1.5s + 50ms",
                    "score": "0.0 / 40",
                    "win_rate": 0.0,
                    "elo": None,
                    "ci_95": [0.0, 0.0],
                    "p_value_two_sided": 0.0
                },
                "match_6": {
                    "opponent": "Stockfish 11",
                    "tc": "1.5s + 50ms",
                    "score": "1.0 / 40",
                    "win_rate": 2.5,
                    "elo": -636.4,
                    "ci_95": [0.0, 5.87],
                    "p_value_two_sided": 0.0
                },
                "match_7": {
                    "opponent": "Stockfish 19",
                    "tc": "1.5s + 50ms",
                    "score": "2.5 / 40",
                    "win_rate": 6.25,
                    "elo": -470.4,
                    "ci_95": [1.38, 11.12],
                    "p_value_two_sided": 0.0
                }
            }
        },
        "regulatory_decision": {
            "verdict": "CATEGORY C — REJECTED CANDIDATE",
            "active_research_reference": "Janus Classical X22 (e33f292)",
            "qualified_1t_baseline": "Janus Classical X7 (b34e342)",
            "qualified_4t_baseline": "Janus Classical X12 (78ca3d5)",
            "disposition_track_a": "Deactivated by default (g_use_backward_pawns = 0)",
            "disposition_track_b": "Permanently Excised (g_use_king_file_exposure = 0)",
            "disposition_pawn_hash": "Retained and Verified (+13.58% eval acceleration)",
            "disposition_quiescence": "Retained and Verified (Q1 legal in-check evasions)"
        }
    }

    out_path = P119_DIR / "experiment_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {out_path}")

def generate_sha256_manifest():
    files_to_hash = []

    # All files in analysis/phase1/p1.19/
    for p in sorted(P119_DIR.rglob("*")):
        if p.is_file() and p.name not in ["sha256_manifest.json", "generate_manifests.py"]:
            # Exclude temporary compile objects if any
            if not p.name.endswith((".obj", ".exp", ".lib")):
                files_to_hash.append(p)

    # Master report
    if DOCS_REPORT.exists():
        files_to_hash.append(DOCS_REPORT)

    manifest = {}
    for p in sorted(files_to_hash):
        rel_path = p.relative_to(ROOT).as_posix()
        manifest[rel_path] = sha256_file(p)

    out_path = P119_DIR / "sha256_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {out_path} ({len(manifest)} files tracked)")

def main():
    generate_experiment_manifest()
    generate_sha256_manifest()

if __name__ == "__main__":
    main()
