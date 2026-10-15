import cProfile
import pstats
import io
import json
import time
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus")
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))

def profile_search(enable_history: bool):
    pr = cProfile.Profile()
    pr.enable()
    for p in positions_data:
        b = chess.Board(p["fen"])
        eng = JanusSearch(enable_history=enable_history)
        eng.search(b, max_depth=4)
    pr.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(40)
    
    stats_dict = {}
    for func_tuple, stat_data in ps.stats.items():
        cc, nc, tottime, cumtime, callers = stat_data
        filename, line, func_name = func_tuple
        if "janus" in filename or func_name in ("_ordered_moves", "_move_order_score", "_update_history", "sort"):
            stats_dict[f"{func_name} ({line})"] = {
                "ncalls": nc,
                "tottime": round(tottime, 4),
                "cumtime": round(cumtime, 4),
                "percall": round(cumtime / nc, 6) if nc else 0,
            }
    return s.getvalue(), stats_dict

print("Profiling with history ENABLED...")
raw_enabled, stats_enabled = profile_search(True)

print("Profiling with history DISABLED...")
raw_disabled, stats_disabled = profile_search(False)

print("\n--- Key Functions with History ENABLED ---")
for k, v in stats_enabled.items():
    print(f"  {k:<35}: ncalls={v['ncalls']:>7}, tottime={v['tottime']:>6.3f}s, cumtime={v['cumtime']:>6.3f}s")

print("\n--- Key Functions with History DISABLED ---")
for k, v in stats_disabled.items():
    print(f"  {k:<35}: ncalls={v['ncalls']:>7}, tottime={v['tottime']:>6.3f}s, cumtime={v['cumtime']:>6.3f}s")

out_prof = {
    "enabled_stats": stats_enabled,
    "disabled_stats": stats_disabled,
    "raw_enabled_top": raw_enabled[:4000],
    "raw_disabled_top": raw_disabled[:4000],
}

(ROOT / "analysis" / "v0.14" / "history_profiling.json").write_text(json.dumps(out_prof, indent=2), encoding="utf-8")
print("\nWrote profiling data to analysis/v0.14/history_profiling.json")
