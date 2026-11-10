#!/usr/bin/env python3
"""
Generate experiment_manifest.json and sha256_manifest.json for Milestone P1.2.
"""

import json
import hashlib
from pathlib import Path

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
P12_DIR = ROOT / "analysis" / "phase1" / "p1.2"
RAW_DIR = P12_DIR / "raw"
PGN_DIR = P12_DIR / "pgn"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("Generating SHA-256 manifest for P1.2...")
    tracked_files = [
        ROOT / "engine" / "classical_x" / "janus_classical_x.cpp",
        ROOT / "engine" / "classical_x" / "janus_classical_x.exe",
        ROOT / "engine" / "classical_x" / "janus_classical_x.dll",
        P12_DIR / "control" / "janus_classical_x6.cpp",
        P12_DIR / "control" / "janus_classical_x6.exe",
        P12_DIR / "control" / "janus_classical_x6.dll",
        ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe",
        P12_DIR / "P11_EVIDENCE_RECONCILIATION.md",
        P12_DIR / "CONTINUATION_HISTORY_REPORT.md",
        P12_DIR / "DYNAMIC_LMR_REPORT.md",
        P12_DIR / "CLASSICAL_EVALUATION_MODERNIZATION.md",
        P12_DIR / "SEARCH_EVALUATION_FACTORIAL.md",
        P12_DIR / "P12_CORRECTNESS_REPORT.md",
        P12_DIR / "P12_CANDIDATE_SELECTION.md",
        P12_DIR / "CLASSICAL_X7_VS_X6.md",
        P12_DIR / "MATCHED_STOCKFISH19_PROGRESS.md",
        P12_DIR / "FINAL_RESEARCH_DECISION.md",
        RAW_DIR / "continuation_history_raw.json",
        RAW_DIR / "dynamic_lmr_raw.json",
        RAW_DIR / "classical_evaluation_raw.json",
        RAW_DIR / "search_eval_factorial_raw.json",
        RAW_DIR / "correctness_raw.json",
        RAW_DIR / "x7_vs_x6_tournament_raw.json",
        RAW_DIR / "matched_sf19_progress_raw.json",
        PGN_DIR / "x7_vs_x6.pgn",
        PGN_DIR / "matched_sf19_progress.pgn",
    ]

    sha_dict = {}
    for f in tracked_files:
        if f.exists():
            rel_path = f.relative_to(ROOT).as_posix()
            sha = sha256_file(f)
            size = f.stat().st_size
            sha_dict[rel_path] = {
                "sha256": sha,
                "size_bytes": size
            }
            print(f"  {rel_path}: {sha} ({size:,} bytes)")
        else:
            print(f"  [WARNING] File missing: {f}")

    with open(P12_DIR / "sha256_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sha_dict, f, indent=2)
    print(f"Wrote {P12_DIR / 'sha256_manifest.json'}")

    # Build experiment manifest
    exp_manifest = {
        "milestone": "P1.2",
        "program": "Classical Engine Supremacy Program",
        "title": "Classical Search Intelligence, Positional Evaluation & Independent Strength Validation",
        "candidate": "Janus Classical X7",
        "control_p11": "Janus Classical X6",
        "control_baseline": "Classical C1",
        "reference_engine": "Stockfish 19 unrestricted",
        "branch": "phase1/classical-janus",
        "rule1_compliance": "STRICTLY NON-ML (0 neural networks, 0 NNUE, 0 weights, 0 offline fitted models)",
        "phases": {
            "phase0_reconciliation": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/P11_EVIDENCE_RECONCILIATION.md",
                "x6_vs_c1_reconstructed_score": "87.0%",
                "x6_vs_c1_clustered_elo": "+330.2 Elo (95% CI: [+264.6, +421.9])"
            },
            "phase1_continuation_history": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/CONTINUATION_HISTORY_REPORT.md",
                "raw_data": "analysis/phase1/p1.2/raw/continuation_history_raw.json",
                "qualified_mode": "H3 (1-ply + 2-ply conthist, bounded gravity)",
                "node_reduction_vs_h0": "-14,821 nodes (-0.61%)"
            },
            "phase2_dynamic_lmr": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/DYNAMIC_LMR_REPORT.md",
                "raw_data": "analysis/phase1/p1.2/raw/dynamic_lmr_raw.json",
                "qualified_mode": "L3 (Logarithmic dynamic table + conthist modulation)",
                "node_reduction_vs_l0": "-1,263,093 nodes (-52.10%)"
            },
            "phase3_classical_evaluation": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/CLASSICAL_EVALUATION_MODERNIZATION.md",
                "raw_data": "analysis/phase1/p1.2/raw/classical_evaluation_raw.json",
                "qualified_mode": "E5 (Combined: Pawn Structure, Mobility/Coordination, King Safety, Endgame Positional)",
                "evaluation_throughput": "~400,000 evals/sec",
                "anti_symmetry": "VERIFIED (startpos = 0 cp exact)",
                "mate_separation_margin": "27,100 cp"
            },
            "phase4_search_eval_factorial": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/SEARCH_EVALUATION_FACTORIAL.md",
                "raw_data": "analysis/phase1/p1.2/raw/search_eval_factorial_raw.json",
                "cell_1_x6_e0_nodes": 2424545,
                "cell_2_x6_e5_nodes": 3135305,
                "cell_3_x7_e0_nodes": 1149608,
                "cell_4_x7_e5_nodes": 1536046,
                "net_reduction_full_candidate": "-36.65% nodes vs frozen X6"
            },
            "phase5_correctness": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/P12_CORRECTNESS_REPORT.md",
                "raw_data": "analysis/phase1/p1.2/raw/correctness_raw.json",
                "perft_status": "PASS (100% exact across depths 1..4)",
                "bit_exact_x6_parity": "PASS (100% exact match in UCI_Variant X6)"
            },
            "phase6_candidate_selection": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/P12_CANDIDATE_SELECTION.md",
                "frozen_candidate": "Janus Classical X7"
            },
            "phase7_internal_validation": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/CLASSICAL_X7_VS_X6.md",
                "raw_data": "analysis/phase1/p1.2/raw/x7_vs_x6_tournament_raw.json",
                "pgn": "analysis/phase1/p1.2/pgn/x7_vs_x6.pgn",
                "games_played": 100,
                "opening_pairs": 50,
                "x7_score": "67.5% (+57 =21 -22)",
                "clustered_elo_difference": "+127.0 Elo (95% CI: [+60.5, +203.9])",
                "significance": "p = 0.00021"
            },
            "phase8_stockfish19_progress": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/MATCHED_STOCKFISH19_PROGRESS.md",
                "raw_data": "analysis/phase1/p1.2/raw/matched_sf19_progress_raw.json",
                "pgn": "analysis/phase1/p1.2/pgn/matched_sf19_progress.pgn",
                "games_played": 20,
                "mean_survival_plies": 67.6,
                "max_survival_plies": 107
            },
            "phase9_decision": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.2/FINAL_RESEARCH_DECISION.md",
                "decision": "QUALIFIED FOR PRODUCTION PROMOTION",
                "cumulative_elo_vs_c1": "+457.2 Elo"
            }
        }
    }

    with open(P12_DIR / "experiment_manifest.json", "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Wrote {P12_DIR / 'experiment_manifest.json'}")

if __name__ == "__main__":
    main()
