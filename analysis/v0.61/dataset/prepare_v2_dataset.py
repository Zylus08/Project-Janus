#!/usr/bin/env python3
"""Project Janus v0.61 - Scaled Value Dataset Generation Pipeline.

Extracts >=100,000 deduplicated, diverse master positions from verified games (Lichess Elite),
labels each position with Stockfish 19 (fixed nodes=10000) using a multi-threaded engine pool,
evaluates Janus Classical Baseline C1 as the control, and writes Train/Val/Test partitions
with zero cross-split leakage.
"""

from __future__ import annotations

import io
import json
import os
import random
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import chess
import chess.engine
import chess.pgn
import numpy as np

# Ensure immediate unbuffered output
sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "analysis" / "v0.61" / "dataset"
RAW_DIR = ROOT / "analysis" / "v0.61" / "raw"
ZIP_PATH = ROOT / "analysis" / "v0.58" / "data" / "lichess_elite_2020-06.zip"
STOCKFISH_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")
C1_BRIDGE_PATH = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

# Compute Stockfish 19 hash
import hashlib
SF_SHA256 = hashlib.sha256(STOCKFISH_EXE.read_bytes()).hexdigest()

# Load C1 Native Bridge
import importlib.util
spec = importlib.util.spec_from_file_location("janus_c1_bridge", C1_BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridgeC1 = mod.NativeEngineBridge

TARGET_TRAIN = 80000
TARGET_VAL = 10000
TARGET_TEST = 10000
TOTAL_TARGET = TARGET_TRAIN + TARGET_VAL + TARGET_TEST
NODES_PER_POS = 10000
NUM_WORKERS = 10


def compute_game_phase(board: chess.Board) -> str:
    ply = board.ply()
    if ply <= 16:
        return "opening"
    non_pawns = sum(
        len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK))
        for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]
    )
    if non_pawns <= 6 or ply >= 55:
        return "endgame"
    return "middlegame"


def extract_candidate_positions(
    target_count: int,
    game_start_idx: int,
    max_games: int,
    seen_fens_global: Set[str],
    split_name: str,
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """Extracts stratified positions from a partitioned range of games."""
    print(f"\n[{split_name.upper()}] Extracting {target_count:,} candidate positions (games {game_start_idx:,}..{game_start_idx+max_games:,})...")
    candidates = []
    seen_in_split: Set[str] = set()

    phase_counts = {"opening": 0, "middlegame": 0, "endgame": 0}
    quota_opening = int(target_count * 0.25)
    quota_middlegame = int(target_count * 0.50)
    quota_endgame = int(target_count * 0.25)

    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open("lichess_elite_2020-06.pgn") as f:
            text_f = io.TextIOWrapper(f, encoding="utf-8")
            
            # Fast skip to game_start_idx
            print(f"  Skipping first {game_start_idx:,} games...")
            for _ in range(game_start_idx):
                if not chess.pgn.skip_game(text_f):
                    break

            g_idx = 0
            while len(candidates) < target_count and g_idx < max_games:
                game = chess.pgn.read_game(text_f)
                if game is None:
                    break
                g_idx += 1
                game_id = f"g_{game_start_idx + g_idx}"

                board = game.board()
                for move_idx, move in enumerate(game.mainline_moves()):
                    board.push(move)
                    ply = board.ply()

                    # Sample every 2-3 plies starting from ply 6
                    if ply < 6:
                        continue
                    if ply % 2 != 0 and ply < 30:
                        continue
                    if ply % 3 != 0 and ply >= 30:
                        continue

                    # Filter terminal positions
                    if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material():
                        continue

                    # Canonical FEN key (board + turn + castling + ep)
                    fen_parts = board.fen().split(" ")
                    canon_key = " ".join(fen_parts[:4])

                    if canon_key in seen_fens_global or canon_key in seen_in_split:
                        continue

                    ph = compute_game_phase(board)
                    if ph == "opening" and phase_counts["opening"] >= quota_opening and len(candidates) < target_count * 0.95:
                        continue
                    if ph == "endgame" and phase_counts["endgame"] >= quota_endgame and len(candidates) < target_count * 0.95:
                        continue

                    seen_in_split.add(canon_key)
                    phase_counts[ph] += 1
                    candidates.append({
                        "fen": board.fen(),
                        "canon_key": canon_key,
                        "source_game": game_id,
                        "split": split_name,
                        "ply": ply,
                        "turn": "white" if board.turn == chess.WHITE else "black",
                        "phase": ph,
                    })

                    if len(candidates) >= target_count:
                        break

                if g_idx % 500 == 0:
                    print(f"  Processed {g_idx:,} games -> {len(candidates):,}/{target_count:,} candidates (O:{phase_counts['opening']}, M:{phase_counts['middlegame']}, E:{phase_counts['endgame']})")

    print(f"[{split_name.upper()}] Extraction complete: {len(candidates):,} positions from {g_idx:,} games.")
    print(f"  Phases: Opening={phase_counts['opening']:,}, Middlegame={phase_counts['middlegame']:,}, Endgame={phase_counts['endgame']:,}")
    return candidates, seen_in_split


def evaluate_worker_chunk(chunk_data: List[Dict[str, Any]], worker_id: int) -> List[Dict[str, Any]]:
    """Evaluates a chunk of positions using a persistent Stockfish 19 engine instance."""
    engine = chess.engine.SimpleEngine.popen_uci(str(STOCKFISH_EXE))
    engine.configure({"Threads": 1, "Hash": 16})
    c1 = NativeEngineBridgeC1()

    labeled = []
    for item in chunk_data:
        fen = item["fen"]
        board = chess.Board(fen)

        # 1. Stockfish 19 Teacher Evaluation
        info = engine.analyse(board, chess.engine.Limit(nodes=NODES_PER_POS))
        score_obj = info["score"].relative
        is_mate = score_obj.is_mate()
        mate_depth = score_obj.mate() if is_mate else None
        raw_score_stm = score_obj.score(mate_score=30000)
        best_move = str(info.get("pv", [None])[0]) if info.get("pv") else ""
        depth = info.get("depth", 0)

        # Clamping and score transformations
        clamped_stm = max(-2000, min(2000, raw_score_stm))
        score_white = clamped_stm if board.turn == chess.WHITE else -clamped_stm
        wdl_stm = 1.0 / (1.0 + 10.0 ** (-clamped_stm / 400.0))

        # 2. Classical Baseline C1 Control
        c1.set_fen(fen)
        c1_score_stm = c1.evaluate()
        c1_score_white = c1_score_stm if board.turn == chess.WHITE else -c1_score_stm

        labeled.append({
            "fen": fen,
            "source_game": item["source_game"],
            "split": item["split"],
            "ply": item["ply"],
            "turn": item["turn"],
            "game_phase": item["phase"],
            "teacher_sha256": SF_SHA256,
            "teacher_uci_options": {"Threads": 1, "Hash": 16},
            "search_nodes": NODES_PER_POS,
            "search_depth": depth,
            "raw_score_stm": clamped_stm,
            "raw_score_white": score_white,
            "is_mate": is_mate,
            "mate_depth": mate_depth,
            "sf_best_move": best_move,
            "wdl_target": round(wdl_stm, 6),
            "c1_score_stm": c1_score_stm,
            "c1_score_white": c1_score_white,
            "feature_encoding_version": "half_kp_v2",
        })

    engine.quit()
    return labeled


def label_positions_parallel(positions: List[Dict[str, Any]], num_workers: int, split_name: str) -> List[Dict[str, Any]]:
    """Labels positions in parallel across multiple Stockfish 19 instances."""
    n = len(positions)
    print(f"\n[{split_name.upper()}] Starting parallel labeling of {n:,} positions with {num_workers} threads...")
    chunk_size = (n + num_workers - 1) // num_workers
    chunks = [positions[i:i + chunk_size] for i in range(0, n, chunk_size)]

    t0 = time.time()
    labeled_results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(evaluate_worker_chunk, chunk, idx) for idx, chunk in enumerate(chunks)]
        done_count = 0
        for f in futures:
            res = f.result()
            labeled_results.extend(res)
            done_count += len(res)
            pct = done_count / n * 100.0
            elapsed = time.time() - t0
            rate = done_count / elapsed if elapsed > 0 else 0
            print(f"  [{split_name.upper()}] Labeled {done_count:,}/{n:,} positions ({pct:.1f}%) - {rate:.1f} pos/sec (elapsed: {elapsed:.1f}s)")

    total_time = time.time() - t0
    print(f"[{split_name.upper()}] Parallel labeling complete in {total_time:.2f}s ({total_time/n*1000:.1f} ms/pos).")
    return labeled_results


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PROJECT JANUS v0.61 — SCALED VALUE DATASET GENERATION PIPELINE")
    print(f"Target: {TOTAL_TARGET:,} positions (Train: {TARGET_TRAIN:,}, Val: {TARGET_VAL:,}, Test: {TARGET_TEST:,})")
    print(f"Teacher: Stockfish 19 at nodes={NODES_PER_POS:,} ({NUM_WORKERS} parallel workers)")
    print("=" * 70)

    # Global FEN tracking to mathematically guarantee zero split leakage
    global_fens: Set[str] = set()

    # Step 1: Extract and label Train set (Games 0 .. 4,500)
    train_candidates, train_fens = extract_candidate_positions(
        target_count=TARGET_TRAIN,
        game_start_idx=0,
        max_games=4500,
        seen_fens_global=global_fens,
        split_name="train",
    )
    global_fens.update(train_fens)

    # Step 2: Extract and label Val set (Games 5,000 .. 5,700)
    val_candidates, val_fens = extract_candidate_positions(
        target_count=TARGET_VAL,
        game_start_idx=5000,
        max_games=700,
        seen_fens_global=global_fens,
        split_name="val",
    )
    global_fens.update(val_fens)

    # Step 3: Extract and label Test set (Games 6,000 .. 6,700)
    test_candidates, test_fens = extract_candidate_positions(
        target_count=TARGET_TEST,
        game_start_idx=6000,
        max_games=700,
        seen_fens_global=global_fens,
        split_name="test",
    )
    global_fens.update(test_fens)

    # Assert strict disjointness
    print("\nVerifying Split Disjointness & Zero Leakage...")
    assert len(train_fens.intersection(val_fens)) == 0, "FATAL: Train and Val sets overlap!"
    assert len(train_fens.intersection(test_fens)) == 0, "FATAL: Train and Test sets overlap!"
    assert len(val_fens.intersection(test_fens)) == 0, "FATAL: Val and Test sets overlap!"
    print("  [PASS] Zero cross-split leakage mathematically confirmed!")

    # Parallel Labeling
    t_start = time.time()
    
    # Label Val first (10K)
    labeled_val = label_positions_parallel(val_candidates, NUM_WORKERS, "val")
    val_out_path = DATA_DIR / "value_v2_val.json"
    with open(val_out_path, "w", encoding="utf-8") as f:
        json.dump(labeled_val, f)
    print(f"Saved {len(labeled_val):,} validation positions to {val_out_path.name}")

    # Label Test second (10K)
    labeled_test = label_positions_parallel(test_candidates, NUM_WORKERS, "test")
    test_out_path = DATA_DIR / "value_v2_test.json"
    with open(test_out_path, "w", encoding="utf-8") as f:
        json.dump(labeled_test, f)
    print(f"Saved {len(labeled_test):,} test positions to {test_out_path.name}")

    # Label Train (80K)
    labeled_train = label_positions_parallel(train_candidates, NUM_WORKERS, "train")
    train_out_path = DATA_DIR / "value_v2_train.json"
    with open(train_out_path, "w", encoding="utf-8") as f:
        json.dump(labeled_train, f)
    print(f"Saved {len(labeled_train):,} training positions to {train_out_path.name}")

    total_elapsed = time.time() - t_start
    print(f"\nAll labeling complete in {total_elapsed:.1f}s ({total_elapsed/60.0:.2f} min).")

    # Generate Manifest
    manifest = {
        "dataset_name": "janus_nnue_v2_dataset",
        "milestone": "v0.61",
        "total_positions": len(labeled_train) + len(labeled_val) + len(labeled_test),
        "splits": {
            "train": {
                "count": len(labeled_train),
                "file": "value_v2_train.json",
                "sha256": hashlib.sha256(train_out_path.read_bytes()).hexdigest(),
                "phases": {
                    "opening": sum(1 for p in labeled_train if p["game_phase"] == "opening"),
                    "middlegame": sum(1 for p in labeled_train if p["game_phase"] == "middlegame"),
                    "endgame": sum(1 for p in labeled_train if p["game_phase"] == "endgame"),
                },
                "mean_abs_sf_score": float(np.mean([abs(p["raw_score_stm"]) for p in labeled_train])),
            },
            "val": {
                "count": len(labeled_val),
                "file": "value_v2_val.json",
                "sha256": hashlib.sha256(val_out_path.read_bytes()).hexdigest(),
                "phases": {
                    "opening": sum(1 for p in labeled_val if p["game_phase"] == "opening"),
                    "middlegame": sum(1 for p in labeled_val if p["game_phase"] == "middlegame"),
                    "endgame": sum(1 for p in labeled_val if p["game_phase"] == "endgame"),
                },
                "mean_abs_sf_score": float(np.mean([abs(p["raw_score_stm"]) for p in labeled_val])),
            },
            "test": {
                "count": len(labeled_test),
                "file": "value_v2_test.json",
                "sha256": hashlib.sha256(test_out_path.read_bytes()).hexdigest(),
                "phases": {
                    "opening": sum(1 for p in labeled_test if p["game_phase"] == "opening"),
                    "middlegame": sum(1 for p in labeled_test if p["game_phase"] == "middlegame"),
                    "endgame": sum(1 for p in labeled_test if p["game_phase"] == "endgame"),
                },
                "mean_abs_sf_score": float(np.mean([abs(p["raw_score_stm"]) for p in labeled_test])),
            },
        },
        "teacher": {
            "engine": "Stockfish 19",
            "sha256": SF_SHA256,
            "nodes_per_position": NODES_PER_POS,
            "uci_options": {"Threads": 1, "Hash": 16},
        },
        "disjointness_verified": True,
        "leakage_count": 0,
    }

    manifest_path = DATA_DIR / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Dataset manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
