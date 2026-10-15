import json
import time
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus")
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, MVV_LVA_PIECE_VALUES

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))

class OptimizedJanusSearch(JanusSearch):
    def _ordered_moves(self, board, tt_move=None, ply=0):
        moves = list(board.legal_moves)
        if len(moves) <= 1:
            return moves

        k1 = self.killers[ply][0] if ply < len(self.killers) else None
        k2 = self.killers[ply][1] if ply < len(self.killers) else None
        history = self.history if self.enable_history else None

        def score_move(move):
            if tt_move is not None and move == tt_move:
                return 10_000_000

            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                victim_value = 100 if board.is_en_passant(move) else (
                    0 if victim is None else MVV_LVA_PIECE_VALUES[victim.piece_type]
                )
                attacker = board.piece_at(move.from_square)
                attacker_value = (
                    0 if attacker is None else MVV_LVA_PIECE_VALUES[attacker.piece_type]
                )
                score = 1_000_000 + 10 * victim_value - attacker_value
                if move.promotion:
                    score += 800_000 + move.promotion
                return score

            if move.promotion:
                return 800_000 + move.promotion

            if move == k1:
                return 700_000
            if move == k2:
                return 600_000

            if history is not None:
                return history[move.from_square][move.to_square]

            return 0

        moves.sort(key=score_move, reverse=True)
        return moves

print("Testing node count equivalence on Depth 3 and Depth 4:")
for depth in (3, 4):
    print(f"\n--- Depth {depth} ---")
    tot_nodes_orig = 0
    tot_nodes_opt = 0
    for p in positions_data:
        b = chess.Board(p["fen"])
        
        orig = JanusSearch(enable_history=True)
        res_orig = orig.search(b, max_depth=depth)
        
        opt = OptimizedJanusSearch(enable_history=True)
        res_opt = opt.search(b, max_depth=depth)
        
        tot_nodes_orig += res_orig.nodes
        tot_nodes_opt += res_opt.nodes
        
        assert res_orig.nodes == res_opt.nodes, f"Node mismatch on {p['id']}: {res_orig.nodes} vs {res_opt.nodes}"
        assert res_orig.best_move == res_opt.best_move, f"Best move mismatch on {p['id']}: {res_orig.best_move} vs {res_opt.best_move}"
        assert res_orig.score == res_opt.score, f"Score mismatch on {p['id']}: {res_orig.score} vs {res_opt.score}"
        print(f"  {p['id']:<18}: nodes={res_opt.nodes}, best={res_opt.best_move}, score={res_opt.score} [OK]")
    print(f"Total Depth {depth} nodes: Orig={tot_nodes_orig}, Opt={tot_nodes_opt} (EXACT MATCH!)")

# Speed benchmark
print("\n--- Speed Comparison (10 runs at Depth 4) ---")
times_orig = []
times_opt = []
for r in range(10):
    t0 = time.perf_counter()
    for p in positions_data:
        b = chess.Board(p["fen"])
        JanusSearch(enable_history=True).search(b, max_depth=4)
    t_orig = time.perf_counter() - t0
    times_orig.append(t_orig)

    t0 = time.perf_counter()
    for p in positions_data:
        b = chess.Board(p["fen"])
        OptimizedJanusSearch(enable_history=True).search(b, max_depth=4)
    t_opt = time.perf_counter() - t0
    times_opt.append(t_opt)
    print(f"  Run {r+1:2d}: Orig={t_orig:.4f}s, Opt={t_opt:.4f}s (delta: {t_orig - t_opt:+.4f}s, {(t_orig - t_opt)/t_orig*100:+.1f}%)")

import statistics
med_orig = statistics.median(times_orig)
med_opt = statistics.median(times_opt)
print(f"\nMedian: Orig={med_orig:.4f}s, Opt={med_opt:.4f}s (Speedup: {(med_orig - med_opt)/med_orig*100:+.2f}%)")
