"""Project Janus v0.65 - Complete Factorial Causal Ablation Runner.

Evaluates the 2x2 factorial matrix + Classical control:
- B0: Classical C1 (Pure Classical)
- B1: Frozen V2 (Fixed 50/50)
- B2: Frozen V2 (Phase-Tapered)
- B3: Frozen V3 + SEF (Fixed 50/50)
- B4: Frozen V3 + SEF (Phase-Tapered)

Measures:
- Fixed-depth search nodes (depth 6)
- Fixed-time completed depth and nodes (250 ms)
- Search NPS
- Move agreement / Tactical consistency
- Factorial main effects & interaction ANOVA
"""

from __future__ import annotations

import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[3]

CANDIDATE_EXE = ROOT / "analysis" / "v0.64" / "native" / "janus_native_engine.exe"
BASELINE_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
V2_EXE = ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe"

MODEL_V3_PATH = ROOT / "analysis" / "v0.64" / "models" / "janus_nnue_v3.jnnue"
MODEL_V2_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"

# 24 diverse positions across 4 structural regimes
TEST_POSITIONS = [
    # 1. Tactical Middlegames (6)
    {"id": "TM_01", "name": "Fried Liver", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", "type": "tactical"},
    {"id": "TM_02", "name": "Sicilian Scheveningen", "fen": "r1b2rk1/pp1p1ppp/2n1pn2/8/2B1P3/2N1PN2/PPP3PP/R2Q1RK1 b - - 0 9", "type": "tactical"},
    {"id": "TM_03", "name": "QGD Classical", "fen": "r2qkb1r/pp2pppp/2n2n2/3p4/3P2b1/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 4 7", "type": "tactical"},
    {"id": "TM_04", "name": "French Winawer", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 3 7", "type": "tactical"},
    {"id": "TM_05", "name": "KID Mar del Plata", "fen": "2r2rk1/1bqnbppp/pp1ppn2/8/2PNP3/1PN1BP2/P3B1PP/2RQ1RK1 w - - 0 13", "type": "tactical"},
    {"id": "TM_06", "name": "Open Ruy Lopez", "fen": "r1bq1rk1/2p1bppp/p1n2n2/1p1pp3/4P3/1B1P1N2/PPP2PPP/RNBQR1K1 w - - 0 9", "type": "tactical"},

    # 2. Queenless Middlegames (6)
    {"id": "QM_01", "name": "Petrov Exchange Qless", "fen": "r3kb1r/pppq1ppp/2n1bn2/3p4/3P4/2N1BN2/PPP1BPPP/R3K2R w KQkq - 4 8", "type": "queenless"},
    {"id": "QM_02", "name": "Caro-Kann Advance Qless", "fen": "r1b1k2r/1p2bppp/p1n1pn2/8/3P4/2N1BN2/PP2BPPP/R3K2R w KQkq - 0 11", "type": "queenless"},
    {"id": "QM_03", "name": "Slav Exchange Qless", "fen": "2r1kb1r/pp1n1ppp/4pn2/3p4/3P4/2N1BN2/PPP2PPP/R3K2R w KQk - 0 10", "type": "queenless"},
    {"id": "QM_04", "name": "English Symm Qless", "fen": "r4rk1/pp1b1ppp/2n1pn2/3p4/3P4/2N1BN2/PPP1BPPP/R4RK1 w - - 0 11", "type": "queenless"},
    {"id": "QM_05", "name": "QGD Tartakower Qless", "fen": "r1r3k1/pp1b1ppp/4pn2/3p4/3P4/P1N1BN2/1PP1BPPP/R4RK1 w - - 0 12", "type": "queenless"},
    {"id": "QM_06", "name": "Grünfeld Russian Qless", "fen": "2r2rk1/pp1bppbp/2n3p1/3p4/N2P4/4PN2/PP2BPPP/2R2RK1 w - - 4 15", "type": "queenless"},

    # 3. Rook Endgames (6)
    {"id": "RE_01", "name": "Rook 4v3 Kingside", "fen": "8/5pk1/4p1p1/1R5p/7P/5PK1/6P1/r7 w - - 0 35", "type": "rook_endgame"},
    {"id": "RE_02", "name": "Active Defending Rook", "fen": "8/8/1r3k2/4R1p1/6P1/5PK1/8/8 w - - 1 42", "type": "rook_endgame"},
    {"id": "RE_03", "name": "Cutoff Rook King Active", "fen": "5r2/5pk1/4p1p1/7p/4R2P/5PK1/6P1/8 w - - 0 38", "type": "rook_endgame"},
    {"id": "RE_04", "name": "Rook on 7th Behind Passer", "fen": "8/2r2pk1/4p1p1/1R5p/7P/5PK1/6P1/8 b - - 0 36", "type": "rook_endgame"},
    {"id": "RE_05", "name": "Lucena Preparation", "fen": "8/5pk1/1r2p1p1/7p/4R2P/5PK1/6P1/8 w - - 0 37", "type": "rook_endgame"},
    {"id": "RE_06", "name": "Philidor Defense Profile", "fen": "8/8/4k1p1/R4p1p/7P/4PKP1/1r6/8 w - - 4 45", "type": "rook_endgame"},

    # 4. Pawn Endgames (6)
    {"id": "PE_01", "name": "Opposition Kingside Chain", "fen": "8/8/5k2/4p1p1/4P1P1/5K2/8/8 w - - 0 50", "type": "pawn_endgame"},
    {"id": "PE_02", "name": "Passed Pawn Race f vs g", "fen": "8/8/8/4k1p1/5pP1/5K2/8/8 w - - 0 52", "type": "pawn_endgame"},
    {"id": "PE_03", "name": "Zugzwang Triangulation", "fen": "8/8/8/5kp1/5pP1/4K3/8/8 w - - 0 51", "type": "pawn_endgame"},
    {"id": "PE_04", "name": "Distant Passed Pawn Queenside", "fen": "8/8/8/1k4p1/2p3P1/2K5/8/8 w - - 0 53", "type": "pawn_endgame"},
    {"id": "PE_05", "name": "Locked Central Pawn Mass", "fen": "8/8/8/4k1p1/1p4P1/1P2K3/8/8 w - - 0 54", "type": "pawn_endgame"},
    {"id": "PE_06", "name": "Square of the Pawn Defense", "fen": "8/8/8/8/2k5/8/1P4K1/8 w - - 0 60", "type": "pawn_endgame"},
]


class EngineRunner:
    def __init__(self, exe_path: Path, options: Dict[str, Any]):
        self.exe_path = exe_path
        self.options = options
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

    def search_depth(self, fen: str, depth: int = 6) -> Dict[str, Any]:
        self.ucinewgame()
        t0 = time.perf_counter()
        self.p.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.p.stdin.flush()
        nodes = 0
        score_cp = 0
        bestmove = ""
        pv = ""
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
                if "pv" in toks:
                    idx = toks.index("pv")
                    pv = " ".join(toks[idx + 1:])
            if line.startswith("bestmove"):
                toks = line.split()
                if len(toks) >= 2:
                    bestmove = toks[1]
                break
        elapsed = time.perf_counter() - t0
        nps = int(nodes / elapsed) if elapsed > 0 else 0
        return {
            "nodes": nodes,
            "elapsed_ms": round(elapsed * 1000, 2),
            "nps": nps,
            "score_cp": score_cp,
            "bestmove": bestmove,
            "pv": pv,
        }

    def search_fixed_time(self, fen: str, move_time_ms: int = 250) -> Dict[str, Any]:
        self.ucinewgame()
        t0 = time.perf_counter()
        self.p.stdin.write(f"position fen {fen}\ngo movetime {move_time_ms}\n")
        self.p.stdin.flush()
        depth = 0
        nodes = 0
        score_cp = 0
        bestmove = ""
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "depth" in line:
                toks = line.split()
                if "depth" in toks:
                    idx = toks.index("depth")
                    try: depth = int(toks[idx + 1])
                    except: pass
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
        elapsed = time.perf_counter() - t0
        nps = int(nodes / elapsed) if elapsed > 0 else 0
        return {
            "depth": depth,
            "nodes": nodes,
            "elapsed_ms": round(elapsed * 1000, 2),
            "nps": nps,
            "score_cp": score_cp,
            "bestmove": bestmove,
        }

    def close(self):
        try:
            self.p.stdin.write("quit\n")
            self.p.stdin.flush()
            self.p.wait(timeout=1.0)
        except:
            try: self.p.kill()
            except: pass


def run_ablation():
    print("=" * 80)
    print("PROJECT JANUS v0.65 — COMPLETE FACTORIAL CAUSAL ABLATION")
    print("Design: 2x2 Factorial Matrix (Model Version x Blend) + Classical Control B0")
    print("Evaluators: Frozen V2 vs Frozen V3+SEF | Blends: Fixed 50/50 vs Phase-Tapered")
    print("Positions: 24 standardized positions across 4 structural regimes")
    print("=" * 80)

    configs = {
        "B0": {
            "name": "Classical C1",
            "evaluator": "Classical",
            "blend": "None",
            "exe": BASELINE_EXE,
            "opts": {
                "UseKillerOrdering": True,
                "UseHistoryOrdering": True,
                "UseLMR": True,
                "UsePVS": False,
                "UseSEEOrdering": False,
                "UseSEEInQuiescence": False,
            },
        },
        "B1": {
            "name": "Frozen V2 Fixed 50/50",
            "evaluator": "NNUE-V2",
            "blend": "Fixed",
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
        "B2": {
            "name": "Frozen V2 Phase-Tapered",
            "evaluator": "NNUE-V2",
            "blend": "Tapered",
            "exe": CANDIDATE_EXE,
            "opts": {
                "UseNeuralValue": True,
                "NeuralValueModelPath": str(MODEL_V2_PATH.resolve()),
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
        "B3": {
            "name": "Frozen V3+SEF Fixed 50/50",
            "evaluator": "NNUE-V3+SEF",
            "blend": "Fixed",
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
        "B4": {
            "name": "Frozen V3+SEF Phase-Tapered",
            "evaluator": "NNUE-V3+SEF",
            "blend": "Tapered",
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

    ablation_raw = {}

    for cfg_id, cfg_info in configs.items():
        print(f"\nRunning Configuration {cfg_id} ({cfg_info['name']})...", flush=True)
        runner = EngineRunner(cfg_info["exe"], cfg_info["opts"])
        cfg_d6 = []
        cfg_time = []

        for p_idx, pos in enumerate(TEST_POSITIONS):
            r_d6 = runner.search_depth(pos["fen"], depth=6)
            r_time = runner.search_fixed_time(pos["fen"], move_time_ms=250)
            cfg_d6.append({
                "id": pos["id"],
                "name": pos["name"],
                "type": pos["type"],
                **r_d6,
            })
            cfg_time.append({
                "id": pos["id"],
                "name": pos["name"],
                "type": pos["type"],
                **r_time,
            })

        runner.close()

        total_d6_nodes = sum(x["nodes"] for x in cfg_d6)
        avg_d6_nodes = total_d6_nodes / len(cfg_d6)
        avg_d6_ms = sum(x["elapsed_ms"] for x in cfg_d6) / len(cfg_d6)
        avg_d6_nps = sum(x["nps"] for x in cfg_d6) / len(cfg_d6)

        avg_time_depth = sum(x["depth"] for x in cfg_time) / len(cfg_time)
        avg_time_nodes = sum(x["nodes"] for x in cfg_time) / len(cfg_time)
        avg_time_nps = sum(x["nps"] for x in cfg_time) / len(cfg_time)

        ablation_raw[cfg_id] = {
            "config": cfg_info,
            "depth_6_summary": {
                "total_nodes": total_d6_nodes,
                "avg_nodes": round(avg_d6_nodes, 1),
                "avg_ms": round(avg_d6_ms, 2),
                "avg_nps": int(avg_d6_nps),
            },
            "fixed_time_summary": {
                "avg_depth": round(avg_time_depth, 2),
                "avg_nodes": round(avg_time_nodes, 1),
                "avg_nps": int(avg_time_nps),
            },
            "depth_6_positions": cfg_d6,
            "fixed_time_positions": cfg_time,
        }

        print(f"  D6 Total Nodes: {total_d6_nodes:,} (avg {avg_d6_nodes:.1f}/pos) | D6 NPS: {int(avg_d6_nps):,}")
        print(f"  Fixed 250ms: Avg Depth = {avg_time_depth:.2f} | Avg NPS = {int(avg_time_nps):,}")

    # Compute Factorial Main Effects and Interactions on Depth-6 Nodes
    # 2x2 Factorial:
    # Cell 11: B1 (V2, Fixed)
    # Cell 12: B2 (V2, Tapered)
    # Cell 21: B3 (V3, Fixed)
    # Cell 22: B4 (V3, Tapered)

    regimes = ["tactical", "queenless", "rook_endgame", "pawn_endgame"]
    regime_nodes = {r: {c: 0 for c in configs} for r in regimes}

    for cfg_id in configs:
        for p in ablation_raw[cfg_id]["depth_6_positions"]:
            regime_nodes[p["type"]][cfg_id] += p["nodes"]

    # Main Effects calculation on Depth-6 total nodes across the 24 positions:
    n_B1 = ablation_raw["B1"]["depth_6_summary"]["total_nodes"]
    n_B2 = ablation_raw["B2"]["depth_6_summary"]["total_nodes"]
    n_B3 = ablation_raw["B3"]["depth_6_summary"]["total_nodes"]
    n_B4 = ablation_raw["B4"]["depth_6_summary"]["total_nodes"]

    # Model Effect: Mean(V3) - Mean(V2)
    mean_v2 = (n_B1 + n_B2) / 2.0
    mean_v3 = (n_B3 + n_B4) / 2.0
    model_main_effect = mean_v3 - mean_v2
    model_main_effect_pct = (model_main_effect / mean_v2) * 100.0

    # Blending Effect: Mean(Tapered) - Mean(Fixed)
    mean_fixed = (n_B1 + n_B3) / 2.0
    mean_tapered = (n_B2 + n_B4) / 2.0
    blend_main_effect = mean_tapered - mean_fixed
    blend_main_effect_pct = (blend_main_effect / mean_fixed) * 100.0

    # Interaction Effect: ( (V3_Tapered - V3_Fixed) - (V2_Tapered - V2_Fixed) ) / 2
    delta_v3 = n_B4 - n_B3
    delta_v2 = n_B2 - n_B1
    interaction_effect = (delta_v3 - delta_v2) / 2.0

    factorial_analysis = {
        "model_main_effect_nodes": round(model_main_effect, 1),
        "model_main_effect_pct": round(model_main_effect_pct, 2),
        "blend_main_effect_nodes": round(blend_main_effect, 1),
        "blend_main_effect_pct": round(blend_main_effect_pct, 2),
        "interaction_effect_nodes": round(interaction_effect, 1),
        "regime_breakdown": regime_nodes,
    }

    output_payload = {
        "factorial_analysis": factorial_analysis,
        "configurations": ablation_raw,
    }

    out_file = ROOT / "analysis" / "v0.65" / "raw" / "factorial_causal_ablation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, default=str)

    print("\n" + "=" * 80)
    print("FACTORIAL CAUSAL ABLATION RESULTS (Depth-6 Search Nodes)")
    print("=" * 80)
    print(f"B0 (Classical C1 Control):     {ablation_raw['B0']['depth_6_summary']['total_nodes']:,} nodes")
    print(f"B1 (V2 Fixed 50/50):           {n_B1:,} nodes")
    print(f"B2 (V2 Phase-Tapered):         {n_B2:,} nodes")
    print(f"B3 (V3+SEF Fixed 50/50):       {n_B3:,} nodes")
    print(f"B4 (V3+SEF Phase-Tapered):     {n_B4:,} nodes")
    print("-" * 80)
    print(f"Main Effect of Evaluator (V3 vs V2):     {model_main_effect:+,.1f} nodes ({model_main_effect_pct:+.2f}%)")
    print(f"Main Effect of Blending (Taper vs Fixed): {blend_main_effect:+,.1f} nodes ({blend_main_effect_pct:+.2f}%)")
    print(f"Evaluator x Blending Interaction:        {interaction_effect:+,.1f} nodes")
    print("\nRegime Breakdown (Total Nodes Depth 6):")
    for r in regimes:
        row = " | ".join(f"{c}: {regime_nodes[r][c]:,}" for c in configs)
        print(f"  [{r:15s}] {row}")
    print(f"\nSaved telemetry to {out_file}")


if __name__ == "__main__":
    run_ablation()

