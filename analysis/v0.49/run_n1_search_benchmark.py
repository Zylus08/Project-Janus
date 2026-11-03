"""Project Janus v0.49 - Candidate N1 Search Integration & Performance (Phases D3 & E2).

Implements Candidate N1 (Native Move Picker Searcher) which delegates move selection
to the compiled C DLL (move_picker.dll) via native_stable_partial_sort.

Compares K0, L1, and N1 at Depth 4 across the 37-position diagnostic corpus.
Evaluates:
- Exact node count agreement (search fidelity)
- Root score and best move agreement
- Wall-clock runtime and ordering overhead
- Quiescence nodes and beta cutoffs
"""

import sys
import os
import json
import time
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent / "native"))

from janus.search import JanusSearch
from native_picker import native_stable_partial_sort, is_native_available


class N1JanusSearch(JanusSearch):
    """Candidate N1: Searcher using compiled native C move picker for move ordering."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.native_sort_calls = 0
        self.native_sort_time = 0.0

    def _ordered_moves(self, board, tt_move=None, ply=0, prev_move=None):
        moves = list(board.legal_moves)
        n = len(moves)
        if n <= 1:
            return moves

        # Score moves using baseline scoring
        node_see = {} if self.enable_see_ordering else None
        scores = [
            self._move_order_score(board, m, tt_move, ply, node_see=node_see, prev_move=prev_move)
            for m in moves
        ]

        t0 = time.perf_counter()
        # Native stable sort
        sorted_indices = native_stable_partial_sort(scores, n)
        dur = time.perf_counter() - t0

        self.native_sort_calls += 1
        self.native_sort_time += dur
        self.total_ordering_time += dur

        return [moves[idx] for idx in sorted_indices]

    def _select_ordered_moves(self, board, tt_move=None, ply=0, prev_move=None):
        moves = list(board.legal_moves)
        total_legal_count = len(moves)
        if total_legal_count <= 1:
            return moves, None, total_legal_count

        node_see = {} if self.enable_see_ordering else None
        scores = [
            self._move_order_score(board, m, tt_move, ply, node_see=node_see, prev_move=prev_move)
            for m in moves
        ]

        t0 = time.perf_counter()
        sorted_indices = native_stable_partial_sort(scores, total_legal_count)
        dur = time.perf_counter() - t0

        self.native_sort_calls += 1
        self.native_sort_time += dur
        self.total_ordering_time += dur

        return [moves[idx] for idx in sorted_indices], None, total_legal_count


def run_n1_search_benchmark():
    corpus_path = Path("analysis/v0.49/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.49 - CANDIDATE N1 SEARCH BENCHMARK (Depth 4)", flush=True)
    print("=" * 80, flush=True)

    depth = 4
    results = []

    k0_nodes_sum = 0
    l1_nodes_sum = 0
    n1_nodes_sum = 0

    k0_time_sum = 0.0
    l1_time_sum = 0.0
    n1_time_sum = 0.0

    k0_ord_sum = 0.0
    l1_ord_sum = 0.0
    n1_ord_sum = 0.0

    n1_k0_node_matches = 0
    n1_k0_move_matches = 0

    for pos in corpus:
        pos_id = pos["id"]
        fen = pos["fen"]
        board = chess.Board(fen)

        # 1. Baseline K0
        s_k0 = JanusSearch(enable_lazy_move_selection=False, diagnostic_ordering=True)
        t0 = time.perf_counter()
        res_k0 = s_k0.search(board.copy(), max_depth=depth)
        t_k0 = time.perf_counter() - t0

        # 2. Candidate L1
        s_l1 = JanusSearch(enable_lazy_move_selection=True, diagnostic_ordering=True)
        t0 = time.perf_counter()
        res_l1 = s_l1.search(board.copy(), max_depth=depth)
        t_l1 = time.perf_counter() - t0

        # 3. Candidate N1
        s_n1 = N1JanusSearch(enable_lazy_move_selection=False, diagnostic_ordering=True)
        t0 = time.perf_counter()
        res_n1 = s_n1.search(board.copy(), max_depth=depth)
        t_n1 = time.perf_counter() - t0

        mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None
        mv_l1 = res_l1.best_move.uci() if res_l1.best_move else None
        mv_n1 = res_n1.best_move.uci() if res_n1.best_move else None

        node_match = (res_n1.nodes == res_k0.nodes)
        move_match = (mv_n1 == mv_k0)

        if node_match:
            n1_k0_node_matches += 1
        if move_match:
            n1_k0_move_matches += 1

        k0_nodes_sum += res_k0.nodes
        l1_nodes_sum += res_l1.nodes
        n1_nodes_sum += res_n1.nodes

        k0_time_sum += t_k0
        l1_time_sum += t_l1
        n1_time_sum += t_n1

        k0_ord_sum += s_k0.total_ordering_time
        l1_ord_sum += s_l1.total_ordering_time
        n1_ord_sum += s_n1.total_ordering_time

        results.append({
            "pos_id": pos_id,
            "k0_nodes": res_k0.nodes,
            "l1_nodes": res_l1.nodes,
            "n1_nodes": res_n1.nodes,
            "k0_time": round(t_k0, 4),
            "l1_time": round(t_l1, 4),
            "n1_time": round(t_n1, 4),
            "k0_move": mv_k0,
            "l1_move": mv_l1,
            "n1_move": mv_n1,
            "k0_score": res_k0.score,
            "n1_score": res_n1.score,
            "node_match": node_match,
            "move_match": move_match,
        })

    print(f"\n--- Aggregate Results across {len(corpus)} positions at Depth 4 ---", flush=True)
    print(f"  Nodes:       K0 = {k0_nodes_sum} | L1 = {l1_nodes_sum} | N1 = {n1_nodes_sum}", flush=True)
    print(f"  Node Match:  N1 matches K0 in {n1_k0_node_matches}/{len(corpus)} positions ({n1_k0_node_matches/len(corpus)*100:.1f}%)", flush=True)
    print(f"  Move Match:  N1 matches K0 in {n1_k0_move_matches}/{len(corpus)} positions ({n1_k0_move_matches/len(corpus)*100:.1f}%)", flush=True)
    print(f"  Runtime:     K0 = {k0_time_sum:.2f}s | L1 = {l1_time_sum:.2f}s | N1 = {n1_time_sum:.2f}s", flush=True)
    print(f"  Time Delta:  N1 vs K0: {(n1_time_sum - k0_time_sum)/k0_time_sum*100:+.2f}% | L1 vs K0: {(l1_time_sum - k0_time_sum)/k0_time_sum*100:+.2f}%", flush=True)
    print(f"  Ord Time:    K0 = {k0_ord_sum:.3f}s | L1 = {l1_ord_sum:.3f}s | N1 = {n1_ord_sum:.3f}s", flush=True)

    out_file = Path("analysis/v0.49/raw/n1_search_benchmark_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "k0_nodes": k0_nodes_sum,
            "l1_nodes": l1_nodes_sum,
            "n1_nodes": n1_nodes_sum,
            "k0_time": round(k0_time_sum, 3),
            "l1_time": round(l1_time_sum, 3),
            "n1_time": round(n1_time_sum, 3),
            "n1_vs_k0_time_pct": round((n1_time_sum - k0_time_sum)/k0_time_sum*100, 2),
            "node_matches": n1_k0_node_matches,
            "move_matches": n1_k0_move_matches,
            "records": results,
        }, f, indent=2)

    print(f"\nN1 search benchmark complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_n1_search_benchmark()

