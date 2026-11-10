#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Phase 2 Test Suite: Quiescence SEE Filtering Ablations (Q0, Q1, Q2, Q3).
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


def run_q_ablation(mode: int, mode_name: str, positions: list, depth: int = 7) -> dict:
    print(f"\n--- Running Quiescence Ablation: {mode_name} (UCI_QuiescenceSEE = {mode}) ---", flush=True)

    total_nodes = 0
    total_time = 0.0
    total_q_pruned = 0
    records = []

    for pos in positions:
        pid = pos["id"]
        cat = pos["cat"]
        fen = pos["fen"]

        p = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        cmds = [
            "uci",
            "isready",
            "setoption name UCI_Variant value X0",  # Base search (no NMP/RFP/Asp) to isolate Quiescence SEE!
            f"setoption name UCI_QuiescenceSEE value {mode}",
            f"position fen {fen}",
            f"go depth {depth}",
            "telemetry_report",
            "quit"
        ]
        t0 = time.perf_counter()
        out, _ = p.communicate("\n".join(cmds) + "\n", timeout=15)
        elapsed = time.perf_counter() - t0

        nodes = 0
        score_cp = 0
        bestmove = None
        q_pruned = 0
        in_telemetry = False

        for line in out.splitlines():
            if line.startswith("info") and "nodes" in line and "depth" in line:
                parts = line.split()
                if "nodes" in parts: nodes = int(parts[parts.index("nodes")+1])
                if "cp" in parts: score_cp = int(parts[parts.index("cp")+1])
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) > 1: bestmove = parts[1]
            elif "TELEMETRY_START" in line:
                in_telemetry = True
            elif "TELEMETRY_END" in line:
                in_telemetry = False
            elif in_telemetry:
                parts = line.split()
                if len(parts) == 2 and parts[0] == "qmoves_pruned":
                    q_pruned = int(parts[1])

        total_nodes += nodes
        total_time += elapsed
        total_q_pruned += q_pruned

        records.append({
            "id": pid,
            "category": cat,
            "bestmove": bestmove,
            "score_cp": score_cp,
            "nodes": nodes,
            "elapsed_sec": round(elapsed, 4),
            "qmoves_pruned": q_pruned
        })

    summary = {
        "mode": mode,
        "mode_name": mode_name,
        "total_positions": len(positions),
        "total_nodes": total_nodes,
        "mean_nodes_per_pos": int(total_nodes / len(positions)),
        "total_time_sec": round(total_time, 2),
        "total_qmoves_pruned": total_q_pruned,
        "avg_nps": int(total_nodes / max(total_time, 0.001))
    }
    print(f"Summary for {mode_name}: Nodes={total_nodes:,} | Time={total_time:.2f}s | Pruned Moves={total_q_pruned:,} | NPS={summary['avg_nps']:,}")
    return {"summary": summary, "positions": records}


def main():
    print("=" * 80)
    print("PHASE 2: QUIESCENCE SEE FILTERING ABLATION SUITE (Q0 vs Q1 vs Q2 vs Q3)")
    print("=" * 80)

    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)

    # We evaluate 20 diverse positions (Tactics, Quiet, Closed, KingAttack, Endgame)
    sample_positions = [p for p in positions if p["cat"] in ["Tactics", "KingAttack", "Endgame", "Quiet", "Closed"]][:25]
    print(f"Loaded {len(sample_positions)} diagnostic benchmark positions.")

    q0_res = run_q_ablation(0, "Q0_Baseline_NoSEE", sample_positions, depth=7)
    q1_res = run_q_ablation(1, "Q1_SEE_Ordering_Only", sample_positions, depth=7)
    q2_res = run_q_ablation(2, "Q2_Conservative_SEE_Filter", sample_positions, depth=7)
    q3_res = run_q_ablation(3, "Q3_Bounded_SEE_Filter", sample_positions, depth=7)

    # Compute comparative metrics
    base_nodes = q0_res["summary"]["total_nodes"]
    base_time = q0_res["summary"]["total_time_sec"]

    comparison = {
        "Q0_Baseline": {
            "nodes": base_nodes,
            "time_sec": base_time,
            "node_reduction_pct": 0.0,
            "speedup": 1.00
        },
        "Q1_Ordering_Only": {
            "nodes": q1_res["summary"]["total_nodes"],
            "time_sec": q1_res["summary"]["total_time_sec"],
            "node_reduction_pct": round(((base_nodes - q1_res["summary"]["total_nodes"]) / base_nodes) * 100.0, 2),
            "speedup": round(base_time / max(q1_res["summary"]["total_time_sec"], 0.001), 2)
        },
        "Q2_Conservative_Filter": {
            "nodes": q2_res["summary"]["total_nodes"],
            "time_sec": q2_res["summary"]["total_time_sec"],
            "node_reduction_pct": round(((base_nodes - q2_res["summary"]["total_nodes"]) / base_nodes) * 100.0, 2),
            "speedup": round(base_time / max(q2_res["summary"]["total_time_sec"], 0.001), 2),
            "moves_pruned": q2_res["summary"]["total_qmoves_pruned"]
        },
        "Q3_Bounded_Filter": {
            "nodes": q3_res["summary"]["total_nodes"],
            "time_sec": q3_res["summary"]["total_time_sec"],
            "node_reduction_pct": round(((base_nodes - q3_res["summary"]["total_nodes"]) / base_nodes) * 100.0, 2),
            "speedup": round(base_time / max(q3_res["summary"]["total_time_sec"], 0.001), 2),
            "moves_pruned": q3_res["summary"]["total_qmoves_pruned"]
        }
    }

    print("\n" + "=" * 80)
    print("COMPARATIVE ABLATION SUMMARY")
    print("=" * 80)
    for variant, stats in comparison.items():
        print(f"  {variant:24s}: Nodes={stats['nodes']:,} ({stats['node_reduction_pct']:+5.1f}% reduction) | Time={stats['time_sec']:5.2f}s (Speedup: {stats['speedup']:4.2f}x)")

    # Tactical move consistency check (ensure Q2 does not alter best moves in tactics)
    tactical_matches = 0
    tactical_total = 0
    for r0, r2 in zip(q0_res["positions"], q2_res["positions"]):
        if r0["category"] == "Tactics":
            tactical_total += 1
            if r0["bestmove"] == r2["bestmove"]:
                tactical_matches += 1

    tactical_fidelity_pct = round((tactical_matches / max(tactical_total, 1)) * 100.0, 1)
    print(f"\nTactical Move Fidelity (Q0 vs Q2): {tactical_matches}/{tactical_total} ({tactical_fidelity_pct}%)")

    out_file = RAW_DIR / "quiescence_see_ablation_raw.json"
    full_output = {
        "comparison": comparison,
        "tactical_fidelity_pct": tactical_fidelity_pct,
        "q0": q0_res,
        "q1": q1_res,
        "q2": q2_res,
        "q3": q3_res
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)
    print(f"Wrote full ablation raw data to: {out_file}")


if __name__ == "__main__":
    main()

