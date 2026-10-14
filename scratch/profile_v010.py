import cProfile
import json
import os
import pstats
import statistics
import sys
import time
from io import StringIO

os.environ['TEMP'] = 'E:\\ChessXML\\project-janus\\scratch'
os.environ['TMP'] = 'E:\\ChessXML\\project-janus\\scratch'
sys.path.insert(0, 'src')

import chess
from janus.search import JanusSearch

positions_path = "benchmarks/positions.json"
with open(positions_path) as f:
    positions = json.load(f)

def run_benchmarks(depth: int, reps: int = 5):
    all_runs = []
    for r in range(reps):
        engine = JanusSearch()
        run_data = {"run": r + 1, "positions": [], "total_nodes": 0}
        t0 = time.perf_counter()
        for p in positions:
            board = chess.Board(p["fen"])
            engine.tt.clear()
            res = engine.search(board, max_depth=depth)
            run_data["total_nodes"] += res.nodes
            run_data["positions"].append({
                "id": p["id"],
                "nodes": res.nodes,
                "score": res.score,
                "best_move": res.best_move.uci() if res.best_move else None,
                "pv": [m.uci() for m in res.pv],
                "elapsed": res.elapsed,
            })
        run_data["total_time"] = time.perf_counter() - t0
        run_data["nps"] = round(run_data["total_nodes"] / run_data["total_time"]) if run_data["total_time"] > 0 else 0
        all_runs.append(run_data)
    return all_runs

def compute_dispersion(times):
    times_sorted = sorted(times)
    n = len(times_sorted)
    q1 = times_sorted[n // 4] if n >= 4 else times_sorted[0]
    q3 = times_sorted[(3 * n) // 4] if n >= 4 else times_sorted[-1]
    return {
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "mean": round(statistics.mean(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
        "iqr": round(q3 - q1, 4),
        "q1": round(q1, 4),
        "q3": round(q3, 4),
    }

print("Running 5 repetitions at Depth 3...")
d3_runs = run_benchmarks(3, 5)
d3_times = [r["total_time"] for r in d3_runs]
d3_stats = compute_dispersion(d3_times)
print(f"Depth 3 (5 runs): median={d3_stats['median']}s, min={d3_stats['min']}s, max={d3_stats['max']}s, iqr={d3_stats['iqr']}s")

print("Running 5 repetitions at Depth 4...")
d4_runs = run_benchmarks(4, 5)
d4_times = [r["total_time"] for r in d4_runs]
d4_stats = compute_dispersion(d4_times)
print(f"Depth 4 (5 runs): median={d4_stats['median']}s, min={d4_stats['min']}s, max={d4_stats['max']}s, iqr={d4_stats['iqr']}s")

# Check determinism across runs
for name, runs in [("Depth 3", d3_runs), ("Depth 4", d4_runs)]:
    nodes_set = {r["total_nodes"] for r in runs}
    assert len(nodes_set) == 1, f"{name} nodes not deterministic: {nodes_set}"
    for pos_idx in range(len(positions)):
        pos_id = positions[pos_idx]["id"]
        bm_set = {r["positions"][pos_idx]["best_move"] for r in runs}
        sc_set = {r["positions"][pos_idx]["score"] for r in runs}
        nd_set = {r["positions"][pos_idx]["nodes"] for r in runs}
        assert len(bm_set) == 1, f"{name} {pos_id} best_move varying: {bm_set}"
        assert len(sc_set) == 1, f"{name} {pos_id} score varying: {sc_set}"
        assert len(nd_set) == 1, f"{name} {pos_id} nodes varying: {nd_set}"
print("Determinism check passed for all positions and depths across all 5 runs!")

# Per-position timing dispersion at Depth 4
per_pos_d4 = {}
for pos_idx in range(len(positions)):
    pos_id = positions[pos_idx]["id"]
    pos_times = [r["positions"][pos_idx]["elapsed"] for r in d4_runs]
    nodes = d4_runs[0]["positions"][pos_idx]["nodes"]
    bm = d4_runs[0]["positions"][pos_idx]["best_move"]
    sc = d4_runs[0]["positions"][pos_idx]["score"]
    per_pos_d4[pos_id] = {
        "nodes": nodes,
        "score": sc,
        "best_move": bm,
        "dispersion": compute_dispersion(pos_times),
    }

# Profiling run at Depth 4
print("Running cProfile on 6 benchmark positions at Depth 4...")
pr = cProfile.Profile()
engine = JanusSearch()
pr.enable()
t0 = time.perf_counter()
for p in positions:
    board = chess.Board(p["fen"])
    engine.tt.clear()
    engine.search(board, max_depth=4)
profile_elapsed = time.perf_counter() - t0
pr.disable()

s_stream = StringIO()
ps = pstats.Stats(pr, stream=s_stream).sort_stats("cumtime")
ps.print_stats(60)
profile_text = s_stream.getvalue()

# Categorize profiling by subsystem
# Subsystems:
# 1. Move generation and sorting: _ordered_moves, _move_order_score, legal_moves, generate_legal_moves, sort
# 2. Evaluation: evaluate_side_to_move, evaluate_white, CENTER_BONUS, PIECE_VALUES, etc.
# 3. Quiescence search: _quiescence, _quiescence_moves, generate_legal_captures
# 4. Transposition table: _key, fen, _score_to_tt, _score_from_tt, tt.get, tt[...]
# 5. Search recursion & control: _negamax, board.push, board.pop, _check_stop, _terminal_score

subsystems = {
    "move_generation_and_ordering": 0.0,
    "evaluation": 0.0,
    "quiescence_search": 0.0,
    "transposition_table": 0.0,
    "board_push_pop_and_state": 0.0,
    "terminal_and_check_stop": 0.0,
    "other_search_overhead": 0.0,
}

# Aggregate self-times from stats
for func_tuple, (cc, nc, tottime, cumtime, callers) in ps.stats.items():
    filename, line, func_name = func_tuple
    # Classify based on function identity
    if func_name in ("_move_order_score", "_ordered_moves") or "legal_moves" in func_name:
        subsystems["move_generation_and_ordering"] += tottime
    elif func_name in ("evaluate_side_to_move", "evaluate_white", "_compute_center_bonus", "_center_bonus"):
        subsystems["evaluation"] += tottime
    elif func_name in ("_quiescence", "_quiescence_moves", "generate_legal_captures"):
        subsystems["quiescence_search"] += tottime
    elif func_name in ("_key", "fen", "_score_to_tt", "_score_from_tt") or ("tt" in func_name and "entry" not in func_name):
        subsystems["transposition_table"] += tottime
    elif func_name in ("push", "pop", "copy"):
        subsystems["board_push_pop_and_state"] += tottime
    elif func_name in ("_terminal_score", "_check_stop", "is_checkmate", "is_stalemate", "is_insufficient_material", "is_fivefold_repetition", "is_seventyfive_moves", "is_check"):
        subsystems["terminal_and_check_stop"] += tottime
    else:
        subsystems["other_search_overhead"] += tottime

output_data = {
    "depth_3": {
        "nodes": d3_runs[0]["total_nodes"],
        "timing_dispersion": d3_stats,
        "runs": d3_runs,
    },
    "depth_4": {
        "nodes": d4_runs[0]["total_nodes"],
        "timing_dispersion": d4_stats,
        "per_position": per_pos_d4,
        "runs": d4_runs,
    },
    "profiling": {
        "profile_wall_clock": profile_elapsed,
        "subsystems_self_time": {k: round(v, 4) for k, v in subsystems.items()},
        "total_self_time": round(sum(subsystems.values()), 4),
        "raw_stats_top_lines": profile_text[:3000],
    }
}

os.makedirs("analysis", exist_ok=True)
with open("analysis/v0.10_search_profiling.json", "w") as f:
    json.dump(output_data, f, indent=2)

print("\nProfiling summary (Self Time):")
total_t = sum(subsystems.values())
for sub, t in sorted(subsystems.items(), key=lambda x: x[1], reverse=True):
    pct = (t / total_t) * 100 if total_t > 0 else 0
    print(f"  {sub:32}: {t:.4f}s ({pct:5.1f}%)")

print("\nSaved report data to analysis/v0.10_search_profiling.json")
