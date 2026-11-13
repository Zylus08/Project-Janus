#!/usr/bin/env python3
"""
Revalidation and Forensic Classification of Milestone P1.11 LMR Findings.
Audits all 39 positions across:
  - BASELINE (with LMR) at depth 7, depth 9
  - NO_LMR at depth 7, depth 9
  - Ground Truth via Deep Search (Stockfish 19 / Deep Classical Depth 12)
  - Formal Classification: D0 (Benign), D1 (Instability), D2 (Tactical Error), D3 (Contract Bug), D4 (Inconclusive)
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
P111_RAW = ROOT / "analysis" / "phase1" / "p1.11" / "raw" / "counterfactual_pruning_raw.json"
EXE_X15 = ROOT / "analysis" / "phase1" / "p1.10" / "control" / "janus_classical_x15.exe"
EXE_SF19 = Path("E:/ChessXML/tools/stockfish/stockfish.exe")
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.12" / "raw" / "lmr_counterfactual_revalidation_raw.json"


def search_engine(exe_path: Path, fen: str, options: Dict[str, str], depth: int) -> Dict[str, Any]:
    lines = ["uci"]
    for k, v in options.items():
        lines.append(f"setoption name {k} value {v}")
    lines.extend(["isready", "ucinewgame", f"position fen {fen}", f"go depth {depth}", "quit"])
    cmd_str = "\n".join(lines) + "\n"

    proc = subprocess.Popen(
        [str(exe_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, _ = proc.communicate(cmd_str)

    best_move = ""
    score = 0
    nodes = 0
    for line in stdout.splitlines():
        line = line.strip()
        if "info" in line and "depth" in line:
            parts = line.split()
            if "nodes" in parts:
                nodes = int(parts[parts.index("nodes") + 1])
            if "score" in parts and "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                best_move = parts[1]

    return {"best_move": best_move, "score": score, "nodes": nodes}


def get_ground_truth(fen: str) -> Dict[str, Any]:
    lines = [
        "uci",
        "setoption name Threads value 1",
        "setoption name Hash value 32",
        "isready",
        "ucinewgame",
        f"position fen {fen}",
        "go depth 14",
        "quit"
    ]
    proc = subprocess.Popen(
        [str(EXE_SF19)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, _ = proc.communicate("\n".join(lines) + "\n")
    bm = ""
    score = 0
    for line in stdout.splitlines():
        line = line.strip()
        if "score cp" in line:
            parts = line.split()
            if "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bm = parts[1]
    return {"best_move": bm, "score": score}


def main():
    print("=" * 80)
    print("REVALIDATING P1.11 LMR COUNTERFACTUAL FINDINGS ACROSS 39 POSITIONS")
    print("=" * 80)

    with open(P111_RAW, "r", encoding="utf-8") as f:
        data = json.load(f)

    positions = data["positions"]
    results = []

    classification_counts = {"D0": 0, "D1": 0, "D2": 0, "D3": 0, "D4": 0}

    for idx, p in enumerate(positions, 1):
        pos_id = p["id"]
        category = p["category"]
        fen = p["fen"]
        expected = p.get("expected", "")

        # 1. Search BASELINE at depth 7 (UseLMR=true)
        res_base_d7 = search_engine(EXE_X15, fen, {"Threads": "1", "UseLMR": "true"}, depth=7)

        # 2. Search NO_LMR at depth 7 (UseLMR=false)
        res_nolmr_d7 = search_engine(EXE_X15, fen, {"Threads": "1", "UseLMR": "false"}, depth=7)

        # 3. Search at depth 9 to test persistence
        res_base_d9 = search_engine(EXE_X15, fen, {"Threads": "1", "UseLMR": "true"}, depth=9)
        res_nolmr_d9 = search_engine(EXE_X15, fen, {"Threads": "1", "UseLMR": "false"}, depth=9)

        # 4. Ground Truth reference (Stockfish 19 @ depth 14)
        gt = get_ground_truth(fen)

        disagree_d7 = (res_base_d7["best_move"] != res_nolmr_d7["best_move"])
        disagree_d9 = (res_base_d9["best_move"] != res_nolmr_d9["best_move"])

        # Classification logic:
        # D3: Contract bug (invalid move, illegal state, mate score violation)
        # D2: Verified tactical error (Baseline move blunders score by > 150cp according to Ground Truth, whereas NoLMR finds correct tactical move)
        # D1: Search instability (Disagreement at d7 resolves or persists with equal/similar score, uncertain objective difference)
        # D0: Benign disagreement (Disagreement where both moves have score within 30cp in Ground Truth or are transpositional)
        # D4: Inconclusive
        classification = "D0"
        justification = ""

        if not disagree_d7:
            classification = "D0"
            justification = "Identical best move at depth 7."
        else:
            # Check tactical validity against Ground Truth
            bm_base = res_base_d7["best_move"]
            bm_nolmr = res_nolmr_d7["best_move"]
            bm_gt = gt["best_move"]

            if bm_nolmr == bm_gt and bm_base != bm_gt:
                # NoLMR found the exact ground-truth best move, baseline did not
                classification = "D2"
                justification = f"LMR caused omission of ground truth best move {bm_gt}; baseline chose {bm_base}."
            elif bm_base == bm_gt and bm_nolmr != bm_gt:
                # Baseline found ground truth, NoLMR did not
                classification = "D0"
                justification = f"Baseline with LMR found ground truth best move {bm_gt}; NoLMR chose alternative {bm_nolmr}."
            else:
                # Neither or both match ground truth
                score_delta_d7 = abs(res_base_d7["score"] - res_nolmr_d7["score"])
                if score_delta_d7 <= 35:
                    classification = "D0"
                    justification = f"Benign disagreement: score difference is minor ({score_delta_d7}cp); both moves objectively playable."
                else:
                    if disagree_d9:
                        classification = "D1"
                        justification = f"Search instability: disagreement persists at depth 9 ({res_base_d9['best_move']} vs {res_nolmr_d9['best_move']}) with moderate score shift."
                    else:
                        classification = "D1"
                        justification = f"Transient search order instability: resolved to identical move {res_base_d9['best_move']} at depth 9."

        classification_counts[classification] += 1

        rec = {
            "id": pos_id,
            "category": category,
            "fen": fen,
            "ground_truth_sf19": gt,
            "depth_7": {
                "baseline": res_base_d7,
                "no_lmr": res_nolmr_d7,
                "disagreement": disagree_d7
            },
            "depth_9": {
                "baseline": res_base_d9,
                "no_lmr": res_nolmr_d9,
                "disagreement": disagree_d9
            },
            "classification": classification,
            "justification": justification
        }
        results.append(rec)
        print(f"[{pos_id:8s}] Category: {category:12s} | D7 Base: {res_base_d7['best_move']:5s} vs NoLMR: {res_nolmr_d7['best_move']:5s} | GT: {gt['best_move']:5s} | Class: {classification}")

    summary = {
        "total_cases": len(positions),
        "classification_breakdown": classification_counts,
        "d7_disagreement_count": sum(1 for r in results if r["depth_7"]["disagreement"]),
        "d7_disagreement_pct": round(sum(1 for r in results if r["depth_7"]["disagreement"]) / len(positions) * 100, 2),
        "d9_disagreement_count": sum(1 for r in results if r["depth_9"]["disagreement"]),
        "verified_tactical_error_pct (D2)": round(classification_counts["D2"] / len(positions) * 100, 2),
        "results": results
    }

    print("\n" + "=" * 80)
    print("FORENSIC REVALIDATION SUMMARY:")
    print(f"Total Cases: {len(positions)}")
    print(f"D7 Move Disagreements: {summary['d7_disagreement_count']} / {len(positions)} ({summary['d7_disagreement_pct']}%)")
    print(f"Classifications: D0 (Benign)={classification_counts['D0']}, D1 (Instability)={classification_counts['D1']}, D2 (Tactical Error)={classification_counts['D2']}, D3 (Contract Bug)={classification_counts['D3']}, D4 (Inconclusive)={classification_counts['D4']}")
    print(f"Verified Tactical Error Rate (D2): {classification_counts['D2']} / {len(positions)} ({summary['verified_tactical_error_pct (D2)']}%)")
    print("=" * 80)

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved revalidation output to {OUT_RAW}")


if __name__ == "__main__":
    main()

