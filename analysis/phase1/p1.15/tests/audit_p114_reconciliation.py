#!/usr/bin/env python3
"""
audit_p114_reconciliation.py
Phase 0 Evidence Reconciliation for Milestone P1.15.
Reconstructs and verifies all 410 tournament games from P1.14 PGNs and raw JSON telemetry.
Computes rigorous confidence intervals (including Clopper-Pearson and Wilson for 0-score boundaries)
and audits fixed-depth ablation records.
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
P114_DIR = ROOT / "analysis" / "phase1" / "p1.14"
PGN_DIR = P114_DIR / "pgn"
RAW_P114 = P114_DIR / "raw" / "p114_tournaments_raw.json"
ABLATIONS_RAW = P114_DIR / "raw" / "controlled_ablations_raw.json"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.15" / "raw" / "p114_reconciliation_raw.json"

def wilson_ci(k: float, n: int, z: float = 1.95996) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))

def clopper_pearson_upper(n: int, alpha: float = 0.05) -> float:
    """One-sided or conservative two-sided upper bound for 0 successes: 1 - alpha^(1/n)."""
    return float(1.0 - (alpha / 2.0) ** (1.0 / n))

def paired_ci(pair_scores: List[float], z: float = 1.95996) -> Tuple[float, float]:
    n = len(pair_scores)
    if n <= 1:
        return 0.0, 1.0
    mean_p = sum(pair_scores) / n
    var = sum((x - mean_p) ** 2 for x in pair_scores) / (n - 1)
    se = math.sqrt(var / n)
    return float(max(0.0, mean_p - z * se)), float(min(1.0, mean_p + z * se))

def audit_pgn_file(pgn_path: Path, eng_a_name: str) -> Dict[str, Any]:
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if not g:
                break
            moves = list(g.mainline_moves())
            games.append({
                "round": g.headers.get("Round", ""),
                "white": g.headers.get("White", ""),
                "black": g.headers.get("Black", ""),
                "result": g.headers.get("Result", ""),
                "termination": g.headers.get("Termination", ""),
                "eco": g.headers.get("ECO", ""),
                "opening": g.headers.get("Opening", ""),
                "plies": len(moves)
            })

    total_games = len(games)
    num_pairs = total_games // 2
    wins_a, draws, losses_a = 0, 0, 0
    terminations = {}

    for g in games:
        res = g["result"]
        term = g["termination"]
        terminations[term] = terminations.get(term, 0) + 1
        is_a_white = (g["white"] == eng_a_name)
        if res == "1-0":
            if is_a_white: wins_a += 1
            else: losses_a += 1
        elif res == "0-1":
            if is_a_white: losses_a += 1
            else: wins_a += 1
        elif res in ("1/2-1/2", "0.5-0.5"):
            draws += 1
        else:
            raise ValueError(f"Unknown game result {res} in {pgn_path}")

    pts_a = wins_a + 0.5 * draws
    score_pct = (pts_a / total_games) * 100.0 if total_games > 0 else 0.0
    w_low, w_high = wilson_ci(pts_a, total_games)

    pentanomial = {"WW": 0, "WD": 0, "DD_WL": 0, "LD": 0, "LL": 0}
    pair_scores = []
    for p in range(num_pairs):
        g1 = games[2 * p]
        g2 = games[2 * p + 1]
        def g_pts(g):
            aw = (g["white"] == eng_a_name)
            if g["result"] == "1-0": return 1.0 if aw else 0.0
            if g["result"] == "0-1": return 0.0 if aw else 1.0
            return 0.5
        p_pts = g_pts(g1) + g_pts(g2)
        pair_scores.append(p_pts / 2.0)
        if p_pts == 2.0: pentanomial["WW"] += 1
        elif p_pts == 1.5: pentanomial["WD"] += 1
        elif p_pts == 1.0: pentanomial["DD_WL"] += 1
        elif p_pts == 0.5: pentanomial["LD"] += 1
        elif p_pts == 0.0: pentanomial["LL"] += 1

    p_low, p_high = paired_ci(pair_scores)

    # Proper boundary treatment for 0-score matches
    proper_boundary_interval = None
    if pts_a == 0:
        cp_upper = clopper_pearson_upper(total_games, alpha=0.05)
        proper_boundary_interval = [0.0, cp_upper * 100.0]

    return {
        "file": pgn_path.name,
        "total_games": total_games,
        "num_pairs": num_pairs,
        "wins_a": wins_a,
        "draws": draws,
        "losses_a": losses_a,
        "pts_a": pts_a,
        "score_pct": score_pct,
        "wilson_ci_pct": [w_low * 100.0, w_high * 100.0],
        "paired_ci_pct": [p_low * 100.0, p_high * 100.0],
        "proper_boundary_ci_pct": proper_boundary_interval,
        "pentanomial": pentanomial,
        "terminations": terminations
    }

def audit_ablations(abl_path: Path) -> Dict[str, Any]:
    with open(abl_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    b0_1t = data["B0_X7_1T"]
    b1_1t = data["B1_X19_1T"]
    b0_4t = data["B0_X12_4T"]
    b1_4t = data["B1_X19_4T"]

    # 1T: B0_X7 vs B1_X19
    nodes_b0_1t = b0_1t["total_nodes"]
    nodes_b1_1t = b1_1t["total_nodes"]
    time_b0_1t = b0_1t["total_time_s"]
    time_b1_1t = b1_1t["total_time_s"]

    # 4T: B0_X12 vs B1_X19
    nodes_b0_4t = b0_4t["total_nodes"]
    nodes_b1_4t = b1_4t["total_nodes"]
    time_b0_4t = b0_4t["total_time_s"]
    time_b1_4t = b1_4t["total_time_s"]

    # Score comparison across all positions
    score_mismatches_1t = []
    score_mismatches_4t = []
    for p0, p1 in zip(b0_1t["positions"], b1_1t["positions"]):
        if p0["score"] != p1["score"]:
            score_mismatches_1t.append((p0["id"], p0["score"], p1["score"]))
    for p0, p1 in zip(b0_4t["positions"], b1_4t["positions"]):
        if p0["score"] != p1["score"]:
            score_mismatches_4t.append((p0["id"], p0["score"], p1["score"]))

    return {
        "num_benchmark_positions": len(b0_1t["positions"]),
        "1T": {
            "nodes_b0_x7": nodes_b0_1t,
            "nodes_b1_x19": nodes_b1_1t,
            "node_reduction_pct": (nodes_b1_1t - nodes_b0_1t) / nodes_b0_1t * 100.0,
            "time_b0_x7": time_b0_1t,
            "time_b1_x19": time_b1_1t,
            "speedup_factor": time_b0_1t / time_b1_1t if time_b1_1t > 0 else 0.0,
            "score_mismatches": score_mismatches_1t,
            "bf1_b0": b0_1t["bf1_pct"],
            "bf1_b1": b1_1t["bf1_pct"]
        },
        "4T": {
            "nodes_b0_x12": nodes_b0_4t,
            "nodes_b1_x19": nodes_b1_4t,
            "node_reduction_pct": (nodes_b1_4t - nodes_b0_4t) / nodes_b0_4t * 100.0,
            "time_b0_x12": time_b0_4t,
            "time_b1_x19": time_b1_4t,
            "speedup_factor": time_b0_4t / time_b1_4t if time_b1_4t > 0 else 0.0,
            "score_mismatches": score_mismatches_4t,
            "bf1_b0": b0_4t["bf1_pct"],
            "bf1_b1": b1_4t["bf1_pct"]
        }
    }

def main():
    print("=== Reconciling P1.14 Tournament PGN Archives ===")
    match_targets = [
        ("x19_1t_vs_x7_1t.pgn", "Janus-X19-1T", 100),
        ("x19_1t_vs_x7_1t_slow.pgn", "Janus-X19-1T", 50),
        ("x19_4t_vs_x12_4t.pgn", "Janus-X19-4T", 100),
        ("x19_1t_vs_sf4_1t.pgn", "Janus-X19-1T", 40),
        ("x19_1t_vs_sf11_1t.pgn", "Janus-X19-1T", 40),
        ("x19_1t_vs_sf19_1t.pgn", "Janus-X19-1T", 40),
        ("x19_4t_vs_sf19_4t.pgn", "Janus-X19-4T", 40),
    ]

    reconciled_matches = []
    total_games_verified = 0

    for fname, eng_a, expected_games in match_targets:
        p = PGN_DIR / fname
        assert p.exists(), f"Missing PGN {p}"
        rec = audit_pgn_file(p, eng_a)
        assert rec["total_games"] == expected_games, f"Game count mismatch in {fname}: {rec['total_games']} vs {expected_games}"
        reconciled_matches.append(rec)
        total_games_verified += rec["total_games"]
        print(f"[{fname}] {rec['total_games']} games verified: {rec['wins_a']}W - {rec['draws']}D - {rec['losses_a']}L ({rec['score_pct']:.2f}%)")
        print(f"  Wilson CI: {rec['wilson_ci_pct'][0]:.2f}% - {rec['wilson_ci_pct'][1]:.2f}%")
        print(f"  Paired CI: {rec['paired_ci_pct'][0]:.2f}% - {rec['paired_ci_pct'][1]:.2f}%")
        if rec['proper_boundary_ci_pct']:
            print(f"  Proper Boundary CI: {rec['proper_boundary_ci_pct'][0]:.2f}% - {rec['proper_boundary_ci_pct'][1]:.2f}%")
        print(f"  Pentanomial: {rec['pentanomial']}")

    print(f"\nTotal tournament games verified across 7 PGNs: {total_games_verified}")

    print("\n=== Reconciling Fixed-Depth Benchmark Ablation Records ===")
    abl_res = audit_ablations(ABLATIONS_RAW)
    print(f"1T Node Reduction: {abl_res['1T']['node_reduction_pct']:.2f}% | Speedup: {abl_res['1T']['speedup_factor']:.2f}x | Score mismatches: {len(abl_res['1T']['score_mismatches'])}")
    print(f"4T Node Reduction: {abl_res['4T']['node_reduction_pct']:.2f}% | Speedup: {abl_res['4T']['speedup_factor']:.2f}x | Score mismatches: {len(abl_res['4T']['score_mismatches'])}")

    out_data = {
        "total_tournament_games": total_games_verified,
        "matches": reconciled_matches,
        "ablations": abl_res
    }

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\nReconciliation complete. Raw audit saved to {OUT_RAW}")

if __name__ == "__main__":
    main()
