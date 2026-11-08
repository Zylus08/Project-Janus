#!/usr/bin/env python3
"""Project Janus v0.62 - Causal Strength Attribution & Search Interaction Study.

Decomposes the source of playing-strength advantage across:
- A0: Classical Baseline C1 (Native N5 handcrafted evaluation)
- A1: Pure NNUE-V2-Small with AVX2 (Blend=100)
- A2: Hybrid NNUE-V2-Small 50/50 with AVX2 (Blend=50) [The Promoted Candidate]
- A3: Hybrid NNUE-V2-Small 50/50 with Scalar C++17 (Blend=50, Scalar)
- A4: Pure NNUE-V2-Small with Scalar C++17 (Blend=100, Scalar)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Any
import chess
import chess.engine

ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR_V61 = ROOT / "analysis" / "v0.61" / "native"
MODEL_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"
STOCKFISH_PATH = Path(r"E:\ChessXML\tools\stockfish\stockfish.exe")
RAW_DIR = ROOT / "analysis" / "v0.62" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(NATIVE_DIR_V61))
from janus_native_bridge import NativeEngineBridge

DEV_POSITIONS = [
    {"id": "DEV_01_STARTPOS", "desc": "Starting position", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "DEV_02_ITALIAN", "desc": "Italian Game Giuoco Piano", "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5"},
    {"id": "DEV_03_SICILIAN", "desc": "Sicilian Najdorf 6.Be3", "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6"},
    {"id": "DEV_04_FRENCH", "desc": "French Winawer 5.Bd3", "fen": "r1bqk1nr/pp3ppp/2n1p3/2bpP3/8/2PB1N2/PP1P1PPP/RNBQK2R w KQkq - 0 6"},
    {"id": "DEV_05_QGD", "desc": "QGD Tartakower", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 b - - 4 8"},
    {"id": "DEV_06_TACTICAL_PIN", "desc": "Sharp tactical pin / fork", "fen": "r1b2rk1/1pq1bppp/p1np4/4p3/2B1P3/1NN1B3/PPP2PPP/R2Q1RK1 w - - 0 11"},
    {"id": "DEV_07_ROOK_ENDGAME", "desc": "Rook + pawn technical endgame", "fen": "8/8/8/4k3/8/8/4K1P1/7r w - - 0 1"},
    {"id": "DEV_08_OPP_BISHOPS", "desc": "Opposite colored bishops", "fen": "8/2b5/8/4k3/8/5B2/4K3/8 w - - 0 1"},
    {"id": "DEV_09_CLOSED_MANOEUVRE", "desc": "Closed strategic maneuvering", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2BPP1b1/2P1BN2/PP1N1PPP/R2Q1RK1 b - - 1 9"},
    {"id": "DEV_10_ASYMMETRIC", "desc": "Dynamic pawn structure imbalance", "fen": "r1bqr1k1/pp3pbp/2p3p1/8/3PB3/1P4P1/PB2PP1P/R2Q1RK1 w - - 1 15"},
    {"id": "DEV_11_TACTIC_DEFLECTION", "desc": "Tactical deflection sacrifice", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8"},
    {"id": "DEV_12_QUEENLESS_MIDGAME", "desc": "Queenless middlegame imbalance", "fen": "r4rk1/1p2bppp/p1n1p3/3p4/3P4/2N1PB2/PP3PPP/R4RK1 w - - 0 15"},
]


def run_causal_attribution():
    print("=" * 80)
    print("PROJECT JANUS v0.62 — CAUSAL STRENGTH ATTRIBUTION STUDY")
    print("=" * 80)

    # Reference Stockfish
    sf_engine = None
    if STOCKFISH_PATH.exists():
        sf_engine = chess.engine.SimpleEngine.popen_uci(str(STOCKFISH_PATH))
        print("Teacher Engine: Stockfish 19 loaded for ground-truth move validation.")

    engine = NativeEngineBridge()

    configs = {
        "A0_Classical_C1": {"neural": False, "blend": 0, "avx2": False, "desc": "Classical C1 Frozen Baseline"},
        "A1_Pure_NNUE_AVX2": {"neural": True, "blend": 100, "avx2": True, "desc": "Pure NNUE-V2 AVX2 (100% Neural)"},
        "A2_Hybrid_AVX2": {"neural": True, "blend": 50, "avx2": True, "desc": "Hybrid NNUE-V2 AVX2 (50% Neural + 50% Classical)"},
        "A3_Hybrid_Scalar": {"neural": True, "blend": 50, "avx2": False, "desc": "Hybrid NNUE-V2 Scalar C++17 (50/50 Blend, Scalar)"},
        "A4_Pure_NNUE_Scalar": {"neural": True, "blend": 100, "avx2": False, "desc": "Pure NNUE-V2 Scalar C++17 (100% Neural, Scalar)"},
    }

    results: Dict[str, Any] = {
        "fixed_depth_5": {},
        "fixed_time_500ms": {},
        "causal_decomposition": {},
    }

    # 1. Fixed-Depth Search (Depth = 5)
    print("\n[1] Running Fixed-Depth Search Evaluation (Depth 5 across 12 positions)...")
    for cfg_key, cfg in configs.items():
        print(f"  Testing {cfg_key} ({cfg['desc']})...")
        pos_results = []
        tot_nodes = 0
        tot_time = 0.0

        for pos in DEV_POSITIONS:
            fen = pos["fen"]
            engine.clear_tt()
            engine.clear_killers()
            engine.clear_history_heuristic()
            engine.set_ordering_options(True, True)
            engine.set_pvs_options(False)
            engine.set_lmr_options(True, 3, 4, 1)
            engine.set_see_options(False, False)

            engine.set_neural_value_options(
                enabled=cfg["neural"],
                model_path=str(MODEL_PATH),
                blend=cfg["blend"],
                use_avx2=cfg["avx2"],
            )

            engine.set_fen(fen)
            bm, sc, d, nodes, elapsed, pv = engine.search(max_depth=5, time_limit=10.0)
            tot_nodes += nodes
            tot_time += elapsed

            # Teacher move
            sf_bm = ""
            if sf_engine:
                b_sf = chess.Board(fen)
                sf_res = sf_engine.play(b_sf, chess.engine.Limit(nodes=25000))
                sf_bm = sf_res.move.uci() if sf_res.move else ""

            pos_results.append({
                "id": pos["id"],
                "best_move": bm,
                "score_cp": sc,
                "nodes": nodes,
                "elapsed_s": round(elapsed, 4),
                "nps": round(nodes / elapsed) if elapsed > 0 else 0,
                "sf_move": sf_bm,
            })

        results["fixed_depth_5"][cfg_key] = {
            "total_nodes": tot_nodes,
            "total_time_s": round(tot_time, 4),
            "aggregate_nps": round(tot_nodes / tot_time) if tot_time > 0 else 0,
            "positions": pos_results,
        }
        print(f"    Nodes: {tot_nodes:,} | Time: {tot_time:.3f}s | NPS: {round(tot_nodes / tot_time):,}")

    # 2. Fixed-Time Search (500 ms per position)
    print("\n[2] Running Fixed-Time Search Evaluation (500ms per position across 12 positions)...")
    for cfg_key, cfg in configs.items():
        print(f"  Testing {cfg_key} ({cfg['desc']})...")
        pos_results = []
        tot_nodes = 0
        tot_depth = 0.0

        for pos in DEV_POSITIONS:
            fen = pos["fen"]
            engine.clear_tt()
            engine.clear_killers()
            engine.clear_history_heuristic()
            engine.set_ordering_options(True, True)
            engine.set_pvs_options(False)
            engine.set_lmr_options(True, 3, 4, 1)
            engine.set_see_options(False, False)

            engine.set_neural_value_options(
                enabled=cfg["neural"],
                model_path=str(MODEL_PATH),
                blend=cfg["blend"],
                use_avx2=cfg["avx2"],
            )

            engine.set_fen(fen)
            bm, sc, d, nodes, elapsed, pv = engine.search(max_depth=30, time_limit=0.5)
            tot_nodes += nodes
            tot_depth += d

            pos_results.append({
                "id": pos["id"],
                "best_move": bm,
                "score_cp": sc,
                "depth_reached": d,
                "nodes": nodes,
                "elapsed_s": round(elapsed, 4),
                "nps": round(nodes / elapsed) if elapsed > 0 else 0,
            })

        avg_depth = tot_depth / len(DEV_POSITIONS)
        results["fixed_time_500ms"][cfg_key] = {
            "total_nodes": tot_nodes,
            "avg_depth_reached": round(avg_depth, 2),
            "aggregate_nps": round(tot_nodes / (0.5 * len(DEV_POSITIONS))),
            "positions": pos_results,
        }
        print(f"    Avg Depth: {avg_depth:.2f} plies | Nodes: {tot_nodes:,} | NPS: {round(tot_nodes / (0.5 * len(DEV_POSITIONS))):,}")

    if sf_engine:
        sf_engine.quit()

    # 3. Causal Decomposition Analysis
    print("\n[3] Computing Causal Attribution Metrics...")
    c1_nodes_d5 = results["fixed_depth_5"]["A0_Classical_C1"]["total_nodes"]
    c1_nps_d5 = results["fixed_depth_5"]["A0_Classical_C1"]["aggregate_nps"]
    c1_depth_ft = results["fixed_time_500ms"]["A0_Classical_C1"]["avg_depth_reached"]

    for cfg_key in ["A1_Pure_NNUE_AVX2", "A2_Hybrid_AVX2", "A3_Hybrid_Scalar", "A4_Pure_NNUE_Scalar"]:
        d5_data = results["fixed_depth_5"][cfg_key]
        ft_data = results["fixed_time_500ms"][cfg_key]

        node_red_pct = ((d5_data["total_nodes"] - c1_nodes_d5) / c1_nodes_d5) * 100.0
        nps_ret_pct = (d5_data["aggregate_nps"] / c1_nps_d5) * 100.0
        depth_delta = ft_data["avg_depth_reached"] - c1_depth_ft

        # Agreement with Stockfish 19
        c_moves = [p["best_move"] for p in d5_data["positions"]]
        sf_moves = [p["sf_move"] for p in d5_data["positions"]]
        c1_moves = [p["best_move"] for p in results["fixed_depth_5"]["A0_Classical_C1"]["positions"]]

        agr_sf = sum(1 for a, b in zip(c_moves, sf_moves) if a == b) / len(sf_moves) * 100.0
        agr_c1 = sum(1 for a, b in zip(c_moves, c1_moves) if a == b) / len(c1_moves) * 100.0

        results["causal_decomposition"][cfg_key] = {
            "node_delta_depth5_pct": round(node_red_pct, 2),
            "nps_retention_depth5_pct": round(nps_ret_pct, 2),
            "depth_delta_500ms": round(depth_delta, 2),
            "sf19_move_agreement_pct": round(agr_sf, 1),
            "c1_move_agreement_pct": round(agr_c1, 1),
        }

        print(f"\n{cfg_key}:")
        print(f"  Node Delta (Depth 5):    {node_red_pct:+.2f}%")
        print(f"  NPS Retention (Depth 5): {nps_ret_pct:.1f}%")
        print(f"  Depth Delta (500ms):     {depth_delta:+.2f} plies")
        print(f"  Agreement with SF19:     {agr_sf:.1f}% | with C1: {agr_c1:.1f}%")

    out_file = RAW_DIR / "causal_attribution_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nCausal attribution telemetry saved to: {out_file}")


if __name__ == "__main__":
    run_causal_attribution()

