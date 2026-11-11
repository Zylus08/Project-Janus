#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 1: Atlas Corpus Evaluation and Failure Classification
Evaluates 240 positions across X7, X10, X12, X13, and SF19 under 500ms fixed budget.
"""

import sys
import os
import json
import time
import re
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path("E:/ChessXML/project-janus-phase1")
CORPUS_PATH = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.9" / "raw" / "generalized_failure_atlas_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X13 = ROOT / "analysis" / "phase1" / "p1.8" / "control" / "janus_classical_x13.exe"
EXE_SF  = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

ENGINES = [
    {"id": "X7_1T",  "exe": EXE_X7,  "threads": 1, "is_sf": False},
    {"id": "X10_1T", "exe": EXE_X10, "threads": 1, "is_sf": False},
    {"id": "X12_4T", "exe": EXE_X12, "threads": 4, "is_sf": False},
    {"id": "X13_4T", "exe": EXE_X13, "threads": 4, "is_sf": False},
    {"id": "SF19_4T","exe": EXE_SF,  "threads": 4, "is_sf": True}
]

def run_single_engine(exe, fen, movetime_ms, threads, is_sf=False):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=15)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None
    score_cp = 0

    for line in out.splitlines():
        if line.startswith("info depth"):
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            m_m = re.search(r'score mate (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
            elif m_m: score_cp = 10000 if int(m_m.group(1)) > 0 else -10000
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "depth": depth,
        "nodes": nodes,
        "score_cp": score_cp,
        "bestmove": bestmove,
        "nps": nps,
        "elapsed_s": round(dur, 4)
    }

def eval_position_task(pos_item):
    pid = pos_item["id"]
    fen = pos_item["fen"]
    theme = pos_item.get("theme", "general")
    partition = pos_item.get("partition", "DEV")
    sol = pos_item.get("solution", None)

    pos_res = {
        "id": pid,
        "partition": partition,
        "theme": theme,
        "fen": fen,
        "solution": sol,
        "engines": {}
    }

    for eng in ENGINES:
        eid = eng["id"]
        res = run_single_engine(eng["exe"], fen, 350, eng["threads"], eng["is_sf"])
        pos_res["engines"][eid] = res

    # Classify failure category for X13 relative to SF19 or solution
    sf_res = pos_res["engines"]["SF19_4T"]
    x13_res = pos_res["engines"]["X13_4T"]
    x12_res = pos_res["engines"]["X12_4T"]
    target_move = sol if sol else sf_res["bestmove"]

    if x13_res["bestmove"] == target_move:
        primary_cat = "SOLVED"
    elif "endgame" in theme or "pawn_endgame" in theme or "rook_endgame" in theme or "minor_piece_endgame" in theme:
        primary_cat = "F6" # Endgame knowledge / horizon error
    elif "tactical" in theme or "forced" in theme or abs(sf_res["score_cp"]) > 300:
        if x13_res["depth"] < sf_res["depth"] - 4:
            primary_cat = "F2" # Search horizon / tactical miss
        else:
            primary_cat = "F3" # Selective pruning error
    elif abs(x13_res["score_cp"] - sf_res["score_cp"]) > 150:
        primary_cat = "F1" # Static evaluation error / positional blindness
    else:
        primary_cat = "F7" # Interacting / Multi-Cause

    pos_res["failure_category"] = primary_cat
    return pos_res

def main():
    print("=== PROJECT JANUS P1.9: PHASE 1 ATLAS EVALUATION MATRIX (240 POSITIONS) ===")
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    all_positions = corpus["dev_positions"] + corpus["held_out_positions"]
    print(f"Total positions to evaluate: {len(all_positions)} across 5 engines (350ms budget)...")

    results_by_id = {}
    cat_counts = {"SOLVED": 0, "F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0, "F7": 0}
    t0 = time.time()

    # Use 4 parallel workers
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(eval_position_task, pos): pos["id"] for pos in all_positions}
        completed = 0
        for fut in as_completed(futures):
            r = fut.result()
            results_by_id[r["id"]] = r
            cat = r["failure_category"]
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            completed += 1
            if completed % 20 == 0 or completed == len(all_positions):
                print(f"  Completed {completed}/{len(all_positions)} positions [{(time.time()-t0):.1f}s]")

    # Aggregate partition statistics
    dev_results = [r for r in results_by_id.values() if r["partition"] == "DEV"]
    held_results = [r for r in results_by_id.values() if r["partition"] == "HELD_OUT"]

    dev_cats = Counter(r["failure_category"] for r in dev_results)
    held_cats = Counter(r["failure_category"] for r in held_results)

    summary = {
        "metadata": {
            "title": "Phase 1: 240-Position Generalized Failure Atlas Evaluation",
            "total_positions": len(all_positions),
            "dev_count": len(dev_results),
            "held_out_count": len(held_results),
            "duration_sec": round(time.time() - t0, 2)
        },
        "overall_categories": cat_counts,
        "dev_categories": dict(dev_cats),
        "held_out_categories": dict(held_cats),
        "positions": results_by_id
    }

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[DONE] Saved evaluation results to {RAW_OUT}")
    print("\n--- FAILURE DISTRIBUTION ACROSS 240 POSITIONS ---")
    total_failures = len(all_positions) - cat_counts.get("SOLVED", 0)
    for c, cnt in sorted(cat_counts.items()):
        pct = (cnt / total_failures * 100.0) if total_failures > 0 and c != "SOLVED" else (cnt / len(all_positions) * 100.0)
        label = "Total Positions" if c == "SOLVED" else "Of All Failures"
        print(f"  {c}: {cnt} ({pct:.1f}% {label})")

if __name__ == "__main__":
    from collections import Counter
    main()

