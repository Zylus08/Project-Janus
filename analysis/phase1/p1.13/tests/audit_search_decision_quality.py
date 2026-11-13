#!/usr/bin/env python3
"""
audit_search_decision_quality.py
Phase 3: Search Decision Quality Audit Across Diagnostic Corpus
Project Janus — Phase 1, Milestone P1.13
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
CORPUS_PATH = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
EXE_X = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.13" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


class UCIEngine:
    def __init__(self, exe_path: Path, threads: int = 1, variant: str = "", is_sf: bool = False):
        self.exe_path = exe_path
        self.threads = threads
        self.variant = variant
        self.is_sf = is_sf
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        self.send(f"setoption name Threads value {self.threads}")
        if self.is_sf:
            self.send("setoption name Hash value 32")
        elif self.variant:
            self.send(f"setoption name UCI_Variant value {self.variant}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            self.start()
        try:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
        except Exception:
            self.start()
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def analyze(self, fen: str, depth: int = 8) -> dict:
        if not self.proc or self.proc.poll() is not None:
            self.start()
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break
        self.send("ucinewgame")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        bestmove = None
        score_cp = 0
        nodes = 0
        pv = []
        is_mate = False

        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("info") and "depth" in line:
                parts = line.split()
                if "cp" in parts:
                    try:
                        score_cp = int(parts[parts.index("cp") + 1])
                    except Exception:
                        pass
                elif "mate" in parts:
                    try:
                        m_val = int(parts[parts.index("mate") + 1])
                        score_cp = 30000 if m_val > 0 else -30000
                        is_mate = True
                    except Exception:
                        pass
                if "nodes" in parts:
                    try:
                        nodes = int(parts[parts.index("nodes") + 1])
                    except Exception:
                        pass
                if "pv" in parts:
                    pv_idx = parts.index("pv")
                    pv = parts[pv_idx + 1:]
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break

        return {
            "bestmove": bestmove,
            "score_cp": score_cp,
            "nodes": nodes,
            "pv": pv[:5],
            "is_mate": is_mate
        }

    def stop(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                self.proc.kill()
            self.proc = None


def classify_outcome(board: chess.Board, janus_res: dict, sf_res: dict) -> str:
    jm = janus_res.get("bestmove")
    sfm = sf_res.get("bestmove")

    # Q4: Technical Failure
    if not jm:
        return "Q4"
    try:
        m = chess.Move.from_uci(jm)
        if m not in board.legal_moves:
            return "Q4"
    except Exception:
        return "Q4"

    # Q0: Verified Correct Decision (Matches reference best move or exact mate)
    if jm == sfm:
        return "Q0"

    # Evaluate centipawn difference according to reference
    j_score = janus_res.get("score_cp", 0)
    sf_score = sf_res.get("score_cp", 0)
    score_diff = abs(sf_score - j_score)

    # Q1: Verified Tactical Mistake (Large score gap >= 180 cp in tactical position)
    if score_diff >= 180:
        return "Q1"

    # Q3: Positional Reference Disagreement (Modest score gap <= 50 cp, both quiet moves)
    if score_diff <= 50:
        return "Q3"

    # Q2: Search Instability / Evaluative Disagreement
    if 50 < score_diff < 180:
        return "Q2"

    return "Q5"


def main():
    print("================================================================================")
    print("PHASE 3: SEARCH DECISION QUALITY AUDIT")
    print("================================================================================")

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus_data = json.load(f)

    # Stratified sample: 30 from dev_positions, 30 from held_out_positions = 60 total
    dev = corpus_data.get("dev_positions", [])
    held = corpus_data.get("held_out_positions", [])
    
    # Step sampling
    sample_dev = dev[::4][:30]
    sample_held = held[::4][:30]
    sample_corpus = sample_dev + sample_held
    print(f"Loaded {len(sample_corpus)} diagnostic positions for audit.")

    eng_x7 = UCIEngine(EXE_X, threads=1, variant="X7", is_sf=False)
    eng_x12 = UCIEngine(EXE_X, threads=4, variant="X12", is_sf=False)
    eng_sf11 = UCIEngine(EXE_SF11, threads=1, is_sf=True)

    eng_x7.start()
    eng_x12.start()
    eng_sf11.start()

    q_counts_x7 = {"Q0": 0, "Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "Q5": 0}
    q_counts_x12 = {"Q0": 0, "Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "Q5": 0}
    
    detailed_records = []
    search_depth = 8

    for idx, pos in enumerate(sample_corpus):
        fen = pos["fen"]
        pid = pos.get("id", f"POS_{idx+1}")
        cluster = pos.get("cluster", "general")
        board = chess.Board(fen)

        res_sf11 = eng_sf11.analyze(fen, depth=search_depth)
        res_x7 = eng_x7.analyze(fen, depth=search_depth)
        res_x12 = eng_x12.analyze(fen, depth=search_depth)

        q_x7 = classify_outcome(board, res_x7, res_sf11)
        q_x12 = classify_outcome(board, res_x12, res_sf11)

        q_counts_x7[q_x7] += 1
        q_counts_x12[q_x12] += 1

        record = {
            "id": pid,
            "cluster": cluster,
            "fen": fen,
            "sf11": res_sf11,
            "x7": res_x7,
            "x12": res_x12,
            "class_x7": q_x7,
            "class_x12": q_x12
        }
        detailed_records.append(record)

        if (idx + 1) % 10 == 0 or idx == len(sample_corpus) - 1:
            print(f"[{idx+1}/{len(sample_corpus)}] Pos {pid} ({cluster}): SF={res_sf11['bestmove']}, X7={res_x7['bestmove']} [{q_x7}], X12={res_x12['bestmove']} [{q_x12}]")

    eng_x7.stop()
    eng_x12.stop()
    eng_sf11.stop()

    total_n = len(sample_corpus)
    print("\n================================================================================")
    print("SEARCH DECISION QUALITY DISTRIBUTION SUMMARY (N = 60)")
    print("================================================================================")
    print("Janus X7 (1T Baseline):")
    for k in ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5"]:
        cnt = q_counts_x7[k]
        pct = (cnt / total_n) * 100.0
        print(f"  {k}: {cnt:2d} / {total_n} ({pct:5.1f}%)")

    print("\nJanus X12 (4T Baseline):")
    for k in ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5"]:
        cnt = q_counts_x12[k]
        pct = (cnt / total_n) * 100.0
        print(f"  {k}: {cnt:2d} / {total_n} ({pct:5.1f}%)")

    out_file = RAW_DIR / "search_decision_quality_atlas_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "positions_audited": total_n,
            "q_counts_x7": q_counts_x7,
            "q_counts_x12": q_counts_x12,
            "records": detailed_records
        }, f, indent=2)
    print(f"\nSaved raw audit data to {out_file}")

if __name__ == "__main__":
    main()
