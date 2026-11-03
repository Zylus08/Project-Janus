"""Phase 8 Tactical and Endgame Regression Suite for Milestone v0.22.

Evaluates tactical robustness across 4 SEE configurations:
1. baseline (ordering=False, pruning=False)
2. see_ordering_only (ordering=True, pruning=False)
3. see_pruning_only (ordering=False, pruning=True)
4. see_ordering_and_pruning (ordering=True, pruning=True)

Covers:
- Forced mates and defensive resources
- Hanging pieces and profitable exchanges
- Captures that lose material but are tactically necessary
- Checking captures
- Capture promotions and underpromotions
- En passant tactics
- Pinned attackers and king recaptures
- Stalemate and draw-sensitive positions
- Positions where negative-SEE move avoids worse outcome / prevents mate

Depths: 3 and 4
Outputs machine-readable audit report to analysis/v0.22/see_tactical_audit.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import chess

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch

OUT_DIR = ROOT / "analysis" / "v0.22"
OUT_FILE = OUT_DIR / "see_tactical_audit.json"

AUDIT_SUITE: list[dict[str, Any]] = [
    # 1. Forced Mate
    {
        "id": "mate_in_one_scholar",
        "category": "forced_mate",
        "description": "Scholar's mate motif (White Queen delivers mate on f7)",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        "expected_moves": ["h5f7"],
        "target_outcome": "mate",
    },
    {
        "id": "mate_in_two_smothered",
        "category": "forced_mate",
        "description": "Smothered mate pattern with Queen sacrifice threat",
        "fen": "6k1/5ppp/8/8/8/8/1Q4PP/6K1 w - - 0 1",
        "expected_moves": ["b2b8"],
        "target_outcome": "mate",
    },
    # 2. Tactical Evasions and Forks
    {
        "id": "tactical_fork_knight",
        "category": "forks_and_pins",
        "description": "Royal fork / check evasion defending equality",
        "fen": "r1b1k2r/pppp1ppp/8/4q3/1b2N3/8/PPP1PPPP/R2QKB1R w KQkq - 0 1",
        "expected_moves": ["c2c3", "e4d2", "b1d2", "b1c3", "d1d2"],
        "target_outcome": "evasion_preserving_equality",
    },
    {
        "id": "absolute_pin_skewer",
        "category": "forks_and_pins",
        "description": "Absolute pin on rook along e-file",
        "fen": "4k3/4r3/8/8/8/8/4R3/4K3 w - - 0 1",
        "expected_moves": ["e2e7"],
        "target_outcome": "equal_or_winning_trade",
    },
    # 3. Promotions and Capture Promotions
    {
        "id": "promotion_passed_pawn",
        "category": "promotion",
        "description": "Queen promotion with unstoppable 7th rank pawn",
        "fen": "8/1P6/8/8/8/8/k7/7K w - - 0 1",
        "expected_moves": ["b7b8q", "b7b8r"],
        "target_outcome": "promotion",
    },
    {
        "id": "capture_promotion_mate",
        "category": "capture_promotion",
        "description": "Pawn captures rook on 8th rank promoting to queen with checkmate",
        "fen": "4r1k1/3P1ppp/8/8/8/8/5PPP/6K1 w - - 0 1",
        "expected_moves": ["d7e8q", "d7e8r"],
        "target_outcome": "capture_promotion_mate",
    },
    # 4. Defensive Resource
    {
        "id": "defensive_block_promotion",
        "category": "defensive_resource",
        "description": "Black rook must capture white pawn before promotion",
        "fen": "8/1P6/8/8/8/8/1r6/k6K b - - 0 1",
        "expected_moves": ["b2b7"],
        "target_outcome": "defensive_capture",
    },
    # 5. Hanging Pieces and Profitable Exchanges
    {
        "id": "hanging_piece_free_bishop",
        "category": "hanging_piece",
        "description": "Black bishop on b4 is completely undefended",
        "fen": "r1bqk2r/pppp1ppp/2n5/4p3/1bB1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
        "expected_moves": ["c3b4", "a2a3", "d2d3", "d2d4", "c3d5", "c4f7", "e1g1"],
        "target_outcome": "profitable_exchange_or_development",
    },
    {
        "id": "hanging_knight_capture",
        "category": "hanging_piece",
        "description": "Black knight on e4 is undefended after pawn push",
        "fen": "r1bqk2r/ppp2ppp/2n5/3p4/3Pn3/2NB1N2/PPP2PPP/R1BQK2R w KQkq - 0 8",
        "expected_moves": ["c3e4", "d3e4"],
        "target_outcome": "capture_undefended_piece",
    },
    # 6. Checking Captures
    {
        "id": "checking_capture_pawn",
        "category": "checking_capture",
        "description": "Queen captures defended pawn on f7 delivering check",
        "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        "expected_moves": ["f3f7"],
        "target_outcome": "checking_capture_mate",
    },
    # 7. En Passant Tactic
    {
        "id": "en_passant_discovered_check",
        "category": "en_passant",
        "description": "White pawn plays exd6 e.p. capturing pawn and opening e-file",
        "fen": "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",
        "expected_moves": ["e5d6", "g1f3", "d2d4", "f1c4", "b1c3"],
        "target_outcome": "legal_en_passant_handling",
    },
    # 8. Pinned Attacker and King Recaptures
    {
        "id": "pinned_defender_cannot_retaliate",
        "category": "pins_and_legality",
        "description": "Black rook pinned to king cannot legally capture queen",
        "fen": "8/8/8/3r4/4Q3/8/3R4/3K3k w - - 0 1",
        "expected_moves": ["e4g2", "e4d5", "d2d5"],
        "target_outcome": "capture_pinned_piece_or_deliver_mate",
    },
    {
        "id": "king_recapture_only_legal_move",
        "category": "king_recaptures",
        "description": "King must recapture queen on undefended square",
        "fen": "8/8/8/8/8/3q4/3K4/8 w - - 0 1",
        "expected_moves": ["d2d3"],
        "target_outcome": "king_recapture",
    },
    # 9. Negative-SEE Tactically Necessary Moves
    {
        "id": "losing_capture_avoids_mate",
        "category": "negative_see_defense",
        "description": "Queen capture on f3 (Qxf3) loses queen to pawn gxf3, but prevents Qxf2#",
        "fen": "r1b1k2r/pp3ppp/8/8/8/5q2/PP3PPP/R1BQKB1R w KQkq - 0 1",
        "expected_moves": ["d1f3", "g2f3"],
        "target_outcome": "eliminate_mating_attacker",
    },
    {
        "id": "queen_sacrifice_for_stalemate",
        "category": "stalemate_defense",
        "description": "Black king stalemated in corner",
        "fen": "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
        "expected_moves": [],
        "target_outcome": "stalemate_draw",
    },
    # 10. Endgames & Zugzwang
    {
        "id": "trebuchet_zugzwang",
        "category": "zugzwang",
        "description": "Mutual zugzwang (Trébuchet); White to move loses d3 pawn",
        "fen": "8/8/8/3k4/3p4/3K4/8/8 w - - 0 1",
        "expected_moves": [],
        "target_outcome": "preserves_material_guard_against_nmp",
    },
    {
        "id": "king_pawn_opposition",
        "category": "endgame_opposition",
        "description": "Distant opposition in king-and-pawn endgame",
        "fen": "8/8/4k3/8/8/4K3/8/8 w - - 0 1",
        "expected_moves": [],
        "target_outcome": "opposition_defense",
    },
    {
        "id": "rook_endgame_lucena",
        "category": "low_material_endgame",
        "description": "Lucena position bridge-building setup",
        "fen": "1K1k4/1P1r4/8/8/8/8/8/2R5 w - - 0 1",
        "expected_moves": [],
        "target_outcome": "winning_technique",
    },
    {
        "id": "forced_single_evasion",
        "category": "check_evasion",
        "description": "White king in check with exactly 1 legal evasion (Kh1-h2)",
        "fen": "8/8/8/8/8/7P/6P1/4r2K w - - 0 1",
        "expected_moves": ["h1h2"],
        "target_outcome": "forced_single_evasion",
    },
    {
        "id": "multiple_check_evasions",
        "category": "check_evasion",
        "description": "White king in check with 5 legal evasions (c3, Nc3, Nd2, Bd2, Qd2)",
        "fen": "rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3",
        "expected_moves": ["c2c3", "b1c3", "b1d2", "c1d2", "d1d2"],
        "target_outcome": "multiple_evasions",
    },
]

CONFIGS = {
    "baseline": {"enable_see_ordering": False, "enable_see_pruning": False},
    "see_ordering_only": {"enable_see_ordering": True, "enable_see_pruning": False},
    "see_pruning_only": {"enable_see_ordering": False, "enable_see_pruning": True},
    "see_ordering_and_pruning": {"enable_see_ordering": True, "enable_see_pruning": True},
}

DEPTHS = [3, 4]


def validate_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    v = board.copy()
    for m in pv:
        if m not in v.legal_moves:
            return False
        v.push(m)
    return True


def run_tactical_audit() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": "Janus v0.22",
        "suite_size": len(AUDIT_SUITE),
        "configs": list(CONFIGS.keys()),
        "depths": DEPTHS,
        "positions": [],
        "divergences": [],
        "failures": [],
    }

    print(f"=== Project Janus v0.22 Tactical & Endgame Regression Audit ===")
    print(f"Suite size: {len(AUDIT_SUITE)} positions | Configs: {list(CONFIGS.keys())} | Depths: {DEPTHS}")

    total_evals = 0
    passed_checks = 0

    for pos in AUDIT_SUITE:
        pos_entry: dict[str, Any] = {
            "id": pos["id"],
            "category": pos["category"],
            "description": pos["description"],
            "fen": pos["fen"],
            "expected_moves": pos["expected_moves"],
            "target_outcome": pos["target_outcome"],
            "depth_results": {},
        }
        board = chess.Board(pos["fen"])
        is_terminal = board.is_game_over()

        for d in DEPTHS:
            d_entry: dict[str, Any] = {}
            for cfg_name, cfg in CONFIGS.items():
                engine = JanusSearch(
                    check_extension_policy="disabled",
                    enable_history=True,
                    enable_pvs=True,
                    enable_aspiration=True,
                    enable_lmr=True,
                    enable_nmp=True,
                    enable_see_ordering=cfg["enable_see_ordering"],
                    enable_see_pruning=cfg["enable_see_pruning"],
                )
                board_copy = board.copy()
                engine.tt.clear()
                res = engine.search(board_copy, max_depth=d)
                best_uci = res.best_move.uci() if res.best_move else ""
                pv_uci = [m.uci() for m in res.pv]
                pv_valid = validate_pv(board, res.pv)
                legal_move = is_terminal or (res.best_move is not None and res.best_move in board.legal_moves)

                total_evals += 1
                if pv_valid and legal_move:
                    passed_checks += 1
                else:
                    report["failures"].append({
                        "id": pos["id"],
                        "depth": d,
                        "config": cfg_name,
                        "legal_move": legal_move,
                        "pv_valid": pv_valid,
                    })

                # Expected move check
                expected = pos["expected_moves"]
                expected_match = (best_uci in expected) if expected else True
                if expected and not expected_match:
                    report["divergences"].append({
                        "id": pos["id"],
                        "depth": d,
                        "config": cfg_name,
                        "expected": expected,
                        "actual": best_uci,
                        "score": res.score,
                    })

                d_entry[cfg_name] = {
                    "completed_depth": res.depth,
                    "score": res.score,
                    "best_move": best_uci,
                    "pv": pv_uci,
                    "pv_legal": pv_valid,
                    "legal_best_move": legal_move,
                    "nodes": res.nodes,
                    "elapsed": round(res.elapsed, 6),
                    "expected_match": expected_match,
                    "see_evaluations": res.see_evaluations,
                    "captures_ordered_see": res.captures_ordered_see,
                    "qsearch_captures_considered": res.qsearch_captures_considered,
                    "qsearch_captures_pruned": res.qsearch_captures_pruned,
                    "qsearch_captures_exempted": res.qsearch_captures_exempted,
                    "see_cache_hits": res.see_cache_hits,
                }
            pos_entry["depth_results"][f"depth_{d}"] = d_entry

        report["positions"].append(pos_entry)
        print(f"  Processed {pos['id']:<35} (legal_moves: {len(list(board.legal_moves))})")

    report["summary"] = {
        "total_searches": total_evals,
        "valid_pv_and_legal_rate": f"{passed_checks}/{total_evals} ({(passed_checks / total_evals) * 100:.2f}%)",
        "divergences_count": len(report["divergences"]),
        "failures_count": len(report["failures"]),
    }

    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nAudit completed. Report saved to {OUT_FILE}")
    print(f"Summary: {report['summary']}")
    return report


if __name__ == "__main__":
    run_tactical_audit()
