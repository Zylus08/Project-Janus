#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 5 Test Suite: Aspiration Windows Verification & Ablation.
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


def run_aspiration_ablation(positions: list, depth: int = 7) -> dict:
    print("=" * 80)
    print("TEST: A0 (FULL WINDOW [-INF, +INF]) VS A1 (ASPIRATION WINDOW DELTA=25cp) ABLATION")
    print("=" * 80)

    # 1. A0: Full Window (Variant X0)
    print("Running A0: Full Window [-INF, +INF]...", flush=True)
    t0_nodes, t0_time, a0_recs = 0, 0.0, []
    for pos in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value X0\nposition fen {pos['fen']}\ngo depth {depth}\nquit\n"
        t_start = time.perf_counter()
        out, _ = p.communicate(cmds, timeout=15)
        dur = time.perf_counter() - t_start
        nodes = 0
        bm = None
        for l in out.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: nodes = int(parts[parts.index("nodes")+1])
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: bm = parts[1]
        t0_nodes += nodes
        t0_time += dur
        a0_recs.append({"id": pos["id"], "nodes": nodes, "elapsed_sec": dur, "bestmove": bm})

    # 2. A1: Aspiration Window (Variant X5)
    print("Running A1: Aspiration Window (Variant X5, delta=25cp)...", flush=True)
    t1_nodes, t1_time, a1_recs = 0, 0.0, []
    total_researches = 0
    for pos in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value X5\nposition fen {pos['fen']}\ngo depth {depth}\ntelemetry_report\nquit\n"
        t_start = time.perf_counter()
        out, _ = p.communicate(cmds, timeout=15)
        dur = time.perf_counter() - t_start
        nodes = 0
        bm = None
        researches = 0
        in_tel = False
        for l in out.splitlines():
            if l.startswith("info") and "nodes" in l:
                parts = l.split()
                if "nodes" in parts: nodes = int(parts[parts.index("nodes")+1])
            elif l.startswith("bestmove"):
                parts = l.split()
                if len(parts) > 1: bm = parts[1]
            elif "TELEMETRY_START" in l: in_tel = True
            elif "TELEMETRY_END" in l: in_tel = False
            elif in_tel:
                parts = l.split()
                if len(parts) == 2 and parts[0] == "aspiration_researches":
                    researches = int(parts[1])
        t1_nodes += nodes
        t1_time += dur
        total_researches += researches
        a1_recs.append({"id": pos["id"], "nodes": nodes, "elapsed_sec": dur, "bestmove": bm, "aspiration_researches": researches})

    node_reduction_pct = ((t0_nodes - t1_nodes) / t0_nodes) * 100.0
    speedup = t0_time / max(t1_time, 0.001)

    print("\n" + "=" * 80)
    print("ASPIRATION WINDOW ABLATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"A0 (Full Window) Total Nodes : {t0_nodes:,} ({t0_time:.2f}s)")
    print(f"A1 (Aspiration) Total Nodes  : {t1_nodes:,} ({t1_time:.2f}s)")
    print(f"Node Reduction               : {node_reduction_pct:.2f}%")
    print(f"Search Speedup               : {speedup:.2f}x")
    print(f"Total Re-searches (widening) : {total_researches:,}")

    # Move consistency
    matching_moves = sum(1 for r0, r1 in zip(a0_recs, a1_recs) if r0["bestmove"] == r1["bestmove"])
    print(f"Move Agreement (A0 vs A1)    : {matching_moves} / {len(positions)} ({round((matching_moves/len(positions))*100, 1)}%)")

    out_file = RAW_DIR / "aspiration_window_raw.json"
    full_output = {
        "a0_total_nodes": t0_nodes,
        "a1_total_nodes": t1_nodes,
        "node_reduction_pct": round(node_reduction_pct, 2),
        "speedup": round(speedup, 2),
        "total_aspiration_researches": total_researches,
        "move_agreement_pct": round((matching_moves / len(positions)) * 100, 1),
        "a0_positions": a0_recs,
        "a1_positions": a1_recs
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"Wrote Aspiration Window ablation data to: {out_file}")
    return full_output


def main():
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    sample_positions = [p for p in positions if p["cat"] in ["Tactics", "KingAttack", "Endgame", "Quiet", "Closed"]][:25]
    res = run_aspiration_ablation(sample_positions, depth=7)


if __name__ == "__main__":
    main()

