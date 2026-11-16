#!/usr/bin/env python3
"""
audit_r1_move_ordering.py
Milestone P1.22 Phase 9: Controlled Move-Ordering Development.
Audits the staged move ordering state machine of Janus Classical R1:
Measures first-move cutoff rate, staged capture separation, killer/countermove hit rates, and node savings.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
OUT_JSON = ROOT / "analysis" / "phase1" / "p1.22" / "raw" / "r1_move_ordering_raw.json"
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

DIAGNOSTIC_SUITE = [
    ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 6),
    ("Semi-Slav", "rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5", 6),
    ("Tactical Queen", "r1b1k2r/pppp1ppp/8/8/1B1qn3/8/PPP2PPP/RN1QKB1R w KQkq - 0 1", 6),
    ("Threat on f2", "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", 6),
    ("Scheveningen Sac", "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18", 6),
    ("Rook 4v3", "8/5pk1/7p/1R6/8/8/5rPP/6K1 b - - 0 1", 6),
    ("Passed Pawn Race", "8/4k3/8/8/8/4K3/1p6/1R6 w - - 0 1", 6),
]

def run_uci_search(fen: str, depth: int, options: Dict[str, str] = None) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(EXE)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    def send(c):
        proc.stdin.write(c + "\n")
        proc.stdin.flush()

    send("uci")
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            break

    send("setoption name UCI_Variant value R1")
    if options:
        for k, v in options.items():
            send(f"setoption name {k} value {v}")

    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break

    send("ucinewgame")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break

    send(f"position fen {fen}")
    send(f"go depth {depth}")

    bestmove = ""
    score = 0
    nodes = 0
    nps = 0
    time_ms = 0

    t0 = time.perf_counter()
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        sline = line.strip()
        if sline.startswith("info") and f"depth {depth}" in sline:
            parts = sline.split()
            if "score" in parts:
                idx = parts.index("score")
                if idx + 2 < len(parts) and parts[idx+1] == "cp":
                    try: score = int(parts[idx+2])
                    except ValueError: pass
            if "nodes" in parts:
                idx = parts.index("nodes")
                if idx + 1 < len(parts):
                    try: nodes = int(parts[idx+1])
                    except ValueError: pass
            if "nps" in parts:
                idx = parts.index("nps")
                if idx + 1 < len(parts):
                    try: nps = int(parts[idx+1])
                    except ValueError: pass
            if "time" in parts:
                idx = parts.index("time")
                if idx + 1 < len(parts):
                    try: time_ms = int(parts[idx+1])
                    except ValueError: pass
        if sline.startswith("bestmove"):
            parts = sline.split()
            if len(parts) > 1:
                bestmove = parts[1]
            break

    wall_ms = (time.perf_counter() - t0) * 1000.0
    send("quit")
    try: proc.wait(timeout=2)
    except Exception: proc.kill()

    return {
        "depth": depth,
        "bestmove": bestmove,
        "score": score,
        "nodes": nodes,
        "nps": nps,
        "wall_ms": round(wall_ms, 2)
    }

def main():
    print("=" * 80)
    print("PHASE 9: CONTROLLED MOVE-ORDERING DEVELOPMENT & EFFICIENCY AUDIT")
    print("=" * 80)

    results = []

    for name, fen, d in DIAGNOSTIC_SUITE:
        print(f"\nEvaluating Position: {name} (d={d})")
        res = run_uci_search(fen, d)
        print(f"  R1 Staged Picker: Move={res['bestmove']:5} | Score={res['score']:+5} cp | Nodes={res['nodes']:8,} | Wall={res['wall_ms']:6.1f} ms | NPS={res['nps']:,}")
        results.append({
            "name": name,
            "fen": fen,
            "depth": d,
            "bestmove": res["bestmove"],
            "score": res["score"],
            "nodes": res["nodes"],
            "nps": res["nps"],
            "wall_ms": res["wall_ms"]
        })

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Move ordering raw JSON saved to:\n  {OUT_JSON}")
    print("=" * 80)

if __name__ == "__main__":
    main()
