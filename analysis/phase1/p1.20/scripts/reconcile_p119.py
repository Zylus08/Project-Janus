#!/usr/bin/env python3
"""
reconcile_p119.py
Milestone P1.20 Phase 0: Independent P1.19 Scientific Reconciliation & Statistical Audit.
Parses all 570 P1.19 tournament and development games, recomputes paired statistics,
audits cryptographic checksums, and tests the exact slow-time paired p-value calculation.
"""

import os
import sys
import json
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
P119_DIR = ROOT / "analysis" / "phase1" / "p1.19"
PGN_DIR = P119_DIR / "pgn"
RAW_DIR = P119_DIR / "raw"
CONTROL_DIR = P119_DIR / "control"
OUT_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def calc_elo(p: float) -> Optional[float]:
    if p <= 0.00001 or p >= 0.99999:
        return None
    return -400.0 * math.log10(1.0 / p - 1.0)

def calc_paired_ci_and_pvalue(pair_scores: List[float], z: float = 1.95996) -> Tuple[float, float, float, float, float]:
    n = len(pair_scores)
    if n == 0:
        return 0.0, 0.0, 1.0, 1.0, 1.0
    mean_p = sum(pair_scores) / n
    if n == 1:
        return mean_p, 0.0, 1.0, 0.5, 1.0
    var = sum((x - mean_p) ** 2 for x in pair_scores) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 1e-6
    ci_low = max(0.0, mean_p - z * se)
    ci_high = min(1.0, mean_p + z * se)
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    one_sided_p = 0.5 * math.erfc(t_stat / math.sqrt(2))
    two_sided_p = 2.0 * min(one_sided_p, 1.0 - one_sided_p)
    return mean_p, ci_low, ci_high, one_sided_p, two_sided_p

def parse_pgn_file(pgn_path: Path, cand_name: str) -> Dict[str, Any]:
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            result = game.headers.get("Result", "*")
            term = game.headers.get("Termination", "")
            eco = game.headers.get("ECO", "")
            opening = game.headers.get("Opening", "")

            # Move count
            plies = 0
            curr = game
            while curr.variations:
                curr = curr.variation(0)
                plies += 1

            games.append({
                "white": white,
                "black": black,
                "result": result,
                "termination": term,
                "eco": eco,
                "opening": opening,
                "plies": plies
            })

    total_games = len(games)
    num_pairs = total_games // 2

    wins = 0
    draws = 0
    losses = 0
    cand_score = 0.0

    penta = {2.0: 0, 1.5: 0, 1.0: 0, 0.5: 0, 0.0: 0}
    pair_scores = []

    for p in range(num_pairs):
        g1 = games[2 * p]
        g2 = games[2 * p + 1]

        # Determine points for candidate in g1 and g2
        if cand_name in g1["white"]:
            s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
        else:
            s1 = 1.0 if g1["result"] == "0-1" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)

        if cand_name in g2["white"]:
            s2 = 1.0 if g2["result"] == "1-0" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)
        else:
            s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)

        pair_s = (s1 + s2) / 2.0
        pair_scores.append(pair_s)
        penta[s1 + s2] += 1
        cand_score += (s1 + s2)

        for s in (s1, s2):
            if s == 1.0: wins += 1
            elif s == 0.5: draws += 1
            else: losses += 1

    win_rate = (cand_score / total_games) * 100.0 if total_games > 0 else 0.0
    elo = calc_elo(cand_score / total_games) if total_games > 0 else None
    mean_p, ci_low, ci_high, p_val_one, p_val_two = calc_paired_ci_and_pvalue(pair_scores)

    return {
        "file": pgn_path.name,
        "total_games": total_games,
        "num_pairs": num_pairs,
        "cand_score": cand_score,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate_percent": round(win_rate, 2),
        "elo": round(elo, 1) if elo is not None else None,
        "paired_ci_95": [round(ci_low * 100, 2), round(ci_high * 100, 2)],
        "p_value_one_sided": round(p_val_one, 4),
        "p_value_two_sided": round(p_val_two, 4),
        "pentanomial": penta,
        "sample_pair_scores": pair_scores[:10]
    }

def audit_all():
    print("=" * 80)
    print("MILESTONE P1.20 PHASE 0: P1.19 SCIENTIFIC RECONCILIATION AUDIT")
    print("=" * 80)

    # 1. Checksum verification of control binaries
    binaries = {
        "x7_single_thread": ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe",
        "x12_four_thread": ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe",
        "x22_research_ref": ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe",
        "x23_rejected_candidate": ROOT / "analysis" / "phase1" / "p1.18" / "control" / "janus_classical_x23.exe",
        "x24_candidate_exe": CONTROL_DIR / "janus_classical_x24.exe",
        "x24_candidate_dll": CONTROL_DIR / "janus_classical_x24.dll",
        "x24_candidate_cpp": CONTROL_DIR / "janus_classical_x24.cpp"
    }

    checksum_results = {}
    for name, path in binaries.items():
        if path.exists():
            h = sha256_file(path)
            checksum_results[name] = {"path": str(path), "sha256": h, "status": "EXISTS"}
            print(f"[{name}] {h} ({path.name})")
        else:
            checksum_results[name] = {"path": str(path), "status": "MISSING"}
            print(f"[{name}] MISSING: {path}")

    # 2. PGN Reconstruction
    matches = [
        ("match_dev_x24_vs_x22.pgn", "Janus Classical X24-S"),
        ("match_1_x24-s_vs_x22-s_ref_1t.pgn", "Janus Classical X24-S"),
        ("match_2_x24-s_vs_x7_baseline_1t.pgn", "Janus Classical X24-S"),
        ("match_3_x24-p_vs_x12_baseline_4t.pgn", "Janus Classical X24-P"),
        ("match_4_x24-s_vs_x7_slow_tc.pgn", "Janus Classical X24-S"),
        ("match_5_x24-s_vs_stockfish_4.pgn", "Janus Classical X24-S"),
        ("match_6_x24-s_vs_stockfish_11.pgn", "Janus Classical X24-S"),
        ("match_7_x24-s_vs_stockfish_19.pgn", "Janus Classical X24-S"),
    ]

    reconstructed_matches = {}
    total_reconstructed_games = 0

    print("\n--- Reconstructing Tournament PGNs ---")
    for filename, cand_name in matches:
        p = PGN_DIR / filename
        if p.exists():
            res = parse_pgn_file(p, cand_name)
            reconstructed_matches[filename] = res
            total_reconstructed_games += res["total_games"]
            print(f"Parsed {filename:40s}: {res['total_games']:3d} games | Score: {res['cand_score']:4.1f}/{res['total_games']} ({res['win_rate_percent']:5.1f}%) | Elo: {res['elo']} | CI: {res['paired_ci_95']} | p2: {res['p_value_two_sided']}")
        else:
            print(f"MISSING PGN: {p}")

    print(f"\nTotal Reconstructed Games: {total_reconstructed_games} (Expected: 570 games)")

    # 3. Audit slow-time p-value of Match 4
    m4 = reconstructed_matches.get("match_4_x24-s_vs_x7_slow_tc.pgn")
    p_value_audit = {}
    if m4:
        p_val_2 = m4["p_value_two_sided"]
        p_val_1 = m4["p_value_one_sided"]
        p_value_audit = {
            "match": "Match 4 (Slow TC)",
            "games": m4["total_games"],
            "pairs": m4["num_pairs"],
            "score": m4["cand_score"],
            "win_rate": m4["win_rate_percent"],
            "paired_ci_95": m4["paired_ci_95"],
            "reported_two_sided_p": 0.0129,
            "recomputed_two_sided_p": p_val_2,
            "recomputed_one_sided_p": p_val_1,
            "match_exact": (abs(p_val_2 - 0.0129) < 0.001)
        }
        print(f"\nMatch 4 Slow-TC p-value verification:")
        print(f"  Reported: 0.0129 | Recomputed: {p_val_2:.4f} | Exact Match: {p_value_audit['match_exact']}")

    output = {
        "checksums": checksum_results,
        "total_games": total_reconstructed_games,
        "reconstructed_matches": reconstructed_matches,
        "p_value_audit": p_value_audit
    }

    out_file = OUT_DIR / "p119_reconciliation_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nReconciliation output saved to {out_file}")

if __name__ == "__main__":
    audit_all()
