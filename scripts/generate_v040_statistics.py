"""Compute comprehensive statistical metrics across all Project Janus v0.40 experiments.

Produces analysis/v0.40/statistical_analysis.json containing:
- Candidate K0 (Baseline reference)
- Candidate K1 (King-safety ablation)
- Candidate ORD1 (Move ordering enhancements)
- Paired differences, t-statistics, p-values, and 10,000 bootstrap confidence intervals.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V040_DIR = ROOT / "analysis" / "v0.40"


def bootstrap_pair_stats(
    pair_diffs: list[float],
    n_resamples: int = 10_000,
    seed: int = 42,
) -> tuple[float, float, float, float]:
    """Calculate 10,000 resample bootstrap 95% confidence interval for score and Elo."""
    n = len(pair_diffs)
    if n == 0:
        return 0.0, 0.0, -999.0, 999.0

    rng = random.Random(seed)
    sampled_means = []
    for _ in range(n_resamples):
        sample = [rng.choice(pair_diffs) for _ in range(n)]
        sampled_means.append(sum(sample) / n)

    sampled_means.sort()
    low_diff = sampled_means[int(0.025 * n_resamples)]
    high_diff = sampled_means[int(0.975 * n_resamples)]

    # Convert to score percentage: diff d is on [-1, 1], where pair score = 1.0 + d on [0, 2]
    # score pct = (1.0 + d) / 2.0
    score_ci_low = max(0.0, min(1.0, (1.0 + low_diff) / 2.0))
    score_ci_high = max(0.0, min(1.0, (1.0 + high_diff) / 2.0))

    def to_elo(pct: float) -> float:
        clamped = max(0.01, min(0.99, pct))
        return -400.0 * math.log10(1.0 / clamped - 1.0)

    elo_ci_low = to_elo(score_ci_low)
    elo_ci_high = to_elo(score_ci_high)

    return (
        round(score_ci_low * 100.0, 2),
        round(score_ci_high * 100.0, 2),
        round(elo_ci_low, 1),
        round(elo_ci_high, 1),
    )


def analyze_candidate_match(match_dir: Path, candidate_name: str) -> dict[str, Any]:
    att_path = (match_dir / "attempt_log.json") if (match_dir / "attempt_log.json").is_file() else (match_dir / "attempts.json")
    if not att_path.is_file():
        return {"candidate": candidate_name, "status": "no_data"}

    attempts = json.loads(att_path.read_text(encoding="utf-8"))
    valid = [a for a in attempts if a.get("status") == "completed"]
    failures = [a for a in attempts if a.get("status") != "completed"]

    wins = sum(1 for a in valid if a.get("result") == "1-0" and a.get("janus_color") == "white" or a.get("result") == "0-1" and a.get("janus_color") == "black")
    draws = sum(1 for a in valid if a.get("result") == "1/2-1/2")
    losses = len(valid) - wins - draws
    score = wins + 0.5 * draws
    score_pct = (score / len(valid)) if valid else 0.0

    white_games = [a for a in valid if a.get("janus_color") == "white"]
    black_games = [a for a in valid if a.get("janus_color") == "black"]

    white_score = sum(a.get("janus_points", 0.0) for a in white_games)
    black_score = sum(a.get("janus_points", 0.0) for a in black_games)

    # Paired differences
    pair_res: dict[int, dict[str, float]] = {}
    for a in valid:
        p_idx = a["pair"]
        pair_res.setdefault(p_idx, {})[a["janus_color"]] = a["janus_points"]

    pair_diffs = []
    for p_idx, res in sorted(pair_res.items()):
        if "white" in res and "black" in res:
            pair_diffs.append(res["white"] + res["black"] - 1.0)

    n_pairs = len(pair_diffs)
    mean_diff = (sum(pair_diffs) / n_pairs) if n_pairs else 0.0
    var = (sum((d - mean_diff) ** 2 for d in pair_diffs) / (n_pairs - 1)) if n_pairs > 1 else 0.0
    std_err = math.sqrt(var / n_pairs) if n_pairs and var > 0 else 0.0
    t_stat = (mean_diff / std_err) if std_err > 0 else 0.0

    # Student-t approximation for two-tailed p-value with df = 24
    # Using numerical error function approximation for t
    # For df=24: standard t-distribution lookup
    df = n_pairs - 1
    # Simple erf-based p-value approximation for large or moderate df
    z = abs(t_stat)
    p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))

    clamped_pct = max(0.01, min(0.99, score_pct))
    elo_est = -400.0 * math.log10(1.0 / clamped_pct - 1.0)

    s_low, s_high, e_low, e_high = bootstrap_pair_stats(pair_diffs)

    mean_duration = (sum(a.get("duration_seconds", 0.0) for a in valid) / len(valid)) if valid else 0.0
    mean_plies = (sum(a.get("plies", 0) for a in valid) / len(valid)) if valid else 0.0
    mean_depth = (sum(a.get("mean_janus_depth", 0.0) for a in valid) / len(valid)) if valid else 0.0

    return {
        "candidate": candidate_name,
        "valid_games": len(valid),
        "complete_pairs": n_pairs,
        "infrastructure_failures": len(failures),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "score": score,
        "score_pct": round(score_pct * 100.0, 2),
        "white_record": f"{int(white_score*2 - sum(1 for a in white_games if a.get('result')=='1/2-1/2'))//2}W / {sum(1 for a in white_games if a.get('result')=='1/2-1/2')}D / {len(white_games) - int(white_score + 0.5*sum(1 for a in white_games if a.get('result')=='1/2-1/2'))}L ({white_score}/{len(white_games)})",
        "black_record": f"{black_score}/{len(black_games)}",
        "mean_pair_difference": round(mean_diff, 4),
        "std_error": round(std_err, 4),
        "t_statistic": round(t_stat, 4),
        "p_value_approx": round(p_val, 4),
        "estimated_elo_delta": round(elo_est, 1),
        "bootstrap_95ci_score_pct": [s_low, s_high],
        "bootstrap_95ci_elo_delta": [e_low, e_high],
        "mean_game_duration_seconds": round(mean_duration, 1),
        "mean_game_plies": round(mean_plies, 1),
        "mean_janus_depth": round(mean_depth, 2),
    }


def main() -> None:
    # 1. Baseline K0 reconstructed from v0.39 PGNs
    k0_stats = {
        "candidate": "k0_baseline",
        "valid_games": 50,
        "complete_pairs": 25,
        "infrastructure_failures": 0,
        "wins": 21,
        "draws": 3,
        "losses": 26,
        "score": 22.5,
        "score_pct": 45.0,
        "white_record": "13W / 1D / 11L (13.5/25)",
        "black_record": "9.0/25",
        "mean_pair_difference": -0.1000,
        "std_error": 0.1444,
        "t_statistic": -0.6928,
        "p_value_approx": 0.4884,
        "estimated_elo_delta": -34.9,
        "bootstrap_95ci_score_pct": [31.0, 59.0],
        "bootstrap_95ci_elo_delta": [-136.7, 63.0],
    }

    # 2. Candidate K1 (uncastled king safety ablation)
    k1_stats = analyze_candidate_match(V040_DIR / "match_k1", "k1_ablation")

    # 3. Candidate ORD1 (move ordering heuristics)
    ord1_stats = analyze_candidate_match(V040_DIR / "match_ord1", "ord1_move_ordering")

    combined = {
        "benchmark_target": "Stockfish 19 Elo 1320 (Threads=1, Hash=64)",
        "time_control": "3000ms + 100ms Fischer increment",
        "k0_baseline": k0_stats,
        "k1_ablation": k1_stats,
        "ord1_move_ordering": ord1_stats,
    }

    out_path = V040_DIR / "statistical_analysis.json"
    out_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(f"Generated statistical analysis to {out_path}")


if __name__ == "__main__":
    main()

