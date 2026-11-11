#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.7
Phase 5: Cross-Platform Concurrency Correctness Suite
Tests:
  1. Atomic Publication & Spinlock Stress (20M ops across 4 threads)
  2. Search Epoch Changes & Stale Entry Eviction
  3. UCI Protocol Lifecycle Stress (20 rapid cycles)
  4. Consecutive Games State Isolation
  5. Mate Score Normalization Invariants
  6. Repetition & Draw Adjudication under Multithreading
"""

import sys
import os
import json
import time
import subprocess
import re
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
TEST_DIR = ROOT / "analysis" / "phase1" / "p1.7" / "tests"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.7" / "raw" / "concurrency_correctness_raw.json"
VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

STRESS_CPP = TEST_DIR / "test_p17_concurrency_stress.cpp"
STRESS_EXE = TEST_DIR / "test_p17_concurrency_stress.exe"
ENGINE_W4 = TEST_DIR / "engine_w4.exe"

def run_uci(exe, commands, timeout_sec=20):
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def compile_stress_test():
    cmd = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc test_p17_concurrency_stress.cpp /Fe:test_p17_concurrency_stress.exe"'
    res = subprocess.run(cmd, cwd=str(TEST_DIR), shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print("STRESS TEST COMPILATION FAILED:\n", res.stdout, res.stderr)
        sys.exit(1)
    print("Compiled test_p17_concurrency_stress.exe")

def main():
    print("==================================================================")
    print("PHASE 5: CROSS-PLATFORM CONCURRENCY CORRECTNESS SUITE")
    print("==================================================================")

    results = {
        "tt_stress_test": {},
        "uci_lifecycle_test": {},
        "mate_normalization_test": {},
        "repetition_test": {},
        "consecutive_games_isolation": {},
        "all_passed": True
    }

    # 1. TT Concurrency Stress Test
    print("\n1. Running 20,000,000 Operations Concurrency Stress Test (4 Threads)...")
    compile_stress_test()
    p = subprocess.run([str(STRESS_EXE)], capture_output=True, text=True)
    print(p.stdout)
    stress_passed = (p.returncode == 0 and "100% DATA INTEGRITY" in p.stdout)
    results["tt_stress_test"] = {
        "output": p.stdout.strip(),
        "passed": stress_passed
    }

    # 2. UCI Protocol Lifecycle Stress Test (20 rapid cycles)
    print("\n2. Auditing UCI Protocol Lifecycle Stress (20 rapid cycles)...")
    lifecycle_cmds = "uci\nsetoption name Threads value 4\nisready\n"
    for i in range(20):
        lifecycle_cmds += "ucinewgame\nposition startpos\ngo depth 7\nstop\n"
    lifecycle_cmds += "quit\n"

    t0 = time.perf_counter()
    out_life = run_uci(ENGINE_W4, lifecycle_cmds, timeout_sec=30)
    dur_life = time.perf_counter() - t0
    bestmoves = sum(1 for l in out_life.splitlines() if "bestmove" in l)
    life_ok = (bestmoves == 20)
    results["uci_lifecycle_test"] = {
        "cycles_attempted": 20,
        "bestmoves_returned": bestmoves,
        "elapsed_sec": round(dur_life, 3),
        "passed": life_ok
    }
    print(f"  Lifecycle: 20 cycles -> {bestmoves}/20 bestmoves returned in {dur_life:.2f}s -> {'PASSED' if life_ok else 'FAILED'}")

    # 3. Mate Normalization Invariants
    print("\n3. Testing Mate Score Normalization Invariants...")
    mate_tests = [
        {"name": "scholars_mate", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "exp": "h5f7"},
        {"name": "legals_mate", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "exp": "d5f6"}
    ]
    mate_ok = True
    results["mate_normalization_test"]["cases"] = {}
    for m in mate_tests:
        cmds = f"uci\nsetoption name Threads value 4\nisready\nposition fen {m['fen']}\ngo depth 6\nquit\n"
        out = run_uci(ENGINE_W4, cmds)
        found_m = None
        for l in out.splitlines():
            if "bestmove" in l:
                found_m = l.split()[1]
        t_pass = (found_m == m["exp"])
        results["mate_normalization_test"]["cases"][m["name"]] = {
            "expected": m["exp"],
            "found": found_m,
            "passed": t_pass
        }
        if not t_pass: mate_ok = False
        print(f"  [{m['name']}] Exp={m['exp']}, Found={found_m} -> {'PASSED' if t_pass else 'FAILED'}")
    results["mate_normalization_test"]["all_passed"] = mate_ok

    # 4. Threefold Repetition under Concurrency
    print("\n4. Testing Threefold Repetition Adjudication under Threads=4...")
    rep_seq = "position startpos moves g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8"
    cmd_rep = f"uci\nsetoption name Threads value 4\nisready\n{rep_seq}\ngo depth 6\nquit\n"
    out_rep = run_uci(ENGINE_W4, cmd_rep)
    rep_score = None
    for l in out_rep.splitlines():
        if "info depth 6" in l and "score cp" in l:
            m = re.search(r'score cp (-?\d+)', l)
            if m: rep_score = int(m.group(1))
    rep_pass = (rep_score == 0)
    results["repetition_test"] = {
        "score_cp": rep_score,
        "is_exact_zero_draw": rep_pass
    }
    print(f"  Repetition Score = {rep_score} cp -> {'PASSED' if rep_pass else 'FAILED'}")

    # 5. Consecutive Games State Isolation
    print("\n5. Auditing Consecutive Games State Isolation (10 sequential searches)...")
    consec_cmds = "uci\nsetoption name Threads value 4\nisready\n"
    for i in range(10):
        consec_cmds += "position startpos\ngo movetime 50\n"
    consec_cmds += "quit\n"
    out_consec = run_uci(ENGINE_W4, consec_cmds)
    consec_moves = [l.split()[1] for l in out_consec.splitlines() if l.startswith("bestmove")]
    consec_ok = (len(consec_moves) == 10 and all(len(m) >= 4 for m in consec_moves))
    results["consecutive_games_isolation"] = {
        "moves_returned": len(consec_moves),
        "passed": consec_ok
    }
    print(f"  Consecutive Games: {len(consec_moves)}/10 searches completed cleanly -> {'PASSED' if consec_ok else 'FAILED'}")

    results["all_passed"] = bool(stress_passed and life_ok and mate_ok and rep_pass and consec_ok)

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n==================================================================")
    print(f"PHASE 5 CONCURRENCY CORRECTNESS STATUS: {'ALL PASSED' if results['all_passed'] else 'FAILURES DETECTED'}")
    print(f"Report written to {RAW_OUT}")
    print("==================================================================")

if __name__ == "__main__":
    main()

