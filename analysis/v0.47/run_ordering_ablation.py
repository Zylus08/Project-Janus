"""Move-ordering ablation study for Project Janus v0.47 (Phase I).

Measures the independent contribution of each move-ordering heuristic to:
1. First-move (move 0) cutoff rate
2. Total beta cutoffs
3. Total nodes searched
4. Search execution time
"""

import json
import time
from pathlib import Path
from typing import Optional
import chess

from janus.search import JanusSearch


class NoTTMoveSearch(JanusSearch):
    def _move_order_score(
        self,
        board: chess.Board,
        move: chess.Move,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
        node_see: Optional[dict[chess.Move, int]] = None,
        prev_move: Optional[chess.Move] = None,
    ) -> int:
        # Ignore tt_move in ordering score
        return super()._move_order_score(
            board, move, None, ply, node_see=node_see, prev_move=prev_move
        )


def run_ablation():
    corpus_path = Path("analysis/v0.47/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    depth = 4
    configs = [
        {"name": "Full_K0", "cls": JanusSearch, "kwargs": {"enable_lazy_move_selection": False}},
        {"name": "Candidate_L1", "cls": JanusSearch, "kwargs": {"enable_lazy_move_selection": True}},
        {"name": "No_TT_Ordering", "cls": NoTTMoveSearch, "kwargs": {"enable_lazy_move_selection": False}},
        {"name": "No_Killers", "cls": JanusSearch, "kwargs": {"max_killers_ply": 0}},
        {"name": "No_History", "cls": JanusSearch, "kwargs": {"enable_history": False}},
        {"name": "With_Countermoves", "cls": JanusSearch, "kwargs": {"enable_countermoves": True}},
    ]

    ablation_results = {}
    print(f"Starting Ordering Ablation Study across {len(corpus)} positions at Depth {depth}...\n", flush=True)

    for cfg in configs:
        name = cfg["name"]
        cls = cfg["cls"]
        kwargs = dict(cfg["kwargs"])
        kwargs["diagnostic_ordering"] = True

        print(f"--- Evaluating Ablation: {name} ---", flush=True)
        total_nodes = 0
        total_cutoffs = 0
        first_cutoffs = 0
        total_time = 0.0
        ordering_time = 0.0

        for pos in corpus:
            board = chess.Board(pos["fen"])
            searcher = cls(**kwargs)
            t0 = time.perf_counter()
            res = searcher.search(board, max_depth=depth)
            el = time.perf_counter() - t0

            total_nodes += res.nodes
            total_time += el
            stats = res.ordering_stats
            total_cutoffs += stats.get("total_cutoffs", 0)
            first_cutoffs += stats.get("first_move_cutoffs", 0)
            ordering_time += stats.get("total_ordering_time_s", 0.0)

        first_move_rate = (first_cutoffs / total_cutoffs) if total_cutoffs > 0 else 0.0
        nps = int(total_nodes / total_time) if total_time > 0 else 0

        ablation_results[name] = {
            "config": name,
            "depth": depth,
            "total_nodes": total_nodes,
            "total_time_s": round(total_time, 3),
            "nps": nps,
            "total_cutoffs": total_cutoffs,
            "first_move_cutoffs": first_cutoffs,
            "first_move_cutoff_rate": round(first_move_rate, 4),
            "total_ordering_time_s": round(ordering_time, 3),
            "ordering_time_pct": round(ordering_time / total_time * 100.0, 2) if total_time > 0 else 0,
        }

        print(
            f"  Nodes: {total_nodes:,} | Time: {total_time:.2f}s | NPS: {nps:,} | "
            f"Cutoffs: {total_cutoffs:,} | First-Move Rate: {first_move_rate:.2%} | Ordering Time: {ordering_time:.2f}s",
            flush=True,
        )

    out_file = Path("analysis/v0.47/raw/ordering_ablation.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ablation_results, f, indent=2)

    print(f"\nAblation study completed! Results saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_ablation()
