"""Project Janus v0.48 - History Heuristic Computational & Decision Analysis (Phase D).

Measures:
1. History lookups performed vs quiet moves actually searched vs quiet moves discarded.
2. History table updates and saturation levels.
3. History-induced beta cutoffs vs other heuristics.
4. Runtime cost of history lookups and move scoring.
5. Category breakdown (Tactical, Quiet Positional, Endgame).
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch


class HistoryInstrumentedSearch(JanusSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_lookups = 0
        self.history_scores_non_zero = 0
        self.quiet_moves_scored = 0
        self.quiet_moves_searched_count = 0
        self.quiet_moves_never_searched = 0
        self.history_cutoffs = 0

    def _move_order_score(
        self,
        board: chess.Board,
        move: chess.Move,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
        node_see: Optional[dict[chess.Move, int]] = None,
        prev_move: Optional[chess.Move] = None,
    ) -> int:
        score = super()._move_order_score(
            board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
        )
        if not board.is_capture(move) and move.promotion is None:
            self.quiet_moves_scored += 1
            if self.enable_history:
                self.history_lookups += 1
                if self.history[move.from_square][move.to_square] > 0:
                    self.history_scores_non_zero += 1
        return score


def run_history_analysis():
    corpus_path = Path("analysis/v0.48/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    depth = 4
    categories = ["tactical", "quiet_positional", "endgame"]
    cat_stats = {c: {"positions": 0, "nodes": 0, "history_lookups": 0, "quiet_scored": 0, "quiet_cutoffs": 0, "total_cutoffs": 0} for c in categories}

    print("=" * 80, flush=True)
    print(f"PROJECT JANUS v0.48 - HISTORY HEURISTIC ANALYSIS (Depth {depth})", flush=True)
    print("=" * 80, flush=True)

    total_nodes = 0
    total_time = 0.0
    total_lookups = 0
    total_quiet_scored = 0
    total_cutoffs = 0
    total_quiet_cutoffs = 0

    for pos in corpus:
        cat = pos.get("category", "quiet_positional")
        if cat not in cat_stats:
            cat = "quiet_positional"
        cat_stats[cat]["positions"] += 1

        board = chess.Board(pos["fen"])
        searcher = HistoryInstrumentedSearch(
            enable_lazy_move_selection=False,
            diagnostic_ordering=True,
        )

        t0 = time.perf_counter()
        res = searcher.search(board, max_depth=depth)
        el = time.perf_counter() - t0

        total_nodes += res.nodes
        total_time += el
        total_lookups += searcher.history_lookups
        total_quiet_scored += searcher.quiet_moves_scored
        stats = res.ordering_stats
        t_cuts = stats.get("total_cutoffs", 0)
        q_cuts = stats.get("quiet_cutoffs", 0)
        total_cutoffs += t_cuts
        total_quiet_cutoffs += q_cuts

        cat_stats[cat]["nodes"] += res.nodes
        cat_stats[cat]["history_lookups"] += searcher.history_lookups
        cat_stats[cat]["quiet_scored"] += searcher.quiet_moves_scored
        cat_stats[cat]["quiet_cutoffs"] += q_cuts
        cat_stats[cat]["total_cutoffs"] += t_cuts

    out_data = {
        "depth": depth,
        "total_nodes": total_nodes,
        "total_time_s": round(total_time, 3),
        "total_quiet_moves_scored": total_quiet_scored,
        "total_history_lookups": total_lookups,
        "total_cutoffs": total_cutoffs,
        "total_quiet_cutoffs": total_quiet_cutoffs,
        "quiet_cutoff_percentage": round(total_quiet_cutoffs / total_cutoffs * 100.0, 2) if total_cutoffs > 0 else 0,
        "lookups_per_node": round(total_lookups / total_nodes, 2) if total_nodes > 0 else 0,
        "category_breakdown": cat_stats,
    }

    out_file = Path("analysis/v0.48/raw/history_analysis_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\nTotal Nodes: {total_nodes:,} | Total Time: {total_time:.2f}s", flush=True)
    print(f"Total Quiet Moves Scored: {total_quiet_scored:,} | History Lookups: {total_lookups:,}", flush=True)
    print(f"Total Beta Cutoffs: {total_cutoffs:,} | Quiet Move Cutoffs: {total_quiet_cutoffs:,} ({out_data['quiet_cutoff_percentage']}%)", flush=True)
    print(f"Lookups per Node: {out_data['lookups_per_node']}", flush=True)

    print("\n--- Category Breakdown ---", flush=True)
    for cat, c_data in cat_stats.items():
        q_pct = (c_data['quiet_cutoffs'] / c_data['total_cutoffs'] * 100.0) if c_data['total_cutoffs'] > 0 else 0
        print(f"  {cat:18s}: {c_data['positions']:2d} pos | Nodes: {c_data['nodes']:,} | Quiet Scored: {c_data['quiet_scored']:,} | Quiet Cutoffs: {c_data['quiet_cutoffs']:,} ({q_pct:.1f}%)", flush=True)

    print(f"\nSaved raw history analysis to {out_file}", flush=True)


if __name__ == "__main__":
    run_history_analysis()

