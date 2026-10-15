import cProfile
import json
import pstats
import sys
import time
from io import StringIO
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "src"))

import chess
from janus.search import JanusSearch

positions_path = ROOT / "benchmarks" / "positions.json"
positions = json.loads(positions_path.read_text(encoding="utf-8"))

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

subsystems = {
    "move_generation_and_ordering": 0.0,
    "evaluation": 0.0,
    "quiescence_search": 0.0,
    "transposition_table": 0.0,
    "board_push_pop_and_state": 0.0,
    "terminal_and_check_stop": 0.0,
    "other_search_overhead": 0.0,
}

for func_tuple, (cc, nc, tottime, cumtime, callers) in ps.stats.items():
    filename, line, func_name = func_tuple
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

# Extract call counts and cumulative times of terminal functions
terminal_stats = {}
for func_name_target in ("_terminal_score", "is_stalemate", "is_checkmate", "generate_legal_moves", "is_check"):
    for func_tuple, (cc, nc, tottime, cumtime, callers) in ps.stats.items():
        if func_tuple[2] == func_name_target:
            terminal_stats[func_name_target] = {
                "ncalls": cc,
                "tottime": round(tottime, 4),
                "cumtime": round(cumtime, 4),
            }

output_data = {
    "profile_wall_clock": round(profile_elapsed, 4),
    "subsystems_self_time": {k: round(v, 4) for k, v in subsystems.items()},
    "terminal_functions_stats": terminal_stats,
    "raw_stats_top_lines": profile_text[:3000],
}

out_path = ROOT / "analysis" / "v0.11" / "optimized_profiling.json"
out_path.write_text(json.dumps(output_data, indent=2) + "\n", encoding="utf-8")
print(f"Saved optimized profiling to {out_path}")

print("\n--- Terminal Functions In Profile ---")
for k, v in terminal_stats.items():
    print(f"  {k:25}: ncalls={v['ncalls']:<8} tottime={v['tottime']}s cumtime={v['cumtime']}s")
