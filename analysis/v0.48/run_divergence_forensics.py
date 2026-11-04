"""Project Janus v0.48 - K0/L1 Search Divergence Forensics (Phase E).

Identifies and analyzes every disagreement between K0 and L1 across the 37 diagnostic positions
at depths 2, 3, 4, and 5.
Evaluates:
- Root move and score deltas
- Classification (transposition, alternate equal line, score drift, tactical divergence)
- Stockfish 19 reference move comparison
"""

import json
from pathlib import Path

def run_forensics():
    # Load fixed-depth ladder data from v0.48 decomposition or v0.47 ladder
    ladder_path = Path("analysis/v0.48/raw/performance_decomposition_raw.json")
    if not ladder_path.exists():
        ladder_path = Path("analysis/v0.47/raw/fixed_depth_ladder.json")

    with open(ladder_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Load SF19 reference
    sf_ref_path = Path("analysis/v0.48/reference/stockfish_reference_ladder.json")
    sf_ref = {}
    if sf_ref_path.exists():
        with open(sf_ref_path, "r", encoding="utf-8") as f:
            sf_ref = json.load(f)

    # Map (pos_id, depth) -> {K0: rec, L1: rec}
    paired = {}
    for r in records:
        key = (r["pos_id"], r["depth"])
        if key not in paired:
            paired[key] = {}
        paired[key][r["config"]] = r

    disagreements = []
    score_only_diffs = []
    agreements = []

    for (pos_id, d), cfgs in sorted(paired.items()):
        if "K0" not in cfgs or "L1" not in cfgs:
            continue
        k0 = cfgs["K0"]
        l1 = cfgs["L1"]

        mv_k0 = k0["best_move"]
        mv_l1 = l1["best_move"]
        sc_k0 = k0["score"]
        sc_l1 = l1["score"]

        sf_entry = sf_ref.get(pos_id, {})
        sf_mv = sf_entry.get("reference_move_d14") or sf_entry.get("reference_move_d12")
        sf_score = sf_entry.get("reference_score_d14") or sf_entry.get("reference_score_d12")

        if mv_k0 != mv_l1:
            diff_cp = abs(sc_k0 - sc_l1)
            # Classification
            if diff_cp <= 15:
                cat = "alternate_equal_line"
            elif diff_cp <= 50:
                cat = "minor_score_variance"
            else:
                cat = "tactical_divergence"

            disagreements.append({
                "pos_id": pos_id,
                "depth": d,
                "category": k0.get("category", "unknown"),
                "k0_move": mv_k0,
                "l1_move": mv_l1,
                "k0_score": sc_k0,
                "l1_score": sc_l1,
                "score_diff_cp": diff_cp,
                "k0_nodes": k0["nodes"],
                "l1_nodes": l1["nodes"],
                "node_delta": l1["nodes"] - k0["nodes"],
                "sf19_move": sf_mv,
                "sf19_score": sf_score,
                "k0_matches_sf": (mv_k0 == sf_mv),
                "l1_matches_sf": (mv_l1 == sf_mv),
                "classification": cat,
            })
        else:
            if sc_k0 != sc_l1:
                score_only_diffs.append({
                    "pos_id": pos_id,
                    "depth": d,
                    "move": mv_k0,
                    "k0_score": sc_k0,
                    "l1_score": sc_l1,
                    "score_diff_cp": abs(sc_k0 - sc_l1),
                })
            else:
                agreements.append((pos_id, d))

    out_inv = {
        "total_evaluations": len(paired),
        "total_move_disagreements": len(disagreements),
        "total_score_only_differences": len(score_only_diffs),
        "total_perfect_agreements": len(agreements),
        "disagreements": disagreements,
        "score_only_differences": score_only_diffs,
    }

    raw_out = Path("analysis/v0.48/raw/divergence_inventory.json")
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_out, "w", encoding="utf-8") as f:
        json.dump(out_inv, f, indent=2)

    print(f"Total Evaluations: {len(paired)}", flush=True)
    print(f"Move Disagreements: {len(disagreements)} ({len(disagreements)/len(paired):.1%})", flush=True)
    print(f"Score-Only Differences: {len(score_only_diffs)}", flush=True)
    print(f"Perfect Move+Score Agreements: {len(agreements)}", flush=True)

    print("\n--- Move Disagreements ---", flush=True)
    for d_rec in disagreements:
        print(
            f"  [{d_rec['pos_id']}] d={d_rec['depth']}: K0={d_rec['k0_move']} (sc={d_rec['k0_score']}), "
            f"L1={d_rec['l1_move']} (sc={d_rec['l1_score']}) | SF19={d_rec['sf19_move']} | "
            f"Diff={d_rec['score_diff_cp']}cp [{d_rec['classification']}]",
            flush=True,
        )


if __name__ == "__main__":
    run_forensics()

