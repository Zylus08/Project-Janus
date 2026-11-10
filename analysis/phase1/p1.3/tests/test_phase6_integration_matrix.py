#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.3
Phase 6 Test Suite: Search Integration Matrix & Candidate Qualification
Evaluates cumulative integration steps from Baseline X7 to Candidate X8.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
SUITE_50_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.3" / "raw"
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

INTEGRATION_STEPS = [
    ("Step_0_X7_Baseline", "Baseline X7 Control", "X7", "M0", "S0", "C0", "P0"),
    ("Step_1_Tactical_Ordering", "X7 + CapHist & Countermove (M3)", "X7", "M3", "S0", "C0", "P0"),
    ("Step_2_Singular_Extensions", "Step 1 + Singular Extensions (S1)", "X7", "M3", "S1", "C0", "P0"),
    ("Step_3_Multi_Cut", "Step 2 + Multi-Cut Pruning (C1)", "X7", "M3", "S1", "C1", "P0"),
    ("Step_4_ProbCut", "Step 3 + Conservative ProbCut (P1)", "X7", "M3", "S1", "C1", "P1"),
    ("Candidate_X8_Integrated", "Full Candidate X8 (with calibrated LMR)", "X8", "M3", "S1", "C1", "P1"),
]

def run_search(fen: str, depth: int, variant: str, m_val: str, s_val: str, c_val: str, p_val: str) -> Dict[str, Any]:
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
        f"setoption name UCI_Variant value {variant}",
        f"setoption name UCI_TacticalOrdering value {m_val}",
        f"setoption name UCI_SingularExtensions value {s_val}",
        f"setoption name UCI_MultiCut value {c_val}",
        f"setoption name UCI_ProbCut value {p_val}",
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
            toks = line.split()
            if len(toks) > 1:
                bestmove = toks[1]
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
    print("=== Phase 6 Integration Matrix: Stepwise Evaluation to Candidate X8 ===")
    with open(SUITE_50_PATH, "r", encoding="utf-8") as f:
        positions_50 = json.load(f)
    print(f"Loaded {len(positions_50)} suite positions and {len(TACTICAL_CORPUS)} tactical positions.")
    
    matrix_results = {}
    
    for key, desc, var, m_v, s_v, c_v, p_v in INTEGRATION_STEPS:
        print(f"\n--- Testing Integration Step: {key} ({desc}) ---")
        t_start = time.perf_counter()
        
        # 1. Standard 50 Evaluation Suite at d=6
        total_nodes_50 = 0
        total_time_50 = 0.0
        details_50 = []
        
        for pos in positions_50:
            res = run_search(pos["fen"], 6, var, m_v, s_v, c_v, p_v)
            total_nodes_50 += res["nodes"]
            total_time_50 += res["elapsed_sec"]
            details_50.append({
                "id": pos.get("id", ""),
                "nodes": res["nodes"],
                "score": res["score"],
                "bestmove": res["bestmove"]
            })
            
        # 2. Tactical Atlas at d=7
        tactical_solved = 0
        total_nodes_tac = 0
        details_tac = []
        last_telem = {}
        
        for tac in TACTICAL_CORPUS:
            res = run_search(tac["fen"], 7, var, m_v, s_v, c_v, p_v)
            total_nodes_tac += res["nodes"]
            last_telem = res["telemetry"]
            is_solved = (res["bestmove"] == tac["best"])
            if is_solved:
                tactical_solved += 1
            details_tac.append({
                "id": tac["id"],
                "expected": tac["best"],
                "bestmove": res["bestmove"],
                "solved": is_solved,
                "nodes": res["nodes"]
            })
            
        elapsed_total = time.perf_counter() - t_start
        
        matrix_results[key] = {
            "description": desc,
            "variant": var,
            "options": {"M": m_v, "S": s_v, "C": c_v, "P": p_v},
            "suite_50": {
                "total_nodes": total_nodes_50,
                "elapsed_sec": round(total_time_50, 2),
                "nps": int(total_nodes_50 / max(total_time_50, 0.001)),
                "positions": details_50
            },
            "tactical_atlas": {
                "solved": tactical_solved,
                "total": len(TACTICAL_CORPUS),
                "accuracy_pct": round(100.0 * tactical_solved / len(TACTICAL_CORPUS), 2),
                "total_nodes": total_nodes_tac,
                "positions": details_tac
            },
            "total_benchmark_time_sec": round(elapsed_total, 2)
        }
        
        print(f"Results for {key}:")
        print(f"  Suite 50 Nodes: {total_nodes_50:,} (Time: {total_time_50:.2f}s, NPS: {matrix_results[key]['suite_50']['nps']:,})")
        print(f"  Tactical Solved: {tactical_solved}/{len(TACTICAL_CORPUS)} ({matrix_results[key]['tactical_atlas']['accuracy_pct']}%) in {total_nodes_tac:,} nodes")

    raw_out = RAW_DIR / "search_integration_matrix_raw.json"
    with open(raw_out, "w", encoding="utf-8") as f:
        json.dump(matrix_results, f, indent=2)
    print(f"\nRaw results saved to {raw_out}")

if __name__ == "__main__":
    main()

