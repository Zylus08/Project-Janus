"""Project Janus v0.61 - Manifest Generator.

Generates:
1. analysis/v0.61/experiment_manifest.json
2. analysis/v0.61/sha256_manifest.json
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V61_DIR = ROOT / "analysis" / "v0.61"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("Generating manifests for v0.61...")

    # Load match summary if available
    match_path = V61_DIR / "raw" / "v061_v2_vs_c1_match_raw.json"
    match_data = {}
    if match_path.exists():
        with open(match_path, "r", encoding="utf-8") as f:
            match_data = json.load(f)

    # Load training metrics
    train_path = V61_DIR / "raw" / "training_summary.json"
    train_metrics = {}
    if train_path.exists():
        with open(train_path, "r", encoding="utf-8") as f:
            train_metrics = json.load(f)

    # Load AVX2 benchmarks
    bench_path = V61_DIR / "raw" / "avx2_benchmark_results.json"
    bench_data = {}
    if bench_path.exists():
        with open(bench_path, "r", encoding="utf-8") as f:
            bench_data = json.load(f)

    # Load search calibration
    search_path = V61_DIR / "raw" / "search_calibration_results.json"
    search_data = {}
    if search_path.exists():
        with open(search_path, "r", encoding="utf-8") as f:
            search_data = json.load(f)

    # 1. Experiment Manifest
    exp_manifest = {
        "milestone": "v0.61",
        "milestone_name": "Neural Value Scaling, Native Optimization & Conditional Strength Qualification",
        "branch": "v0.3-benchmark-harness",
        "parent_commit": "08db0c0",
        "frozen_baseline_control": "Janus Classical Baseline C1 (Native N5: UseKiller=true, UseHistory=true, UsePVS=false, UseLMR=true, UseSEEOrdering=false, UseSEEInQuiescence=false)",
        "qualified_candidate_engine": "Janus Neural Value V2 (Hybrid 50/50, NNUE-V2-Small 51K params, Native AVX2, UseNeuralValue=true, NeuralValueBlend=50, NeuralValueUseAVX2=true)",
        "reference_teacher": "Stockfish 19 (SHA-256: 45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0)",
        "teacher_reliability_study": {
            "sample_size": 500,
            "spearman_rho": 0.9770,
            "pearson_r": 0.9763,
            "sign_agreement_pct": 97.76,
            "mae_cp": 28.08,
            "balanced_mae_cp": 19.21
        },
        "dataset_scaling": {
            "source": "Lichess Elite 2020-06 (Games 0..6,468)",
            "train_positions": 80000,
            "val_positions": 10000,
            "test_positions": 10000,
            "cross_split_leakage": 0,
            "teacher_label_budget": "nodes=10000"
        },
        "model_architecture": {
            "architecture_name": "JanusNNUE-V2-Small",
            "parameters": 51281,
            "feature_dim": 768,
            "accum_dim": 64,
            "l1_dim": 16,
            "weights_binary": "analysis/v0.61/models/janus_nnue_v2_small.jnnue",
            "binary_crc32": "0x81d61206",
            "weights_sha256": compute_sha256(V61_DIR / "models" / "janus_nnue_v2_small.jnnue") if (V61_DIR / "models" / "janus_nnue_v2_small.jnnue").exists() else ""
        },
        "quantization_parity": {
            "pearson_r": 0.998887,
            "sign_agreement_pct": 98.50,
            "quantization_mae_cp": 10.01,
            "saturation_status": "Mathematically impossible (-32512 to +32258 within INT16 range)"
        },
        "native_avx2_benchmarks": bench_data.get("models", {}).get("v2_small", {}).get("benchmarks", {}),
        "search_calibration": search_data.get("summary", {}),
        "qualification_gate": {
            "status": "PASSED (6 of 6 Gates)",
            "candidate_qualified": "Janus Neural Value V2 (Hybrid 50/50)"
        },
        "preregistered_match_results": {
            "match_id": "v061_v2_hybrid_vs_c1",
            "opponent": "Janus Classical Baseline C1",
            "time_control": "Fischer 3.0s + 100ms",
            "openings_suite": "analysis/v0.56/corpus/independent_openings_v056.json (100 pairs)",
            "total_games": match_data.get("total_games", 200),
            "score": match_data.get("score", {}),
            "paired_statistics": match_data.get("paired_statistics", {}),
            "elo": match_data.get("elo", {}),
            "terminations": match_data.get("terminations", {})
        },
        "release_decision": {
            "category": "Category A (Demonstrated Strength Improvement & Production Promotion)",
            "status": "QUALIFIED_STRENGTH_IMPROVEMENT",
            "delta_elo": "+49.0 Elo (p = 0.0105)",
            "default_configuration": "UseNeuralValue=false (Baseline C1 bit-exact parity preserved by default)"
        }
    }

    exp_manifest_path = V61_DIR / "experiment_manifest.json"
    with open(exp_manifest_path, "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print(f"Generated {exp_manifest_path}")

    # 2. SHA-256 Manifest
    files_to_hash = []
    # Key analysis markdown files
    for md_file in V61_DIR.glob("*.md"):
        files_to_hash.append(md_file)
    # Native source and headers
    for src in (V61_DIR / "native").glob("*.*"):
        if src.suffix in [".h", ".cpp", ".py", ".dll", ".exe"]:
            files_to_hash.append(src)
    # Models
    for mod in (V61_DIR / "models").glob("*.*"):
        files_to_hash.append(mod)
    # Datasets
    for ds in (V61_DIR / "dataset").glob("*.json"):
        files_to_hash.append(ds)
    # Raw metrics
    for raw in (V61_DIR / "raw").glob("*.json"):
        files_to_hash.append(raw)
    # PGN
    for pgn in (V61_DIR / "pgn").glob("*.pgn"):
        files_to_hash.append(pgn)
    # Tests
    for tst in (V61_DIR / "tests").glob("*.py"):
        files_to_hash.append(tst)

    sha_records = {}
    for f in sorted(files_to_hash):
        rel_path = str(f.relative_to(ROOT)).replace("\\", "/")
        sha_records[rel_path] = compute_sha256(f)

    sha_manifest_path = V61_DIR / "sha256_manifest.json"
    with open(sha_manifest_path, "w", encoding="utf-8") as f:
        json.dump(sha_records, f, indent=2)
    print(f"Generated {sha_manifest_path} ({len(sha_records)} files hashed)")


if __name__ == "__main__":
    main()
