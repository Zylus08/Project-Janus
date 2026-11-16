#!/usr/bin/env python3
"""
audit_feature_schema.py
Phase 1: Feature Schema Forensics & Classification.
Audits the input representation across all mandatory feature tests.
"""

import sys
import json
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from train_janus_nnue import fen_to_features

def test_feature_schema():
    results = {}

    # 1. Starting position
    fen_start = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    stm_f, ntm_f, stm = fen_to_features(fen_start)
    results["startpos"] = {
        "active_stm_count": len(stm_f),
        "active_ntm_count": len(ntm_f),
        "stm": stm
    }

    # 2. Color Inversion / Symmetry
    # Startpos Black to move
    fen_start_b = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
    stm_f_b, ntm_f_b, stm_b = fen_to_features(fen_start_b)
    # The active features from Black's perspective should match the features of White's perspective under color/rank flip
    results["color_inversion_symmetry"] = {
        "white_stm_features_sorted": sorted(stm_f),
        "black_stm_features_sorted": sorted(stm_f_b),
        "exact_set_match": sorted(stm_f) == sorted(stm_f_b)
    }

    # 3. King placement test:
    # Position A: King on e1
    # Position B: King on g1 (all other pieces identical)
    fen_ke1 = "8/8/8/8/8/8/4P3/4K3 w - - 0 1"
    fen_kg1 = "8/8/8/8/8/8/4P3/6K1 w - - 0 1"
    stm_ke1, _, _ = fen_to_features(fen_ke1)
    stm_kg1, _, _ = fen_to_features(fen_kg1)
    
    # Check what features change:
    added = set(stm_kg1) - set(stm_ke1)
    removed = set(stm_ke1) - set(stm_kg1)
    unchanged = set(stm_ke1) & set(stm_kg1)
    
    results["king_placement_differential"] = {
        "fen_ke1": fen_ke1,
        "fen_kg1": fen_kg1,
        "features_ke1": sorted(stm_ke1),
        "features_kg1": sorted(stm_kg1),
        "removed_feature": list(removed),
        "added_feature": list(added),
        "unchanged_features": list(unchanged),
        "is_pawn_feature_affected_by_king_position": len(unchanged) == 1
    }

    # 4. Castling feature test
    # White O-O
    b_before_castling = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    fen_pre_oo = b_before_castling.fen()
    stm_pre, _, _ = fen_to_features(fen_pre_oo)
    b_before_castling.push(chess.Move.from_uci("e1g1"))
    fen_post_oo = b_before_castling.fen()
    stm_post, _, _ = fen_to_features(fen_post_oo)
    results["castling_white_kingside"] = {
        "removed": sorted(list(set(stm_pre) - set(stm_post))),
        "added": sorted(list(set(stm_post) - set(stm_pre))),
        "num_removed": len(set(stm_pre) - set(stm_post)),
        "num_added": len(set(stm_post) - set(stm_pre))
    }

    # 5. En Passant feature test
    b_ep = chess.Board("8/8/8/3pP3/8/8/8/4K2k w - d6 0 1")
    stm_pre_ep, _, _ = fen_to_features(b_ep.fen())
    b_ep.push(chess.Move.from_uci("e5d6"))
    stm_post_ep, _, _ = fen_to_features(b_ep.fen())
    results["en_passant"] = {
        "removed": sorted(list(set(stm_pre_ep) - set(stm_post_ep))),
        "added": sorted(list(set(stm_post_ep) - set(stm_pre_ep))),
        "num_removed": len(set(stm_pre_ep) - set(stm_post_ep)), # pawn from e5, pawn on d5
        "num_added": len(set(stm_post_ep) - set(stm_pre_ep))     # pawn on d6
    }

    # 6. Promotion & Underpromotion feature test
    b_promo = chess.Board("8/4P3/8/8/8/8/8/4K2k w - - 0 1")
    stm_pre_pr, _, _ = fen_to_features(b_promo.fen())
    # Q promo
    b_q = b_promo.copy()
    b_q.push(chess.Move.from_uci("e7e8q"))
    stm_q, _, _ = fen_to_features(b_q.fen())
    # N promo (underpromotion)
    b_n = b_promo.copy()
    b_n.push(chess.Move.from_uci("e7e8n"))
    stm_n, _, _ = fen_to_features(b_n.fen())
    results["promotions"] = {
        "queen_promo_added": sorted(list(set(stm_q) - set(stm_pre_pr))),
        "knight_promo_added": sorted(list(set(stm_n) - set(stm_pre_pr))),
        "distinct_promotions": set(stm_q) != set(stm_n)
    }

    # 7. Make/Unmake Invariance across 100 legal moves
    board = chess.Board()
    import random
    random.seed(42)
    make_unmake_failures = 0
    for step in range(100):
        legal = list(board.legal_moves)
        if not legal or board.is_game_over():
            board = chess.Board()
            legal = list(board.legal_moves)
        m = random.choice(legal)
        f_before, _, _ = fen_to_features(board.fen())
        board.push(m)
        board.pop()
        f_after, _, _ = fen_to_features(board.fen())
        if sorted(f_before) != sorted(f_after):
            make_unmake_failures += 1
    results["make_unmake_invariant"] = (make_unmake_failures == 0)

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "feature_schema_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print("PHASE 1 FEATURE SCHEMA AUDIT COMPLETE")
    print(f"Active features in startpos: STM={results['startpos']['active_stm_count']}, NTM={results['startpos']['active_ntm_count']}")
    print(f"Color inversion symmetry match: {results['color_inversion_symmetry']['exact_set_match']}")
    print(f"King placement independence: Is pawn feature affected by king? {not results['king_placement_differential']['is_pawn_feature_affected_by_king_position']}")
    print(f"Castling features modified: -{results['castling_white_kingside']['num_removed']} +{results['castling_white_kingside']['num_added']}")
    print(f"En passant features modified: -{results['en_passant']['num_removed']} +{results['en_passant']['num_added']}")
    print(f"Distinct promotions: {results['promotions']['distinct_promotions']}")
    print(f"Make/Unmake invariance: {results['make_unmake_invariant']}")
    print(f"Raw report saved to: {out_file}")

if __name__ == "__main__":
    test_feature_schema()
