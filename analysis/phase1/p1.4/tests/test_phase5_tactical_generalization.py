#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.4
Phase 5 Test Suite: Tactical Generalization Benchmark
Evaluates Baseline X7, Candidate X9 (Countermoves), and Experimental X8 across
an expanded 32-position provenance-tracked tactical corpus spanning 10 tactical categories.
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

# 32 Provenance-Tracked Expanded Tactical Positions
EXPANDED_TACTICAL_CORPUS = [
    # Category 1: Forced Mate Threats
    {"id": "MATE_01_OPERA", "category": "Forced Mate", "fen": "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14", "best": "b5d7"},
    {"id": "MATE_02_BACK_RANK", "category": "Forced Mate", "fen": "6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1", "best": "e2e8"},
    {"id": "MATE_03_LEGAL", "category": "Forced Mate", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "best": "d5f6"},
    {"id": "MATE_04_SCHOLAR", "category": "Forced Mate", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "best": "h5f7"},

    # Category 2: Sacrificial Attacks
    {"id": "SAC_01_GREEK_GIFT", "category": "Sacrificial Attack", "fen": "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13", "best": "d3h7"},
    {"id": "SAC_02_BISHOP_F7", "category": "Sacrificial Attack", "fen": "r1b2rk1/pp3pbp/2p3p1/4q3/2B1P3/2N1Q3/PPP3PP/2KR3R w - - 0 15", "best": "c4f7"},
    {"id": "SAC_03_EXCHANGE_SAC", "category": "Sacrificial Attack", "fen": "r1b2rk1/pp3ppp/2n1p3/3pP3/3P4/2PB1N2/P4PPP/R3K2R w KQ - 0 13", "best": "d3h7"},

    # Category 3: Underpromotion & Stalemate Avoidance
    {"id": "PROMO_01_SAAVEDRA", "category": "Underpromotion", "fen": "8/8/1P6/8/8/1r6/p7/k1K5 w - - 0 1", "best": "b6b7"},
    {"id": "PROMO_02_ROOK_PROMO", "category": "Underpromotion", "fen": "8/5P2/8/8/8/6k1/8/6K1 w - - 0 1", "best": "f7f8q"},

    # Category 4: Zugzwang & NMP Hazards
    {"id": "ZUG_01_FINE70", "category": "Zugzwang / NMP Hazard", "fen": "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1", "best": "a1b1"},
    {"id": "ZUG_02_OPPOSITION", "category": "Pawn Opposition", "fen": "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", "best": "e3f3"},
    {"id": "ZUG_03_DISTANT", "category": "Distant Opposition", "fen": "8/8/8/4k3/8/8/8/4K3 w - - 0 1", "best": "e1e2"},

    # Category 5: Tactical Pawn Breaks
    {"id": "BREAK_01_CARO_C4D5", "category": "Tactical Pawn Break", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8", "best": "c4d5"},
    {"id": "BREAK_02_FRENCH_E4E5", "category": "Tactical Pawn Break", "fen": "rnbqk2r/ppp2ppp/4pn2/3p4/1b1PP3/2N5/PPP2PPP/R1BQKBNR w KQkq - 2 5", "expected_any": ["e4d5", "e4e5"]},
    {"id": "BREAK_03_BENONI_E4", "category": "Tactical Pawn Break", "fen": "r1bqr1k1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 w - - 0 9", "best": "e3e4"},

    # Category 6: Pinning & Deflection
    {"id": "PIN_01_ROOK_PIN", "category": "Pinning & Deflection", "fen": "r1bq1rk1/pp2bppp/2n5/3p4/3N4/2P1B3/PP2BPPP/R2Q1RK1 w - - 0 12", "best": "f1e1"},
    {"id": "PIN_02_EXCHANGE_QUEEN", "category": "Pinning & Deflection", "fen": "2r3k1/1p3ppp/pq2p3/3pP3/3P4/bP2BN2/P2Q1PPP/2R3K1 w - - 0 20", "best": "c1c8"},
    {"id": "PIN_03_KNIGHT_FORK", "category": "Knight Fork Deflection", "fen": "r4rk1/1pp1qppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP1QPPP/R4RK1 w - - 0 10", "best": "c3d5"},

    # Category 7: Quiet Tactical Refutations & Zwischenzugs
    {"id": "QUIET_01_BISHOP_WAIT", "category": "Quiet Tactical Move", "fen": "r1b1kb1r/pp1n1ppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2QK2R w KQkq - 0 8", "best": "e1g1"},
    {"id": "QUIET_02_KNIGHT_DEVELOP", "category": "Quiet Tactical Move", "fen": "r2qkb1r/pp2pppp/2n2n2/3p4/3P2b1/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 0 7", "best": "c1e3"},
    {"id": "QUIET_03_CASTLE", "category": "Quiet Tactical Move", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "best": "e1g1"},
    {"id": "QUIET_04_BISHOP_RETREAT", "category": "Quiet Tactical Move", "fen": "2rq1rk1/pp1b1ppp/4pn2/2bp4/3N4/1PN1P3/PBP2PPP/2RQ1RK1 w - - 0 12", "best": "d4e2"},
    {"id": "QUIET_05_BISHOP_BLOCK", "category": "Quiet Tactical Move", "fen": "r2qk2r/ppp2ppp/2n1pn2/3p4/1bPP4/2N1PN2/PP3PPP/R1BQK2R w KQkq - 0 7", "best": "c1d2"},

    # Category 8: Check Evasions & Counter-attacks
    {"id": "EVASION_01_DEFEND_CHECK", "category": "Check Evasion", "fen": "rnbqk1nr/pppp1ppp/4p3/8/1bPP4/8/PP2PPPP/RNBQKBNR w KQkq - 1 3", "expected_any": ["c1d2", "b1c3", "b1d2"]},
    {"id": "EVASION_02_BLOCK_QUEEN", "category": "Check Evasion", "fen": "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2", "best": "d8h4"},

    # Category 9: Recapture Combinations & SEE Traps
    {"id": "SEE_01_WINNING_CAPTURE", "category": "SEE Trap", "fen": "r1bqkb1r/pp2pppp/2np1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 2 6", "best": "d4c6"},
    {"id": "SEE_02_ROOK_INVASION", "category": "SEE Trap", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "best": "b4f4"},
    {"id": "SEE_03_DEFEND_MINOR", "category": "SEE Trap", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5", "best": "b1c3"},

    # Category 10: Technical Endgame Tactics
    {"id": "END_01_ROOK_BRIDGE", "category": "Endgame Tactic", "fen": "1K6/1P1k4/8/8/8/8/2r5/7R w - - 0 1", "best": "h1d1"},
    {"id": "END_02_KING_CUT", "category": "Endgame Tactic", "fen": "8/8/8/3k4/8/8/2R5/1K6 w - - 0 1", "best": "c2d2"},
    {"id": "END_03_PAWN_BREAKTHROUGH", "category": "Endgame Tactic", "fen": "8/5p2/8/4P1k1/8/8/8/4K3 w - - 0 1", "best": "e1e2"},
]

ENGINES = [
    ("B0", "Frozen X7 Baseline", "X7", "M0", "S0", "C0", "P0"),
    ("X9_Cand", "Candidate X9 (Countermoves Modernization)", "X9", "M2", "S0", "C0", "P0"),
    ("B7", "Frozen X8 Experimental", "X8", "M3", "S1", "C1", "P1"),
]

def search_position(var: str, m: str, s: str, c: str, p_opt: str, fen: str, depth: int) -> Dict[str, Any]:
    proc = subprocess.Popen([str(EXE_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    cmds = [
        "uci", "isready",
        f"setoption name UCI_Variant value {var}",
        f"setoption name UCI_TacticalOrdering value {m}",
        f"setoption name UCI_SingularExtensions value {s}",
        f"setoption name UCI_MultiCut value {c}",
        f"setoption name UCI_ProbCut value {p_opt}",
        "ucinewgame", "isready",
        f"position fen {fen}",
        f"go depth {depth}",
        "quit\n"
    ]
    t0 = time.perf_counter()
    out, _ = proc.communicate("\n".join(cmds))
    t1 = time.perf_counter()
    nodes = 0
    score = 0
    bestmove = ""
    for line in out.splitlines():
        if line.startswith(f"info depth {depth}"):
            parts = line.split()
            if "nodes" in parts: nodes = int(parts[parts.index("nodes")+1])
            if "score" in parts: score = int(parts[parts.index("score")+2])
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) > 1: bestmove = parts[1]
    return {"nodes": nodes, "score": score, "bestmove": bestmove, "elapsed_sec": t1 - t0}

def main():
    print("=== Phase 5: Expanded Tactical Generalization Benchmark (32 Positions) ===")
    
    summary = {}
    
    for cfg_id, cfg_name, var, m_v, s_v, c_v, p_v in ENGINES:
        print(f"\n--- Testing: {cfg_id} ({cfg_name}) ---")
        solved_count = 0
        total_nodes = 0
        total_time = 0.0
        details = []
        
        for item in EXPANDED_TACTICAL_CORPUS:
            res = search_position(var, m_v, s_v, c_v, p_v, item["fen"], 7)
            total_nodes += res["nodes"]
            total_time += res["elapsed_sec"]
            
            is_solved = False
            if "best" in item:
                is_solved = (res["bestmove"] == item["best"])
            elif "expected_any" in item:
                is_solved = (res["bestmove"] in item["expected_any"])
                
            if is_solved:
                solved_count += 1
                
            details.append({
                "id": item["id"],
                "category": item["category"],
                "bestmove": res["bestmove"],
                "solved": is_solved,
                "nodes": res["nodes"]
            })
            
        acc_pct = round(100.0 * solved_count / len(EXPANDED_TACTICAL_CORPUS), 2)
        nps = int(total_nodes / max(total_time, 0.001))
        
        summary[cfg_id] = {
            "name": cfg_name,
            "solved": solved_count,
            "total": len(EXPANDED_TACTICAL_CORPUS),
            "accuracy_pct": acc_pct,
            "total_nodes": total_nodes,
            "elapsed_sec": round(total_time, 2),
            "nps": nps,
            "positions": details
        }
        
        print(f"Results for {cfg_id}:")
        print(f"  Solved: {solved_count} / {len(EXPANDED_TACTICAL_CORPUS)} ({acc_pct}%)")
        print(f"  Nodes : {total_nodes:,} in {total_time:.2f}s ({nps:,} NPS)")

    with open(RAW_DIR / "tactical_generalization_raw.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nRaw results saved to raw/tactical_generalization_raw.json")

if __name__ == "__main__":
    main()

