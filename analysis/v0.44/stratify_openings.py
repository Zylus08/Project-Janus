"""Stratify match results across color, opening family, and tactical sharpness."""
import json
from collections import defaultdict
from pathlib import Path

def run():
    with open("analysis/v0.43/match_replication/match_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    games = data["games"]
    pairs = defaultdict(lambda: {"k0_w": 0, "k0_b": 0, "rfp_w": 0, "rfp_b": 0, "name": ""})

    for g in games:
        p = g["pair"]
        c = g["candidate"]
        col = g["janus_color"]
        pts = g["janus_points"]
        pairs[p]["name"] = g["opening_name"]
        if c == "k0":
            if col == "white": pairs[p]["k0_w"] += pts
            else: pairs[p]["k0_b"] += pts
        elif c == "rfp":
            if col == "white": pairs[p]["rfp_w"] += pts
            else: pairs[p]["rfp_b"] += pts

    # Categorize into 4 major families
    families = {
        "Open & Gambits (1.e4 e5)": [],
        "Semi-Open (Sicilian, French, Caro-Kann, etc.)": [],
        "Closed (1.d4 d5, QG, Slav, Tarrasch)": [],
        "Flank & Indian (English, Reti, Indian Defenses)": [],
    }

    for p, d in sorted(pairs.items()):
        name = d["name"].lower()
        if any(k in name for k in ["gambit", "open game", "giuoco", "ruy lopez", "two knights", "four knights", "vienna"]):
            fam = "Open & Gambits (1.e4 e5)"
        elif any(k in name for k in ["sicilian", "french", "caro-kann", "scandinavian", "pirc", "modern defense", "alekhine"]):
            fam = "Semi-Open (Sicilian, French, Caro-Kann, etc.)"
        elif any(k in name for k in ["queen's gambit", "slav", "tarrasch", "queen's pawn", "horwitz"]):
            fam = "Closed (1.d4 d5, QG, Slav, Tarrasch)"
        else:
            fam = "Flank & Indian (English, Reti, Indian Defenses)"
        
        families[fam].append((p, d))

    strat_summary = {}

    print("=== Opening Family & Color Stratification ===")
    for fam, pair_list in families.items():
        n_pairs = len(pair_list)
        k0_w_pts = sum(d["k0_w"] for _, d in pair_list)
        k0_b_pts = sum(d["k0_b"] for _, d in pair_list)
        rfp_w_pts = sum(d["rfp_w"] for _, d in pair_list)
        rfp_b_pts = sum(d["rfp_b"] for _, d in pair_list)

        k0_total = k0_w_pts + k0_b_pts
        rfp_total = rfp_w_pts + rfp_b_pts

        strat_summary[fam] = {
            "pairs_count": n_pairs,
            "k0_white_score_pct": (k0_w_pts / n_pairs) * 100,
            "rfp_white_score_pct": (rfp_w_pts / n_pairs) * 100,
            "white_delta_pct": ((rfp_w_pts - k0_w_pts) / n_pairs) * 100,
            "k0_black_score_pct": (k0_b_pts / n_pairs) * 100,
            "rfp_black_score_pct": (rfp_b_pts / n_pairs) * 100,
            "black_delta_pct": ((rfp_b_pts - k0_b_pts) / n_pairs) * 100,
            "k0_total_score_pct": (k0_total / (2 * n_pairs)) * 100,
            "rfp_total_score_pct": (rfp_total / (2 * n_pairs)) * 100,
            "total_delta_pct": ((rfp_total - k0_total) / (2 * n_pairs)) * 100,
        }

        print(f"\n{fam} ({n_pairs} pairs):")
        print(f"  White: K0 = {k0_w_pts:.1f}/{n_pairs} ({k0_w_pts/n_pairs*100:.1f}%), RFP = {rfp_w_pts:.1f}/{n_pairs} ({rfp_w_pts/n_pairs*100:.1f}%) | Delta: {rfp_w_pts - k0_w_pts:+.1f}")
        print(f"  Black: K0 = {k0_b_pts:.1f}/{n_pairs} ({k0_b_pts/n_pairs*100:.1f}%), RFP = {rfp_b_pts:.1f}/{n_pairs} ({rfp_b_pts/n_pairs*100:.1f}%) | Delta: {rfp_b_pts - k0_b_pts:+.1f}")
        print(f"  Total: K0 = {k0_total:.1f}/{2*n_pairs} ({k0_total/(2*n_pairs)*100:.1f}%), RFP = {rfp_total:.1f}/{2*n_pairs} ({rfp_total/(2*n_pairs)*100:.1f}%) | Delta: {rfp_total - k0_total:+.1f}")

    out_file = Path("analysis/v0.44/stratification_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(strat_summary, f, indent=2)

if __name__ == "__main__":
    run()

