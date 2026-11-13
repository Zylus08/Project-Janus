#!/usr/bin/env python3
"""
run_development_ablations.py
Phase 8: Independent Development Ablations Benchmark
Project Janus — Phase 1, Milestone P1.13
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.13" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

ABLATION_POSITIONS = [
    {"id": "STARTPOS", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "TACTICAL_FORK", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"},
    {"id": "QUIET_MIDDLEGAME", "fen": "r2q1rk1/1b2bppp/p1np4/1p1Np3/4P3/1B2BN2/PPP2PPP/R2Q1RK1 w - - 4 13"},
    {"id": "PAWN_ENDGAME", "fen": "8/5p2/4k3/4p1p1/4P1P1/4KP2/8/8 w - - 0 45"},
]

def run_ablation(variant_name, lmr_mode, threads, fen, depth=9):
    proc = subprocess.Popen(
        [str(EXE_X)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    def send(cmd):
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    send("uci")
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            break

    send(f"setoption name Threads value {threads}")
    send(f"setoption name UCI_Variant value {variant_name}")
    send(f"setoption name UCI_DynamicLMR value L{lmr_mode}")
    send("ucinewgame")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break

    send(f"position fen {fen}")
    t0 = time.time()
    send(f"go depth {depth}")

    nodes = 0
    nps = 0
    bestmove = None
    score_cp = 0

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("info") and "depth" in line:
            parts = line.split()
            if "nodes" in parts:
                try: nodes = int(parts[parts.index("nodes") + 1])
                except Exception: pass
            if "nps" in parts:
                try: nps = int(parts[parts.index("nps") + 1])
                except Exception: pass
            if "score" in parts and "cp" in parts:
                try: score_cp = int(parts[parts.index("cp") + 1])
                except Exception: pass
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bestmove = parts[1]
            break

    dur = time.time() - t0
    send("quit")
    try:
        proc.terminate()
        proc.wait(timeout=1.0)
    except Exception:
        proc.kill()

    return {
        "nodes": nodes,
        "nps": nps,
        "bestmove": bestmove,
        "score_cp": score_cp,
        "time_s": dur
    }


def main():
    print("================================================================================")
    print("PHASE 8: CONTROLLED DEVELOPMENT ABLATIONS")
    print("================================================================================")
    
    configs = [
        ("B0", "Baseline Static LMR (X7)", "X7", 1),
        ("B1", "Primary Intervention (X18 History-LMR)", "X18", 2),
        ("B2", "Baseline Static LMR (X12 4T)", "X12", 1),
        ("B3", "Primary Intervention (X18 4T History-LMR)", "X18", 2),
    ]

    ablation_results = {}

    for cfg_id, cfg_desc, var, lmr_m in configs:
        threads = 4 if "4T" in cfg_desc else 1
        print(f"\n--- Testing Configuration: {cfg_id} ({cfg_desc}) ---")
        cfg_records = []
        tot_nodes = 0
        tot_time = 0.0

        for pos in ABLATION_POSITIONS:
            pid = pos["id"]
            fen = pos["fen"]
            r = run_ablation(var, lmr_m, threads, fen, depth=9)
            r["pos_id"] = pid
            cfg_records.append(r)
            tot_nodes += r["nodes"]
            tot_time += r["time_s"]
            print(f"  [{pid}] bm={r['bestmove']} nodes={r['nodes']} nps={r['nps']} time={r['time_s']:.3f}s cp={r['score_cp']}")

        avg_nps = int(tot_nodes / tot_time) if tot_time > 0 else 0
        print(f"  Summary for {cfg_id}: Total Nodes = {tot_nodes}, Avg NPS = {avg_nps}, Total Time = {tot_time:.3f}s")
        ablation_results[cfg_id] = {
            "description": cfg_desc,
            "threads": threads,
            "total_nodes": tot_nodes,
            "total_time_s": tot_time,
            "avg_nps": avg_nps,
            "records": cfg_records
        }

    out_file = RAW_DIR / "controlled_ablations_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ablation_results, f, indent=2)
    print(f"\nSaved ablation results to {out_file}")

if __name__ == "__main__":
    main()

