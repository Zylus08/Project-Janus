#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 2: TT Architecture Playing Strength Comparison
Plays a 20-game match (10 balanced opening pairs) at 1.0s + 50ms:
  Match A: T1 (Private TT 4T) vs T2 (Historical X11 Shared TT 4T)
  Match B: T4 (Smart Replacement & 64B Cluster 4T) vs T2 (Historical X11 Shared TT 4T)
"""

import sys
import os
import json
import time
import math
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
TEST_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "tests"
OPENINGS_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
EXE_T0 = TEST_DIR / "engine_t0.exe"
EXE_T1 = TEST_DIR / "engine_t1.exe"
EXE_T2 = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
EXE_T3 = TEST_DIR / "engine_t3.exe"
EXE_T4 = TEST_DIR / "engine_t4.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.7" / "raw" / "tt_matches_raw.json"

sys.path.append(str(ROOT / "analysis" / "phase1" / "p1.6" / "tests"))
from run_p16_tournaments import EngineRunner, play_pair_worker, run_parallel_tournament

def main():
    with open(OPENINGS_PATH, "r", encoding="utf-8") as f:
        openings = json.load(f)

    cfg_t1 = {"exe": EXE_T1, "name": "T1_PrivateTT_4T", "threads": 4, "is_x7": False, "is_sf": False}
    cfg_t2 = {"exe": EXE_T2, "name": "T2_SharedX11_4T", "threads": 4, "is_x7": False, "is_sf": False}
    cfg_t4 = {"exe": EXE_T4, "name": "T4_SmartPackedTT_4T", "threads": 4, "is_x7": False, "is_sf": False}

    results = {}

    # Match A: T1 (Private TT 4T) vs T2 (Shared X11 4T) - 20 games (10 pairs) at 1.0s + 50ms
    pgn_a = ROOT / "analysis" / "phase1" / "p1.7" / "pgn" / "match_t1_vs_t2.pgn"
    print("\n--- Running Match A: T1 (Private TT 4T) vs T2 (Shared X11 4T) ---")
    res_a = run_parallel_tournament(cfg_t1, cfg_t2, openings, 10, 1000, 50, pgn_a, workers=2)
    results["T1_vs_T2"] = res_a

    # Match B: T4 (Smart Packed TT 4T) vs T2 (Shared X11 4T) - 20 games (10 pairs) at 1.0s + 50ms
    pgn_b = ROOT / "analysis" / "phase1" / "p1.7" / "pgn" / "match_t4_vs_t2.pgn"
    print("\n--- Running Match B: T4 (Smart Packed TT 4T) vs T2 (Shared X11 4T) ---")
    res_b = run_parallel_tournament(cfg_t4, cfg_t2, openings, 10, 1000, 50, pgn_b, workers=2)
    results["T4_vs_T2"] = res_b

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] TT Playing Strength matches saved to {RAW_OUT}")

if __name__ == "__main__":
    main()

