#!/usr/bin/env python3
"""
benchmark_feature_families.py
Phase 11: Feature Expansion Research & Quantitative Comparison.
Compares:
- F0: Existing Dual-Perspective Piece-Square-768 (DP-PS-768)
- F1: Standard HalfKP-40960 (Stockfish NNUE Classic)
- F2: King-Bucketed HalfKP-4 (4 Symmetrical King Buckets)
- F3: Compact HalfKP-4096 (64 King Squares x 64 Relative Coordinates)
"""

import sys
import json
import math
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")

FEATURE_FAMILIES = {
    "F0_DP_PS_768": {
        "name": "Janus Dual-Perspective Piece-Square-768",
        "feature_dim": 768,
        "active_features_min": 2,
        "active_features_max": 32,
        "accumulator_width": 128,
        "hidden_width": 32,
        "king_conditioned": False,
        "normal_move_ops": 4, # 2 additions + 2 subtractions max
        "king_move_ops": 4,   # Constant time!
        "king_move_refresh_needed": False,
        "pawn_shelter_encoded": False,
        "king_attack_geometry_encoded": False
    },
    "F1_HalfKP_40960": {
        "name": "Standard HalfKP-40960 (Full King-Piece Conditioning)",
        "feature_dim": 64 * 10 * 64, # 40,960
        "active_features_min": 2,
        "active_features_max": 30,
        "accumulator_width": 128,
        "hidden_width": 32,
        "king_conditioned": True,
        "normal_move_ops": 4,
        "king_move_ops": 16 * 128, # Refresh friendly accumulator (~16 pieces)
        "king_move_refresh_needed": True,
        "pawn_shelter_encoded": True,
        "king_attack_geometry_encoded": True
    },
    "F2_HalfKP_Bucketed_4": {
        "name": "King-Bucketed HalfKP-4 (4 King Quadrants)",
        "feature_dim": 4 * 10 * 64, # 2,560
        "active_features_min": 2,
        "active_features_max": 30,
        "accumulator_width": 128,
        "hidden_width": 32,
        "king_conditioned": True,
        "normal_move_ops": 4,
        "king_move_ops": 16 * 128, # Refresh only when king changes bucket
        "king_move_refresh_needed": True,
        "pawn_shelter_encoded": True,
        "king_attack_geometry_encoded": False # Coarse
    },
    "F3_HalfKP_4096": {
        "name": "Compact HalfKP-4096 (64 King x 64 Relative Geometry)",
        "feature_dim": 64 * 64, # 4,096
        "active_features_min": 2,
        "active_features_max": 32,
        "accumulator_width": 128,
        "hidden_width": 32,
        "king_conditioned": True,
        "normal_move_ops": 4,
        "king_move_ops": 16 * 128,
        "king_move_refresh_needed": True,
        "pawn_shelter_encoded": True,
        "king_attack_geometry_encoded": True
    }
}

def analyze_families():
    print("=" * 85)
    print("PHASE 11: FEATURE EXPANSION ARCHITECTURAL COMPARISON")
    print("=" * 85)
    print(f"{'Feature Family':22s} | {'Dim':8s} | {'Params':10s} | {'Weight Size':12s} | {'King Cond?':10s} | {'King Refresh'}")
    print("-" * 85)

    comparison_results = {}

    for k, d in FEATURE_FAMILIES.items():
        # Parameters calculation:
        # FT weights: feature_dim * accum_width (int16 = 2 bytes)
        # FT bias: accum_width (int16 = 2 bytes)
        # L1 weights: (accum_width * 2) * hidden_width (int8 = 1 byte)
        # L1 bias: hidden_width (int32 = 4 bytes)
        # L2 weights: hidden_width * 1 (int8 = 1 byte)
        # L2 bias: 1 (int32 = 4 bytes)
        ft_params = d["feature_dim"] * d["accumulator_width"]
        l1_params = (d["accumulator_width"] * 2) * d["hidden_width"]
        l2_params = d["hidden_width"] * 1
        total_params = ft_params + l1_params + l2_params + d["accumulator_width"] + d["hidden_width"] + 1

        # Memory in bytes (quantized weights)
        ft_bytes = ft_params * 2 + d["accumulator_width"] * 2
        l1_bytes = l1_params * 1 + d["hidden_width"] * 4
        l2_bytes = l2_params * 1 + 4
        total_bytes = ft_bytes + l1_bytes + l2_bytes
        total_kb = total_bytes / 1024.0
        total_mb = total_kb / 1024.0

        size_str = f"{total_mb:.2f} MB" if total_mb >= 1.0 else f"{total_kb:.1f} KB"

        print(f"{d['name'][:22]:22s} | {d['feature_dim']:8d} | {total_params:10,d} | {size_str:12s} | {str(d['king_conditioned']):10s} | {d['king_move_refresh_needed']}")

        comparison_results[k] = {
            "name": d["name"],
            "feature_dim": d["feature_dim"],
            "total_params": total_params,
            "weight_bytes": total_bytes,
            "weight_size_formatted": size_str,
            "king_conditioned": d["king_conditioned"],
            "pawn_shelter_encoded": d["pawn_shelter_encoded"],
            "king_attack_geometry_encoded": d["king_attack_geometry_encoded"]
        }

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "feature_expansion_study.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, indent=2)

    print(f"\nFeature study saved to: {out_file}")

if __name__ == "__main__":
    analyze_families()
