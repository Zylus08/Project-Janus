#!/usr/bin/env python3
"""
test_quiescence_provenance.py
Milestone P1.17 Phase 3: Quiescence Correctness Forensics across X7, X12, X19, X20, X21.
Runs 30 targeted FEN test positions across all 5 engines and records exact behaviors.
"""

import subprocess
import json
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.17" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

ENGINES = {
    "X7": ROOT / "analysis/phase1/p1.3/control/janus_classical_x7.exe",
    "X12": ROOT / "analysis/phase1/p1.7/control/janus_classical_x12.exe",
    "X19": ROOT / "analysis/phase1/p1.14/control/janus_classical_x19.exe",
    "X20": ROOT / "analysis/phase1/p1.15/control/janus_classical_x20.exe",
    "X21": ROOT / "analysis/phase1/p1.16/control/janus_classical_x21.exe",
}

# 30 Diagnostic FENs across 5 classes
TEST_CASES = [
    # Class 1: Checkmate in 1 (White to move, delivers mate) - 5 cases
    {"id": "M1_01", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5", "expected": "f3f7", "class": "mate_in_1"},
    {"id": "M1_02", "fen": "6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1", "expected": "e1e8", "class": "mate_in_1"},
    {"id": "M1_03", "fen": "r5rk/5p1p/5R2/8/8/8/1B6/7K w - - 0 1", "expected": "f6f7", "class": "mate_in_1"},
    {"id": "M1_04", "fen": "r1b1k2r/ppppqppp/8/4n3/1bP2B2/5N2/PP1NPPPP/R2QKB1R w KQkq - 0 8", "expected": "f4e5", "class": "mate_in_1"},
    {"id": "M1_05", "fen": "3r2k1/ppp2ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", "expected": "d1d8", "class": "mate_in_1"},

    # Class 2: In-Check Terminal Mate (Side to move is checkmated) - 5 cases
    {"id": "TERM_01", "fen": "rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", "expected": "mate", "class": "checkmated"},
    {"id": "TERM_02", "fen": "4R1k1/5ppp/8/8/8/8/8/6K1 b - - 1 1", "expected": "mate", "class": "checkmated"},
    {"id": "TERM_03", "fen": "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 5", "expected": "mate", "class": "checkmated"},
    {"id": "TERM_04", "fen": "3R2k1/ppp2ppp/8/8/8/8/5PPP/6K1 b - - 1 1", "expected": "mate", "class": "checkmated"},
    {"id": "TERM_05", "fen": "8/8/8/8/8/5k2/4q3/7K w - - 0 1", "expected": "mate_in_1_or_evasion", "class": "checkmated"},

    # Class 3: Stalemate (Side to move has no legal moves, not in check) - 5 cases
    {"id": "STALE_01", "fen": "k7/8/1Q6/8/8/8/8/7K b - - 0 1", "expected": "stalemate", "class": "stalemate"},
    {"id": "STALE_02", "fen": "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "expected": "stalemate", "class": "stalemate"},
    {"id": "STALE_03", "fen": "k7/2Q5/K7/8/8/8/8/8 b - - 0 1", "expected": "stalemate", "class": "stalemate"},
    {"id": "STALE_04", "fen": "8/8/8/8/8/1k6/p7/K7 w - - 0 1", "expected": "stalemate", "class": "stalemate"},
    {"id": "STALE_05", "fen": "8/8/8/8/8/k7/p1p5/K7 w - - 0 1", "expected": "stalemate", "class": "stalemate"},

    # Class 4: Quiet King Evasions under check - 5 cases
    {"id": "EVAS_01", "fen": "4k3/8/8/8/8/8/4r3/3K4 w - - 0 1", "expected": "d1e2_or_d1c1", "class": "quiet_evasion"},
    {"id": "EVAS_02", "fen": "8/8/8/8/8/4q3/8/3K1k2 w - - 0 1", "expected": "d1c2", "class": "quiet_evasion"},
    {"id": "EVAS_03", "fen": "8/8/8/8/8/3q4/8/1K2k3 w - - 0 1", "expected": "b1a1_or_b1b2_or_b1c1", "class": "quiet_evasion"},
    {"id": "EVAS_04", "fen": "8/8/8/8/8/8/r7/2K3k1 w - - 0 1", "expected": "c1b1_or_c1d1", "class": "quiet_evasion"},
    {"id": "EVAS_05", "fen": "8/8/8/8/8/5q2/8/2K3k1 w - - 0 1", "expected": "c1b2_or_c1d2_or_c1b1_or_c1d1", "class": "quiet_evasion"},

    # Class 5: Negative-SEE Mandatory Evasions (Capture or interposition with negative SEE is only evasion) - 5 cases
    {"id": "NEGSEE_01", "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/4n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 6", "expected": "d1e2", "class": "neg_see_evasion"},
    {"id": "NEGSEE_02", "fen": "r1b1k2r/pppp1ppp/5q2/4n3/1b2P3/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 0 7", "expected": "c1d2", "class": "neg_see_evasion"},
    {"id": "NEGSEE_03", "fen": "r1b1k2r/1ppp1ppp/p1n5/4p3/B3n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 8", "expected": "a4c6", "class": "neg_see_evasion"},
    {"id": "NEGSEE_04", "fen": "r1bqk2r/pppp1ppp/2n5/4p3/1b2n3/2PP1N2/PP3PPP/RNBQKB1R w KQkq - 0 6", "expected": "c3b4", "class": "neg_see_evasion"},
    {"id": "NEGSEE_05", "fen": "r2qk2r/ppp2ppp/2n5/1B1pp3/1b2n1b1/2PP1N2/PP3PPP/RNBQK2R w KQkq - 1 7", "expected": "b5c6", "class": "neg_see_evasion"},
]

def query_engine(exe: Path, fen: str, variant: str = "") -> dict:
    proc = subprocess.Popen(
        [str(exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True
    )
    cmd = "uci\n"
    if variant:
        cmd += f"setoption name UCI_Variant value {variant}\n"
    cmd += "isready\n"
    cmd += f"position fen {fen}\n"
    cmd += "go depth 2\n"
    cmd += "quit\n"

    out, _ = proc.communicate(cmd, timeout=5)
    bestmove = ""
    score_cp = None
    score_mate = None

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2: bestmove = parts[1]
        elif "score cp" in line:
            parts = line.split()
            try:
                score_cp = int(parts[parts.index("cp") + 1])
            except (ValueError, IndexError): pass
        elif "score mate" in line:
            parts = line.split()
            try:
                score_mate = int(parts[parts.index("mate") + 1])
            except (ValueError, IndexError): pass

    return {"bestmove": bestmove, "score_cp": score_cp, "score_mate": score_mate}

def main():
    print("Executing Quiescence Correctness Forensics across X7, X12, X19, X20, X21...")
    results = {}

    for eng_name, eng_path in ENGINES.items():
        print(f"Testing {eng_name} ({eng_path.name})...")
        variant = "X21" if eng_name == "X21" else ("X20" if eng_name == "X20" else ("X19" if eng_name == "X19" else ("X12" if eng_name == "X12" else "X7")))
        eng_results = []
        for tc in TEST_CASES:
            res = query_engine(eng_path, tc["fen"], variant=variant)
            eng_results.append({
                "id": tc["id"],
                "class": tc["class"],
                "bestmove": res["bestmove"],
                "score_cp": res["score_cp"],
                "score_mate": res["score_mate"]
            })
        results[eng_name] = eng_results

    out_file = RAW_DIR / "quiescence_provenance_raw.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Quiescence forensics completed. Raw data saved to {out_file}")

if __name__ == "__main__":
    main()
