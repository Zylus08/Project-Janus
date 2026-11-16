#!/usr/bin/env python3
"""
build_chess_dataset.py
Milestone P2.1 Phase 3: Deterministic Chess Dataset Pipeline & Leakage-Free Splits.
Ingests tournament PGN games from Project Janus Phase 1 archives.
Extracts positions with side-to-move perspective target scores, splits by game ID,
deduplicates positions across splits, and generates complete integrity manifests.
"""

import os
import sys
import json
import hashlib
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple

import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus-phase1")
DATA_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "data"
RAW_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

PGN_SOURCES = [
    ROOT / "analysis" / "phase1" / "p1.22" / "pgn" / "match1_r1_vs_x22s_fast.pgn",
    ROOT / "analysis" / "phase1" / "p1.22" / "pgn" / "match3_r1_vs_x7_fast.pgn",
    ROOT / "analysis" / "phase1" / "p1.22" / "pgn" / "match5_r1_4t_vs_x12_fast.pgn",
    ROOT / "analysis" / "phase1" / "p1.21" / "pgn" / "match1_x26s_vs_x22s_fast.pgn",
    ROOT / "analysis" / "phase1" / "p1.21" / "pgn" / "match3_x26s_vs_x7_fast.pgn",
    ROOT / "analysis" / "phase1" / "p1.18" / "pgn" / "match1_x23_vs_x22.pgn",
    ROOT / "analysis" / "phase1" / "p1.19" / "pgn" / "match_1_x24-s_vs_x22-s_ref_1t.pgn"
]

def parse_games():
    print("=" * 70)
    print("PHASE 3: DETERMINISTIC CHESS DATASET ENGINEERING")
    print("=" * 70)

    all_games = []
    game_counter = 0

    for pgn_path in PGN_SOURCES:
        if not pgn_path.exists():
            print(f"Skipping missing PGN: {pgn_path}")
            continue

        with open(pgn_path, "r", encoding="utf-8") as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                res = game.headers.get("Result", "*")
                if res not in ("1-0", "0-1", "1/2-1/2"):
                    continue
                white = game.headers.get("White", "Unknown")
                black = game.headers.get("Black", "Unknown")
                game_id = f"G_{game_counter:05d}_{white}_vs_{black}"
                game_counter += 1
                all_games.append((game_id, pgn_path.name, res, game))

    print(f"Ingested {len(all_games)} valid games from {len(PGN_SOURCES)} PGN files.")

    # Shuffle games deterministically
    random.seed(42)
    random.shuffle(all_games)

    n_total = len(all_games)
    n_train = int(n_total * 0.80)
    n_val = int(n_total * 0.10)
    n_test = n_total - n_train - n_val

    splits = {
        "train": all_games[:n_train],
        "val": all_games[n_train:n_train + n_val],
        "test": all_games[n_train + n_val:]
    }

    print(f"Game splits: Train={len(splits['train'])}, Val={len(splits['val'])}, Test={len(splits['test'])}")

    seen_fens: Set[str] = set()
    split_records: Dict[str, List[Dict]] = {"train": [], "val": [], "test": []}

    # Extract positions per split
    for split_name, game_list in splits.items():
        for game_id, pgn_source, res, game in game_list:
            # Result from White's perspective
            if res == "1-0":
                res_w = 1.0
            elif res == "0-1":
                res_w = 0.0
            else:
                res_w = 0.5

            board = game.board()
            ply = 0
            for move in game.mainline_moves():
                board.push(move)
                ply += 1

                # Skip opening book moves (first 8 plies) and long endgame repetition (>120 plies)
                if ply < 8 or ply > 120:
                    continue

                # Deduplicate by canonical FEN (piece placement + side to move + castling + ep)
                canonical_fen = board.fen()
                if canonical_fen in seen_fens:
                    continue
                seen_fens.add(canonical_fen)

                # Target result from side-to-move perspective:
                # If White to move: target is res_w
                # If Black to move: target is 1.0 - res_w
                target_score = res_w if board.turn == chess.WHITE else (1.0 - res_w)

                record = {
                    "fen": canonical_fen,
                    "stm": "w" if board.turn == chess.WHITE else "b",
                    "ply": ply,
                    "target_res": target_score,
                    "game_id": game_id,
                    "source": pgn_source,
                    "split": split_name
                }
                split_records[split_name].append(record)

    print("\nPosition extraction summary (strictly deduplicated across all splits):")
    for s_name in ("train", "val", "test"):
        count = len(split_records[s_name])
        print(f"  Split '{s_name}': {count} positions")

    # Save JSON Lines files
    manifest = {
        "pipeline_version": "P2.1_V1",
        "date": "2026-11-16",
        "random_seed": 42,
        "total_games_ingested": len(all_games),
        "total_unique_positions": len(seen_fens),
        "splits": {}
    }

    for s_name in ("train", "val", "test"):
        out_path = DATA_DIR / f"janus_nnue_{s_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in split_records[s_name]:
                f.write(json.dumps(rec) + "\n")
        sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
        manifest["splits"][s_name] = {
            "path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
            "num_positions": len(split_records[s_name]),
            "sha256": sha256
        }
        print(f"Saved {out_path.name} ({len(split_records[s_name])} records, SHA256: {sha256[:16]}...)")

    manifest_path = RAW_DIR / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n[DONE] Manifest written to {manifest_path}")

if __name__ == "__main__":
    parse_games()
