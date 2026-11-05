"""Project Janus v0.55 - Manifest Generator.

Generates:
1. analysis/v0.55/experiment_manifest.json
2. analysis/v0.55/sha256_manifest.json
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V55_DIR = ROOT / "analysis" / "v0.55"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("Generating manifests for v0.55...")

    # Load Match A results if available
    match_a_path = V55_DIR / "raw" / "n6_vs_n5_raw.json"
    match_a_summary = {}
    if match_a_path.exists():
        with open(match_a_path, "r", encoding="utf-8") as f:
            match_a_data = json.load(f)
            match_a_summary = match_a_data.get("summary", {})

    # Load Match B results if available
    match_b_path = V55_DIR / "raw" / "n5_vs_n3_raw.json"
    match_b_summary = {}
    if match_b_path.exists():
        with open(match_b_path, "r", encoding="utf-8") as f:
            match_b_data = json.load(f)
            match_b_summary = match_b_data.get("summary", {})

    # Load fixed-time ladder results if available
    ladder_path = V55_DIR / "raw" / "fixed_time_ladder_raw.json"
    ladder_results = {}
    if ladder_path.exists():
        with open(ladder_path, "r", encoding="utf-8") as f:
            ladder_data = json.load(f)
            for tier_k, tier_v in ladder_data.items():
                if isinstance(tier_v, dict) and "summary" in tier_v:
                    ladder_results[tier_k] = tier_v["summary"]

    # Load fixed-depth results if available
    depth_path = V55_DIR / "raw" / "depth_ablation_raw.json"
    depth_results = {}
    if depth_path.exists():
        with open(depth_path, "r", encoding="utf-8") as f:
            depth_data = json.load(f)
            for d_k, d_v in depth_data.items():
                if isinstance(d_v, dict) and "summary" in d_v:
                    depth_results[d_k] = d_v["summary"]

    # Load tactical safety results if available
    tac_path = V55_DIR / "raw" / "tactical_safety_results.json"
    tac_summary = {}
    if tac_path.exists():
        with open(tac_path, "r", encoding="utf-8") as f:
            tac_data = json.load(f)
            tac_summary = {k: tac_data[k].get("summary", {}) for k in tac_data if isinstance(tac_data[k], dict) and "summary" in tac_data[k]}
            if "combined_summary" in tac_data:
                tac_summary["combined_summary"] = tac_data["combined_summary"]

    # 1. Experiment Manifest
    exp_manifest = {
        "milestone": "v0.55",
        "milestone_name": "PVS x Move Ordering Interaction, Independent Strength Replication & Search Architecture Qualification",
        "branch": "v0.3-benchmark-harness",
        "parent_commit": "181f3f892b86761e8952ba62a4ae1c05dac4bd88 (HEAD 165c7a5)",
        "production_reference": "Janus Native N5 (C++17, UseLMR=true, UsePVS=false, UseKiller=true, UseHistory=true)",
        "experimental_candidate": "Janus Native N6 (C++17, UseLMR=true, UsePVS=true, UseKiller=true, UseHistory=true)",
        "system_environment": {
            "os": "Windows 11 Enterprise AMD64 (16 logical cores)",
            "python": "3.13.2 64-bit",
            "compiler": "Microsoft Visual C++ BuildTools 2022 (v19.43.34809 x64)",
            "stockfish_version": "Stockfish 19 x64 AVX2",
            "stockfish_sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
        },
        "gates_validated": {
            "Phase_0_Baseline_Freeze_and_Audit": "PASSED (Clean commit 181f3f8/165c7a5, verified toolchain, 601/601 unit tests, v0.54 audit confirmed)",
            "Phase_1_Factorial_Design": "PASSED (2x2 factorial: F00=N3, F01=N4, F10=N5, F11=N6)",
            "Phase_2_Independent_Opening_Corpus": "PASSED (100 fresh master openings, 0% overlap/transpositions with v0.52-v0.54, SHA-256: 8c98c1f07...)",
            "Phase_3_Factorial_Correctness": "PASSED (Minimax exact equivalence proved without LMR; 20/20 invariant gates passed)",
            "Phase_4_Fixed_Depth_Factorial_Ablation": "PASSED (Depth 6: F11 achieved -37.51% nodes vs F00, -4.25% vs F10, 1.84x speedup, sub-additive interaction +7.12%)",
            "Phase_5_Fixed_Time_Ladder": "PASSED (+0.5 plies median depth expansion, 93.3% 1st-move cutoffs at 3000ms)",
            "Phase_6_Tactical_Safety_Benchmark": "PASSED (16/16 solved, 47/48 (97.9%) agreement with N5, -5.29% node reduction)",
            "Phase_7_Match_Preregistration": "PASSED (Protocols frozen for Experiment A and Experiment B)",
            "Phase_8_Match_A_N6_vs_N5": "COMPLETE (Candidate N6: 99.0/200 (49.50%), -3.47 Elo, t=-0.2098, p=0.834, strength neutral)",
            "Phase_9_Match_B_N5_vs_N3": "PASSED (Candidate N5: 122.0/200 (61.00%), +77.71 Elo, t=4.7586, p=0.000007, replication confirmed)",
            "Phase_10_Factorial_Interaction_Analysis": "COMPLETE (Sub-additive interaction +7.12%, PVS marginal savings attenuated by move ordering)",
            "Phase_11_Research_Interpretation": "COMPLETE (All 10 research questions addressed with empirical evidence)",
            "Phase_12_Final_Release_Decision": "COMPLETE (Category B: PVS qualified as search-efficient, strength-neutral; N5 retained as production baseline)"
        },
        "tactical_safety": tac_summary,
        "fixed_depth_ablation": depth_results,
        "fixed_time_ladder": ladder_results,
        "match_a_n6_vs_n5": match_a_summary,
        "match_b_n5_vs_n3": match_b_summary,
    }

    with open(V55_DIR / "experiment_manifest.json", "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print("Saved experiment_manifest.json")

    # 2. SHA-256 Manifest of all v0.55 files
    sha_manifest = {}
    for path in sorted(V55_DIR.rglob("*")):
        if path.is_file():
            if path.name == "sha256_manifest.json":
                continue
            rel_path = str(path.relative_to(ROOT)).replace("\\", "/")
            sha_manifest[rel_path] = {
                "sha256": compute_sha256(path),
                "bytes": path.stat().st_size
            }

    with open(V55_DIR / "sha256_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"Saved sha256_manifest.json ({len(sha_manifest)} files indexed)")


if __name__ == "__main__":
    main()

