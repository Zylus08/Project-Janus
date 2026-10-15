import json
import subprocess
import statistics
import sys
import time
import cProfile
import pstats
import io
from pathlib import Path
import chess
import chess.polyglot

ROOT = Path("E:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, INF, TTEntry, MATE_SCORE

def run_reps(depth: int, reps: int = 5):
    runs = []
    for r in range(reps):
        cmd = [PYTHON, "scripts/benchmark.py", "--depth", str(depth)]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
        json_path = None
        for line in proc.stdout.splitlines():
            if line.startswith("JSON:"):
                json_path = Path(line.split(":", 1)[1].strip())
                break
        assert json_path and json_path.exists(), f"Could not find json output: {proc.stdout}"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        runs.append({
            "run": r + 1,
            "total_nodes": data["summary"]["total_nodes"],
            "total_elapsed_seconds": data["summary"]["total_elapsed_seconds"],
            "json_file": str(json_path),
            "results": [
                {
                    "id": row["id"],
                    "nodes": row["nodes"],
                    "score": row["score_from_side_to_move"],
                    "best_move": row["best_move_uci"],
                    "pv": row["pv_uci"],
                    "elapsed": row["elapsed_seconds"],
                }
                for row in data["results"]
            ]
        })
    times = [r["total_elapsed_seconds"] for r in runs]
    times_sorted = sorted(times)
    n = len(times_sorted)
    q1 = times_sorted[n // 4] if n >= 4 else times_sorted[0]
    q3 = times_sorted[(3 * n) // 4] if n >= 4 else times_sorted[-1]
    stats = {
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "mean": round(statistics.mean(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) > 1 else 0.0,
        "iqr": round(q3 - q1, 4),
    }
    return {"runs": runs, "stats": stats}

print("Running 5 independent process runs at Depth 3 (v0.12 Zobrist TT)...")
d3 = run_reps(3, 5)
print(f"Depth 3 stats: median={d3['stats']['median']}s, min={d3['stats']['min']}s, max={d3['stats']['max']}s, iqr={d3['stats']['iqr']}s")

print("Running 5 independent process runs at Depth 4 (v0.12 Zobrist TT)...")
d4 = run_reps(4, 5)
print(f"Depth 4 stats: median={d4['stats']['median']}s, min={d4['stats']['min']}s, max={d4['stats']['max']}s, iqr={d4['stats']['iqr']}s")

# Load v0.11 baseline benchmarks
v011_path = ROOT / "analysis" / "v0.11" / "optimized_benchmarks.json"
v011 = json.loads(v011_path.read_text(encoding="utf-8"))

d3_v011_med = v011["depth_3"]["stats"]["median"]
d3_v012_med = d3["stats"]["median"]
d3_speedup = (d3_v011_med - d3_v012_med) / d3_v011_med * 100

d4_v011_med = v011["depth_4"]["stats"]["median"]
d4_v012_med = d4["stats"]["median"]
d4_speedup = (d4_v011_med - d4_v012_med) / d4_v011_med * 100

print(f"\n--- Performance Comparison Against v0.11 ---")
print(f"Depth 3 Median: {d3_v011_med:.3f}s -> {d3_v012_med:.3f}s (delta: {d3_v011_med - d3_v012_med:+.3f}s, speedup: {d3_speedup:+.1f}%)")
print(f"Depth 4 Median: {d4_v011_med:.3f}s -> {d4_v012_med:.3f}s (delta: {d4_v011_med - d4_v012_med:+.3f}s, speedup: {d4_speedup:+.1f}%)")

# Instrumented TT metrics run
print("\n--- Running Instrumented TT Metrics and Profiling ---")
class InstrumentedJanusSearch(JanusSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tt_probes = 0
        self.tt_hits = 0
        self.tt_cutoffs = 0
        self.tt_stores = 0

    def _negamax(self, board, depth, alpha, beta, ply):
        self.nodes += 1
        self._check_stop()

        if (
            board.is_insufficient_material()
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0, []

        if depth <= 0:
            if not any(board.generate_legal_moves()):
                return (-MATE_SCORE + ply if board.is_check() else 0), []
            return self._quiescence(board, alpha, beta, ply), []

        alpha_original = alpha
        beta_original = beta
        key = self._key(board)
        self.tt_probes += 1
        entry = self.tt.get(key)
        tt_move = None

        if entry is not None:
            self.tt_hits += 1
            tt_move = entry.best_move
            tt_score = self._score_from_tt(entry.score, ply)

            if ply > 0 and entry.depth >= depth:
                if (board.halfmove_clock + depth < 150) or entry.score == 0:
                    if entry.flag == "exact":
                        self.tt_cutoffs += 1
                        return tt_score, ([] if tt_move is None else [tt_move])
                    if entry.flag == "lower":
                        alpha = max(alpha, tt_score)
                    elif entry.flag == "upper":
                        beta = min(beta, tt_score)
                    if alpha >= beta:
                        self.tt_cutoffs += 1
                        return tt_score, ([] if tt_move is None else [tt_move])

        best_score = -INF
        best_move = None
        best_pv = []

        moves = self._ordered_moves(board, tt_move, ply)
        if not moves:
            if board.is_check():
                return -MATE_SCORE + ply, []
            return 0, []

        for move in moves:
            board.push(move)
            try:
                child_score, child_pv = self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
                score = -child_score
            finally:
                board.pop()

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv

            alpha = max(alpha, score)
            if alpha >= beta:
                if not board.is_capture(move) and move.promotion is None:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                break

        if len(self.tt) >= self.tt_max_entries:
            self.tt.clear()

        if best_score <= alpha_original:
            flag = "upper"
        elif best_score >= beta_original:
            flag = "lower"
        else:
            flag = "exact"

        self.tt_stores += 1
        self.tt[key] = TTEntry(
            depth=depth,
            score=self._score_to_tt(best_score, ply),
            flag=flag,
            best_move=best_move,
        )
        return best_score, best_pv

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))
tt_metrics = {}
for p in positions_data:
    b = chess.Board(p["fen"])
    eng = InstrumentedJanusSearch()
    eng.search(b, max_depth=4)
    tt_metrics[p["id"]] = {
        "nodes": eng.nodes,
        "probes": eng.tt_probes,
        "hits": eng.tt_hits,
        "cutoffs": eng.tt_cutoffs,
        "stores": eng.tt_stores,
        "hit_rate": round(eng.tt_hits / eng.tt_probes * 100, 2) if eng.tt_probes else 0,
        "cutoff_rate": round(eng.tt_cutoffs / eng.tt_probes * 100, 2) if eng.tt_probes else 0,
    }

total_probes = sum(m["probes"] for m in tt_metrics.values())
total_hits = sum(m["hits"] for m in tt_metrics.values())
total_cutoffs = sum(m["cutoffs"] for m in tt_metrics.values())
total_stores = sum(m["stores"] for m in tt_metrics.values())

tt_summary = {
    "total_probes": total_probes,
    "total_hits": total_hits,
    "total_cutoffs": total_cutoffs,
    "total_stores": total_stores,
    "overall_hit_rate": round(total_hits / total_probes * 100, 2) if total_probes else 0,
    "overall_cutoff_rate": round(total_cutoffs / total_probes * 100, 2) if total_probes else 0,
    "positions": tt_metrics,
}
print(f"TT Metrics: probes={total_probes}, hits={total_hits} ({tt_summary['overall_hit_rate']}%), cutoffs={total_cutoffs} ({tt_summary['overall_cutoff_rate']}%), stores={total_stores}")

# Run cProfile on depth 4 suite
pr = cProfile.Profile()
pr.enable()
for p in positions_data:
    b = chess.Board(p["fen"])
    searcher = JanusSearch()
    searcher.search(b, max_depth=4)
pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
ps.print_stats(60)
raw_profile_output = s.getvalue()

# Extract _key stats
key_stats = {}
for func_tuple, stat_data in ps.stats.items():
    cc, nc, tottime, cumtime, callers = stat_data
    if func_tuple[2] == "_key":
        key_stats["_key"] = {
            "ncalls": nc,
            "tottime": round(tottime, 4),
            "cumtime": round(cumtime, 4),
            "percall": round(cumtime / nc, 6) if nc else 0,
        }
    elif func_tuple[2] == "zobrist_hash":
        key_stats["zobrist_hash"] = {
            "ncalls": nc,
            "tottime": round(tottime, 4),
            "cumtime": round(cumtime, 4),
            "percall": round(cumtime / nc, 6) if nc else 0,
        }

out_benchmarks = {
    "engine_commit": "zobrist_v0.12",
    "description": "Milestone v0.12 Zobrist TT hashing benchmark results across 5 independent process runs",
    "depth_3": d3,
    "depth_4": d4,
    "comparison_against_v011": {
        "depth_3_v011_median": d3_v011_med,
        "depth_3_v012_median": d3_v012_med,
        "depth_3_speedup_percent": round(d3_speedup, 2),
        "depth_4_v011_median": d4_v011_med,
        "depth_4_v012_median": d4_v012_med,
        "depth_4_speedup_percent": round(d4_speedup, 2),
        "depth_3_total_nodes": d3["runs"][0]["total_nodes"],
        "depth_4_total_nodes": d4["runs"][0]["total_nodes"],
        "node_reduction_depth_4": 71195 - d4["runs"][0]["total_nodes"],
        "node_reduction_depth_4_percent": round((71195 - d4["runs"][0]["total_nodes"]) / 71195 * 100, 2),
    },
    "tt_metrics": tt_summary,
    "key_profiling": key_stats,
}

out_file = ROOT / "analysis" / "v0.12" / "zobrist_benchmarks.json"
out_file.write_text(json.dumps(out_benchmarks, indent=2), encoding="utf-8")
print(f"\nWrote benchmark data to {out_file}")

prof_file = ROOT / "analysis" / "v0.12" / "zobrist_profiling.json"
prof_data = {
    "key_stats": key_stats,
    "raw_stats_top_lines": raw_profile_output[:3000],
}
prof_file.write_text(json.dumps(prof_data, indent=2), encoding="utf-8")
print(f"Wrote profiling data to {prof_file}")
