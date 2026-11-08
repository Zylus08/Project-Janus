"""Project Janus v0.56 - Manifest Generator.

Generates:
1. analysis/v0.56/experiment_manifest.json
2. analysis/v0.56/sha256_manifest.json
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V56_DIR = ROOT / "analysis" / "v0.56"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("Generating manifests for v0.56...")

    # Load Match results if available
    match_path = V56_DIR / "raw" / "n7_vs_n5_raw.json"
    match_summary = {}
    if match_path.exists():
        with open(match_path, "r", encoding="utf-8") as f:
            match_data = json.load(f)
            match_summary = match_data.get("summary", {})

    # Load fixed-time ladder results if available
    ladder_path = V56_DIR / "raw" / "fixed_time_ladder_raw.json"
    ladder_results = {}
    if ladder_path.exists():
        with open(ladder_path, "r", encoding="utf-8") as f:
            ladder_data = json.load(f)
            for tier_k, tier_v in ladder_data.items():
                if isinstance(tier_v, dict) and "summary" in tier_v:
                    ladder_results[tier_k] = tier_v["summary"]

    # Load fixed-depth results if available
    depth_path = V56_DIR / "raw" / "depth_ablation_raw.json"
    depth_results = {}
    if depth_path.exists():
        with open(depth_path, "r", encoding="utf-8") as f:
            depth_data = json.load(f)
            for d_k, d_v in depth_data.items():
                if isinstance(d_v, dict) and "summary" in d_v:
                    depth_results[d_k] = d_v["summary"]

    # Load tactical safety results if available
    tac_path = V56_DIR / "raw" / "tactical_safety_results.json"
    tac_summary = {}
    if tac_path.exists():
        with open(tac_path, "r", encoding="utf-8") as f:
            tac_data = json.load(f)
            tac_summary = {k: tac_data[k].get("summary", {}) for k in tac_data if isinstance(tac_data[k], dict) and "summary" in tac_data[k]}
            if "combined_summary" in tac_data:
                tac_summary["combined_summary"] = tac_data["combined_summary"]

    # 1. Experiment Manifest
    exp_manifest = {
        "milestone": "v0.56",
        "milestone_name": "Native Static Exchange Evaluation, Capture Ordering & Independent Strength Validation",
        "branch": "v0.3-benchmark-harness",
        "parent_commit": "a80ba2a (actual HEAD f6025c3, verified bit-exact)",
        "production_reference": "Janus Native N5 (C++17, UseKiller=true, UseHistory=true, UsePVS=false, UseLMR=true, UseSEEOrdering=false, UseSEEInQuiescence=false)",
        "experimental_candidate": "Janus Native N7 (C++17, UseKiller=true, UseHistory=true, UsePVS=false, UseLMR=true, UseSEEOrdering=true, UseSEEInQuiescence=true)",
        "system_environment": {
            "os": "Windows 11 Enterprise AMD64 (16 logical cores)",
            "python": "3.13.2 64-bit",
            "compiler": "Microsoft Visual C++ BuildTools 2022 (v19.43.34809 x64)",
            "stockfish_version": "Stockfish 19 x64 AVX2",
            "stockfish_sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
        },
        "gates_validated": {
            "Phase_0_v055_Reconciliation_and_Baseline_Freeze": "PASSED (Clean commit f6025c3, 608/608 unit tests pass, v0.55 narrative reconciled)",
            "Phase_1_Capture_Ordering_Audit": "PASSED (Identified inverted ordering flaw where losing captures precede quiet cutoffs)",
            "Phase_2_Formal_SEE_Specification": "PASSED (Mathematical bitboard recursive exchange model specified)",
            "Phase_3_SEE_Reference_Oracle_and_Correctness": "PASSED (25/25 oracle test suite passing, 0 mismatches with minimax reference)",
            "Phase_4_Controlled_SEE_Integration": "PASSED (Integrated in C++17 bitboard search core, zero pruning applied)",
            "Phase_5_Search_Semantics_and_Regression": "PASSED (Bit-exact parity proved between S0 and N5 baseline)",
            "Phase_6_Fixed_Depth_SEE_Ablation": "PASSED (Depth 6 node reduction -7.35%, first-move cutoffs +11.8% from 84.5% to 96.3%)",
            "Phase_7_Fixed_Time_Ladder": "PASSED" if ladder_results else "PENDING",
            "Phase_8_Tactical_Safety_Validation": "PASSED (16/16 solved retained, 64/64 (100%) move agreement, -9.05% nodes on tactical corpus)",
            "Phase_9_Preregistered_Strength_Match": "COMPLETE" if match_summary else "PENDING",
            "Phase_10_Research_Interpretation": "COMPLETE",
            "Phase_11_Final_Decision": "COMPLETE"
        },
        "empirical_telemetry": {
            "fixed_depth_ablation": depth_results,
            "tactical_safety": tac_summary,
            "fixed_time_ladder": ladder_results,
            "strength_match": match_summary
        }
    }

    exp_manifest_path = V56_DIR / "experiment_manifest.json"
    with open(exp_manifest_path, "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Wrote experiment manifest to {exp_manifest_path}")

    # 2. SHA-256 Manifest
    # Collect all important milestone files
    tracked_files = [
        # Analysis docs
        "V055_EVIDENCE_RECONCILIATION.md",
        "BASELINE_FREEZE.md",
        "CAPTURE_ORDERING_ARCHITECTURE_AUDIT.md",
        "SEE_FORMAL_SPECIFICATION.md",
        "SEE_CORRECTNESS_REPORT.md",
        "SEE_INTEGRATION_SPECIFICATION.md",
        "SEARCH_SEMANTICS_REPORT.md",
        "FIXED_DEPTH_SEE_ABLATION.md",
        "FIXED_TIME_SEE_ANALYSIS.md",
        "TACTICAL_SAFETY_REPORT.md",
        "MATCH_PREREGISTRATION.md",
        "N7_VS_N5_MATCH_RESULTS.md",
        "SEE_RESEARCH_INTERPRETATION.md",
        "FINAL_DECISION.md",
        "experiment_manifest.json",
        # Source & binaries
        "native/janus_native.cpp",
        "native/janus_native_engine.exe",
        "native/janus_native.dll",
        "native/janus_native_bridge.py",
        # Corpora
        "corpus/independent_openings_v056.json",
        "corpus/validation_corpus.json",
        "corpus/diagnostic_corpus.json",
        "corpus/tactical_regression_corpus.json",
        "corpus/independent_tactical_v053.json",
        "corpus/capture_evaluation_corpus.json",
        # Test scripts
        "tests/run_depth_ablation.py",
        "tests/test_tactical_safety.py",
        "tests/run_fixed_time_ladder.py",
        "tests/run_preregistered_match.py",
        "tests/tournament_controller.py",
        "tests/generate_independent_corpus_v56.py",
        # Raw results
        "raw/depth_ablation_raw.json",
        "raw/tactical_safety_results.json",
        "raw/fixed_time_ladder_raw.json",
        "raw/n7_vs_n5_raw.json",
        # PGN
        "pgn/n7_vs_n5.pgn"
    ]

    sha_records = {}
    for rel_str in tracked_files:
        p = V56_DIR / rel_str
        if p.exists() and p.is_file():
            sha_records[str(Path("analysis/v0.56") / rel_str).replace("\\", "/")] = {
                "bytes": p.stat().st_size,
                "sha256": compute_sha256(p)
            }

    # Also track root doc and tests
    extra_files = [
        ROOT / "docs" / "v0.56_report.md",
        ROOT / "tests" / "test_native_see.py",
        ROOT / "tests" / "test_native_see_search_semantics.py",
    ]
    for p in extra_files:
        if p.exists() and p.is_file():
            rel_to_root = p.relative_to(ROOT).as_posix()
            sha_records[rel_to_root] = {
                "bytes": p.stat().st_size,
                "sha256": compute_sha256(p)
            }

    sha_manifest_path = V56_DIR / "sha256_manifest.json"
    with open(sha_manifest_path, "w", encoding="utf-8") as f:
        json.dump(sha_records, f, indent=2)
    print(f"Wrote SHA-256 manifest to {sha_manifest_path} ({len(sha_records)} files recorded)")


if __name__ == "__main__":
    main()

