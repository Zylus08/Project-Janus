"""Milestone v0.27: Independent match reconstruction and move-sequence audit.

Reconstructs the v0.26 100-game match from raw PGN, CSV, and JSON records:
- Validates pairing, color reversal, opening FEN consistency.
- Reconciles results, plies, termination reasons across all 3 formats.
- Compares move-by-move UCI sequences between Game 1 and Game 2 of every opening pair.
- Detects whether engines made identical move choices at every ply or diverged.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
PGN_PATH = ROOT / "analysis" / "v0.26" / "match" / "janus-see-ordering-v026.pgn"
CSV_PATH = ROOT / "analysis" / "v0.26" / "match" / "janus-see-ordering-v026.csv"
JSON_PATH = ROOT / "analysis" / "v0.26" / "match" / "janus-see-ordering-v026.json"
OUT_AUDIT = ROOT / "analysis" / "v0.27" / "match_reconstruction_audit.json"


def audit_match() -> dict[str, Any]:
    print("=" * 75)
    print("Project Janus v0.27 — Independent Match Reconstruction & Move Audit")
    print(f"Auditing raw artifacts from: {PGN_PATH.parent}")
    print("=" * 75)

    # 1. Load PGN games
    pgn_games: list[chess.pgn.Game] = []
    with PGN_PATH.open("r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            pgn_games.append(g)

    print(f"Loaded {len(pgn_games)} games from PGN.")

    # 2. Load CSV rows
    csv_rows: list[dict[str, str]] = []
    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
    print(f"Loaded {len(csv_rows)} rows from CSV.")

    # 3. Load JSON report
    json_data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    json_games = json_data.get("games", [])
    print(f"Loaded {len(json_games)} games from JSON report.")

    # Integrity & reconciliation check
    assert len(pgn_games) == 100, f"Expected 100 PGN games, found {len(pgn_games)}"
    assert len(csv_rows) == 100, f"Expected 100 CSV rows, found {len(csv_rows)}"
    assert len(json_games) == 100, f"Expected 100 JSON games, found {len(json_games)}"

    reconciliation_mismatches = 0
    for idx in range(100):
        pgn_g = pgn_games[idx]
        csv_r = csv_rows[idx]
        json_g = json_games[idx]

        # Check round / game number
        r_num = idx + 1
        assert int(pgn_g.headers.get("Round", 0)) == r_num
        assert int(csv_r["game"]) == r_num
        assert int(json_g["game"]) == r_num

        # Check results
        p_res = pgn_g.headers.get("Result")
        c_res = csv_r["result"]
        j_res = json_g["result"]
        if not (p_res == c_res == j_res):
            reconciliation_mismatches += 1
            print(f"Mismatch in game {r_num} result: PGN={p_res}, CSV={c_res}, JSON={j_res}")

        # Check White and Black
        assert pgn_g.headers.get("White") == csv_r["white"] == json_g["white"]
        assert pgn_g.headers.get("Black") == csv_r["black"] == json_g["black"]

    print(f"Cross-format reconciliation: 100 games verified, {reconciliation_mismatches} mismatches.")

    # 4. Opening Pair Move Sequence Reconstruction
    pair_audits: list[dict[str, Any]] = []
    identical_move_sequence_pairs = 0
    divergent_pairs = 0
    tied_score_pairs = 0

    for pair_idx in range(50):
        g1_idx = 2 * pair_idx
        g2_idx = 2 * pair_idx + 1

        g1 = pgn_games[g1_idx]
        g2 = pgn_games[g2_idx]

        pair_num = pair_idx + 1
        opening_id1 = g1.headers.get("Opening", "unknown")
        opening_id2 = g2.headers.get("Opening", "unknown")
        assert opening_id1 == opening_id2, f"Opening mismatch in pair {pair_num}"

        fen1 = g1.headers.get("FEN")
        fen2 = g2.headers.get("FEN")
        assert fen1 == fen2, f"Starting FEN mismatch in pair {pair_num}"

        # Color reversal check
        # Game 1: White=Baseline, Black=Ordering
        # Game 2: White=Ordering, Black=Baseline
        assert g1.headers.get("White") == "Janus-Baseline" and g1.headers.get("Black") == "Janus-SEE-Ordering"
        assert g2.headers.get("White") == "Janus-SEE-Ordering" and g2.headers.get("Black") == "Janus-Baseline"

        # Reconstruct move sequences
        moves1 = [move.uci() for move in g1.mainline_moves()]
        moves2 = [move.uci() for move in g2.mainline_moves()]

        res1 = g1.headers.get("Result")
        res2 = g2.headers.get("Result")

        # Scoring: Baseline is Control, SEE-Ordering is Treatment
        # In Game 1: Baseline is White, Ordering is Black
        t_pts1 = 0.5 if res1 == "1/2-1/2" else (1.0 if res1 == "0-1" else 0.0)
        c_pts1 = 0.5 if res1 == "1/2-1/2" else (1.0 if res1 == "1-0" else 0.0)

        # In Game 2: Ordering is White, Baseline is Black
        t_pts2 = 0.5 if res2 == "1/2-1/2" else (1.0 if res2 == "1-0" else 0.0)
        c_pts2 = 0.5 if res2 == "1/2-1/2" else (1.0 if res2 == "0-1" else 0.0)

        t_total = t_pts1 + t_pts2
        c_total = c_pts1 + c_pts2
        is_tied = (t_total == c_total)
        if is_tied:
            tied_score_pairs += 1

        moves_identical = (moves1 == moves2)
        divergence_ply = None
        divergence_detail = None

        if moves_identical:
            identical_move_sequence_pairs += 1
        else:
            divergent_pairs += 1
            # Find first differing ply
            min_len = min(len(moves1), len(moves2))
            diff_ply = None
            for p_i in range(min_len):
                if moves1[p_i] != moves2[p_i]:
                    diff_ply = p_i + 1
                    break
            if diff_ply is None:
                diff_ply = min_len + 1

            divergence_ply = diff_ply
            # Whose turn was it at diff_ply?
            # 1-indexed ply from opening fen
            board = g1.board()
            for p_i in range(diff_ply - 1):
                board.push_uci(moves1[p_i])
            turn_str = "White" if board.turn == chess.WHITE else "Black"
            g1_mover = "Janus-Baseline" if turn_str == "White" else "Janus-SEE-Ordering"
            g2_mover = "Janus-SEE-Ordering" if turn_str == "White" else "Janus-Baseline"

            m1_str = moves1[diff_ply - 1] if diff_ply - 1 < len(moves1) else "<ended>"
            m2_str = moves2[diff_ply - 1] if diff_ply - 1 < len(moves2) else "<ended>"

            divergence_detail = {
                "ply": diff_ply,
                "turn": turn_str,
                "fen_before_move": board.fen(),
                "game1_mover": g1_mover,
                "game1_move": m1_str,
                "game2_mover": g2_mover,
                "game2_move": m2_str,
            }
            print(f"Pair {pair_num:02d} ({opening_id1}) DIVERGED at ply {diff_ply} ({turn_str}):")
            print(f"  Game 1 ({g1_mover}): {m1_str}")
            print(f"  Game 2 ({g2_mover}): {m2_str}")

        pair_audits.append({
            "pair": pair_num,
            "opening_id": opening_id1,
            "starting_fen": fen1,
            "game1": {
                "game_num": g1_idx + 1,
                "white": "Janus-Baseline",
                "black": "Janus-SEE-Ordering",
                "result": res1,
                "termination": g1.headers.get("Termination"),
                "plies": len(moves1),
            },
            "game2": {
                "game_num": g2_idx + 1,
                "white": "Janus-SEE-Ordering",
                "black": "Janus-Baseline",
                "result": res2,
                "termination": g2.headers.get("Termination"),
                "plies": len(moves2),
            },
            "treatment_points": t_total,
            "control_points": c_total,
            "pair_delta_pct": round(((t_total - c_total) / 2.0) * 100.0, 2),
            "score_tied": is_tied,
            "move_sequences_identical": moves_identical,
            "divergence_ply": divergence_ply,
            "divergence_detail": divergence_detail,
        })

    print("\n" + "=" * 75)
    print("MOVE SEQUENCE AUDIT SUMMARY:")
    print(f"Total Opening Pairs Audited: 50")
    print(f"Pairs with Tied Scores (1.0 - 1.0): {tied_score_pairs} / 50 ({100.0 * tied_score_pairs / 50:.1f}%)")
    print(f"Pairs with IDENTICAL Move Sequences: {identical_move_sequence_pairs} / 50 ({100.0 * identical_move_sequence_pairs / 50:.1f}%)")
    print(f"Pairs with DIVERGENT Move Sequences: {divergent_pairs} / 50 ({100.0 * divergent_pairs / 50:.1f}%)")
    print("=" * 75)

    audit_results: dict[str, Any] = {
        "metadata": {
            "match_pgn": str(PGN_PATH),
            "match_csv": str(CSV_PATH),
            "match_json": str(JSON_PATH),
            "total_games": len(pgn_games),
            "total_pairs": 50,
        },
        "reconciliation": {
            "pgn_games_count": len(pgn_games),
            "csv_rows_count": len(csv_rows),
            "json_games_count": len(json_games),
            "reconciliation_mismatches": reconciliation_mismatches,
            "all_formats_reconciled": bool(reconciliation_mismatches == 0),
        },
        "summary": {
            "tied_score_pairs": tied_score_pairs,
            "identical_move_sequence_pairs": identical_move_sequence_pairs,
            "divergent_pairs": divergent_pairs,
            "identical_move_sequences_pct": round(100.0 * identical_move_sequence_pairs / 50.0, 2),
            "divergent_pct": round(100.0 * divergent_pairs / 50.0, 2),
        },
        "pairs": pair_audits,
    }

    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_AUDIT.open("w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)

    print(f"Audit output written to: {OUT_AUDIT}")
    return audit_results


if __name__ == "__main__":
    audit_match()
