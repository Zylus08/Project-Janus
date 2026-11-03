"""Project Janus v0.41 - Effective-Depth and Tactical-Reliability Diagnostics.

Evaluates search depth, node efficiency, and tactical accuracy across a 16-position
tactical diagnostic suite comparing Baseline (K0), Candidate ORD1, and Candidate RFP.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, SearchResult
from janus import evaluation


@dataclass
class DiagnosticPosition:
    id: str
    category: str
    description: str
    fen: str
    expected_best_moves: list[str]
    provenance: str


# 16-position curated diagnostic suite spanning mates, forks, pins, promotions,
# sacrifices, king safety, and quiet tactical defenses.
TACTICAL_SUITE: list[DiagnosticPosition] = [
    DiagnosticPosition(
        id="pos_01_mate_in_one_queen",
        category="mate_in_one",
        description="White delivers mate in one with Queen supported by King",
        fen="8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
        expected_best_moves=["g5g7"],
        provenance="benchmarks/positions.json (mate_in_one)",
    ),
    DiagnosticPosition(
        id="pos_02_mate_in_one_scholars",
        category="mate_in_one",
        description="Scholar's mate pattern against f7 pawn",
        fen="r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        expected_best_moves=["h5f7"],
        provenance="tests/test_selective_search_reliability.py (Part B LMR)",
    ),
    DiagnosticPosition(
        id="pos_03_mate_in_one_back_rank",
        category="mate_in_one",
        description="Back rank mate with Queen along open 8th rank",
        fen="6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1",
        expected_best_moves=["e2e8"],
        provenance="standard back-rank tactical motif",
    ),
    DiagnosticPosition(
        id="pos_04_knight_fork",
        category="fork_and_skewer",
        description="Knight fork attacking uncastled King and Rook",
        fen="r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R1B1K2R w KQkq - 0 1",
        expected_best_moves=["d5c7"],
        provenance="tests/test_tactics_lmr.py (knight_fork)",
    ),
    DiagnosticPosition(
        id="pos_05_pin_skewer",
        category="fork_and_skewer",
        description="Rook pins Knight along file to King; winning capture or pawn lever",
        fen="4k3/8/8/4n3/8/8/8/4R1K1 w - - 0 1",
        expected_best_moves=["e1e5", "f2f4"],
        provenance="tests/test_tactics_lmr.py (pin_skewer)",
    ),
    DiagnosticPosition(
        id="pos_06_passed_pawn_promotion",
        category="pawn_endgame",
        description="Passed pawn on 7th rank promotes with King support",
        fen="8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
        expected_best_moves=["a7a8q", "a7a8r"],
        provenance="benchmarks/positions.json (promotion_tactic)",
    ),
    DiagnosticPosition(
        id="pos_07_defensive_move_against_mate",
        category="tactical_defense",
        description="Black must defend against combined Queen and Bishop mate threat on f7/h7",
        fen="r2qk3/pp2pp2/2P2n1Q/1B2p2b/4P2p/2N5/PPP3PP/2K4R b q - 0 19",
        expected_best_moves=["e7e6", "d8a5"],
        provenance="tests/test_tactics_lmr.py (defensive_move)",
    ),
    DiagnosticPosition(
        id="pos_08_overworked_deflection",
        category="deflection",
        description="White Queen recaptures rook on d1 resolving back-rank pin",
        fen="3r2k1/p4ppp/1p6/8/8/1Q2B3/PP3PPP/3r2K1 w - - 0 1",
        expected_best_moves=["b3d1"],
        provenance="tactical deflection and evasion motif",
    ),
    DiagnosticPosition(
        id="pos_09_trebuchet_zugzwang",
        category="pawn_endgame",
        description="Trébuchet pawn zugzwang; whoever moves loses pawn",
        fen="8/8/8/3k4/3p4/3K4/8/8 w - - 0 1",
        expected_best_moves=["d3d2", "d3e2"],
        provenance="tests/test_selective_search_reliability.py (trebuchet)",
    ),
    DiagnosticPosition(
        id="pos_10_opposition_endgame",
        category="pawn_endgame",
        description="Direct King opposition in king-and-pawn endgame",
        fen="8/8/4k3/8/4K3/8/8/8 w - - 0 1",
        expected_best_moves=["e4d4", "e4f4"],
        provenance="tests/test_selective_search_reliability.py (opposition)",
    ),
    DiagnosticPosition(
        id="pos_11_smothered_mate_pattern",
        category="mating_attack",
        description="Knight delivers smothered mate pattern to trapped corner King",
        fen="6rk/5Npp/8/8/8/8/8/6K1 w - - 0 1",
        expected_best_moves=["f7h6"],
        provenance="classic Philidor smothered mate geometry",
    ),
    DiagnosticPosition(
        id="pos_12_poisoned_rook_capture",
        category="tactical_defense",
        description="Queen capture vs recapture material balance evaluation",
        fen="3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1",
        expected_best_moves=["d1a4", "d1e2", "d1d5", "d1f3", "d1g4"],
        provenance="tests/test_evaluation_tactical.py (quiet_queen_retreats)",
    ),
    DiagnosticPosition(
        id="pos_13_central_fork_trick",
        category="tactical_opening",
        description="Standard Italian/Four Knights open middlegame position",
        fen="r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
        expected_best_moves=["c1g5", "c3d5", "h2h3", "a2a3"],
        provenance="benchmarks/positions.json (open_game)",
    ),
    DiagnosticPosition(
        id="pos_14_tactical_discovery_threat",
        category="tactical_middlegame",
        description="Bishop pair active in open center with pin against Black Queen/King",
        fen="r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7",
        expected_best_moves=["e1g1", "c1d2", "c4d5", "a2a3"],
        provenance="tests/test_selective_search_reliability.py (NMP PV legality)",
    ),
    DiagnosticPosition(
        id="pos_15_material_conversion",
        category="material_endgame",
        description="White has rook against minor piece; technical conversion",
        fen="4k3/8/8/8/8/8/4N3/4K2R w K - 0 1",
        expected_best_moves=["e1g1", "h1h7", "e1f2", "h1h4"],
        provenance="benchmarks/positions.json (white_up_rook)",
    ),
    DiagnosticPosition(
        id="pos_16_stalemate_detection",
        category="terminal",
        description="Black King stalemated in corner",
        fen="7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
        expected_best_moves=[],
        provenance="benchmarks/positions.json (stalemate)",
    ),
]


def create_engine(config_name: str) -> JanusSearch:
    """Create a JanusSearch instance with specified candidate configuration."""
    # Ensure baseline evaluation is active
    evaluation.set_evaluation_features(
        pawn_structure=True,
        rook_files=True,
        king_safety=True,
        uncastled_king_safety=True,
        tapered_eval=True,
    )

    if config_name == "baseline":
        return JanusSearch(
            enable_countermoves=False,
            enable_history_malus=False,
            enable_rfp=False,
        )
    elif config_name == "ord1":
        return JanusSearch(
            enable_countermoves=True,
            enable_history_malus=True,
            enable_rfp=False,
        )
    elif config_name == "rfp":
        return JanusSearch(
            enable_countermoves=False,
            enable_history_malus=False,
            enable_rfp=True,
            rfp_max_depth=2,
            rfp_margin_per_depth=120,
        )
    else:
        raise ValueError(f"Unknown configuration {config_name}")


def run_diagnostics(
    max_depth: int = 4,
    time_limit: Optional[float] = None,
) -> dict[str, Any]:
    configs = ["baseline", "ord1", "rfp"]
    results_by_config: dict[str, list[dict[str, Any]]] = {c: [] for c in configs}

    print(f"Running Effective-Depth & Tactical Diagnostics across {len(TACTICAL_SUITE)} positions...")
    print(f"Settings: max_depth={max_depth}, time_limit={time_limit}")
    print("-" * 80)

    for pos in TACTICAL_SUITE:
        board = chess.Board(pos.fen)
        for cfg_name in configs:
            engine = create_engine(cfg_name)
            t0 = time.perf_counter()
            search_res: SearchResult = engine.search(
                board,
                max_depth=max_depth,
                time_limit=time_limit,
            )
            elapsed = time.perf_counter() - t0

            best_uci = search_res.best_move.uci() if search_res.best_move else None
            # Check tactical success
            if not pos.expected_best_moves:
                # Terminal stalemate position
                success = (search_res.best_move is None)
            else:
                success = (best_uci in pos.expected_best_moves)

            pv_str = " ".join(m.uci() for m in search_res.pv)
            record = {
                "position_id": pos.id,
                "category": pos.category,
                "description": pos.description,
                "completed_depth": search_res.depth,
                "nodes": search_res.nodes,
                "elapsed_sec": round(elapsed, 4),
                "nps": int(search_res.nodes / elapsed) if elapsed > 0 else 0,
                "score_cp": search_res.score,
                "best_move": best_uci,
                "expected_moves": pos.expected_best_moves,
                "tactical_success": success,
                "pv": pv_str,
                "beta_cutoffs": search_res.beta_cutoffs,
                "countermove_cutoffs": search_res.countermove_cutoffs,
                "rfp_considered": search_res.rfp_considered,
                "rfp_cutoffs": search_res.rfp_cutoffs,
            }
            results_by_config[cfg_name].append(record)

    summary: dict[str, Any] = {}
    for cfg_name in configs:
        records = results_by_config[cfg_name]
        total_nodes = sum(r["nodes"] for r in records)
        total_time = sum(r["elapsed_sec"] for r in records)
        total_success = sum(1 for r in records if r["tactical_success"])
        rfp_cutoffs = sum(r["rfp_cutoffs"] for r in records)
        cm_cutoffs = sum(r["countermove_cutoffs"] for r in records)
        summary[cfg_name] = {
            "total_nodes": total_nodes,
            "total_time_sec": round(total_time, 4),
            "mean_nps": int(total_nodes / total_time) if total_time > 0 else 0,
            "tactical_accuracy_pct": round(100.0 * total_success / len(records), 2),
            "tactical_success_count": f"{total_success}/{len(records)}",
            "rfp_cutoffs_total": rfp_cutoffs,
            "countermove_cutoffs_total": cm_cutoffs,
        }

    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "platform": platform.platform(),
            "python_version": sys.version,
            "positions_count": len(TACTICAL_SUITE),
            "max_depth": max_depth,
            "time_limit": time_limit,
        },
        "summary": summary,
        "positions": [asdict(p) for p in TACTICAL_SUITE],
        "detailed_results": results_by_config,
    }


def main() -> None:
    out_dir = ROOT / "analysis" / "v0.41"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "effective_depth_diagnostics.json"

    # Run fixed depth 4 benchmark (representative of depth search across full tree)
    data = run_diagnostics(max_depth=4)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("\n" + "=" * 80)
    print("EFFECTIVE DEPTH & TACTICAL DIAGNOSTICS SUMMARY")
    print("=" * 80)
    for cfg, s in data["summary"].items():
        print(f"Config: {cfg.upper():<10} | Nodes: {s['total_nodes']:>8} | Time: {s['total_time_sec']:>6.3f}s | NPS: {s['mean_nps']:>7} | Tactical: {s['tactical_success_count']} ({s['tactical_accuracy_pct']}%) | RFP Cutoffs: {s['rfp_cutoffs_total']} | CM Cutoffs: {s['countermove_cutoffs_total']}")
    print(f"\nWritten raw JSON data to: {json_path}")


if __name__ == "__main__":
    main()

