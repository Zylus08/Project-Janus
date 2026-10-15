import json
import subprocess
import statistics
import sys
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus")
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, INF, MATE_SCORE

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

print("Running 5 independent process runs at Depth 3 (v0.12 Baseline)...")
d3 = run_reps(3, 5)
print(f"Depth 3 stats: median={d3['stats']['median']}s, min={d3['stats']['min']}s, max={d3['stats']['max']}s, iqr={d3['stats']['iqr']}s")

print("Running 5 independent process runs at Depth 4 (v0.12 Baseline)...")
d4 = run_reps(4, 5)
print(f"Depth 4 stats: median={d4['stats']['median']}s, min={d4['stats']['min']}s, max={d4['stats']['max']}s, iqr={d4['stats']['iqr']}s")

# Cutoff and Move Ordering Statistics Instrumentation
print("\n--- Measuring Baseline Move-Ordering & Cutoff Statistics ---")
class CutoffInstrumentedSearch(JanusSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_cutoffs = 0
        self.first_move_cutoffs = 0
        self.cutoff_categories = {
            "tt_move": 0,
            "capture": 0,
            "promotion": 0,
            "killer_1": 0,
            "killer_2": 0,
            "quiet": 0,
        }

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
        entry = self.tt.get(key)
        tt_move = None

        if entry is not None:
            tt_move = entry.best_move
            tt_score = self._score_from_tt(entry.score, ply)

            if ply > 0 and entry.depth >= depth:
                if (board.halfmove_clock + depth < 150) or entry.score == 0:
                    if entry.flag == "exact":
                        return tt_score, ([] if tt_move is None else [tt_move])
                    if entry.flag == "lower":
                        alpha = max(alpha, tt_score)
                    elif entry.flag == "upper":
                        beta = min(beta, tt_score)
                    if alpha >= beta:
                        return tt_score, ([] if tt_move is None else [tt_move])

        best_score = -INF
        best_move = None
        best_pv = []

        moves = self._ordered_moves(board, tt_move, ply)
        if not moves:
            if board.is_check():
                return -MATE_SCORE + ply, []
            return 0, []

        for move_idx, move in enumerate(moves):
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
                self.total_cutoffs += 1
                if move_idx == 0:
                    self.first_move_cutoffs += 1

                # Classify cutoff move into mutually exclusive categories
                if tt_move is not None and move == tt_move:
                    self.cutoff_categories["tt_move"] += 1
                elif board.is_capture(move):
                    self.cutoff_categories["capture"] += 1
                elif move.promotion is not None:
                    self.cutoff_categories["promotion"] += 1
                elif ply < len(self.killers) and move == self.killers[ply][0]:
                    self.cutoff_categories["killer_1"] += 1
                elif ply < len(self.killers) and move == self.killers[ply][1]:
                    self.cutoff_categories["killer_2"] += 1
                else:
                    self.cutoff_categories["quiet"] += 1

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

        self.tt[key] = TTEntry(
            depth=depth,
            score=self._score_to_tt(best_score, ply),
            flag=flag,
            best_move=best_move,
        )
        return best_score, best_pv

from janus.search import TTEntry

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))
cutoff_stats = {}
for p in positions_data:
    b = chess.Board(p["fen"])
    searcher = CutoffInstrumentedSearch()
    searcher.search(b, max_depth=4)
    fm_rate = round(searcher.first_move_cutoffs / searcher.total_cutoffs * 100, 2) if searcher.total_cutoffs else 0.0
    cutoff_stats[p["id"]] = {
        "nodes": searcher.nodes,
        "total_cutoffs": searcher.total_cutoffs,
        "first_move_cutoffs": searcher.first_move_cutoffs,
        "first_move_cutoff_rate": fm_rate,
        "categories": dict(searcher.cutoff_categories),
    }

total_c = sum(s["total_cutoffs"] for s in cutoff_stats.values())
total_fm = sum(s["first_move_cutoffs"] for s in cutoff_stats.values())
overall_fm_rate = round(total_fm / total_c * 100, 2) if total_c else 0.0

overall_categories = {
    "tt_move": sum(s["categories"]["tt_move"] for s in cutoff_stats.values()),
    "capture": sum(s["categories"]["capture"] for s in cutoff_stats.values()),
    "promotion": sum(s["categories"]["promotion"] for s in cutoff_stats.values()),
    "killer_1": sum(s["categories"]["killer_1"] for s in cutoff_stats.values()),
    "killer_2": sum(s["categories"]["killer_2"] for s in cutoff_stats.values()),
    "quiet": sum(s["categories"]["quiet"] for s in cutoff_stats.values()),
}

print(f"Overall Cutoffs: {total_c}")
print(f"First-Move Cutoffs: {total_fm} ({overall_fm_rate}%)")
print(f"Cutoff Breakdown: {overall_categories}")

out_data = {
    "engine_commit": "93524b1a024cfed34ca39a427490401d02c143d0",
    "description": "Milestone v0.12 baseline for v0.13 history heuristic",
    "depth_3": d3,
    "depth_4": d4,
    "cutoff_statistics": {
        "total_cutoffs": total_c,
        "first_move_cutoffs": total_fm,
        "overall_first_move_cutoff_rate": overall_fm_rate,
        "categories": overall_categories,
        "positions": cutoff_stats,
    }
}

out_file = ROOT / "analysis" / "v0.13" / "baseline_benchmarks.json"
out_file.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
print(f"Wrote baseline benchmarks to {out_file}")
