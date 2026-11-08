#!/usr/bin/env python3
"""Project Janus v0.61 - Search Integration & Threshold Calibration Harness.

Evaluates Classical C1 (S0), Pure NNUE-V2 (S1), Hybrid NNUE-V2 50/50 (S2),
and Pure NNUE-V2 Scalar (S3) across 10 diverse benchmark positions at depth 4 and 5.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import chess
import chess.engine

ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR = ROOT / "analysis" / "v0.61" / "native"
MODEL_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"
STOCKFISH_PATH = Path(r"E:\ChessXML\tools\stockfish\stockfish.exe")

sys.path.insert(0, str(NATIVE_DIR))
from janus_native_bridge import NativeEngineBridge

BENCHMARK_POSITIONS = [
    {
        "id": "POS_01_STARTPOS",
        "category": "Opening",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    },
    {
        "id": "POS_02_ITALIAN",
        "category": "Open Game",
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
    },
    {
        "id": "POS_03_SICILIAN_NAJDORF",
        "category": "Semi-Open",
        "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
    },
    {
        "id": "POS_04_FRENCH_WINAWER",
        "category": "Closed/Semi-Closed",
        "fen": "r1bqk1nr/pp3ppp/2n1p3/2bpP3/8/2PB1N2/PP1P1PPP/RNBQK2R w KQkq - 0 6",
    },
    {
        "id": "POS_05_QGD_TARTAKOWER",
        "category": "Classical Defense",
        "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 b - - 4 8",
    },
    {
        "id": "POS_06_TACTICAL_MIDGAME",
        "category": "Sharp Middlegame",
        "fen": "r1b2rk1/1pq1bppp/p1np4/4p3/2B1P3/1NN1B3/PPP2PPP/R2Q1RK1 w - - 0 11",
    },
    {
        "id": "POS_07_ROOK_ENDGAME",
        "category": "Endgame R+P",
        "fen": "8/8/8/4k3/8/8/4K1P1/7r w - - 0 1",
    },
    {
        "id": "POS_08_OPPOSITE_BISHOPS",
        "category": "Technical Endgame",
        "fen": "8/2b5/8/4k3/8/5B2/4K3/8 w - - 0 1",
    },
    {
        "id": "POS_09_STRATEGIC_CLOSED",
        "category": "Manoeuvring",
        "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2BPP1b1/2P1BN2/PP1N1PPP/R2Q1RK1 b - - 1 9",
    },
    {
        "id": "POS_10_ASYMMETRIC_PAWNS",
        "category": "Dynamic Imbalance",
        "fen": "r1bqr1k1/pp3pbp/2p3p1/8/3PB3/1P4P1/PB2PP1P/R2Q1RK1 w - - 1 15",
    },
]


def run_search_calibration():
    print("=" * 70)
    print("PROJECT JANUS v0.61 — SEARCH INTEGRATION & THRESHOLD CALIBRATION")
    print("=" * 70)

    # Launch Stockfish 19 for teacher best move verification
    sf_engine = None
    if STOCKFISH_PATH.exists():
        sf_engine = chess.engine.SimpleEngine.popen_uci(str(STOCKFISH_PATH))
        print(f"Reference Teacher: Stockfish 19 loaded from {STOCKFISH_PATH.name}")

    engine = NativeEngineBridge()

    configs = {
        "S0_Classical_C1": {
            "use_neural": False,
            "blend": 0,
            "use_avx2": False,
            "desc": "Classical Baseline C1 (Native N5 Handcrafted Eval)",
        },
        "S1_Pure_NNUE_V2_AVX2": {
            "use_neural": True,
            "blend": 100,
            "use_avx2": True,
            "desc": "Pure NNUE-V2-Small with AVX2 SIMD",
        },
        "S2_Hybrid_50_AVX2": {
            "use_neural": True,
            "blend": 50,
            "use_avx2": True,
            "desc": "Hybrid 50% NNUE-V2 + 50% Classical C1 with AVX2",
        },
        "S3_Pure_NNUE_V2_Scalar": {
            "use_neural": True,
            "blend": 100,
            "use_avx2": False,
            "desc": "Pure NNUE-V2-Small Scalar C++17 Reference",
        },
    }

    results: Dict[str, Any] = {
        "depth_4": {},
        "depth_5": {},
        "summary": {},
    }

    for depth in [4, 5]:
        print(f"\n>>> Running Calibration at Search Depth {depth}...")
        results[f"depth_{depth}"] = {}

        for cfg_name, cfg in configs.items():
            print(f"\nEvaluating Config: {cfg_name} ({cfg['desc']})")
            cfg_data = []

            total_nodes = 0
            total_time = 0.0
            move_agreements_sf = 0
            move_agreements_c1 = 0

            for p_idx, pos in enumerate(BENCHMARK_POSITIONS):
                fen = pos["fen"]

                # Configure engine
                engine.clear_tt()
                engine.clear_killers()
                engine.clear_history_heuristic()
                engine.set_ordering_options(True, True)
                engine.set_pvs_options(False)
                engine.set_lmr_options(True, 3, 4, 1)
                engine.set_see_options(False, False)

                engine.set_neural_value_options(
                    enabled=cfg["use_neural"],
                    model_path=str(MODEL_PATH),
                    blend=cfg["blend"],
                    use_avx2=cfg["use_avx2"],
                )

                engine.set_fen(fen)
                bm, sc, d, nodes, elapsed, pv = engine.search(max_depth=depth, time_limit=10.0)

                total_nodes += nodes
                total_time += elapsed

                # SF Teacher best move
                sf_bm = ""
                if sf_engine:
                    b_sf = chess.Board(fen)
                    sf_res = sf_engine.play(b_sf, chess.engine.Limit(nodes=25000))
                    sf_bm = sf_res.move.uci() if sf_res.move else ""

                cfg_data.append({
                    "pos_id": pos["id"],
                    "best_move": bm,
                    "score_cp": sc,
                    "nodes": nodes,
                    "elapsed_s": round(elapsed, 4),
                    "nps": round(nodes / elapsed) if elapsed > 0 else 0,
                    "sf_move": sf_bm,
                })

            results[f"depth_{depth}"][cfg_name] = {
                "positions": cfg_data,
                "total_nodes": total_nodes,
                "total_time_s": round(total_time, 4),
                "aggregate_nps": round(total_nodes / total_time) if total_time > 0 else 0,
            }

            print(f"  Total Nodes: {total_nodes:,} | Time: {total_time:.3f}s | Aggregate NPS: {round(total_nodes/total_time):,}")

    if sf_engine:
        sf_engine.quit()

    # Compare S1 and S2 against S0
    for depth in [4, 5]:
        d_key = f"depth_{depth}"
        c1_res = results[d_key]["S0_Classical_C1"]
        c1_nodes = c1_res["total_nodes"]
        c1_nps = c1_res["aggregate_nps"]

        results["summary"][d_key] = {}
        print(f"\n--- DEPTH {depth} SUMMARY VS CLASSICAL C1 ---")
        for cfg_name in ["S1_Pure_NNUE_V2_AVX2", "S2_Hybrid_50_AVX2", "S3_Pure_NNUE_V2_Scalar"]:
            c_res = results[d_key][cfg_name]
            node_pct = ((c_res["total_nodes"] - c1_nodes) / c1_nodes) * 100.0
            nps_retention = (c_res["aggregate_nps"] / c1_nps) * 100.0

            # Move agreement with C1
            c1_moves = [p["best_move"] for p in c1_res["positions"]]
            c_moves = [p["best_move"] for p in c_res["positions"]]
            agr_c1 = sum(1 for a, b in zip(c1_moves, c_moves) if a == b) / len(c1_moves) * 100.0

            # Move agreement with Stockfish
            sf_moves = [p["sf_move"] for p in c1_res["positions"]]
            agr_sf = sum(1 for a, b in zip(sf_moves, c_moves) if a == b) / len(sf_moves) * 100.0
            c1_agr_sf = sum(1 for a, b in zip(sf_moves, c1_moves) if a == b) / len(sf_moves) * 100.0

            results["summary"][d_key][cfg_name] = {
                "node_delta_pct": round(node_pct, 2),
                "nps_retention_pct": round(nps_retention, 2),
                "agreement_with_c1_pct": round(agr_c1, 1),
                "agreement_with_sf_pct": round(agr_sf, 1),
                "c1_agreement_with_sf_pct": round(c1_agr_sf, 1),
            }

            print(f"{cfg_name}:")
            print(f"  Nodes: {c_res['total_nodes']:,} (Delta: {node_pct:+.2f}%)")
            print(f"  NPS:   {c_res['aggregate_nps']:,} ({nps_retention:.1f}% C1 retention)")
            print(f"  Move Agreement with C1: {agr_c1:.1f}% | with SF19: {agr_sf:.1f}% (C1 with SF19: {c1_agr_sf:.1f}%)")

    # Save raw calibration results
    out_file = ROOT / "analysis" / "v0.61" / "raw" / "search_calibration_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nCalibration raw data saved to: {out_file}")


if __name__ == "__main__":
    run_search_calibration()

