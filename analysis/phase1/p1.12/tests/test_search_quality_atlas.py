#!/usr/bin/env python3
"""
Comprehensive Search Quality Atlas Benchmark for Milestone P1.12.
Independent 16-position diagnostic set comparing:
  - 1T Track: X7, X15, X16
  - 4T Track: X12, X15, X16
Metrics: root move, depth, nodes, time_ms, NPS, score_cp, ground truth correctness.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X15 = ROOT / "analysis" / "phase1" / "p1.10" / "control" / "janus_classical_x15.exe"
EXE_X16 = ROOT / "analysis" / "phase1" / "p1.11" / "control" / "janus_classical_x16.exe"
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

OUT_RAW = ROOT / "analysis" / "phase1" / "p1.12" / "raw" / "search_quality_atlas_raw.json"

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


def search_uci(exe_path: Path, fen: str, threads: int, extra_opts: dict, movetime_ms: int = 200) -> Dict[str, Any]:
    lines = ["uci", f"setoption name Threads value {threads}"]
    for k, v in extra_opts.items():
        lines.append(f"setoption name {k} value {v}")
    lines.extend(["isready", "ucinewgame", f"position fen {fen}", f"go movetime {movetime_ms}", "quit"])
    cmd_str = "\n".join(lines) + "\n"

    proc = subprocess.Popen(
        [str(exe_path)],
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
    score = 0
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
            if "score" in parts and "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bm = parts[1]

    return {
        "best_move": bm,
        "depth": depth,
        "seldepth": seldepth if seldepth > 0 else depth,
        "nodes": nodes,
        "nps": nps,
        "score_cp": score
    }


def main():
    print("=" * 80)
    print("EXECUTING CLASSICAL SEARCH QUALITY ATLAS BENCHMARK (16 POSITIONS @ 200ms)")
    print("=" * 80)

    atlas_data = []

    for idx, pos in enumerate(ATLAS_POSITIONS, 1):
        fen = pos["fen"]
        pos_id = pos["id"]
        category = pos["category"]
        desc = pos["desc"]

        # Track S (1T)
        res_x7_1t  = search_uci(EXE_X7,  fen, threads=1, extra_opts={"UCI_Variant": "X7", "UCI_DynamicTime": "false"})
        res_x15_1t = search_uci(EXE_X15, fen, threads=1, extra_opts={"UCI_Variant": "X15"})
        res_x16_1t = search_uci(EXE_X16, fen, threads=1, extra_opts={"UCI_Variant": "X16"})

        # Track P (4T)
        res_x12_4t = search_uci(EXE_X12, fen, threads=4, extra_opts={"UCI_Variant": "X12", "UCI_ClassicalEval": "E10"})
        res_x15_4t = search_uci(EXE_X15, fen, threads=4, extra_opts={"UCI_Variant": "X15"})
        res_x16_4t = search_uci(EXE_X16, fen, threads=4, extra_opts={"UCI_Variant": "X16"})

        # Ground Truth Stockfish 19
        gt_res = search_uci(EXE_SF19, fen, threads=1, extra_opts={"Hash": "32"}, movetime_ms=300)

        entry = {
            "id": pos_id,
            "category": category,
            "description": desc,
            "fen": fen,
            "ground_truth_sf19": gt_res["best_move"],
            "track_s_1t": {
                "x7": res_x7_1t,
                "x15": res_x15_1t,
                "x16": res_x16_1t
            },
            "track_p_4t": {
                "x12": res_x12_4t,
                "x15": res_x15_4t,
                "x16": res_x16_4t
            }
        }
        atlas_data.append(entry)

        print(f"[{pos_id:7s}] {category:10s} | 1T: X7={res_x7_1t['best_move']:5s} ({res_x7_1t['nps']} nps), X16={res_x16_1t['best_move']:5s} ({res_x16_1t['nps']} nps) | 4T: X12={res_x12_4t['best_move']:5s} ({res_x12_4t['nps']} nps), X16={res_x16_4t['best_move']:5s} ({res_x16_4t['nps']} nps) | GT: {gt_res['best_move']}")

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(atlas_data, f, indent=2)
    print(f"\nSaved Search Quality Atlas results to {OUT_RAW}")


if __name__ == "__main__":
    main()

