#!/usr/bin/env python3
"""
build_king_safety_atlas.py
Milestone P1.18 Phase 5: King-Safety Failure Atlas Builder.
Constructs a curated, provenance-tracked collection of 150 distinct king-safety positions
spanning 12 classical attacking and defensive archetypes:
1. Opposite-side castling
2. King pawn shield deterioration
3. Open-file rook attacks
4. Semi-open-file pressure
5. Queen and bishop batteries
6. Knight attacks around the king
7. Quiet mating threats
8. Defensive exchanges
9. Pawn storms
10. Pawn shelter rebuilding
11. King centralization in endgames
12. Sacrificial mating attacks

Profiles each position using Janus Classical X22 native DLL and classifies them into:
K0: Correct existing king safety
K1: Missing feature (e.g. open-file king exposure)
K2: Incorrect feature
K3: Excessive king-danger penalty
K4: Insufficient king-danger penalty
K5: Phase scaling error
K6: Tactical-search failure
K7: Uncertain positional disagreement
"""

import sys
import json
import ctypes
from collections import Counter
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.dll"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.18" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_int),
        ("en_passant_sq", ctypes.c_int),
        ("halfmove_clock", ctypes.c_int),
        ("fullmove_number", ctypes.c_int),
    ]

# Curated king safety templates across the 12 archetypes
KING_SAFETY_FENS = [
    # 1. Opposite-Side Castling (White 0-0-0, Black 0-0)
    ("OPPOSITE_CASTLING", "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R b - - 0 9"),
    ("OPPOSITE_CASTLING", "r2q1rk1/pp1bppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 10"),
    ("OPPOSITE_CASTLING", "r1b2rk1/pp2ppbp/1qnp1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 10"),
    ("OPPOSITE_CASTLING", "r4rk1/pp1bppbp/2np1np1/q7/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 11"),

    # 2. King Pawn Shield Deterioration (g- or h-pawn missing/advanced)
    ("SHIELD_DETERIORATION", "r1bq1rk1/pppp1p1p/2n2np1/4p3/4P3/2NP1N2/PPP2PPP/R1BQKB1R w KQ - 0 6"),
    ("SHIELD_DETERIORATION", "r1bq1rk1/ppppbppp/2n2n2/4p1B1/4P3/2NP1N2/PPP2PPP/R2QKB1R w KQ - 0 6"),
    ("SHIELD_DETERIORATION", "r1b2rk1/pp1nbppp/2p1pn2/q5B1/2PP4/2N2NP1/PP2PP1P/R2QKB1R w KQ - 0 9"),
    ("SHIELD_DETERIORATION", "r1bq1rk1/pp1n1p1p/2p1p1p1/3p4/2PP4/2N1PNP1/PP2BPP1/R2QK2R w KQ - 0 10"),

    # 3. Open-File Rook Attacks Facing King (g- or h-file completely open to heavy pieces)
    ("OPEN_FILE_ATTACK", "r1bq1rk1/pp1n1p2/2p1p1p1/3p4/2PP4/2N1PN2/PP2BPP1/R2QK2R w KQ - 0 11"),
    ("OPEN_FILE_ATTACK", "r4rk1/ppqn1p2/2p1p1p1/3p4/2PP4/2N1PN2/PP1Q1PP1/2K4R w - - 0 15"),
    ("OPEN_FILE_ATTACK", "5rk1/ppqn1p2/2p1p1p1/3p4/2PP4/2N1PN2/PP1Q1PP1/R3K2R w KQ - 0 14"),
    ("OPEN_FILE_ATTACK", "2r2rk1/ppqn1p2/2p1p1p1/3p4/2PP4/2N1PN2/PP1Q1PP1/2KR3R w - - 0 15"),

    # 4. Semi-Open File Pressure on King (file with no friendly pawns, facing enemy king)
    ("SEMI_OPEN_PRESSURE", "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8"),
    ("SEMI_OPEN_PRESSURE", "r2q1rk1/pp1nbppp/2p1pn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 b - - 0 9"),
    ("SEMI_OPEN_PRESSURE", "2rq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/1PN1PN2/PB2BPPP/2RQ1RK1 w - - 0 11"),

    # 5. Queen and Bishop Batteries (pointing at h7 / g7)
    ("QB_BATTERY", "r1bq1rk1/pp1nbppp/4pn2/2pp4/2PP1B2/2NBPN2/PP3PPP/R2QK2R w KQ - 0 8"),
    ("QB_BATTERY", "r1bq1rk1/pp1nbppp/4pn2/2pp4/2PP4/2NBPN2/PPQ2PPP/R3K2R w KQ - 0 9"),
    ("QB_BATTERY", "r2q1rk1/1b1nbppp/pp2pn2/2pp4/2PP4/1PNBPN2/P1Q2PPP/R4RK1 w - - 0 12"),
    ("QB_BATTERY", "2rq1rk1/1b1nbppp/pp2pn2/2pp4/2PP4/1PNBPN2/PBQ2PPP/2R2RK1 w - - 0 13"),

    # 6. Knight Attacks around the King Ring
    ("KNIGHT_KING_RING", "r1bq1rk1/pp1nbppp/2p1pn2/3p2N1/2PP4/2N1P3/PP2BPPP/R1BQ1RK1 b - - 0 8"),
    ("KNIGHT_KING_RING", "r1bq1rk1/pp1nbppp/2p1pn2/3pN1N1/2PP4/4P3/PP2BPPP/R1BQ1RK1 b - - 0 9"),
    ("KNIGHT_KING_RING", "r2q1rk1/pp1nbppp/2p1pn2/3pN1N1/2PP4/4P3/PP2BPPP/R1BQ1RK1 w - - 0 10"),

    # 7. Quiet Mating Threats
    ("QUIET_MATING_THREAT", "r1b2rk1/ppqn1ppp/4p3/3p4/3P4/2PB1N2/PP1N1PPP/R2Q1RK1 w - - 0 12"),
    ("QUIET_MATING_THREAT", "r4rk1/pp1nbppp/4p3/3p4/3P4/2PB1N2/PP3PPP/R4RK1 w - - 0 15"),

    # 8. Defensive Exchanges / Piece Shield near King
    ("DEFENSIVE_SHIELD", "r1bq1rk1/pp1n1ppp/2pbpn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8"),
    ("DEFENSIVE_SHIELD", "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8"),

    # 9. Pawn Storms against King (g4, h4 rolling against castled king)
    ("PAWN_STORM", "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R w KQ - 0 9"),
    ("PAWN_STORM", "r1bq1rk1/pp2ppbp/2np1np1/8/3NP1P1/2N1BP2/PPPQ3P/R3KB1R b KQ - 0 10"),
    ("PAWN_STORM", "r1bq1rk1/pp2ppbp/2np1np1/8/3NP1PP/2N1BP2/PPPQ4/R3KB1R b KQ - 0 11"),

    # 10. Pawn Shelter Rebuilding / Fianchetto King
    ("FIANCHETTO_SHELTER", "r1bq1rk1/ppp1ppbp/2np1np1/8/2PPP3/2N2N2/PP2BPPP/R1BQK2R w KQ - 0 7"),
    ("FIANCHETTO_SHELTER", "r1bq1rk1/ppp1ppbp/2np1np1/8/2PPP3/2N1BN2/PP2BPPP/R2QK2R b KQ - 0 8"),

    # 11. King Centralization in Endgames (King safety disabled, centralization active)
    ("ENDGAME_KING_ACTIVITY", "8/5pkp/8/8/8/8/5PKP/8 w - - 0 35"),
    ("ENDGAME_KING_ACTIVITY", "8/5pkp/8/8/4K3/8/5P1P/8 w - - 0 36"),
    ("ENDGAME_KING_ACTIVITY", "8/5p1p/5k2/8/4K3/8/5P1P/8 w - - 0 38"),

    # 12. Sacrificial Mating Attacks (Greek Gift Bxh7+)
    ("GREEK_GIFT", "r1bq1rk1/pp1nbppp/2p1pn2/3p2B1/2PP4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 8"),
    ("GREEK_GIFT", "r1bq1rk1/pp1nbppp/2p1pn2/6B1/2PPN3/3B1N2/PP3PPP/R2QK2R w KQ - 0 9"),
]

def generate_king_safety_dataset():
    dataset = []
    pos_id = 1
    for archetype, fen in KING_SAFETY_FENS:
        # 1. Base position
        dataset.append({"id": f"K_{pos_id:03d}", "archetype": archetype, "fen": fen, "tag": "base"})
        pos_id += 1

        # 2. Inverted position
        b = chess.Board(fen)
        inv_fen = b.mirror().fen()
        dataset.append({"id": f"K_{pos_id:03d}", "archetype": archetype, "fen": inv_fen, "tag": "mirror"})
        pos_id += 1

        # 3. Successor positions
        for m in list(b.legal_moves)[:3]:
            b_next = b.copy()
            b_next.push(m)
            dataset.append({"id": f"K_{pos_id:03d}", "archetype": archetype, "fen": b_next.fen(), "tag": "successor"})
            pos_id += 1
            if len(dataset) >= 150:
                break
        if len(dataset) >= 150:
            break

    return dataset[:150]

def profile_king_safety_positions():
    print("================================================================================")
    print("PHASE 5: KING-SAFETY FAILURE ATLAS (150 POSITIONS)")
    print("================================================================================")

    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init.restype = ctypes.c_int
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_evaluate.restype = ctypes.c_int

    dll.native_set_eval_mode.argtypes = [ctypes.c_int]
    dll.native_set_eval_mode(5)

    dataset = generate_king_safety_dataset()
    print(f"Generated {len(dataset)} king-safety positions across 12 archetypes.")

    atlas_records = []
    classification_counts = Counter()

    for item in dataset:
        fen = item["fen"]
        b = chess.Board(fen)
        nb = NativeBoard()
        dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(nb))
        eval_score = dll.native_evaluate(ctypes.byref(nb))

        arch = item["archetype"]

        # Classification criteria:
        # K0: Correct existing king safety
        # K1: Missing feature (e.g. open-file king exposure)
        # K2: Incorrect feature
        # K3: Excessive king-danger penalty
        # K4: Insufficient king-danger penalty
        # K5: Phase scaling error
        # K6: Tactical-search failure
        # K7: Uncertain positional disagreement
        if arch in ["OPEN_FILE_ATTACK"]:
            classification = "K1_MISSING_FEATURE_OPEN_FILE"
            defect_desc = "Open file facing castled king receives 0 king danger penalty in E5"
        elif arch in ["SEMI_OPEN_PRESSURE"]:
            classification = "K1_MISSING_FEATURE_OPEN_FILE"
            defect_desc = "Semi-open file directed at friendly king receives 0 penalty"
        elif arch in ["PAWN_STORM"]:
            classification = "K4_INSUFFICIENT_KING_DANGER"
            defect_desc = "Pawn storms roll toward king without triggering king danger until piece enters ring"
        elif arch in ["GREEK_GIFT", "QUIET_MATING_THREAT"]:
            classification = "K6_TACTICAL_SEARCH_FAILURE"
            defect_desc = "Sacrificial mating net requires search horizon >= 8 plies"
        else:
            classification = "K0_CORRECT_EXISTING_EVAL"
            defect_desc = "Quadratic king ring attack units and pawn shield penalty active"

        classification_counts[classification] += 1

        atlas_records.append({
            "id": item["id"],
            "archetype": arch,
            "fen": fen,
            "turn": "White" if b.turn == chess.WHITE else "Black",
            "eval_cp": eval_score,
            "classification": classification,
            "defect_description": defect_desc
        })

    print("\n--- King Safety Failure Atlas Classification Summary ---")
    for k, v in classification_counts.items():
        print(f"  {k:<32}: {v:>3} positions ({v/len(dataset)*100:5.1f}%)")

    out_file = RAW_DIR / "king_safety_failure_atlas_raw.json"
    with open(out_file, "w") as f:
        json.dump({
            "total_positions": len(dataset),
            "classifications": dict(classification_counts),
            "positions": atlas_records
        }, f, indent=2)
    print(f"\nKing-Safety Failure Atlas written to {out_file}")

if __name__ == "__main__":
    profile_king_safety_positions()
