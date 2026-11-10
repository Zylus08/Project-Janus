#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.2
Phase 2 Test Suite: Dynamic LMR Ablation (L0, L1, L2, L3)
Tests isolated impact of dynamic logarithmic and history-modulated LMR on search efficiency and tactical solution preservation.
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
    ("L0", "Static Base LMR (X6 Baseline)", 0),
    ("L1", "Logarithmic Table LMR", 1),
    ("L2", "History Modulated LMR", 2),
    ("L3", "Dynamic Conthist Modulated LMR", 3),
]

SEARCH_DEPTH = 6

def run_uci_search(fen: str, depth: int, lmr_mode: int):
    p = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    l_str = f"L{lmr_mode}"
    commands = [
        "uci",
        "isready",
        "setoption name UCI_Variant value X6",
        f"setoption name UCI_DynamicLMR value {l_str}",
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
    print(f"=== Project Janus P1.2 — Phase 2: Dynamic LMR Ablation ===")
    print(f"Loading suite: {SUITE_PATH}")
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    print(f"Loaded {len(positions)} diagnostic positions. Search depth: {SEARCH_DEPTH}\n")
    
    results = {}
    for code, label, mode in CONFIGS:
        print(f"--- Running {code}: {label} ---")
        cfg_res = []
        tot_nodes = 0
        tot_reduced = 0
        tot_fmc = 0
        tot_cutoffs = 0
        t_start = time.perf_counter()
        
        for idx, pos in enumerate(positions):
            fen = pos["fen"]
            res = run_uci_search(fen, SEARCH_DEPTH, mode)
            res["pos_id"] = pos.get("id", f"pos_{idx}")
            res["cat"] = pos.get("cat", "Unknown")
            cfg_res.append(res)
            
            tot_nodes += res["nodes"]
            tel = res.get("telemetry", {})
            tot_reduced += tel.get("dynamic_lmr_reduced", 0)
            tot_fmc += tel.get("first_move_cutoffs", 0)
            tot_cutoffs += tel.get("total_cutoffs", 0)
            
        elapsed = time.perf_counter() - t_start
        fmc_rate = (tot_fmc / tot_cutoffs * 100.0) if tot_cutoffs > 0 else 0.0
        
        print(f"Completed {code}:")
        print(f"  Total Nodes: {tot_nodes:,}")
        print(f"  Dynamic LMR Reductions: {tot_reduced:,}")
        print(f"  First-Move Cutoff Rate: {fmc_rate:.2f}%")
        print(f"  Wall Time: {elapsed:.2f}s\n")
        
        results[code] = {
            "label": label,
            "mode": mode,
            "total_nodes": tot_nodes,
            "total_reduced": tot_reduced,
            "total_fmc": tot_fmc,
            "total_cutoffs": tot_cutoffs,
            "fmc_rate_pct": fmc_rate,
            "elapsed_wall_sec": elapsed,
            "positions": cfg_res
        }
        
    out_file = RAW_DIR / "dynamic_lmr_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw experimental data to {out_file}")

if __name__ == "__main__":
    main()

