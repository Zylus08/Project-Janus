import json
import chess
from janus.search import JanusSearch

with open("analysis/v0.44/diagnostic_positions.json") as f:
    pos = json.load(f)

for p in pos[:12]:
    b = chess.Board(p["fen"])
    e = JanusSearch(enable_rfp=False)
    m2 = e.search(b.copy(), max_depth=2).best_move.uci()
    m3 = e.search(b.copy(), max_depth=3).best_move.uci()
    m4 = e.search(b.copy(), max_depth=4).best_move.uci()
    print(f"Pair {p['pair']:2d} ({p['color']:5s}) ply {p['ply']:2d}: Match K0={p['k0_move']}, RFP={p['rfp_move']} | d2={m2}, d3={m3}, d4={m4}")

