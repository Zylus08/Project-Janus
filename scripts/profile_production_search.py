"""Profile production search configuration on standard benchmark positions.

Runs cProfile across all 6 standard benchmark positions at depth 4 and depth 5:
- Captures cumulative and exclusive execution time breakdowns.
- Identifies major bottlenecks and call frequencies.
- Saves detailed pstats and JSON reports for Milestone v0.28.
"""
from __future__ import annotations

import cProfile
import io
import json
from pathlib import Path
import pstats
import time
from typing import Any
import chess

from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]
POSITIONS_FILE = ROOT / "benchmarks" / "positions.json"
OUT_PROFILE_TXT = ROOT / "analysis" / "v0.28" / "profile" / "production_profile.txt"
OUT_PROFILE_JSON = ROOT / "analysis" / "v0.28" / "profile" / "production_profile.json"


def profile_searches() -> dict[str, Any]:
    positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    print("=" * 75)
    print("Project Janus v0.28 — Profiling Production Search Configuration")
    print(f"Loaded {len(positions)} standard positions from: {POSITIONS_FILE}")
    print("=" * 75)

    profiler = cProfile.Profile()
    depths = [4, 5]
    results_by_depth: dict[str, Any] = {}

    profiler.enable()
    start_wall = time.perf_counter()

    for depth in depths:
        print(f"\nProfiling depth {depth} across all {len(positions)} positions...")
        pos_results = []
        for pos in positions:
            p_id = pos["id"]
            fen = pos["fen"]
            board = chess.Board(fen)

            engine = JanusSearch(
                enable_see_ordering=False,
                enable_see_pruning=False,
                tt_replacement_policy="always_replace",
                check_extension_policy="disabled",
            )

            t0 = time.perf_counter()
            res = engine.search(board, max_depth=depth)
            dt = time.perf_counter() - t0

            pos_results.append({
                "position_id": p_id,
                "nodes": res.nodes,
                "elapsed_s": round(dt, 4),
                "score": res.score,
                "best_move": res.best_move.uci() if res.best_move else None,
            })
            print(f"  Pos: {p_id:<18} | Nodes: {res.nodes:>6} | Time: {dt:>6.3f}s | Move: {res.best_move}")

        results_by_depth[str(depth)] = pos_results

    profiler.disable()
    wall_duration = time.perf_counter() - start_wall

    print(f"\nTotal profiling search duration: {wall_duration:.2f}s")

    # Format pstats reports
    stream_tottime = io.StringIO()
    ps_tot = pstats.Stats(profiler, stream=stream_tottime)
    ps_tot.sort_stats("tottime")
    ps_tot.print_stats(40)

    stream_cumtime = io.StringIO()
    ps_cum = pstats.Stats(profiler, stream=stream_cumtime)
    ps_cum.sort_stats("cumtime")
    ps_cum.print_stats(40)

    OUT_PROFILE_TXT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PROFILE_TXT.open("w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("PROJECT JANUS v0.28 — PRODUCTION CONFIGURATION SEARCH PROFILE\n")
        f.write(f"Total Wall Time: {wall_duration:.3f}s\n")
        f.write("=" * 80 + "\n\n")
        f.write("TOP 40 FUNCTIONS BY EXCLUSIVE TIME (tottime):\n")
        f.write("-" * 80 + "\n")
        f.write(stream_tottime.getvalue())
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("TOP 40 FUNCTIONS BY CUMULATIVE TIME (cumtime):\n")
        f.write("-" * 80 + "\n")
        f.write(stream_cumtime.getvalue())

    # Build structured JSON report of top exclusive time functions
    stats_dict: list[dict[str, Any]] = []
    for func, (cc, nc, tt, ct, callers) in ps_tot.stats.items():
        file_path, line_num, func_name = func
        # Filter to project or chess library
        stats_dict.append({
            "file": file_path,
            "line": line_num,
            "function": func_name,
            "call_count": cc,
            "ncalls": nc,
            "tottime": round(tt, 4),
            "cumtime": round(ct, 4),
            "percall_tottime": round(tt / cc, 6) if cc else 0,
            "percall_cumtime": round(ct / cc, 6) if cc else 0,
        })

    stats_dict.sort(key=lambda x: x["tottime"], reverse=True)

    summary = {
        "metadata": {
            "wall_duration_s": round(wall_duration, 3),
            "depths": depths,
            "positions_count": len(positions),
        },
        "results_by_depth": results_by_depth,
        "top_exclusive_time_functions": stats_dict[:40],
    }

    with OUT_PROFILE_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nProfile output saved to:")
    print(f"  {OUT_PROFILE_TXT}")
    print(f"  {OUT_PROFILE_JSON}")

    print("\nTOP 15 HOTSPOTS BY EXCLUSIVE TIME (tottime):")
    print(f"{'Function':<35} | {'Calls':<10} | {'Tottime (s)':<12} | {'Cumtime (s)':<12} | {'Location'}")
    print("-" * 100)
    for entry in stats_dict[:15]:
        loc = f"{Path(entry['file']).name}:{entry['line']}"
        print(f"{entry['function']:<35} | {entry['call_count']:<10} | {entry['tottime']:<12.4f} | {entry['cumtime']:<12.4f} | {loc}")

    return summary


if __name__ == "__main__":
    profile_searches()
