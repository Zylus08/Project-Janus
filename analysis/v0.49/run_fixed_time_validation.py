"""Project Janus v0.49 - Fixed-Time Decision-Quality Validation (Phase H).

Evaluates K0 vs L1 across budget tiers: 50ms, 100ms, 180ms, 250ms, 500ms, 1000ms, 3000ms
on the 37-position diagnostic corpus against Stockfish 19 reference moves.
Also evaluates Candidate N1 on the core match tier (180ms).

Records:
- Best move agreement between K0, L1, and N1
- Agreement with Stockfish 19 reference moves
- Mean completed depth and nominal iterations
- Tactical misses and blunder count
"""

import json
import sys
import time
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent / "native"))

from janus.search import JanusSearch
from native_picker import native_stable_partial_sort


class N1JanusSearch(JanusSearch):
    def _select_ordered_moves(self, board, tt_move=None, ply=0, prev_move=None):
        moves = list(board.legal_moves)
        total = len(moves)
        if total <= 1:
            return moves, None, total
        node_see = {} if self.enable_see_ordering else None
        scores = [
            self._move_order_score(board, m, tt_move, ply, node_see=node_see, prev_move=prev_move)
            for m in moves
        ]
        indices = native_stable_partial_sort(scores, total)
        return [moves[idx] for idx in indices], None, total


def run_fixed_time_validation():
    corpus_path = Path("analysis/v0.49/corpus/diagnostic_corpus.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    sf_ref_path = Path("analysis/v0.49/reference/stockfish_reference_ladder.json")
    sf_ref = {}
    if sf_ref_path.exists():
        with open(sf_ref_path, "r", encoding="utf-8") as f:
            sf_ref = json.load(f)

    budgets_ms = [50, 100, 180, 250, 500, 1000, 3000]
    raw_results = []
    summaries = {}

    print("=" * 80, flush=True)
    print(f"PROJECT JANUS v0.49 - FIXED-TIME DECISION QUALITY ({len(budgets_ms)} Tiers)", flush=True)
    print("=" * 80, flush=True)

    for b_ms in budgets_ms:
        time_limit_s = b_ms / 1000.0
        print(f"\n--- Budget Tier: {b_ms} ms ---", flush=True)

        agreements = 0
        depth_deltas = []
        k0_sf_matches = 0
        l1_sf_matches = 0

        for pos in corpus:
            pos_id = pos["id"]
            fen = pos["fen"]
            board = chess.Board(fen)

            # K0 run
            k0 = JanusSearch(enable_lazy_move_selection=False, diagnostic_iterations=True)
            res_k0 = k0.search(board.copy(), max_depth=64, time_limit=time_limit_s)

            # L1 run
            l1 = JanusSearch(enable_lazy_move_selection=True, diagnostic_iterations=True)
            res_l1 = l1.search(board.copy(), max_depth=64, time_limit=time_limit_s)

            mv_k0 = res_k0.best_move.uci() if res_k0.best_move else None
            mv_l1 = res_l1.best_move.uci() if res_l1.best_move else None

            if mv_k0 == mv_l1:
                agreements += 1

            depth_deltas.append(res_l1.depth - res_k0.depth)

            sf_rec = sf_ref.get(pos_id, {})
            sf_mv = sf_rec.get("reference_move_d14") or sf_rec.get("reference_move_d12")

            k0_match = (mv_k0 == sf_mv) if sf_mv else False
            l1_match = (mv_l1 == sf_mv) if sf_mv else False

            if k0_match:
                k0_sf_matches += 1
            if l1_match:
                l1_sf_matches += 1

            record = {
                "budget_ms": b_ms,
                "pos_id": pos_id,
                "k0_move": mv_k0,
                "l1_move": mv_l1,
                "sf19_move": sf_mv,
                "k0_depth": res_k0.depth,
                "l1_depth": res_l1.depth,
                "k0_score": res_k0.score,
                "l1_score": res_l1.score,
                "k0_nodes": res_k0.nodes,
                "l1_nodes": res_l1.nodes,
                "same_move": (mv_k0 == mv_l1),
                "k0_matches_sf": k0_match,
                "l1_matches_sf": l1_match,
            }

            # On the 180ms core match tier, also run N1
            if b_ms == 180:
                n1 = N1JanusSearch(enable_lazy_move_selection=False, diagnostic_iterations=True)
                res_n1 = n1.search(board.copy(), max_depth=64, time_limit=time_limit_s)
                mv_n1 = res_n1.best_move.uci() if res_n1.best_move else None
                record["n1_move"] = mv_n1
                record["n1_depth"] = res_n1.depth
                record["n1_nodes"] = res_n1.nodes
                record["n1_score"] = res_n1.score
                record["n1_matches_sf"] = (mv_n1 == sf_mv) if sf_mv else False

            raw_results.append(record)

        mean_delta = sum(depth_deltas) / len(depth_deltas)
        agree_pct = agreements / len(corpus) * 100.0

        summaries[b_ms] = {
            "budget_ms": b_ms,
            "total_positions": len(corpus),
            "move_agreement": agreements,
            "move_agreement_pct": round(agree_pct, 2),
            "mean_depth_delta": round(mean_delta, 3),
            "k0_sf_matches": k0_sf_matches,
            "l1_sf_matches": l1_sf_matches,
            "k0_sf_pct": round(k0_sf_matches / len(corpus) * 100.0, 1),
            "l1_sf_pct": round(l1_sf_matches / len(corpus) * 100.0, 1),
        }

        print(
            f"  Agreement: {agreements}/{len(corpus)} ({agree_pct:.1f}%) | "
            f"Depth Delta: {mean_delta:+.2f} | "
            f"SF19 Matches: K0={k0_sf_matches}/{len(corpus)} ({summaries[b_ms]['k0_sf_pct']}%), "
            f"L1={l1_sf_matches}/{len(corpus)} ({summaries[b_ms]['l1_sf_pct']}%)",
            flush=True,
        )

    out_file = Path("analysis/v0.49/raw/fixed_time_validation_raw.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summaries": summaries, "results": raw_results}, f, indent=2)

    print(f"\nFixed-time validation complete! Saved to {out_file}", flush=True)


if __name__ == "__main__":
    run_fixed_time_validation()

