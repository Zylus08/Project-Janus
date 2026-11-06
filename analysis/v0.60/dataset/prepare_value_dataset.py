"""Project Janus v0.60 - Teacher-Labeled Value Dataset Generation Pipeline.

Extracts diverse, deduplicated chess positions from verified master games,
queries Stockfish 19 (fixed nodes=5000) for high-accuracy ground-truth teacher evaluations,
computes Janus C1 classical static evaluations as control, and stores train/val/test splits.
"""

from __future__ import annotations

import io
import json
import os
import random
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess
import chess.pgn
import numpy as np

# Ensure immediate unbuffered output
sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "analysis" / "v0.60" / "dataset"
ZIP_PATH = ROOT / "analysis" / "v0.58" / "data" / "lichess_elite_2020-06.zip"
STOCKFISH_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

# Baseline C1 bridge for E0 baseline evaluation
C1_BRIDGE_PATH = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

import importlib.util

spec = importlib.util.spec_from_file_location("janus_c1_bridge", C1_BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridgeC1 = mod.NativeEngineBridge


def compute_game_phase(board: chess.Board) -> str:
    """Classifies game phase into opening, middlegame, or endgame."""
    ply = board.ply()
    if ply < 16:
        return "opening"
    non_pawn_pieces = 0
    for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        non_pawn_pieces += len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK))
    if non_pawn_pieces <= 6 or ply >= 60:
        return "endgame"
    return "middlegame"


def evaluate_batch_stockfish(
    fens: List[str], sf_path: Path, nodes: int = 5000
) -> List[Dict[str, Any]]:
    """Evaluates a batch of FENs with a persistent Stockfish 19 process."""
    p = subprocess.Popen(
        [str(sf_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p.stdin.write("uci\nsetoption name Threads value 1\nsetoption name Hash value 16\nisready\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if "readyok" in line:
            break

    results = []
    for fen in fens:
        p.stdin.write(f"position fen {fen}\ngo nodes {nodes}\n")
        p.stdin.flush()
        score_cp = None
        is_mate = False
        mate_depth = None
        best_move = None

        while True:
            line = p.stdout.readline()
            if "score cp" in line:
                parts = line.split()
                idx = parts.index("cp")
                score_cp = int(parts[idx + 1])
            elif "score mate" in line:
                parts = line.split()
                idx = parts.index("mate")
                mate_depth = int(parts[idx + 1])
                is_mate = True
                score_cp = 30000 if mate_depth > 0 else -30000
            if "bestmove" in line:
                best_move = line.split()[1]
                break

        results.append(
            {
                "score_cp": score_cp,
                "is_mate": is_mate,
                "mate_depth": mate_depth,
                "best_move": best_move,
            }
        )

    p.stdin.write("quit\n")
    p.stdin.flush()
    p.terminate()
    return results


def build_value_dataset(
    target_train: int = 10000,
    target_val: int = 1250,
    target_test: int = 1250,
    sf_nodes: int = 5000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Extracts, labels, and partitions dataset."""
    print("=" * 60)
    print("PROJECT JANUS v0.60 — VALUE DATASET GENERATION")
    print("=" * 60)
    print(f"Targets: Train={target_train}, Val={target_val}, Test={target_test}")

    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Missing {ZIP_PATH}")

    zf = zipfile.ZipFile(ZIP_PATH)
    pgn_names = [n for n in zf.namelist() if n.endswith(".pgn")]
    if not pgn_names:
        raise ValueError(f"No .pgn found in {ZIP_PATH}")
    pgn_filename = pgn_names[0]
    print(f"Streaming from PGN archive: {pgn_filename}")

    pgn_file = zf.open(pgn_filename)
    pgn_text = io.TextIOWrapper(pgn_file, encoding="utf-8", errors="ignore")

    train_raw, val_raw, test_raw = [], [], []
    seen_fens = set()
    games_parsed = 0

    t0 = time.time()
    while len(train_raw) < target_train or len(val_raw) < target_val or len(test_raw) < target_test:
        game = chess.pgn.read_game(pgn_text)
        if game is None:
            break
        games_parsed += 1

        game_id = f"game_{games_parsed}"
        # Strict game-level split based on deterministic hash
        game_hash = (hash(game.headers.get("Site", "") + game.headers.get("Date", "") + str(games_parsed)) & 0x7FFFFFFF)
        split_val = game_hash % 100

        if split_val < 80:
            target_list = train_raw
            max_for_split = target_train
        elif split_val < 90:
            target_list = val_raw
            max_for_split = target_val
        else:
            target_list = test_raw
            max_for_split = target_test

        if len(target_list) >= max_for_split:
            continue

        board = game.board()
        ply = 0

        for move in game.mainline_moves():
            board.push(move)
            ply += 1

            if ply < 10 or ply > 85:
                continue

            # Sample 1 position every 4 plies
            if ply % 4 != (games_parsed % 4):
                continue

            if board.is_check() or board.is_game_over():
                continue

            fen = board.fen()
            core_fen = " ".join(fen.split()[:4])
            if core_fen in seen_fens:
                continue
            seen_fens.add(core_fen)

            target_list.append(
                {
                    "fen": fen,
                    "game_id": game_id,
                    "ply": ply,
                    "turn": "white" if board.turn == chess.WHITE else "black",
                    "phase": compute_game_phase(board),
                }
            )

            if len(target_list) >= max_for_split:
                break

        if games_parsed % 200 == 0:
            print(f"  Parsed {games_parsed} games | Extracted: Train={len(train_raw)}/{target_train}, Val={len(val_raw)}/{target_val}, Test={len(test_raw)}/{target_test}")

    print(f"\nExtraction complete in {time.time()-t0:.2f}s across {games_parsed} games.")
    print(f"Positions: Train={len(train_raw)}, Val={len(val_raw)}, Test={len(test_raw)}")

    # Initialize C1 Native Engine Bridge
    print("\nInitializing Janus Classical C1 Native Engine...")
    c1 = NativeEngineBridgeC1()
    c1.set_ordering_options(True, True)
    c1.set_pvs_options(False)
    c1.set_lmr_options(True, 3, 4, 1)
    c1.set_see_options(False, False)

    def label_partition(partition_data: List[Dict[str, Any]], name: str) -> List[Dict[str, Any]]:
        print(f"\nLabeling {name} partition ({len(partition_data)} positions) with Stockfish 19...")
        fens = [p["fen"] for p in partition_data]
        t_label_start = time.perf_counter()

        batch_size = 500
        sf_results = []
        for i in range(0, len(fens), batch_size):
            chunk = fens[i : i + batch_size]
            res = evaluate_batch_stockfish(chunk, STOCKFISH_EXE, nodes=sf_nodes)
            sf_results.extend(res)
            done = len(sf_results)
            pct = done / len(fens) * 100
            elapsed = time.perf_counter() - t_label_start
            rate = done / max(0.001, elapsed)
            print(f"  [{name}] {done}/{len(fens)} positions labeled ({pct:.1f}%) — {rate:.1f} pos/sec")

        labeled_records = []
        for pos, sf_res in zip(partition_data, sf_results):
            fen = pos["fen"]
            c1.set_fen(fen)
            c1_stm_score = c1.evaluate()
            is_white = pos["turn"] == "white"
            c1_white_score = c1_stm_score if is_white else -c1_stm_score

            sf_stm_score = sf_res["score_cp"]
            sf_white_score = sf_stm_score if is_white else -sf_stm_score

            wdl_stm = 1.0 / (1.0 + np.exp(-sf_stm_score / 400.0))

            rec = {
                "fen": fen,
                "game_id": pos["game_id"],
                "ply": pos["ply"],
                "turn": pos["turn"],
                "phase": pos["phase"],
                "sf_score_stm": sf_stm_score,
                "sf_score_white": sf_white_score,
                "sf_is_mate": sf_res["is_mate"],
                "sf_mate_depth": sf_res["mate_depth"],
                "sf_best_move": sf_res["best_move"],
                "wdl_stm": float(wdl_stm),
                "c1_score_stm": c1_stm_score,
                "c1_score_white": c1_white_score,
            }
            labeled_records.append(rec)

        return labeled_records

    train_labeled = label_partition(train_raw, "train")
    val_labeled = label_partition(val_raw, "val")
    test_labeled = label_partition(test_raw, "test")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    train_file = DATA_DIR / "value_train.json"
    val_file = DATA_DIR / "value_val.json"
    test_file = DATA_DIR / "value_test.json"

    print(f"\nWriting dataset JSON files to {DATA_DIR}...")
    with open(train_file, "w", encoding="utf-8") as f:
        json.dump(train_labeled, f)
    with open(val_file, "w", encoding="utf-8") as f:
        json.dump(val_labeled, f)
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_labeled, f)

    manifest = {
        "dataset_name": "Project Janus v0.60 Teacher-Labeled Value Corpus",
        "teacher": {
            "name": "Stockfish 19",
            "path": str(STOCKFISH_EXE),
            "sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0",
            "search_limit": f"nodes {sf_nodes}",
            "threads": 1,
            "hash_mb": 16,
        },
        "source_data": {
            "name": "Lichess Elite Database 2020-06",
            "license": "CC0 / Open Data",
            "source_archive": str(ZIP_PATH),
        },
        "counts": {
            "train": len(train_labeled),
            "val": len(val_labeled),
            "test": len(test_labeled),
            "total": len(train_labeled) + len(val_labeled) + len(test_labeled),
        },
        "phase_breakdown": {
            "train": {
                "opening": sum(1 for p in train_labeled if p["phase"] == "opening"),
                "middlegame": sum(1 for p in train_labeled if p["phase"] == "middlegame"),
                "endgame": sum(1 for p in train_labeled if p["phase"] == "endgame"),
            },
            "val": {
                "opening": sum(1 for p in val_labeled if p["phase"] == "opening"),
                "middlegame": sum(1 for p in val_labeled if p["phase"] == "middlegame"),
                "endgame": sum(1 for p in val_labeled if p["phase"] == "endgame"),
            },
            "test": {
                "opening": sum(1 for p in test_labeled if p["phase"] == "opening"),
                "middlegame": sum(1 for p in test_labeled if p["phase"] == "middlegame"),
                "endgame": sum(1 for p in test_labeled if p["phase"] == "endgame"),
            },
        },
        "files": {
            "train": str(train_file.name),
            "val": str(val_file.name),
            "test": str(test_file.name),
        },
    }

    manifest_file = DATA_DIR / "dataset_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 60)
    print("DATASET PREPARATION COMPLETED SUCCESSFULLY")
    print(f"Saved to: {DATA_DIR}")
    print(f"Manifest: {manifest_file}")
    print(json.dumps(manifest["counts"], indent=2))
    print("=" * 60)
    return manifest


if __name__ == "__main__":
    build_value_dataset()
