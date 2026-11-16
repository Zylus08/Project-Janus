import os
import sys
import json

def calculate_model_budget():
    repo_root = r"E:\ChessXML\project-janus-phase1"
    
    # Architecture N1: HalfKP-40960 -> 128x2 -> 32 -> 1
    # Inputs: 40960
    # Hidden 1: 128 per perspective (shared weights)
    # Dense 1: 256 -> 32
    # Dense 2: 32 -> 1
    
    ft_inputs = 40960
    ft_units = 128
    ft_weights = ft_inputs * ft_units
    ft_biases = ft_units
    ft_params = ft_weights + ft_biases
    ft_bytes_int16 = ft_params * 2
    
    dense1_inputs = ft_units * 2 # 256
    dense1_outputs = 32
    dense1_weights = dense1_inputs * dense1_outputs # 8192
    dense1_biases = dense1_outputs # 32
    dense1_bytes_weights = dense1_weights * 1 # int8
    dense1_bytes_biases = dense1_biases * 4 # int32
    
    dense2_inputs = 32
    dense2_outputs = 1
    dense2_weights = dense2_inputs * dense2_outputs # 32
    dense2_biases = dense2_outputs # 1
    dense2_bytes_weights = dense2_weights * 1 # int8
    dense2_bytes_biases = dense2_biases * 4 # int32
    
    total_params = ft_params + (dense1_weights + dense1_biases) + (dense2_weights + dense2_biases)
    header_bytes = 64
    total_file_bytes = (header_bytes + ft_bytes_int16 + 
                        dense1_bytes_weights + dense1_bytes_biases + 
                        dense2_bytes_weights + dense2_bytes_biases)
    
    # Cache and stack memory analysis
    max_search_depth = 128
    bytes_per_accumulator = ft_units * 2 * 2 # 128 units * 2 perspectives * 2 bytes = 512 bytes
    stack_bytes_per_thread = max_search_depth * bytes_per_accumulator # 64 KB
    
    report = {
        "architecture_id": "N1_HalfKP_40960_128x2_32_1",
        "feature_transformer": {
            "input_features": ft_inputs,
            "units_per_perspective": ft_units,
            "perspectives_share_weights": True,
            "weight_matrix_shape": [ft_inputs, ft_units],
            "weights_count": ft_weights,
            "biases_count": ft_biases,
            "quantization_type": "int16_t (16-bit signed)",
            "scale": 256.0,
            "size_bytes": ft_bytes_int16,
            "size_mb": round(ft_bytes_int16 / (1024 * 1024), 2)
        },
        "dense_layers": {
            "layer1": {
                "in": dense1_inputs,
                "out": dense1_outputs,
                "weights": dense1_weights,
                "biases": dense1_biases,
                "size_bytes": dense1_bytes_weights + dense1_bytes_biases
            },
            "layer2": {
                "in": dense2_inputs,
                "out": dense2_outputs,
                "weights": dense2_weights,
                "biases": dense2_biases,
                "size_bytes": dense2_bytes_weights + dense2_bytes_biases
            }
        },
        "total_parameters": total_params,
        "quantized_file_size_bytes": total_file_bytes,
        "quantized_file_size_mb": round(total_file_bytes / (1024 * 1024), 2),
        "runtime_cache_footprint": {
            "bytes_per_accumulator": bytes_per_accumulator,
            "max_search_depth": max_search_depth,
            "stack_bytes_per_thread": stack_bytes_per_thread,
            "stack_kb_per_thread": stack_bytes_per_thread / 1024,
            "l1_cache_fit": "Fits within standard 32KB/48KB L1 per 64 plies, 100% fits in 512KB L2 cache",
            "model_weights_l3_residency": "10.0 MB fits completely in CPU L3 cache (16MB - 32MB)"
        }
    }
    
    out_json = os.path.join(repo_root, "analysis/phase2/p2.3/raw/model_budget_audit.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Model budget report written to {out_json}")
    print(f"Total Params: {total_params:,}")
    print(f"File Size: {total_file_bytes:,} bytes ({total_file_bytes/(1024*1024):.2f} MB)")
    print(f"Search Stack per thread: {stack_bytes_per_thread/1024:.1f} KB")

if __name__ == "__main__":
    calculate_model_budget()
