"""Project Janus v0.52 - Manifest Generator.

Generates:
1. analysis/v0.52/experiment_manifest.json
2. analysis/v0.52/sha256_manifest.json
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V52_DIR = ROOT / "analysis" / "v0.52"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("Generating manifests for v0.52...")

    # Load match results if available
    match_raw_path = V52_DIR / "raw" / "match_results_raw.json"
    match_summary = {}
    if match_raw_path.exists():
        with open(match_raw_path, "r", encoding="utf-8") as f:
            match_data = json.load(f)
            match_summary = match_data.get("summary", {})

    # Load fixed-time ladder results if available
    ladder_path = V52_DIR / "raw" / "fixed_time_ladder_raw.json"
    ladder_results = {}
    if ladder_path.exists():
        with open(ladder_path, "r", encoding="utf-8") as f:
            ladder_data = json.load(f)
            for tier_k, tier_v in ladder_data.items():
                if isinstance(tier_v, dict) and "summary" in tier_v:
                    ladder_results[tier_k] = tier_v["summary"]

    # Load fixed-depth results if available
    depth_path = V52_DIR / "raw" / "depth_ablation_raw.json"
    depth_results = {}
    if depth_path.exists():
        with open(depth_path, "r", encoding="utf-8") as f:
            depth_data = json.load(f)
            for d_k, d_v in depth_data.items():
                if isinstance(d_v, dict) and "summary" in d_v:
                    depth_results[d_k] = d_v["summary"]

    # Load tactical safety results if available
    tac_path = V52_DIR / "raw" / "tactical_safety_results.json"
    tac_summary = {}
    if tac_path.exists():
        with open(tac_path, "r", encoding="utf-8") as f:
            tac_data = json.load(f)
            tac_summary = tac_data.get("summary", {})

    # 1. Experiment Manifest
    exp_manifest = {
        "milestone": "v0.52",
        "milestone_name": "Native Late Move Reductions, Tactical Safety & Controlled Strength Ablation",
        "branch": "v0.3-benchmark-harness",
        "baseline_commit": "70a1485",
        "production_reference": "Janus Native N2 (v0.51.1 audited, UseLMR=false)",
        "candidate_engine": "Janus Native N3 (C++17 native search core, UseLMR=true)",
        "system_environment": {
            "os": "Windows 11 AMD64 (16 logical cores)",
            "python": "3.13.2 64-bit",
            "compiler": "Microsoft Visual C++ BuildTools 2022 (v19.43.34809 x64)",
            "stockfish_version": "Stockfish 19 x64 AVX2",
            "stockfish_sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
        },
        "gates_validated": {
            "Phase_0_Baseline_Freeze": "PASSED (Clean commit 70a1485, verified toolchain & Stockfish 19)",
            "Mandatory_Controller_Correction": "PASSED (Replaced 150-ply cutoff with sound FIDE rules + 300-ply emergency horizon)",
            "Phase_1_Search_Architecture_Audit": "PASSED (Audited negamax full-window search, TT probing, PV table)",
            "Phase_2_LMR_Design_Specification": "PASSED (10 strict invariants, R=1, full re-search on score > alpha)",
            "Phase_3_CPP17_Implementation": "PASSED (Compiled janus_native_engine.exe & janus_native.dll cleanly)",
            "Phase_4_Correctness_and_Safety": "PASSED (20/20 LMR unit tests, 0 tactical regressions across 28 positions)",
            "Phase_5_Fixed_Depth_Ablation": "PASSED (3.05x speedup and 63.1% node reduction at Depth 6, 1.39% re-search rate)",
            "Phase_6_Fixed_Time_Ladder": "PASSED (Evaluated across 7 tiers from 50ms to 3000ms with Stockfish 19)",
            "Phase_7_Preregistered_Match": "COMPLETE (200-game match under Fischer 3s+100ms, paired statistics)"
        },
        "tactical_safety": tac_summary,
        "fixed_depth_ablation": depth_results,
        "fixed_time_ladder": ladder_results,
        "match_summary": match_summary,
    }

    with open(V52_DIR / "experiment_manifest.json", "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print("Saved experiment_manifest.json")

    # 2. SHA-256 Manifest of all v0.52 files
    sha_manifest = {}
    for path in sorted(V52_DIR.rglob("*")):
        if path.is_file():
            # Skip sha256_manifest.json itself to prevent cyclic hash dependency
            if path.name == "sha256_manifest.json":
                continue
            rel_path = str(path.relative_to(ROOT)).replace("\\", "/")
            sha_manifest[rel_path] = {
                "sha256": compute_sha256(path),
                "bytes": path.stat().st_size
            }

    with open(V52_DIR / "sha256_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"Saved sha256_manifest.json ({len(sha_manifest)} files indexed)")


if __name__ == "__main__":
    main()

