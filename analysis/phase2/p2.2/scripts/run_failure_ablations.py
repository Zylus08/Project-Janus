#!/usr/bin/env python3
"""
run_failure_ablations.py
Phase 8: Controlled Model Failure Ablations & Match Qualification.
Ablations:
- A0: Classical R1 Baseline
- A1: Original Frozen H1 NNUE
- A2: Calibrated Scale H1 (Scaled 4x & De-biased)
- A4: Random / Untrained Network
- A5: Controlled Hybrid H2 (50% Classical + 50% H1)

Executes:
1. Diagnostic Evaluation on Benchmark Positions
2. 50-Game Head-to-Head Match: H2 (Hybrid) vs R1 (Classical) to determine whether
   Hybrid evaluation genuinely improves Classical R1 or degrades it.
"""

import sys
import ctypes
import json
import math
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import torch
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from run_p21_tournaments import UciEngine, play_opening_pair, wilson_score_interval, calc_paired_ci_and_pvalue, calc_elo

# Executables
H1_EXE = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.exe"
R1_EXE = ROOT / "analysis" / "phase1" / "p1.22" / "control" / "janus_classical_r1.exe"
OPENINGS_FILE = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

# Load DLL for evaluation testing
dll = ctypes.CDLL(str(ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.dll"))

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupied", ctypes.c_uint64 * 2),
        ("all_occupied", ctypes.c_uint64),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_int8),
        ("halfmove_clock", ctypes.c_uint8),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
        ("pawn_key", ctypes.c_uint64),
    ]

dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
dll.native_set_fen.restype = ctypes.c_bool
dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_evaluate.restype = ctypes.c_int
dll.native_r1_evaluate_nnue.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_r1_evaluate_nnue.restype = ctypes.c_int

def evaluate_ablation_diagnostics():
    print("=" * 80)
    print("PHASE 8: EVALUATION BEHAVIOR OF ABLATION CONFIGURATIONS")
    print("=" * 80)

    # Positions to test
    diag_fens = [
        ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 20),
        ("White +Q", "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 850),
        ("White +R", "1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 500),
        ("White +N", "r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 325),
        ("White +P", "rnbqkbnr/1ppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 100),
        ("Down Queen", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1", -850),
    ]

    print(f"{'Position':15s} | {'Truth':6s} | {'A0 (R1)':8s} | {'A1 (H1)':8s} | {'A2 (Calib)':10s} | {'A5 (H2 50/50)':12s}")
    print("-" * 75)

    diag_data = []

    for name, fen, truth in diag_fens:
        nb = NativeBoard()
        dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
        a0 = dll.native_evaluate(ctypes.byref(nb))
        a1 = dll.native_r1_evaluate_nnue(ctypes.byref(nb))
        # A2: Calibrated Scale H1 (de-bias by -52 cp, scale by 3.5x)
        a2 = int((a1 - 52) * 3.5) if a1 != 0 else 0
        # A5: Hybrid 50/50
        a5 = (a0 + a1) // 2

        print(f"{name:15s} | {truth:6d} | {a0:8d} | {a1:8d} | {a2:10d} | {a5:12d}")

        diag_data.append({
            "name": name,
            "fen": fen,
            "truth": truth,
            "a0_classical": a0,
            "a1_nnue": a1,
            "a2_calibrated": a2,
            "a5_hybrid": a5
        })

    return diag_data

def run_match_h2_vs_r1(n_pairs=25):
    print("\n" + "=" * 80)
    print(f"CRITICAL MATCH: HYBRID H2 vs CLASSICAL R1 ({n_pairs*2} GAMES)")
    print("Does Hybrid H2 genuinely improve Classical R1, or merely beat weak H1?")
    print("=" * 80)

    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        raw_openings = json.load(f)
        openings = [x["uci_sequence"] for x in raw_openings[:n_pairs]]

    c_h2 = (H1_EXE, "Janus_Hybrid_H2", 1, {"UCI_Variant": "H2", "UCI_Evaluation": "Hybrid", "NNUE_Weight": "50"})
    ref_r1 = (R1_EXE, "Janus_Classical_R1", 1, {"UCI_Variant": "R1", "UCI_Evaluation": "Classical"})

    concurrency = 8
    base_time = 5.0
    inc = 0.05
    t0 = time.time()
    pair_results = [None] * len(openings)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(play_opening_pair, i, c_h2, ref_r1, openings[i], base_time, inc): i
            for i in range(len(openings))
        }
        done = 0
        for fut in as_completed(futures):
            p_idx, r1, r2 = fut.result()
            pair_results[p_idx] = (r1, r2)
            done += 1
            if done % 5 == 0 or done == len(openings):
                print(f"  Progress: {done*2}/{len(openings)*2} games ({done*2/(len(openings)*2)*100:.1f}%)", flush=True)

    elapsed = time.time() - t0
    total_games = len(openings) * 2
    wins = draws = losses = 0
    h2_points = 0.0
    subcat_counts = {"LL": 0, "LD": 0, "DD": 0, "WL": 0, "WD": 0, "WW": 0}
    pair_scores_norm = []
    penta_asc = [0, 0, 0, 0, 0]

    for r1, r2 in pair_results:
        s1 = 1.0 if r1["result"] == "1-0" else (0.5 if r1["result"] == "1/2-1/2" else 0.0)
        s2 = 1.0 if r2["result"] == "0-1" else (0.5 if r2["result"] == "1/2-1/2" else 0.0)
        if s1 == 1.0: wins += 1
        elif s1 == 0.0: losses += 1
        else: draws += 1

        if s2 == 1.0: wins += 1
        elif s2 == 0.0: losses += 1
        else: draws += 1

        ps = s1 + s2
        h2_points += ps
        pair_scores_norm.append(ps / 2.0)

        if ps == 0.0: subcat_counts["LL"] += 1; penta_asc[0] += 1
        elif ps == 0.5: subcat_counts["LD"] += 1; penta_asc[1] += 1
        elif ps == 1.0:
            if s1 == 0.5 and s2 == 0.5: subcat_counts["DD"] += 1
            else: subcat_counts["WL"] += 1
            penta_asc[2] += 1
        elif ps == 1.5: subcat_counts["WD"] += 1; penta_asc[3] += 1
        elif ps == 2.0: subcat_counts["WW"] += 1; penta_asc[4] += 1

    score_pct = (h2_points / total_games) * 100.0
    elo = calc_elo(h2_points / total_games)
    mean_p, ci_low, ci_high, se, p2 = calc_paired_ci_and_pvalue(pair_scores_norm)
    wilson_low, wilson_high = wilson_score_interval(h2_points, total_games)
    elo_str = f"{elo:.1f}" if elo is not None else "N/A"

    print(f"\nRESULT H2 vs R1: {h2_points}/{total_games} (+{wins} ={draws} -{losses}) | {score_pct:.1f}% | Elo: {elo_str}")
    print(f"  Subcategories: {subcat_counts}")
    print(f"  Pentanomial [0.0..2.0]: {penta_asc}")
    print(f"  Paired 95% CI: [{ci_low*100.0:.1f}%, {ci_high*100.0:.1f}%] | SE: {se:.4f} | p-value: {p2:.4f} ({elapsed:.1f}s)")

    # Save PGN
    pgn_path = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "match_h2_vs_r1.pgn"
    with open(pgn_path, "w", encoding="utf-8") as pf:
        for p_idx, (r1, r2) in enumerate(pair_results):
            for g_num, gres in enumerate([r1, r2], 1):
                pf.write(f'[Event "H2 vs R1 Ablation Match"]\n')
                pf.write(f'[Round "{p_idx*2 + g_num}"]\n')
                pf.write(f'[White "{gres["white"]}"]\n')
                pf.write(f'[Black "{gres["black"]}"]\n')
                pf.write(f'[Result "{gres["result"]}"]\n')
                pf.write(f'[Termination "{gres["term_reason"]}"]\n\n')
                pf.write(" ".join(gres["moves"]) + f" {gres['result']}\n\n")

    return {
        "candidate": "Janus_Hybrid_H2",
        "opponent": "Janus_Classical_R1",
        "total_games": total_games,
        "points": h2_points,
        "score_pct": round(score_pct, 2),
        "elo": round(elo, 2) if elo is not None else None,
        "wins": wins, "draws": draws, "losses": losses,
        "subcategories": subcat_counts,
        "pentanomial_asc": penta_asc,
        "paired_ci_95": [round(ci_low * 100.0, 2), round(ci_high * 100.0, 2)],
        "p_value": round(p2, 4),
        "wilson_ci_95": [round(wilson_low * 100.0, 2), round(wilson_high * 100.0, 2)],
        "elapsed_seconds": round(elapsed, 1)
    }

def main():
    diag_data = evaluate_ablation_diagnostics()
    match_data = run_match_h2_vs_r1(25)

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "ablation_findings.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "diagnostics": diag_data,
            "h2_vs_r1_match": match_data
        }, f, indent=2)
    print(f"\nAblation report saved to: {out_file}")

if __name__ == "__main__":
    main()
