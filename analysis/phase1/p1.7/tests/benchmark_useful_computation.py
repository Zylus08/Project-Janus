#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 6: Useful Search Efficiency Benchmark
Measures Throughput, Completed Depth, Tactical Decision Quality, and Move Stability
across 12 diverse positions at 500ms and 1000ms budgets for:
  - X7 (1T Control)
  - X11 (1T)
  - X11 (4T)
  - X12-Candidate (1T)
  - X12-Candidate (2T)
  - X12-Candidate (4T)
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
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.7" / "raw" / "useful_computation_raw.json"

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X11 = ROOT / "analysis" / "phase1" / "p1.6" / "control" / "janus_classical_x11.exe"
EXE_X12 = TEST_DIR / "engine_w4.exe" # Candidate X12 prototype with T4 TT + W4 worker cooperation

BENCHMARK_SUITE = [
    {"name": "quiet_middlegame", "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10", "expected": None},
    {"name": "open_tactical", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "expected": None},
    {"name": "closed_pawn", "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8", "expected": None},
    {"name": "defensive_pos", "fen": "2r2rk1/1b2bppp/pp2p3/3qN3/3P4/P2B1P2/1P2Q1PP/2RR2K1 b - - 0 20", "expected": None},
    {"name": "endgame_transition", "fen": "4k3/1p3pp1/p3p3/3pP3/3P1P2/P3K3/1P6/8 b - - 0 35", "expected": None},
    {"name": "passed_pawn_race", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "expected": "b4f4"},
    {"name": "forced_check_mate", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected": "h5f7"},
    {"name": "multi_candidate_1", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "expected": None},
    {"name": "multi_candidate_2", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "expected": "e2a6"},
    {"name": "tactical_sacrifice", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected": "d5f6"},
    {"name": "opposite_bishops_draw", "fen": "8/4b3/8/2k5/8/8/4B3/4K3 w - - 0 1", "expected": None},
    {"name": "rook_pawn_breakthrough", "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40", "expected": "d3c3"}
]

def run_bench(exe, fen, movetime_ms, threads):
    cmds = f"uci\nsetoption name Threads value {threads}\nisready\nposition fen {fen}\ngo movetime {movetime_ms}\nquit\n"
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate(cmds, timeout=15)
    dur = time.perf_counter() - t0

    depth = 0
    nodes = 0
    bestmove = None
    score = 0
    for line in out.splitlines():
        if line.startswith("info depth"):
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score = int(m_s.group(1))
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "depth": depth,
        "nodes": nodes,
        "nps": nps,
        "score": score,
        "bestmove": bestmove,
        "elapsed_sec": round(dur, 4)
    }

def main():
    print("==================================================================")
    print("PHASE 6: USEFUL SEARCH EFFICIENCY BENCHMARK")
    print("==================================================================")

    configs = [
        {"id": "X7_1T",  "name": "Janus Classical X7 (1T Control)", "exe": EXE_X7,  "threads": 1},
        {"id": "X11_1T", "name": "Janus Classical X11 (1T)",        "exe": EXE_X11, "threads": 1},
        {"id": "X11_4T", "name": "Janus Classical X11 (4T)",        "exe": EXE_X11, "threads": 4},
        {"id": "X12_1T", "name": "Candidate X12 (1T)",              "exe": EXE_X12, "threads": 1},
        {"id": "X12_2T", "name": "Candidate X12 (2T)",              "exe": EXE_X12, "threads": 2},
        {"id": "X12_4T", "name": "Candidate X12 (4T)",              "exe": EXE_X12, "threads": 4}
    ]

    time_budgets = [500, 1000]
    results = {}

    for tb in time_budgets:
        tb_key = f"{tb}ms"
        results[tb_key] = {}
        print(f"\n==================== TIME BUDGET: {tb} ms ====================")
        for cfg in configs:
            cid = cfg["id"]
            cname = cfg["name"]
            print(f"\n[RUNNING] {cname} (Threads={cfg['threads']})...")

            tot_nodes = 0
            tot_depth = 0
            tot_time = 0.0
            solved_tactics = 0
            tactics_tested = 0
            pos_results = []

            for p in BENCHMARK_SUITE:
                res = run_bench(cfg["exe"], p["fen"], tb, cfg["threads"])
                res["name"] = p["name"]
                
                # Check tactical accuracy
                if p["expected"] is not None:
                    tactics_tested += 1
                    is_correct = (res["bestmove"] == p["expected"])
                    res["tactics_correct"] = is_correct
                    if is_correct: solved_tactics += 1

                pos_results.append(res)
                tot_nodes += res["nodes"]
                tot_depth += res["depth"]
                tot_time += res["elapsed_sec"]

            avg_depth = round(tot_depth / len(BENCHMARK_SUITE), 2)
            agg_nps = int(tot_nodes / tot_time) if tot_time > 0 else 0
            tactical_accuracy = round((solved_tactics / tactics_tested) * 100.0, 1) if tactics_tested > 0 else 100.0

            results[tb_key][cid] = {
                "name": cname,
                "threads": cfg["threads"],
                "total_nodes": tot_nodes,
                "total_elapsed_sec": round(tot_time, 3),
                "avg_depth": avg_depth,
                "aggregate_nps": agg_nps,
                "tactical_accuracy_pct": tactical_accuracy,
                "solved_tactics": f"{solved_tactics}/{tactics_tested}",
                "positions": pos_results
            }

            print(f"  Result -> Nodes: {tot_nodes:,}, Depth: {avg_depth}, NPS: {agg_nps:,}, Tactics: {solved_tactics}/{tactics_tested} ({tactical_accuracy}%)")

    # Move Stability Analysis between 500ms and 1000ms
    stability_data = {}
    for cfg in configs:
        cid = cfg["id"]
        cname = cfg["name"]
        agreed = 0
        total = len(BENCHMARK_SUITE)
        for i in range(total):
            m500 = results["500ms"][cid]["positions"][i]["bestmove"]
            m1000 = results["1000ms"][cid]["positions"][i]["bestmove"]
            if m500 == m1000:
                agreed += 1
        stability_pct = round((agreed / total) * 100.0, 1)
        stability_data[cid] = {
            "name": cname,
            "agreed_moves": f"{agreed}/{total}",
            "move_stability_pct": stability_pct
        }
        results["500ms"][cid]["move_stability_vs_1000ms"] = stability_pct
        results["1000ms"][cid]["move_stability_vs_500ms"] = stability_pct

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Useful Search Efficiency benchmark saved to {RAW_OUT}")
    print("\n" + "=" * 105)
    print(f"{'Engine / Configuration':<36} | {'Thr':<3} | {'Avg Depth':<9} | {'Agg NPS':<10} | {'Tactics (1000ms)':<16} | {'Move Stability'}")
    print("-" * 105)
    for cfg in configs:
        cid = cfg["id"]
        d1000 = results["1000ms"][cid]
        stab = stability_data[cid]["move_stability_pct"]
        print(f"{d1000['name']:<36} | {d1000['threads']:<3} | {d1000['avg_depth']:<9} | {d1000['aggregate_nps']:<10,d} | {d1000['solved_tactics']:<6} ({d1000['tactical_accuracy_pct']}%)   | {stab}%")
    print("=" * 105)

if __name__ == "__main__":
    main()

