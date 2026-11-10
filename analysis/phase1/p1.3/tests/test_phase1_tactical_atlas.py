#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.3
Phase 1: Tactical Failure Atlas Suite
Evaluates Classical X6 and Classical X7 across a comprehensive diagnostic corpus
of 16 tactical, positional, and LMR/NMP-sensitive test positions.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
X6_EXE = ROOT / "analysis" / "phase1" / "p1.2" / "control" / "janus_classical_x6.exe"
X7_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.3" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 16 Comprehensive Tactical Benchmark Positions
TACTICAL_CORPUS = [
    {
        "id": "TAC_01_OPERA_MATE",
        "category": "Forced Mate / Deflection",
        "fen": "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14",
        "expected_move": "b5d7",
        "solution_desc": "Bxd7+ deflecting knight/queen, leading to Morphy's Opera mate",
        "theme": "deflection_mate"
    },
    {
        "id": "TAC_02_SMOTHERED_MATE",
        "category": "Forced Mate / Knight Sac",
        "fen": "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13",
        "expected_move": "d3h7",
        "solution_desc": "Bxh7+ followed by greek gift / king attack sequence",
        "theme": "king_attack"
    },
    {
        "id": "TAC_03_SAAVEDRA_PROMO",
        "category": "Underpromotion / Stalemate Avoidance",
        "fen": "8/8/1P6/8/8/1r6/p7/k1K5 w - - 0 1",
        "expected_move": "b6b7",
        "solution_desc": "Advance pawn toward promotion c8=R avoiding stalemate",
        "theme": "underpromotion"
    },
    {
        "id": "TAC_04_ZUGZWANG_FINE70",
        "category": "Zugzwang / NMP Hazard",
        "fen": "8/k7/3p4/p2P1p2/P2P1P2/8/8/K7 w - - 0 1",
        "expected_move": "a1b1",
        "solution_desc": "Triangulation/waiting move Kb1; engine must not blunder via false null-move cutoff",
        "theme": "zugzwang"
    },
    {
        "id": "TAC_05_EXCHANGE_SAC",
        "category": "Exchange Sacrifice / Outpost",
        "fen": "r1b2rk1/pp3ppp/2n1p3/3pP3/3P4/2PB1N2/P4PPP/R3K2R w KQ - 0 13",
        "expected_move": "d3h7",
        "solution_desc": "Classic Bxh7+ Greek gift sacrifice",
        "theme": "greek_gift"
    },
    {
        "id": "TAC_06_QUIET_TACTICAL",
        "category": "Quiet Tactical Move",
        "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/4n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 6",
        "expected_move": "f1e1",
        "solution_desc": "Re1 pinning knight to king with decisive initiative",
        "theme": "pin_initiative"
    },
    {
        "id": "TAC_07_LMR_TACTICAL_REFUTATION",
        "category": "LMR Sensitivity / Late Refutation",
        "fen": "r2qkb1r/pp2pppp/2n2n2/3p4/3P2b1/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 3 7",
        "expected_move": "c1e3",
        "solution_desc": "Be3 solidifying d4 center without falling for tactics",
        "theme": "positional_defense"
    },
    {
        "id": "TAC_08_FORK_TRICK",
        "category": "Tactical Fork Trick",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5",
        "expected_move": "c4f7",
        "solution_desc": "Bxf7+ Kxf7 Nxe5+ or d4 fork trick resolution",
        "theme": "fork_trick"
    },
    {
        "id": "TAC_09_DISCOVERED_ATTACK",
        "category": "Discovered Attack",
        "fen": "r1b1k2r/ppppqppp/2n5/8/1bPPn3/2N2N2/PP1B1PPP/R2QKB1R w KQkq - 0 8",
        "expected_move": "c3e4",
        "solution_desc": "Nxe4 resolving pin and eliminating the e4 tactical bind",
        "theme": "discovered_attack"
    },
    {
        "id": "TAC_10_DEFENSIVE_RESOURCE",
        "category": "Defensive Resource / Perpetual",
        "fen": "r4rk1/pp3ppp/2n5/3p4/8/1PB2N2/P1P2PPP/R4RK1 b - - 0 16",
        "expected_move": "d5d4",
        "solution_desc": "d4! disrupting White's bishop battery on long diagonal",
        "theme": "defensive_interposition"
    },
    {
        "id": "TAC_11_ENDGAME_TACTICS_PASSER",
        "category": "Endgame Tactical Conversion",
        "fen": "8/5p2/4pk2/8/5K2/4P3/8/8 w - - 0 1",
        "expected_move": "f4e4",
        "solution_desc": "Ke4 taking opposition in pawn endgame",
        "theme": "opposition"
    },
    {
        "id": "TAC_12_CHECK_EVASION_INTERPOS",
        "category": "Check Evasion / Interposition",
        "fen": "r1bqk2r/ppppbppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "expected_move": "d2d3",
        "solution_desc": "d3 calm development maintaining symmetry",
        "theme": "calm_development"
    },
    {
        "id": "TAC_13_SF_BLUNDER_RECON_1",
        "category": "SF19 Match Loss Diagnostic (Caro-Kann)",
        "fen": "r2qkb1r/pp1n1ppp/2p1pn2/5b2/3P4/2N2NP1/PPP2P1P/R1BQKB1R w KQkq - 1 8",
        "expected_move": "f1g2",
        "solution_desc": "Bg2 completing kingside development safely",
        "theme": "safe_development"
    },
    {
        "id": "TAC_14_SF_BLUNDER_RECON_2",
        "category": "SF19 Match Loss Diagnostic (Najdorf)",
        "fen": "r1bqkb1r/1p3ppp/p1np4/3Np3/4P3/3B4/PPP2PPP/R1BQK2R w KQkq - 0 10",
        "expected_move": "e1g1",
        "solution_desc": "O-O castling before launching central operations",
        "theme": "king_safety"
    },
    {
        "id": "TAC_15_INTERMEDIATE_MOVE_ZWISCHENZUG",
        "category": "Zwischenzug / In-between Move",
        "fen": "r1b2rk1/pp2ppbp/2np1np1/q7/2PNP3/2N1BP2/PP2B1PP/R2QK2R w KQ - 3 10",
        "expected_move": "e1g1",
        "solution_desc": "O-O safely securing king against Sicilian queen counter",
        "theme": "zwischenzug"
    },
    {
        "id": "TAC_16_ROOK_ENDGAME_LUCENA",
        "category": "Endgame Tactical Technique (Lucena)",
        "fen": "1K1k4/1P6/8/8/8/8/r7/2R5 w - - 0 1",
        "expected_move": "c1d1",
        "solution_desc": "Rd1+ cutting off black king to build the bridge",
        "theme": "lucena_bridge"
    }
]

def search_position(exe: Path, fen: str, depth: int, options: Dict[str, str] = None) -> Dict[str, Any]:
    p = subprocess.Popen(
        [str(exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    commands = ["uci", "isready"]
    if options:
        for k, v in options.items():
            commands.append(f"setoption name {k} value {v}")
    commands.append("ucinewgame")
    commands.append("isready")
    commands.append("telemetry_reset")
    commands.append(f"position fen {fen}")
    commands.append(f"go depth {depth}")
    commands.append("telemetry_report")
    commands.append("quit\n")
    
    t0 = time.perf_counter()
    out, _ = p.communicate("\n".join(commands))
    elapsed = time.perf_counter() - t0
    
    bestmove = ""
    score_cp = 0
    nodes = 0
    pv = ""
    telemetry = {}
    
    in_telemetry = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(f"info depth {depth}"):
            toks = line.split()
            if "nodes" in toks:
                nodes = int(toks[toks.index("nodes") + 1])
            if "score" in toks and "cp" in toks:
                score_cp = int(toks[toks.index("cp") + 1])
            if "pv" in toks:
                pv = " ".join(toks[toks.index("pv") + 1:])
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
        "bestmove": bestmove,
        "score_cp": score_cp,
        "nodes": nodes,
        "pv": pv,
        "elapsed_sec": elapsed,
        "telemetry": telemetry
    }

def main():
    print("=== PROJECT JANUS P1.3: PHASE 1 TACTICAL FAILURE ATLAS ===")
    print(f"Auditing {len(TACTICAL_CORPUS)} tactical test positions at depth 7...")
    
    SEARCH_DEPTH = 7
    results = []
    
    x6_solved = 0
    x7_solved = 0
    
    for idx, item in enumerate(TACTICAL_CORPUS):
        pid = item["id"]
        fen = item["fen"]
        exp = item["expected_move"]
        
        # Test X6 Control
        res_x6 = search_position(X6_EXE, fen, SEARCH_DEPTH, {"UCI_Variant": "X6"})
        x6_ok = (res_x6["bestmove"] == exp)
        if x6_ok: x6_solved += 1
        
        # Test X7 Candidate
        res_x7 = search_position(X7_EXE, fen, SEARCH_DEPTH, {"UCI_Variant": "X7"})
        x7_ok = (res_x7["bestmove"] == exp)
        if x7_ok: x7_solved += 1
        
        status_x6 = "SOLVED" if x6_ok else "MISSED"
        status_x7 = "SOLVED" if x7_ok else "MISSED"
        
        print(f"[{idx+1:2d}/16] {pid[:24]:24s} | Exp: {exp:5s} | X6: {res_x6['bestmove']:5s} ({status_x6:6s}, {res_x6['nodes']:,} nodes) | X7: {res_x7['bestmove']:5s} ({status_x7:6s}, {res_x7['nodes']:,} nodes)")
        
        results.append({
            "position": item,
            "x6_result": res_x6,
            "x6_solved": x6_ok,
            "x7_result": res_x7,
            "x7_solved": x7_ok
        })
        
    print(f"\n--- Tactical Atlas Summary ---")
    print(f"Classical X6 Solved: {x6_solved} / {len(TACTICAL_CORPUS)} ({x6_solved/len(TACTICAL_CORPUS)*100:.1f}%)")
    print(f"Classical X7 Solved: {x7_solved} / {len(TACTICAL_CORPUS)} ({x7_solved/len(TACTICAL_CORPUS)*100:.1f}%)")
    
    out_file = RAW_DIR / "tactical_failure_atlas_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "depth": SEARCH_DEPTH,
            "x6_solved": x6_solved,
            "x7_solved": x7_solved,
            "total_positions": len(TACTICAL_CORPUS),
            "results": results
        }, f, indent=2)
    print(f"Saved raw tactical atlas evidence to {out_file}")

if __name__ == "__main__":
    main()

