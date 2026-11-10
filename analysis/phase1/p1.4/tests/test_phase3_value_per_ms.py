#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.4
Phase 3 Test Suite: Search Value per Millisecond
Measures search depth, nodes, throughput, bestmove stability, and solution accuracy
across 4 distinct time controls (100ms, 250ms, 1000ms, 3000ms) over an independent
20-position multi-archetype corpus.
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

# 20 Independent Multi-Archetype Positions with proven reference moves
INDEPENDENT_CORPUS = [
    # 1. Tactical
    {"id": "TAC_DEFLECT", "archetype": "Tactical Deflection", "fen": "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14", "expected": "b5d7"},
    {"id": "TAC_GREEK_GIFT", "archetype": "Sacrificial Attack", "fen": "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13", "expected": "d3h7"},
    {"id": "TAC_PAWN_BREAK", "archetype": "Tactical Pawn Break", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 8", "expected": "c4d5"},
    {"id": "TAC_SMOTHER", "archetype": "Smothered Mate Threat", "fen": "6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1", "expected": "e2e8"},

    # 2. Quiet Strategic
    {"id": "STRAT_STARTPOS", "archetype": "Quiet Opening", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "expected": None},
    {"id": "STRAT_KIWIPETE", "archetype": "Complex Middlegame", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "expected": None},
    {"id": "STRAT_BISHOP_PAIR", "archetype": "Minority / Bishop Pair", "fen": "r1bqkb1r/pp2pppp/2np1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 2 6", "expected": "d4c6"},
    {"id": "STRAT_OUTPOST", "archetype": "Knight Outpost", "fen": "r4rk1/1pp1qppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP1QPPP/R4RK1 w - - 0 10", "expected": "c3d5"},

    # 3. Closed Pawn Structures
    {"id": "CLOSED_FRENCH", "archetype": "Closed French Chain", "fen": "rnbqk2r/ppp2ppp/4pn2/3p4/1b1PP3/2N5/PPP2PPP/R1BQKBNR w KQkq - 2 5", "expected": "e4d5"},
    {"id": "CLOSED_KID", "archetype": "Closed King's Indian", "fen": "r1bq1rk1/ppp1npbp/3p1np1/3Pp3/2P1P3/2N2N2/PP2BPPP/R1BQ1RK1 w - - 1 9", "expected": "c1g5"},
    {"id": "CLOSED_BENONI", "archetype": "Closed Benoni Structure", "fen": "r1bqr1k1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 w - - 0 9", "expected": "e3e4"},

    # 4. Open Attacking
    {"id": "OPEN_SICILIAN", "archetype": "Open Sicilian Najdorf", "fen": "r1b1kb1r/pp1n1ppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2QK2R w KQkq - 0 8", "expected": "e1g1"},
    {"id": "OPEN_GAMBIT", "archetype": "King's Gambit Open", "fen": "rnbqkbnr/pppp1ppp/8/4p3/4PP2/8/PPPP2PP/RNBQKBNR b KQkq f3 0 2", "expected": "e5f4"},
    {"id": "OPEN_INITIATIVE", "archetype": "Attacking Initiative", "fen": "r1bq1rk1/pp2bppp/2n5/3p4/3N4/2P1B3/PP2BPPP/R2Q1RK1 w - - 0 12", "expected": "f1e1"},

    # 5. Defensive
    {"id": "DEF_COUNTER", "archetype": "Defensive Counter-blow", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5", "expected": "b1c3"},
    {"id": "DEF_FORTRESS", "archetype": "Defensive Consolidation", "fen": "2r3k1/1p3ppp/pq2p3/3pP3/3P4/bP2BN2/P2Q1PPP/2R3K1 w - - 0 20", "expected": "c1c8"},

    # 6. Endgames & Zugzwang
    {"id": "END_LUCENA", "archetype": "Rook Endgame Bridge", "fen": "1K6/1P1k4/8/8/8/8/2r5/7R w - - 0 1", "expected": "h1d1"},
    {"id": "END_PHILIDOR", "archetype": "Rook Endgame 3rd Rank", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "expected": "b4f4"},
    {"id": "END_PAWN_OPP", "archetype": "KPK Opposition", "fen": "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", "expected": "e3f3"},
    {"id": "ZUGZWANG_FINE", "archetype": "Pawn Zugzwang Triangulation", "fen": "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1", "expected": "a1b1"},
]

CONFIGURATIONS = [
    ("B0", "Frozen X7 Baseline", "X7", "M0", "S0", "C0", "P0"),
    ("B2", "X7 + Countermoves", "X7", "M2", "S0", "C0", "P0"),
    ("B3", "X7 + CapHist & Countermoves", "X7", "M3", "S0", "C0", "P0"),
    ("B6", "X7 + Conservative ProbCut", "X7", "M0", "S0", "C0", "P1"),
    ("B7", "Full Frozen X8", "X8", "M3", "S1", "C1", "P1"),
]

TIME_CONTROLS = [100, 250, 1000, 3000]

def search_movetime(var: str, m: str, s: str, c: str, p_opt: str, fen: str, movetime_ms: int) -> Dict[str, Any]:
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
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    
    t0 = time.perf_counter()
    out, _ = proc.communicate("\n".join(cmds))
    t1 = time.perf_counter()
    
    nodes = 0
    max_depth = 0
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
                    if d > max_depth: max_depth = d
            if "nodes" in toks:
                idx = toks.index("nodes") + 1
                if idx < len(toks): nodes = int(toks[idx])
            if "score" in toks:
                idx = toks.index("score") + 2
                if idx < len(toks): score = int(toks[idx])
        elif line.startswith("bestmove"):
            toks = line.split()
            if len(toks) > 1: bestmove = toks[1]
            
    return {
        "nodes": nodes,
        "depth": max_depth,
        "score": score,
        "bestmove": bestmove,
        "elapsed_sec": t1 - t0
    }

def main():
    print("=== Phase 3: Search Value per Millisecond Benchmark ===")
    print(f"Corpus size: {len(INDEPENDENT_CORPUS)} positions across 6 archetypes.")
    print(f"Time controls: {TIME_CONTROLS} ms\n")
    
    master_results = {}
    
    for tc in TIME_CONTROLS:
        print(f"--- Running Time Budget: {tc} ms ---")
        master_results[f"tc_{tc}ms"] = {}
        
        for cfg_id, cfg_name, var, m_v, s_v, c_v, p_v in CONFIGURATIONS:
            tot_nodes = 0
            tot_depth = 0
            correct_count = 0
            verifiable_total = 0
            details = []
            
            for item in INDEPENDENT_CORPUS:
                res = search_movetime(var, m_v, s_v, c_v, p_v, item["fen"], tc)
                tot_nodes += res["nodes"]
                tot_depth += res["depth"]
                
                is_correct = False
                if item["expected"] is not None:
                    verifiable_total += 1
                    is_correct = (res["bestmove"] == item["expected"])
                    if is_correct: correct_count += 1
                    
                details.append({
                    "id": item["id"],
                    "depth": res["depth"],
                    "nodes": res["nodes"],
                    "score": res["score"],
                    "bestmove": res["bestmove"],
                    "correct": is_correct if item["expected"] is not None else None
                })
                
            avg_depth = round(tot_depth / len(INDEPENDENT_CORPUS), 2)
            nps = int(tot_nodes / (tc * len(INDEPENDENT_CORPUS) / 1000.0))
            accuracy = round(100.0 * correct_count / verifiable_total, 1) if verifiable_total > 0 else 0.0
            
            master_results[f"tc_{tc}ms"][cfg_id] = {
                "name": cfg_name,
                "avg_depth": avg_depth,
                "total_nodes": tot_nodes,
                "effective_nps": nps,
                "tactical_accuracy_pct": accuracy,
                "correct_solutions": f"{correct_count}/{verifiable_total}",
                "positions": details
            }
            
            print(f"  [{tc:4d}ms] {cfg_id:2s} ({cfg_name:30s}): Depth = {avg_depth:4.2f} plies | Accuracy = {accuracy:4.1f}% ({correct_count}/{verifiable_total}) | Nodes = {tot_nodes:,}")

    with open(RAW_DIR / "search_value_per_ms_raw.json", "w", encoding="utf-8") as f:
        json.dump(master_results, f, indent=2)
    print(f"\nMaster telemetry saved to raw/search_value_per_ms_raw.json")

if __name__ == "__main__":
    main()

