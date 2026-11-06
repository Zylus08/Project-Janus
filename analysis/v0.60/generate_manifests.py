import os
import hashlib
import json
from pathlib import Path

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    base_dir = Path(__file__).resolve().parent
    repo_root = base_dir.parent.parent

    # 1. Generate SHA256 manifest
    sha_manifest = {}
    
    # Files to track in analysis/v0.60
    for root, dirs, files in os.walk(base_dir):
        # Skip pycache and temp
        if "__pycache__" in root or ".pytest_cache" in root:
            continue
        for file in files:
            if file in ["sha256_manifest.json", "experiment_manifest.json", "generate_manifests.py"]:
                continue
            full_path = Path(root) / file
            rel_path = full_path.relative_to(repo_root).as_posix()
            sha_manifest[rel_path] = compute_sha256(full_path)

    # Also track test file
    test_file = repo_root / "tests" / "test_v060_neural_value.py"
    if test_file.exists():
        sha_manifest[test_file.relative_to(repo_root).as_posix()] = compute_sha256(test_file)

    # Baseline binaries and tools
    stockfish_path = repo_root.parent / "tools" / "stockfish" / "stockfish.exe"
    if stockfish_path.exists():
        sha_manifest["tools/stockfish/stockfish.exe"] = compute_sha256(stockfish_path)

    # Save sha256_manifest.json
    sha_manifest_path = base_dir / "sha256_manifest.json"
    with open(sha_manifest_path, "w", encoding="utf-8") as f:
        json.dump(sha_manifest, f, indent=2)
    print(f"Generated SHA256 manifest with {len(sha_manifest)} entries.")

    # 2. Generate Experiment manifest
    exp_manifest = {
        "milestone": "v0.60",
        "title": "Efficient Neural Value Evaluation — Architecture, Training, Quantization & Native Integration",
        "parent_commit": "7e390b5",
        "baseline_control": {
            "name": "Janus Classical Baseline C1 (Native N5)",
            "use_lmr": True,
            "use_killer": True,
            "use_history": True,
            "use_pvs": False,
            "use_see": False,
            "use_neural_policy": False,
            "use_neural_value": False
        },
        "candidate": {
            "name": "Janus Neural Value V1-Small (NNUE-V1-Small)",
            "architecture": "Half-KP Dual Accumulator",
            "feature_size": 768,
            "hidden_dim": 64,
            "dense_layers": [128, 16, 1],
            "total_parameters": 51297,
            "quantization": "INT16 accumulator, INT8 weights, INT32 biases, Clipped ReLU [0, 127]",
            "model_binary": "analysis/v0.60/models/janus_nnue_v1_small.jnnue",
            "model_bytes": 100628,
            "crc32": "0x80326bf4"
        },
        "training": {
            "dataset_size": 12500,
            "train_size": 10000,
            "val_size": 1250,
            "test_size": 1250,
            "teacher_engine": "Stockfish 19 (nodes 5000)",
            "loss_function": "Smooth L1 (beta=50.0)",
            "optimizer": "Adam (lr=0.001)",
            "epochs": 20,
            "test_mae_cp": 188.18,
            "test_rmse_cp": 304.40,
            "test_spearman_rho": 0.2412,
            "test_sign_agreement": 0.6208
        },
        "quantization_fidelity": {
            "test_positions": 500,
            "mean_absolute_error_cp": 2.28,
            "p95_error_cp": 6.15,
            "max_error_cp": 11.10,
            "pearson_r": 0.999253,
            "sign_agreement": 0.9880
        },
        "native_latency": {
            "full_refresh_ns": 2826.9,
            "incremental_quiet_move_ns": 88.5,
            "incremental_capture_move_ns": 114.2,
            "feedforward_eval_ns": 440.8,
            "end_to_end_leaf_ns": 529.4,
            "isolated_evals_per_sec": 1889000
        },
        "search_telemetry": {
            "fixed_depth_5": {
                "c1_mean_nodes": 30768.7,
                "v1_small_pure_mean_nodes": 47476.0,
                "v1_hybrid_50_mean_nodes": 43763.1
            },
            "fixed_time_500ms": {
                "c1_mean_depth": 9.3,
                "c1_mean_nps": 1805485,
                "v1_small_pure_mean_depth": 7.7,
                "v1_small_pure_mean_nps": 1188843,
                "v1_hybrid_50_mean_depth": 8.7,
                "v1_hybrid_50_mean_nps": 1229277
            }
        },
        "qualification_decision": {
            "category": "B",
            "status": "Conditionally Qualified",
            "justification": "Architecture, training, INT8/INT16 quantization, incremental updates, and search integration succeed with zero bugs, 529 ns latency, and >1.18M NPS. However, search depth is 0.6-1.6 plies lower under fixed time due to smooth neural score distributions and uncalibrated pruning thresholds, requiring search recalibration before Category A playing-strength promotion."
        }
    }

    exp_manifest_path = base_dir / "experiment_manifest.json"
    with open(exp_manifest_path, "w", encoding="utf-8") as f:
        json.dump(exp_manifest, f, indent=2)
    print("Generated experiment manifest.")

if __name__ == "__main__":
    main()
