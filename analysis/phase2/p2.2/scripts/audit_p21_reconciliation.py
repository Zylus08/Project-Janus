#!/usr/bin/env python3
"""
audit_p21_reconciliation.py
Phase 0: Formal Scientific Reconciliation of Milestone P2.1 Artifacts, Hashes, and Tournament Records.
"""

import os
import sys
import json
import hashlib
import math
from pathlib import Path
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
P21_DIR = ROOT / "analysis" / "phase2" / "p2.1"
P22_DIR = ROOT / "analysis" / "phase2" / "p2.2"
P22_DIR.mkdir(parents=True, exist_ok=True)
(P22_DIR / "raw").mkdir(parents=True, exist_ok=True)
(P22_DIR / "scripts").mkdir(parents=True, exist_ok=True)

def sha256_file(p: Path) -> str:
    if not p.exists():
        return "MISSING"
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def wilson_interval(k: float, n: int, z: float = 1.95996):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    spread = (z / denom) * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4 * (n**2)))
    return max(0.0, center - spread), min(1.0, center + spread)

def main():
    print("=" * 80)
    print("PHASE 0: P2.1 SCIENTIFIC RECONCILIATION & INTEGRITY AUDIT")
    print("=" * 80)

    # 1. Binary & Model Identities
    h1_exe = P21_DIR / "control" / "janus_hybrid_h1.exe"
    h1_dll = P21_DIR / "control" / "janus_hybrid_h1.dll"
    h1_bin = P21_DIR / "models" / "janus_nnue_h1.bin"
    r1_exe = ROOT / "analysis" / "phase1" / "p1.22" / "control" / "janus_classical_r1.exe"
    x7_exe = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
    x22_exe = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"

    expected_hashes = {
        "H1_EXE": "755C451D064EA38ECC400274CBCE48D28B6F43F67747BB63C0F4E84F6EA4F97A",
        "H1_BIN": "FD4D8105C39FD9A0CBCEB9B66236318CFA54A905E94F0688A4498305FF621B18",
        "R1_EXE": "7312B2B73CD9D40F108EE1B5F3903632A2A7805B19BC73082A796922DE66029B",
        "X7_EXE": "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B",
        "X22_EXE": "35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C",
    }

    actual_hashes = {
        "H1_EXE": sha256_file(h1_exe),
        "H1_BIN": sha256_file(h1_bin),
        "R1_EXE": sha256_file(r1_exe),
        "X7_EXE": sha256_file(x7_exe),
        "X22_EXE": sha256_file(x22_exe),
    }

    print("\n--- 1. Binary & Model SHA-256 Hashes ---")
    all_hashes_match = True
    for k, exp in expected_hashes.items():
        act = actual_hashes[k]
        match = (act == exp)
        print(f"  {k:8s}: {act} (Match: {match})")
        if not match:
            all_hashes_match = False

    # 2. Audit Tournament Records & PGN Files
    print("\n--- 2. Tournament Reconstruction (450 Games across M1-M7) ---")
    with open(P21_DIR / "raw" / "p21_tournaments_raw.json", "r", encoding="utf-8") as f:
        t_data = json.load(f)

    total_reconstructed_games = 0
    recon_summary = []

    for m in t_data:
        mid = m["match_id"]
        desc = m["description"]
        pgn_file = ROOT / m["pgn_path"]
        
        # Verify PGN parsing
        pgn_games = 0
        pgn_w = 0
        pgn_d = 0
        pgn_l = 0
        terminations = {}
        
        if pgn_file.exists():
            with open(pgn_file, "r", encoding="utf-8") as pf:
                while True:
                    game = chess.pgn.read_game(pf)
                    if game is None:
                        break
                    pgn_games += 1
                    res = game.headers.get("Result", "*")
                    term = game.headers.get("Termination", "Unknown")
                    terminations[term] = terminations.get(term, 0) + 1
                    
                    white = game.headers.get("White", "")
                    cand_name = m["candidate"]
                    is_cand_white = (white == cand_name)
                    
                    if res == "1-0":
                        if is_cand_white: pgn_w += 1
                        else: pgn_l += 1
                    elif res == "0-1":
                        if is_cand_white: pgn_l += 1
                        else: pgn_w += 1
                    elif res == "1/2-1/2":
                        pgn_d += 1

        total_reconstructed_games += pgn_games
        pts = pgn_w + 0.5 * pgn_d
        pct = (pts / pgn_games * 100.0) if pgn_games > 0 else 0.0
        
        # Calculate Wilson interval for 0 scores
        w_low, w_high = wilson_interval(pts, pgn_games)

        recon = {
            "match_id": mid,
            "desc": desc,
            "raw_games": m["total_games"],
            "pgn_games": pgn_games,
            "score_pts": pts,
            "score_pct": pct,
            "wdl": f"+{pgn_w} ={pgn_d} -{pgn_l}",
            "raw_wdl": f"+{m['wins']} ={m['draws']} -{m['losses']}",
            "terminations": terminations,
            "wilson_ci": [round(w_low * 100.0, 2), round(w_high * 100.0, 2)],
            "pentanomial_asc": m["pentanomial_ascending_LL_to_WW"],
            "elo": m["elo"]
        }
        recon_summary.append(recon)
        print(f"  Match {mid:2s}: {pgn_games} games | Score: {pts}/{pgn_games} ({pct:.1f}%) | WDL: {recon['wdl']} | PGN matches raw: {pgn_games == m['total_games'] and pts == m['points']}")

    print(f"\nTotal Games Reconstructed from PGNs: {total_reconstructed_games} / 450")

    # Save reconciliation raw report
    out_path = P22_DIR / "raw" / "p21_reconciliation_audit.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "hashes_match": all_hashes_match,
            "actual_hashes": actual_hashes,
            "reconstructed_games": total_reconstructed_games,
            "matches": recon_summary
        }, f, indent=2)
    print(f"Audit output saved to: {out_path}")

if __name__ == "__main__":
    main()
