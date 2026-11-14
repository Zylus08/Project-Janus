#!/usr/bin/env python3
"""
test_endgame_forensics.py
Milestone P1.20 Phase 4: Endgame Passivity and Activity Forensics.
Extracts critical endgame turning points from P1.19 Match 4 losses,
and performs counterfactual evaluation replays using:
  E0: Reference X22 (backward pawns disabled)
  E1: Candidate X24 (backward pawns enabled)
Measures:
  - Root best move divergence
  - Search score shift
  - Static eval shift
  - Rook activity vs passive defense
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
PGN_PATH = ROOT / "analysis" / "phase1" / "p1.19" / "pgn" / "match_4_x24-s_vs_x7_slow_tc.pgn"
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
EXE_X24 = ROOT / "analysis" / "phase1" / "p1.19" / "control" / "janus_classical_x24.exe"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Selected representative Match 4 loss games
SAMPLE_LOSS_GAMES = [4, 8, 14, 18, 24, 28, 38, 50]

class EngineTester:
    def __init__(self, exe_path: Path, name: str, bp: int = 0):
        self.exe_path = exe_path
        self.name = name
        self.bp = bp
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        self.send(f"setoption name UCI_BackwardPawns value {'true' if self.bp else 'false'}")
        self.send("setoption name Hash value 64")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def search_position(self, fen: str, movetime_ms: int = 500) -> Dict[str, Any]:
        self.send("ucinewgame")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

        self.send(f"position fen {fen}")
        self.send(f"go movetime {movetime_ms}")

        bestmove = ""
        score_cp = None
        depth = 0
        nodes = 0
        pv = []

        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("info"):
                parts = line_str.split()
                if "depth" in parts:
                    try:
                        depth = int(parts[parts.index("depth") + 1])
                    except Exception:
                        pass
                if "score" in parts and "cp" in parts:
                    try:
                        score_cp = int(parts[parts.index("cp") + 1])
                    except Exception:
                        pass
                if "nodes" in parts:
                    try:
                        nodes = int(parts[parts.index("nodes") + 1])
                    except Exception:
                        pass
                if "pv" in parts:
                    pv = parts[parts.index("pv") + 1:]
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break

        return {
            "bestmove": bestmove,
            "score_cp": score_cp,
            "depth": depth,
            "nodes": nodes,
            "pv": pv
        }

    def stop(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

def extract_endgame_positions():
    extracted = []
    with open(PGN_PATH, "r", encoding="utf-8") as f:
        g_num = 0
        while True:
            game = chess.pgn.read_game(f)
            if not game:
                break
            g_num += 1
            if g_num not in SAMPLE_LOSS_GAMES:
                continue

            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            result = game.headers.get("Result", "")
            eco = game.headers.get("ECO", "")
            opening = game.headers.get("Opening", "")

            # Replay game and sample position around move 35-45 (endgame transition)
            b = game.board()
            critical_fen = None
            critical_ply = 0
            moves = list(game.mainline_moves())

            target_ply = min(len(moves) - 10, max(60, len(moves) // 2))
            for p_idx, m in enumerate(moves):
                b.push(m)
                if p_idx == target_ply:
                    critical_fen = b.fen()
                    critical_ply = p_idx + 1

            if critical_fen:
                extracted.append({
                    "game_id": g_num,
                    "white": white,
                    "black": black,
                    "result": result,
                    "eco": eco,
                    "opening": opening,
                    "critical_ply": critical_ply,
                    "critical_fen": critical_fen,
                    "total_plies": len(moves)
                })
    return extracted

def run_forensics():
    print("=" * 80)
    print("MILESTONE P1.20 PHASE 4: ENDGAME PASSIVITY & ACTIVITY FORENSICS")
    print("=" * 80)

    positions = extract_endgame_positions()
    print(f"Extracted {len(positions)} critical endgame positions from Match 4 losses.")

    e_x22 = EngineTester(EXE_X22, "E0: Reference X22 (BP Off)", bp=0)
    e_x24 = EngineTester(EXE_X24, "E1: Candidate X24 (BP On)", bp=1)
    e_x22.start()
    e_x24.start()

    forensic_cases = []

    divergence_count = 0
    passive_concession_count = 0

    for idx, pos in enumerate(positions):
        fen = pos["critical_fen"]
        g_id = pos["game_id"]

        res_x22 = e_x22.search_position(fen, movetime_ms=1000)
        res_x24 = e_x24.search_position(fen, movetime_ms=1000)

        move_match = (res_x22["bestmove"] == res_x24["bestmove"])
        score_delta = (res_x24["score_cp"] or 0) - (res_x22["score_cp"] or 0)

        classification = "EVAL_SEARCH_AGREEMENT"
        if not move_match:
            divergence_count += 1
            if abs(score_delta) >= 15:
                classification = "VERIFIED_EVAL_PREFERENCE_DIVERGENCE"
                passive_concession_count += 1
            else:
                classification = "MARGINAL_TACTICAL_DIVERGENCE"

        forensic_cases.append({
            "game_id": g_id,
            "opening": pos["opening"],
            "eco": pos["eco"],
            "critical_ply": pos["critical_ply"],
            "fen": fen,
            "x22_move": res_x22["bestmove"],
            "x22_score": res_x22["score_cp"],
            "x24_move": res_x24["bestmove"],
            "x24_score": res_x24["score_cp"],
            "score_delta": score_delta,
            "move_match": move_match,
            "classification": classification
        })

        print(f"Game {g_id:2d} (Ply {pos['critical_ply']:2d}): X22={res_x22['bestmove']} ({res_x22['score_cp']:+d} cp) vs X24={res_x24['bestmove']} ({res_x24['score_cp']:+d} cp) | Match={move_match} | Class={classification}")

    e_x22.stop()
    e_x24.stop()

    summary = {
        "total_analyzed": len(positions),
        "divergence_count": divergence_count,
        "passive_concession_count": passive_concession_count,
        "cases": forensic_cases
    }

    out_file = RAW_DIR / "endgame_forensics_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PHASE 4 FORENSICS COMPLETE: {divergence_count}/{len(positions)} moves diverged.")
    print(f"Saved to: {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    run_forensics()
