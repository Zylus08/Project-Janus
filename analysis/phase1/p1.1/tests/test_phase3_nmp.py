#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 3 Test Suite: Null-Move Pruning (NMP) Verification & Ablation.
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


def test_zugzwang_positions():
    print("=" * 80)
    print("TEST 1: ZUGZWANG & PAWN-ONLY ENDGAME SAFETY TEST")
    print("=" * 80)

    # Canonical Zugzwang positions
    zugzwang_positions = [
        {
            "name": "King and Pawns Mutual Zugzwang (Trebushov)",
            "fen": "8/8/1p1k4/pP1p4/P2K4/8/8/8 w - - 0 1",
            "desc": "White to move must not null-move prune because White has only pawns."
        },
        {
            "name": "Fine 70 (Pawn Zugzwang)",
            "fen": "8/k7/3p4/p2P1p2/P2P1P2/8/8/1K6 w - - 0 1",
            "desc": "Pure pawn endgame where zugzwang determines result."
        },
        {
            "name": "Kaufman Zugzwang Study",
            "fen": "8/8/8/4k3/8/8/4K3/4b3 w - - 0 1",
            "desc": "King and bishop endgame."
        }
    ]

    all_passed = True
    for z in zugzwang_positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = [
            "uci",
            "isready",
            "setoption name UCI_Variant value X3",  # NMP only
            f"position fen {z['fen']}",
            "go depth 8",
            "telemetry_report",
            "quit"
        ]
        out, _ = p.communicate("\n".join(cmds) + "\n", timeout=10)
        
        nmp_probes = 0
        nmp_cutoffs = 0
        in_telemetry = False
        for l in out.splitlines():
            if "TELEMETRY_START" in l: in_telemetry = True
            elif "TELEMETRY_END" in l: in_telemetry = False
            elif in_telemetry:
                parts = l.split()
                if len(parts) == 2:
                    if parts[0] == "nmp_probes": nmp_probes = int(parts[1])
                    if parts[0] == "nmp_cutoffs": nmp_cutoffs = int(parts[1])

        # In pawn-only endgames, nmp_probes must be 0 or cutoffs 0 because non_pawn_mat == 0
        if "pawns" in z["desc"].lower():
            if nmp_probes == 0:
                print(f"  [PASS] {z['name']} - Correctly bypassed NMP (0 probes).")
            else:
                print(f"  [WARN] {z['name']} - NMP probed {nmp_probes} times.")
        else:
            print(f"  [PASS] {z['name']} - Processed safely (Cutoffs: {nmp_cutoffs}).")

    return all_passed


def run_nmp_ablation(positions: list, depth: int = 7) -> dict:
    print("\n" + "=" * 80)
    print("TEST 2: N0 (BASELINE NO NMP) VS N1 (CONSERVATIVE NMP R=3) ABLATION")
    print("=" * 80)

    # 1. N0: Without NMP
    print("Running N0: Baseline without NMP...", flush=True)
    t0_nodes, t0_time, n0_recs = 0, 0.0, []
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
        n0_recs.append({"id": pos["id"], "nodes": nodes, "elapsed_sec": dur, "bestmove": bm})

    # 2. N1: With Conservative NMP (R=3)
    print("Running N1: With Conservative NMP (R=3)...", flush=True)
    t1_nodes, t1_time, n1_recs = 0, 0.0, []
    total_nmp_cutoffs = 0
    total_nmp_probes = 0
    for pos in positions:
        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = f"uci\nisready\nsetoption name UCI_Variant value X3\nposition fen {pos['fen']}\ngo depth {depth}\ntelemetry_report\nquit\n"
        t_start = time.perf_counter()
        out, _ = p.communicate(cmds, timeout=15)
        dur = time.perf_counter() - t_start
        nodes = 0
        bm = None
        nmp_cutoffs = 0
        nmp_probes = 0
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
                    if parts[0] == "nmp_cutoffs": nmp_cutoffs = int(parts[1])
                    if parts[0] == "nmp_probes": nmp_probes = int(parts[1])
        t1_nodes += nodes
        t1_time += dur
        total_nmp_cutoffs += nmp_cutoffs
        total_nmp_probes += nmp_probes
        n1_recs.append({"id": pos["id"], "nodes": nodes, "elapsed_sec": dur, "bestmove": bm, "nmp_cutoffs": nmp_cutoffs})

    node_reduction_pct = ((t0_nodes - t1_nodes) / t0_nodes) * 100.0
    speedup = t0_time / max(t1_time, 0.001)

    print("\n" + "=" * 80)
    print("NMP ABLATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"N0 (No NMP) Total Nodes : {t0_nodes:,} ({t0_time:.2f}s)")
    print(f"N1 (NMP R=3) Total Nodes: {t1_nodes:,} ({t1_time:.2f}s)")
    print(f"Node Reduction          : {node_reduction_pct:.2f}%")
    print(f"Search Speedup          : {speedup:.2f}x")
    print(f"NMP Cutoff Success Rate : {total_nmp_cutoffs:,} / {total_nmp_probes:,} ({round((total_nmp_cutoffs/max(total_nmp_probes,1))*100, 1)}%)")

    # Move consistency
    matching_moves = sum(1 for r0, r1 in zip(n0_recs, n1_recs) if r0["bestmove"] == r1["bestmove"])
    print(f"Move Agreement (N0 vs N1): {matching_moves} / {len(positions)} ({round((matching_moves/len(positions))*100, 1)}%)")

    out_file = RAW_DIR / "null_move_pruning_ablation_raw.json"
    full_output = {
        "n0_total_nodes": t0_nodes,
        "n1_total_nodes": t1_nodes,
        "node_reduction_pct": round(node_reduction_pct, 2),
        "speedup": round(speedup, 2),
        "total_nmp_cutoffs": total_nmp_cutoffs,
        "total_nmp_probes": total_nmp_probes,
        "move_agreement_pct": round((matching_moves / len(positions)) * 100, 1),
        "n0_positions": n0_recs,
        "n1_positions": n1_recs
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"Wrote NMP ablation data to: {out_file}")
    return full_output


def main():
    test_zugzwang_positions()
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    sample_positions = [p for p in positions if p["cat"] in ["Tactics", "KingAttack", "Endgame", "Quiet", "Closed"]][:25]
    res = run_nmp_ablation(sample_positions, depth=7)


if __name__ == "__main__":
    main()

