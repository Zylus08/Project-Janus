import json
import statistics
import time
from pathlib import Path
import chess
import chess.polyglot

ROOT = Path("E:/ChessXML/project-janus")
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))

def benchmark_suite(key_mode: str, depth: int, reps: int = 5):
    all_runs = []
    for r in range(reps):
        total_time = 0.0
        total_nodes = 0
        pos_results = []
        for p in positions_data:
            eng = JanusSearch()
            if key_mode == "fen":
                eng._key = lambda b: b.fen(en_passant="legal")
            else:
                eng._key = lambda b: chess.polyglot.zobrist_hash(b)
            
            b = chess.Board(p["fen"])
            eng.tt.clear()
            res = eng.search(b, max_depth=depth)
            total_time += res.elapsed
            total_nodes += res.nodes
            pos_results.append({
                "id": p["id"],
                "nodes": res.nodes,
                "best_move": None if res.best_move is None else res.best_move.uci(),
                "score": res.score,
                "elapsed": round(res.elapsed, 4),
            })
        all_runs.append({
            "run": r + 1,
            "total_nodes": total_nodes,
            "total_elapsed_seconds": round(total_time, 4),
            "results": pos_results,
        })
    times = [r["total_elapsed_seconds"] for r in all_runs]
    stats = {
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "mean": round(statistics.mean(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
    }
    return {"runs": all_runs, "stats": stats}

print("Running 5 contemporary Depth 3 runs with FEN keys...")
fen_d3 = benchmark_suite("fen", 3, 5)
print(f"FEN Depth 3: median={fen_d3['stats']['median']}s (min={fen_d3['stats']['min']}s, max={fen_d3['stats']['max']}s)")

print("Running 5 contemporary Depth 3 runs with Zobrist keys...")
zob_d3 = benchmark_suite("zobrist", 3, 5)
print(f"Zobrist Depth 3: median={zob_d3['stats']['median']}s (min={zob_d3['stats']['min']}s, max={zob_d3['stats']['max']}s)")

print("Running 5 contemporary Depth 4 runs with FEN keys...")
fen_d4 = benchmark_suite("fen", 4, 5)
print(f"FEN Depth 4: median={fen_d4['stats']['median']}s (min={fen_d4['stats']['min']}s, max={fen_d4['stats']['max']}s)")

print("Running 5 contemporary Depth 4 runs with Zobrist keys...")
zob_d4 = benchmark_suite("zobrist", 4, 5)
print(f"Zobrist Depth 4: median={zob_d4['stats']['median']}s (min={zob_d4['stats']['min']}s, max={zob_d4['stats']['max']}s)")

d3_sp = (fen_d3['stats']['median'] - zob_d3['stats']['median']) / fen_d3['stats']['median'] * 100
d4_sp = (fen_d4['stats']['median'] - zob_d4['stats']['median']) / fen_d4['stats']['median'] * 100

print(f"\nContemporary Depth 3 speedup: {d3_sp:+.1f}%")
print(f"Contemporary Depth 4 speedup: {d4_sp:+.1f}%")

out = {
    "fen_depth_3": fen_d3,
    "zobrist_depth_3": zob_d3,
    "fen_depth_4": fen_d4,
    "zobrist_depth_4": zob_d4,
    "contemporary_speedup": {
        "depth_3": round(d3_sp, 2),
        "depth_4": round(d4_sp, 2),
    }
}
(ROOT / "analysis" / "v0.12" / "contemporary_fen_vs_zobrist.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("Saved contemporary benchmark data to analysis/v0.12/contemporary_fen_vs_zobrist.json")
