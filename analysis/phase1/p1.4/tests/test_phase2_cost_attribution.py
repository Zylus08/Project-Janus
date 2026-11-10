#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.4
Phase 2 Test Suite: Search Cost Attribution
Measures:
  1. Extra nodes and verification search overhead per mechanism.
  2. Fixed-time nominal depth completed under 500ms and 1000ms clock limits.
  3. First-move beta cutoff rates and move ordering quality.
  4. Node-to-benefit ratio of Singular Extensions, Multi-Cut, ProbCut, and Countermoves.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.4" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Diagnostic positions representing diverse chess archetypes
ARCHETYPE_POSITIONS = [
    ("Tactical_OperaMate", "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14", "b5d7"),
    ("Tactical_GreekGift", "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13", "d3h7"),
    ("Tactical_PawnBreak", "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8", "c4d5"),
    ("Tactical_Pinning", "r1bq1rk1/pp2bppp/2n5/3p4/3N4/2P1B3/PP2BPPP/R2Q1RK1 w - - 0 12", "f1e1"),
    ("Strategic_Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "b1c3"),
    ("Strategic_KiwiPete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "d5e6"),
    ("Closed_French", "rnbqk2r/ppp2ppp/4pn2/3p4/1b1PP3/2N5/PPP2PPP/R1BQKBNR w KQkq - 2 5", "e4d5"),
    ("Endgame_KPK", "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", "e3f3"),
    ("Endgame_Rook", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "b4f4"),
    ("Zugzwang_Fine70", "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1", "a1b1"),
]

CONFIGS = [
    ("B0", "Frozen X7 Baseline", "X7", "M0", "S0", "C0", "P0"),
    ("B2", "X7 + Countermoves", "X7", "M2", "S0", "C0", "P0"),
    ("B3", "X7 + CapHist & Countermoves", "X7", "M3", "S0", "C0", "P0"),
    ("B4", "X7 + Singular Extensions", "X7", "M0", "S1", "C0", "P0"),
    ("B5", "X7 + Singular Extensions + Multi-Cut", "X7", "M0", "S1", "C1", "P0"),
    ("B6", "X7 + Conservative ProbCut", "X7", "M0", "S0", "C0", "P1"),
    ("B7", "Full Frozen X8", "X8", "M3", "S1", "C1", "P1"),
]

def run_uci_search(var: str, m: str, s: str, c: str, p_opt: str, fen: str, depth: int = None, movetime_ms: int = None) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    cmds = [
        "uci",
        "isready",
        f"setoption name UCI_Variant value {var}",
        f"setoption name UCI_TacticalOrdering value {m}",
        f"setoption name UCI_SingularExtensions value {s}",
        f"setoption name UCI_MultiCut value {c}",
        f"setoption name UCI_ProbCut value {p_opt}",
        "ucinewgame",
        "isready",
        "telemetry_reset",
        f"position fen {fen}"
    ]
    if depth is not None:
        cmds.append(f"go depth {depth}")
    elif movetime_ms is not None:
        cmds.append(f"go movetime {movetime_ms}")
        
    cmds.append("telemetry_report")
    cmds.append("quit\n")
    
    t0 = time.perf_counter()
    out, _ = proc.communicate("\n".join(cmds))
    t1 = time.perf_counter()
    
    nodes = 0
    max_depth = 0
    score = 0
    bestmove = ""
    telemetry = {}
    
    in_telemetry = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("info"):
            toks = line.split()
            if "depth" in toks:
                d_idx = toks.index("depth") + 1
                if d_idx < len(toks):
                    cur_d = int(toks[d_idx])
                    if cur_d > max_depth: max_depth = cur_d
            if "nodes" in toks:
                n_idx = toks.index("nodes") + 1
                if n_idx < len(toks): nodes = int(toks[n_idx])
            if "score" in toks:
                s_idx = toks.index("score") + 2
                if s_idx < len(toks): score = int(toks[s_idx])
        elif line.startswith("bestmove"):
            toks = line.split()
            if len(toks) > 1: bestmove = toks[1]
        elif line == "TELEMETRY_START":
            in_telemetry = True
        elif line == "TELEMETRY_END":
            in_telemetry = False
        elif in_telemetry and line:
            parts = line.split()
            if len(parts) >= 2:
                try: telemetry[parts[0]] = int(parts[1])
                except ValueError: telemetry[parts[0]] = parts[1]
                
    return {
        "nodes": nodes,
        "depth": max_depth,
        "score": score,
        "bestmove": bestmove,
        "elapsed_sec": t1 - t0,
        "telemetry": telemetry
    }

def main():
    print("=== Phase 2 Search Cost Attribution Benchmark ===")
    
    summary = {}
    
    # 1. Fixed Depth Work (d=7 across the 10 archetype positions)
    print("\n--- Part 1: Fixed-Depth Work (d=7 across Archetype Corpus) ---")
    fixed_depth_results = {}
    for cfg_id, cfg_name, var, m_v, s_v, c_v, p_v in CONFIGS:
        tot_nodes = 0
        tot_time = 0.0
        tot_se_probes = 0
        tot_se_extended = 0
        tot_multicut = 0
        tot_probcut_probes = 0
        tot_probcut_cutoffs = 0
        tot_capthist_cutoffs = 0
        tot_countermove_cutoffs = 0
        details = []
        
        for name, fen, expected in ARCHETYPE_POSITIONS:
            res = run_uci_search(var, m_v, s_v, c_v, p_v, fen, depth=7)
            tot_nodes += res["nodes"]
            tot_time += res["elapsed_sec"]
            telem = res["telemetry"]
            tot_se_probes += telem.get("se_probes", 0)
            tot_se_extended += telem.get("se_extended", 0)
            tot_multicut += telem.get("multicut_cutoffs", 0)
            tot_probcut_probes += telem.get("probcut_probes", 0)
            tot_probcut_cutoffs += telem.get("probcut_cutoffs", 0)
            tot_capthist_cutoffs += telem.get("capthist_cutoffs", 0)
            tot_countermove_cutoffs += telem.get("countermove_cutoffs", 0)
            details.append({
                "pos": name,
                "nodes": res["nodes"],
                "score": res["score"],
                "bestmove": res["bestmove"],
                "solved": (res["bestmove"] == expected)
            })
            
        fixed_depth_results[cfg_id] = {
            "name": cfg_name,
            "total_nodes": tot_nodes,
            "elapsed_sec": round(tot_time, 3),
            "nps": int(tot_nodes / max(tot_time, 0.001)),
            "se_probes": tot_se_probes,
            "se_extended": tot_se_extended,
            "multicut_cutoffs": tot_multicut,
            "probcut_probes": tot_probcut_probes,
            "probcut_cutoffs": tot_probcut_cutoffs,
            "capthist_cutoffs": tot_capthist_cutoffs,
            "countermove_cutoffs": tot_countermove_cutoffs,
            "positions": details
        }
        print(f"  {cfg_id:2s} ({cfg_name:32s}): {tot_nodes:,} nodes in {tot_time:.2f}s | SE ext: {tot_se_extended}/{tot_se_probes} | MC: {tot_multicut} | PC: {tot_probcut_cutoffs}")

    # 2. Fixed Time Performance (500ms and 1000ms clock limits)
    print("\n--- Part 2: Fixed-Time Nominal Depth Analysis (movetime=500ms & 1000ms) ---")
    fixed_time_results = {}
    for t_ms in [500, 1000]:
        fixed_time_results[f"time_{t_ms}ms"] = {}
        for cfg_id, cfg_name, var, m_v, s_v, c_v, p_v in CONFIGS:
            depths = []
            nodes_list = []
            for name, fen, expected in ARCHETYPE_POSITIONS:
                res = run_uci_search(var, m_v, s_v, c_v, p_v, fen, movetime_ms=t_ms)
                depths.append(res["depth"])
                nodes_list.append(res["nodes"])
                
            avg_d = round(sum(depths) / len(depths), 2)
            tot_n = sum(nodes_list)
            fixed_time_results[f"time_{t_ms}ms"][cfg_id] = {
                "name": cfg_name,
                "avg_completed_depth": avg_d,
                "total_nodes_searched": tot_n,
                "depths": depths
            }
            print(f"  [{t_ms}ms] {cfg_id:2s} ({cfg_name:32s}): Avg Completed Depth = {avg_d:4.2f} plies | Total Nodes = {tot_n:,}")

    summary["fixed_depth"] = fixed_depth_results
    summary["fixed_time"] = fixed_time_results
    
    with open(RAW_DIR / "selectivity_cost_attribution_raw.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nCost attribution raw data saved to raw/selectivity_cost_attribution_raw.json")

if __name__ == "__main__":
    main()

