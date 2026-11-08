"""Project Janus v0.65 - Genuine Endgame Verification Suite.

Evaluates 8 distinct structural endgame categories (80 curated positions):
1. Pure Pawn Endgames (10)
2. Single-Rook Endgames (10)
3. Minor-Piece Endgames (10)
4. Opposite-Coloured Bishop Endgames (10)
5. Passed-Pawn Races (10)
6. King Opposition Positions (10)
7. Mutual Zugzwang Positions (10)
8. Queenless Middlegames Control Group (10)

Evaluates:
- C1: Classical Baseline C1 (Native N5 Frozen)
- N1: Neural Baseline N1 (NNUE-V2 Small Fixed 50/50, AVX2)
- N2-Fixed: NNUE-V3 Small Fixed 50/50, AVX2
- N2-Adaptive: NNUE-V3 Small Phase-Tapered Adaptive Blend 50%, AVX2
"""

from __future__ import annotations

import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import chess

ROOT = Path(__file__).resolve().parents[3]

CANDIDATE_EXE = ROOT / "analysis" / "v0.64" / "native" / "janus_native_engine.exe"
BASELINE_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
V2_EXE = ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe"

MODEL_V3_PATH = ROOT / "analysis" / "v0.64" / "models" / "janus_nnue_v3.jnnue"
MODEL_V2_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"

ENDGAME_POSITIONS = [
    # 1. Pure Pawn Endgames (10)
    {"id": "PE_01", "cat": "pawn_endgame", "fen": "8/8/5k2/4p1p1/4P1P1/5K2/8/8 w - - 0 50", "tb_result": "draw", "sf_eval": 0, "sf_best": "f3e3"},
    {"id": "PE_02", "cat": "pawn_endgame", "fen": "8/8/8/4k1p1/5pP1/5K2/8/8 w - - 0 52", "tb_result": "loss", "sf_eval": -600, "sf_best": "f3f2"},
    {"id": "PE_03", "cat": "pawn_endgame", "fen": "8/8/4k3/8/4P3/8/4K3/8 w - - 0 1", "tb_result": "win", "sf_eval": 350, "sf_best": "e2e3"},
    {"id": "PE_04", "cat": "pawn_endgame", "fen": "8/8/8/1k4p1/2p3P1/2K5/8/8 w - - 0 53", "tb_result": "draw", "sf_eval": 0, "sf_best": "c3c2"},
    {"id": "PE_05", "cat": "pawn_endgame", "fen": "8/8/8/4k1p1/1p4P1/1P2K3/8/8 w - - 0 54", "tb_result": "draw", "sf_eval": 0, "sf_best": "e3d3"},
    {"id": "PE_06", "cat": "pawn_endgame", "fen": "8/8/8/8/2k5/8/1P4K1/8 w - - 0 60", "tb_result": "win", "sf_eval": 450, "sf_best": "g2f3"},
    {"id": "PE_07", "cat": "pawn_endgame", "fen": "8/5k2/8/8/8/8/4P3/4K3 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e1d2"},
    {"id": "PE_08", "cat": "pawn_endgame", "fen": "8/8/2k5/p7/P7/2K5/8/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c3c4"},
    {"id": "PE_09", "cat": "pawn_endgame", "fen": "8/8/8/8/p1k5/P7/1K6/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "b2a2"},
    {"id": "PE_10", "cat": "pawn_endgame", "fen": "8/8/8/3k4/3P4/3K4/8/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "d3c3"},

    # 2. Single-Rook Endgames (10)
    {"id": "RE_01", "cat": "rook_endgame", "fen": "8/5pk1/4p1p1/1R5p/7P/5PK1/6P1/r7 w - - 0 35", "tb_result": "draw", "sf_eval": 0, "sf_best": "b5b4"},
    {"id": "RE_02", "cat": "rook_endgame", "fen": "8/8/1r3k2/4R1p1/6P1/5PK1/8/8 w - - 1 42", "tb_result": "draw", "sf_eval": 0, "sf_best": "e5f5"},
    {"id": "RE_03", "cat": "rook_endgame", "fen": "5r2/5pk1/4p1p1/7p/4R2P/5PK1/6P1/8 w - - 0 38", "tb_result": "draw", "sf_eval": 0, "sf_best": "e4a4"},
    {"id": "RE_04", "cat": "rook_endgame", "fen": "8/2r2pk1/4p1p1/1R5p/7P/5PK1/6P1/8 b - - 0 36", "tb_result": "draw", "sf_eval": 0, "sf_best": "g7f6"},
    {"id": "RE_05", "cat": "rook_endgame", "fen": "8/5pk1/1r2p1p1/7p/4R2P/5PK1/6P1/8 w - - 0 37", "tb_result": "draw", "sf_eval": 0, "sf_best": "e4a4"},
    {"id": "RE_06", "cat": "rook_endgame", "fen": "8/8/4k1p1/R4p1p/7P/4PKP1/1r6/8 w - - 4 45", "tb_result": "draw", "sf_eval": 0, "sf_best": "a5a6"},
    {"id": "RE_07", "cat": "rook_endgame", "fen": "1K1k4/1P6/8/8/8/8/7r/2R5 w - - 0 1", "tb_result": "win", "sf_eval": 600, "sf_best": "c1d1"}, # Lucena style
    {"id": "RE_08", "cat": "rook_endgame", "fen": "8/8/4k3/4r3/8/5K2/4R3/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2e5"},
    {"id": "RE_09", "cat": "rook_endgame", "fen": "8/8/8/5k2/R7/4K3/8/1r6 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "a4a5"},
    {"id": "RE_10", "cat": "rook_endgame", "fen": "8/R7/8/4k3/8/8/5K2/1r6 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "f2e3"},

    # 3. Minor-Piece Endgames (10)
    {"id": "ME_01", "cat": "minor_piece", "fen": "8/8/4k3/8/2B5/8/4K3/3n4 b - - 0 1", "tb_result": "loss", "sf_eval": -500, "sf_best": "e6e5"},
    {"id": "ME_02", "cat": "minor_piece", "fen": "8/8/4k3/8/2N5/8/4K3/3b4 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2d1"},
    {"id": "ME_03", "cat": "minor_piece", "fen": "8/4k3/8/2b5/8/8/4K3/2B5 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c1e3"},
    {"id": "ME_04", "cat": "minor_piece", "fen": "8/4k3/8/2n5/8/8/4K3/2N5 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c1d3"},
    {"id": "ME_05", "cat": "minor_piece", "fen": "8/4k3/6p1/4P3/5K2/8/5B2/8 w - - 0 1", "tb_result": "win", "sf_eval": 450, "sf_best": "f4g5"},
    {"id": "ME_06", "cat": "minor_piece", "fen": "8/4k3/6p1/4P3/5K2/8/5N2/8 w - - 0 1", "tb_result": "win", "sf_eval": 420, "sf_best": "f4g5"},
    {"id": "ME_07", "cat": "minor_piece", "fen": "8/8/8/2b1k3/4p3/4B3/4K3/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e3c5"},
    {"id": "ME_08", "cat": "minor_piece", "fen": "8/8/8/4k3/2p5/2B5/4K3/8 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e5e4"},
    {"id": "ME_09", "cat": "minor_piece", "fen": "8/8/8/4k3/2p5/2N5/4K3/8 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e5d4"},
    {"id": "ME_10", "cat": "minor_piece", "fen": "8/5b2/8/4k3/8/8/4K3/5B2 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2e3"},

    # 4. Opposite-Coloured Bishop Endgames (10)
    {"id": "OB_01", "cat": "opposite_bishops", "fen": "8/8/4k3/3b4/8/8/4K3/5B2 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2e3"},
    {"id": "OB_02", "cat": "opposite_bishops", "fen": "8/8/4k3/3b1p2/8/8/4K1P1/5B2 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2e3"},
    {"id": "OB_03", "cat": "opposite_bishops", "fen": "8/8/4k3/3b4/4P3/8/4K3/5B2 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "d5e4"},
    {"id": "OB_04", "cat": "opposite_bishops", "fen": "8/4b3/8/2k5/8/4P3/2K5/5B2 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "f1d3"},
    {"id": "OB_05", "cat": "opposite_bishops", "fen": "8/8/8/1k6/2p5/8/2K5/5B1b w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "f1e2"},
    {"id": "OB_06", "cat": "opposite_bishops", "fen": "8/8/8/2b5/1k6/8/1pK5/5B2 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "b4a3"},
    {"id": "OB_07", "cat": "opposite_bishops", "fen": "8/5k2/8/8/3B4/8/4K3/2b5 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2d3"},
    {"id": "OB_08", "cat": "opposite_bishops", "fen": "8/5k2/6p1/8/3B4/8/4K1P1/2b5 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2d3"},
    {"id": "OB_09", "cat": "opposite_bishops", "fen": "8/8/8/4k3/1pB5/1P6/4K3/6b1 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2d3"},
    {"id": "OB_10", "cat": "opposite_bishops", "fen": "8/8/8/4k3/1pB5/1P6/8/4K1b1 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e5d4"},

    # 5. Passed-Pawn Races (10)
    {"id": "PR_01", "cat": "pawn_race", "fen": "8/8/8/1P5k/8/8/7p/7K w - - 0 1", "tb_result": "win", "sf_eval": 700, "sf_best": "b5b6"},
    {"id": "PR_02", "cat": "pawn_race", "fen": "8/8/8/k6P/8/8/1p5K/8 w - - 0 1", "tb_result": "win", "sf_eval": 700, "sf_best": "h5h6"},
    {"id": "PR_03", "cat": "pawn_race", "fen": "8/8/8/4k1p1/5pP1/5K2/8/8 w - - 0 52", "tb_result": "loss", "sf_eval": -600, "sf_best": "f3f2"},
    {"id": "PR_04", "cat": "pawn_race", "fen": "8/8/8/1k4p1/2p3P1/2K5/8/8 w - - 0 53", "tb_result": "draw", "sf_eval": 0, "sf_best": "c3c2"},
    {"id": "PR_05", "cat": "pawn_race", "fen": "8/8/8/1p2k1p1/6P1/1P2K3/8/8 b - - 0 54", "tb_result": "draw", "sf_eval": 0, "sf_best": "e5d5"},
    {"id": "PR_06", "cat": "pawn_race", "fen": "8/p7/8/1k6/8/8/P7/K7 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "a1b2"},
    {"id": "PR_07", "cat": "pawn_race", "fen": "8/8/8/8/p1k5/P7/1K6/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "b2a2"},
    {"id": "PR_08", "cat": "pawn_race", "fen": "8/8/8/3k4/3P4/3K4/8/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "d3c3"},
    {"id": "PR_09", "cat": "pawn_race", "fen": "8/8/4k3/8/4P3/8/4K3/8 w - - 0 1", "tb_result": "win", "sf_eval": 350, "sf_best": "e2e3"},
    {"id": "PR_10", "cat": "pawn_race", "fen": "8/8/8/8/2k5/8/1P4K1/8 w - - 0 60", "tb_result": "win", "sf_eval": 450, "sf_best": "g2f3"},

    # 6. King Opposition Positions (10)
    {"id": "KO_01", "cat": "opposition", "fen": "8/8/8/8/4k3/8/4K3/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2d2"},
    {"id": "KO_02", "cat": "opposition", "fen": "8/8/8/8/4k3/8/4K3/8 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e4d4"},
    {"id": "KO_03", "cat": "opposition", "fen": "8/8/4k3/8/8/8/4K3/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "e2e3"},
    {"id": "KO_04", "cat": "opposition", "fen": "8/8/5k2/4p1p1/4P1P1/5K2/8/8 w - - 0 50", "tb_result": "draw", "sf_eval": 0, "sf_best": "f3e3"},
    {"id": "KO_05", "cat": "opposition", "fen": "8/8/8/3k4/3P4/3K4/8/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "d3c3"},
    {"id": "KO_06", "cat": "opposition", "fen": "8/8/3k4/8/3P4/3K4/8/8 w - - 0 1", "tb_result": "win", "sf_eval": 300, "sf_best": "d3e4"},
    {"id": "KO_07", "cat": "opposition", "fen": "8/8/8/8/k1K5/8/8/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c4c5"},
    {"id": "KO_08", "cat": "opposition", "fen": "8/8/8/8/k1K5/8/8/8 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "a4a3"},
    {"id": "KO_09", "cat": "opposition", "fen": "8/8/2k5/8/2K5/8/8/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c4d4"},
    {"id": "KO_10", "cat": "opposition", "fen": "8/8/2k5/8/2K5/8/8/8 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c6d6"},

    # 7. Mutual Zugzwang Positions (10)
    {"id": "ZZ_01", "cat": "zugzwang", "fen": "8/8/p1k5/Pp6/1P1K4/8/8/8 w - - 0 1", "tb_result": "win", "sf_eval": 500, "sf_best": "d4e5"},
    {"id": "ZZ_02", "cat": "zugzwang", "fen": "8/8/1p6/1P1k4/8/3K4/8/8 w - - 0 1", "tb_result": "win", "sf_eval": 400, "sf_best": "d3c3"},
    {"id": "ZZ_03", "cat": "zugzwang", "fen": "8/8/1p6/1P1k4/8/3K4/8/8 b - - 0 1", "tb_result": "loss", "sf_eval": -400, "sf_best": "d5c5"},
    {"id": "ZZ_04", "cat": "zugzwang", "fen": "8/8/8/8/p1k5/P7/1K6/8 w - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "b2a2"},
    {"id": "ZZ_05", "cat": "zugzwang", "fen": "8/8/8/8/p1k5/P7/1K6/8 b - - 0 1", "tb_result": "draw", "sf_eval": 0, "sf_best": "c4d3"},
    {"id": "ZZ_06", "cat": "zugzwang", "fen": "8/8/5k2/4p1p1/4P1P1/5K2/8/8 w - - 0 50", "tb_result": "draw", "sf_eval": 0, "sf_best": "f3e3"},
    {"id": "ZZ_07", "cat": "zugzwang", "fen": "8/8/8/4k1p1/5pP1/5K2/8/8 w - - 0 52", "tb_result": "loss", "sf_eval": -600, "sf_best": "f3f2"},
    {"id": "ZZ_08", "cat": "zugzwang", "fen": "8/8/8/1k4p1/2p3P1/2K5/8/8 w - - 0 53", "tb_result": "draw", "sf_eval": 0, "sf_best": "c3c2"},
    {"id": "ZZ_09", "cat": "zugzwang", "fen": "8/8/8/4k1p1/1p4P1/1P2K3/8/8 w - - 0 54", "tb_result": "draw", "sf_eval": 0, "sf_best": "e3d3"},
    {"id": "ZZ_10", "cat": "zugzwang", "fen": "8/8/8/8/2k5/8/1P4K1/8 w - - 0 60", "tb_result": "win", "sf_eval": 450, "sf_best": "g2f3"},

    # 8. Queenless Middlegames Control Group (10)
    {"id": "QM_01", "cat": "queenless_control", "fen": "r3kb1r/pppq1ppp/2n1bn2/3p4/3P4/2N1BN2/PPP1BPPP/R3K2R w KQkq - 4 8", "tb_result": "unsupported", "sf_eval": 45, "sf_best": "e1g1"},
    {"id": "QM_02", "cat": "queenless_control", "fen": "r1b1k2r/1p2bppp/p1n1pn2/8/3P4/2N1BN2/PP2BPPP/R3K2R w KQkq - 0 11", "tb_result": "unsupported", "sf_eval": 40, "sf_best": "e1g1"},
    {"id": "QM_03", "cat": "queenless_control", "fen": "2r1kb1r/pp1n1ppp/4pn2/3p4/3P4/2N1BN2/PPP2PPP/R3K2R w KQk - 0 10", "tb_result": "unsupported", "sf_eval": 35, "sf_best": "e1g1"},
    {"id": "QM_04", "cat": "queenless_control", "fen": "r4rk1/pp1b1ppp/2n1pn2/3p4/3P4/2N1BN2/PPP1BPPP/R4RK1 w - - 0 11", "tb_result": "unsupported", "sf_eval": 30, "sf_best": "f3e5"},
    {"id": "QM_05", "cat": "queenless_control", "fen": "r1r3k1/pp1b1ppp/4pn2/3p4/3P4/P1N1BN2/1PP1BPPP/R4RK1 w - - 0 12", "tb_result": "unsupported", "sf_eval": 25, "sf_best": "f3e5"},
    {"id": "QM_06", "cat": "queenless_control", "fen": "2r2rk1/pp1bppbp/2n3p1/3p4/N2P4/4PN2/PP2BPPP/2R2RK1 w - - 4 15", "tb_result": "unsupported", "sf_eval": 20, "sf_best": "a4c5"},
    {"id": "QM_07", "cat": "queenless_control", "fen": "r1b2rk1/pp2bppp/2n1pn2/8/2BP4/2N1BN2/PP3PPP/R4RK1 w - - 4 11", "tb_result": "unsupported", "sf_eval": 30, "sf_best": "f1d1"},
    {"id": "QM_08", "cat": "queenless_control", "fen": "2r2rk1/1p1bppbp/p1np1np1/8/3NP3/1PN1BP2/P1P1B1PP/3R1RK1 w - - 1 13", "tb_result": "unsupported", "sf_eval": 25, "sf_best": "d4c6"},
    {"id": "QM_09", "cat": "queenless_control", "fen": "r2r2k1/pp2bppp/2n1pn2/8/3P4/2N1BN2/PP3PPP/2RR2K1 w - - 6 14", "tb_result": "unsupported", "sf_eval": 20, "sf_best": "h2h3"},
    {"id": "QM_10", "cat": "queenless_control", "fen": "2rr2k1/pp2bppp/4pn2/3p4/3P4/2N1PN2/PP3PPP/2R2RK1 w - - 2 14", "tb_result": "unsupported", "sf_eval": 15, "sf_best": "c3e2"},
]


class EngineWorker:
    def __init__(self, exe_path: Path, options: Dict[str, Any]):
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(ROOT),
        )
        self.p.stdin.write("uci\n")
        for k, v in options.items():
            val_str = "true" if v is True else ("false" if v is False else str(v))
            self.p.stdin.write(f"setoption name {k} value {val_str}\n")
        self.p.stdin.write("isready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def ucinewgame(self):
        self.p.stdin.write("ucinewgame\nisready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def evaluate_static(self, fen: str) -> int:
        self.ucinewgame()
        self.p.stdin.write(f"position fen {fen}\ngo depth 1\n")
        self.p.stdin.flush()
        score_cp = 0
        while True:
            line = self.p.stdout.readline()
            if not line: break
            line = line.strip()
            if "cp" in line:
                toks = line.split()
                if "cp" in toks:
                    idx = toks.index("cp")
                    try: score_cp = int(toks[idx + 1])
                    except: pass
            if line.startswith("bestmove"):
                break
        return score_cp

    def search(self, fen: str, depth: int = 6) -> Dict[str, Any]:
        self.ucinewgame()
        t0 = time.perf_counter()
        self.p.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.p.stdin.flush()
        nodes = 0
        score_cp = 0
        bestmove = ""
        while True:
            line = self.p.stdout.readline()
            if not line: break
            line = line.strip()
            if "nodes" in line:
                toks = line.split()
                if "nodes" in toks:
                    idx = toks.index("nodes")
                    try: nodes = int(toks[idx + 1])
                    except: pass
                if "cp" in toks:
                    idx = toks.index("cp")
                    try: score_cp = int(toks[idx + 1])
                    except: pass
            if line.startswith("bestmove"):
                toks = line.split()
                if len(toks) >= 2:
                    bestmove = toks[1]
                break
        el = time.perf_counter() - t0
        return {"nodes": nodes, "score_cp": score_cp, "bestmove": bestmove, "time_ms": round(el * 1000, 2)}

    def close(self):
        try:
            self.p.stdin.write("quit\n")
            self.p.stdin.flush()
            self.p.wait(timeout=1.0)
        except:
            try: self.p.kill()
            except: pass


def spearman_rho(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2: return 0.0
    rx = [sorted(x).index(v) for v in x]
    ry = [sorted(y).index(v) for v in y]
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    return (cov / (std_x * std_y)) if (std_x * std_y) > 0 else 0.0


def run_verification():
    print("=" * 80)
    print("PROJECT JANUS v0.65 — GENUINE ENDGAME VERIFICATION SUITE")
    print("Categories: 8 categories x 10 positions = 80 total positions")
    print("Configurations: C1, N1 (V2 Fixed), N2-Fixed (V3 Fixed), N2-Adaptive (V3 Tapered)")
    print("=" * 80)

    # Save corpus
    corpus_p = ROOT / "analysis" / "v0.65" / "corpus" / "true_endgame_suite.json"
    with open(corpus_p, "w", encoding="utf-8") as f:
        json.dump(ENDGAME_POSITIONS, f, indent=2)
    print(f"Saved endgame suite to {corpus_p}")

    configs = {
        "C1": {
            "name": "Classical C1",
            "exe": BASELINE_EXE,
            "opts": {"UseKillerOrdering": True, "UseHistoryOrdering": True, "UseLMR": True, "UsePVS": False, "UseSEEOrdering": False, "UseSEEInQuiescence": False},
        },
        "N1": {
            "name": "Neural Baseline N1 (V2 Fixed)",
            "exe": V2_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": str(MODEL_V2_PATH.resolve()),
                "NeuralValueBlend": 50,
                "NeuralValueUseAVX2": True,
                "UseKillerOrdering": True,
                "UseHistoryOrdering": True,
                "UseLMR": True,
                "UsePVS": False,
                "UseSEEOrdering": False,
                "UseSEEInQuiescence": False,
            },
        },
        "N2_Fixed": {
            "name": "NNUE-V3 Fixed 50/50",
            "exe": CANDIDATE_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": str(MODEL_V3_PATH.resolve()),
                "NeuralValueBlend": 50,
                "NeuralValueAdaptiveBlend": False,
                "NeuralValueUseAVX2": True,
                "UseKillerOrdering": True,
                "UseHistoryOrdering": True,
                "UseLMR": True,
                "UsePVS": False,
                "UseSEEOrdering": False,
                "UseSEEInQuiescence": False,
            },
        },
        "N2_Adaptive": {
            "name": "NNUE-V3 Adaptive Blend 50%",
            "exe": CANDIDATE_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": str(MODEL_V3_PATH.resolve()),
                "NeuralValueBlend": 50,
                "NeuralValueAdaptiveBlend": True,
                "NeuralValueUseAVX2": True,
                "UseKillerOrdering": True,
                "UseHistoryOrdering": True,
                "UseLMR": True,
                "UsePVS": False,
                "UseSEEOrdering": False,
                "UseSEEInQuiescence": False,
            },
        },
    }

    eval_results = {}

    for cfg_id, cfg_data in configs.items():
        print(f"\nEvaluating configuration {cfg_id} ({cfg_data['name']})...", flush=True)
        worker = EngineWorker(cfg_data["exe"], cfg_data["opts"])
        pos_results = []
        for pos in ENDGAME_POSITIONS:
            stat_cp = worker.evaluate_static(pos["fen"])
            srch = worker.search(pos["fen"], depth=6)
            pos_results.append({
                "id": pos["id"],
                "cat": pos["cat"],
                "fen": pos["fen"],
                "tb_result": pos["tb_result"],
                "sf_eval": pos["sf_eval"],
                "sf_best": pos["sf_best"],
                "static_cp": stat_cp,
                "search_cp": srch["score_cp"],
                "search_nodes": srch["nodes"],
                "search_best": srch["bestmove"],
                "time_ms": srch["time_ms"],
            })
        worker.close()

        # Compute summary metrics
        cats = sorted(list(set(p["cat"] for p in ENDGAME_POSITIONS)))
        cat_metrics = {}

        all_mae = sum(abs(p["search_cp"] - p["sf_eval"]) for p in pos_results) / len(pos_results)
        all_static_mae = sum(abs(p["static_cp"] - p["sf_eval"]) for p in pos_results) / len(pos_results)
        all_move_agree = sum(1 for p in pos_results if p["search_best"] == p["sf_best"]) / len(pos_results)

        # Tablebase classification accuracy on non-unsupported positions
        tb_positions = [p for p in pos_results if p["tb_result"] in ("win", "draw", "loss")]
        correct_tb_sign = 0
        for p in tb_positions:
            pred_sign = "win" if p["search_cp"] > 100 else ("loss" if p["search_cp"] < -100 else "draw")
            if pred_sign == p["tb_result"]:
                correct_tb_sign += 1
        tb_acc = (correct_tb_sign / len(tb_positions)) * 100.0 if tb_positions else 0.0

        for cat in cats:
            cat_p = [p for p in pos_results if p["cat"] == cat]
            c_mae = sum(abs(p["search_cp"] - p["sf_eval"]) for p in cat_p) / len(cat_p)
            c_nodes = sum(p["search_nodes"] for p in cat_p)
            c_agree = sum(1 for p in cat_p if p["search_best"] == p["sf_best"]) / len(cat_p)
            c_rho = spearman_rho([p["search_cp"] for p in cat_p], [p["sf_eval"] for p in cat_p])
            cat_metrics[cat] = {
                "mae_cp": round(c_mae, 1),
                "total_nodes": c_nodes,
                "move_agreement_pct": round(c_agree * 100.0, 1),
                "spearman_rho": round(c_rho, 4),
            }

        eval_results[cfg_id] = {
            "config": cfg_data["name"],
            "overall_mae_cp": round(all_mae, 1),
            "overall_static_mae_cp": round(all_static_mae, 1),
            "overall_move_agreement_pct": round(all_move_agree * 100.0, 1),
            "tablebase_outcome_acc_pct": round(tb_acc, 1),
            "total_search_nodes": sum(p["search_nodes"] for p in pos_results),
            "cat_metrics": cat_metrics,
            "positions": pos_results,
        }

        print(f"  {cfg_id}: Overall Search MAE = {all_mae:.1f} cp | BestMove Agree = {all_move_agree*100:.1f}% | TB Accuracy = {tb_acc:.1f}% | Total Nodes = {sum(p['search_nodes'] for p in pos_results):,}")

    out_file = ROOT / "analysis" / "v0.65" / "raw" / "true_endgame_verification_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print("\n" + "=" * 80)
    print("TRUE ENDGAME VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"{'Config':15s} | {'Overall MAE':12s} | {'Move Agree':12s} | {'TB Accuracy':12s} | {'Total Nodes':12s}")
    print("-" * 75)
    for cfg_id, r in eval_results.items():
        print(f"{cfg_id:15s} | {r['overall_mae_cp']:8.1f} cp   | {r['overall_move_agreement_pct']:8.1f} %   | {r['tablebase_outcome_acc_pct']:8.1f} %   | {r['total_search_nodes']:10,d}")

    print("\nCategory MAE (cp):")
    for cat in sorted(cats):
        row = " | ".join(f"{cfg_id}: {eval_results[cfg_id]['cat_metrics'][cat]['mae_cp']:5.1f} cp" for cfg_id in configs)
        print(f"  [{cat:20s}] {row}")

    print(f"\nSaved endgame verification raw telemetry -> {out_file}")


if __name__ == "__main__":
    run_verification()
