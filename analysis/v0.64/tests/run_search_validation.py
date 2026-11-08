"""Project Janus v0.64 - Search Generalization and Configuration Selection Suite.

Evaluates 5 search configurations across 20 diagnostic positions spanning:
- Tactical middlegames
- Queenless middlegames
- Rook endgames
- Pawn endgames

Configurations evaluated:
- B0: Classical C1 (Native N5 Frozen Control)
- B1: Neural N1 (NNUE-V2-Small Fixed 50/50 Hybrid)
- B2: NNUE-V2 + Phase-Tapered Hybrid
- B3: NNUE-V3 + Fixed 50/50 Hybrid
- B4: NNUE-V3 + Phase-Tapered Adaptive Hybrid (Proposed Candidate)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List
import chess

ROOT = Path("E:/ChessXML/project-janus")
CANDIDATE_EXE = ROOT / "analysis" / "v0.64" / "native" / "janus_native_engine.exe"
BASELINE_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
V2_EXE = ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe"

MODEL_V3_PATH = "analysis/v0.64/models/janus_nnue_v3.jnnue"
MODEL_V2_PATH = "analysis/v0.61/models/janus_nnue_v2_small.jnnue"

import subprocess

# 20 diverse test positions: tactical, queenless, rook endgame, pawn endgame
TEST_POSITIONS = [
    # Tactical / middlegame
    {"name": "Tactical_1", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", "type": "tactical"},
    {"name": "Tactical_2", "fen": "r1b2rk1/pp1p1ppp/2n1pn2/8/2B1P3/2N1PN2/PPP3PP/R2Q1RK1 b - - 0 9", "type": "tactical"},
    {"name": "Tactical_3", "fen": "r2qkb1r/pp2pppp/2n2n2/3p4/3P2b1/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 4 7", "type": "tactical"},
    {"name": "Tactical_4", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 3 7", "type": "tactical"},
    {"name": "Tactical_5", "fen": "2r2rk1/1bqnbppp/pp1ppn2/8/2PNP3/1PN1BP2/P3B1PP/2RQ1RK1 w - - 0 13", "type": "tactical"},

    # Queenless middlegames
    {"name": "Queenless_1", "fen": "r3kb1r/pppq1ppp/2n1bn2/3p4/3P4/2N1BN2/PPP1BPPP/R3K2R w KQkq - 4 8", "type": "queenless"},
    {"name": "Queenless_2", "fen": "r1b1k2r/1p2bppp/p1n1pn2/8/3P4/2N1BN2/PP2BPPP/R3K2R w KQkq - 0 11", "type": "queenless"},
    {"name": "Queenless_3", "fen": "2r1kb1r/pp1n1ppp/4pn2/3p4/3P4/2N1BN2/PPP2PPP/R3K2R w KQk - 0 10", "type": "queenless"},
    {"name": "Queenless_4", "fen": "r4rk1/pp1b1ppp/2n1pn2/3p4/3P4/2N1BN2/PPP1BPPP/R4RK1 w - - 0 11", "type": "queenless"},
    {"name": "Queenless_5", "fen": "r1r3k1/pp1b1ppp/4pn2/3p4/3P4/P1N1BN2/1PP1BPPP/R4RK1 w - - 0 12", "type": "queenless"},

    # Rook endgames
    {"name": "RookEnd_1", "fen": "8/5pk1/4p1p1/1R5p/7P/5PK1/6P1/r7 w - - 0 35", "type": "rook_endgame"},
    {"name": "RookEnd_2", "fen": "8/8/1r3k2/4R1p1/6P1/5PK1/8/8 w - - 1 42", "type": "rook_endgame"},
    {"name": "RookEnd_3", "fen": "5r2/5pk1/4p1p1/7p/4R2P/5PK1/6P1/8 w - - 0 38", "type": "rook_endgame"},
    {"name": "RookEnd_4", "fen": "8/2r2pk1/4p1p1/1R5p/7P/5PK1/6P1/8 b - - 0 36", "type": "rook_endgame"},
    {"name": "RookEnd_5", "fen": "8/5pk1/1r2p1p1/7p/4R2P/5PK1/6P1/8 w - - 0 37", "type": "rook_endgame"},

    # Pawn endgames
    {"name": "PawnEnd_1", "fen": "8/8/5k2/4p1p1/4P1P1/5K2/8/8 w - - 0 50", "type": "pawn_endgame"},
    {"name": "PawnEnd_2", "fen": "8/8/8/4k1p1/5pP1/5K2/8/8 w - - 0 52", "type": "pawn_endgame"},
    {"name": "PawnEnd_3", "fen": "8/8/8/5kp1/5pP1/4K3/8/8 w - - 0 51", "type": "pawn_endgame"},
    {"name": "PawnEnd_4", "fen": "8/8/8/1k4p1/2p3P1/2K5/8/8 w - - 0 53", "type": "pawn_endgame"},
    {"name": "PawnEnd_5", "fen": "8/8/8/4k1p1/1p4P1/1P2K3/8/8 w - - 0 54", "type": "pawn_endgame"},
]


class NativeEngineInstance:
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

    def search_depth(self, fen: str, depth: int = 6) -> Dict[str, Any]:
        self.p.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.p.stdin.flush()
        nodes = 0
        score_cp = 0
        bestmove = ""
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
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
        return {"nodes": nodes, "score_cp": score_cp, "bestmove": bestmove}

    def close(self):
        try:
            self.p.stdin.write("quit\n")
            self.p.stdin.flush()
            self.p.wait(timeout=1.0)
        except:
            try: self.p.kill()
            except: pass


def run_validation():
    print("=" * 70)
    print("PROJECT JANUS v0.64 — PHASE 6 SEARCH GENERALIZATION VALIDATION")
    print("=" * 70)

    configs = {
        "B0_Classical_C1": {
            "exe": BASELINE_EXE,
            "opts": {"UseNeuralValue": False},
        },
        "B1_Neural_N1": {
            "exe": V2_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": MODEL_V2_PATH,
                "NeuralValueBlend": 50,
                "NeuralValueUseAVX2": True,
            },
        },
        "B2_V2_Tapered": {
            "exe": CANDIDATE_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": MODEL_V2_PATH,
                "NeuralValueBlend": 50,
                "NeuralValueAdaptiveBlend": True,
                "NeuralValueUseAVX2": True,
            },
        },
        "B3_V3_Fixed": {
            "exe": CANDIDATE_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": MODEL_V3_PATH,
                "NeuralValueBlend": 50,
                "NeuralValueAdaptiveBlend": False,
                "NeuralValueUseAVX2": True,
            },
        },
        "B4_V3_Adaptive": {
            "exe": CANDIDATE_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": MODEL_V3_PATH,
                "NeuralValueBlend": 50,
                "NeuralValueAdaptiveBlend": True,
                "NeuralValueUseAVX2": True,
            },
        },
    }

    results = {}

    for cfg_id, cfg_data in configs.items():
        print(f"\nEvaluating configuration {cfg_id}...")
        eng = NativeEngineInstance(cfg_data["exe"], cfg_data["opts"])
        cfg_results = []
        t0 = time.time()
        for pos in TEST_POSITIONS:
            res = eng.search_depth(pos["fen"], depth=6)
            cfg_results.append({
                "pos_name": pos["name"],
                "type": pos["type"],
                "nodes": res["nodes"],
                "score_cp": res["score_cp"],
                "bestmove": res["bestmove"],
            })
        eng.close()
        el = time.time() - t0
        total_nodes = sum(r["nodes"] for r in cfg_results)
        avg_nodes = total_nodes / len(TEST_POSITIONS)
        results[cfg_id] = {
            "total_nodes": total_nodes,
            "avg_nodes": avg_nodes,
            "elapsed_s": round(el, 3),
            "positions": cfg_results,
        }
        print(f"  {cfg_id}: Total Nodes = {total_nodes:,} | Avg Nodes/Pos = {avg_nodes:.1f} | Elapsed = {el:.3f}s")

    # Group by category
    categories = ["tactical", "queenless", "rook_endgame", "pawn_endgame"]
    cat_summary = {}
    for cat in categories:
        cat_summary[cat] = {}
        for cfg_id in configs:
            cat_nodes = sum(r["nodes"] for r in results[cfg_id]["positions"] if r["type"] == cat)
            cat_summary[cat][cfg_id] = cat_nodes

    print("\nSearch Nodes by Position Type (Depth 6):")
    for cat, data in cat_summary.items():
        print(f"  [{cat:15s}] " + " | ".join(f"{k}: {v:,}" for k, v in data.items()))

    # Write deliverable raw results
    out_file = ROOT / "analysis" / "v0.64" / "raw" / "search_validation_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summary": results, "categories": cat_summary}, f, indent=2)

    print(f"\nSaved search validation results -> {out_file.name}")


if __name__ == "__main__":
    run_validation()

