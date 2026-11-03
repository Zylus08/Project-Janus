"""Phase I: Tactical correctness and search reliability audit for Milestone v0.26.

Audits four factorial arms across 12 tactical and endgame positions:
- Arm A (Baseline): SEE ordering OFF, SEE pruning OFF
- Arm B (Ordering-only): SEE ordering ON, SEE pruning OFF
- Arm C (Pruning-only): SEE ordering OFF, SEE pruning ON
- Arm D (Combined): SEE ordering ON, SEE pruning ON

Evaluates depths 3, 4, and 5 for:
- Board restoration immutability
- Best-move legality
- Full PV legality
- Forced mate detection
- Best-move and score divergences
- Telemetry (nodes, time, SEE ordered, SEE pruned, cache hits)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
import chess

from janus.search import JanusSearch, MATE_THRESHOLD

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "analysis" / "v0.26" / "tactics_audit.json"

TACTICAL_POSITIONS = [
    {
        "id": "pos01_winning_capture",
        "category": "winning_capture",
        "description": "Undefended hanging bishop on b4; axa4 captures and wins piece",
        "fen": "rnbqk1nr/pppp1ppp/8/8/1b6/P7/1PPPPPPP/RNBQKBNR w KQkq - 0 1",
        "expected_best_move": "a3b4",
    },
    {
        "id": "pos02_losing_capture",
        "category": "losing_capture",
        "description": "Defended pawn f7 attacked by queen; capturing is losing",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        "losing_move": "h5f7",
    },
    {
        "id": "pos03_recapture_xray",
        "category": "recapture_xray",
        "description": "Doubled rooks on d-file; back-rank / recapture sequence",
        "fen": "2r3k1/5ppp/8/3r4/8/8/3R1PPP/3R2K1 w - - 0 1",
        "expected_best_move": "d2d5",
    },
    {
        "id": "pos04_pin_and_king_safety",
        "category": "pins_and_legality",
        "description": "Knight on e4 attacked; pawn on d3 and king safety",
        "fen": "r1bqk2r/ppppbppp/2n5/4p3/2B1n3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 6",
        "expected_best_move": "d3e4",
    },
    {
        "id": "pos05_en_passant",
        "category": "en_passant",
        "description": "En passant capture exf6 available",
        "fen": "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
        "legal_en_passant": "e5f6",
    },
    {
        "id": "pos06_promotion_capture",
        "category": "promotion",
        "description": "Passed pawn on 7th rank promotes with check",
        "fen": "6k1/4P1p1/8/8/8/8/8/4K2R w K - 0 1",
        "expected_promotion": "e7e8q",
    },
    {
        "id": "pos07_scholar_mate",
        "category": "checkmate_one",
        "description": "White Queen captures f7 with bishop defense: Qxf7# mate in 1",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        "expected_best_move": "h5f7",
        "is_mate": True,
    },
    {
        "id": "pos08_check_evasion",
        "category": "check_evasion",
        "description": "White king in check from Qh4; must block or evade",
        "fen": "rnb1kbnr/pppp1ppp/8/4p3/7q/5P2/PPPPP1PP/RNBQKBNR w KQkq - 1 3",
        "expected_best_move": "g2g3",
    },
    {
        "id": "pos09_tactical_sacrifice",
        "category": "tactical_sacrifice",
        "description": "Classical opening structure with developed pieces",
        "fen": "r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7",
    },
    {
        "id": "pos10_quiet_defense",
        "category": "quiet_defense",
        "description": "White Queen attacked by rook on d5; must retreat safely",
        "fen": "3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1",
        "losing_move": "d1d5",
    },
    {
        "id": "pos11_pruning_sensitivity",
        "category": "pruning_sensitivity",
        "description": "Open tactical position testing capture pruning interactions",
        "fen": "r1k4r/ppp1b1pp/2n5/4p3/4N3/8/PPP2PPP/R1BR2K1 w - - 0 1",
    },
    {
        "id": "pos12_zwischenzug",
        "category": "zwischenzug",
        "description": "Italian game tactical development",
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5",
    },
]

ARMS = {
    "Arm_A": {"label": "Baseline", "ordering": False, "pruning": False},
    "Arm_B": {"label": "Ordering-only", "ordering": True, "pruning": False},
    "Arm_C": {"label": "Pruning-only", "ordering": False, "pruning": True},
    "Arm_D": {"label": "Combined", "ordering": True, "pruning": True},
}


def verify_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    b = board.copy()
    for move in pv:
        if not b.is_legal(move):
            return False
        b.push(move)
    return True


def run_tactical_audit() -> dict[str, Any]:
    print("=" * 70)
    print("Project Janus v0.26 — Phase I Tactical & Reliability Audit")
    print("Factorial Comparison: Arms A, B, C, D across depths 3, 4, 5")
    print("=" * 70)

    results: dict[str, Any] = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "positions_count": len(TACTICAL_POSITIONS),
            "arms": ARMS,
            "depths": [3, 4, 5],
        },
        "positions": [],
        "summary": {},
    }

    total_evals = 0
    legal_moves_count = 0
    legal_pvs_count = 0
    immutability_passes = 0
    mate_detections_arm_a = 0
    mate_detections_arm_b = 0
    mate_detections_arm_c = 0
    mate_detections_arm_d = 0
    divergence_count = 0

    for pos_idx, pos in enumerate(TACTICAL_POSITIONS, 1):
        fen = pos["fen"]
        pos_id = pos["id"]
        print(f"\n[{pos_idx:02d}/{len(TACTICAL_POSITIONS):02d}] Auditing {pos_id}: {pos['description']}")

        pos_record: dict[str, Any] = {
            "id": pos_id,
            "category": pos["category"],
            "description": pos["description"],
            "fen": fen,
            "depths": {},
        }

        for depth in [3, 4, 5]:
            depth_record: dict[str, Any] = {}
            moves_at_depth: dict[str, str] = {}
            scores_at_depth: dict[str, int] = {}

            for arm_id, arm_cfg in ARMS.items():
                board = chess.Board(fen)
                engine = JanusSearch(
                    enable_see_ordering=arm_cfg["ordering"],
                    enable_see_pruning=arm_cfg["pruning"],
                )

                t0 = time.perf_counter()
                res = engine.search(board, max_depth=depth)
                elapsed = time.perf_counter() - t0

                total_evals += 1

                # Immutability check
                immutability_ok = (board.fen() == fen)
                if immutability_ok:
                    immutability_passes += 1

                # Best move legality
                best_move = res.best_move
                best_move_str = best_move.uci() if best_move else None
                move_legal = bool(best_move and board.is_legal(best_move))
                if move_legal:
                    legal_moves_count += 1

                # PV legality
                pv_legal = verify_pv(board, res.pv)
                if pv_legal:
                    legal_pvs_count += 1

                is_mate = res.score >= MATE_THRESHOLD or res.score <= -MATE_THRESHOLD
                if is_mate:
                    if arm_id == "Arm_A": mate_detections_arm_a += 1
                    elif arm_id == "Arm_B": mate_detections_arm_b += 1
                    elif arm_id == "Arm_C": mate_detections_arm_c += 1
                    elif arm_id == "Arm_D": mate_detections_arm_d += 1

                moves_at_depth[arm_id] = best_move_str or ""
                scores_at_depth[arm_id] = res.score

                depth_record[arm_id] = {
                    "best_move": best_move_str,
                    "score": res.score,
                    "nodes": res.nodes,
                    "elapsed_s": round(elapsed, 4),
                    "pv": [m.uci() for m in res.pv],
                    "move_legal": move_legal,
                    "pv_legal": pv_legal,
                    "immutability_ok": immutability_ok,
                    "see_ordered": engine.captures_ordered_see,
                    "see_pruned": engine.qsearch_captures_pruned,
                    "see_cache_hits": engine.see_cache_hits,
                }

            # Check divergence against baseline (Arm A)
            baseline_move = moves_at_depth.get("Arm_A")
            for other_arm in ["Arm_B", "Arm_C", "Arm_D"]:
                if moves_at_depth.get(other_arm) != baseline_move:
                    divergence_count += 1
                    print(f"  [DIVERGENCE at depth {depth}] {other_arm} chose {moves_at_depth.get(other_arm)} vs Arm A {baseline_move}")

            pos_record["depths"][str(depth)] = depth_record

        results["positions"].append(pos_record)

    results["summary"] = {
        "total_evaluations": total_evals,
        "legal_moves_count": legal_moves_count,
        "legal_moves_pct": round(100.0 * legal_moves_count / total_evals, 2),
        "legal_pvs_count": legal_pvs_count,
        "legal_pvs_pct": round(100.0 * legal_pvs_count / total_evals, 2),
        "immutability_passes": immutability_passes,
        "immutability_pct": round(100.0 * immutability_passes / total_evals, 2),
        "forced_mate_detections": {
            "Arm_A": mate_detections_arm_a,
            "Arm_B": mate_detections_arm_b,
            "Arm_C": mate_detections_arm_c,
            "Arm_D": mate_detections_arm_d,
        },
        "divergences_vs_baseline": divergence_count,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("PHASE I AUDIT SUMMARY:")
    print(f"Total Evaluations: {total_evals}")
    print(f"Legal Moves: {legal_moves_count}/{total_evals} ({results['summary']['legal_moves_pct']}%)")
    print(f"Legal PVs: {legal_pvs_count}/{total_evals} ({results['summary']['legal_pvs_pct']}%)")
    print(f"Immutability Passes: {immutability_passes}/{total_evals} ({results['summary']['immutability_pct']}%)")
    print(f"Forced Mate Detections: {results['summary']['forced_mate_detections']}")
    print(f"Move Divergences vs Baseline: {divergence_count}")
    print(f"Audit output written to: {OUT_FILE}")
    print("=" * 70)
    return results


if __name__ == "__main__":
    run_tactical_audit()
