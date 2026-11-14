#!/usr/bin/env python3
"""
reconcile_p118.py
Phase 0 Evidence and Statistical Reconciliation for Milestone P1.19.
Audits all 420 authoritative tournament games and 60 development games from P1.18.
Computes WDL, paired confidence intervals, pentanomial distributions, and verifies SHA-256 hashes.
"""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
P118_RAW = ROOT / "analysis" / "phase1" / "p1.18" / "raw"
P119_RAW = ROOT / "analysis" / "phase1" / "p1.19" / "raw"

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def calc_paired_ci_and_pvalues(pair_scores, z=1.95996):
    n = len(pair_scores)
    if n == 0:
        return 0.0, 0.0, 1.0, 1.0, 1.0
    mean_p = sum(pair_scores) / n
    if n == 1:
        return mean_p, 0.0, 1.0, 1.0, 0.5
    var = sum((x - mean_p) ** 2 for x in pair_scores) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 1e-6
    ci_low = max(0.0, mean_p - z * se)
    ci_high = min(1.0, mean_p + z * se)
    t_stat = (mean_p - 0.5) / se if se > 0 else 0.0
    # One-sided p-value (H1: mean > 0.5)
    p_one_sided = 0.5 * math.erfc(t_stat / math.sqrt(2))
    # Two-sided p-value (H1: mean != 0.5)
    p_two_sided = math.erfc(abs(t_stat) / math.sqrt(2))
    return mean_p, ci_low, ci_high, p_one_sided, p_two_sided

def compute_pentanomial(pair_scores):
    # pair score can be: 0.0 (LL), 0.5 (LD), 1.0 (DD or WL), 1.5 (WD), 2.0 (WW)
    # in unit interval [0, 1], these are 0.0, 0.25, 0.5, 0.75, 1.0
    penta = {0.0: 0, 0.25: 0, 0.5: 0, 0.75: 0, 1.0: 0}
    for s in pair_scores:
        # snap to nearest category
        nearest = min(penta.keys(), key=lambda k: abs(k - s))
        penta[nearest] += 1
    return {
        "LL_0_0": penta[0.0],
        "LD_0_25": penta[0.25],
        "DD_or_WL_0_5": penta[0.5],
        "WD_0_75": penta[0.75],
        "WW_1_0": penta[1.0]
    }

def main():
    print("================================================================================")
    print("PROJECT JANUS — P1.19 PHASE 0: EVIDENCE AND STATISTICAL RECONCILIATION")
    print("================================================================================")

    # 1. Verify Frozen Artifact Hashes
    binaries = {
        "X7_Baseline_1T": (ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe",
                           "86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B"),
        "X12_Baseline_4T": (ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe",
                            "00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059"),
        "X22_Reference_1T": (ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe",
                             "35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C"),
        "X23_Archived_1T": (ROOT / "analysis" / "phase1" / "p1.18" / "control" / "janus_classical_x23.exe",
                            "39E875841B36AC82F464ABC7F31DB19D7CF5ABCD0F15B0A923B086A5BB393E39"),
    }

    hash_audit = {}
    for name, (path, expected) in binaries.items():
        actual = sha256_file(path) if path.exists() else "MISSING"
        match = (actual == expected)
        hash_audit[name] = {"path": str(path), "expected": expected, "actual": actual, "match": match}
        print(f"[{'PASS' if match else 'FAIL'}] {name}: {actual}")

    # 2. Reconcile 420 Authoritative Tournament Games
    tourn_file = P118_RAW / "p118_tournaments_raw.json"
    tourn_reconciled = {}
    with open(tourn_file, "r") as f:
        tdata = json.load(f)

    for mk, mv in tdata.items():
        games = mv["games"]
        n_pairs = len(games) // 2
        pair_scores = []
        cand_name = mv["cand"]

        for p_idx in range(n_pairs):
            g1 = games[2 * p_idx]
            g2 = games[2 * p_idx + 1]

            # In g1, candidate is White
            s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
            # In g2, candidate is Black
            s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)

            pair_scores.append((s1 + s2) / 2.0)

        mean_p, ci_low, ci_high, p_one, p_two = calc_paired_ci_and_pvalues(pair_scores)
        penta = compute_pentanomial(pair_scores)

        tourn_reconciled[mk] = {
            "match_name": mv["match_name"],
            "cand": mv["cand"],
            "ref": mv["ref"],
            "games_count": len(games),
            "score": mv["score"],
            "win_rate": mv["win_rate"],
            "wins": mv["wins"],
            "draws": mv["draws"],
            "losses": mv["losses"],
            "paired_ci": [ci_low, ci_high],
            "p_value_one_sided": p_one,
            "p_value_two_sided": p_two,
            "elo": mv["elo"],
            "pentanomial": penta
        }
        print(f"Match {mk} ({mv['match_name']}): Score {mv['score']}/{len(games)} ({mv['win_rate']:.1f}%), CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%], p_one: {p_one:.4f}, p_two: {p_two:.4f}")

    # 3. Reconcile 60 Development Ablation Games
    dev_file = P118_RAW / "dev_ablations_raw.json"
    dev_reconciled = {}
    with open(dev_file, "r") as f:
        ddata = json.load(f)

    for mk, mv in ddata.items():
        games = mv["games"]
        n_pairs = len(games) // 2
        pair_scores = []

        for p_idx in range(n_pairs):
            g1 = games[2 * p_idx]
            g2 = games[2 * p_idx + 1]
            s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
            s2 = 1.0 if g2["result"] == "0-1" else (0.5 if g2["result"] == "1/2-1/2" else 0.0)
            pair_scores.append((s1 + s2) / 2.0)

        mean_p, ci_low, ci_high, p_one, p_two = calc_paired_ci_and_pvalues(pair_scores)
        penta = compute_pentanomial(pair_scores)

        dev_reconciled[mk] = {
            "match_name": mv["match_name"],
            "cand": mv["cand"],
            "ref": mv["ref"],
            "games_count": len(games),
            "score": mv["score"],
            "win_rate": mv["win_rate"],
            "wins": mv["wins"],
            "draws": mv["draws"],
            "losses": mv["losses"],
            "paired_ci": [ci_low, ci_high],
            "p_value_one_sided": p_one,
            "p_value_two_sided": p_two,
            "elo": mv["elo"],
            "pentanomial": penta
        }
        print(f"Dev {mk} ({mv['match_name']}): Score {mv['score']}/{len(games)} ({mv['win_rate']:.1f}%), CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%], p_one: {p_one:.4f}, p_two: {p_two:.4f}")

    summary = {
        "hash_audit": hash_audit,
        "authoritative_tournaments": tourn_reconciled,
        "development_ablations": dev_reconciled
    }

    out_file = P119_RAW / "p118_reconciliation_summary.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[OK] Phase 0 Reconciliation data written to {out_file}")

if __name__ == "__main__":
    main()
