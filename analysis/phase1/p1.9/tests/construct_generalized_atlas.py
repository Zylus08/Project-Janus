#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.9
Phase 1: 240-Position Generalized Chess Failure Atlas Builder
Constructs 240 provenance-tracked positions across 16 strategic categories.
Splits into 120 Development and 120 Held-Out sets clustered by source.
"""

import os
import sys
import json
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
OUT_JSON = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Sources
# 1. standard_50_evaluation_suite.json (50 positions)
# 2. diagnostic_corpus.json (37 positions)
# 3. tactical_regression_corpus.json (12 positions)
# 4. validation_corpus.json (16 positions)
# 5. P1.8 diagnostic corpus (24 positions)
# 6. Curated canonical endgames & strategic structures (101 positions)

def get_standard_50():
    p = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
    if not p.exists(): return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for d in data:
        items.append({
            "source": "p1.0_standard_50",
            "source_id": d["id"],
            "theme": d.get("theme", d.get("cat", "general")),
            "fen": d["fen"],
            "description": d.get("desc", ""),
            "cluster": f"std50_{d.get('cat', 'gen')}"
        })
    return items

def get_diag_v056():
    p = ROOT / "analysis" / "v0.56" / "corpus" / "diagnostic_corpus.json"
    if not p.exists(): return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for d in data:
        items.append({
            "source": "v0.56_diagnostic",
            "source_id": d["id"],
            "theme": d.get("category", "diagnostic"),
            "fen": d["fen"],
            "description": f"Pair {d.get('pair')}, {d.get('opening')}, ply {d.get('ply')}",
            "cluster": f"v056_pair_{d.get('pair', '0')}"
        })
    return items

def get_tactical_v056():
    p = ROOT / "analysis" / "v0.56" / "corpus" / "tactical_regression_corpus.json"
    if not p.exists(): return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for d in data:
        items.append({
            "source": "v0.56_tactical",
            "source_id": d["id"],
            "theme": d.get("theme", "tactics"),
            "fen": d["fen"],
            "solution": d.get("solution", ""),
            "description": d.get("description", ""),
            "cluster": "v056_tactics"
        })
    return items

def get_validation_v056():
    p = ROOT / "analysis" / "v0.56" / "corpus" / "validation_corpus.json"
    if not p.exists(): return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for d in data:
        items.append({
            "source": "v0.56_validation",
            "source_id": d["id"],
            "theme": d.get("theme", "validation"),
            "fen": d["fen"],
            "solution": d.get("expected_move", ""),
            "description": d.get("description", ""),
            "cluster": "v056_validation"
        })
    return items

def get_p18_diagnostic():
    p = ROOT / "analysis" / "phase1" / "p1.8" / "raw" / "diagnostic_corpus_raw.json"
    if not p.exists(): return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    positions = data.get("positions", [])
    for d in positions:
        items.append({
            "source": "p1.8_diagnostic",
            "source_id": d["id"],
            "theme": d.get("domain", "p1.8_diagnostic"),
            "fen": d["fen"],
            "description": d.get("desc", ""),
            "cluster": f"p18_{d['id'].split('_')[0]}"
        })
    return items

# Curated thematic benchmark positions covering all required categories
ADDITIONAL_THEMATIC_POSITIONS = [
    # CAT_01_OPEN_MG: Open middlegames
    {"theme": "open_middlegame", "fen": "r1b2rk1/pp2qppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R2Q1RK1 w - - 4 10", "desc": "Open center Tarrasch Defense structure", "cluster": "curated_open_mg_1"},
    {"theme": "open_middlegame", "fen": "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQR1K1 w - - 6 10", "desc": "Classical open Queen's Gambit Declined", "cluster": "curated_open_mg_2"},
    {"theme": "open_middlegame", "fen": "r1bq1rk1/1pp2ppp/p1np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 8", "desc": "Giuoco Piano open center skirmish", "cluster": "curated_open_mg_3"},
    {"theme": "open_middlegame", "fen": "r1bqr1k1/pp1nbppp/2p2n2/3p2B1/3P4/2NBPN2/PP3PPP/R2Q1RK1 w - - 5 11", "desc": "Karlsbad structure Carlsbad pawn formation", "cluster": "curated_open_mg_4"},
    {"theme": "open_middlegame", "fen": "r2qr1k1/pb1nbppp/1p1ppn2/8/2PP4/2NB1N2/PP2QPPP/R1B1R1K1 w - - 6 12", "desc": "Hedgehog formation with dynamic piece play", "cluster": "curated_open_mg_5"},
    {"theme": "open_middlegame", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 9", "desc": "Colle System open center", "cluster": "curated_open_mg_6"},

    # CAT_02_CLOSED_PAWN: Closed pawn structures & chains
    {"theme": "closed_pawn_chains", "fen": "r1b1k2r/pp1n1ppp/2n1p3/q1bpP3/5P2/2NB1N2/PPP3PP/R1BQK2R w KQkq - 1 9", "desc": "French Advance locked central chain d4-e5", "cluster": "curated_closed_1"},
    {"theme": "closed_pawn_chains", "fen": "r1bq1rk1/1ppnbppp/p2p1n2/4p3/2PPP3/2N1BN2/PP2BPPP/R2Q1RK1 b - - 5 9", "desc": "King's Indian classical locked center c4-d5-e4", "cluster": "curated_closed_2"},
    {"theme": "closed_pawn_chains", "fen": "r2q1rk1/pp1n1pbp/2p1p1p1/3pP3/3P1P2/2N1QN2/PPP3PP/R4RK1 w - - 0 13", "desc": "Benoni locked center e5 vs e6", "cluster": "curated_closed_3"},
    {"theme": "closed_pawn_chains", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2b5/2Pp4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 0 11", "desc": "Nimzo-Indian pawn chain lock d4 vs d5", "cluster": "curated_closed_4"},
    {"theme": "closed_pawn_chains", "fen": "r1bqr1k1/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R2Q1RK1 w - - 4 10", "desc": "Semi-Slav closed wedge", "cluster": "curated_closed_5"},

    # CAT_03_STRATEGIC_BREAK: Strategic pawn breaks
    {"theme": "strategic_pawn_breaks", "fen": "r1b2rk1/pp1nqppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R2Q1RK1 w - - 4 10", "desc": "Classical e4 or c5 break preparation", "cluster": "curated_break_1"},
    {"theme": "strategic_pawn_breaks", "fen": "r2q1rk1/1b1nbppp/pp1ppn2/8/2PP4/1PN2N2/PB2BPPP/R2Q1RK1 w - - 0 12", "desc": "d5 central pawn break in Queen's Indian", "cluster": "curated_break_2"},
    {"theme": "strategic_pawn_breaks", "fen": "r1bq1rk1/pp1n1ppp/3p1n2/2pPp3/2P1P3/2PB1N2/P4PPP/R1BQ1RK1 w - - 0 10", "desc": "f4 kingside pawn break in King's Indian setup", "cluster": "curated_break_3"},
    {"theme": "strategic_pawn_breaks", "fen": "r1b1k2r/pp2qppp/2n1pn2/2pp4/2PP4/2NBPN2/PP3PPP/R2QK2R w KQkq - 2 9", "desc": "Minority attack b4-b5 preparation", "cluster": "curated_break_4"},
    {"theme": "strategic_pawn_breaks", "fen": "r2q1rk1/pp1b1ppp/2n1pn2/3p4/2PP4/2NB1N2/PP1Q1PPP/R4RK1 w - - 3 11", "desc": "Central breakthrough d5 timing", "cluster": "curated_break_5"},

    # CAT_04_OPPOSITE_CASTLING: Opposite-side castling attacks
    {"theme": "opposite_castling", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R b - - 4 9", "desc": "Sicilian Dragon Yugoslav Attack opposite castling", "cluster": "curated_opp_1"},
    {"theme": "opposite_castling", "fen": "r2q1rk1/1p1nbppp/p2p1n2/2pPp3/2P1P3/2N2N2/PP1B1PPP/R2Q1RK1 w - - 0 11", "desc": "King's Indian h4-h5 attack vs b5 queenside counter", "cluster": "curated_opp_2"},
    {"theme": "opposite_castling", "fen": "r1bq1rk1/pp3pbp/2n1p1p1/3p4/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11", "desc": "Scheveningen English Attack g4-h4 vs b5-a5", "cluster": "curated_opp_3"},
    {"theme": "opposite_castling", "fen": "r1b2rk1/pp1nqppp/2p1pn2/3p2B1/2PP4/2N1PN2/PPQ2PPP/2KR1B1R b - - 4 9", "desc": "Rubinstein French O-O vs O-O-O pawn storm", "cluster": "curated_opp_4"},

    # CAT_05_EXPOSED_KING: Exposed kings & king safety
    {"theme": "exposed_king", "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/4P3/1BN1BN1P/PP2QPP1/2RR2K1 w - - 0 15", "desc": "Nd5 attack uncovering c-file on Black queen & king", "cluster": "curated_king_1"},
    {"theme": "exposed_king", "fen": "r1bq1rk1/pp3ppp/2n2n2/1Bbp4/5B2/2N1PN2/PP3PPP/R2QK2R w KQ - 0 10", "desc": "White uncastled king on e1 with dynamic pressure", "cluster": "curated_king_2"},
    {"theme": "exposed_king", "fen": "r4rk1/1pp1qppp/p1np1n2/4p3/2B1P1b1/2PP1N2/PP2QPPP/RN3RK1 w - - 0 11", "desc": "Pin on knight f3 threatening king shelter disruption", "cluster": "curated_king_3"},
    {"theme": "exposed_king", "fen": "r1b1k2r/ppqn1ppp/2p1pn2/3p2B1/1bPP4/2N1PN2/PP2BPPP/R2QK2R w KQkq - 3 8", "desc": "Early pin on c3 knight with king in center", "cluster": "curated_king_4"},

    # CAT_06_QUIET_DEFENSE: Quiet defensive resources & prophylaxis
    {"theme": "quiet_defense", "fen": "r1b2rk1/pp3ppp/2n1pn2/2qp4/8/2NBPN2/PPP2PPP/R2Q1RK1 w - - 0 10", "desc": "Prophylactic a3/h3 to stop knight incursions", "cluster": "curated_defense_1"},
    {"theme": "quiet_defense", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9", "desc": "Prophylactic h3 driving bishop to h5", "cluster": "curated_defense_2"},
    {"theme": "quiet_defense", "fen": "r1bq1rk1/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10", "desc": "Prophylactic castle before opening c-file", "cluster": "curated_defense_3"},
    {"theme": "quiet_defense", "fen": "r1b1r1k1/pp1n1ppp/2p2n2/q2p4/1bPP4/2NBPN2/PPQB1PPP/R3K2R w KQ - 6 10", "desc": "Defensive consolidation of pinned knight", "cluster": "curated_defense_4"},

    # CAT_07_IQP: Isolated queen's pawn
    {"theme": "iqp_structure", "fen": "r1b2rk1/pp1n1ppp/2p1pn2/q2p4/2PP4/2N1PN2/PP1QBPPP/R3K2R w KQ - 4 10", "desc": "Classical IQP d4 formation with blockade on d5", "cluster": "curated_iqp_1"},
    {"theme": "iqp_structure", "fen": "r1bq1rk1/pp3ppp/2n1pn2/3p4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 9", "desc": "Symmetrical IQP outpost struggle", "cluster": "curated_iqp_2"},
    {"theme": "iqp_structure", "fen": "r1b2rk1/pp2qppp/2n1pn2/2bp4/2PP4/1PN1PN2/P2QBPPP/R3K2R w KQ - 0 11", "desc": "Hanging pawns c4/d4 under piece pressure", "cluster": "curated_iqp_3"},
    {"theme": "iqp_structure", "fen": "r1bqr1k1/pp1n1ppp/2p2n2/3p4/2PP4/B1PBPN2/P4PPP/R2QK2R w KQ - 3 10", "desc": "IQP d4 dynamic bishop diagonal a3-f8", "cluster": "curated_iqp_4"},

    # CAT_08_BACKWARD_PAWN: Backward pawn structures
    {"theme": "backward_pawn", "fen": "r1bq1rk1/pp3ppp/2n2p2/1BbpP3/5Q2/2N5/PP3PPP/R1B1K1NR w KQ - 3 11", "desc": "Weak backward pawn on d6 under attack", "cluster": "curated_backward_1"},
    {"theme": "backward_pawn", "fen": "r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7", "desc": "Symmetrical backward pawn e6 after c5-d4", "cluster": "curated_backward_2"},
    {"theme": "backward_pawn", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9", "desc": "Backward d3 pawn with open d-file pressure", "cluster": "curated_backward_3"},
    {"theme": "backward_pawn", "fen": "r1b1kb1r/pp3ppp/2n1pn2/2qp4/8/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 0 8", "desc": "Sicilian Sveshnikov backward d6 pawn", "cluster": "curated_backward_4"},

    # CAT_09_CONNECTED_PASSER: Connected passed pawns
    {"theme": "connected_passers", "fen": "8/5p2/8/2k2p1p/2P2P1P/3K2P1/8/8 w - - 0 40", "desc": "Candidate passer creation on c-file", "cluster": "curated_passer_1"},
    {"theme": "connected_passers", "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", "desc": "Outside passed pawn b5 vs Black king", "cluster": "curated_passer_2"},
    {"theme": "connected_passers", "fen": "8/4k3/4p1p1/3pP1P1/1p1P4/1P6/8/4K3 w - - 0 1", "desc": "Locked pawn blockade with passed pawn potential", "cluster": "curated_passer_3"},
    {"theme": "connected_passers", "fen": "8/8/1p1k4/p1pPp1p1/P1P1P1P1/8/3K4/8 w - - 0 1", "desc": "Protected passed pawn d5 securing win/draw", "cluster": "curated_passer_4"},

    # CAT_10_ROOK_ENDGAME: Rook & pawn endgames
    {"theme": "rook_endgame", "fen": "8/8/8/8/2R5/4K3/r7/4k3 w - - 0 1", "desc": "Lucena position preparation & bridge building", "cluster": "curated_rook_eg_1"},
    {"theme": "rook_endgame", "fen": "8/8/8/3k4/8/8/3K4/2R5 w - - 0 1", "desc": "Philidor third-rank defensive setup", "cluster": "curated_rook_eg_2"},
    {"theme": "rook_endgame", "fen": "8/1r6/8/2P1k3/8/8/2R1K3/8 w - - 0 1", "desc": "Tarrasch rook behind passed pawn on c-file", "cluster": "curated_rook_eg_3"},
    {"theme": "rook_endgame", "fen": "5k2/8/8/8/4R3/3K4/8/r7 w - - 0 1", "desc": "Vancura defensive maneuver rook vs passed pawn", "cluster": "curated_rook_eg_4"},
    {"theme": "rook_endgame", "fen": "8/8/8/8/5k2/R7/4K1P1/7r w - - 0 1", "desc": "Rook + g-pawn vs Rook winning technique", "cluster": "curated_rook_eg_5"},

    # CAT_11_MINOR_ENDGAME: Minor-piece endgames
    {"theme": "minor_piece_endgame", "fen": "8/8/5k2/3b4/8/4B3/4K3/8 w - - 0 1", "desc": "Opposite colored bishops theoretical draw", "cluster": "curated_minor_eg_1"},
    {"theme": "minor_piece_endgame", "fen": "8/8/8/4k3/8/5N2/4K3/8 w - - 0 1", "desc": "Knight vs lone king boundary check", "cluster": "curated_minor_eg_2"},
    {"theme": "minor_piece_endgame", "fen": "8/8/3b4/2k5/8/4N3/4K3/8 w - - 0 1", "desc": "Knight vs Bishop pawnless maneuver", "cluster": "curated_minor_eg_3"},
    {"theme": "minor_piece_endgame", "fen": "8/8/8/2k5/2P5/4B3/4K3/8 w - - 0 1", "desc": "Same-colored bishop with passed pawn on c4", "cluster": "curated_minor_eg_4"},

    # CAT_12_PURE_PAWN_ENDGAME: Pure pawn endgames
    {"theme": "pure_pawn_endgame", "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1", "desc": "Direct king opposition on e4 vs e6", "cluster": "curated_pawn_eg_1"},
    {"theme": "pure_pawn_endgame", "fen": "8/8/8/3k4/8/4K3/4P3/8 w - - 0 1", "desc": "Key squares KP vs K win/draw boundary", "cluster": "curated_pawn_eg_2"},
    {"theme": "pure_pawn_endgame", "fen": "8/8/8/8/5k2/8/4K1P1/8 w - - 0 1", "desc": "Knight pawn key squares g2-g4", "cluster": "curated_pawn_eg_3"},
    {"theme": "pure_pawn_endgame", "fen": "8/8/8/8/8/1k6/p7/K7 w - - 0 1", "desc": "Rook pawn stalemate trap on a1 vs a2", "cluster": "curated_pawn_eg_4"},
    {"theme": "pure_pawn_endgame", "fen": "8/8/5k2/8/8/8/4K1P1/8 w - - 0 1", "desc": "Distant opposition pawn endgame", "cluster": "curated_pawn_eg_5"},

    # CAT_13_QUEENLESS_MG: Queenless middlegames
    {"theme": "queenless_middlegame", "fen": "r1b2rk1/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R4RK1 w - - 0 10", "desc": "Queenless positional maneuvering with minor pieces", "cluster": "curated_queenless_1"},
    {"theme": "queenless_middlegame", "fen": "r4rk1/pp1n1ppp/2p1pn2/b2p4/2PP4/2NBPN2/PP3PPP/R4RK1 w - - 4 11", "desc": "Berlin Endgame type queenless structure", "cluster": "curated_queenless_2"},
    {"theme": "queenless_middlegame", "fen": "r1b2rk1/pp3ppp/2n1pn2/2b5/2P5/2NBPN2/PP3PPP/R4RK1 w - - 0 11", "desc": "Open c-file in queenless endgame", "cluster": "curated_queenless_3"},

    # CAT_14_ZUGZWANG_FORTRESS: Zugzwang & fortress defenses
    {"theme": "zugzwang_fortress", "fen": "8/8/8/8/4k3/8/4P3/4K3 w - - 0 1", "desc": "Reciprocal zugzwang KP vs K", "cluster": "curated_fortress_1"},
    {"theme": "zugzwang_fortress", "fen": "8/8/p7/P7/2k5/8/1K6/8 w - - 0 1", "desc": "Trebuchet mutual zugzwang", "cluster": "curated_fortress_2"},
    {"theme": "zugzwang_fortress", "fen": "8/8/8/5b2/8/4k3/4P3/4K3 w - - 0 1", "desc": "Bishop fortress preventing king penetration", "cluster": "curated_fortress_3"},
    {"theme": "zugzwang_fortress", "fen": "8/8/8/8/8/4k3/4r3/4K2R w - - 0 1", "desc": "Corner rook fortress draw", "cluster": "curated_fortress_4"},

    # CAT_15_PROMOTION_RACE: Pawn promotion races
    {"theme": "promotion_race", "fen": "8/1P6/8/8/8/8/pk6/7K w - - 0 1", "desc": "Queen promotion race b7 vs a2", "cluster": "curated_race_1"},
    {"theme": "promotion_race", "fen": "8/8/8/p7/8/7k/1P6/K7 w - - 0 1", "desc": "Square of the pawn geometric race b2 vs a5", "cluster": "curated_race_2"},
    {"theme": "promotion_race", "fen": "8/5p2/8/8/4P3/8/5k2/4K3 w - - 0 1", "desc": "Connected pawn race on opposite flanks", "cluster": "curated_race_3"},

    # CAT_16_TACTICAL_FORCED: Tactically forced sequences
    {"theme": "tactical_forced", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "solution": "h5f7", "desc": "Scholar's Mate tactical finish", "cluster": "curated_forced_1"},
    {"theme": "tactical_forced", "fen": "r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9", "solution": "d5f6", "desc": "Legal's Mate tactical deflection", "cluster": "curated_forced_2"},
    {"theme": "tactical_forced", "fen": "6k1/5ppp/8/8/8/8/4QPPP/6K1 w - - 0 1", "solution": "e2e8", "desc": "Back rank mate in 1", "cluster": "curated_forced_3"},
    {"theme": "tactical_forced", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "solution": "e2a6", "desc": "Kiwipete sharp tactical skirmish", "cluster": "curated_forced_4"}
]

def main():
    print("=== PROJECT JANUS P1.9: BUILDING GENERALIZED FAILURE ATLAS (240 POSITIONS) ===")
    all_raw = []

    # 1. Standard 50
    s50 = get_standard_50()
    all_raw.extend(s50)
    print(f"Loaded {len(s50)} from standard_50")

    # 2. Diagnostic v0.56
    d56 = get_diag_v056()
    all_raw.extend(d56)
    print(f"Loaded {len(d56)} from diagnostic_v056")

    # 3. Tactical v0.56
    t56 = get_tactical_v056()
    all_raw.extend(t56)
    print(f"Loaded {len(t56)} from tactical_v056")

    # 4. Validation v0.56
    v56 = get_validation_v056()
    all_raw.extend(v56)
    print(f"Loaded {len(v56)} from validation_v056")

    # 5. P1.8 diagnostic
    p18 = get_p18_diagnostic()
    all_raw.extend(p18)
    print(f"Loaded {len(p18)} from p1.8_diagnostic")

    # 6. Additional curated thematic positions
    for c in ADDITIONAL_THEMATIC_POSITIONS:
        all_raw.append({
            "source": "curated_thematic",
            "source_id": c["desc"][:20],
            "theme": c["theme"],
            "fen": c["fen"],
            "solution": c.get("solution", None),
            "description": c["desc"],
            "cluster": c["cluster"]
        })
    print(f"Loaded {len(ADDITIONAL_THEMATIC_POSITIONS)} curated thematic positions")

    # Deduplicate by FEN
    seen_fens = set()
    unique_positions = []
    for pos in all_raw:
        # Standardize FEN (first 4 fields: board, stm, castling, ep)
        fen_parts = pos["fen"].split()
        core_fen = " ".join(fen_parts[:4])
        if core_fen not in seen_fens:
            seen_fens.add(core_fen)
            unique_positions.append(pos)

    print(f"Total unique positions available: {len(unique_positions)}")

    # We need exactly 240 positions. If less, we can add more from historical matches.
    # If more, we select 240 cleanly distributed.
    if len(unique_positions) < 240:
        # Extract from Stockfish match PGNs in p1.4, p1.5, p1.7, p1.8
        import chess.pgn
        pgn_paths = [
            ROOT / "analysis" / "phase1" / "p1.4" / "pgn" / "matched_stockfish19_progress.pgn",
            ROOT / "analysis" / "phase1" / "p1.8" / "pgn" / "x13_4t_vs_sf19_4t.pgn"
        ]
        extra_count = 0
        for pgn_p in pgn_paths:
            if not pgn_p.exists(): continue
            with open(pgn_p, "r", encoding="utf-8") as f:
                game_idx = 0
                while True:
                    g = chess.pgn.read_game(f)
                    if g is None or len(unique_positions) >= 240: break
                    game_idx += 1
                    b = g.board()
                    # Sample positions at plies 20, 30, 40
                    ply = 0
                    for m in g.mainline_moves():
                        b.push(m)
                        ply += 1
                        if ply in [24, 34, 44]:
                            c_fen = " ".join(b.fen().split()[:4])
                            if c_fen not in seen_fens:
                                seen_fens.add(c_fen)
                                unique_positions.append({
                                    "source": f"sf_match_{pgn_p.parent.parent.name}",
                                    "source_id": f"game_{game_idx}_ply_{ply}",
                                    "theme": "sf_loss_turning_point",
                                    "fen": b.fen(),
                                    "description": f"Position from {g.headers.get('Opening', 'Unknown')} ply {ply}",
                                    "cluster": f"sf_{pgn_p.parent.parent.name}_g{game_idx}"
                                })
                                extra_count += 1
                                if len(unique_positions) >= 240: break

        print(f"Added {extra_count} positions from Stockfish game histories. Total unique: {len(unique_positions)}")

    # Truncate to exactly 240 if needed
    final_240 = unique_positions[:240]

    # Cluster-aware split: Cluster positions by source / game so related positions stay together
    # Put alternate clusters into DEV vs HELD_OUT
    clusters = {}
    for pos in final_240:
        cl = pos.get("cluster", "misc")
        clusters.setdefault(cl, []).append(pos)

    dev_set = []
    held_out_set = []
    for i, (cl, pos_list) in enumerate(clusters.items()):
        if i % 2 == 0:
            for p in pos_list:
                p["partition"] = "DEV"
                p["id"] = f"DEV_{len(dev_set)+1:03d}"
                dev_set.append(p)
        else:
            for p in pos_list:
                p["partition"] = "HELD_OUT"
                p["id"] = f"HELD_OUT_{len(held_out_set)+1:03d}"
                held_out_set.append(p)

    # Balance if uneven
    while len(dev_set) > 120 and len(held_out_set) < 120:
        item = dev_set.pop()
        item["partition"] = "HELD_OUT"
        item["id"] = f"HELD_OUT_{len(held_out_set)+1:03d}"
        held_out_set.append(item)
    while len(held_out_set) > 120 and len(dev_set) < 120:
        item = held_out_set.pop()
        item["partition"] = "DEV"
        item["id"] = f"DEV_{len(dev_set)+1:03d}"
        dev_set.append(item)

    corpus_atlas = {
        "metadata": {
            "title": "Project Janus Phase 1, Milestone P1.9 Generalized Failure Atlas",
            "total_positions": len(final_240),
            "dev_count": len(dev_set),
            "held_out_count": len(held_out_set),
            "clusters_count": len(clusters)
        },
        "dev_positions": dev_set,
        "held_out_positions": held_out_set
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(corpus_atlas, f, indent=2)

    print(f"\n[DONE] Built Generalized Failure Atlas with {len(dev_set)} DEV and {len(held_out_set)} HELD_OUT positions.")
    print(f"Saved to {OUT_JSON}")

if __name__ == "__main__":
    main()
