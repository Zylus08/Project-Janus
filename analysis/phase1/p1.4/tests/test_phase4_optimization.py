#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.4
Phase 4 Test Suite: Surgical Selectivity Optimization & X9 Candidate Evaluation
Compares:
  - B0: Frozen X7 Baseline
  - B2: X7 + Countermoves Only
  - X9: Candidate X9 (Surgically Optimized Selectivity Economics)
  - B7: Frozen X8
Across fixed-depth suites and fixed-time (1000ms) performance.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
SUITE_50_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.4" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TACTICAL_CORPUS = [
    {"id": "TAC_01", "fen": "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14", "best": "b5d7"},
    {"id": "TAC_02", "fen": "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13", "best": "d3h7"},
    {"id": "TAC_03", "fen": "8/8/1P6/8/8/1r6/p7/k1K5 w - - 0 1", "best": "b6b7"},
    {"id": "TAC_04", "fen": "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1", "best": "a1b1"},
    {"id": "TAC_05", "fen": "r1b2rk1/pp3ppp/2n1p3/3pP3/3P4/2PB1N2/P4PPP/R3K2R w KQ - 0 13", "best": "d3h7"},
    {"id": "TAC_06", "fen": "r1bq1rk1/pp2bppp/2n5/3p4/3N4/2P1B3/PP2BPPP/R2Q1RK1 w - - 0 12", "best": "f1e1"},
    {"id": "TAC_07", "fen": "2r3k1/1p3ppp/pq2p3/3pP3/3P4/bP2BN2/P2Q1PPP/2R3K1 w - - 0 20", "best": "c1c8"},
    {"id": "TAC_08", "fen": "r1b2rk1/pp3pbp/2p3p1/4q3/2B1P3/2N1Q3/PPP3PP/2KR3R w - - 0 15", "best": "c4f7"},
    {"id": "TAC_09", "fen": "r4rk1/1pp1qppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP1QPPP/R4RK1 w - - 0 10", "best": "c3d5"},
    {"id": "TAC_10", "fen": "r1b1kb1r/pp1n1ppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2QK2R w KQkq - 0 8", "best": "e1g1"},
    {"id": "TAC_11", "fen": "r2qkb1r/pp2pppp/2n2n2/3p4/3P2b1/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 0 7", "best": "c1e3"},
    {"id": "TAC_12", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "best": "e1g1"},
    {"id": "TAC_13", "fen": "r1bqr1k1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 w - - 0 9", "best": "e3e4"},
    {"id": "TAC_14", "fen": "2rq1rk1/pp1b1ppp/4pn2/2bp4/3N4/1PN1P3/PBP2PPP/2RQ1RK1 w - - 0 12", "best": "d4e2"},
    {"id": "TAC_15", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8", "best": "c4d5"},
    {"id": "TAC_16", "fen": "r2qk2r/ppp2ppp/2n1pn2/3p4/1bPP4/2N1PN2/PP3PPP/R1BQK2R w KQkq - 0 7", "best": "c1d2"}
]

ARCHETYPES_10 = [
    ("TAC_DEFLECT", "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14", "b5d7"),
    ("TAC_GREEK_GIFT", "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13", "d3h7"),
    ("TAC_PAWN_BREAK", "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8", "c4d5"),
    ("TAC_PINNING", "r1bq1rk1/pp2bppp/2n5/3p4/3N4/2P1B3/PP2BPPP/R2Q1RK1 w - - 0 12", "f1e1"),
    ("STRAT_STARTPOS", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", None),
    ("STRAT_KIWIPETE", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", None),
    ("CLOSED_FRENCH", "rnbqk2r/ppp2ppp/4pn2/3p4/1b1PP3/2N5/PPP2PPP/R1BQKBNR w KQkq - 2 5", "e4d5"),
    ("END_PHILIDOR", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "b4f4"),
    ("END_PAWN_OPP", "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", "e3f3"),
    ("ZUGZWANG_FINE", "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1", "a1b1"),
]

COMPARE_CONFIGS = [
    ("B0", "Frozen X7 Baseline", "X7", "M0", "S0", "C0", "P0"),
    ("B2", "X7 + Countermoves", "X7", "M2", "S0", "C0", "P0"),
    ("X9_Cand", "Candidate X9 (Surgically Optimized)", "X9", "M4", "S3", "C1", "P3"),
    ("B7", "Full Frozen X8", "X8", "M3", "S1", "C1", "P1"),
]

def search(var: str, m: str, s: str, c: str, p_opt: str, fen: str, depth: int = None, movetime_ms: int = None) -> Dict[str, Any]:
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
        f"position fen {fen}"
    ]
    if depth is not None:
        cmds.append(f"go depth {depth}")
    elif movetime_ms is not None:
        cmds.append(f"go movetime {movetime_ms}")
    cmds.append("quit\n")
    
    t0 = time.perf_counter()
    out, _ = proc.communicate("\n".join(cmds))
    t1 = time.perf_counter()
    
    nodes = 0
    max_d = 0
    score = 0
    bestmove = ""
    
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("info"):
            toks = line.split()
            if "depth" in toks:
                idx = toks.index("depth") + 1
                if idx < len(toks):
                    d = int(toks[idx])
                    if d > max_d: max_d = d
            if "nodes" in toks:
                idx = toks.index("nodes") + 1
                if idx < len(toks): nodes = int(toks[idx])
            if "score" in toks:
                idx = toks.index("score") + 2
                if idx < len(toks): score = int(toks[idx])
        elif line.startswith("bestmove"):
            toks = line.split()
            if len(toks) > 1: bestmove = toks[1]
            
    return {"nodes": nodes, "depth": max_d, "score": score, "bestmove": bestmove, "elapsed_sec": t1 - t0}

def main():
    print("=== Phase 4: Surgical Selectivity Optimization & Candidate X9 Benchmark ===")
    
    with open(SUITE_50_PATH, "r", encoding="utf-8") as f:
        positions_50 = json.load(f)
        
    summary = {}
    
    for cfg_id, cfg_name, var, m_v, s_v, c_v, p_v in COMPARE_CONFIGS:
        print(f"\n--- Testing Configuration: {cfg_id} ({cfg_name}) ---")
        
        # 1. Suite 50 (d=6)
        tot_nodes_50 = 0
        tot_time_50 = 0.0
        for pos in positions_50:
            res = search(var, m_v, s_v, c_v, p_v, pos["fen"], depth=6)
            tot_nodes_50 += res["nodes"]
            tot_time_50 += res["elapsed_sec"]
            
        nps_50 = int(tot_nodes_50 / max(tot_time_50, 0.001))
        
        # 2. Tactical Atlas (d=7)
        tot_nodes_tac = 0
        solved_tac = 0
        for tac in TACTICAL_CORPUS:
            res = search(var, m_v, s_v, c_v, p_v, tac["fen"], depth=7)
            tot_nodes_tac += res["nodes"]
            if res["bestmove"] == tac["best"]:
                solved_tac += 1
                
        # 3. Fixed Time (1000ms on 10 archetypes)
        depths_1s = []
        nodes_1s = []
        solved_1s = 0
        verifiable_1s = 0
        for name, fen, exp in ARCHETYPES_10:
            res = search(var, m_v, s_v, c_v, p_v, fen, movetime_ms=1000)
            depths_1s.append(res["depth"])
            nodes_1s.append(res["nodes"])
            if exp is not None:
                verifiable_1s += 1
                if res["bestmove"] == exp:
                    solved_1s += 1
                    
        avg_d_1s = round(sum(depths_1s) / len(depths_1s), 2)
        tot_n_1s = sum(nodes_1s)
        acc_1s = round(100.0 * solved_1s / verifiable_1s, 1) if verifiable_1s > 0 else 0.0
        
        summary[cfg_id] = {
            "name": cfg_name,
            "suite_50": {"nodes": tot_nodes_50, "time_sec": round(tot_time_50, 2), "nps": nps_50},
            "tactical_atlas_d7": {"solved": solved_tac, "total": len(TACTICAL_CORPUS), "pct": round(100.0 * solved_tac / len(TACTICAL_CORPUS), 1), "nodes": tot_nodes_tac},
            "fixed_time_1000ms": {"avg_depth": avg_d_1s, "total_nodes": tot_n_1s, "accuracy_pct": acc_1s, "solved": f"{solved_1s}/{verifiable_1s}"}
        }
        
        print(f"Results for {cfg_id}:")
        print(f"  Suite 50 (d=6)       : {tot_nodes_50:,} nodes | {nps_50:,} NPS")
        print(f"  Tactical Atlas (d=7) : {solved_tac}/{len(TACTICAL_CORPUS)} solved ({summary[cfg_id]['tactical_atlas_d7']['pct']}%) in {tot_nodes_tac:,} nodes")
        print(f"  Fixed Time (1000ms)  : Avg Depth = {avg_d_1s} plies | Accuracy = {acc_1s}% ({solved_1s}/{verifiable_1s}) | Nodes = {tot_n_1s:,}")

    with open(RAW_DIR / "selectivity_optimization_raw.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nOptimization results saved to raw/selectivity_optimization_raw.json")

if __name__ == "__main__":
    main()

