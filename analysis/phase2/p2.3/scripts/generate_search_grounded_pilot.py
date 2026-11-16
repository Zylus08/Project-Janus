import os
import sys
import json
import time
import math
import hashlib
import random
import subprocess
import chess

REPO_ROOT = r"E:\ChessXML\project-janus-phase1"
R1_EXE = os.path.join(REPO_ROOT, "analysis/phase1/p1.22/control/janus_classical_r1.exe")
OPENINGS_FILE = os.path.join(REPO_ROOT, "analysis/v0.56/corpus/independent_openings_v056.json")
R1_HASH = "7312B2B73CD9D40F108EE1B5F3903632A2A7805B19BC73082A796922DE66029B"

class ScoringUciEngine:
    def __init__(self, exe_path):
        self.proc = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        self.send("setoption name Threads value 1")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def search_depth(self, moves_str, depth=5):
        if moves_str:
            self.send(f"position startpos moves {moves_str}")
        else:
            self.send("position startpos")
            
        self.send(f"go depth {depth}")
        
        bestmove = None
        score_cp = 0
        mate_score = None
        
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "score" in line:
                parts = line.split()
                if "cp" in parts:
                    idx = parts.index("cp")
                    score_cp = int(parts[idx + 1])
                elif "mate" in parts:
                    idx = parts.index("mate")
                    mate_score = int(parts[idx + 1])
                    score_cp = 2000 if mate_score > 0 else -2000
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break
                
        return bestmove, score_cp, mate_score

    def close(self):
        try:
            self.send("quit")
            self.proc.kill()
        except Exception:
            pass

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def generate_pilot_dataset(n_games=100, depth=5, target_positions=5000):
    print(f"=== PHASE 4: GENERATING SEARCH-GROUNDED PILOT DATASET ({target_positions} POSITIONS) ===")
    
    with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
        openings = json.load(f)
        
    engine = ScoringUciEngine(R1_EXE)
    
    games = []
    all_positions = []
    t0 = time.time()
    
    try:
        for g_idx in range(n_games):
            op = openings[g_idx % len(openings)]
            op_id = op.get("opening_id", f"OP_{g_idx:03d}")
            op_moves = op.get("uci_sequence", [])
            
            board = chess.Board()
            for m_str in op_moves:
                board.push(chess.Move.from_uci(m_str))
                
            game_id = f"PILOT_G_{g_idx:04d}"
            played_moves = list(op_moves)
            game_pos_list = []
            
            max_plies = 90
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
                    
                # Record position
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
            
            # Finalize records for this game
            for pos in game_pos_list:
                z = res_w if pos["stm"] == "w" else (1.0 - res_w)
                pos["game_result"] = res_str
                pos["target_outcome"] = z
                pos["target_score_prob"] = round(sigmoid(pos["teacher_score_cp"] / 400.0), 6)
                pos["lambda_target"] = round(0.8 * pos["target_score_prob"] + 0.2 * z, 6)
                all_positions.append(pos)
                
            games.append({
                "game_id": game_id,
                "opening_id": op_id,
                "result": res_str,
                "plies": len(played_moves),
                "positions_count": len(game_pos_list)
            })
            
            if (g_idx + 1) % 10 == 0 or len(all_positions) >= target_positions:
                print(f"  Game {g_idx+1}/{n_games}: {res_str} ({len(played_moves)} plies) | Accumulated Positions: {len(all_positions)}")
                
            if len(all_positions) >= target_positions:
                break
                
    finally:
        engine.close()
        
    elapsed = time.time() - t0
    print(f"\nGeneration completed in {elapsed:.1f}s ({len(all_positions)} positions from {len(games)} games).")
    
    # Clean partition by Game ID into Train (80%), Val (10%), Test (10%)
    random.seed(42)
    game_ids = [g["game_id"] for g in games]
    random.shuffle(game_ids)
    
    n_train = int(len(game_ids) * 0.8)
    n_val = int(len(game_ids) * 0.1)
    
    train_ids = set(game_ids[:n_train])
    val_ids = set(game_ids[n_train:n_train+n_val])
    test_ids = set(game_ids[n_train+n_val:])
    
    train_recs = []
    val_recs = []
    test_recs = []
    
    for pos in all_positions:
        gid = pos["game_id"]
        if gid in train_ids:
            pos["partition"] = "train"
            train_recs.append(pos)
        elif gid in val_ids:
            pos["partition"] = "val"
            val_recs.append(pos)
        else:
            pos["partition"] = "test"
            test_recs.append(pos)
            
    # Verify ZERO cross-partition FEN leakage
    train_fens = set(p["fen"] for p in train_recs)
    val_fens = set(p["fen"] for p in val_recs)
    test_fens = set(p["fen"] for p in test_recs)
    
    leakage_train_val = len(train_fens.intersection(val_fens))
    leakage_train_test = len(train_fens.intersection(test_fens))
    leakage_val_test = len(val_fens.intersection(test_fens))
    total_leakage = leakage_train_val + leakage_train_test + leakage_val_test
    
    print("\n--- DATASET PARTITION AUDIT ---")
    print(f"Train Records: {len(train_recs)} ({len(train_fens)} unique FENs, {len(train_ids)} games)")
    print(f"Val Records  : {len(val_recs)} ({len(val_fens)} unique FENs, {len(val_ids)} games)")
    print(f"Test Records : {len(test_recs)} ({len(test_fens)} unique FENs, {len(test_ids)} games)")
    print(f"Cross-Partition FEN Leakage: {total_leakage} FENs (100.0% clean isolation)")
    assert total_leakage == 0, f"Detected {total_leakage} leaking FENs across partitions!"
    
    # Write JSONL files
    data_dir = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/data")
    train_path = os.path.join(data_dir, "pilot_train.jsonl")
    val_path = os.path.join(data_dir, "pilot_val.jsonl")
    test_path = os.path.join(data_dir, "pilot_test.jsonl")
    
    with open(train_path, "w", encoding="utf-8") as f:
        for r in train_recs: f.write(json.dumps(r) + "\n")
    with open(val_path, "w", encoding="utf-8") as f:
        for r in val_recs: f.write(json.dumps(r) + "\n")
    with open(test_path, "w", encoding="utf-8") as f:
        for r in test_recs: f.write(json.dumps(r) + "\n")
        
    def hash_file(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536): h.update(chunk)
        return h.hexdigest().upper()
        
    manifest = {
        "pipeline": "P2.3_Search_Grounded_Data_Pilot",
        "total_games": len(games),
        "total_positions": len(all_positions),
        "teacher": {
            "engine": "Janus_Classical_R1",
            "exe_sha256": R1_HASH,
            "depth": depth
        },
        "partitions": {
            "train": {"positions": len(train_recs), "games": len(train_ids), "sha256": hash_file(train_path)},
            "val": {"positions": len(val_recs), "games": len(val_ids), "sha256": hash_file(val_path)},
            "test": {"positions": len(test_recs), "games": len(test_ids), "sha256": hash_file(test_path)}
        },
        "leakage_count": total_leakage,
        "generation_time_sec": round(elapsed, 1)
    }
    
    manifest_path = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/raw/pilot_data_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Pilot Data Manifest written to {manifest_path}")

if __name__ == "__main__":
    generate_pilot_dataset(n_games=100, depth=5, target_positions=5000)
