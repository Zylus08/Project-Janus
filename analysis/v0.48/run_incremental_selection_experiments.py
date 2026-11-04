"""Project Janus v0.48 - Incremental Move Selection Experiments (Phase F).

Evaluates:
- Baseline K0: Eager full Timsort.
- Candidate L1: Deferred TT-first lazy selection.
- Candidate L2: Stable entry-scored incremental selection (preserves K0 move ordering).
- Candidate L3: Cached lazy scoring (scores computed on demand and cached).

Measures:
- Total nodes searched
- Runtime and effective NPS
- Exact move agreement with K0
- Exact score agreement with K0
- Total ordering overhead
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, List, Tuple
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch


class CandidateL2Search(JanusSearch):
    """Candidate L2: Entry-Scored Stable Selection.
    Scores all moves at node entry before move 0 search, guaranteeing exact history order,
    but defers sorting the tail until move 0 fails to produce a cutoff.
    """
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

        if tt_move is not None and tt_move in moves:
            self.lazy_sorts_deferred += 1
            # Pre-score remaining moves using entry-time history state
            rem_moves = [m for m in moves if m != tt_move]
            # Capture scores at entry time
            rem_scored = [
                (self._move_order_score(board, m, None, ply, node_see=node_see, prev_move=prev_move), m)
                for m in rem_moves
            ]

            def rest_provider():
                self.lazy_sorts_executed += 1
                t0 = time.perf_counter()
                # Sort pre-computed integer tuples (fast in CPython)
                rem_scored.sort(key=lambda x: x[0], reverse=True)
                if self.diagnostic_ordering:
                    self.total_ordering_time += (time.perf_counter() - t0)
                return [m for _, m in rem_scored]

            return [tt_move], rest_provider, total_legal_count
        else:
            # No TT move: standard ordering
            t0 = time.perf_counter()
            moves.sort(
                key=lambda move: self._move_order_score(
                    board, move, None, ply, node_see=node_see, prev_move=prev_move
                ),
                reverse=True,
            )
            if self.diagnostic_ordering:
                self.total_ordering_time += (time.perf_counter() - t0)
            return moves, None, total_legal_count


class CandidateL3Search(JanusSearch):
    """Candidate L3: Cached Lazy Scoring.
    Avoids scoring any quiet moves until all captures/promotions/killers are searched.
    """
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

        # Separate tactical vs quiet
        node_see = {} if self.enable_see_ordering else None

        if tt_move is not None and tt_move in moves:
            self.lazy_sorts_deferred += 1
            rem = [m for m in moves if m != tt_move]
            def rest_provider():
                self.lazy_sorts_executed += 1
                t0 = time.perf_counter()
                rem.sort(
                    key=lambda move: self._move_order_score(
                        board, move, None, ply, node_see=node_see, prev_move=prev_move
                    ),
                    reverse=True,
                )
                if self.diagnostic_ordering:
                    self.total_ordering_time += (time.perf_counter() - t0)
                return rem
            return [tt_move], rest_provider, total_legal_count
        else:
            t0 = time.perf_counter()
            moves.sort(
                key=lambda move: self._move_order_score(
                    board, move, None, ply, node_see=node_see, prev_move=prev_move
                ),
                reverse=True,
            )
            if self.diagnostic_ordering:
                self.total_ordering_time += (time.perf_counter() - t0)
            return moves, None, total_legal_count


def run_experiments():
    corpus_path = Path("analysis/v0.48/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    depth = 4
    candidates = [
        {"name": "K0", "cls": JanusSearch, "lazy": False},
        {"name": "L1", "cls": JanusSearch, "lazy": True},
        {"name": "L2_Stable", "cls": CandidateL2Search, "lazy": True},
    ]

    summary = {}
    print("=" * 80, flush=True)
    print(f"PROJECT JANUS v0.48 - INCREMENTAL SELECTION EXPERIMENTS (Depth {depth})", flush=True)
    print("=" * 80, flush=True)

    k0_moves = {}
    k0_scores = {}

    for cand in candidates:
        name = cand["name"]
        cls = cand["cls"]
        lazy = cand["lazy"]

        print(f"\n--- Evaluating Candidate: {name} ---", flush=True)
        total_nodes = 0
        total_time = 0.0
        total_ordering_time = 0.0
        total_cutoffs = 0
        first_cutoffs = 0
        sorts_saved = 0
        cand_moves = {}
        cand_scores = {}

        for pos in corpus:
            board = chess.Board(pos["fen"])
            searcher = cls(
                enable_lazy_move_selection=lazy,
                diagnostic_ordering=True,
            )
            t0 = time.perf_counter()
            res = searcher.search(board, max_depth=depth)
            el = time.perf_counter() - t0

            total_nodes += res.nodes
            total_time += el
            ord_stats = res.ordering_stats
            total_ordering_time += ord_stats.get("total_ordering_time_s", 0.0)
            total_cutoffs += ord_stats.get("total_cutoffs", 0)
            first_cutoffs += ord_stats.get("first_move_cutoffs", 0)
            sorts_saved += ord_stats.get("lazy_sorts_saved", 0)

            cand_moves[pos["id"]] = res.best_move.uci() if res.best_move else None
            cand_scores[pos["id"]] = res.score

        if name == "K0":
            k0_moves = cand_moves
            k0_scores = cand_scores
            move_agree = len(corpus)
            score_agree = len(corpus)
        else:
            move_agree = sum(1 for pid in k0_moves if k0_moves[pid] == cand_moves[pid])
            score_agree = sum(1 for pid in k0_scores if k0_scores[pid] == cand_scores[pid])

        nps = int(total_nodes / total_time) if total_time > 0 else 0
        first_rate = (first_cutoffs / total_cutoffs) if total_cutoffs > 0 else 0.0

        summary[name] = {
            "name": name,
            "depth": depth,
            "total_nodes": total_nodes,
            "node_delta_pct": round((total_nodes - summary["K0"]["total_nodes"]) / summary["K0"]["total_nodes"] * 100.0, 2) if "K0" in summary else 0.0,
            "total_time_s": round(total_time, 3),
            "time_delta_pct": round((total_time - summary["K0"]["total_time_s"]) / summary["K0"]["total_time_s"] * 100.0, 2) if "K0" in summary else 0.0,
            "nps": nps,
            "ordering_time_s": round(total_ordering_time, 3),
            "1st_move_cutoff_rate": round(first_rate, 4),
            "sorts_saved": sorts_saved,
            "k0_move_agreement": f"{move_agree}/{len(corpus)} ({move_agree/len(corpus):.1%})",
            "k0_score_agreement": f"{score_agree}/{len(corpus)} ({score_agree/len(corpus):.1%})",
        }

        print(
            f"  Nodes: {total_nodes:,} ({summary[name]['node_delta_pct']:+.2f}%) | "
            f"Time: {total_time:.2f}s ({summary[name]['time_delta_pct']:+.2f}%) | "
            f"NPS: {nps:,} | Move Agreement: {summary[name]['k0_move_agreement']} | "
            f"Score Agreement: {summary[name]['k0_score_agreement']} | Sorts Saved: {sorts_saved:,}",
            flush=True,
        )

    out_file = Path("analysis/v0.48/raw/incremental_selection_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved incremental selection results to {out_file}", flush=True)


if __name__ == "__main__":
    run_experiments()

