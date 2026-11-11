#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 4: Parallel Root Result & Concurrency Time Management Audit
Tests clock compliance, latency, and root result integrity across:
  Budgets: 50ms, 100ms, 250ms, 400ms, 1000ms, 3000ms
  Engines: X11 1T, X11 4T, and X12-Candidate (W4+T4) 4T
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
TEST_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "tests"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.7" / "raw" / "root_clock_audit_raw.json"

EXE_X11 = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
EXE_W4  = TEST_DIR / "engine_w4.exe"

BUDGETS_MS = [50, 100, 250, 400, 1000, 3000]

TEST_POSITIONS = [
    {"name": "startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"name": "kiwipete", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"},
    {"name": "pos3_endgame", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"},
    {"name": "sharp_sicilian", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6"},
    {"name": "king_safety_sharp", "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15"}
]

def run_clock_test(exe, fen, movetime_ms, threads):
    cmds = f"uci\nsetoption name Threads value {threads}\nisready\nposition fen {fen}\ngo movetime {movetime_ms}\nquit\n"
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate(cmds, timeout=15)
    wall_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    bestmove = None
    depth = 0
    engine_time_ms = 0
    nodes = 0
    pv_moves = []

    for line in out.splitlines():
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]
        elif line.startswith("info depth"):
            m_d = re.search(r'depth (\d+)', line)
            m_t = re.search(r'time (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_t: engine_time_ms = int(m_t.group(1))
            if m_n: nodes = int(m_n.group(1))
            if "pv" in line:
                pv_idx = line.find("pv")
                pv_moves = line[pv_idx+3:].strip().split()

    latency_ms = wall_elapsed_ms - movetime_ms
    legal = (bestmove is not None and len(bestmove) >= 4 and bestmove != "0000")

    return {
        "budget_ms": movetime_ms,
        "wall_elapsed_ms": round(wall_elapsed_ms, 2),
        "engine_reported_ms": engine_time_ms,
        "latency_overrun_ms": round(latency_ms, 2),
        "depth": depth,
        "nodes": nodes,
        "bestmove": bestmove,
        "legal": legal,
        "pv_length": len(pv_moves)
    }

def main():
    print("==================================================================")
    print("PHASE 4: PARALLEL ROOT RESULT & CONCURRENCY TIME MANAGEMENT AUDIT")
    print("==================================================================")

    configs = [
        {"name": "X11 (1T)", "exe": EXE_X11, "threads": 1},
        {"name": "X11 (4T)", "exe": EXE_X11, "threads": 4},
        {"name": "Candidate X12 Prototype (4T)", "exe": EXE_W4, "threads": 4}
    ]

    results = {}

    for cfg in configs:
        cname = cfg["name"]
        print(f"\n[EVALUATING] {cname} across 6 time budgets...")
        results[cname] = {}
        for b_ms in BUDGETS_MS:
            b_results = []
            for p in TEST_POSITIONS:
                res = run_clock_test(cfg["exe"], p["fen"], b_ms, cfg["threads"])
                res["pos"] = p["name"]
                b_results.append(res)

            avg_elapsed = sum(r["wall_elapsed_ms"] for r in b_results) / len(b_results)
            avg_overrun = sum(r["latency_overrun_ms"] for r in b_results) / len(b_results)
            avg_depth = sum(r["depth"] for r in b_results) / len(b_results)
            all_legal = all(r["legal"] for r in b_results)

            results[cname][f"{b_ms}ms"] = {
                "budget_ms": b_ms,
                "avg_wall_elapsed_ms": round(avg_elapsed, 2),
                "avg_latency_overrun_ms": round(avg_overrun, 2),
                "avg_depth": round(avg_depth, 2),
                "all_legal": all_legal,
                "positions": b_results
            }
            print(f"  Budget: {b_ms:>4} ms -> Avg Wall: {avg_elapsed:>6.1f} ms (Overrun: {avg_overrun:>+5.1f} ms), Depth: {avg_depth:>4.1f}, Legal: {all_legal}")

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Root and Clock Audit written to {RAW_OUT}")

if __name__ == "__main__":
    main()

