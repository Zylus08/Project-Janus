#!/usr/bin/env python3
"""
janus_h3_uci.py
Standalone UCI Engine Bridge for Candidate Janus Hybrid H3 (HalfKP-40960 NNUE).
Speaks standard UCI protocol over stdin/stdout.
Uses INT16/INT8 quantized weights from janus_nnue_h3.bin.
"""

import os
import sys
import time
import struct
import chess
import numpy as np

# Load quantized weights
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
BIN_PATH = os.path.join(REPO_ROOT, "analysis", "phase2", "p2.3", "models", "janus_nnue_h3.bin")

with open(BIN_PATH, "rb") as f:
    header = f.read(64)
    magic, ver, s_id, n_feat, n_hid, n_d1, n_d2, s_ft, s_l1, s_l2, tau = struct.unpack("<4sIIIIIIIIII", header[:44])
    assert magic == b"JNN3", f"Invalid magic: {magic}"
    
    ft_w = np.frombuffer(f.read(n_feat * n_hid * 2), dtype=np.int16).reshape(n_feat, n_hid)
    ft_b = np.frombuffer(f.read(n_hid * 2), dtype=np.int16)
    fc1_w = np.frombuffer(f.read(n_d1 * (n_hid * 2) * 1), dtype=np.int8).reshape(n_d1, n_hid * 2).astype(np.int32)
    fc1_b = np.frombuffer(f.read(n_d1 * 4), dtype=np.int32)
    fc2_w = np.frombuffer(f.read(n_d2 * n_d1 * 1), dtype=np.int8).reshape(n_d2, n_d1).astype(np.int32)
    fc2_b = np.frombuffer(f.read(n_d2 * 4), dtype=np.int32)

TAU = float(tau)

PIECE_TO_TYPE_INDEX = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}

def flip_square(sq: int) -> int:
    return sq ^ 56

def evaluate_board_h3(board: chess.Board) -> int:
    white_k = board.king(chess.WHITE)
    black_k = board.king(chess.BLACK)
    if white_k is None or black_k is None:
        return 0
    black_k_flipped = flip_square(black_k)
    
    wf = []
    bf = []
    
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p is None or p.piece_type == chess.KING:
            continue
        t_idx = PIECE_TO_TYPE_INDEX[p.piece_type]
        cat_w = t_idx if p.color == chess.WHITE else 5 + t_idx
        wf.append(white_k * 640 + cat_w * 64 + sq)
        
        cat_b = t_idx if p.color == chess.BLACK else 5 + t_idx
        bf.append(black_k_flipped * 640 + cat_b * 64 + flip_square(sq))
        
    stm = 1 if board.turn == chess.WHITE else 0
    acc_w = np.copy(ft_b) + (np.sum(ft_w[wf], axis=0) if wf else 0)
    acc_b = np.copy(ft_b) + (np.sum(ft_w[bf], axis=0) if bf else 0)
    
    h_w = np.clip(acc_w, 0, 256)
    h_b = np.clip(acc_b, 0, 256)
    
    friendly = h_w if stm == 1 else h_b
    enemy = h_b if stm == 1 else h_w
    cat_in = np.concatenate([friendly, enemy])
    
    l1 = np.clip((np.dot(fc1_w, cat_in) + fc1_b) // 256, 0, 128)
    l2 = np.dot(fc2_w, l1) + fc2_b
    score_cp = int((l2[0] / 16384.0) * TAU)
    return score_cp

# Simple Alpha-Beta Negamax Search with TT and Quiescence
PIECE_VALS = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}

class H3SearchEngine:
    def __init__(self):
        self.tt = {}
        self.nodes = 0
        self.time_limit = 0.5
        self.start_time = 0.0

    def quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int) -> int:
        self.nodes += 1
        stand_pat = evaluate_board_h3(board)
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
            
        # Captures ordered by MVV-LVA
        captures = [m for m in board.legal_moves if board.is_capture(m)]
        captures.sort(key=lambda m: PIECE_VALS.get(board.piece_type_at(m.to_square) or chess.PAWN, 100) - 
                                    PIECE_VALS.get(board.piece_type_at(m.from_square) or chess.PAWN, 100), reverse=True)
                                    
        for m in captures:
            board.push(m)
            try:
                score = -self.quiescence(board, -beta, -alpha, ply + 1)
            finally:
                board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def negamax(self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int) -> int:
        self.nodes += 1
        if time.perf_counter() - self.start_time > self.time_limit:
            raise TimeoutError()
            
        if board.is_checkmate():
            return -29000 + ply
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.halfmove_clock >= 100:
            return 0
            
        if depth <= 0:
            return self.quiescence(board, alpha, beta, ply)
            
        key = (board.zobrist_hash() if hasattr(board, 'zobrist_hash') else hash(board.fen()), board.turn)
        tt_entry = self.tt.get(key)
        best_move = None
        if tt_entry:
            tt_d, tt_score, tt_flag, tt_best = tt_entry
            if tt_d >= depth:
                if tt_flag == 'EXACT':
                    return tt_score
                elif tt_flag == 'LOWER' and tt_score > alpha:
                    alpha = tt_score
                elif tt_flag == 'UPPER' and tt_score < beta:
                    beta = tt_score
                if alpha >= beta:
                    return tt_score
            best_move = tt_best

        moves = list(board.legal_moves)
        if not moves:
            return 0
            
        # Move ordering
        def move_score(m):
            if m == best_move:
                return 100000
            s = 0
            if board.is_capture(m):
                victim = board.piece_type_at(m.to_square) or chess.PAWN
                attacker = board.piece_type_at(m.from_square) or chess.PAWN
                s = 10000 + PIECE_VALS.get(victim, 100) * 10 - PIECE_VALS.get(attacker, 100)
            return s
            
        moves.sort(key=move_score, reverse=True)
        
        orig_alpha = alpha
        best_val = -30000
        cur_best_move = moves[0]
        
        for m in moves:
            board.push(m)
            try:
                val = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            finally:
                board.pop()
            
            if val > best_val:
                best_val = val
                cur_best_move = m
            if val > alpha:
                alpha = val
            if alpha >= beta:
                break
                
        # Store in TT
        flag = 'EXACT'
        if best_val <= orig_alpha:
            flag = 'UPPER'
        elif best_val >= beta:
            flag = 'LOWER'
        self.tt[key] = (depth, best_val, flag, cur_best_move)
        
        return best_val

    def search(self, board: chess.Board, time_limit: float = 0.5, max_depth: int = 5) -> chess.Move:
        self.nodes = 0
        self.start_time = time.perf_counter()
        self.time_limit = time_limit
        
        search_board = board.copy()
        legal_moves = list(search_board.legal_moves)
        if not legal_moves:
            return None
        if len(legal_moves) == 1:
            return legal_moves[0]
            
        best_move = legal_moves[0]
        
        for d in range(1, max_depth + 1):
            try:
                val = self.negamax(search_board, d, -30000, 30000, 0)
                key = (search_board.zobrist_hash() if hasattr(search_board, 'zobrist_hash') else hash(search_board.fen()), search_board.turn)
                if key in self.tt and self.tt[key][3] is not None:
                    best_move = self.tt[key][3]
            except TimeoutError:
                break
                
        return best_move

def main():
    engine = H3SearchEngine()
    board = chess.Board()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            cmd = parts[0]
            
            if cmd == "uci":
                print("id name Janus_Hybrid_H3")
                print("id author Project Janus Team")
                print("option name UCI_Variant type combo default H3 var H3")
                print("uciok", flush=True)
            elif cmd == "isready":
                print("readyok", flush=True)
            elif cmd == "ucinewgame":
                engine.tt.clear()
                board.reset()
            elif cmd == "position":
                if parts[1] == "startpos":
                    board.reset()
                    if len(parts) > 2 and parts[2] == "moves":
                        for m_str in parts[3:]:
                            board.push_uci(m_str)
                elif parts[1] == "fen":
                    fen_parts = []
                    idx = 2
                    while idx < len(parts) and parts[idx] != "moves":
                        fen_parts.append(parts[idx])
                        idx += 1
                    board.set_fen(" ".join(fen_parts))
                    if idx < len(parts) and parts[idx] == "moves":
                        for m_str in parts[idx+1:]:
                            board.push_uci(m_str)
            elif cmd == "go":
                wtime = 5000
                btime = 5000
                winc = 50
                binc = 50
                movetime = None
                depth = 4
                
                for i in range(1, len(parts)):
                    if parts[i] == "wtime" and i + 1 < len(parts):
                        wtime = int(parts[i+1])
                    elif parts[i] == "btime" and i + 1 < len(parts):
                        btime = int(parts[i+1])
                    elif parts[i] == "winc" and i + 1 < len(parts):
                        winc = int(parts[i+1])
                    elif parts[i] == "binc" and i + 1 < len(parts):
                        binc = int(parts[i+1])
                    elif parts[i] == "movetime" and i + 1 < len(parts):
                        movetime = int(parts[i+1])
                    elif parts[i] == "depth" and i + 1 < len(parts):
                        depth = int(parts[i+1])
                        
                if movetime is not None:
                    limit_sec = max(0.02, (movetime / 1000.0) * 0.9)
                else:
                    my_time = wtime if board.turn == chess.WHITE else btime
                    my_inc = winc if board.turn == chess.WHITE else binc
                    limit_sec = max(0.02, min(2.0, (my_time / 1000.0) / 30.0 + (my_inc / 1000.0) * 0.8))
                    
                best = engine.search(board, time_limit=limit_sec, max_depth=depth)
                best_str = best.uci() if best else "(none)"
                print(f"bestmove {best_str}", flush=True)
            elif cmd == "quit":
                break
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            # Emergency fallback
            sys.stderr.write(f"Engine error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
