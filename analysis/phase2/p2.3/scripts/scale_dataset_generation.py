import os
import sys
import json
import time
import math
import hashlib
import random
import chess

from generate_search_grounded_pilot import ScoringUciEngine, R1_EXE, R1_HASH, sigmoid

REPO_ROOT = r"E:\ChessXML\project-janus-phase1"
DATA_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/data")
RAW_DIR = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/raw")
OPENINGS_FILE = os.path.join(REPO_ROOT, "analysis/v0.56/corpus/independent_openings_v056.json")

def generate_scaled_corpus(additional_games=75, depth=4, target_new_pos=5050):
    print(f"=== PHASE 8: SCALING SEARCH-GROUNDED DATASET (+{target_new_pos} POSITIONS) ===")
    
    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        openings = json.load(f)
        
    engine = ScoringUciEngine(R1_EXE)
    new_positions = []
    games = []
    t0 = time.time()
    
    try:
        for g_idx in range(additional_games):
            # Reverse opening selection to maximize diversity from pilot
            op_idx = len(openings) - 1 - (g_idx % len(openings))
            op = openings[op_idx]
            op_id = op.get("opening_id", f"OP_SCALED_{g_idx:03d}")
            op_moves = op.get("uci_sequence", [])
            
            board = chess.Board()
            for m_str in op_moves:
                board.push(chess.Move.from_uci(m_str))
                
            game_id = f"SCALED_G_{g_idx:04d}"
            played_moves = list(op_moves)
            game_pos_list = []
            
            max_plies = 85
            res_str = "*"
            
            while len(played_moves) < max_plies and not board.is_game_over(claim_draw=True):
                moves_str = " ".join(played_moves)
                bm, score_cp, mate = engine.search_depth(moves_str, depth)
                
                if not bm or bm == "(none)":
                    res_str = "0-1" if board.turn == chess.WHITE else "1-0"
                    break
                try:
                    mv = chess.Move.from_uci(bm)
                except Exception:
                    res_str = "0-1" if board.turn == chess.WHITE else "1-0"
                    break
                if mv not in board.legal_moves:
                    res_str = "0-1" if board.turn == chess.WHITE else "1-0"
                    break
                    
                fen = board.fen()
                fen_checksum = hashlib.sha256(fen.encode("utf-8")).hexdigest()[:16]
                ply = len(played_moves)
                stm_str = "w" if board.turn == chess.WHITE else "b"
                
                game_pos_list.append({
                    "fen": fen,
                    "game_id": game_id,
                    "opening_id": op_id,
                    "ply": ply,
                    "stm": stm_str,
                    "teacher_engine": "Janus_Classical_R1",
                    "teacher_exe_sha256": R1_HASH,
                    "teacher_depth": depth,
                    "teacher_score_perspective": "STM",
                    "teacher_score_cp": score_cp,
                    "teacher_mate": mate,
                    "position_checksum": fen_checksum
                })
                
                board.push(mv)
                played_moves.append(bm)
                
            if board.is_checkmate():
                res_str = "0-1" if board.turn == chess.WHITE else "1-0"
            elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
                res_str = "1/2-1/2"
            elif res_str == "*":
                res_str = "1/2-1/2"
                
            res_w = 1.0 if res_str == "1-0" else (0.0 if res_str == "0-1" else 0.5)
            
            for pos in game_pos_list:
                z = res_w if pos["stm"] == "w" else (1.0 - res_w)
                pos["game_result"] = res_str
                pos["target_outcome"] = z
                pos["target_score_prob"] = round(sigmoid(pos["teacher_score_cp"] / 400.0), 6)
                pos["lambda_target"] = round(0.8 * pos["target_score_prob"] + 0.2 * z, 6)
                new_positions.append(pos)
                
            games.append({"game_id": game_id, "plies": len(played_moves), "result": res_str})
            if (g_idx + 1) % 10 == 0 or len(new_positions) >= target_new_pos:
                print(f"  Scaled Batch Game {g_idx+1}/{additional_games}: {res_str} | Accumulated: {len(new_positions)}")
            if len(new_positions) >= target_new_pos:
                break
                
    finally:
        engine.close()
        
    elapsed = time.time() - t0
    print(f"Scaled generation batch complete: {len(new_positions)} positions in {elapsed:.1f}s.")
    
    # Load pilot positions
    pilot_positions = []
    for fname in ["pilot_train.jsonl", "pilot_val.jsonl", "pilot_test.jsonl"]:
        p = os.path.join(DATA_DIR, fname)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        pilot_positions.append(json.loads(line))
                        
    combined_positions = pilot_positions + new_positions
    
    # Deduplicate by FEN
    seen_fens = {}
    deduped = []
    for pos in combined_positions:
        fen = pos["fen"]
        if fen not in seen_fens:
            seen_fens[fen] = pos
            deduped.append(pos)
            
    print(f"Total Combined Positions: {len(combined_positions)} | Unique Deduplicated: {len(deduped)}")
    
    # Clean partition by game_id
    game_to_positions = {}
    for pos in deduped:
        gid = pos["game_id"]
        if gid not in game_to_positions:
            game_to_positions[gid] = []
        game_to_positions[gid].append(pos)
        
    all_gids = list(game_to_positions.keys())
    random.seed(42)
    random.shuffle(all_gids)
    
    n_train_g = int(len(all_gids) * 0.8)
    n_val_g = int(len(all_gids) * 0.1)
    
    train_gids = set(all_gids[:n_train_g])
    val_gids = set(all_gids[n_train_g:n_train_g+n_val_g])
    test_gids = set(all_gids[n_train_g+n_val_g:])
    
    scaled_train = [p for gid in train_gids for p in game_to_positions[gid]]
    scaled_val = [p for gid in val_gids for p in game_to_positions[gid]]
    scaled_test = [p for gid in test_gids for p in game_to_positions[gid]]
    
    # Leakage check
    train_fens = set(p["fen"] for p in scaled_train)
    val_fens = set(p["fen"] for p in scaled_val)
    test_fens = set(p["fen"] for p in scaled_test)
    
    leakage = len(train_fens.intersection(val_fens)) + len(train_fens.intersection(test_fens)) + len(val_fens.intersection(test_fens))
    print(f"Scaled Partition: Train={len(scaled_train)} | Val={len(scaled_val)} | Test={len(scaled_test)}")
    print(f"Cross-Partition Leakage: {leakage} (100% Clean Isolation)")
    assert leakage == 0, "Leakage detected in scaled dataset!"
    
    # Save files
    with open(os.path.join(DATA_DIR, "scaled_train.jsonl"), "w", encoding="utf-8") as f:
        for r in scaled_train: r["partition"] = "train"; f.write(json.dumps(r) + "\n")
    with open(os.path.join(DATA_DIR, "scaled_val.jsonl"), "w", encoding="utf-8") as f:
        for r in scaled_val: r["partition"] = "val"; f.write(json.dumps(r) + "\n")
    with open(os.path.join(DATA_DIR, "scaled_test.jsonl"), "w", encoding="utf-8") as f:
        for r in scaled_test: r["partition"] = "test"; f.write(json.dumps(r) + "\n")
        
    manifest = {
        "pipeline": "P2.3_Scaled_Search_Grounded_Corpus",
        "total_games": len(all_gids),
        "total_positions_deduped": len(deduped),
        "partitions": {
            "train": {"positions": len(scaled_train), "games": len(train_gids)},
            "val": {"positions": len(scaled_val), "games": len(val_gids)},
            "test": {"positions": len(scaled_test), "games": len(test_gids)}
        },
        "leakage_count": 0,
        "compute_time_sec": round(elapsed, 1)
    }
    
    with open(os.path.join(RAW_DIR, "scaled_data_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("Saved scaled_data_manifest.json")

if __name__ == "__main__":
    generate_scaled_corpus(additional_games=75, depth=4, target_new_pos=5050)
