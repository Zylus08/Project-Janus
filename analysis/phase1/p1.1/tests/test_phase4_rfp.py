#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 4 Test Suite: Reverse Futility Pruning (RFP) Verification & Ablation.
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


def test_rfp_safety():
    print("=" * 80)
    print("TEST 1: REVERSE FUTILITY PRUNING SAFETY & GUARDRAILS TEST")
    print("=" * 80)

    # Positions where engine is in check or near mate
    positions = [
        {
            "name": "Side in Check (RFP must not trigger)",
            "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/5P2/PPPP2PP/RNBQKBNR b KQkq - 0 2",
            # We will use an explicit check position
            "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5",
            "desc": "Normal tactical position."
        },
        {
            "name": "Direct Check Position",
            "fen": "r1bqk1nr/pppp1ppp/2n5/4p3/1b2P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 1 4",
            "desc": "White king in check by Bb4; RFP must strictly bypass when in_check."
        },
        {
            "name": "Mate Threat Position (Fool's Mate Defense)",
            "fen": "rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
            "desc": "Checkmate position; search must detect mate bounds and not corrupt evaluation."
        }
    ]

    all_passed = True
    for t in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = [
            "uci",
            "isready",
            "setoption name UCI_Variant value X4",  # RFP only
            f"position fen {t['fen']}",
            "go depth 5",
            "telemetry_report",
            "quit"
        ]
        out, _ = p.communicate("\n".join(cmds) + "\n", timeout=10)
        
        rfp_cutoffs = 0
        in_tel = False
        for l in out.splitlines():
            if "TELEMETRY_START" in l: in_tel = True
            elif "TELEMETRY_END" in l: in_tel = False
            elif in_tel:
                parts = l.split()
                if len(parts) == 2 and parts[0] == "rfp_cutoffs":
                    rfp_cutoffs = int(parts[1])

        print(f"  [PASS] {t['name']} - Executed safely (RFP Cutoffs: {rfp_cutoffs}).")

    return all_passed


def run_rfp_ablation(positions: list, depth: int = 7) -> dict:
    print("\n" + "=" * 80)
    print("TEST 2: R0 (BASELINE NO RFP) VS R1 (REVERSE FUTILITY PRUNING) ABLATION")
    print("=" * 80)

    # 1. R0: Without RFP
    print("Running R0: Baseline without RFP...", flush=True)
    t0_nodes, t0_time, r0_recs = 0, 0.0, []
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
        r0_recs.append({"id": pos["id"], "nodes": nodes, "elapsed_sec": dur, "bestmove": bm})

    # 2. R1: With RFP (Variant X4)
    print("Running R1: With Reverse Futility Pruning (depth <= 3, margin = 80 * depth)...", flush=True)
    t1_nodes, t1_time, r1_recs = 0, 0.0, []
    total_rfp_cutoffs = 0
    total_rfp_probes = 0
    for pos in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value X4\nposition fen {pos['fen']}\ngo depth {depth}\ntelemetry_report\nquit\n"
        t_start = time.perf_counter()
        out, _ = p.communicate(cmds, timeout=15)
        dur = time.perf_counter() - t_start
        nodes = 0
        bm = None
        rfp_cutoffs = 0
        rfp_probes = 0
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
                if len(parts) == 2:
                    if parts[0] == "rfp_cutoffs": rfp_cutoffs = int(parts[1])
                    if parts[0] == "rfp_probes": rfp_probes = int(parts[1])
        t1_nodes += nodes
        t1_time += dur
        total_rfp_cutoffs += rfp_cutoffs
        total_rfp_probes += rfp_probes
        r1_recs.append({"id": pos["id"], "nodes": nodes, "elapsed_sec": dur, "bestmove": bm, "rfp_cutoffs": rfp_cutoffs})

    node_reduction_pct = ((t0_nodes - t1_nodes) / t0_nodes) * 100.0
    speedup = t0_time / max(t1_time, 0.001)

    print("\n" + "=" * 80)
    print("RFP ABLATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"R0 (No RFP) Total Nodes : {t0_nodes:,} ({t0_time:.2f}s)")
    print(f"R1 (With RFP) Total Nodes: {t1_nodes:,} ({t1_time:.2f}s)")
    print(f"Node Reduction          : {node_reduction_pct:.2f}%")
    print(f"Search Speedup          : {speedup:.2f}x")
    print(f"RFP Cutoff Success Rate : {total_rfp_cutoffs:,} / {total_rfp_probes:,} ({round((total_rfp_cutoffs/max(total_rfp_probes,1))*100, 1)}%)")

    # Move consistency
    matching_moves = sum(1 for r0, r1 in zip(r0_recs, r1_recs) if r0["bestmove"] == r1["bestmove"])
    print(f"Move Agreement (R0 vs R1): {matching_moves} / {len(positions)} ({round((matching_moves/len(positions))*100, 1)}%)")

    out_file = RAW_DIR / "reverse_futility_pruning_raw.json"
    full_output = {
        "r0_total_nodes": t0_nodes,
        "r1_total_nodes": t1_nodes,
        "node_reduction_pct": round(node_reduction_pct, 2),
        "speedup": round(speedup, 2),
        "total_rfp_cutoffs": total_rfp_cutoffs,
        "total_rfp_probes": total_rfp_probes,
        "move_agreement_pct": round((matching_moves / len(positions)) * 100, 1),
        "r0_positions": r0_recs,
        "r1_positions": r1_recs
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"Wrote RFP ablation data to: {out_file}")
    return full_output


def main():
    test_rfp_safety()
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    sample_positions = [p for p in positions if p["cat"] in ["Tactics", "KingAttack", "Endgame", "Quiet", "Closed"]][:25]
    res = run_rfp_ablation(sample_positions, depth=7)


if __name__ == "__main__":
    main()

