import json
import statistics
import time
import os
import sys

os.environ['TEMP'] = 'E:\\ChessXML\\project-janus\\scratch'
os.environ['TMP'] = 'E:\\ChessXML\\project-janus\\scratch'
sys.path.insert(0, 'src')

import chess
from janus.search import JanusSearch, INF, TTEntry

ROOT = "E:/ChessXML/project-janus"

with open("benchmarks/positions.json") as f:
    positions = json.load(f)

def run_benchmarks(depth, repetitions=3):
    runs = []
    for r in range(repetitions):
        pos_results = []
        total_nodes = 0
        t0 = time.perf_counter()
        s = JanusSearch()
        for p in positions:
            b = chess.Board(p["fen"])
            res = s.search(b, max_depth=depth)
            total_nodes += res.nodes
            pos_results.append({
                "id": p["id"],
                "nodes": res.nodes,
                "score": res.score,
                "best_move": res.best_move.uci() if res.best_move else None,
                "pv": [m.uci() for m in res.pv],
                "elapsed": res.elapsed,
            })
        total_time = time.perf_counter() - t0
        runs.append({
            "run": r + 1,
            "total_nodes": total_nodes,
            "total_time": total_time,
            "nps": round(total_nodes / total_time),
            "positions": pos_results,
        })
    return runs

class InstrumentedSearch(JanusSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_beta_cutoffs = 0
        self.first_move_cutoffs = 0
        self.killer1_cutoffs = 0
        self.killer2_cutoffs = 0
        self.total_ordered_move_loops = 0

    def _negamax(self, board, depth, alpha, beta, ply):
        self.nodes += 1
        self._check_stop()

        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal, []
        if depth <= 0:
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
        self.total_ordered_move_loops += 1

        for idx, move in enumerate(moves):
            is_k1 = (ply < len(self.killers) and move == self.killers[ply][0])
            is_k2 = (ply < len(self.killers) and move == self.killers[ply][1])

            board.push(move)
            try:
                child_score, child_pv = self._negamax(
                    board, depth - 1, -beta, -alpha, ply + 1
                )
                score = -child_score
            finally:
                board.pop()

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv

            alpha = max(alpha, score)
            if alpha >= beta:
                self.total_beta_cutoffs += 1
                if idx == 0:
                    self.first_move_cutoffs += 1
                if is_k1:
                    self.killer1_cutoffs += 1
                elif is_k2:
                    self.killer2_cutoffs += 1

                if not board.is_capture(move) and move.promotion is None:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                break

        if best_move is None:
            from janus.evaluation import evaluate_side_to_move
            return evaluate_side_to_move(board), []

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

print("Running Depth 3 (3 runs)...")
d3_runs = run_benchmarks(3, 3)
d3_times = [r["total_time"] for r in d3_runs]
d3_nodes = d3_runs[0]["total_nodes"]
d3_median_time = statistics.median(d3_times)
print(f"Depth 3: {d3_nodes} nodes, times: {[round(t, 3) for t in d3_times]}, median: {d3_median_time:.3f}s")

print("Running Depth 4 (3 runs)...")
d4_runs = run_benchmarks(4, 3)
d4_times = [r["total_time"] for r in d4_runs]
d4_nodes = d4_runs[0]["total_nodes"]
d4_median_time = statistics.median(d4_times)
print(f"Depth 4: {d4_nodes} nodes, times: {[round(t, 3) for t in d4_times]}, median: {d4_median_time:.3f}s")

print("Running Depth 4 cutoff diagnostics...")
diag_s = InstrumentedSearch()
for p in positions:
    b = chess.Board(p["fen"])
    diag_s.search(b, max_depth=4)

cutoff_pct = round(100.0 * diag_s.first_move_cutoffs / diag_s.total_beta_cutoffs, 1) if diag_s.total_beta_cutoffs else 0
print(f"Depth 4 Beta Cutoffs: {diag_s.total_beta_cutoffs}")
print(f"Depth 4 First Move Cutoffs: {diag_s.first_move_cutoffs} ({cutoff_pct}%)")
print(f"Depth 4 Killer 1 Cutoffs: {diag_s.killer1_cutoffs}")
print(f"Depth 4 Killer 2 Cutoffs: {diag_s.killer2_cutoffs}")

results = {
    "depth_3": {
        "nodes": d3_nodes,
        "runs": d3_runs,
        "median_time": round(d3_median_time, 3),
        "median_nps": round(d3_nodes / d3_median_time) if d3_median_time > 0 else 0,
    },
    "depth_4": {
        "nodes": d4_nodes,
        "runs": d4_runs,
        "median_time": round(d4_median_time, 3),
        "median_nps": round(d4_nodes / d4_median_time) if d4_median_time > 0 else 0,
        "diagnostics": {
            "total_beta_cutoffs": diag_s.total_beta_cutoffs,
            "first_move_cutoffs": diag_s.first_move_cutoffs,
            "first_move_cutoff_rate_pct": cutoff_pct,
            "killer1_cutoffs": diag_s.killer1_cutoffs,
            "killer2_cutoffs": diag_s.killer2_cutoffs,
            "total_move_loops": diag_s.total_ordered_move_loops,
        }
    }
}

os.makedirs("analysis", exist_ok=True)
with open("analysis/v0.9_post_killer_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Saved to analysis/v0.9_post_killer_results.json")
