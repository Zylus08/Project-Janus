"""Project Janus v0.49 - Killer Move Integration in Lazy Framework (Phase G).

Evaluates Candidate K1 (Multi-Stage Lazy Picker with Killer Priority):
- Phase 1: TT Move (if legal)
- Phase 2: Good Captures & Promotions (SEE >= 0)
- Phase 3: Killer Moves (Slot 0, then Slot 1, if legal, quiet, and not searched)
- Phase 4: Remaining moves (underpromotions, losing captures, quiets with history)

Tests across the 37-position diagnostic corpus at Depth 4.
Measures:
- Killer cutoffs produced
- Killer availability rate
- Avoided sort operations
- Search nodes, wall-clock time, and best-move agreement with K0.
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


class K1LazyKillerSearch(JanusSearch):
    """Candidate K1: Multi-stage lazy move selector with TT -> Captures -> Killers -> Quiets."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.killer_considered = 0
        self.killer_cutoffs_count = 0
        self.killer_searched_first = 0
        self.tt_immediate_cutoffs = 0

    def _select_ordered_moves(self, board, tt_move=None, ply=0, prev_move=None):
        legal_moves = list(board.legal_moves)
        total_legal_count = len(legal_moves)
        if total_legal_count <= 1:
            return legal_moves, None, total_legal_count

        # Extract TT move
        phase1_moves = []
        if tt_move is not None and tt_move in legal_moves:
            phase1_moves.append(tt_move)

        # Provider for subsequent stages
        def rest_provider():
            searched = set(phase1_moves)
            remaining = [m for m in legal_moves if m not in searched]

            # Stage 2: Captures & Promotions
            caps = []
            quiets = []
            for m in remaining:
                if m.promotion is not None or board.is_capture(m):
                    caps.append(m)
                else:
                    quiets.append(m)

            if caps:
                node_see = {} if self.enable_see_ordering else None
                caps.sort(
                    key=lambda m: self._move_order_score(board, m, None, ply, node_see=node_see, prev_move=prev_move),
                    reverse=True,
                )

            # Stage 3: Extract Killers from quiets
            killers = []
            if ply < self.max_killers_ply:
                k0 = self.killers[ply][0]
                k1 = self.killers[ply][1]
                if k0 is not None and k0 in quiets:
                    self.killer_considered += 1
                    killers.append(k0)
                if k1 is not None and k1 != k0 and k1 in quiets:
                    self.killer_considered += 1
                    killers.append(k1)

            killer_set = set(killers)
            rem_quiets = [m for m in quiets if m not in killer_set]

            # Stage 4: Quiets sorted by history
            if rem_quiets:
                rem_quiets.sort(
                    key=lambda m: self._move_order_score(board, m, None, ply, node_see=None, prev_move=prev_move),
                    reverse=True,
                )

            return caps + killers + rem_quiets

        if phase1_moves:
            return phase1_moves, rest_provider, total_legal_count
        else:
            return rest_provider(), None, total_legal_count


def run_killer_analysis():
    corpus_path = Path("analysis/v0.49/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.49 - KILLER MOVE INTEGRATION IN LAZY FRAMEWORK (Phase G)", flush=True)
    print("=" * 80, flush=True)

    depth = 4
    results = []

    k0_time = 0.0
    k1_time = 0.0
    l1_time = 0.0

    k0_nodes = 0
    k1_nodes = 0
    l1_nodes = 0

    k1_agreements = 0
    k1_killers_total = 0

    for pos in corpus:
        pos_id = pos["id"]
        fen = pos["fen"]
        board = chess.Board(fen)

        # Baseline K0
        s_k0 = JanusSearch(enable_lazy_move_selection=False)
        t0 = time.perf_counter()
        res_k0 = s_k0.search(board.copy(), max_depth=depth)
        dur_k0 = time.perf_counter() - t0

        # Candidate L1
        s_l1 = JanusSearch(enable_lazy_move_selection=True)
        t0 = time.perf_counter()
        res_l1 = s_l1.search(board.copy(), max_depth=depth)
        dur_l1 = time.perf_counter() - t0

        # Candidate K1
        s_k1 = K1LazyKillerSearch(enable_lazy_move_selection=True)
        t0 = time.perf_counter()
        res_k1 = s_k1.search(board.copy(), max_depth=depth)
        dur_k1 = time.perf_counter() - t0

        mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None
        mv_k1 = res_k1.best_move.uci() if res_k1.best_move else None

        if mv_k1 == mv_k0:
            k1_agreements += 1

        k0_time += dur_k0
        l1_time += dur_l1
        k1_time += dur_k1

        k0_nodes += res_k0.nodes
        l1_nodes += res_l1.nodes
        k1_nodes += res_k1.nodes

        k1_killers_total += s_k1.killer_considered

        results.append({
            "pos_id": pos_id,
            "k0_nodes": res_k0.nodes,
            "l1_nodes": res_l1.nodes,
            "k1_nodes": res_k1.nodes,
            "k0_time": round(dur_k0, 4),
            "l1_time": round(dur_l1, 4),
            "k1_time": round(dur_k1, 4),
            "k0_move": mv_k0,
            "k1_move": mv_k1,
            "same_move": (mv_k1 == mv_k0),
            "killers_considered": s_k1.killer_considered,
        })

    print(f"\n--- Aggregate Results across {len(corpus)} positions at Depth 4 ---", flush=True)
    print(f"  Nodes:       K0 = {k0_nodes} | L1 = {l1_nodes} | K1 = {k1_nodes}", flush=True)
    print(f"  Node Delta:  K1 vs K0: {(k1_nodes - k0_nodes)/k0_nodes*100:+.2f}%", flush=True)
    print(f"  Runtime:     K0 = {k0_time:.2f}s | L1 = {l1_time:.2f}s | K1 = {k1_time:.2f}s", flush=True)
    print(f"  Time Delta:  K1 vs K0: {(k1_time - k0_time)/k0_time*100:+.2f}% | L1 vs K0: {(l1_time - k0_time)/k0_time*100:+.2f}%", flush=True)
    print(f"  Agreement:   K1 matches K0 in {k1_agreements}/{len(corpus)} positions ({k1_agreements/len(corpus)*100:.1f}%)", flush=True)
    print(f"  Killers:     {k1_killers_total:,} killer move opportunities identified", flush=True)

    out_file = Path("analysis/v0.49/raw/killer_analysis_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "k0_time": round(k0_time, 3),
            "l1_time": round(l1_time, 3),
            "k1_time": round(k1_time, 3),
            "k0_nodes": k0_nodes,
            "l1_nodes": l1_nodes,
            "k1_nodes": k1_nodes,
            "k1_agreements": k1_agreements,
            "records": results,
        }, f, indent=2)

    print(f"\nKiller analysis complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_killer_analysis()

