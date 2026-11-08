"""Project Janus v0.64 - Scaled Phase-Balanced Dataset Generation Pipeline.

Constructs a 150,000-position supervised dataset with dedicated coverage of
endgames (pawn, rook, minor-piece, opposite-bishop) and closed/king-attack structures.
Labels positions with Stockfish 19 at depth 10 using high-throughput multi-worker evaluation.
Partitions with strict game-level and FEN-level deduplication into:
- train_v3.json (120,000 positions = 80k v2 + 40k new)
- val_v3.json   (15,000 positions = 10k v2 + 5k new)
- test_v3.json  (15,000 positions = 10k v2 + 5k new)
"""

from __future__ import annotations

import io
import json
import math
import subprocess
import sys
import time
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import chess
import chess.pgn

ROOT = Path("E:/ChessXML/project-janus")
ZIP_PATH = ROOT / "analysis" / "v0.58" / "data" / "lichess_elite_2020-06.zip"
STOCKFISH_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")
V61_DATA_DIR = ROOT / "analysis" / "v0.61" / "dataset"
OUT_DATA_DIR = ROOT / "analysis" / "v0.64" / "dataset"
OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)

SF_SHA256 = hashlib.sha256(STOCKFISH_EXE.read_bytes()).hexdigest()
NUM_WORKERS = 10


def compute_material_phase(board: chess.Board) -> int:
    return (
        len(board.pieces(chess.KNIGHT, chess.WHITE)) * 1 +
        len(board.pieces(chess.KNIGHT, chess.BLACK)) * 1 +
        len(board.pieces(chess.BISHOP, chess.WHITE)) * 1 +
        len(board.pieces(chess.BISHOP, chess.BLACK)) * 1 +
        len(board.pieces(chess.ROOK, chess.WHITE)) * 2 +
        len(board.pieces(chess.ROOK, chess.BLACK)) * 2 +
        len(board.pieces(chess.QUEEN, chess.WHITE)) * 4 +
        len(board.pieces(chess.QUEEN, chess.BLACK)) * 4
    )


def classify_subtype(board: chess.Board, phase: int) -> str:
    w_q = len(board.pieces(chess.QUEEN, chess.WHITE))
    b_q = len(board.pieces(chess.QUEEN, chess.BLACK))
    w_r = len(board.pieces(chess.ROOK, chess.WHITE))
    b_r = len(board.pieces(chess.ROOK, chess.BLACK))
    w_b = len(board.pieces(chess.BISHOP, chess.WHITE))
    b_b = len(board.pieces(chess.BISHOP, chess.BLACK))
    w_n = len(board.pieces(chess.KNIGHT, chess.WHITE))
    b_n = len(board.pieces(chess.KNIGHT, chess.BLACK))

    total_queens = w_q + b_q
    total_rooks = w_r + b_r
    total_minors = w_b + b_b + w_n + b_n

    if phase == 0:
        return "pawn_endgame"
    elif total_queens == 0 and total_rooks in (1, 2) and total_minors == 0:
        return "rook_endgame"
    elif total_queens == 0 and total_rooks == 0 and total_minors in (1, 2):
        if w_b == 1 and b_b == 1 and total_minors == 2:
            return "opposite_bishops"
        return "minor_piece_endgame"
    elif phase <= 12 and total_queens == 0:
        return "queenless_middlegame"
    else:
        white_pawns = board.pieces(chess.PAWN, chess.WHITE)
        black_pawns = board.pieces(chess.PAWN, chess.BLACK)
        locked = sum(1 for sq in white_pawns if sq + 8 < 64 and (black_pawns & (1 << (sq + 8))))
        if locked >= 1:
            return "locked_pawn_structure"
        return "tactical_middlegame"


def extract_split_positions(
    split_name: str,
    target_count: int,
    quotas: Dict[str, int],
    start_game_idx: int,
    max_games: int,
    seen_fens: Set[str],
) -> List[Dict[str, Any]]:
    print(f"\n[{split_name.upper()}] Extracting {target_count:,} positions from games {start_game_idx:,}..{start_game_idx+max_games:,}...")
    counts = {k: 0 for k in quotas}
    candidates = []

    t0 = time.time()
    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open("lichess_elite_2020-06.pgn") as f:
            text_f = io.TextIOWrapper(f, encoding="utf-8")

            for _ in range(start_game_idx):
                if not chess.pgn.skip_game(text_f):
                    break

            g_idx = 0
            while len(candidates) < target_count and g_idx < max_games:
                game = chess.pgn.read_game(text_f)
                if game is None:
                    break
                g_idx += 1
                game_id = f"g_v3_{start_game_idx + g_idx}"

                board = game.board()
                game_sub_counts: Dict[str, int] = {}

                for move in game.mainline_moves():
                    board.push(move)
                    ply = board.ply()
                    if ply < 10:
                        continue
                    if board.is_game_over() or board.is_check():
                        continue

                    canon_key = " ".join(board.fen().split(" ")[:4])
                    if canon_key in seen_fens:
                        continue

                    ph = compute_material_phase(board)
                    sub = classify_subtype(board, ph)
                    if sub in quotas:
                        per_game_limit = 5 if "endgame" in sub or sub == "opposite_bishops" else 2
                        if game_sub_counts.get(sub, 0) < per_game_limit:
                            if counts[sub] < quotas[sub]:
                                counts[sub] += 1
                                game_sub_counts[sub] = game_sub_counts.get(sub, 0) + 1
                                seen_fens.add(canon_key)
                                candidates.append({
                                    "fen": board.fen(),
                                    "canon_key": canon_key,
                                    "source_game": game_id,
                                    "ply": ply,
                                    "material_phase": ph,
                                    "subtype": sub,
                                    "split": split_name,
                                })
                                if len(candidates) >= target_count:
                                    break

                if g_idx % 1000 == 0 or len(candidates) >= target_count:
                    el = time.time() - t0
                    print(f"  [{split_name.upper()}] {len(candidates):,}/{target_count:,} from {g_idx:,} games | Elapsed: {el:.1f}s | {counts}", flush=True)

    print(f"[{split_name.upper()}] Extraction complete: {len(candidates):,} positions from {g_idx:,} games in {time.time()-t0:.1f}s.", flush=True)
    return candidates


def evaluate_worker_chunk(chunk_data: List[Dict[str, Any]], worker_id: int, depth: int = 10) -> List[Dict[str, Any]]:
    p = subprocess.Popen(
        [str(STOCKFISH_EXE.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    p.stdin.write("uci\nsetoption name Threads value 1\nsetoption name Hash value 16\nisready\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line or "readyok" in line:
            break

    labeled = []
    for item in chunk_data:
        fen = item["fen"]
        p.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        p.stdin.flush()

        score_cp = 0
        bestmove = ""
        is_mate = False
        mate_depth = None

        while True:
            line = p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "score cp" in line:
                tokens = line.split()
                if "cp" in tokens:
                    idx = tokens.index("cp")
                    try:
                        score_cp = int(tokens[idx + 1])
                    except Exception:
                        pass
            elif "score mate" in line:
                tokens = line.split()
                if "mate" in tokens:
                    idx = tokens.index("mate")
                    try:
                        m = int(tokens[idx + 1])
                        is_mate = True
                        mate_depth = m
                        score_cp = 10000 if m > 0 else -10000
                    except Exception:
                        pass
            if line.startswith("bestmove"):
                toks = line.split()
                if len(toks) >= 2:
                    bestmove = toks[1]
                break

        # Turn normalization
        b = chess.Board(fen)
        turn_str = "white" if b.turn == chess.WHITE else "black"
        clamped_stm = max(-2000, min(2000, score_cp))
        score_white = clamped_stm if b.turn == chess.WHITE else -clamped_stm
        wdl = 1.0 / (1.0 + 10.0 ** (-clamped_stm / 400.0))

        labeled_item = dict(item)
        labeled_item.update({
            "turn": turn_str,
            "teacher_sha256": SF_SHA256,
            "search_depth": depth,
            "raw_score_stm": clamped_stm,
            "raw_score_white": score_white,
            "is_mate": is_mate,
            "mate_depth": mate_depth,
            "sf_best_move": bestmove,
            "wdl_target": round(wdl, 6),
            "feature_encoding_version": "v3_hybrid_phase",
        })
        labeled.append(labeled_item)

    try:
        p.stdin.write("quit\n")
        p.stdin.flush()
        p.wait(timeout=2.0)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass

    return labeled


def label_positions_parallel(positions: List[Dict[str, Any]], num_workers: int, name: str) -> List[Dict[str, Any]]:
    n = len(positions)
    print(f"\n[{name.upper()}] Starting parallel labeling of {n:,} positions with {num_workers} workers...", flush=True)
    chunk_size = (n + num_workers - 1) // num_workers
    chunks = [positions[i : i + chunk_size] for i in range(0, n, chunk_size)]

    t0 = time.time()
    labeled_results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(evaluate_worker_chunk, chunk, idx) for idx, chunk in enumerate(chunks)]
        done_count = 0
        for idx, f in enumerate(futures):
            res = f.result()
            labeled_results.extend(res)
            done_count += len(res)
            pct = done_count / n * 100.0
            el = time.time() - t0
            rate = done_count / el if el > 0 else 0
            print(f"  [{name.upper()}] Worker {idx+1}/{len(chunks)} finished ({done_count:,}/{n:,} - {pct:.1f}%) | {rate:.1f} pos/sec (elapsed: {el:.1f}s)", flush=True)

    total_time = time.time() - t0
    print(f"[{name.upper()}] Labeling complete in {total_time:.2f}s ({total_time/n*1000:.2f} ms/pos, {n/total_time:.1f} pos/sec).", flush=True)
    return labeled_results


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.64 — PHASE 1 DATASET EXPANSION PIPELINE")
    print(f"Teacher: Stockfish 19 x64 AVX2 | Workers: {NUM_WORKERS} parallel threads")
    print("=" * 80)

    # 1. Load historical v0.61 dataset (100,000 positions)
    print("Loading historical v0.61 dataset partitions...")
    with open(V61_DATA_DIR / "value_v2_train.json", "r", encoding="utf-8") as f:
        v2_train = json.load(f)
    with open(V61_DATA_DIR / "value_v2_val.json", "r", encoding="utf-8") as f:
        v2_val = json.load(f)
    with open(V61_DATA_DIR / "value_v2_test.json", "r", encoding="utf-8") as f:
        v2_test = json.load(f)

    seen_fens: Set[str] = set()
    for item in v2_train + v2_val + v2_test:
        k = " ".join(item["fen"].split(" ")[:4])
        seen_fens.add(k)
    print(f"Loaded {len(v2_train):,} train, {len(v2_val):,} val, {len(v2_test):,} test. Global FEN set: {len(seen_fens):,} unique keys.")

    # 2. Extract targeted endgame & structural positions with strict game isolation
    train_quotas = {
        "pawn_endgame": 4000,
        "rook_endgame": 8000,
        "minor_piece_endgame": 6000,
        "opposite_bishops": 2000,
        "queenless_middlegame": 10000,
        "locked_pawn_structure": 10000,
    }
    val_quotas = {
        "pawn_endgame": 500,
        "rook_endgame": 1000,
        "minor_piece_endgame": 750,
        "opposite_bishops": 250,
        "queenless_middlegame": 1250,
        "locked_pawn_structure": 1250,
    }
    test_quotas = {
        "pawn_endgame": 500,
        "rook_endgame": 1000,
        "minor_piece_endgame": 750,
        "opposite_bishops": 250,
        "queenless_middlegame": 1250,
        "locked_pawn_structure": 1250,
    }

    # Games 15,000..37,000 for train (22,000 games)
    new_train_candidates = extract_split_positions(
        "train", 40000, train_quotas, start_game_idx=15000, max_games=22000, seen_fens=seen_fens
    )

    # Games 38,000..44,000 for val (6,000 games)
    new_val_candidates = extract_split_positions(
        "val", 5000, val_quotas, start_game_idx=38000, max_games=6000, seen_fens=seen_fens
    )

    # Games 45,000..51,000 for test (6,000 games)
    new_test_candidates = extract_split_positions(
        "test", 5000, test_quotas, start_game_idx=45000, max_games=6000, seen_fens=seen_fens
    )

    total_new = len(new_train_candidates) + len(new_val_candidates) + len(new_test_candidates)
    print(f"\nTotal new candidate positions extracted: {total_new:,}")

    # 3. Parallel Labeling across NUM_WORKERS
    labeled_train = label_positions_parallel(new_train_candidates, NUM_WORKERS, "train")
    labeled_val = label_positions_parallel(new_val_candidates, NUM_WORKERS, "val")
    labeled_test = label_positions_parallel(new_test_candidates, NUM_WORKERS, "test")

    # 4. Combine with historical v0.61 sets
    import random
    random.seed(42)

    v3_train = v2_train + labeled_train
    v3_val = v2_val + labeled_val
    v3_test = v2_test + labeled_test

    random.shuffle(v3_train)
    random.shuffle(v3_val)
    random.shuffle(v3_test)

    # Deduplication and isolation verification
    train_fens = {" ".join(x["fen"].split(" ")[:4]) for x in v3_train}
    val_fens = {" ".join(x["fen"].split(" ")[:4]) for x in v3_val}
    test_fens = {" ".join(x["fen"].split(" ")[:4]) for x in v3_test}

    assert len(train_fens.intersection(val_fens)) == 0, "FATAL: Train/Val FEN leakage!"
    assert len(train_fens.intersection(test_fens)) == 0, "FATAL: Train/Test FEN leakage!"
    assert len(val_fens.intersection(test_fens)) == 0, "FATAL: Val/Test FEN leakage!"

    print("\nWriting v0.64 unified dataset partitions...", flush=True)
    with open(OUT_DATA_DIR / "value_v3_train.json", "w", encoding="utf-8") as f:
        json.dump(v3_train, f)
    with open(OUT_DATA_DIR / "value_v3_val.json", "w", encoding="utf-8") as f:
        json.dump(v3_val, f)
    with open(OUT_DATA_DIR / "value_v3_test.json", "w", encoding="utf-8") as f:
        json.dump(v3_test, f)

    total_positions = len(v3_train) + len(v3_val) + len(v3_test)
    print(f"\nDataset v3 successfully written:")
    print(f"  Train: {len(v3_train):,} positions")
    print(f"  Val:   {len(v3_val):,} positions")
    print(f"  Test:  {len(v3_test):,} positions")
    print(f"  Total: {total_positions:,} positions")

    all_labeled_new = labeled_train + labeled_val + labeled_test
    manifest = {
        "dataset_version": "v3_phase_balanced",
        "total_positions": total_positions,
        "partitions": {
            "train": len(v3_train),
            "val": len(v3_val),
            "test": len(v3_test),
        },
        "endgame_composition": {
            "total_new_endgame_positions": len(all_labeled_new),
            "pawn_endgames": sum(1 for item in all_labeled_new if item.get("subtype") == "pawn_endgame"),
            "rook_endgames": sum(1 for item in all_labeled_new if item.get("subtype") == "rook_endgame"),
            "minor_piece_endgames": sum(1 for item in all_labeled_new if item.get("subtype") == "minor_piece_endgame"),
            "opposite_bishops": sum(1 for item in all_labeled_new if item.get("subtype") == "opposite_bishops"),
            "queenless_middlegames": sum(1 for item in all_labeled_new if item.get("subtype") == "queenless_middlegame"),
            "locked_pawn_structures": sum(1 for item in all_labeled_new if item.get("subtype") == "locked_pawn_structure"),
        },
        "teacher": {
            "engine": "Stockfish 19 x64 AVX2",
            "sha256": SF_SHA256,
            "depth": 10,
            "workers": NUM_WORKERS,
        },
        "provenance": {
            "historical_v2_positions": 100000,
            "v3_augmented_positions": 50000,
            "source_archive": "lichess_elite_2020-06.zip",
            "game_ranges": {
                "train": "15,000 .. 37,000",
                "val": "38,000 .. 44,000",
                "test": "45,000 .. 51,000"
            },
            "source_games_partitioned": True,
            "zero_leakage_verified": True,
        }
    }
    with open(OUT_DATA_DIR / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSaved dataset manifest to {OUT_DATA_DIR / 'dataset_manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
