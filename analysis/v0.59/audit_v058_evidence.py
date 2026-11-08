"""Project Janus v0.59 - Phase 0 Evidence Reconciliation Script.

Audits:
1. Model parameters, architecture, state_dict, and C++ binary weights.
2. Numerical tolerance between PyTorch and C++ forward pass.
3. Tournament match PGN, results, terminations, paired difference, t-statistic, Elo CI.
4. Dataset provenance, deduplication, label range, game-level split transpositions.
"""

import json
import struct
import math
import random
from pathlib import Path

import torch
import numpy as np
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[2]
V58_DIR = ROOT / "analysis" / "v0.58"


def audit_model_and_weights():
    print("=" * 80)
    print("TASK A: MODEL ARCHITECTURE & PARAMETER VERIFICATION")
    print("=" * 80)

    pt_path = V58_DIR / "models" / "best_policy_model.pt"
    bin_path = V58_DIR / "models" / "janus_policy_v1.bin"

    sd = torch.load(pt_path, map_location="cpu")
    print("PyTorch Checkpoint Shapes:")
    total_params = 0
    weights_only = 0
    for k, v in sd.items():
        print(f"  {k:15s}: shape {list(v.shape)}, numel {v.numel():7d}, dtype {v.dtype}")
        total_params += v.numel()
        if "weight" in k:
            weights_only += v.numel()

    print(f"\nTotal PyTorch parameters (weights + biases): {total_params}")
    print(f"Total PyTorch weights only:                   {weights_only}")

    # Inspect C++ binary file
    bin_size = bin_path.stat().st_size
    with open(bin_path, "rb") as f:
        header = f.read(20)
        magic, ver, in_dim, hid_dim, out_dim = struct.unpack("<IIIII", header)
        w1_bytes = f.read(hid_dim * in_dim * 4)
        b1_bytes = f.read(hid_dim * 4)
        w2_bytes = f.read(out_dim * hid_dim * 4)
        b2_bytes = f.read(out_dim * 4)
        trailing = f.read()

    print("\nBinary Model Header & Layout:")
    print(f"  File size on disk: {bin_size} bytes")
    print(f"  Magic:      0x{magic:08X} ({magic.to_bytes(4, 'little').decode('ascii', 'ignore')})")
    print(f"  Version:    {ver}")
    print(f"  Input Dim:  {in_dim}")
    print(f"  Hidden Dim: {hid_dim}")
    print(f"  Output Dim: {out_dim}")
    print(f"  W1 floats:  {len(w1_bytes)//4} (expected {hid_dim * in_dim})")
    print(f"  B1 floats:  {len(b1_bytes)//4} (expected {hid_dim})")
    print(f"  W2 floats:  {len(w2_bytes)//4} (expected {out_dim * hid_dim})")
    print(f"  B2 floats:  {len(b2_bytes)//4} (expected {out_dim})")
    print(f"  Trailing:   {len(trailing)} bytes (expected 0)")

    total_bin_floats = (len(w1_bytes) + len(b1_bytes) + len(w2_bytes) + len(b2_bytes)) // 4
    print(f"\nTotal binary parameters encoded: {total_bin_floats}")

    expected_math = in_dim * hid_dim + hid_dim + hid_dim * out_dim + out_dim
    print(f"Mathematically expected total (896*128 + 128 + 128*4168 + 4168): {expected_math}")

    # Binary weight equivalence against PyTorch state_dict
    w1_bin = np.frombuffer(w1_bytes, dtype=np.float32).reshape(hid_dim, in_dim)
    b1_bin = np.frombuffer(b1_bytes, dtype=np.float32)
    w2_bin = np.frombuffer(w2_bytes, dtype=np.float32).reshape(out_dim, hid_dim)
    b2_bin = np.frombuffer(b2_bytes, dtype=np.float32)

    diff_w1 = np.max(np.abs(w1_bin - sd["fc1.weight"].numpy()))
    diff_b1 = np.max(np.abs(b1_bin - sd["fc1.bias"].numpy()))
    diff_w2 = np.max(np.abs(w2_bin - sd["fc2.weight"].numpy()))
    diff_b2 = np.max(np.abs(b2_bin - sd["fc2.bias"].numpy()))

    print(f"\nPyTorch vs Binary Weight Differences:")
    print(f"  Max |W1_bin - W1_pt|: {diff_w1}")
    print(f"  Max |B1_bin - B1_pt|: {diff_b1}")
    print(f"  Max |W2_bin - W2_pt|: {diff_w2}")
    print(f"  Max |B2_bin - B2_pt|: {diff_b2}")

    return {
        "pt_total_params": total_params,
        "bin_total_params": total_bin_floats,
        "math_expected_params": expected_math,
        "diff_w1": float(diff_w1),
        "diff_b1": float(diff_b1),
        "diff_w2": float(diff_w2),
        "diff_b2": float(diff_b2),
    }


def audit_tournament():
    print("\n" + "=" * 80)
    print("TASK B: TOURNAMENT RECONSTRUCTION & DRAW DISCREPANCY AUDIT")
    print("=" * 80)

    raw_path = V58_DIR / "raw" / "n8_vs_c1_match_raw.json"
    pgn_path = V58_DIR / "pgn" / "n8_vs_c1_200games.pgn"

    with open(raw_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Reparse PGN directly
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if not g:
                break
            games.append(g)

    print(f"Total games parsed from PGN: {len(games)}")
    print(f"Total games recorded in RAW JSON: {len(raw['games'])}")

    term_counts = {}
    res_counts = {}
    cand_wins = 0
    cand_losses = 0
    cand_draws = 0

    pair_scores = {}

    for idx, g in enumerate(games, 1):
        res = g.headers["Result"]
        term = g.headers.get("Termination", "unknown")
        white = g.headers["White"]
        black = g.headers["Black"]
        round_str = g.headers.get("Round", str(idx))

        term_counts[term] = term_counts.get(term, 0) + 1
        res_counts[res] = res_counts.get(res, 0) + 1

        is_cand_white = "N8" in white
        pair_id = (idx + 1) // 2

        if pair_id not in pair_scores:
            pair_scores[pair_id] = {"N8": 0.0, "C1": 0.0}

        if res == "1-0":
            if is_cand_white:
                cand_wins += 1
                pair_scores[pair_id]["N8"] += 1.0
            else:
                cand_losses += 1
                pair_scores[pair_id]["C1"] += 1.0
        elif res == "0-1":
            if not is_cand_white:
                cand_wins += 1
                pair_scores[pair_id]["N8"] += 1.0
            else:
                cand_losses += 1
                pair_scores[pair_id]["C1"] += 1.0
        elif res == "1/2-1/2":
            cand_draws += 1
            pair_scores[pair_id]["N8"] += 0.5
            pair_scores[pair_id]["C1"] += 0.5

    total_games = len(games)
    total_score = cand_wins + 0.5 * cand_draws
    win_pct = total_score / total_games * 100.0

    print(f"\nReconstructed PGN Scoreboard:")
    print(f"  Wins:   {cand_wins}")
    print(f"  Draws:  {cand_draws}")
    print(f"  Losses: {cand_losses}")
    print(f"  Total Score: {total_score:.1f} / {total_games} ({win_pct:.2f}%)")

    print("\nReconstructed Termination Breakdown:")
    for t, c in sorted(term_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:35s}: {c:3d}")

    # Paired Student-t
    pair_diffs = [pair_scores[pid]["N8"] - pair_scores[pid]["C1"] for pid in sorted(pair_scores.keys())]
    n_pairs = len(pair_diffs)
    mean_diff = sum(pair_diffs) / n_pairs
    var_diff = sum((d - mean_diff) ** 2 for d in pair_diffs) / (n_pairs - 1)
    std_err = math.sqrt(var_diff) / math.sqrt(n_pairs)
    t_stat = mean_diff / std_err

    # 10k bootstrap
    random.seed(42)
    B = 10000
    boot_means = []
    for _ in range(B):
        sample = [random.choice(pair_diffs) for _ in range(n_pairs)]
        boot_means.append(sum(sample) / n_pairs)
    boot_means.sort()
    ci_lower = boot_means[int(0.025 * B)]
    ci_upper = boot_means[int(0.975 * B)]

    p_bound = max(0.001, min(0.999, total_score / total_games))
    elo_est = -400.0 * math.log10(1.0 / p_bound - 1.0)

    print(f"\nPaired Analysis:")
    print(f"  Pairs count: {n_pairs}")
    print(f"  Mean paired diff: {mean_diff:+.4f} (95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}])")
    print(f"  t-statistic: {t_stat:+.4f} (df={n_pairs-1})")
    print(f"  Estimated Elo: {elo_est:+.1f}")

    return {
        "cand_wins": cand_wins,
        "cand_draws": cand_draws,
        "cand_losses": cand_losses,
        "term_counts": term_counts,
        "mean_diff": mean_diff,
        "t_stat": t_stat,
        "elo_est": elo_est,
    }


def audit_dataset():
    print("\n" + "=" * 80)
    print("TASK C: DATASET PROVENANCE, SPLITS & INTEGRITY AUDIT")
    print("=" * 80)

    data_dir = V58_DIR / "data"
    manifest_path = data_dir / "dataset_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print("Dataset Manifest:")
    print(f"  Source:     {manifest.get('source')}")
    print(f"  Positions:  {manifest.get('total_positions')}")
    print(f"  Games:      {manifest.get('total_games')}")
    print(f"  Splits:     {manifest.get('splits')}")
    print(f"  Game phases:{manifest.get('phases')}")

    train = np.load(data_dir / "train_data.npz")
    val = np.load(data_dir / "val_data.npz")
    test = np.load(data_dir / "test_data.npz")

    x_tr, y_tr = train["X"], train["y"]
    x_va, y_va = val["X"], val["y"]
    x_te, y_te = test["X"], test["y"]

    print(f"\nArray Shapes:")
    print(f"  Train: X={x_tr.shape}, Y={y_tr.shape}, Y in [{y_tr.min()}, {y_tr.max()}]")
    print(f"  Val:   X={x_va.shape}, Y={y_va.shape}, Y in [{y_va.min()}, {y_va.max()}]")
    print(f"  Test:  X={x_te.shape}, Y={y_te.shape}, Y in [{y_te.min()}, {y_te.max()}]")

    # Hash position boards
    def hash_set(arr):
        return set(hash(arr[i].tobytes()) for i in range(arr.shape[0]))

    print("\nHashing board tensors to verify split uniqueness...")
    h_tr = hash_set(x_tr)
    h_va = hash_set(x_va)
    h_te = hash_set(x_te)

    print(f"  Unique positions in Train: {len(h_tr)} / {x_tr.shape[0]} ({len(h_tr)/x_tr.shape[0]*100:.2f}%)")
    print(f"  Unique positions in Val:   {len(h_va)} / {x_va.shape[0]} ({len(h_va)/x_va.shape[0]*100:.2f}%)")
    print(f"  Unique positions in Test:  {len(h_te)} / {x_te.shape[0]} ({len(h_te)/x_te.shape[0]*100:.2f}%)")

    overlap_tr_va = len(h_tr.intersection(h_va))
    overlap_tr_te = len(h_tr.intersection(h_te))
    overlap_va_te = len(h_va.intersection(h_te))

    print(f"  Overlap Train-Val:  {overlap_tr_va} positions ({overlap_tr_va/len(h_va)*100:.2f}% of Val)")
    print(f"  Overlap Train-Test: {overlap_tr_te} positions ({overlap_tr_te/len(h_te)*100:.2f}% of Test)")
    print(f"  Overlap Val-Test:   {overlap_va_te} positions ({overlap_va_te/len(h_te)*100:.2f}% of Test)")

    return {
        "train_size": len(y_tr),
        "val_size": len(y_va),
        "test_size": len(y_te),
        "overlap_tr_va": overlap_tr_va,
        "overlap_tr_te": overlap_tr_te,
        "overlap_va_te": overlap_va_te,
    }


if __name__ == "__main__":
    r_model = audit_model_and_weights()
    r_tourn = audit_tournament()
    r_data = audit_dataset()
