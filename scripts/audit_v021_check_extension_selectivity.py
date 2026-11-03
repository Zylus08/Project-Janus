"""Phase 6 Tactical Evaluation: Check Extension Selectivity Audit for Project Janus v0.21.

Evaluates the 12-position selective search reliability suite plus dedicated
check-evasion positions across three extension policies:
- disabled
- bounded_all_checks
- single_reply

Depths: 3 and 4
Outputs machine-readable audit report to analysis/v0.21/check_extension_selectivity_audit.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
import chess

from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis" / "v0.21"
OUT_FILE = OUT_DIR / "check_extension_selectivity_audit.json"

AUDIT_SUITE = [
    # 12-position core selective-search reliability suite
    {
        "id": "mate_in_one_scholar",
        "category": "forced_mate",
        "description": "Scholar's mate motif (White Queen delivers mate on f7)",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        "expected_move": "h5f7",
        "target_outcome": "mate",
    },
    {
        "id": "mate_in_two_smothered",
        "category": "forced_mate",
        "description": "Smothered mate pattern with Queen sacrifice threat",
        "fen": "6k1/5ppp/8/8/8/8/1Q4PP/6K1 w - - 0 1",
        "expected_move": "b2b8",
        "target_outcome": "mate",
    },
    {
        "id": "tactical_fork_knight",
        "category": "forks_and_pins",
        "description": "Royal fork winning queen",
        "fen": "r1b1k2r/pppp1ppp/8/4q3/1b2N3/8/PPP1PPPP/R2QKB1R w KQkq - 0 1",
        "expected_move": "c2c3",
        "target_outcome": "evasion_preserving_equality",
    },
    {
        "id": "absolute_pin_skewer",
        "category": "forks_and_pins",
        "description": "Absolute pin on rook along e-file",
        "fen": "4k3/4r3/8/8/8/8/4R3/4K3 w - - 0 1",
        "expected_move": "e2e7",
        "target_outcome": "equal_or_winning_trade",
    },
    {
        "id": "promotion_passed_pawn",
        "category": "promotion",
        "description": "Queen promotion with unstoppable 7th rank pawn",
        "fen": "8/1P6/8/8/8/8/k7/7K w - - 0 1",
        "expected_move": "b7b8q",
        "target_outcome": "promotion",
    },
    {
        "id": "defensive_block_promotion",
        "category": "defensive_resource",
        "description": "Black rook must blockade or capture white pawn before promotion",
        "fen": "8/1P6/8/8/8/8/1r6/k6K b - - 0 1",
        "expected_move": "b2b7",
        "target_outcome": "defensive_capture",
    },
    {
        "id": "trebuchet_zugzwang",
        "category": "zugzwang",
        "description": "Mutual zugzwang (Trébuchet); White to move loses d3 pawn",
        "fen": "8/8/8/3k4/3p4/3K4/8/8 w - - 0 1",
        "expected_move": None,
        "target_outcome": "preserves_material_guard_against_nmp",
    },
    {
        "id": "king_pawn_opposition",
        "category": "endgame_opposition",
        "description": "Distant opposition in king-and-pawn endgame",
        "fen": "8/8/4k3/8/8/4K3/8/8 w - - 0 1",
        "expected_move": None,
        "target_outcome": "opposition_defense",
    },
    {
        "id": "stalemate_defense",
        "category": "draw_defense",
        "description": "Black king in corner is stalemated",
        "fen": "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
        "expected_move": None,
        "target_outcome": "stalemate_draw",
    },
    {
        "id": "rook_endgame_lucena",
        "category": "low_material_endgame",
        "description": "Lucena position bridge-building setup",
        "fen": "1K1k4/1P1r4/8/8/8/8/8/2R5 w - - 0 1",
        "expected_move": None,
        "target_outcome": "winning_technique",
    },
    {
        "id": "discovered_check_defense",
        "category": "checks_counterchecks",
        "description": "Discovered check response required",
        "fen": "r1bqk2r/ppppbppp/2n5/4P3/2B1n3/5N2/PPP2PPP/RNBQK2R w KQkq - 1 6",
        "expected_move": None,
        "target_outcome": "tactical_defense",
    },
    {
        "id": "seventyfive_move_near_draw",
        "category": "draw_rules",
        "description": "Near seventy-five move threshold (halfmove clock 146)",
        "fen": "8/8/8/8/8/4k3/4r3/4K3 w - - 146 73",
        "expected_move": None,
        "target_outcome": "avoids_invalid_cutoffs",
    },
    # Dedicated check extension selectivity fixtures
    {
        "id": "forced_single_evasion",
        "category": "check_extension_selectivity",
        "description": "White king in check with exactly 1 legal evasion (Kh1-h2)",
        "fen": "8/8/8/8/8/7P/6P1/4r2K w - - 0 1",
        "expected_move": "h1h2",
        "target_outcome": "forced_single_evasion",
    },
    {
        "id": "multiple_check_evasions",
        "category": "check_extension_selectivity",
        "description": "White king in check with 5 legal evasions (c3, Nc3, Nd2, Bd2, Qd2)",
        "fen": "rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3",
        "expected_move": None,
        "target_outcome": "multiple_evasions",
    },
    {
        "id": "consecutive_checks_threat",
        "category": "check_extension_selectivity",
        "description": "Complex middlegame with multiple check and countercheck motifs",
        "fen": "r1b1k2r/pppp1ppp/2n5/4p3/2B1P1nq/3P4/PPP2PPP/RNBQK2R w KQkq - 1 7",
        "expected_move": None,
        "target_outcome": "tactical_stability",
    },
    {
        "id": "endgame_zugzwang_kp",
        "category": "endgame_zugzwang",
        "description": "King and pawn endgame with reciprocal zugzwang pressure",
        "fen": "8/8/p1p5/1p5p/1P5p/8/PPP2k1p/4K1br w - - 0 1",
        "expected_move": None,
        "target_outcome": "endgame_accuracy",
    },
]

POLICIES = ["disabled", "bounded_all_checks", "single_reply"]
DEPTHS = [3, 4]


def validate_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    v = board.copy()
    for m in pv:
        if m not in v.legal_moves:
            return False
        v.push(m)
    return True


def run_tactical_audit() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": "Janus v0.21",
        "suite_size": len(AUDIT_SUITE),
        "policies": POLICIES,
        "depths": DEPTHS,
        "positions": [],
        "divergences": [],
        "summary": {},
    }

    total_runs = 0
    divergence_count = 0
    pv_failures = 0
    forced_mates_found = {p: 0 for p in POLICIES}
    forced_mates_total = 0

    for pos in AUDIT_SUITE:
        is_mate_pos = pos["category"] == "forced_mate"
        if is_mate_pos:
            forced_mates_total += 1

        pos_entry = {
            "id": pos["id"],
            "category": pos["category"],
            "description": pos["description"],
            "fen": pos["fen"],
            "expected_move": pos["expected_move"],
            "target_outcome": pos["target_outcome"],
            "results": {},
        }

        board = chess.Board(pos["fen"])

        for depth in DEPTHS:
            depth_key = f"depth_{depth}"
            pos_entry["results"][depth_key] = {}
            depth_moves = {}
            depth_scores = {}

            for pol in POLICIES:
                engine = JanusSearch(
                    check_extension_policy=pol,
                    enable_lmr=True,
                    enable_nmp=True,
                    max_check_extensions=2,
                )
                start_t = time.perf_counter()
                res = engine.search(board.copy(), max_depth=depth)
                elapsed = time.perf_counter() - start_t

                pv_valid = validate_pv(board, res.pv)
                if not pv_valid:
                    pv_failures += 1

                best_uci = res.best_move.uci() if res.best_move else None
                if is_mate_pos and depth == 4:
                    if res.score >= 90000 and (pos["expected_move"] is None or best_uci == pos["expected_move"]):
                        forced_mates_found[pol] += 1

                run_res = {
                    "score": res.score,
                    "best_move": best_uci,
                    "pv": [m.uci() for m in res.pv],
                    "pv_valid": pv_valid,
                    "nodes": res.nodes,
                    "elapsed_s": round(elapsed, 4),
                    "check_extensions_eligible": res.check_extensions_eligible,
                    "check_extensions_applied": res.check_extensions_applied,
                    "check_extension_plies": res.check_extension_plies,
                    "check_extensions_suppressed": res.check_extensions_suppressed,
                    "check_extensions_multiple_replies": res.check_extensions_multiple_replies,
                    "check_extensions_terminal_mates": res.check_extensions_terminal_mates,
                }
                pos_entry["results"][depth_key][pol] = run_res
                depth_moves[pol] = best_uci
                depth_scores[pol] = res.score
                total_runs += 1

            # Detect divergences against disabled baseline
            base_move = depth_moves["disabled"]
            base_score = depth_scores["disabled"]
            for pol in ["bounded_all_checks", "single_reply"]:
                cand_move = depth_moves[pol]
                cand_score = depth_scores[pol]
                if cand_move != base_move or abs(cand_score - base_score) > 25:
                    divergence_count += 1
                    report["divergences"].append({
                        "position_id": pos["id"],
                        "depth": depth,
                        "policy": pol,
                        "baseline_move": base_move,
                        "candidate_move": cand_move,
                        "baseline_score": base_score,
                        "candidate_score": cand_score,
                        "score_delta": cand_score - base_score,
                    })

        report["positions"].append(pos_entry)

    report["summary"] = {
        "total_positions": len(AUDIT_SUITE),
        "total_evaluations": total_runs,
        "total_divergences": divergence_count,
        "pv_legality_failures": pv_failures,
        "pv_legality_pass_rate": 1.0 if pv_failures == 0 else 1.0 - (pv_failures / total_runs),
        "forced_mates_found_depth4": forced_mates_found,
        "forced_mates_total": forced_mates_total,
    }

    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Tactical audit complete: {len(AUDIT_SUITE)} positions x {len(POLICIES)} policies x {len(DEPTHS)} depths.")
    print(f"Saved machine-readable audit to {OUT_FILE}")
    print(f"Divergences detected: {divergence_count}")
    print(f"PV legality pass rate: {report['summary']['pv_legality_pass_rate'] * 100:.1f}%")
    print(f"Forced mates found at depth 4: {forced_mates_found}")
    return report


if __name__ == "__main__":
    run_tactical_audit()
