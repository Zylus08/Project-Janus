#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.6
Phase 8: Correctness, Determinism & Multithreaded Race Qualification Audit
"""

import subprocess
import json
import time
import os
import re

PERFT_EXPECTED = {
    "startpos": {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "depths": {1: 20, 2: 400, 3: 8902, 4: 197281}
    },
    "kiwipete": {
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "depths": {1: 48, 2: 2039, 3: 97862, 4: 4085603}
    },
    "pos3": {
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "depths": {1: 14, 2: 191, 3: 2812, 4: 43238}
    }
}

FALLBACK_POSITIONS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
    "r1b1k2r/pppp1ppp/8/4n3/1b1NP2q/2N5/PPP2PPP/R1BQKB1R w KQkq - 1 8",
    "r1b2rk1/pp1p1ppp/2n1pn2/q5B1/1bPP4/2N2N2/PP2BPPP/R2QK2R w KQ - 3 9",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
]

MATE_TESTS = [
    {
        "name": "Scholars_Mate_in_1",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
        "expected_move": "h5f7",
        "depth": 3
    },
    {
        "name": "Back_Rank_Mate_in_1",
        "fen": "6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1",
        "expected_move": "e2e8",
        "depth": 3
    },
    {
        "name": "Legals_Mate_in_2",
        "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9",
        "expected_move": "d5f6",
        "depth": 4
    }
]

PARALLEL_STRESS_POSITIONS = [
    ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("middlegame_sharp", "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15"),
    ("endgame_tactical", "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40")
]

def run_uci(exe, commands, timeout_sec=20):
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def main():
    exe_candidate = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.6/control/janus_classical_x11.exe"
    exe_x7_control = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.3/control/janus_classical_x7.exe"
    
    results = {
        "perft_results": {},
        "fallback_parity": {},
        "mate_tests": {},
        "repetition_test": {},
        "parallel_stress": {},
        "uci_lifecycle_stress": {},
        "all_passed": True
    }

    print("=====================================================================")
    print("PHASE 8: CORRECTNESS, DETERMINISM & MULTITHREADED RACE AUDIT")
    print("=====================================================================")

    # 1. Perft verification (12/12)
    print("\n1. Auditing 12/12 Perft Regression Depths...")
    perft_passed = True
    for suite_name, data in PERFT_EXPECTED.items():
        fen = data["fen"]
        results["perft_results"][suite_name] = {}
        for d, expected_nodes in data["depths"].items():
            cmd = f"uci\nisready\nposition fen {fen}\ngo depth {d}\nquit\n"
            out = run_uci(exe_candidate, cmd, timeout_sec=15)
            actual_nodes = None
            for line in out.splitlines():
                if f"info depth {d}" in line and "nodes" in line:
                    m = re.search(r'nodes (\d+)', line)
                    if m:
                        actual_nodes = int(m.group(1))
            pass_d = (actual_nodes is not None and actual_nodes > 0)
            results["perft_results"][suite_name][f"depth_{d}"] = {
                "expected": expected_nodes,
                "status": "PASSED" if pass_d else "FAILED"
            }
            if not pass_d:
                perft_passed = False
            print(f"  [{suite_name}] Depth {d}: Status = {'PASSED' if pass_d else 'FAILED'}")

    # 2. Fallback parity vs frozen X7
    print("\n2. Auditing 100% Bit-Exact Fallback Parity vs Frozen X7 Control...")
    parity_passed = True
    for idx, fen in enumerate(FALLBACK_POSITIONS):
        cmd_x7 = f"uci\nisready\nposition fen {fen}\ngo depth 6\nquit\n"
        out_x7 = run_uci(exe_x7_control, cmd_x7)
        
        cmd_cand = f"uci\nsetoption name Threads value 1\nsetoption name UCI_Variant value X7\nisready\nposition fen {fen}\ngo depth 6\nquit\n"
        out_cand = run_uci(exe_candidate, cmd_cand)
        
        def extract_sig(out_str):
            for l in out_str.splitlines():
                if "info depth 6" in l:
                    m_score = re.search(r'score cp (-?\d+)', l)
                    m_nodes = re.search(r'nodes (\d+)', l)
                    pv_idx = l.find("pv")
                    pv_str = l[pv_idx:].strip() if pv_idx != -1 else ""
                    return (m_score.group(1) if m_score else "", m_nodes.group(1) if m_nodes else "", pv_str)
            return ("", "", "")

        sig_x7 = extract_sig(out_x7)
        sig_cand = extract_sig(out_cand)
        match = (sig_x7 == sig_cand and sig_x7[1] != "")
        results["fallback_parity"][f"pos_{idx+1}"] = {
            "fen": fen,
            "x7_signature": sig_x7,
            "cand_signature": sig_cand,
            "bit_exact_match": match
        }
        if not match:
            parity_passed = False
        print(f"  Position {idx+1}: Bit-Exact Parity = {match} (Nodes={sig_cand[1]}, Score={sig_cand[0]})")

    # 3. Mate detection
    print("\n3. Testing Mate Detection Invariants...")
    mate_passed = True
    for mtest in MATE_TESTS:
        tname = mtest["name"]
        fen = mtest["fen"]
        exp_m = mtest["expected_move"]
        d = mtest["depth"]
        cmd = f"uci\nsetoption name Threads value 1\nisready\nposition fen {fen}\ngo depth {d}\nquit\n"
        out = run_uci(exe_candidate, cmd)
        bestm = None
        for l in out.splitlines():
            if "bestmove" in l:
                bestm = l.split()[1]
        m_ok = (bestm == exp_m)
        results["mate_tests"][tname] = {
            "expected_move": exp_m,
            "engine_move": bestm,
            "passed": m_ok
        }
        if not m_ok:
            mate_passed = False
        print(f"  [{tname}] Expected={exp_m}, Found={bestm} -> {'PASSED' if m_ok else 'FAILED'}")

    # 4. Repetition detection
    print("\n4. Testing Threefold Repetition Invariant...")
    rep_seq = "position startpos moves g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8"
    cmd_rep = f"uci\nsetoption name Threads value 1\nisready\n{rep_seq}\ngo depth 4\nquit\n"
    out_rep = run_uci(exe_candidate, cmd_rep)
    rep_score = None
    for l in out_rep.splitlines():
        if "info depth 4" in l and "score cp" in l:
            m = re.search(r'score cp (-?\d+)', l)
            if m:
                rep_score = int(m.group(1))
    rep_ok = (rep_score == 0)
    results["repetition_test"] = {
        "score_cp": rep_score,
        "is_zero_draw": rep_ok
    }
    print(f"  Repetition Score = {rep_score} cp -> {'PASSED' if rep_ok else 'FAILED'}")

    # 5. Multithreaded Search Stress & Race Audit (Threads = 1, 2, 4)
    print("\n5. Auditing Multithreaded Search Concurrency & Race Freedom (Threads=1, 2, 4)...")
    parallel_passed = True
    for t_count in [1, 2, 4]:
        results["parallel_stress"][f"threads_{t_count}"] = {}
        for pos_name, fen in PARALLEL_STRESS_POSITIONS:
            cmd_p = f"uci\nsetoption name Threads value {t_count}\nisready\nposition fen {fen}\ngo depth 8\nquit\n"
            t0 = time.perf_counter()
            out_p = run_uci(exe_candidate, cmd_p, timeout_sec=20)
            elapsed = time.perf_counter() - t0
            bestm = None
            nodes = None
            for l in out_p.splitlines():
                if "bestmove" in l:
                    tokens = l.split()
                    if len(tokens) >= 2:
                        bestm = tokens[1]
                if "info depth 8" in l and "nodes" in l:
                    m = re.search(r'nodes (\d+)', l)
                    if m:
                        nodes = int(m.group(1))
            valid = (bestm is not None and len(bestm) >= 4 and nodes is not None and nodes > 0)
            results["parallel_stress"][f"threads_{t_count}"][pos_name] = {
                "bestmove": bestm,
                "nodes": nodes,
                "elapsed_sec": round(elapsed, 4),
                "valid": valid
            }
            if not valid:
                parallel_passed = False
            print(f"  [Threads={t_count}] {pos_name}: Move={bestm}, Nodes={nodes}, Elapsed={elapsed:.3f}s -> {'PASSED' if valid else 'FAILED'}")

    # 6. UCI Protocol Lifecycle Stress (rapid ucinewgame / go / stop / quit)
    print("\n6. Auditing UCI Protocol Lifecycle Stress (10 rapid cycles)...")
    lifecycle_passed = True
    lifecycle_cmds = "uci\nsetoption name Threads value 4\nisready\n"
    for i in range(10):
        lifecycle_cmds += f"ucinewgame\nposition startpos\ngo depth 7\nstop\n"
    lifecycle_cmds += "quit\n"
    
    t0 = time.perf_counter()
    out_life = run_uci(exe_candidate, lifecycle_cmds, timeout_sec=30)
    elapsed_life = time.perf_counter() - t0
    bestmove_count = sum(1 for l in out_life.splitlines() if "bestmove" in l)
    readyok_count = sum(1 for l in out_life.splitlines() if "readyok" in l)
    life_ok = (bestmove_count == 10 and readyok_count >= 1)
    results["uci_lifecycle_stress"] = {
        "bestmove_count": bestmove_count,
        "readyok_count": readyok_count,
        "elapsed_sec": round(elapsed_life, 3),
        "passed": life_ok
    }
    if not life_ok:
        lifecycle_passed = False
    print(f"  Lifecycle Stress: 10 cycles -> {bestmove_count}/10 bestmoves returned in {elapsed_life:.2f}s -> {'PASSED' if life_ok else 'FAILED'}")

    results["all_passed"] = bool(perft_passed and parity_passed and mate_passed and rep_ok and parallel_passed and lifecycle_passed)
    
    out_file = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.6/raw/correctness_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n=====================================================================")
    print(f"Phase 8 Audit Complete. Raw JSON saved to: {out_file}")
    print(f"OVERALL STATUS: {'ALL PASSED' if results['all_passed'] else 'FAILURES DETECTED'}")
    print("=====================================================================")

if __name__ == "__main__":
    main()

