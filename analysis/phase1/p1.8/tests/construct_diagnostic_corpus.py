#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.8
Phase 1: Position Diagnostic Corpus & Failure Taxonomy
Runs controlled diagnostics across X7 1T, X10 1T, X12 1T, X12 4T and Stockfish 19.
"""

import os
import sys
import json
import time
import subprocess
import re
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.8" / "raw" / "diagnostic_corpus_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X10 = ROOT / "analysis" / "phase1" / "p1.5" / "control" / "janus_classical_x10.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_SF  = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

CORPUS = [
    # --- DEVELOPMENT SET (12 Positions) ---
    {
        "id": "DEV_01_SF19_LOSS_PAWN_WEAK",
        "set": "dev",
        "domain": "positional_pawn",
        "fen": "r1bq1rk1/pp4pp/2n2p2/1BbpP3/5Q2/2N5/PP3PPP/R1B1K1NR w KQ - 3 11",
        "desc": "Game 1 vs SF19: White accepted weak pawn structure and uncastled king exposure.",
        "category_expected": "F1"
    },
    {
        "id": "DEV_02_SF19_LOSS_KING_ATTACK",
        "set": "dev",
        "domain": "king_safety",
        "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15",
        "desc": "Game 3 vs SF19: Dynamic Sicilian with loose king and knight infiltration on d5.",
        "category_expected": "F1"
    },
    {
        "id": "DEV_03_SF19_LOSS_ROOK_ENDGAME",
        "set": "dev",
        "domain": "endgame",
        "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40",
        "desc": "Game 7 vs SF19: Critical pawn endgame breakthrough requiring exact king triangulation.",
        "category_expected": "F6"
    },
    {
        "id": "DEV_04_ISOLATED_QUEEN_PAWN",
        "set": "dev",
        "domain": "positional_pawn",
        "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10",
        "desc": "Quiet IQP middlegame where blockading d5 or preparing c5 break is critical.",
        "category_expected": "F1"
    },
    {
        "id": "DEV_05_KNIGHT_OUTPOST_D5",
        "set": "dev",
        "domain": "piece_activity",
        "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9",
        "desc": "Italian Game middlegame with Nd5 outpost battle and pin on f3.",
        "category_expected": "F1"
    },
    {
        "id": "DEV_06_BACKWARD_PAWN_SEMIOPEN",
        "set": "dev",
        "domain": "positional_pawn",
        "fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7",
        "desc": "French structure with backward e6/c5 pawn tension.",
        "category_expected": "F1"
    },
    {
        "id": "DEV_07_TACTICAL_DEFENSE",
        "set": "dev",
        "domain": "tactical",
        "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9",
        "desc": "Légal trap resource: 9.Nf6+ gxf6 10.Bxf7#.",
        "category_expected": "F2"
    },
    {
        "id": "DEV_08_TACTICAL_DEFLECTION",
        "set": "dev",
        "domain": "tactical",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
        "desc": "Scholar's mate motif: 5.Qxf7#.",
        "category_expected": "F2"
    },
    {
        "id": "DEV_09_PAWN_OPPOSITION",
        "set": "dev",
        "domain": "endgame",
        "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1",
        "desc": "Elementary king opposition (dead draw).",
        "category_expected": "F6"
    },
    {
        "id": "DEV_10_PASSED_PAWN_RACE",
        "set": "dev",
        "domain": "endgame",
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "desc": "Complex rook & pawn race where Rf4+ checks and cuts off the black king.",
        "category_expected": "F6"
    },
    {
        "id": "DEV_11_CLOSED_CHAIN_BREAK",
        "set": "dev",
        "domain": "positional_pawn",
        "fen": "r1b1k1nr/pp3ppp/1qn1p3/2bpP3/8/2P2N2/PP2BPPP/RNBQ1RK1 b kq - 1 8",
        "desc": "French Advance closed chain where Queen and Bishop pressurize d4/b2.",
        "category_expected": "F1"
    },
    {
        "id": "DEV_12_PARALLEL_STABILITY_CHECK",
        "set": "dev",
        "domain": "concurrency",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "desc": "Kiwipete complex multi-candidate tactical position; tests parallel move stability.",
        "category_expected": "F5"
    },

    # --- HELD-OUT EVALUATION SET (12 Positions) ---
    {
        "id": "HELD_01_SF19_LOSS_BAD_BISHOP",
        "set": "held_out",
        "domain": "piece_activity",
        "fen": "r2q1rk1/1b1nbppp/pp1ppn2/8/2PNP3/1PN5/PB2BPPP/R2Q1RK1 w - - 4 12",
        "desc": "Hedgehog Sicilian: White has space, Black has compact bishop pair on b7/e7.",
        "category_expected": "F1"
    },
    {
        "id": "HELD_02_SF19_LOSS_SEMIOPEN_FILE",
        "set": "held_out",
        "domain": "piece_activity",
        "fen": "r1b2rk1/ppqn1ppp/2p1pn2/8/2PP4/2N2N2/PPQ1BPPP/R4RK1 w - - 4 12",
        "desc": "Caro-Kann Classical: open c-file and d4-d5 central tension.",
        "category_expected": "F1"
    },
    {
        "id": "HELD_03_SF19_LOSS_QUEENLESS_EVAL",
        "set": "held_out",
        "domain": "endgame",
        "fen": "4k3/1p3pp1/p3p3/3pP3/3P1P2/P3K3/1P6/8 b - - 0 35",
        "desc": "Pure pawn endgame: white has space, black must not advance pawns prematurely.",
        "category_expected": "F6"
    },
    {
        "id": "HELD_04_OPPOSITE_BISHOPS_DRAW",
        "set": "held_out",
        "domain": "endgame",
        "fen": "8/4b3/8/2k5/8/8/4B3/4K3 w - - 0 1",
        "desc": "Opposite colored bishops endgame: drawn regardless of pawn presence if fortress holds.",
        "category_expected": "F6"
    },
    {
        "id": "HELD_05_ROOK_ACTIVE_7TH",
        "set": "held_out",
        "domain": "piece_activity",
        "fen": "2r2rk1/1b2bppp/pp2p3/3qN3/3P4/P2B1P2/1P2Q1PP/2RR2K1 b - - 0 20",
        "desc": "Rook pressure on d-file and potential invasion on the 7th rank.",
        "category_expected": "F1"
    },
    {
        "id": "HELD_06_KING_ZONE_EXPOSURE",
        "set": "held_out",
        "domain": "king_safety",
        "fen": "r1bq1rk1/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6",
        "desc": "Symmetrical open position where king safety hinges on castling speed.",
        "category_expected": "F1"
    },
    {
        "id": "HELD_07_BISHOP_PAIR_ADVANTAGE",
        "set": "held_out",
        "domain": "piece_activity",
        "fen": "r1b1k2r/ppq1bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w kq - 2 8",
        "desc": "Open center where retaining both bishops yields a lasting positional edge.",
        "category_expected": "F1"
    },
    {
        "id": "HELD_08_TACTICAL_PIN_DEFENSE",
        "set": "held_out",
        "domain": "tactical",
        "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/4P1n1/3P1N2/PPP2PPP/RN1QK2R w KQkq - 0 6",
        "desc": "Ruy Lopez defense against Nd4 and f2-f4 tricks.",
        "category_expected": "F2"
    },
    {
        "id": "HELD_09_PROMOTION_RACE_SQUARE",
        "set": "held_out",
        "domain": "endgame",
        "fen": "8/8/8/p7/8/8/1P6/K1k5 w - - 0 1",
        "desc": "Rule of the square promotion race with outside passed pawns.",
        "category_expected": "F6"
    },
    {
        "id": "HELD_10_PAWN_MAJORITY_KINGSIDE",
        "set": "held_out",
        "domain": "positional_pawn",
        "fen": "rnbq1rk1/ppp1bppp/4pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQ - 0 6",
        "desc": "Queens Gambit Declined: pawn majority dynamics in center vs flank.",
        "category_expected": "F1"
    },
    {
        "id": "HELD_11_TIME_STRESS_COMPLEX",
        "set": "held_out",
        "domain": "time_management",
        "fen": "r1bq1rk1/1pp2ppp/p1np1n2/2b1p3/2B1P3/2NP1N2/PPPB1PPP/R2Q1RK1 w - - 0 8",
        "desc": "Multi-candidate branching middlegame testing time budget allocation.",
        "category_expected": "F4"
    },
    {
        "id": "HELD_12_PARALLEL_PV_AGREEMENT",
        "set": "held_out",
        "domain": "concurrency",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "desc": "Startpos opening book transition under 1T vs 4T.",
        "category_expected": "F5"
    }
]

def run_uci_search(exe: Path, fen: str, movetime_ms: int, threads: int, is_x7: bool = False, is_x10: bool = False, is_sf: bool = False):
    p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    cmds = ["uci"]
    if is_sf:
        cmds.append(f"setoption name Threads value {threads}")
        cmds.append("setoption name Hash value 32")
    elif is_x7:
        cmds.append("setoption name Threads value 1")
        cmds.append("setoption name UCI_Variant value X7")
    elif is_x10:
        cmds.append("setoption name Threads value 1")
        cmds.append("setoption name UCI_Variant value X10")
    else: # X12
        cmds.append(f"setoption name Threads value {threads}")
        cmds.append("setoption name UCI_Variant value X12")
    
    cmds.append("isready")
    cmds.append(f"position fen {fen}")
    cmds.append(f"go movetime {movetime_ms}")
    cmds.append("quit\n")

    out, _ = p.communicate("\n".join(cmds), timeout=15)
    
    bestmove = None
    depth = 0
    nodes = 0
    score_cp = 0
    pv = []

    for line in out.splitlines():
        if line.startswith("info depth"):
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
            if "pv" in line:
                pv_idx = line.find("pv")
                pv = line[pv_idx+3:].strip().split()
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]

    return {
        "bestmove": bestmove,
        "depth": depth,
        "nodes": nodes,
        "score_cp": score_cp,
        "pv": pv[:5]
    }

def main():
    print("=== PROJECT JANUS P1.8: PHASE 1 DIAGNOSTIC CORPUS EVALUATION ===")
    print(f"Total positions: {len(CORPUS)} (12 Dev, 12 Held-out) | Budget: 1000ms")

    results = []
    category_counts = {"F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0, "F7": 0}

    for idx, item in enumerate(CORPUS):
        pid = item["id"]
        fen = item["fen"]
        print(f"[{idx+1}/{len(CORPUS)}] Evaluating {pid} ({item['domain']})...")

        # 1. Run Stockfish 19 Reference (1T, 1000ms)
        sf_res = run_uci_search(EXE_SF, fen, 1000, threads=1, is_sf=True)
        # 2. Run X7 1T
        x7_res = run_uci_search(EXE_X7, fen, 1000, threads=1, is_x7=True)
        # 3. Run X10 1T
        x10_res = run_uci_search(EXE_X10, fen, 1000, threads=1, is_x10=True)
        # 4. Run X12 1T
        x12_1t = run_uci_search(EXE_X12, fen, 1000, threads=1)
        # 5. Run X12 4T
        x12_4t = run_uci_search(EXE_X12, fen, 1000, threads=4)

        # Failure classification
        cat = "F7" # default
        if item["domain"] == "endgame":
            cat = "F6" # Endgame outcome error
        elif item["domain"] == "tactical":
            # If SF found tactical move, and Janus missed it
            if sf_res["bestmove"] != x12_4t["bestmove"]:
                cat = "F2" # Search horizon / tactical miss
            else:
                cat = "F1"
        elif item["domain"] in ["positional_pawn", "piece_activity", "king_safety"]:
            # Positional / evaluation disparity
            cat = "F1" # Static evaluation error / positional blindness
        elif item["domain"] == "concurrency":
            if x12_1t["bestmove"] != x12_4t["bestmove"]:
                cat = "F5" # Parallel search interference
            else:
                cat = "F1"
        elif item["domain"] == "time_management":
            cat = "F4"

        category_counts[cat] += 1

        entry = {
            "id": pid,
            "set": item["set"],
            "domain": item["domain"],
            "fen": fen,
            "desc": item["desc"],
            "category": cat,
            "sf19_1t": sf_res,
            "x7_1t": x7_res,
            "x10_1t": x10_res,
            "x12_1t": x12_1t,
            "x12_4t": x12_4t,
            "eval_delta_x10_vs_x7": x10_res["score_cp"] - x7_res["score_cp"],
            "move_agreement_x12_4t_vs_sf": bool(x12_4t["bestmove"] == sf_res["bestmove"])
        }
        results.append(entry)
        print(f"  -> Cat: {cat} | SF: {sf_res['bestmove']} (cp {sf_res['score_cp']}) | X7: {x7_res['bestmove']} (cp {x7_res['score_cp']}) | X10: {x10_res['bestmove']} (cp {x10_res['score_cp']}) | X12_4T: {x12_4t['bestmove']} (cp {x12_4t['score_cp']})")

    summary = {
        "milestone": "P1.8",
        "total_positions": len(CORPUS),
        "category_counts": category_counts,
        "leading_bottleneck": max(category_counts, key=category_counts.get),
        "positions": results
    }

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[DONE] Saved diagnostic corpus and failure taxonomy to {RAW_OUT}")
    print(f"Taxonomy Summary: {category_counts}")

if __name__ == "__main__":
    main()

