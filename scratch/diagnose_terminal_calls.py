import json
import os
import sys

os.environ['TEMP'] = 'E:\\ChessXML\\project-janus\\scratch'
os.environ['TMP'] = 'E:\\ChessXML\\project-janus\\scratch'
sys.path.insert(0, 'src')

import chess
from janus.search import JanusSearch

positions = json.load(open("benchmarks/positions.json"))

class CountingSearch(JanusSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal_calls_negamax = 0
        self.terminal_calls_quiescence = 0
        self.is_checkmate_calls = 0
        self.is_stalemate_calls = 0
        self.is_insufficient_material_calls = 0
        self.is_repetition_calls = 0

    def _terminal_score(self, board, ply):
        # We know who called based on stack or context
        return super()._terminal_score(board, ply)

    def _negamax(self, board, depth, alpha, beta, ply):
        self.terminal_calls_negamax += 1
        return super()._negamax(board, depth, alpha, beta, ply)

    def _quiescence(self, board, alpha, beta, ply):
        self.terminal_calls_quiescence += 1
        return super()._quiescence(board, alpha, beta, ply)

for depth in [3, 4]:
    s = CountingSearch()
    total_nodes = 0
    pos_data = []
    for p in positions:
        board = chess.Board(p["fen"])
        s.tt.clear()
        res = s.search(board, max_depth=depth)
        total_nodes += res.nodes
        pos_data.append({
            "id": p["id"],
            "nodes": res.nodes,
            "score": res.score,
            "best_move": res.best_move.uci() if res.best_move else None,
            "pv": [m.uci() for m in res.pv],
        })

    print(f"=== DEPTH {depth} INVOCATION COUNTS ===")
    print(f"Total Nodes: {total_nodes}")
    print(f"_negamax nodes: {s.terminal_calls_negamax}")
    print(f"_quiescence nodes: {s.terminal_calls_quiescence}")
    print(f"Total _terminal_score invocations: {s.terminal_calls_negamax + s.terminal_calls_quiescence}")
    print(f"Positions: {pos_data}\n")
