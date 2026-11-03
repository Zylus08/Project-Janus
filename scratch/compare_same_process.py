import sys
import time
from pathlib import Path
import chess

ROOT = Path("e:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch

def run_d4(engine):
    positions_file = ROOT / "benchmarks" / "positions.json"
    import json
    positions = json.loads(positions_file.read_text(encoding="utf-8"))
    
    t0 = time.perf_counter()
    total_nodes = 0
    for pos in positions:
        b = chess.Board(pos["fen"])
        engine.tt.clear()
        res = engine.search(b, max_depth=4)
        total_nodes += res.nodes
    elapsed = time.perf_counter() - t0
    return elapsed, total_nodes

print("Test 1: enable_pvs=False (Baseline)")
e1 = JanusSearch(enable_pvs=False)
t1, n1 = run_d4(e1)
print(f"Disabled: time={t1:.3f}s, nodes={n1}")

print("\nTest 2: enable_pvs=True (PVS)")
e2 = JanusSearch(enable_pvs=True)
t2, n2 = run_d4(e2)
print(f"Enabled:  time={t2:.3f}s, nodes={n2}")
