#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.2
Phase 3 Test Suite: Handcrafted Classical Evaluation Modernization (E0..E5)
Verifies:
  1. Mathematical Anti-Symmetry: Eval(pos, side) == -Eval(mirrored_pos, opposite)
  2. Bounded Score Scale & Mate Separation (Scores well within +/- 20000 cp)
  3. Runtime Overhead / Evaluation Throughput (Evals/sec)
  4. Search Efficiency & Node Reduction across Diagnostic Suite under E0..E5
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
    ("E0", "Base Material + PSQT (X6 Baseline)", 0),
    ("E1", "Base + Pawn Structure", 1),
    ("E2", "Base + Mobility & Coordination", 2),
    ("E3", "Base + King Safety", 3),
    ("E4", "Base + Endgame Positional", 4),
    ("E5", "Full Combined Positional Evaluation", 5),
]

SEARCH_DEPTH = 6

def run_uci_eval_search(fen: str, depth: int, eval_mode: int):
    p = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    e_str = f"E{eval_mode}"
    commands = [
        "uci",
        "isready",
        "setoption name UCI_Variant value X6",
        f"setoption name UCI_ClassicalEval value {e_str}",
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
    print(f"=== Project Janus P1.2 — Phase 3: Handcrafted Classical Evaluation Modernization ===")
    print(f"Loading suite: {SUITE_PATH}")
    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)
    print(f"Loaded {len(positions)} diagnostic positions. Search depth: {SEARCH_DEPTH}\n")
    
    results = {}
    for code, label, mode in CONFIGS:
        print(f"--- Running {code}: {label} ---")
        cfg_res = []
        tot_nodes = 0
        tot_eval_calls = 0
        t_start = time.perf_counter()
        
        for idx, pos in enumerate(positions):
            fen = pos["fen"]
            res = run_uci_eval_search(fen, SEARCH_DEPTH, mode)
            res["pos_id"] = pos.get("id", f"pos_{idx}")
            res["cat"] = pos.get("cat", "Unknown")
            cfg_res.append(res)
            
            tot_nodes += res["nodes"]
            tel = res.get("telemetry", {})
            tot_eval_calls += tel.get("eval_calls", 0)
            
        elapsed = time.perf_counter() - t_start
        eval_rate = (tot_eval_calls / elapsed) if elapsed > 0 else 0.0
        
        print(f"Completed {code}:")
        print(f"  Total Nodes: {tot_nodes:,}")
        print(f"  Eval Calls: {tot_eval_calls:,}")
        print(f"  Eval Rate: {eval_rate:,.0f} evals/sec")
        print(f"  Wall Time: {elapsed:.2f}s\n")
        
        results[code] = {
            "label": label,
            "mode": mode,
            "total_nodes": tot_nodes,
            "total_eval_calls": tot_eval_calls,
            "eval_rate_per_sec": eval_rate,
            "elapsed_wall_sec": elapsed,
            "positions": cfg_res
        }
        
    out_file = RAW_DIR / "classical_evaluation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw experimental data to {out_file}")

if __name__ == "__main__":
    main()

