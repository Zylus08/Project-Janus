#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.4
Phase 1 Test Suite: Full Isolation of X8 Search Modifications (B0 through B7)
Verifies:
  1. Bit-exact parity of B0 with frozen janus_classical_x7.exe control.
  2. Isolated impact of every individual P1.3 search mechanism across standard suite (d=6) and tactical atlas (d=7).
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
FROZEN_X7_EXE = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
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

CONFIGURATIONS = [
    ("B0", "Frozen X7 Baseline", "X7", "M0", "S0", "C0", "P0"),
    ("B1", "X7 + Capture History", "X7", "M1", "S0", "C0", "P0"),
    ("B2", "X7 + Countermove Ordering", "X7", "M2", "S0", "C0", "P0"),
    ("B3", "X7 + Combined CapHist & Countermove", "X7", "M3", "S0", "C0", "P0"),
    ("B4", "X7 + Singular Extensions", "X7", "M0", "S1", "C0", "P0"),
    ("B5", "X7 + Singular Extensions + Multi-Cut", "X7", "M0", "S1", "C1", "P0"),
    ("B6", "X7 + Conservative ProbCut", "X7", "M0", "S0", "C0", "P1"),
    ("B7", "Full Frozen X8", "X8", "M3", "S1", "C1", "P1"),
]

def run_engine_search(exe: Path, var: str, m: str, s: str, c: str, p_opt: str, fen: str, depth: int) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(exe)],
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
        f"position fen {fen}",
        f"go depth {depth}",
        "telemetry_report",
        "quit\n"
    ]
    
    t0 = time.perf_counter()
    out, _ = proc.communicate("\n".join(cmds))
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
            if "nodes" in toks: nodes = int(toks[toks.index("nodes") + 1])
            if "score" in toks: score = int(toks[toks.index("score") + 2])
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
        "score": score,
        "bestmove": bestmove,
        "elapsed_sec": t1 - t0,
        "telemetry": telemetry
    }

def main():
    print("=== Milestone P1.4 Phase 1: Feature Isolation (B0..B7) ===")
    
    # 1. Parity Check: B0 on new engine vs Frozen janus_classical_x7.exe
    print("\n--- Step 1: Strict Bit-Exact Parity Check (B0 vs Frozen X7 Control) ---")
    test_positions = [
        ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 6),
        ("KiwiPete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 5),
        ("Middlegame Pos 3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 7),
        ("Tactical Pos 4", "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5", 6),
        ("Endgame Pos 5", "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", 8),
    ]
    
    parity_passed = True
    for name, fen, d in test_positions:
        res_ctrl = run_engine_search(FROZEN_X7_EXE, "X7", "M0", "S0", "C0", "P0", fen, d)
        res_b0 = run_engine_search(EXE_PATH, "X7", "M0", "S0", "C0", "P0", fen, d)
        
        match = (res_ctrl["nodes"] == res_b0["nodes"]) and (res_ctrl["score"] == res_b0["score"]) and (res_ctrl["bestmove"] == res_b0["bestmove"])
        if not match: parity_passed = False
        status = "PASS" if match else "FAIL"
        print(f"  [{status}] {name}: Ctrl(n={res_ctrl['nodes']}, s={res_ctrl['score']}, bm={res_ctrl['bestmove']}) vs B0(n={res_b0['nodes']}, s={res_b0['score']}, bm={res_b0['bestmove']})")
        
    assert parity_passed, "FATAL: Parity check between B0 and Frozen X7 failed!"
    print("Bit-exact parity verified with 100% compliance.\n")
    
    # 2. Evaluate all configurations B0..B7
    with open(SUITE_50_PATH, "r", encoding="utf-8") as f:
        positions_50 = json.load(f)
        
    results_matrix = {}
    
    for cfg_id, cfg_name, var, m_v, s_v, c_v, p_v in CONFIGURATIONS:
        print(f"Evaluating {cfg_id}: {cfg_name}...")
        t_start = time.perf_counter()
        
        # A. Suite 50 (d=6)
        suite_nodes = 0
        suite_time = 0.0
        details_50 = []
        tot_capthist_cutoffs = 0
        tot_countermove_cutoffs = 0
        tot_se_extended = 0
        tot_multicut_cutoffs = 0
        tot_probcut_cutoffs = 0
        
        for pos in positions_50:
            res = run_engine_search(EXE_PATH, var, m_v, s_v, c_v, p_v, pos["fen"], 6)
            suite_nodes += res["nodes"]
            suite_time += res["elapsed_sec"]
            telem = res["telemetry"]
            tot_capthist_cutoffs += telem.get("capthist_cutoffs", 0)
            tot_countermove_cutoffs += telem.get("countermove_cutoffs", 0)
            tot_se_extended += telem.get("se_extended", 0)
            tot_multicut_cutoffs += telem.get("multicut_cutoffs", 0)
            tot_probcut_cutoffs += telem.get("probcut_cutoffs", 0)
            details_50.append({
                "id": pos.get("id", ""),
                "nodes": res["nodes"],
                "score": res["score"],
                "bestmove": res["bestmove"]
            })
            
        # B. Tactical Atlas (d=7)
        tac_nodes = 0
        tac_solved = 0
        details_tac = []
        
        for tac in TACTICAL_CORPUS:
            res = run_engine_search(EXE_PATH, var, m_v, s_v, c_v, p_v, tac["fen"], 7)
            tac_nodes += res["nodes"]
            is_solved = (res["bestmove"] == tac["best"])
            if is_solved: tac_solved += 1
            details_tac.append({
                "id": tac["id"],
                "expected": tac["best"],
                "bestmove": res["bestmove"],
                "solved": is_solved,
                "nodes": res["nodes"]
            })
            
        elapsed_total = time.perf_counter() - t_start
        nps_50 = int(suite_nodes / max(suite_time, 0.001))
        
        results_matrix[cfg_id] = {
            "name": cfg_name,
            "variant": var,
            "options": {"M": m_v, "S": s_v, "C": c_v, "P": p_v},
            "suite_50": {
                "nodes": suite_nodes,
                "elapsed_sec": round(suite_time, 2),
                "nps": nps_50,
                "capthist_cutoffs": tot_capthist_cutoffs,
                "countermove_cutoffs": tot_countermove_cutoffs,
                "se_extended": tot_se_extended,
                "multicut_cutoffs": tot_multicut_cutoffs,
                "probcut_cutoffs": tot_probcut_cutoffs,
            },
            "tactical_atlas": {
                "solved": tac_solved,
                "total": len(TACTICAL_CORPUS),
                "accuracy_pct": round(100.0 * tac_solved / len(TACTICAL_CORPUS), 2),
                "nodes": tac_nodes,
                "positions": details_tac
            },
            "total_benchmark_time_sec": round(elapsed_total, 2)
        }
        
        print(f"  -> Suite 50: {suite_nodes:,} nodes ({nps_50:,} NPS)")
        print(f"  -> Tactical: {tac_solved}/{len(TACTICAL_CORPUS)} solved ({results_matrix[cfg_id]['tactical_atlas']['accuracy_pct']}%) in {tac_nodes:,} nodes")

    with open(RAW_DIR / "feature_isolation_raw.json", "w", encoding="utf-8") as f:
        json.dump(results_matrix, f, indent=2)
    print(f"\nAll results saved to raw/feature_isolation_raw.json")

if __name__ == "__main__":
    main()

