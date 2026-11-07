"""Project Janus v0.63 - Phase 0 Cross-Milestone Evidence Reconciliation.

Reconstructs and verifies telemetry, opening suites, and heterogeneity between:
- v0.61 tournament: 114.0/200 (71W / 86D / 43L) on independent_openings_v056.json
- v0.62 confirmatory tournament: 98.5/200 (51W / 95D / 54L) on independent_openings_v062.json
"""

import json
import math
import random
import hashlib
from pathlib import Path
import chess


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def student_t_pvalue(t: float, df: int) -> float:
    # Accurate two-tailed p-value for Student-t
    x = df / (df + t * t)
    # Using incomplete beta or normal approximation for large df (df=99)
    # For df=99, Cornish-Fisher / Hill expansion gives 5 decimals precision
    # Normal approximation with df correction:
    z = abs(t) * (1.0 - 1.0 / (4.0 * df))
    p_norm = 2.0 * (1.0 - normal_cdf(z))
    return p_norm


def chi2_1df_pvalue(q: float) -> float:
    if q <= 0:
        return 1.0
    return 2.0 * (1.0 - normal_cdf(math.sqrt(q)))

ROOT = Path(__file__).resolve().parents[2]
V61_RAW = ROOT / "analysis" / "v0.61" / "raw" / "v061_v2_vs_c1_match_raw.json"
V62_RAW = ROOT / "analysis" / "v0.62" / "raw" / "v062_confirmatory_match_raw.json"
V61_PGN = ROOT / "analysis" / "v0.61" / "pgn" / "v061_v2_vs_c1_match.pgn"
V62_PGN = ROOT / "analysis" / "v0.62" / "pgn" / "v062_confirmatory_match.pgn"
V61_OPENINGS = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
V62_OPENINGS = ROOT / "analysis" / "v0.62" / "corpus" / "independent_openings_v062.json"
OUT_DIR = ROOT / "analysis" / "v0.63"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_paired_stats(games, candidate_name_substr="Neural"):
    # Group by pair_id
    pairs = {}
    for g in games:
        pid = g["pair_id"]
        if pid not in pairs:
            pairs[pid] = {}
        # Identify whether candidate was white
        w_name = g.get("white", "")
        cand_white = candidate_name_substr in w_name or g.get("white_is_candidate", False)
        pts = g.get("candidate_points", None)
        if pts is None:
            res = g.get("result", "")
            if res == "1-0":
                pts = 1.0 if cand_white else 0.0
            elif res == "0-1":
                pts = 0.0 if cand_white else 1.0
            else:
                pts = 0.5
        if cand_white:
            pairs[pid]["white"] = pts
        else:
            pairs[pid]["black"] = pts

    pair_diffs = []
    w_pts = 0.0
    b_pts = 0.0
    for pid, pdata in pairs.items():
        w = pdata.get("white", 0.5)
        b = pdata.get("black", 0.5)
        w_pts += w
        b_pts += b
        # Difference = (w + b) - 1.0 (since control gets 2 - (w+b))
        diff = (w + b) - 1.0
        pair_diffs.append(diff)

    n_pairs = len(pair_diffs)
    total_pts = w_pts + b_pts
    n_games = n_pairs * 2
    pct = total_pts / n_games

    mean_d = sum(pair_diffs) / n_pairs
    var_d = sum((d - mean_d) ** 2 for d in pair_diffs) / (n_pairs - 1) if n_pairs > 1 else 0.0
    std_d = math.sqrt(var_d)
    se_d = std_d / math.sqrt(n_pairs)

    t_stat = mean_d / se_d if se_d > 0 else 0.0
    p_val = student_t_pvalue(t_stat, df=n_pairs - 1) if n_pairs > 1 else 1.0

    # Elo
    p_clamped = max(0.001, min(0.999, pct))
    elo = -400.0 * math.log10(1.0 / p_clamped - 1.0)

    # 10,000 bootstrap CI
    random.seed(42)
    b_elos = []
    b_diffs = []
    for _ in range(10000):
        sample = [random.choice(pair_diffs) for _ in range(n_pairs)]
        mean_s = sum(sample) / n_pairs
        b_diffs.append(mean_s)
        # mean_s = 2*p_s - 1 => p_s = (mean_s + 1) / 2
        p_s = max(0.001, min(0.999, (mean_s + 1.0) / 2.0))
        b_elos.append(-400.0 * math.log10(1.0 / p_s - 1.0))

    b_elos.sort()
    b_diffs.sort()
    elo_ci = (round(b_elos[250], 1), round(b_elos[9750], 1))
    diff_ci = (round(b_diffs[250], 4), round(b_diffs[9750], 4))

    return {
        "n_games": n_games,
        "n_pairs": n_pairs,
        "total_points": total_pts,
        "score_pct": pct,
        "white_points": w_pts,
        "black_points": b_pts,
        "mean_pair_diff": mean_d,
        "std_pair_diff": std_d,
        "se_pair_diff": se_d,
        "t_stat": t_stat,
        "p_val": p_val,
        "elo": elo,
        "elo_ci_95": elo_ci,
        "diff_ci_95": diff_ci,
        "pair_diffs": pair_diffs,
    }


def analyze_openings():
    ops_v61 = load_json(V61_OPENINGS)
    ops_v62 = load_json(V62_OPENINGS)

    # Convert each opening to final FEN / EPD
    def get_terminal_epd(op):
        seq = op.get("uci_sequence", op.get("moves", []))
        b = chess.Board()
        for m in seq:
            b.push(chess.Move.from_uci(m))
        return b.epd()

    epds_v61 = {get_terminal_epd(op): op for op in ops_v61}
    epds_v62 = {get_terminal_epd(op): op for op in ops_v62}

    overlap = set(epds_v61.keys()) & set(epds_v62.keys())

    # Sequences
    seqs_v61 = {tuple(op.get("uci_sequence", op.get("moves", []))): op for op in ops_v61}
    seqs_v62 = {tuple(op.get("uci_sequence", op.get("moves", []))): op for op in ops_v62}
    seq_overlap = set(seqs_v61.keys()) & set(seqs_v62.keys())

    # Categories
    def cat_counts(ops):
        counts = {}
        for op in ops:
            c = op.get("category", op.get("eco_category", "UNKNOWN"))
            counts[c] = counts.get(c, 0) + 1
        return counts

    return {
        "v61_count": len(ops_v61),
        "v62_count": len(ops_v62),
        "unique_epd_v61": len(epds_v61),
        "unique_epd_v62": len(epds_v62),
        "exact_epd_overlap_count": len(overlap),
        "exact_seq_overlap_count": len(seq_overlap),
        "v61_categories": cat_counts(ops_v61),
        "v62_categories": cat_counts(ops_v62),
    }


def main():
    print("Reconstructing v0.61 and v0.62 match telemetry...")
    v61_data = load_json(V61_RAW)
    v62_data = load_json(V62_RAW)

    # v0.61 games
    g61 = v61_data.get("games", [])
    g62 = v62_data.get("games", [])

    stats61 = compute_paired_stats(g61, "Neural")
    stats62 = compute_paired_stats(g62, "Neural")

    print("\n--- v0.61 Reconstructed Stats ---")
    print(f"Games: {stats61['n_games']} ({stats61['n_pairs']} pairs)")
    print(f"Points: {stats61['total_points']} ({stats61['score_pct']*100:.2f}%)")
    print(f"Elo: {stats61['elo']:+.1f} [95% CI: {stats61['elo_ci_95']}]")
    print(f"Paired Diff: {stats61['mean_pair_diff']:+.4f} (SE: {stats61['se_pair_diff']:.4f})")
    print(f"t-stat: {stats61['t_stat']:+.4f}, p-val: {stats61['p_val']:.5f}")

    print("\n--- v0.62 Reconstructed Stats ---")
    print(f"Games: {stats62['n_games']} ({stats62['n_pairs']} pairs)")
    print(f"Points: {stats62['total_points']} ({stats62['score_pct']*100:.2f}%)")
    print(f"Elo: {stats62['elo']:+.1f} [95% CI: {stats62['elo_ci_95']}]")
    print(f"Paired Diff: {stats62['mean_pair_diff']:+.4f} (SE: {stats62['se_pair_diff']:.4f})")
    print(f"t-stat: {stats62['t_stat']:+.4f}, p-val: {stats62['p_val']:.5f}")

    # Heterogeneity test
    # Difference between paired means
    diff_of_diffs = stats61["mean_pair_diff"] - stats62["mean_pair_diff"]
    se_diff_of_diffs = math.sqrt(stats61["se_pair_diff"] ** 2 + stats62["se_pair_diff"] ** 2)
    z_hetero = diff_of_diffs / se_diff_of_diffs
    p_hetero = 2.0 * (1.0 - normal_cdf(abs(z_hetero)))

    # Cochran's Q test (k=2)
    # Weights w_i = 1 / se_i^2
    w1 = 1.0 / (stats61["se_pair_diff"] ** 2)
    w2 = 1.0 / (stats62["se_pair_diff"] ** 2)
    sum_w = w1 + w2
    fixed_effect_mean = (w1 * stats61["mean_pair_diff"] + w2 * stats62["mean_pair_diff"]) / sum_w
    q_stat = w1 * (stats61["mean_pair_diff"] - fixed_effect_mean) ** 2 + w2 * (stats62["mean_pair_diff"] - fixed_effect_mean) ** 2
    q_pval = chi2_1df_pvalue(q_stat)

    # I^2 metric
    # I^2 = max(0, (Q - df) / Q)
    i2 = max(0.0, (q_stat - 1) / q_stat) * 100.0 if q_stat > 0 else 0.0

    print("\n--- Between-Experiment Heterogeneity Analysis ---")
    print(f"Effect Difference (d_v61 - d_v62): {diff_of_diffs:+.4f} (SE: {se_diff_of_diffs:.4f})")
    print(f"Elo Difference: {stats61['elo'] - stats62['elo']:+.1f} Elo")
    print(f"Two-sample z-test: z = {z_hetero:+.4f}, p = {p_hetero:.5f}")
    print(f"Cochran's Q: Q = {q_stat:.4f} (df = 1), p = {q_pval:.5f}")
    print(f"Inconsistency I^2: {i2:.1f}%")

    openings_info = analyze_openings()
    print("\n--- Opening Suite Audit ---")
    print(f"v0.61 Openings: {openings_info['v61_count']} ({openings_info['unique_epd_v61']} unique EPDs)")
    print(f"v0.62 Openings: {openings_info['v62_count']} ({openings_info['unique_epd_v62']} unique EPDs)")
    print(f"Exact EPD Overlap: {openings_info['exact_epd_overlap_count']}")
    print(f"Exact UCI Sequence Overlap: {openings_info['exact_seq_overlap_count']}")
    print(f"v0.61 Categories: {openings_info['v61_categories']}")
    print(f"v0.62 Categories: {openings_info['v62_categories']}")

    results = {
        "v61": {
            "n_games": stats61["n_games"],
            "total_points": stats61["total_points"],
            "score_pct": stats61["score_pct"],
            "elo": stats61["elo"],
            "elo_ci_95": stats61["elo_ci_95"],
            "mean_pair_diff": stats61["mean_pair_diff"],
            "se_pair_diff": stats61["se_pair_diff"],
            "t_stat": stats61["t_stat"],
            "p_val": stats61["p_val"],
        },
        "v62": {
            "n_games": stats62["n_games"],
            "total_points": stats62["total_points"],
            "score_pct": stats62["score_pct"],
            "elo": stats62["elo"],
            "elo_ci_95": stats62["elo_ci_95"],
            "mean_pair_diff": stats62["mean_pair_diff"],
            "se_pair_diff": stats62["se_pair_diff"],
            "t_stat": stats62["t_stat"],
            "p_val": stats62["p_val"],
        },
        "heterogeneity": {
            "effect_diff": diff_of_diffs,
            "se_effect_diff": se_diff_of_diffs,
            "elo_diff": stats61["elo"] - stats62["elo"],
            "z_stat": z_hetero,
            "z_p_val": p_hetero,
            "cochrans_q": q_stat,
            "q_p_val": q_pval,
            "i_squared": i2,
        },
        "openings": openings_info,
    }

    out_file = OUT_DIR / "cross_milestone_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved cross-milestone audit to {out_file}")


if __name__ == "__main__":
    main()
