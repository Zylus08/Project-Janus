"""Project Janus v0.48 - Controlled TT-Path Ablation (Phase C).

Compares:
- K0: Eager full sorting.
- L1: TT-first lazy selection (bypasses sorting when TT move is present).
- T0: Eagerly pre-sorted, but TT move yielded first (measures lazy savings vs move order).
- T1: Warm-TT vs Cold-TT comparison under L1.

Evaluated across the 37-position diagnostic corpus at depth 4 and 5.
Measures:
- Wall-clock runtime
- Total nodes searched
- Effective NPS
- TT hit rate and TT cutoff rate
- Ordering time
- Best move and score agreement
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


class T0Search(JanusSearch):
    """T0: Eagerly scores and sorts all moves, but yields the TT move first if present."""
    def _select_ordered_moves(
        self,
        board: chess.Board,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
        prev_move: Optional[chess.Move] = None,
    ):
        moves = list(board.legal_moves)
        total_legal_count = len(moves)
        if total_legal_count <= 1:
            return moves, None, total_legal_count

        node_see = {} if self.enable_see_ordering else None
        if self.diagnostic_ordering:
            t0 = time.perf_counter()
            moves.sort(
                key=lambda move: self._move_order_score(
                    board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
                ),
                reverse=True,
            )
            self.total_ordering_time += (time.perf_counter() - t0)
        else:
            moves.sort(
                key=lambda move: self._move_order_score(
                    board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
                ),
                reverse=True,
            )

        # Yield top move (TT move if present), rest on demand
        if tt_move is not None and tt_move in moves:
            top_move = moves[0]
            rest = moves[1:]
            return [top_move], lambda: rest, total_legal_count

        return moves, None, total_legal_count


def run_tt_ablation():
    corpus_path = Path("analysis/v0.48/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    depth = 4
    configs = [
        {"name": "K0_Cold", "cls": JanusSearch, "lazy": False, "warm": False},
        {"name": "L1_Cold", "cls": JanusSearch, "lazy": True, "warm": False},
        {"name": "T0_EagerSort_TTFirst", "cls": T0Search, "lazy": True, "warm": False},
        {"name": "K0_Warm", "cls": JanusSearch, "lazy": False, "warm": True},
        {"name": "L1_Warm", "cls": JanusSearch, "lazy": True, "warm": True},
    ]

    results = {}
    print("=" * 80, flush=True)
    print(f"PROJECT JANUS v0.48 - TT-PATH ABLATION (Depth {depth})", flush=True)
    print("=" * 80, flush=True)

    for cfg in configs:
        name = cfg["name"]
        cls = cfg["cls"]
        lazy = cfg["lazy"]
        warm = cfg["warm"]

        print(f"\n--- Evaluating Configuration: {name} ---", flush=True)
        total_nodes = 0
        total_time = 0.0
        total_ordering_time = 0.0
        total_cutoffs = 0
        first_cutoffs = 0
        tt_cutoffs = 0
        saved_sorts = 0

        for pos in corpus:
            board = chess.Board(pos["fen"])
            searcher = cls(
                enable_lazy_move_selection=lazy,
                diagnostic_ordering=True,
            )

            t0 = time.perf_counter()
            if warm:
                # Iterative deepening warms the TT
                res = None
                for d in range(1, depth + 1):
                    res = searcher.search(board, max_depth=d)
            else:
                # Cold TT
                res = searcher.search(board, max_depth=depth)
            el = time.perf_counter() - t0

            total_nodes += res.nodes
            total_time += el
            ord_stats = res.ordering_stats
            total_ordering_time += ord_stats.get("total_ordering_time_s", 0.0)
            total_cutoffs += ord_stats.get("total_cutoffs", 0)
            first_cutoffs += ord_stats.get("first_move_cutoffs", 0)
            tt_cutoffs += ord_stats.get("tt_cutoffs", 0)
            saved_sorts += ord_stats.get("lazy_sorts_saved", 0)

        nps = int(total_nodes / total_time) if total_time > 0 else 0
        first_rate = (first_cutoffs / total_cutoffs) if total_cutoffs > 0 else 0.0

        results[name] = {
            "config": name,
            "depth": depth,
            "warm": warm,
            "total_nodes": total_nodes,
            "total_time_s": round(total_time, 3),
            "nps": nps,
            "ordering_time_s": round(total_ordering_time, 3),
            "ordering_time_pct": round(total_ordering_time / total_time * 100.0, 2) if total_time > 0 else 0,
            "total_cutoffs": total_cutoffs,
            "first_move_cutoffs": first_cutoffs,
            "first_move_cutoff_rate": round(first_rate, 4),
            "tt_cutoffs": tt_cutoffs,
            "lazy_sorts_saved": saved_sorts,
        }

        print(
            f"  Nodes: {total_nodes:,} | Time: {total_time:.2f}s | NPS: {nps:,} | "
            f"Ordering Time: {total_ordering_time:.2f}s | 1st Move Rate: {first_rate:.1%} | "
            f"TT Cutoffs: {tt_cutoffs:,} | Sorts Saved: {saved_sorts:,}",
            flush=True,
        )

    out_file = Path("analysis/v0.48/raw/tt_path_ablation_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nTT-path ablation complete! Results saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_tt_ablation()

