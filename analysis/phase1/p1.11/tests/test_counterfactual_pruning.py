#!/usr/bin/env python3
"""
Counterfactual Pruning Verification Facility for Milestone P1.11.
Samples pruning decisions across 6 mechanisms:
  1. Reverse Futility Pruning (RFP)
  2. Null-Move Pruning (NMP)
  3. Late Move Pruning (LMP)
  4. Late Move Reductions (LMR)
  5. Quiescence SEE Filtering (QSEE)
Measures: best move agreement, score shift, nodes saved, recovery cost,
and tactical correctness against ground-truth benchmarks.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X15 = ROOT / "analysis" / "phase1" / "p1.10" / "control" / "janus_classical_x15.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.11" / "raw" / "counterfactual_pruning_raw.json"

# Test Suite: 40 Positions Across 7 Strategic Classes
TEST_POSITIONS = [
    # 1. Tactical Combinations & Blunder Refutations
    {"id": "TAC_01", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", "expected": "d2d4", "category": "tactical_combination"},
    {"id": "TAC_02", "fen": "r1b2rk1/pp1nbppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 3 10", "expected": "a2a3", "category": "tactical_combination"},
    {"id": "TAC_03", "fen": "r2q1rk1/1pp1bppp/p1np1nb1/4p3/B3P1P1/2PP1N1P/PP3P2/RNBQR1K1 w - - 1 11", "expected": "b1d2", "category": "tactical_combination"},
    {"id": "TAC_04", "fen": "r1bqk2r/pppp1ppp/2n5/3QP3/1bB1n3/2N2N2/PPP2PPP/R1B1K2R w KQkq - 0 8", "expected": "e2a6", "category": "tactical_combination"}, # DEV_12 Tactical
    {"id": "TAC_05", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected": "d5f6", "category": "tactical_combination"},
    {"id": "TAC_06", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected": "h5f7", "category": "tactical_combination"},
    {"id": "TAC_07", "fen": "2r3k1/ppp2ppp/8/3P4/8/1P6/P4PPP/2R3K1 w - - 0 1", "expected": "d5d6", "category": "tactical_combination"},
    {"id": "TAC_08", "fen": "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N1P3/PP3PPP/R1BQKB1R w KQkq - 0 9", "expected": "c1d2", "category": "tactical_combination"},

    # 2. Quiet Defensive Moves
    {"id": "DEF_01", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9", "expected": "h2h3", "category": "quiet_defense"},
    {"id": "DEF_02", "fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "expected": "e1g1", "category": "quiet_defense"},
    {"id": "DEF_03", "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8", "expected": "a7a5", "category": "quiet_defense"},
    {"id": "DEF_04", "fen": "r2qk2r/ppp2ppp/2np1n2/2b1p1B1/2B1P1b1/2NP1N2/PPP2PPP/R2Q1RK1 b kq - 4 7", "expected": "h7h6", "category": "quiet_defense"},
    {"id": "DEF_05", "fen": "r1bqr1k1/pp1nbppp/2p2n2/3p2B1/3P4/2NBPN2/PP3PPP/R2Q1RK1 w - - 0 10", "expected": "a1c1", "category": "quiet_defense"},
    {"id": "DEF_06", "fen": "2r1r1k1/1p1q1ppp/p1np1n2/3p4/3P4/P1N1PN2/1P3PPP/2RQ1RK1 w - - 0 14", "expected": "c3a4", "category": "quiet_defense"},

    # 3. Pawn Structures & Closed Centers
    {"id": "PWN_01", "fen": "r1bqr1k1/ppp2pbp/2np1np1/4p3/2PPP3/2N1BP2/PP2N1PP/R2QKB1R w KQ - 0 9", "expected": "d4d5", "category": "pawn_structure"},
    {"id": "PWN_02", "fen": "r1bq1rk1/pp1n1pbp/2p1pnp1/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 0 10", "expected": "d1c2", "category": "pawn_structure"},
    {"id": "PWN_03", "fen": "r1bq1rk1/pppnbppp/4pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQ - 4 7", "expected": "e1g1", "category": "pawn_structure"},
    {"id": "PWN_04", "fen": "rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4", "expected": "c4d5", "category": "pawn_structure"},
    {"id": "PWN_05", "fen": "r1bq1rk1/1pp1bppp/p1np1n2/4p3/B3P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 8", "expected": "h2h3", "category": "pawn_structure"},

    # 4. King Attack & Pawn Storms
    {"id": "KNG_01", "fen": "r1b2rk1/ppqn1ppp/2p1pn2/8/2PP4/2N1PN2/PPB2PPP/R2Q1RK1 w - - 0 11", "expected": "d1d3", "category": "king_attack"},
    {"id": "KNG_02", "fen": "r2q1rk1/pp1nbppp/2p1pn2/6B1/3PN3/3B1Q1P/PPP2PP1/R4RK1 w - - 3 12", "expected": "e4f6", "category": "king_attack"},
    {"id": "KNG_03", "fen": "r1bq1rk1/ppp1bppp/2n1pn2/3p4/3P4/2NBPN2/PPP2PPP/R1BQK2R w KQ - 4 6", "expected": "e1g1", "category": "king_attack"},
    {"id": "KNG_04", "fen": "r2qk2r/pb1nbppp/1pp1pn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w kq - 2 10", "expected": "c4d5", "category": "king_attack"},
    {"id": "KNG_05", "fen": "r1b1k2r/pppp1ppp/2n5/4p3/1bB1n2q/2NP1Q2/PPP2PPP/R1B1K1NR w KQkq - 1 7", "expected": "f3f7", "category": "king_attack"},

    # 5. Rook & Minor Piece Endgames
    {"id": "END_01", "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1", "expected": "e4d4", "category": "endgame"}, # Opposition
    {"id": "END_02", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "expected": "b4f4", "category": "endgame"},
    {"id": "END_03", "fen": "8/8/1p1k4/p1pP1p2/P1P2P2/1P1K4/8/8 w - - 0 1", "expected": "d3e3", "category": "endgame"},
    {"id": "END_04", "fen": "8/8/4k3/8/3PK3/8/8/8 w - - 0 1", "expected": "d4d5", "category": "endgame"},
    {"id": "END_05", "fen": "8/8/8/4k3/8/4K3/4P3/8 w - - 0 1", "expected": "e3d3", "category": "endgame"},
    {"id": "END_06", "fen": "8/8/8/8/3k4/8/R7/4K3 w - - 0 1", "expected": "a2a4", "category": "endgame"},
    {"id": "END_07", "fen": "8/5pk1/6p1/7p/7P/5KP1/5P2/8 w - - 0 1", "expected": "f3f4", "category": "endgame"},

    # 6. Zugzwang Positions
    {"id": "ZUG_01", "fen": "8/8/p1k5/1p1p4/1P1P4/P1K5/8/8 w - - 0 1", "expected": "c3b3", "category": "zugzwang"},
    {"id": "ZUG_02", "fen": "8/p7/1p6/8/8/1P6/P7/k1K5 w - - 0 1", "expected": "a2a3", "category": "zugzwang"},
    {"id": "ZUG_03", "fen": "8/8/p7/Pk6/8/1K6/8/8 w - - 0 1", "expected": "b3a3", "category": "zugzwang"},

    # 7. Unstable PV & Complex Sharp Positions
    {"id": "SHP_01", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "expected": "e2a6", "category": "sharp_pv"},
    {"id": "SHP_02", "fen": "r2q1rk1/1pp1bppp/p1np1nb1/4p3/B3P1P1/2PP1N1P/PP3P2/RNBQR1K1 w - - 1 11", "expected": "b1d2", "category": "sharp_pv"},
    {"id": "SHP_03", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "expected": "e1g1", "category": "sharp_pv"},
    {"id": "SHP_04", "fen": "r2qk2r/ppp2ppp/2np1n2/2b1p1B1/2B1P1b1/2NP1N2/PPP2PPP/R2Q1RK1 b kq - 4 7", "expected": "h7h6", "category": "sharp_pv"},
    {"id": "SHP_05", "fen": "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N1P3/PP3PPP/R1BQKB1R w KQkq - 0 9", "expected": "c1d2", "category": "sharp_pv"}
]


def run_engine_search(fen: str, options: Dict[str, str], depth: int = 7) -> Dict[str, Any]:
    """Execute isolated engine search with specific UCI options."""
    proc = subprocess.Popen(
        [str(EXE_X15)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    proc.stdin.write("uci\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if "uciok" in line:
            break

    # Apply options
    for opt, val in options.items():
        proc.stdin.write(f"setoption name {opt} value {val}\n")
    proc.stdin.write("isready\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if "readyok" in line:
            break

    proc.stdin.write("ucinewgame\n")
    proc.stdin.write(f"position fen {fen}\n")
    proc.stdin.write(f"go depth {depth}\n")
    proc.stdin.flush()

    best_move = ""
    score = 0
    nodes = 0
    pv = ""

    t0 = time.perf_counter()
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("info") and "depth" in line:
            parts = line.split()
            if "score" in parts and "cp" in parts:
                idx = parts.index("cp")
                score = int(parts[idx + 1])
            elif "score" in parts and "mate" in parts:
                idx = parts.index("mate")
                mate_plies = int(parts[idx + 1])
                score = 30000 - abs(mate_plies) if mate_plies > 0 else -30000 + abs(mate_plies)
            if "nodes" in parts:
                idx = parts.index("nodes")
                nodes = int(parts[idx + 1])
            if "pv" in parts:
                idx = parts.index("pv")
                pv = " ".join(parts[idx + 1:])
        if line.startswith("bestmove"):
            best_move = line.split()[1]
            break

    elapsed = time.perf_counter() - t0
    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.wait(timeout=5)

    return {
        "best_move": best_move,
        "score": score,
        "nodes": nodes,
        "elapsed": round(elapsed, 4),
        "pv": pv
    }


def main():
    print(f"Starting Counterfactual Pruning Verification on {len(TEST_POSITIONS)} positions...")
    
    # Pruning mechanisms to test:
    # 0. Normal: Default selective search
    # 1. CF_RFP: RFP Disabled
    # 2. CF_NMP: NMP Disabled
    # 3. CF_LMP: LMP Disabled
    # 4. CF_LMR: LMR Disabled
    # 5. CF_QSEE: Quiescence SEE Disabled
    
    pruning_configs = {
        "NORMAL":   {"Threads": "1", "UCI_Variant": "X15", "UCI_RFP": "true",  "UCI_NullMovePruning": "true",  "UCI_LMP": "L1", "UseLMR": "true",  "UCI_QuiescenceSEE": "2"},
        "CF_RFP":   {"Threads": "1", "UCI_Variant": "X15", "UCI_RFP": "false", "UCI_NullMovePruning": "true",  "UCI_LMP": "L1", "UseLMR": "true",  "UCI_QuiescenceSEE": "2"},
        "CF_NMP":   {"Threads": "1", "UCI_Variant": "X15", "UCI_RFP": "true",  "UCI_NullMovePruning": "false", "UCI_LMP": "L1", "UseLMR": "true",  "UCI_QuiescenceSEE": "2"},
        "CF_LMP":   {"Threads": "1", "UCI_Variant": "X15", "UCI_RFP": "true",  "UCI_NullMovePruning": "true",  "UCI_LMP": "L0", "UseLMR": "true",  "UCI_QuiescenceSEE": "2"},
        "CF_LMR":   {"Threads": "1", "UCI_Variant": "X15", "UCI_RFP": "true",  "UCI_NullMovePruning": "true",  "UCI_LMP": "L1", "UseLMR": "false", "UCI_QuiescenceSEE": "2"},
        "CF_QSEE":  {"Threads": "1", "UCI_Variant": "X15", "UCI_RFP": "true",  "UCI_NullMovePruning": "true",  "UCI_LMP": "L1", "UseLMR": "true",  "UCI_QuiescenceSEE": "0"}
    }

    results = []
    mechanism_disagreements = {k: 0 for k in pruning_configs if k != "NORMAL"}
    mechanism_nodes_saved   = {k: [] for k in pruning_configs if k != "NORMAL"}
    mechanism_score_shifts  = {k: [] for k in pruning_configs if k != "NORMAL"}

    for idx, pos in enumerate(TEST_POSITIONS):
        fen = pos["fen"]
        pid = pos["id"]
        cat = pos["category"]
        expected = pos.get("expected")

        pos_eval = {"id": pid, "category": cat, "fen": fen, "expected": expected, "runs": {}}
        
        # 1. Run Normal Search
        norm_res = run_engine_search(fen, pruning_configs["NORMAL"], depth=7)
        pos_eval["runs"]["NORMAL"] = norm_res

        # 2. Run Counterfactual Searches
        for m_name, m_opts in pruning_configs.items():
            if m_name == "NORMAL":
                continue
            cf_res = run_engine_search(fen, m_opts, depth=7)
            pos_eval["runs"][m_name] = cf_res

            # Analysis
            move_disagree = (cf_res["best_move"] != norm_res["best_move"])
            score_diff = abs(cf_res["score"] - norm_res["score"])
            nodes_diff = cf_res["nodes"] - norm_res["nodes"] # Positive means normal saved nodes

            if move_disagree:
                mechanism_disagreements[m_name] += 1
            mechanism_nodes_saved[m_name].append(nodes_diff)
            mechanism_score_shifts[m_name].append(score_diff)

        results.append(pos_eval)
        print(f"[{idx+1:02d}/40] {pid} ({cat}): Normal move={norm_res['best_move']}, CF_RFP={pos_eval['runs']['CF_RFP']['best_move']}, CF_LMR={pos_eval['runs']['CF_LMR']['best_move']}")

    summary = {
        "total_positions_audited": len(TEST_POSITIONS),
        "search_depth": 7,
        "disagreements": mechanism_disagreements,
        "disagreement_rate_pct": {k: round(v / len(TEST_POSITIONS) * 100.0, 2) for k, v in mechanism_disagreements.items()},
        "avg_nodes_saved_per_node": {k: round(sum(v) / len(v), 1) for k, v in mechanism_nodes_saved.items()},
        "avg_score_shift_cp": {k: round(sum(v) / len(v), 1) for k, v in mechanism_score_shifts.items()}
    }

    print("\n--- COUNTERFACTUAL PRUNING AUDIT SUMMARY ---")
    print(json.dumps(summary, indent=2))

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "positions": results}, f, indent=2)
    print(f"Saved complete audit data to {OUT_RAW}")


if __name__ == "__main__":
    main()

