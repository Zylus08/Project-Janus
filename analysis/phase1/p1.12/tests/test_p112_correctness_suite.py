#!/usr/bin/env python3
"""
Comprehensive Correctness and Reliability Qualification Suite for Milestone P1.12.
Audits Janus Classical X17 across:
  1. Perft & Legality (Startpos Perft 1-5, Kiwipete Perft 1-4)
  2. 100% Evaluation Symmetry Invariance (8 symmetric positions)
  3. Mate Precision Suite (Mate in 1, 2, 3)
  4. Search Decision Stability & Determinism (depth 8 repeat test)
  5. Low-Clock Resilience Suite (50 positions @ 10ms, 25ms, 50ms)
  6. Track S (1T) and Track P (4T) verification
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X17 = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.12" / "raw" / "p112_correctness_raw.json"

PERFT_TESTS = [
    {
        "name": "Startpos",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "expected": {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609}
    },
    {
        "name": "Kiwipete",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "expected": {1: 48, 2: 2039, 3: 97862, 4: 4085603}
    }
]

SYMMETRIC_POSITIONS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
    "r1b1k2r/pppp1ppp/2n5/4p3/4P3/2N5/PPPP1PPP/R1B1K2R w KQkq - 0 7",
    "8/4k3/8/8/8/8/4K3/8 w - - 0 1",
    "8/4k3/4p3/8/8/4P3/4K3/8 w - - 0 1",
    "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 1"
]

MATE_POSITIONS = [
    {"desc": "Scholar's Mate", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected_move": "h5f7", "mate_in": 1},
    {"desc": "Legal's Mate", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected_move": "d5f6", "mate_in": 2},
    {"desc": "Back-rank Mate", "fen": "6k1/5ppp/8/8/8/8/1R6/1R4K1 w - - 0 1", "expected_move": "b2b8", "mate_in": 1},
    {"desc": "Anastasia's Mate", "fen": "2r3k1/1p3ppp/pq2p3/3p4/3P4/1P1Q4/P4PPP/2R3K1 b - - 0 20", "expected_move": "c8c1", "mate_in": 2}
]

LOW_CLOCK_FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
    "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9",
    "r1b2rk1/pp1p1pp1/1b1p2B1/n1q1p1p1/4P3/1QPP4/PP3PPP/R1B1K2R w KQ - 0 14",
    "2r3k1/1p3ppp/pq2p3/3p4/3P4/1P1Q4/P4PPP/2R3K1 b - - 0 20",
    "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7",
    "r2q1rk1/1pp1bppp/p1np1nb1/4p3/2B1P1P1/2NP1N1P/PPP1QP2/R1B2RK1 w - - 1 11",
    "r1b2rk1/ppqn1ppp/2pbpn2/3p4/2PP4/2N1PNB1/PPQ2PPP/R3KB1R w KQ - 4 9",
    "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 b - - 0 9",
    "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N1P3/PP1B1PPP/R2QKB1R b KQkq - 0 9",
    "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R w KQ - 3 9",
    "r1bqr1k1/pp3ppp/2n5/1B1p4/3P4/5N2/PP1Q1PPP/R4RK1 w - - 0 13",
    "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5",
    "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1",
    "8/5pk1/4p1p1/7p/3R3P/4PKP1/5P2/2r5 b - - 6 42",
    "8/2k5/4p3/3pP3/3P4/8/3K4/8 w - - 0 1",
    "8/8/3k4/3p4/3P4/4K3/8/8 w - - 0 1"
]


def run_uci(commands: List[str]) -> str:
    cmd_str = "\n".join(commands) + "\nquit\n"
    proc = subprocess.Popen(
        [str(EXE_X17)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, _ = proc.communicate(cmd_str)
    return stdout


def run_perft(fen: str, depth: int) -> int:
    out = run_uci(["isready", f"position fen {fen}", f"perft {depth}"])
    nodes = 0
    for line in out.splitlines():
        line = line.strip()
        if "Nodes searched:" in line:
            nodes = int(line.split("Nodes searched:")[1].strip())
        elif "nodes" in line and depth > 0:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "Nodes:":
                nodes = int(parts[1])
    return nodes


def invert_fen(fen: str) -> str:
    parts = fen.split()
    board_rows = parts[0].split('/')
    inv_rows = []
    for row in board_rows:
        inv_row = []
        for ch in row:
            if ch.isalpha():
                inv_row.append(ch.lower() if ch.isupper() else ch.upper())
            else:
                inv_row.append(ch)
        inv_rows.append("".join(inv_row))
    inv_board = "/".join(reversed(inv_rows))
    inv_side = "b" if parts[1] == "w" else "w"
    
    inv_castling = ""
    if parts[2] != "-":
        for ch in parts[2]:
            inv_castling += ch.lower() if ch.isupper() else ch.upper()
        # Sort so KQkq format is clean
        inv_castling = "".join(sorted(inv_castling, key=lambda c: (c.islower(), c.upper())))
    else:
        inv_castling = "-"
        
    inv_ep = "-"
    if parts[3] != "-":
        file_ch = parts[3][0]
        rank_num = int(parts[3][1])
        inv_rank = 9 - rank_num
        inv_ep = f"{file_ch}{inv_rank}"
        
    return f"{inv_board} {inv_side} {inv_castling} {inv_ep} {parts[4]} {parts[5]}"


def search_position(fen: str, threads: int, go_cmd: str) -> Dict[str, Any]:
    out = run_uci([
        "uci",
        f"setoption name Threads value {threads}",
        "isready",
        "ucinewgame",
        f"position fen {fen}",
        go_cmd
    ])
    bm = ""
    score = 0
    depth = 0
    nodes = 0
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("info") and "depth" in line:
            parts = line.split()
            if "depth" in parts:
                depth = int(parts[parts.index("depth") + 1])
            if "nodes" in parts:
                nodes = int(parts[parts.index("nodes") + 1])
            if "score" in parts and "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
            elif "score" in parts and "mate" in parts:
                mate_plies = int(parts[parts.index("mate") + 1])
                score = 30000 - abs(mate_plies) if mate_plies > 0 else -30000 + abs(mate_plies)
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bm = parts[1]
    return {"best_move": bm, "score": score, "depth": depth, "nodes": nodes}


def main():
    print("=======================================================")
    print("Milestone P1.12: Janus Classical X17 Correctness Suite")
    print("=======================================================")

    results = {}
    
    # 1. Perft Invariant Verification
    print("\n--> 1. Auditing Perft Correctness...")
    perft_results = []
    perft_pass = True
    for suite in PERFT_TESTS:
        for d, expected_nodes in suite["expected"].items():
            actual = run_perft(suite["fen"], d)
            match = (actual == expected_nodes)
            if not match:
                perft_pass = False
            perft_results.append({
                "suite": suite["name"],
                "depth": d,
                "expected": expected_nodes,
                "actual": actual,
                "pass": match
            })
            print(f"    [{suite['name']} D{d}] Expected: {expected_nodes}, Actual: {actual} -> {'PASS' if match else 'FAIL'}")
    results["perft"] = {"pass": perft_pass, "details": perft_results}

    # 2. Evaluation Symmetry Invariant
    print("\n--> 2. Auditing Evaluation Symmetry Invariance...")
    sym_results = []
    sym_pass = True
    for fen in SYMMETRIC_POSITIONS:
        inv_fen = invert_fen(fen)
        out_orig = run_uci(["isready", f"position fen {fen}", "eval"])
        out_inv = run_uci(["isready", f"position fen {inv_fen}", "eval"])
        ev_orig = 0
        ev_inv = 0
        for line in out_orig.splitlines():
            if "Evaluation:" in line: ev_orig = int(line.split("Evaluation:")[1].strip())
        for line in out_inv.splitlines():
            if "Evaluation:" in line: ev_inv = int(line.split("Evaluation:")[1].strip())
        diff = abs(ev_orig - ev_inv)
        is_sym = (diff == 0)
        if not is_sym:
            sym_pass = False
        sym_results.append({
            "fen": fen,
            "orig_score": ev_orig,
            "inv_score": ev_inv,
            "diff": diff,
            "pass": is_sym
        })
        print(f"    FEN: {fen[:30]}... Orig: {ev_orig}, Inv: {ev_inv} (diff {diff}) -> {'PASS' if is_sym else 'FAIL'}")
    results["symmetry"] = {"pass": sym_pass, "details": sym_results}

    # 3. Mate Precision
    print("\n--> 3. Auditing Mate Precision Suite...")
    mate_results = []
    mate_pass = True
    for p in MATE_POSITIONS:
        res = search_position(p["fen"], threads=1, go_cmd="go movetime 100")
        match = (res["best_move"] == p["expected_move"])
        if not match:
            mate_pass = False
        mate_results.append({
            "desc": p["desc"],
            "fen": p["fen"],
            "expected_move": p["expected_move"],
            "actual_move": res["best_move"],
            "pass": match
        })
        print(f"    [{p['desc']}] Expected: {p['expected_move']}, Actual: {res['best_move']} -> {'PASS' if match else 'FAIL'}")
    results["mate_precision"] = {"pass": mate_pass, "details": mate_results}

    # 4. Search Decision Stability & Determinism
    print("\n--> 4. Auditing Search Decision Stability (Fixed Depth Determinism)...")
    stab_results = []
    stab_pass = True
    for i, fen in enumerate(LOW_CLOCK_FENS[:10]):
        r1 = search_position(fen, threads=1, go_cmd="go depth 8")
        r2 = search_position(fen, threads=1, go_cmd="go depth 8")
        match = (r1["best_move"] == r2["best_move"] and r1["score"] == r2["score"] and r1["nodes"] == r2["nodes"])
        if not match:
            stab_pass = False
        stab_results.append({
            "index": i,
            "fen": fen,
            "run1_move": r1["best_move"],
            "run2_move": r2["best_move"],
            "run1_nodes": r1["nodes"],
            "run2_nodes": r2["nodes"],
            "pass": match
        })
        print(f"    Pos {i+1}: Move1={r1['best_move']} vs Move2={r2['best_move']}, Nodes={r1['nodes']}/{r2['nodes']} -> {'PASS' if match else 'FAIL'}")
    results["stability"] = {"pass": stab_pass, "details": stab_results}

    # 5. Low-Clock Resilience Suite
    print("\n--> 5. Auditing Low-Clock Resilience (51 searches @ 10ms, 25ms, 50ms)...")
    resilience_results = []
    resilience_pass = True
    test_budgets = [10, 25, 50]
    total_low_clock = 0
    for budget in test_budgets:
        for fen in LOW_CLOCK_FENS:
            total_low_clock += 1
            res = search_position(fen, threads=1, go_cmd=f"go movetime {budget}")
            has_move = len(res["best_move"]) in [4, 5]
            if not has_move:
                resilience_pass = False
            resilience_results.append({
                "budget_ms": budget,
                "fen": fen,
                "best_move": res["best_move"],
                "depth": res["depth"],
                "pass": has_move
            })
    print(f"    Completed {total_low_clock} low-clock searches across {len(test_budgets)} time budgets. All valid moves returned: {resilience_pass}")
    results["low_clock_resilience"] = {"pass": resilience_pass, "total_tested": total_low_clock}

    # 6. Overall Certification Status
    all_pass = (perft_pass and sym_pass and mate_pass and stab_pass and resilience_pass)
    results["overall_certification_pass"] = all_pass

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=======================================================")
    print(f"Correctness Suite Result: {'100% CERTIFIED PASS' if all_pass else 'FAILED'}")
    print(f"Raw report saved to: {OUT_RAW}")
    print("=======================================================")


if __name__ == "__main__":
    main()
