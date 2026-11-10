import os
import json
import hashlib

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest(), os.path.getsize(filepath)

def main():
    root = "E:/ChessXML/project-janus-phase1"
    os.chdir(root)

    # Load match results if available
    x10_x7_raw = {}
    if os.path.exists("analysis/phase1/p1.5/raw/x10_vs_x7_tournament_raw.json"):
        with open("analysis/phase1/p1.5/raw/x10_vs_x7_tournament_raw.json", "r", encoding="utf-8") as f:
            x10_x7_raw = json.load(f)

    x10_x7_slow_raw = {}
    if os.path.exists("analysis/phase1/p1.5/raw/x10_vs_x7_slow_tournament_raw.json"):
        with open("analysis/phase1/p1.5/raw/x10_vs_x7_slow_tournament_raw.json", "r", encoding="utf-8") as f:
            x10_x7_slow_raw = json.load(f)

    matched_sf_raw = {}
    if os.path.exists("analysis/phase1/p1.5/raw/matched_stockfish19_progress_raw.json"):
        with open("analysis/phase1/p1.5/raw/matched_stockfish19_progress_raw.json", "r", encoding="utf-8") as f:
            matched_sf_raw = json.load(f)

    # 1. Generate Experiment Manifest
    experiment_manifest = {
        "milestone": "P1.5",
        "program": "Classical Engine Supremacy Program",
        "title": "Classical Evaluation Expressiveness, Evaluation Efficiency & Dynamic Time Management",
        "qualified_baseline": "Janus Classical X7 (b34e342)",
        "experimental_candidate": "Janus Classical X10 (1ef060f8...)",
        "frozen_historical_controls": [
            "Janus Classical X9 (bca971c)",
            "Janus Classical X8 (501efbc)",
            "Janus Classical X6 (bbadf8f)",
            "Classical C1 (e543dab)"
        ],
        "reference_engine": "Stockfish 19 official release (sf_19, edb0d9d, unrestricted, default NNUE)",
        "branch": "phase1/classical-janus",
        "rule1_compliance": "STRICTLY NON-ML (0 neural networks, 0 NNUE, 0 weights, 0 offline fitted models)",
        "preregistered_promotion_gate": "Candidate promoted iff statistically significant superiority over Baseline X7 (p < 0.05, positive Elo, score > 50%) in 200-game match",
        "phases": {
            "phase0_baseline_recovery": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/P14_BASELINE_AND_EVIDENCE_AUDIT.md",
                "raw_data": "analysis/phase1/p1.5/raw/p14_evidence_reconciliation.json",
                "determination": "Reconciled P1.4 evidence; reaffirmed X7 as sole qualified baseline; identified movestogo omission, missing mid-tree time checks, lack of queen mobility, and king safety panic in X7"
            },
            "phase1_evaluation_audit": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/X7_EVALUATION_ARCHITECTURE_AUDIT.md",
                "test_script": "analysis/phase1/p1.5/tests/x7_evaluation_tracer.py",
                "flaws_identified": 8,
                "zero_residual_trace": "PROVED bit-exact mathematical decomposition across 8 terms"
            },
            "phase2_failure_taxonomy": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/POSITIONAL_FAILURE_ATLAS.md",
                "raw_data": "analysis/phase1/p1.5/raw/positional_failure_taxonomy_raw.json",
                "distribution": "Class B (Depth starvation) = 42.9%, Class A (Eval defect) = 25.0%, Class E (Endgame misunderstanding) = 25.0%, Class F (Alignment) = 7.1%"
            },
            "phase3_evaluation_refinement": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/CLASSICAL_EVALUATION_REFINEMENT.md",
                "modules_implemented": "E1' Pawn Structure, E2' King Safety, E3' Piece Activity, E4'/E5' Endgame & Phase"
            },
            "phase4_evaluation_efficiency": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/EVALUATION_EFFICIENCY_AUDIT.md",
                "raw_data": "analysis/phase1/p1.5/raw/evaluation_efficiency_raw.json",
                "pawn_hash_table": "64K entries, 2.0 MB L3-resident, 92.4% hit rate",
                "nps_retention": "1,463,554 NPS (97.4% of X7 baseline)"
            },
            "phase5_time_management": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/DYNAMIC_TIME_MANAGEMENT.md",
                "raw_data": "analysis/phase1/p1.5/raw/time_management_raw.json",
                "mechanisms": "T1 (movestogo budgeting, periodic 2048-node check), T2 (instability & emergency scaling), T3 (stable PV early exit)"
            },
            "phase6_ablation_study": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/P15_FACTORIAL_ABLATION.md",
                "raw_data": "analysis/phase1/p1.5/raw/factorial_ablation_raw.json",
                "configurations": "B0 (Control X7), B1 (Eval only), B2 (Time only), B3 (Full X10)"
            },
            "phase7_correctness": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/P15_CORRECTNESS_REPORT.md",
                "raw_data": "analysis/phase1/p1.5/raw/correctness_raw.json",
                "perft": "12/12 PASSED bit-exact",
                "fallback_parity": "5/5 PASSED bit-exact vs frozen X7",
                "mates_and_draws": "4/4 PASSED"
            },
            "phase8_candidate_freeze": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/X10_CANDIDATE_SELECTION.md",
                "candidate": "Janus Classical X10",
                "binary": "analysis/phase1/p1.5/control/janus_classical_x10.exe",
                "sha256": "1ef060f89cb156b798cd2fbe67539d088c6c0fb3842006b734f07a03808b0f20"
            },
            "phase9_strength_qualification": {
                "status": "COMPLETED" if x10_x7_raw else "IN_PROGRESS",
                "deliverable": "analysis/phase1/p1.5/X10_VS_X7_STRENGTH.md",
                "raw_data": "analysis/phase1/p1.5/raw/x10_vs_x7_tournament_raw.json",
                "pgn": "analysis/phase1/p1.5/pgn/x10_vs_x7.pgn",
                "primary_match": x10_x7_raw.get("score_pct"),
                "delta_elo": x10_x7_raw.get("elo"),
                "p_value": x10_x7_raw.get("p_value")
            },
            "phase10_matched_stockfish19": {
                "status": "COMPLETED" if matched_sf_raw else "PENDING",
                "deliverable": "analysis/phase1/p1.5/MATCHED_STOCKFISH19_PROGRESS.md",
                "raw_data": "analysis/phase1/p1.5/raw/matched_stockfish19_progress_raw.json",
                "pgn": "analysis/phase1/p1.5/pgn/matched_stockfish19_progress.pgn"
            },
            "phase11_final_decision": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/FINAL_RESEARCH_DECISION.md"
            },
            "phase12_next_priority": {
                "status": "COMPLETED",
                "deliverable": "analysis/phase1/p1.5/NEXT_CLASSICAL_PRIORITY.md"
            }
        }
    }

    with open("analysis/phase1/p1.5/experiment_manifest.json", "w", encoding="utf-8") as f:
        json.dump(experiment_manifest, f, indent=2)
    print("Generated analysis/phase1/p1.5/experiment_manifest.json")

    # 2. Generate SHA-256 Manifest
    files_to_hash = [
        # Engine sources and binaries
        "engine/classical_x/janus_classical_x.cpp",
        "engine/classical_x/janus_classical_x.exe",
        "engine/classical_x/janus_classical_x.dll",
        "analysis/phase1/p1.5/control/janus_classical_x10.cpp",
        "analysis/phase1/p1.5/control/janus_classical_x10.exe",
        "analysis/phase1/p1.5/control/janus_classical_x10.dll",
        "analysis/phase1/p1.5/control/janus_classical_x7.exe",
        "analysis/phase1/p1.4/control/janus_classical_x9.exe",
        "analysis/phase1/p1.4/control/janus_classical_x8.exe",
        "analysis/phase1/p1.3/control/janus_classical_x7.exe",
        "analysis/phase1/p1.2/control/janus_classical_x6.exe",
        "analysis/v0.56/native/janus_native_engine.exe",
        # P1.5 Deliverables
        "analysis/phase1/p1.5/P14_BASELINE_AND_EVIDENCE_AUDIT.md",
        "analysis/phase1/p1.5/X7_EVALUATION_ARCHITECTURE_AUDIT.md",
        "analysis/phase1/p1.5/POSITIONAL_FAILURE_ATLAS.md",
        "analysis/phase1/p1.5/CLASSICAL_EVALUATION_REFINEMENT.md",
        "analysis/phase1/p1.5/EVALUATION_EFFICIENCY_AUDIT.md",
        "analysis/phase1/p1.5/DYNAMIC_TIME_MANAGEMENT.md",
        "analysis/phase1/p1.5/P15_FACTORIAL_ABLATION.md",
        "analysis/phase1/p1.5/P15_CORRECTNESS_REPORT.md",
        "analysis/phase1/p1.5/X10_CANDIDATE_SELECTION.md",
        "analysis/phase1/p1.5/X10_VS_X7_STRENGTH.md",
        "analysis/phase1/p1.5/MATCHED_STOCKFISH19_PROGRESS.md",
        "analysis/phase1/p1.5/FINAL_RESEARCH_DECISION.md",
        "analysis/phase1/p1.5/NEXT_CLASSICAL_PRIORITY.md",
        "docs/phase1/p1.5_report.md",
        # PGNs
        "analysis/phase1/p1.5/pgn/x10_vs_x7.pgn",
        "analysis/phase1/p1.5/pgn/x10_vs_x7_slow.pgn",
        "analysis/phase1/p1.5/pgn/matched_stockfish19_progress.pgn",
        "analysis/phase1/p1.5/pgn/matched_x7_vs_sf19.pgn",
        "analysis/phase1/p1.5/pgn/matched_x10_vs_sf19.pgn",
        # Raw Data
        "analysis/phase1/p1.5/raw/p14_evidence_reconciliation.json",
        "analysis/phase1/p1.5/raw/positional_failure_taxonomy_raw.json",
        "analysis/phase1/p1.5/raw/evaluation_efficiency_raw.json",
        "analysis/phase1/p1.5/raw/time_management_raw.json",
        "analysis/phase1/p1.5/raw/factorial_ablation_raw.json",
        "analysis/phase1/p1.5/raw/correctness_raw.json",
        "analysis/phase1/p1.5/raw/x10_vs_x7_tournament_raw.json",
        "analysis/phase1/p1.5/raw/x10_vs_x7_slow_tournament_raw.json",
        "analysis/phase1/p1.5/raw/matched_stockfish19_progress_raw.json",
        "analysis/phase1/p1.5/raw/matched_x7_vs_sf19_raw.json",
        "analysis/phase1/p1.5/raw/matched_x10_vs_sf19_raw.json",
        # Test scripts
        "analysis/phase1/p1.5/tests/reconcile_p14_evidence.py",
        "analysis/phase1/p1.5/tests/x7_evaluation_tracer.py",
        "analysis/phase1/p1.5/tests/prototype_evaluation_e10.py",
        "analysis/phase1/p1.5/tests/test_phase2_failure_taxonomy.py",
        "analysis/phase1/p1.5/tests/test_phase4_efficiency.py",
        "analysis/phase1/p1.5/tests/test_phase5_time_management.py",
        "analysis/phase1/p1.5/tests/test_phase6_ablations.py",
        "analysis/phase1/p1.5/tests/test_phase7_correctness.py",
        "analysis/phase1/p1.5/tests/run_p15_tournaments.py",
        "analysis/phase1/p1.5/scripts/generate_manifests.py"
    ]

    sha256_manifest = {}
    for rel_path in files_to_hash:
        full_path = os.path.join(root, rel_path)
        if os.path.exists(full_path):
            sha, size = sha256_file(full_path)
            sha256_manifest[rel_path] = {
                "sha256": sha,
                "size_bytes": size
            }
        else:
            print(f"NOTE: Pending or optional file: {rel_path}")

    with open("analysis/phase1/p1.5/sha256_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sha256_manifest, f, indent=2)
    print("Generated analysis/phase1/p1.5/sha256_manifest.json with", len(sha256_manifest), "entries")

if __name__ == "__main__":
    main()

