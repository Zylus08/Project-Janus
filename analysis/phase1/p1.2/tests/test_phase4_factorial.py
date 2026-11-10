#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.2
Phase 4 Test Suite: Search-Evaluation Interaction 2x2 Factorial
Tests:
  Cell 1: Search X6 (H0, L0) x Eval E0 (Base Material+PSQT) -> Frozen X6 Baseline
  Cell 2: Search X6 (H0, L0) x Eval E5 (Combined Positional) -> Eval Upgrade Only
  Cell 3: Search X7 (H3, L3) x Eval E0 (Base Material+PSQT) -> Search Upgrade Only
  Cell 4: Search X7 (H3, L3) x Eval E5 (Combined Positional) -> Full Candidate X7
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

FACTORIAL_CELLS = [
    {
        "id": "CELL_1_X6_E0",
        "label": "Search X6 (H0,L0) x Eval E0 (Frozen X6)",
        "search_variant": "X6",
        "h_mode": "H0",
        "l_mode": "L0",
        "e_mode": "E0"
    },
    {
        "id": "CELL_2_X6_E5",
        "label": "Search X6 (H0,L0) x Eval E5 (Eval Modernization Only)",
        "search_variant": "X6",
        "h_mode": "H0",
        "l_mode": "L0",
        "e_mode": "E5"
    },
    {
        "id": "CELL_3_X7_E0",
        "label": "Search X7 (H3,L3) x Eval E0 (Search Intelligence Only)",
        "search_variant": "X7",
        "h_mode": "H3",
        "l_mode": "L3",
        "e_mode": "E0"
    },
    {
        "id": "CELL_4_X7_E5",
        "label": "Search X7 (H3,L3) x Eval E5 (Full Candidate X7)",
        "search_variant": "X7",
        "h_mode": "H3",
        "l_mode": "L3",
        "e_mode": "E5"
    },
]

SEARCH_DEPTH = 6

def run_cell_search(fen: str, depth: int, cell: dict):
    p = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    commands = [
        "uci",
        "isready",
        f"setoption name UCI_Variant value {cell['search_variant']}",
        f"setoption name UCI_ContinuationHistory value {cell['h_mode']}",
        f"setoption name UCI_DynamicLMR value {cell['l_mode']}",
        f"setoption name UCI_ClassicalEval value {cell['e_mode']}",
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
    print(f"=== Project Janus P1.2 — Phase 4: Search-Evaluation Interaction 2x2 Factorial ===")
    print(f"Loading suite: {SUITE_PATH}")
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    print(f"Loaded {len(positions)} diagnostic positions. Search depth: {SEARCH_DEPTH}\n")
    
    results = {}
    for cell in FACTORIAL_CELLS:
        cid = cell["id"]
        label = cell["label"]
        print(f"--- Running {cid}: {label} ---")
        cfg_res = []
        tot_nodes = 0
        tot_fmc = 0
        tot_cutoffs = 0
        tot_eval_calls = 0
        t_start = time.perf_counter()
        
        for idx, pos in enumerate(positions):
            fen = pos["fen"]
            res = run_cell_search(fen, SEARCH_DEPTH, cell)
            res["pos_id"] = pos.get("id", f"pos_{idx}")
            res["cat"] = pos.get("cat", "Unknown")
            cfg_res.append(res)
            
            tot_nodes += res["nodes"]
            tel = res.get("telemetry", {})
            tot_fmc += tel.get("first_move_cutoffs", 0)
            tot_cutoffs += tel.get("total_cutoffs", 0)
            tot_eval_calls += tel.get("eval_calls", 0)
            
        elapsed = time.perf_counter() - t_start
        fmc_rate = (tot_fmc / tot_cutoffs * 100.0) if tot_cutoffs > 0 else 0.0
        nps = (tot_nodes / elapsed) if elapsed > 0 else 0.0
        
        print(f"Completed {cid}:")
        print(f"  Total Nodes: {tot_nodes:,}")
        print(f"  First-Move Cutoffs: {fmc_rate:.2f}%")
        print(f"  Throughput: {nps:,.0f} NPS")
        print(f"  Wall Time: {elapsed:.2f}s\n")
        
        results[cid] = {
            "cell": cell,
            "total_nodes": tot_nodes,
            "total_fmc": tot_fmc,
            "total_cutoffs": tot_cutoffs,
            "fmc_rate_pct": fmc_rate,
            "nps": nps,
            "elapsed_wall_sec": elapsed,
            "positions": cfg_res
        }
        
    out_file = RAW_DIR / "search_eval_factorial_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw experimental data to {out_file}")

if __name__ == "__main__":
    main()

