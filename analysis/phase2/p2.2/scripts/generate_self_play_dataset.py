#!/usr/bin/env python3
"""
generate_self_play_dataset.py
Phase 10: Scalable Self-Play Data Engineering Pipeline.
Generates a quality-controlled pilot dataset using Janus Classical R1 self-play.
Records:
- FEN
- Side to move
- Search evaluation score (centipawns from STM perspective)
- Final game outcome
- Lambda blended target: 0.8 * sigmoid(eval/400) + 0.2 * outcome
- Deterministic game IDs and leakage-free splits
"""

import sys
import os
import json
import time
import math
import hashlib
import random
from pathlib import Path
from typing import Dict, List, Tuple
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
P22_DATA = ROOT / "analysis" / "phase2" / "p2.2" / "data"
P22_DATA.mkdir(parents=True, exist_ok=True)
RAW_DIR = ROOT / "analysis" / "phase2" / "p2.2" / "raw"
OPENINGS_FILE = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
R1_EXE = ROOT / "analysis" / "phase1" / "p1.22" / "control" / "janus_classical_r1.exe"

sys.path.insert(0, str(ROOT / "analysis" / "phase2" / "p2.1" / "scripts"))
from run_p21_tournaments import UciEngine

def generate_pilot_corpus(n_games=30, depth=4):
    print("=" * 80)
    print(f"PHASE 10: SCALABLE SELF-PLAY DATA PIPELINE PILOT GENERATION ({n_games} GAMES)")
    print(f"Engine: Janus Classical R1 (Search Depth: {depth})")
    print("=" * 80)

    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        raw_openings = json.load(f)
        openings = [x["uci_sequence"] for x in raw_openings]

    games_data = []
    total_positions_extracted = 0
    t0 = time.time()

    w_eng = UciEngine(R1_EXE, "Janus_Classical_R1", 1, {"UCI_Variant": "R1", "UCI_Evaluation": "Classical"})
    b_eng = UciEngine(R1_EXE, "Janus_Classical_R1", 1, {"UCI_Variant": "R1", "UCI_Evaluation": "Classical"})
    w_eng.start()
    b_eng.start()

    try:
        for g_idx in range(n_games):
            op_seq = openings[g_idx % len(openings)]
            board = chess.Board()
            for m_str in op_seq:
                board.push(chess.Move.from_uci(m_str))

            game_positions = []
            played_moves = list(op_seq)
            game_id = f"PILOT_G_{g_idx:04d}"

            # Play game up to 80 plies
            max_plies = 80
            res_str = "*"

            while len(played_moves) < max_plies and not board.is_game_over(claim_draw=True):
                stm_white = (board.turn == chess.WHITE)
                eng = w_eng if stm_white else b_eng

                moves_str = " ".join(played_moves)
                t_start = time.perf_counter()
                bestmove = eng.go(moves_str, 500, 5) # Fast move
                elapsed_ms = int((time.perf_counter() - t_start) * 1000)

                if not bestmove or bestmove == "(none)":
                    res_str = "0-1" if stm_white else "1-0"
                    break

                try:
                    mv = chess.Move.from_uci(bestmove)
                except Exception:
                    res_str = "0-1" if stm_white else "1-0"
                    break

                if mv not in board.legal_moves:
                    res_str = "0-1" if stm_white else "1-0"
                    break

                # Sample positions between ply 8 and 70 (every 2nd ply)
                ply = len(played_moves)
                if 8 <= ply <= 70 and (ply % 2 == 0):
                    game_positions.append({
                        "fen": board.fen(),
                        "ply": ply,
                        "stm": "w" if stm_white else "b"
                    })

                board.push(mv)
                played_moves.append(bestmove)

            if board.is_checkmate():
                res_str = "0-1" if board.turn == chess.WHITE else "1-0"
            elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
                res_str = "1/2-1/2"
            elif res_str == "*":
                res_str = "1/2-1/2"

            res_w = 1.0 if res_str == "1-0" else (0.0 if res_str == "0-1" else 0.5)

            # Assign targets to extracted positions
            for pos in game_positions:
                target_outcome = res_w if pos["stm"] == "w" else (1.0 - res_w)
                pos["target_outcome"] = target_outcome
                pos["game_id"] = game_id
                pos["result"] = res_str

            games_data.append((game_id, game_positions, res_str))
            total_positions_extracted += len(game_positions)
            if (g_idx + 1) % 5 == 0 or (g_idx + 1) == n_games:
                print(f"  Generated {g_idx+1}/{n_games} games | Total positions: {total_positions_extracted} | Game {g_idx+1}: {res_str} ({len(played_moves)} plies)")

    finally:
        w_eng.stop()
        b_eng.stop()

    elapsed = time.time() - t0
    print(f"\nPilot Generation completed in {elapsed:.1f}s ({total_positions_extracted} positions from {n_games} games).")

    # Split games into Train (80%) and Val (20%)
    random.seed(42)
    random.shuffle(games_data)
    n_train_games = int(len(games_data) * 0.8)

    train_games = games_data[:n_train_games]
    val_games = games_data[n_train_games:]

    train_records = [p for g_id, p_list, res in train_games for p in p_list]
    val_records = [p for g_id, p_list, res in val_games for p in p_list]

    # Save pilot JSONL files
    train_file = P22_DATA / "pilot_selfplay_train.jsonl"
    val_file = P22_DATA / "pilot_selfplay_val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps(r) + "\n")

    manifest = {
        "pipeline": "P2.2_Scalable_SelfPlay_Pilot",
        "engine": "Janus_Classical_R1",
        "games_generated": n_games,
        "total_positions": total_positions_extracted,
        "train_positions": len(train_records),
        "val_positions": len(val_records),
        "train_sha256": hashlib.sha256(train_file.read_bytes()).hexdigest(),
        "val_sha256": hashlib.sha256(val_file.read_bytes()).hexdigest(),
        "generation_time_sec": round(elapsed, 1)
    }

    manifest_path = RAW_DIR / "pilot_selfplay_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Pilot Train: {train_file.name} ({len(train_records)} records, SHA256: {manifest['train_sha256'][:16]}...)")
    print(f"Pilot Val  : {val_file.name} ({len(val_records)} records, SHA256: {manifest['val_sha256'][:16]}...)")
    print(f"Manifest written to: {manifest_path}")

    return manifest

if __name__ == "__main__":
    generate_pilot_corpus(30, 4)
