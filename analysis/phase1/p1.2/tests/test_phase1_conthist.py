#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.2
Phase 1 Test Suite: Continuation History Ablation (H0, H1, H2, H3)
Tests isolated impact of continuation history on move ordering, first-move cutoff rate, and search efficiency.
"""

import json
import time
import subprocess
from pathlib import Path

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
SUITE_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.2" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CONFIGS = [
    ("H0", "No Conthist (X6 Baseline)", 0),
    ("H1", "1-ply Conthist", 1),
    ("H2", "2-ply Conthist", 2),
    ("H3", "1-ply + 2-ply Conthist", 3),
]

SEARCH_DEPTH = 6

def run_uci_search(fen: str, depth: int, conthist_mode: int):
    p = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    h_str = f"H{conthist_mode}"
    commands = [
        "uci",
        "isready",
        "setoption name UCI_Variant value X6",
        f"setoption name UCI_ContinuationHistory value {h_str}",
        "ucinewgame",
        "isready",
        "telemetry_reset",
        f"position fen {fen}",
        f"go depth {depth}",
        "telemetry_report",
        "quit\n"
    ]
    
    t0 = time.perf_counter()
    out, _ = p.communicate("\n".join(commands))
    t1 = time.perf_counter()
    
    # Parse output
    nodes = 0
    score = 0
    bestmove = ""
    telemetry = {}
    
    in_telemetry = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(f"info depth {depth}"):
            toks = line.split()
            if "nodes" in toks:
                nodes = int(toks[toks.index("nodes") + 1])
            if "score" in toks:
                score = int(toks[toks.index("score") + 2])
        elif line.startswith("bestmove"):
            bestmove = line.split()[1]
        elif line == "TELEMETRY_START":
            in_telemetry = True
        elif line == "TELEMETRY_END":
            in_telemetry = False
        elif in_telemetry and line:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    telemetry[parts[0]] = int(parts[1])
                except ValueError:
                    telemetry[parts[0]] = parts[1]
                    
    return {
        "nodes": nodes,
        "score": score,
        "bestmove": bestmove,
        "elapsed_sec": t1 - t0,
        "telemetry": telemetry
    }

def main():
    print(f"=== Project Janus P1.2 — Phase 1: Continuation History Ablation ===")
    print(f"Loading suite: {SUITE_PATH}")
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    print(f"Loaded {len(positions)} diagnostic positions. Search depth: {SEARCH_DEPTH}\n")
    
    results = {}
    for code, label, mode in CONFIGS:
        print(f"--- Running {code}: {label} ---")
        cfg_res = []
        tot_nodes = 0
        tot_fmc = 0
        tot_cutoffs = 0
        tot_searched = 0
        t_start = time.perf_counter()
        
        for idx, pos in enumerate(positions):
            fen = pos["fen"]
            res = run_uci_search(fen, SEARCH_DEPTH, mode)
            res["pos_id"] = pos.get("id", f"pos_{idx}")
            res["cat"] = pos.get("cat", "Unknown")
            cfg_res.append(res)
            
            tot_nodes += res["nodes"]
            tel = res.get("telemetry", {})
            tot_fmc += tel.get("first_move_cutoffs", 0)
            tot_cutoffs += tel.get("total_cutoffs", 0)
            tot_searched += tel.get("moves_searched", 0)
            
        elapsed = time.perf_counter() - t_start
        fmc_rate = (tot_fmc / tot_cutoffs * 100.0) if tot_cutoffs > 0 else 0.0
        
        print(f"Completed {code}:")
        print(f"  Total Nodes: {tot_nodes:,}")
        print(f"  First-Move Cutoffs: {tot_fmc:,} / {tot_cutoffs:,} ({fmc_rate:.2f}%)")
        print(f"  Wall Time: {elapsed:.2f}s\n")
        
        results[code] = {
            "label": label,
            "mode": mode,
            "total_nodes": tot_nodes,
            "total_fmc": tot_fmc,
            "total_cutoffs": tot_cutoffs,
            "fmc_rate_pct": fmc_rate,
            "elapsed_wall_sec": elapsed,
            "positions": cfg_res
        }
        
    out_file = RAW_DIR / "continuation_history_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw experimental data to {out_file}")

if __name__ == "__main__":
    main()

