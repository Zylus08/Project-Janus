"""Project Janus v0.58 - Supervised Policy Dataset Preparation Pipeline.

Extracts canonical 14-plane tensors ([14, 8, 8] = 896 floats) and 4,168-dimensional
action targets from Lichess Elite Grandmaster/Master games.

Dataset Properties:
- Source: Lichess Elite Database (nikonoel.fr, CC0 / Open Database License).
- Game-level split: Strict split by complete games (80% Train, 10% Val, 10% Test).
- Deduplication: Exact FEN deduplication within splits.
- Promotion preservation: Full support for Queen, Rook, Bishop, Knight promotions into [0, 4167].
- Phase distribution: Opening (ply < 20), Middlegame (20 <= ply < 60), Endgame (ply >= 60).
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import chess
import chess.pgn
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
ZIP_PATH = DATA_DIR / "lichess_elite_2020-06.zip"


def encode_board_canonical(board: chess.Board) -> np.ndarray:
    """Encodes chess.Board into canonical [14, 8, 8] float32 tensor from STM perspective."""
    stm = board.turn
    tensor = np.zeros((14, 8, 8), dtype=np.float32)

    # Friendly pieces (planes 0-5), Enemy pieces (planes 6-11)
    # Piece types: PAWN=1, KNIGHT=2, BISHOP=3, ROOK=4, QUEEN=5, KING=6
    for pt in range(1, 7):
        friendly_bb = board.pieces(pt, stm)
        enemy_bb = board.pieces(pt, not stm)

        for sq in friendly_bb:
            r = sq // 8 if stm == chess.WHITE else 7 - (sq // 8)
            f = sq % 8
            tensor[pt - 1, r, f] = 1.0

        for sq in enemy_bb:
            r = sq // 8 if stm == chess.WHITE else 7 - (sq // 8)
            f = sq % 8
            tensor[6 + pt - 1, r, f] = 1.0

    # Plane 12: Original Side to Move
    tensor[12, :, :] = 1.0 if stm == chess.WHITE else 0.0

    # Plane 13: Auxiliary state
    # Friendly castling rights
    tensor[13, 0, 0] = 1.0 if board.has_kingside_castling_rights(stm) else 0.0
    tensor[13, 0, 1] = 1.0 if board.has_queenside_castling_rights(stm) else 0.0
    # Enemy castling rights
    tensor[13, 0, 2] = 1.0 if board.has_kingside_castling_rights(not stm) else 0.0
    tensor[13, 0, 3] = 1.0 if board.has_queenside_castling_rights(not stm) else 0.0

    # En passant square (canonical rank 6)
    if board.ep_square is not None:
        ep_sq = board.ep_square
        ep_r = ep_sq // 8 if stm == chess.WHITE else 7 - (ep_sq // 8)
        if ep_r == 5: # Rank 6 (0-indexed 5)
            tensor[13, 0, 4] = (ep_sq % 8) / 7.0

    # Fifty-move rule halfmove counter
    tensor[13, 0, 5] = min(1.0, board.halfmove_clock / 100.0)

    return tensor


def encode_action_canonical(move: chess.Move, stm: chess.Color) -> int:
    """Encodes a chess.Move from STM canonical perspective into unique action index in [0, 4167]."""
    from_sq = move.from_square if stm == chess.WHITE else move.from_square ^ 56
    to_sq = move.to_square if stm == chess.WHITE else move.to_square ^ 56
    promo = move.promotion

    if promo is None or promo == chess.QUEEN:
        return from_sq * 64 + to_sq

    # Underpromotions: pawn moves from rank 7 (48..55) to rank 8 (56..63)
    f = from_sq % 8
    f_to = to_sq % 8
    dir_idx = f_to - f + 1 # 0=left, 1=straight, 2=right
    t = f * 3 + dir_idx

    if promo == chess.ROOK:
        return 4096 + t
    elif promo == chess.BISHOP:
        return 4120 + t
    elif promo == chess.KNIGHT:
        return 4144 + t

    return from_sq * 64 + to_sq


def decode_action_canonical(action: int, board: chess.Board) -> chess.Move:
    """Decodes canonical action index in [0, 4167] back to chess.Move in current board state."""
    stm = board.turn
    if action < 4096:
        c_from = action // 64
        c_to = action % 64
        orig_from = c_from if stm == chess.WHITE else c_from ^ 56
        orig_to = c_to if stm == chess.WHITE else c_to ^ 56

        piece = board.piece_at(orig_from)
        is_pawn = (piece is not None and piece.piece_type == chess.PAWN)
        is_promo_rank = (orig_to // 8 == 7 if stm == chess.WHITE else orig_to // 8 == 0)

        if is_pawn and is_promo_rank:
            return chess.Move(orig_from, orig_to, promotion=chess.QUEEN)
        return chess.Move(orig_from, orig_to)

    elif action < 4120:
        t = action - 4096
        f = t // 3
        f_to = f + (t % 3) - 1
        c_from = 48 + f
        c_to = 56 + f_to
        orig_from = c_from if stm == chess.WHITE else c_from ^ 56
        orig_to = c_to if stm == chess.WHITE else c_to ^ 56
        return chess.Move(orig_from, orig_to, promotion=chess.ROOK)

    elif action < 4144:
        t = action - 4120
        f = t // 3
        f_to = f + (t % 3) - 1
        c_from = 48 + f
        c_to = 56 + f_to
        orig_from = c_from if stm == chess.WHITE else c_from ^ 56
        orig_to = c_to if stm == chess.WHITE else c_to ^ 56
        return chess.Move(orig_from, orig_to, promotion=chess.BISHOP)

    elif action < 4168:
        t = action - 4144
        f = t // 3
        f_to = f + (t % 3) - 1
        c_from = 48 + f
        c_to = 56 + f_to
        orig_from = c_from if stm == chess.WHITE else c_from ^ 56
        orig_to = c_to if stm == chess.WHITE else c_to ^ 56
        return chess.Move(orig_from, orig_to, promotion=chess.KNIGHT)

    raise ValueError(f"Action index {action} out of range [0, 4167]")


def build_dataset(
    target_train: int = 60000,
    target_val: int = 10000,
    target_test: int = 10000,
) -> Dict[str, Any]:
    print("=================================================================")
    print("PROJECT JANUS v0.58 — DATASET EXTRACTION PIPELINE")
    print(f"Target Positions: Train={target_train}, Val={target_val}, Test={target_test}")
    print("=================================================================")

    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Missing {ZIP_PATH}. Run download_data.py first.")

    zf = zipfile.ZipFile(ZIP_PATH)
    pgn_names = [n for n in zf.namelist() if n.endswith(".pgn")]
    if not pgn_names:
        raise ValueError(f"No .pgn found in {ZIP_PATH}")
    pgn_filename = pgn_names[0]
    print(f"Opening PGN archive member: {pgn_filename}")

    pgn_file = zf.open(pgn_filename)
    pgn_text = io.TextIOWrapper(pgn_file, encoding="utf-8", errors="ignore")

    train_tensors, train_actions = [], []
    val_tensors, val_actions = [], []
    test_tensors, test_actions = [], []

    seen_fens = set()
    games_parsed = 0
    phase_counts = {"opening": 0, "middlegame": 0, "endgame": 0}
    promo_count = 0
    total_positions_needed = target_train + target_val + target_test

    t0 = time.time()

    while len(train_tensors) < target_train or len(val_tensors) < target_val or len(test_tensors) < target_test:
        game = chess.pgn.read_game(pgn_text)
        if game is None:
            break

        games_parsed += 1

        # Strict game-level split based on deterministic hash of game ID / headers
        # Prevents any position from a game appearing in more than one partition
        game_hash = hash(game.headers.get("Site", "") + game.headers.get("Date", "") + str(games_parsed))
        split_val = (game_hash % 100 + 100) % 100 # 0..99

        if split_val < 80:
            target_list_t = train_tensors
            target_list_a = train_actions
            max_for_split = target_train
        elif split_val < 90:
            target_list_t = val_tensors
            target_list_a = val_actions
            max_for_split = target_val
        else:
            target_list_t = test_tensors
            target_list_a = test_actions
            max_for_split = target_test

        if len(target_list_t) >= max_for_split:
            continue

        board = game.board()
        ply = 0

        for move in game.mainline_moves():
            # Skip very early opening book moves (< ply 6) to focus on decision positions
            if ply >= 6 and ply <= 90:
                fen = board.fen()
                # Deduplication within dataset
                if fen not in seen_fens:
                    seen_fens.add(fen)

                    tensor = encode_board_canonical(board)
                    action = encode_action_canonical(move, board.turn)

                    # Verify lossless round-trip on extraction
                    decoded_move = decode_action_canonical(action, board)
                    assert decoded_move == move, f"Round-trip failed: {move} != {decoded_move}"

                    target_list_t.append(tensor)
                    target_list_a.append(action)

                    # Telemetry tracking
                    if move.promotion is not None:
                        promo_count += 1

                    if ply < 20: phase_counts["opening"] += 1
                    elif ply < 60: phase_counts["middlegame"] += 1
                    else: phase_counts["endgame"] += 1

                    if len(target_list_t) >= max_for_split:
                        break

            board.push(move)
            ply += 1

        if games_parsed % 500 == 0:
            total_extracted = len(train_tensors) + len(val_tensors) + len(test_tensors)
            print(f"Parsed {games_parsed} games | Extracted: Train={len(train_tensors)}/{target_train}, Val={len(val_tensors)}/{target_val}, Test={len(test_tensors)}/{target_test} ({total_extracted}/{total_positions_needed})", flush=True)

    pgn_file.close()
    zf.close()

    total_extracted = len(train_tensors) + len(val_tensors) + len(test_tensors)
    duration = time.time() - t0
    print(f"\nExtraction complete in {duration:.1f}s!")
    print(f"Total Games Parsed: {games_parsed}")
    print(f"Total Unique Positions Extracted: {total_extracted}")
    print(f"Phases: Opening={phase_counts['opening']}, Middlegame={phase_counts['middlegame']}, Endgame={phase_counts['endgame']}")
    print(f"Promotions Included: {promo_count}")

    # Convert to NumPy arrays
    print("Converting to NumPy float32 tensors and int64 targets...")
    X_train = np.stack(train_tensors)
    y_train = np.array(train_actions, dtype=np.int64)

    X_val = np.stack(val_tensors)
    y_val = np.array(val_actions, dtype=np.int64)

    X_test = np.stack(test_tensors)
    y_test = np.array(test_actions, dtype=np.int64)

    train_path = DATA_DIR / "train_data.npz"
    val_path = DATA_DIR / "val_data.npz"
    test_path = DATA_DIR / "test_data.npz"

    np.savez_compressed(train_path, X=X_train, y=y_train)
    np.savez_compressed(val_path, X=X_val, y=y_val)
    np.savez_compressed(test_path, X=X_test, y=y_test)

    print(f"Saved Train NPZ: {train_path} ({train_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Saved Val NPZ:   {val_path} ({val_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Saved Test NPZ:  {test_path} ({test_path.stat().st_size / 1024 / 1024:.1f} MB)")

    manifest = {
        "dataset_name": "Lichess Elite Grandmaster/Master Supervised Policy Dataset (2020-06)",
        "source": "https://database.nikonoel.fr/lichess_elite_2020-06.zip",
        "license": "CC0 / Open Data",
        "games_parsed": games_parsed,
        "total_unique_positions": total_extracted,
        "splits": {
            "train": {"positions": len(y_train), "path": str(train_path.name)},
            "val": {"positions": len(y_val), "path": str(val_path.name)},
            "test": {"positions": len(y_test), "path": str(test_path.name)},
        },
        "phase_distribution": phase_counts,
        "promotions_observed": promo_count,
        "tensor_shape": [14, 8, 8],
        "action_space_size": 4168,
        "extraction_duration_sec": round(duration, 2),
    }

    manifest_path = DATA_DIR / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote dataset manifest to {manifest_path}")
    return manifest


if __name__ == "__main__":
    build_dataset()
