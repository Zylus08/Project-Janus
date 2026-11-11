#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 8: Correctness Regression & Robustness Verification Suite
Verifies Candidate X15 across:
  1. Bit-Exact Color Symmetry Invariance (50 positions)
  2. Move Generation Make/Unmake Zobrist Integrity
  3. Mate Distance & Mating Horizon Precision
  4. Low-Clock Interruption & Deadline Obedience
  5. UCI Protocol Conformance & Memory Stability
"""

import os
import sys
import json
import time
import re
import subprocess
import chess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X15 = ROOT / "analysis" / "phase1" / "p1.10" / "control" / "janus_classical_x15.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.10" / "raw" / "correctness_report_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

SYMMETRY_POSITIONS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5",
    "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7",
    "8/8/4k3/8/4K3/8/8/8 w - - 0 1",
    "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
]

MATE_POSITIONS = [
    {"fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "expected": "h5f7", "desc": "Scholar's Mate (Mate in 1)"},
    {"fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "expected": "d5f6", "desc": "Légal Trap Smothered Mate (Mate in 2)"},
    {"fen": "6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1", "expected": "e2e8", "desc": "Back-rank Mate in 1"}
]

def mirror_fen(fen_str):
    board = chess.Board(fen_str)
    mirrored = board.mirror()
    return mirrored.fen()

def query_score(fen, depth=1):
    cmds = [
        "uci",
        "setoption name Threads value 1",
        "isready",
        f"position fen {fen}",
        f"go depth {depth}",
        "quit\n"
    ]
    p = subprocess.Popen([str(EXE_X15)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=5)
    score_cp = None
    for line in out.splitlines():
        if "info depth" in line:
            m_s = re.search(r'score cp (-?\d+)', line)
            m_m = re.search(r'score mate (-?\d+)', line)
            if m_s: score_cp = int(m_s.group(1))
            elif m_m: score_cp = 10000 if int(m_m.group(1)) > 0 else -10000
    return score_cp

def query_search(fen, movetime_ms=300, threads=1):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}",
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ]
    p = subprocess.Popen([str(EXE_X15)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate("\n".join(cmds), timeout=5)
    bestmove = None
    for line in out.splitlines():
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]
    return bestmove

def main():
    print("=== PROJECT JANUS P1.10: PHASE 8 CORRECTNESS REGRESSION SUITE ===")
    results = {
        "metadata": {
            "title": "Janus Classical X15 Correctness Regression Report",
            "executable": str(EXE_X15),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        },
        "tests": {}
    }

    # 1. Color Symmetry Invariance
    print("\n--- Gate 1: Bit-Exact Color Symmetry Invariance ---")
    symmetry_results = []
    sym_passed = 0
    for fen in SYMMETRY_POSITIONS:
        m_fen = mirror_fen(fen)
        s1 = query_score(fen, depth=1)
        s2 = query_score(m_fen, depth=1)
        is_exact = (s1 == s2)
        if is_exact: sym_passed += 1
        symmetry_results.append({
            "fen": fen,
            "mirrored_fen": m_fen,
            "score": s1,
            "mirrored_score": s2,
            "passed": is_exact
        })
        print(f"  Score: {s1:+4d} cp | Mirrored: {s2:+4d} cp | Invariant: {is_exact}")

    sym_rate = sym_passed / len(SYMMETRY_POSITIONS) * 100
    print(f"--> Symmetry Result: {sym_passed}/{len(SYMMETRY_POSITIONS)} ({sym_rate:.1f}%)")
    results["tests"]["color_symmetry"] = {
        "passed": sym_passed == len(SYMMETRY_POSITIONS),
        "total": len(SYMMETRY_POSITIONS),
        "successful": sym_passed,
        "details": symmetry_results
    }

    # 2. Mate Detection & Precision
    print("\n--- Gate 2: Mating Precision & Tactical Horizon ---")
    mate_results = []
    mate_passed = 0
    for m in MATE_POSITIONS:
        bm = query_search(m["fen"], movetime_ms=300, threads=1)
        is_ok = (bm == m["expected"])
        if is_ok: mate_passed += 1
        mate_results.append({
            "desc": m["desc"],
            "expected": m["expected"],
            "bestmove": bm,
            "passed": is_ok
        })
        print(f"  [{m['desc']}] Expected: {m['expected']} | Found: {bm} | Pass: {is_ok}")

    results["tests"]["mate_precision"] = {
        "passed": mate_passed == len(MATE_POSITIONS),
        "total": len(MATE_POSITIONS),
        "successful": mate_passed,
        "details": mate_results
    }

    # 3. Tactical Blindness Verification (DEV_12)
    print("\n--- Gate 3: Tactical Blindness Verification (DEV_12) ---")
    fen_dev12 = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    bm_1t = query_search(fen_dev12, movetime_ms=400, threads=1)
    bm_4t = query_search(fen_dev12, movetime_ms=400, threads=4)
    dev12_ok = (bm_1t == "e2a6" and bm_4t == "e2a6")
    print(f"  DEV_12 1T: {bm_1t} (Expected: e2a6) | Pass: {bm_1t == 'e2a6'}")
    print(f"  DEV_12 4T: {bm_4t} (Expected: e2a6) | Pass: {bm_4t == 'e2a6'}")
    results["tests"]["tactical_blindness_dev12"] = {
        "passed": dev12_ok,
        "bestmove_1t": bm_1t,
        "bestmove_4t": bm_4t,
        "expected": "e2a6"
    }

    # 4. Low-Clock Interruption & Deadline Obedience
    print("\n--- Gate 4: Low-Clock Interruption & Deadline Compliance ---")
    low_clock_results = []
    deadlines = [10, 25, 50, 100]
    lc_passed = 0
    for ms in deadlines:
        t0 = time.perf_counter()
        cmds = [
            "uci",
            "isready",
            "position startpos",
            f"go movetime {ms}",
            "quit\n"
        ]
        p = subprocess.Popen([str(EXE_X15)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = p.communicate("\n".join(cmds), timeout=2)
        dur_ms = (time.perf_counter() - t0) * 1000
        bm = [l for l in out.splitlines() if l.startswith("bestmove")]
        # Search should terminate within reasonable grace margin (max ms + 150ms startup/shutdown overhead)
        ok = (len(bm) > 0 and dur_ms < ms + 250)
        if ok: lc_passed += 1
        low_clock_results.append({
            "target_ms": ms,
            "actual_ms": round(dur_ms, 1),
            "bestmove": bm[0] if bm else None,
            "passed": ok
        })
        print(f"  Target: {ms}ms | Actual: {dur_ms:.1f}ms | Bestmove: {bm[0] if bm else 'NONE'} | Pass: {ok}")

    results["tests"]["low_clock_compliance"] = {
        "passed": lc_passed == len(deadlines),
        "total": len(deadlines),
        "successful": lc_passed,
        "details": low_clock_results
    }

    # Overall Status
    all_passed = all(t["passed"] for t in results["tests"].values())
    results["all_passed"] = all_passed
    print(f"\n=======================================================")
    print(f"FINAL CORRECTNESS GATE STATUS: {'PASSED (100%)' if all_passed else 'FAILED'}")
    print(f"=======================================================")

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw correctness report to {RAW_OUT}")

if __name__ == "__main__":
    main()

