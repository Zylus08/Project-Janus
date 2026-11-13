#!/usr/bin/env python3
"""
Project Janus — Milestone P1.12
Phase 6: Causal Feature Decomposition Orchestrator

Evaluates individual components of P1.11's intervention on clean baselines:
  - F0: Frozen Baseline (Clean X7 for 1T, Clean X12 for 4T)
  - F1: Search-stack static evaluation tracking only
  - F2: Evaluation-aware RFP margin expansion only (+40*d if !improving)
  - F3: History-dampened LMR only (lower thresholds, no !improving dampening)
  - F4: Combined F2 + F3 (Evaluation-aware RFP + History-dampened LMR, without unconditional stack tracking)
  - F5: Full P1.11 intervention applied to clean baseline (Unconditional eval + RFP margin expansion + !improving LMR + History LMR)

Metrics:
  - NPS impact relative to F0 (%)
  - Search depth reached @ 200ms
  - Effective Branching Factor (EBF = nodes^(1/depth))
  - Agreement with F0 best move (%)
  - Ground truth tactical/positional precision (%)
  - Telemetry: RFP cutoffs, LMR reductions, eval calls
"""

import json
import math
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_HARNESS = ROOT / "analysis" / "phase1" / "p1.12" / "tests" / "feature_decomp.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.12" / "raw" / "p111_causal_feature_decomposition_raw.json"

ATLAS_POSITIONS = [
    # Category 1: Tactical Combinations
    {"id": "TAC_01", "category": "tactical", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "desc": "Scholar's Mate in 1", "expected": "h5f7"},
    {"id": "TAC_02", "category": "tactical", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "desc": "Legal's Mate in 2", "expected": "d5f6"},
    {"id": "TAC_03", "category": "tactical", "fen": "r1b2rk1/pp1p1pp1/1b1p2B1/n1q1p1p1/4P3/1QPP4/PP3PPP/R1B1K2R w KQ - 0 14", "desc": "Quiet deflection / mate threat", "expected": "c1e3"},
    {"id": "TAC_04", "category": "tactical", "fen": "2r3k1/1p3ppp/pq2p3/3p4/3P4/1P1Q4/P4PPP/2R3K1 b - - 0 20", "desc": "Back-rank tactic / rook trade", "expected": "c8c1"},

    # Category 2: Positional / Prophylaxis
    {"id": "POS_01", "category": "positional", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "desc": "Rubinstein French pawn center", "expected": "e1g1"},
    {"id": "POS_02", "category": "positional", "fen": "r2q1rk1/1pp1bppp/p1np1nb1/4p3/2B1P1P1/2NP1N1P/PPP1QP2/R1B2RK1 w - - 1 11", "desc": "Italian King-side prophylaxis", "expected": "h3h4"},
    {"id": "POS_03", "category": "positional", "fen": "r1b2rk1/ppqn1ppp/2pbpn2/3p4/2PP4/2N1PNB1/PPQ2PPP/R3KB1R w KQ - 4 9", "desc": "Caro-Kann outpost tension", "expected": "c4c5"},
    {"id": "POS_04", "category": "positional", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 b - - 0 9", "desc": "Queen's Indian space struggle", "expected": "a7a5"},

    # Category 3: Defensive & Counter-Attacking
    {"id": "DEF_01", "category": "defensive", "fen": "r1b1k2r/pppp1ppp/8/4q3/1bP5/2N1P3/PP1B1PPP/R2QKB1R b KQkq - 0 9", "desc": "Neutralizing pin on c3", "expected": "b4c3"},
    {"id": "DEF_02", "category": "defensive", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R w KQ - 3 9", "desc": "Dragon Sicilian English attack defense", "expected": "e1c1"},
    {"id": "DEF_03", "category": "defensive", "fen": "r1bqr1k1/pp3ppp/2n5/1B1p4/3P4/5N2/PP1Q1PPP/R4RK1 w - - 0 13", "desc": "Tarrasch IQP blockade", "expected": "b5c6"},
    {"id": "DEF_04", "category": "defensive", "fen": "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", "desc": "Four Knights tactical fork trick defense", "expected": "c4d5"},

    # Category 4: Endgames & Technique
    {"id": "END_01", "category": "endgame", "fen": "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1", "desc": "Key square opposition K+P", "expected": "e3f4"},
    {"id": "END_02", "category": "endgame", "fen": "8/5pk1/4p1p1/7p/3R3P/4PKP1/5P2/2r5 b - - 6 42", "desc": "Rook endgame active king", "expected": "c1c2"},
    {"id": "END_03", "category": "endgame", "fen": "8/2k5/4p3/3pP3/3P4/8/3K4/8 w - - 0 1", "desc": "Triangulation / waiting pawn endgame", "expected": "d2c3"},
    {"id": "END_04", "category": "endgame", "fen": "8/8/3k4/3p4/3P4/4K3/8/8 w - - 0 1", "desc": "Pawn break test position", "expected": "d4d5"}
]

FACTORS = ["F0", "F1", "F2", "F3", "F4", "F5"]

FACTOR_DESCRIPTIONS = {
    "F0": "Clean Baseline Control",
    "F1": "Search-Stack Static Eval Tracking Only",
    "F2": "Evaluation-Aware RFP Margin Expansion Only (+40*d if !improving)",
    "F3": "History-Dampened LMR Only (lower threshold, no !improving dampening)",
    "F4": "Combined F2 + F3 (RFP Expansion + History LMR, Lazy Static Eval)",
    "F5": "Full P1.11 Intervention (Unconditional Eval + RFP Expansion + !improving LMR + History LMR)"
}

def search_factor(fen: str, variant: str, factor: str, threads: int, movetime_ms: int = 200) -> Dict[str, Any]:
    cmd_lines = [
        "uci",
        f"setoption name UCI_Variant value {variant}",
        f"setoption name Threads value {threads}",
        f"setoption name UCI_FeatureFactor value {factor}",
        "telemetry_reset",
        "isready",
        "ucinewgame",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "telemetry_report",
        "quit"
    ]
    cmd_str = "\n".join(cmd_lines) + "\n"

    proc = subprocess.Popen(
        [str(EXE_HARNESS)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, _ = proc.communicate(cmd_str)

    bm = ""
    depth = 0
    seldepth = 0
    nodes = 0
    nps = 0
    score_cp = 0
    time_ms = 0
    telemetry = {}

    in_telemetry = False
    for line in stdout.splitlines():
        line = line.strip()
        if "info" in line and "depth" in line:
            parts = line.split()
            if "depth" in parts:
                depth = int(parts[parts.index("depth") + 1])
            if "seldepth" in parts:
                seldepth = int(parts[parts.index("seldepth") + 1])
            if "nodes" in parts:
                nodes = int(parts[parts.index("nodes") + 1])
            if "nps" in parts:
                nps = int(parts[parts.index("nps") + 1])
            if "time" in parts:
                time_ms = int(parts[parts.index("time") + 1])
            if "score" in parts and "cp" in parts:
                score_cp = int(parts[parts.index("cp") + 1])
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bm = parts[1]
        if line == "TELEMETRY_START":
            in_telemetry = True
            continue
        if line == "TELEMETRY_END":
            in_telemetry = False
            continue
        if in_telemetry:
            tokens = line.split()
            if len(tokens) == 2:
                try:
                    telemetry[tokens[0]] = int(tokens[1])
                except ValueError:
                    telemetry[tokens[0]] = tokens[1]

    ebf = round(math.pow(nodes, 1.0 / max(1, depth)), 3) if depth > 0 and nodes > 0 else 0.0

    return {
        "best_move": bm,
        "depth": depth,
        "seldepth": seldepth if seldepth > 0 else depth,
        "nodes": nodes,
        "nps": nps,
        "time_ms": time_ms,
        "score_cp": score_cp,
        "ebf": ebf,
        "telemetry": telemetry
    }


def run_track(track_name: str, variant: str, threads: int) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f"Running Causal Feature Decomposition: {track_name} ({threads}T, {variant})")
    print(f"=======================================================")

    track_results = {f: {} for f in FACTORS}
    f0_moves = {}

    for factor in FACTORS:
        print(f"--> Testing Factor {factor}: {FACTOR_DESCRIPTIONS[factor]} ...")
        factor_positions = []
        for p in ATLAS_POSITIONS:
            res = search_factor(p["fen"], variant, factor, threads, movetime_ms=200)
            if factor == "F0":
                f0_moves[p["id"]] = res["best_move"]

            agreement = (res["best_move"] == f0_moves.get(p["id"], ""))
            correct = (res["best_move"] == p["expected"])

            pos_record = {
                "id": p["id"],
                "category": p["category"],
                "desc": p["desc"],
                "expected": p["expected"],
                "best_move": res["best_move"],
                "depth": res["depth"],
                "seldepth": res["seldepth"],
                "nodes": res["nodes"],
                "nps": res["nps"],
                "ebf": res["ebf"],
                "time_ms": res["time_ms"],
                "agreement_with_f0": agreement,
                "ground_truth_match": correct,
                "rfp_probes": res["telemetry"].get("rfp_probes", 0),
                "rfp_cutoffs": res["telemetry"].get("rfp_cutoffs", 0),
                "dynamic_lmr_reduced": res["telemetry"].get("dynamic_lmr_reduced", 0),
                "eval_calls": res["telemetry"].get("eval_calls", 0)
            }
            factor_positions.append(pos_record)

        # Aggregate summary for this factor
        total_nodes = sum(x["nodes"] for x in factor_positions)
        total_time_ms = sum(x["time_ms"] for x in factor_positions)
        mean_nps = int(sum(x["nps"] for x in factor_positions) / len(factor_positions))
        mean_depth = round(sum(x["depth"] for x in factor_positions) / len(factor_positions), 2)
        mean_ebf = round(sum(x["ebf"] for x in factor_positions) / len(factor_positions), 3)
        agreement_count = sum(1 for x in factor_positions if x["agreement_with_f0"])
        solved_count = sum(1 for x in factor_positions if x["ground_truth_match"])
        total_rfp_probes = sum(x["rfp_probes"] for x in factor_positions)
        total_rfp_cutoffs = sum(x["rfp_cutoffs"] for x in factor_positions)
        total_lmr_reduced = sum(x["dynamic_lmr_reduced"] for x in factor_positions)

        track_results[factor] = {
            "factor": factor,
            "description": FACTOR_DESCRIPTIONS[factor],
            "mean_nps": mean_nps,
            "mean_depth": mean_depth,
            "mean_ebf": mean_ebf,
            "total_nodes": total_nodes,
            "total_time_ms": total_time_ms,
            "f0_agreement_rate": round(agreement_count / len(factor_positions) * 100, 1),
            "ground_truth_accuracy": round(solved_count / len(factor_positions) * 100, 1),
            "rfp_cutoff_rate": round((total_rfp_cutoffs / max(1, total_rfp_probes)) * 100, 2),
            "total_rfp_cutoffs": total_rfp_cutoffs,
            "total_lmr_reduced": total_lmr_reduced,
            "positions": factor_positions
        }

    # Relative comparisons against F0
    f0_nps = track_results["F0"]["mean_nps"]
    f0_depth = track_results["F0"]["mean_depth"]
    for f in FACTORS:
        track_results[f]["nps_relative_pct"] = round(((track_results[f]["mean_nps"] - f0_nps) / f0_nps) * 100, 2)
        track_results[f]["depth_delta"] = round(track_results[f]["mean_depth"] - f0_depth, 2)

    return track_results


def main():
    start_time = time.time()
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

    # 1. Track S (1T) on X7 Foundation
    track_s = run_track("Track S (1-Threaded X7)", variant="X7", threads=1)

    # 2. Track P (4T) on X12 Foundation
    track_p = run_track("Track P (4-Threaded X12)", variant="X12", threads=4)

    total_duration = round(time.time() - start_time, 2)

    dataset = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration_sec": total_duration,
        "harness_binary": str(EXE_HARNESS),
        "test_budget_movetime_ms": 200,
        "num_diagnostic_positions": len(ATLAS_POSITIONS),
        "track_s_1t": track_s,
        "track_p_4t": track_p
    }

    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"\n=======================================================")
    print(f"Phase 6 Decomposition Complete in {total_duration}s!")
    print(f"Output saved to: {OUT_RAW}")
    print(f"=======================================================")

    # Print summary tables
    for track_label, data in [("Track S (1T, X7 Base)", track_s), ("Track P (4T, X12 Base)", track_p)]:
        print(f"\n--- {track_label} Summary ---")
        print(f"{'Factor':<8} {'NPS':<10} {'Rel %':<10} {'Depth':<8} {'Δ Depth':<10} {'EBF':<8} {'F0 Agree %':<12} {'Solved %':<10}")
        for f in FACTORS:
            d = data[f]
            print(f"{f:<8} {d['mean_nps']:<10} {d['nps_relative_pct']:>+6.2f}%   {d['mean_depth']:<8} {d['depth_delta']:>+5.2f}    {d['mean_ebf']:<8} {d['f0_agreement_rate']:<12} {d['ground_truth_accuracy']:<10}")


if __name__ == "__main__":
    main()

