"""Project Janus v0.49 - History Heuristic Optimization (Phase F).

Evaluates:
- Baseline K0: 2D history table (64x64 list of lists), eager scoring
- Candidate H1: Flat 1D history table (4096-element list, index = (from_sq << 6) | to_sq), cached lookups
- Candidate H2: Stage-separated Lazy History Scoring (search TT + Captures first; only score quiets with history if captures fail to cut off)

Tests across the 37-position diagnostic corpus at Depth 4.
Measures:
- History lookups executed
- History lookup time
- Wall-clock search time
- Total search nodes
- Search agreement with K0
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, List
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch


class H1FlatHistorySearch(JanusSearch):
    """Candidate H1: Uses flattened 4096 integer array for O(1) single-lookup history."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flat_history: List[int] = [0] * 4096
        self.history_lookups_count = 0

    def _update_history(self, move: chess.Move, depth: int) -> None:
        if not self.enable_history:
            return
        bonus = depth * depth
        idx = (move.from_square << 6) | move.to_square
        val = self.flat_history[idx] + bonus
        self.flat_history[idx] = 10000 if val > 10000 else val
        # Sync 2D table for compatibility
        self.history[move.from_square][move.to_square] = self.flat_history[idx]

    def _move_order_score(self, board, move, tt_move=None, ply=0, node_see=None, prev_move=None):
        if move == tt_move:
            return 10_000_000

        if move.promotion is not None:
            if move.promotion == chess.QUEEN:
                return 900_000
            return 800_000

        is_cap = board.is_capture(move)
        if is_cap:
            victim_type = board.piece_type_at(move.to_square)
            if victim_type is None and board.is_en_passant(move):
                victim_type = chess.PAWN
            attacker_type = board.piece_type_at(move.from_square)

            if victim_type is not None and attacker_type is not None:
                if self.enable_see_ordering:
                    see_val = self._see(board, move)
                    if see_val < 0:
                        return -100_000 + see_val
                    return 100_000 + (victim_type * 10) - attacker_type
                return 100_000 + (victim_type * 10) - attacker_type
            return 100_000

        score = 0
        if ply < self.max_killers_ply and self.killers[ply][0] == move:
            return 700_000
        if ply < self.max_killers_ply and self.killers[ply][1] == move:
            return 600_000

        if self.enable_countermoves and prev_move is not None:
            if move == self.countermoves[prev_move.from_square][prev_move.to_square]:
                return 550_000

        if self.enable_history:
            self.history_lookups_count += 1
            idx = (move.from_square << 6) | move.to_square
            return self.flat_history[idx]

        return score


class H2LazyQuietHistorySearch(JanusSearch):
    """Candidate H2: Staged Lazy Ordering. Yields TT, then Captures.

    Only scores and sorts quiet moves using history if TT and Captures fail to cut off.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_lookups_count = 0
        self.quiet_sorts_saved = 0
        self.quiet_sorts_executed = 0

    def _select_ordered_moves(self, board, tt_move=None, ply=0, prev_move=None):
        moves = list(board.legal_moves)
        total_legal_count = len(moves)
        if total_legal_count <= 1:
            return moves, None, total_legal_count

        # Partition moves into tactical (TT, promotions, captures) and quiet
        tactical_moves = []
        quiet_moves = []

        for m in moves:
            if m == tt_move:
                tactical_moves.append(m)
            elif m.promotion is not None or board.is_capture(m):
                tactical_moves.append(m)
            else:
                quiet_moves.append(m)

        # Sort tactical moves (small list, usually 1-4 moves)
        if len(tactical_moves) > 1:
            node_see = {} if self.enable_see_ordering else None
            tactical_moves.sort(
                key=lambda m: self._move_order_score(board, m, tt_move, ply, node_see=node_see, prev_move=prev_move),
                reverse=True,
            )

        # Provider for quiet moves
        def rest_provider():
            if not quiet_moves:
                return []
            self.quiet_sorts_executed += 1
            node_see = None
            for m in quiet_moves:
                self.history_lookups_count += 1
            quiet_moves.sort(
                key=lambda m: self._move_order_score(board, m, None, ply, node_see=node_see, prev_move=prev_move),
                reverse=True,
            )
            return quiet_moves

        if not tactical_moves:
            # No tactical moves, must evaluate quiets immediately
            return rest_provider(), None, total_legal_count

        self.quiet_sorts_saved += 1
        return tactical_moves, rest_provider, total_legal_count


def run_history_optimization():
    corpus_path = Path("analysis/v0.49/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.49 - HISTORY HEURISTIC OPTIMIZATION (Phase F)", flush=True)
    print("=" * 80, flush=True)

    depth = 4
    results = []

    k0_time = 0.0
    h1_time = 0.0
    h2_time = 0.0

    k0_nodes = 0
    h1_nodes = 0
    h2_nodes = 0

    h1_matches_k0 = 0
    h2_matches_k0 = 0

    h1_lookups_total = 0
    h2_lookups_total = 0

    for pos in corpus:
        pos_id = pos["id"]
        fen = pos["fen"]
        board = chess.Board(fen)

        # K0 baseline
        s_k0 = JanusSearch(enable_lazy_move_selection=False)
        t0 = time.perf_counter()
        res_k0 = s_k0.search(board.copy(), max_depth=depth)
        dur_k0 = time.perf_counter() - t0

        # H1 Flat History
        s_h1 = H1FlatHistorySearch(enable_lazy_move_selection=False)
        t0 = time.perf_counter()
        res_h1 = s_h1.search(board.copy(), max_depth=depth)
        dur_h1 = time.perf_counter() - t0

        # H2 Lazy Quiet History
        s_h2 = H2LazyQuietHistorySearch(enable_lazy_move_selection=True)
        t0 = time.perf_counter()
        res_h2 = s_h2.search(board.copy(), max_depth=depth)
        dur_h2 = time.perf_counter() - t0

        mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None
        mv_h1 = res_h1.best_move.uci() if res_h1.best_move else None
        mv_h2 = res_h2.best_move.uci() if res_h2.best_move else None

        if res_h1.nodes == res_k0.nodes and mv_h1 == mv_k0:
            h1_matches_k0 += 1
        if mv_h2 == mv_k0:
            h2_matches_k0 += 1

        k0_time += dur_k0
        h1_time += dur_h1
        h2_time += dur_h2

        k0_nodes += res_k0.nodes
        h1_nodes += res_h1.nodes
        h2_nodes += res_h2.nodes

        h1_lookups_total += s_h1.history_lookups_count
        h2_lookups_total += s_h2.history_lookups_count

        results.append({
            "pos_id": pos_id,
            "k0_nodes": res_k0.nodes,
            "h1_nodes": res_h1.nodes,
            "h2_nodes": res_h2.nodes,
            "k0_time": round(dur_k0, 4),
            "h1_time": round(dur_h1, 4),
            "h2_time": round(dur_h2, 4),
            "k0_move": mv_k0,
            "h1_move": mv_h1,
            "h2_move": mv_h2,
            "h1_lookups": s_h1.history_lookups_count,
            "h2_lookups": s_h2.history_lookups_count,
            "h2_quiet_sorts_saved": s_h2.quiet_sorts_saved,
            "h2_quiet_sorts_executed": s_h2.quiet_sorts_executed,
        })

    print(f"\n--- Aggregate Results across {len(corpus)} positions at Depth 4 ---", flush=True)
    print(f"  Nodes:       K0 = {k0_nodes} | H1 = {h1_nodes} | H2 = {h2_nodes}", flush=True)
    print(f"  H1 Match:    {h1_matches_k0}/{len(corpus)} exact node-and-move identity to K0 ({h1_matches_k0/len(corpus)*100:.1f}%)", flush=True)
    print(f"  H2 Match:    {h2_matches_k0}/{len(corpus)} move agreement with K0 ({h2_matches_k0/len(corpus)*100:.1f}%)", flush=True)
    print(f"  Runtime:     K0 = {k0_time:.2f}s | H1 = {h1_time:.2f}s | H2 = {h2_time:.2f}s", flush=True)
    print(f"  Time Delta:  H1 vs K0: {(h1_time - k0_time)/k0_time*100:+.2f}% | H2 vs K0: {(h2_time - k0_time)/k0_time*100:+.2f}%", flush=True)
    print(f"  Lookups:     H1 = {h1_lookups_total:,} lookups | H2 = {h2_lookups_total:,} lookups", flush=True)
    print(f"  Lookup Cut:  H2 reduced history lookups by {(h1_lookups_total - h2_lookups_total)/h1_lookups_total*100:.1f}%!", flush=True)

    out_file = Path("analysis/v0.49/raw/history_optimization_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "k0_time": round(k0_time, 3),
            "h1_time": round(h1_time, 3),
            "h2_time": round(h2_time, 3),
            "k0_nodes": k0_nodes,
            "h1_nodes": h1_nodes,
            "h2_nodes": h2_nodes,
            "h1_lookups": h1_lookups_total,
            "h2_lookups": h2_lookups_total,
            "records": results,
        }, f, indent=2)

    print(f"\nHistory optimization benchmark complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_history_optimization()

