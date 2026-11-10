#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 6 Test Suite: Controlled Search Integration Matrix (Variants X0 through X6).
Evaluates all individual search modernizations and the combined candidate engine.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
SUITE_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.1" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

VARIANTS = [
    ("X0", "C1 Baseline Equivalent (All flags OFF)"),
    ("X1", "Staged Move Generation Only"),
    ("X2", "Quiescence SEE Filtering Only (Mode 2)"),
    ("X3", "Null-Move Pruning Only (R=3)"),
    ("X4", "Reverse Futility Pruning Only (80*d)"),
    ("X5", "Aspiration Windows Only (delta=25cp)"),
    ("X6", "Full Integrated Modernized Candidate (All Active)")
]


def run_single_variant_fixed_depth(variant: str, positions: list, depth: int = 7) -> dict:
    total_nodes = 0
    total_time = 0.0
    results = []

    for pos in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value {variant}\nposition fen {pos['fen']}\ngo depth {depth}\nquit\n"
        t0 = time.perf_counter()
        out, _ = p.communicate(cmds, timeout=20)
        dur = time.perf_counter() - t0
        
        nodes = 0
        nps = 0
        bm = None
        score = 0
        for l in out.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: nodes = int(parts[parts.index("nodes")+1])
                if "nps" in parts: nps = int(parts[parts.index("nps")+1])
                if "cp" in parts: score = int(parts[parts.index("cp")+1])
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: bm = parts[1]
                
        total_nodes += nodes
        total_time += dur
        results.append({
            "id": pos["id"],
            "nodes": nodes,
            "elapsed_sec": dur,
            "nps": nps,
            "score_cp": score,
            "bestmove": bm
        })

    # Effective Branching Factor (EBF) approximation: nodes^(1/depth)
    ebf = (total_nodes / max(len(positions), 1)) ** (1.0 / max(depth, 1))

    return {
        "variant": variant,
        "total_nodes": total_nodes,
        "elapsed_sec": total_time,
        "nps": int(total_nodes / max(total_time, 0.001)),
        "ebf": round(ebf, 3),
        "positions": results
    }


def run_single_variant_fixed_time(variant: str, positions: list, movetime_ms: int = 250) -> dict:
    total_nodes = 0
    total_depth = 0
    total_time = 0.0
    results = []

    for pos in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value {variant}\nposition fen {pos['fen']}\ngo movetime {movetime_ms}\nquit\n"
        t0 = time.perf_counter()
        out, _ = p.communicate(cmds, timeout=10)
        dur = time.perf_counter() - t0
        
        nodes = 0
        nps = 0
        depth = 0
        bm = None
        score = 0
        for l in out.splitlines():
            if l.startswith("info") and "depth" in l:
                parts = l.split()
                if "depth" in parts: depth = int(parts[parts.index("depth")+1])
                if "nodes" in parts: nodes = int(parts[parts.index("nodes")+1])
                if "nps" in parts: nps = int(parts[parts.index("nps")+1])
                if "cp" in parts: score = int(parts[parts.index("cp")+1])
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: bm = parts[1]
                
        total_nodes += nodes
        total_depth += depth
        total_time += dur
        results.append({
            "id": pos["id"],
            "depth": depth,
            "nodes": nodes,
            "elapsed_sec": dur,
            "nps": nps,
            "score_cp": score,
            "bestmove": bm
        })

    avg_depth = round(total_depth / max(len(positions), 1), 2)
    return {
        "variant": variant,
        "movetime_ms": movetime_ms,
        "avg_depth": avg_depth,
        "total_nodes": total_nodes,
        "elapsed_sec": total_time,
        "nps": int(total_nodes / max(total_time, 0.001)),
        "positions": results
    }


def main():
    print("=" * 80)
    print("PHASE 6: CONTROLLED SEARCH INTEGRATION MATRIX (VARIANTS X0 - X6)")
    print("=" * 80)

    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        all_positions = json.load(f)
    sample_positions = [p for p in all_positions if p["cat"] in ["Tactics", "KingAttack", "Endgame", "Quiet", "Closed"]][:25]

    matrix_depth_results = {}
    print("\n--- PART A: FIXED-DEPTH (DEPTH 7) EVALUATION ---")
    for var_code, desc in VARIANTS:
        print(f"Testing {var_code}: {desc}...", flush=True)
        res = run_single_variant_fixed_depth(var_code, sample_positions, depth=7)
        matrix_depth_results[var_code] = res
        print(f"  -> Nodes: {res['total_nodes']:,} | Time: {res['elapsed_sec']:.2f}s | EBF: {res['ebf']} | NPS: {res['nps']:,}")

    matrix_time_results = {}
    print("\n--- PART B: FIXED-TIME (250 ms/pos) EVALUATION ---")
    for var_code, desc in VARIANTS:
        print(f"Testing {var_code}: {desc} (250ms/pos)...", flush=True)
        res = run_single_variant_fixed_time(var_code, sample_positions, movetime_ms=250)
        matrix_time_results[var_code] = res
        print(f"  -> Avg Depth: {res['avg_depth']} | Total Nodes: {res['total_nodes']:,} | NPS: {res['nps']:,}")

    # Summary table
    base_nodes = matrix_depth_results["X0"]["total_nodes"]
    base_time = matrix_depth_results["X0"]["elapsed_sec"]
    base_depth = matrix_time_results["X0"]["avg_depth"]

    print("\n" + "=" * 80)
    print("INTEGRATION MATRIX FINAL SUMMARY")
    print("=" * 80)
    print(f"{'Var':<4} | {'Description':<38} | {'Nodes (d=7)':<12} | {'Node Red%':<10} | {'Speedup':<8} | {'EBF':<6} | {'Avg D (250ms)':<12}")
    print("-" * 105)

    summary_table = []
    for var_code, desc in VARIANTS:
        d_res = matrix_depth_results[var_code]
        t_res = matrix_time_results[var_code]
        red_pct = round(((base_nodes - d_res["total_nodes"]) / base_nodes) * 100.0, 1)
        speedup = round(base_time / max(d_res["elapsed_sec"], 0.001), 2)
        print(f"{var_code:<4} | {desc:<38} | {d_res['total_nodes']:<12,f} | {f'{red_pct}%':<10} | {f'{speedup}x':<8} | {d_res['ebf']:<6} | {t_res['avg_depth']:<12}")
        summary_table.append({
            "variant": var_code,
            "description": desc,
            "depth_7_nodes": d_res["total_nodes"],
            "depth_7_time_sec": round(d_res["elapsed_sec"], 2),
            "node_reduction_pct": red_pct,
            "speedup": speedup,
            "ebf": d_res["ebf"],
            "fixed_time_avg_depth": t_res["avg_depth"]
        })

    out_file = RAW_DIR / "search_integration_matrix_raw.json"
    full_output = {
        "summary": summary_table,
        "fixed_depth_results": matrix_depth_results,
        "fixed_time_results": matrix_time_results
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"\nWrote full integration matrix data to: {out_file}")


if __name__ == "__main__":
    main()

