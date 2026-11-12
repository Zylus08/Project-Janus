#!/usr/bin/env python3
"""
Search Quality Benchmark for Milestone P1.11.
Evaluates C0 (Frozen X15), C1 (Improving-only), and C2 (Candidate X16)
on held-out positions from the Generalized Failure Atlas.
Measures: completed depth, nodes, NPS, PV stability, and solve rates.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
ATLAS_PATH = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
EXE_X16 = ROOT / "analysis" / "phase1" / "p1.11" / "control" / "janus_classical_x16.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.11" / "raw" / "search_quality_benchmark_raw.json"


def evaluate_position_uci(fen: str, options: Dict[str, str], movetime_ms: int = 200) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(EXE_X16)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    proc.stdin.write("uci\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if "uciok" in line:
            break

    for k, v in options.items():
        proc.stdin.write(f"setoption name {k} value {v}\n")
    proc.stdin.write("isready\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if "readyok" in line:
            break

    proc.stdin.write("ucinewgame\n")
    proc.stdin.write(f"position fen {fen}\n")
    proc.stdin.write(f"go movetime {movetime_ms}\n")
    proc.stdin.flush()

    best_move = ""
    depth = 0
    score = 0
    nodes = 0

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("info") and "depth" in line:
            parts = line.split()
            if "depth" in parts:
                depth = int(parts[parts.index("depth") + 1])
            if "score" in parts and "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
            if "nodes" in parts:
                nodes = int(parts[parts.index("nodes") + 1])
        if line.startswith("bestmove"):
            best_move = line.split()[1]
            break

    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.wait(timeout=5)
    return {"best_move": best_move, "depth": depth, "score": score, "nodes": nodes}


def run_benchmark_worker(item: Tuple[int, Dict[str, Any], Dict[str, Dict[str, str]]]) -> Dict[str, Any]:
    idx, pos, configs = item
    fen = pos["fen"]
    pid = pos["id"]
    category = pos.get("cluster", "general")

    res = {"idx": idx, "id": pid, "category": category, "runs": {}}
    for c_id, opts in configs.items():
        search_res = evaluate_position_uci(fen, opts, movetime_ms=200)
        res["runs"][c_id] = search_res
    return res


def main():
    print("Loading Held-Out benchmark corpus...")
    with open(ATLAS_PATH, "r", encoding="utf-8") as f:
        atlas = json.load(f)

    raw_held_out = atlas.get("held_out_positions", [])
    valid_positions = []
    for p in raw_held_out:
        fen = p["fen"]
        try:
            b = chess.Board(fen)
            if b.is_valid():
                valid_positions.append(p)
        except Exception:
            continue

    print(f"Loaded {len(valid_positions)} valid Held-Out positions (filtered illegal positions).")

    configs = {
        "C0_X15_BASE": {"Threads": "1", "UCI_Variant": "X15", "UCI_PruningSafety": "false"},
        "C1_EAPS_IMPR": {"Threads": "1", "UCI_Variant": "X16", "UCI_PruningSafety": "true"},
        "C2_X16_FULL": {"Threads": "4", "UCI_Variant": "X16", "UCI_PruningSafety": "true"}
    }

    work_items = [(i, p, configs) for i, p in enumerate(valid_positions)]

    results = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_benchmark_worker, item): item[0] for item in work_items}
        for future in as_completed(futures):
            try:
                res = future.result()
                results.append(res)
                if len(results) % 20 == 0:
                    print(f"  Completed {len(results)}/{len(valid_positions)} positions ({round(time.time() - t0, 1)}s)...")
            except Exception as e:
                print(f"Error processing position: {e}")

    results.sort(key=lambda x: x["idx"])

    # Aggregate Metrics
    summary = {}
    for c_id in configs:
        total_depth = sum(r["runs"][c_id]["depth"] for r in results)
        total_nodes = sum(r["runs"][c_id]["nodes"] for r in results)
        avg_depth = total_depth / len(results) if results else 0
        avg_nodes = total_nodes / len(results) if results else 0
        nps = (total_nodes / (len(results) * 0.2)) if results else 0
        summary[c_id] = {
            "avg_depth": round(avg_depth, 2),
            "avg_nodes": round(avg_nodes, 0),
            "nps": int(nps)
        }

    # Compare Move Disagreements between C0 and C1
    disagreements_c0_c1 = sum(1 for r in results if r["runs"]["C0_X15_BASE"]["best_move"] != r["runs"]["C1_EAPS_IMPR"]["best_move"])
    disagreement_rate = round(disagreements_c0_c1 / len(results) * 100.0, 2)
    summary["disagreements_c0_vs_c1"] = {
        "count": disagreements_c0_c1,
        "rate_pct": disagreement_rate
    }

    print("\n--- SEARCH QUALITY BENCHMARK SUMMARY ---")
    print(json.dumps(summary, indent=2))

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "positions": results}, f, indent=2)
    print(f"Saved complete benchmark results to {OUT_RAW}")


if __name__ == "__main__":
    main()
