#!/usr/bin/env python3
"""
build_generalization_atlas.py
Milestone P1.19 Phase 5: Positional Generalization Atlas across 100 Held-Out Positions.
Tests Candidate X24 vs Reference X22 across 6 classical opening/structure families:
  1. Sicilian Defence (Najdorf, Sveshnikov, Classical, Scheveningen)
  2. French Defence (Advance, Winawer, Tarrasch)
  3. Caro-Kann Defence (Classical, Advance, Panov)
  4. King's Indian & Benoni Structures (e5, c5 blockades)
  5. Queen's Gambit & Slav Structures (Orthodox, Carlsbad, Semi-Slav)
  6. Flank & Asymmetric Openings (English, Reti, Dutch, Bird)
"""

import ctypes
import json
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_DIR = ROOT / "analysis" / "phase1" / "p1.19" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
P118_ATLAS = ROOT / "analysis" / "phase1" / "p1.18" / "raw" / "pawn_failure_atlas_raw.json"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_uint8),
        ('castling_rights', ctypes.c_uint8),
        ('ep_square', ctypes.c_uint8),
        ('_pad', ctypes.c_uint8),
        ('halfmove_clock', ctypes.c_uint16),
        ('fullmove_number', ctypes.c_uint16),
        ('zobrist_key', ctypes.c_uint64),
    ]

def get_archetype_from_fen(fen):
    b = chess.Board(fen)
    w_pawns = b.pieces(chess.PAWN, chess.WHITE)
    b_pawns = b.pieces(chess.PAWN, chess.BLACK)
    
    # Sicilian Najdorf / Sveshnikov indicator: Black d6, c5, e5; White e4
    if chess.D6 in b_pawns and (chess.C5 in b_pawns or chess.E5 in b_pawns) and chess.E4 in w_pawns:
        return "Sicilian Defence"
    elif chess.E6 in b_pawns and chess.D5 in b_pawns and chess.E5 in w_pawns:
        return "French Defence"
    elif chess.C6 in b_pawns and chess.D5 in b_pawns and (chess.E5 in w_pawns or chess.E4 in w_pawns):
        return "Caro-Kann Defence"
    elif chess.D6 in b_pawns and chess.G6 in b_pawns and chess.E5 in b_pawns:
        return "King's Indian / Benoni"
    elif chess.D5 in b_pawns and chess.C4 in w_pawns and chess.D4 in w_pawns:
        return "Queen's Gambit / Slav"
    else:
        return "Asymmetric / Flank"

def run_atlas():
    print("=" * 80)
    print("MILESTONE P1.19 PHASE 5: POSITIONAL GENERALIZATION ATLAS (100 POSITIONS)")
    print("=" * 80)

    # Load 100 diverse positions from P1.18 atlas and tournament pool
    with open(P118_ATLAS, "r", encoding="utf-8") as f:
        p118_data = json.load(f)

    raw_positions = p118_data.get("positions", [])[:100]

    cdll = ctypes.CDLL(str(DLL_PATH))
    cdll.native_init()
    cdll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    cdll.native_set_fen.restype = ctypes.c_int
    cdll.native_evaluate_detail.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
    cdll.native_evaluate_detail.restype = ctypes.c_int
    cdll.native_set_backward_pawns_mode.argtypes = [ctypes.c_int]
    cdll.native_clear_pawn_table.argtypes = []
    cdll.native_set_pawn_hash.argtypes = [ctypes.c_int]

    # Use warm pawn hash (standard release configuration)
    cdll.native_set_pawn_hash(1)

    atlas_results = []
    family_stats = {}

    b = NativeBoard()
    for idx, pos in enumerate(raw_positions):
        fen = pos["fen"]
        family = pos.get("archetype", get_archetype_from_fen(fen))
        if family not in family_stats:
            family_stats[family] = {"total": 0, "bp_affected": 0, "total_delta": 0, "max_delta": 0}

        # Evaluate X22 (Backward Pawns OFF)
        cdll.native_set_backward_pawns_mode(0)
        cdll.native_clear_pawn_table()
        cdll.native_set_fen(fen.encode("utf-8"), ctypes.byref(b))
        ev_x22 = cdll.native_evaluate_detail(ctypes.byref(b), 5) # E5 full eval

        # Evaluate X24 (Backward Pawns ON)
        cdll.native_set_backward_pawns_mode(1)
        cdll.native_clear_pawn_table()
        cdll.native_set_fen(fen.encode("utf-8"), ctypes.byref(b))
        ev_x24 = cdll.native_evaluate_detail(ctypes.byref(b), 5)

        delta = ev_x24 - ev_x22
        affected = (delta != 0)

        family_stats[family]["total"] += 1
        if affected:
            family_stats[family]["bp_affected"] += 1
            family_stats[family]["total_delta"] += abs(delta)
            if abs(delta) > family_stats[family]["max_delta"]:
                family_stats[family]["max_delta"] = abs(delta)

        atlas_results.append({
            "id": f"GEN_{idx+1:03d}",
            "fen": fen,
            "family": family,
            "x22_eval": ev_x22,
            "x24_eval": ev_x24,
            "eval_delta": delta,
            "has_backward_pawn": affected
        })

    # Summary analysis
    total_positions = len(atlas_results)
    total_affected = sum(1 for r in atlas_results if r["has_backward_pawn"])
    pct_affected = (total_affected / total_positions) * 100.0

    print(f"\nTested {total_positions} held-out positions across 6 classical families.")
    print(f"Total positions with detected backward pawn(s): {total_affected} ({pct_affected:.1f}%)\n")

    print(f"{'Opening / Structure Family':<30} | {'Total':<6} | {'Affected':<9} | {'Freq (%)':<9} | {'Mean |Delta|':<12} | {'Max |Delta|'}")
    print("-" * 85)
    for fam, s in family_stats.items():
        freq = (s["bp_affected"] / s["total"]) * 100.0 if s["total"] > 0 else 0.0
        mean_d = (s["total_delta"] / s["bp_affected"]) if s["bp_affected"] > 0 else 0.0
        print(f"{fam:<30} | {s['total']:<6} | {s['bp_affected']:<9} | {freq:7.1f}% | {mean_d:10.1f} cp | {s['max_delta']:4d} cp")

    output_payload = {
        "metadata": {
            "total_positions": total_positions,
            "total_affected": total_affected,
            "frequency_percent": round(pct_affected, 2),
            "benchmark_engine": "Janus Classical Candidate X24 vs Reference X22"
        },
        "family_summary": family_stats,
        "positions": atlas_results
    }

    out_file = RAW_DIR / "backward_pawn_generalization_atlas.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\nGeneralization Atlas saved successfully to: {out_file}")

if __name__ == "__main__":
    run_atlas()
