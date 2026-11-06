"""Project Janus v0.60 - Quantization Numerical Audit Script."""

import json
import importlib.util
from pathlib import Path
import chess
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
TRAIN_MODULE = ROOT / "analysis" / "v0.60" / "train_nnue.py"
EXPORT_MODULE = ROOT / "analysis" / "v0.60" / "export_nnue.py"

spec_t = importlib.util.spec_from_file_location("train_nnue_mod", TRAIN_MODULE)
mod_t = importlib.util.module_from_spec(spec_t)
spec_t.loader.exec_module(mod_t)
NNUEValueNet = mod_t.NNUEValueNet
extract_features_v1_small = mod_t.extract_features_v1_small

spec_e = importlib.util.spec_from_file_location("export_nnue_mod", EXPORT_MODULE)
mod_e = importlib.util.module_from_spec(spec_e)
spec_e.loader.exec_module(mod_e)
simulate_quantized_inference = mod_e.simulate_quantized_inference

def run_audit():
    DATA_PATH = ROOT / "analysis" / "v0.60" / "dataset" / "value_test.json"
    MODEL_PT = ROOT / "analysis" / "v0.60" / "models" / "v1_small_best.pt"
    MODEL_BIN = ROOT / "analysis" / "v0.60" / "models" / "janus_nnue_v1_small.jnnue"

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        test_data = json.load(f)[:500]

    model_fp = NNUEValueNet(768, 64, 16, 600.0)
    model_fp.load_state_dict(torch.load(MODEL_PT, map_location="cpu"))
    model_fp.eval()

    fp_scores = []
    q_scores = []

    for rec in test_data:
        b = chess.Board(rec["fen"])
        ft_w, ft_b = extract_features_v1_small(b)
        stm = (b.turn == chess.WHITE)
        f_stm = ft_w if stm else ft_b
        f_nstm = ft_b if stm else ft_w
        x_stm = torch.zeros(768)
        x_nstm = torch.zeros(768)
        x_stm[f_stm] = 1.0
        x_nstm[f_nstm] = 1.0
        with torch.no_grad():
            score_fp = float(model_fp(x_stm.unsqueeze(0), x_nstm.unsqueeze(0))[0])

        score_q = simulate_quantized_inference(MODEL_BIN, b, arch_id=1)
        fp_scores.append(score_fp)
        q_scores.append(score_q)

    fp_arr = np.array(fp_scores)
    q_arr = np.array(q_scores)
    diff = np.abs(fp_arr - q_arr)

    mean_diff = float(np.mean(diff))
    median_diff = float(np.median(diff))
    max_diff = float(np.max(diff))
    p95_diff = float(np.percentile(diff, 95))
    sign_match = float(np.mean(np.sign(fp_arr) == np.sign(q_arr)))
    corr = float(np.corrcoef(fp_arr, q_arr)[0, 1])

    print("=" * 60)
    print("QUANTIZATION NUMERICAL AUDIT (500 Test Positions)")
    print("=" * 60)
    print(f"  Mean Absolute Difference (FP32 vs INT8/INT16): {mean_diff:.2f} cp")
    print(f"  Median Absolute Difference:                   {median_diff:.2f} cp")
    print(f"  Max Absolute Difference:                      {max_diff:.2f} cp")
    print(f"  P95 Absolute Difference:                      {p95_diff:.2f} cp")
    print(f"  Score Sign Agreement:                         {sign_match * 100:.2f}%")
    print(f"  Pearson Correlation:                          {corr:.6f}")
    print("=" * 60)

    results = {
        "num_positions": len(test_data),
        "mean_absolute_diff_cp": mean_diff,
        "median_absolute_diff_cp": median_diff,
        "max_absolute_diff_cp": max_diff,
        "p95_absolute_diff_cp": p95_diff,
        "sign_agreement": sign_match,
        "pearson_correlation": corr,
    }

    out_file = ROOT / "analysis" / "v0.60" / "raw" / "quantization_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_audit()
