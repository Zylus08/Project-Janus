"""Profile Move Ordering variants and Reverse Futility Pruning on 8 representative positions.

Evaluates:
- 'baseline': Default v0.40 baseline (K0, no countermoves, no history penalty, no RFP)
- 'ord_malus': History penalty only (penalize quiet moves searched prior to beta cutoff)
- 'ord_cm': Countermove heuristic only (countermove prioritized at 550_000)
- 'ord1': Combined move ordering enhancements (countermove + history penalty)
- 'rfp': Reverse futility pruning (depth <= 2, margin 120 cp/depth)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import chess

from janus.search import JanusSearch

ROOT = Path(__file__).resolve().parents[1]

PROFILING_POSITIONS = [
    {
        "id": "startpos",
        "category": "opening",
        "description": "Standard initial starting position",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "history": [],
    },
    {
        "id": "open_tactical",
        "category": "tactical_middlegame",
        "description": "Open center with developed minor pieces and tactical tension",
        "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
        "history": [],
    },
    {
        "id": "quiet_middlegame",
        "category": "quiet_middlegame",
        "description": "Closed positional Ruy Lopez structure with subtle pawn chains",
        "fen": "r2q1rk1/1bp1bppp/p1np1n2/1p2p3/4P3/1B1P1N2/PPPN1PPP/R1BQR1K1 w - - 0 10",
        "history": [],
    },
    {
        "id": "forcing_checks",
        "category": "forcing_checks",
        "description": "Position with open king lines and forcing checks",
        "fen": "r1b1k2r/ppppqppp/2n5/4P3/1b2n3/2P2N2/PP2QPPP/RNB1KB1R b KQkq - 0 6",
        "history": [],
    },
    {
        "id": "endgame_few_pieces",
        "category": "endgame",
        "description": "Symmetrical pawn endgame with active kings",
        "fen": "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",
        "history": [],
    },
    {
        "id": "forced_mate",
        "category": "forced_mate",
        "description": "Tactical queen mate in two plies",
        "fen": "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
        "history": [],
    },
    {
        "id": "repetition_history",
        "category": "repetition_history",
        "description": "Position reached after repetitive knight cycles with move history",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "history": ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"],
    },
    {
        "id": "qsearch_expansion",
        "category": "qsearch_expansion",
        "description": "Complex capture chain with reciprocal trades across files",
        "fen": "r3k2r/pb1q1ppp/1pnp4/2p1p3/2P1P3/1PNP4/PB1Q1PPP/R3K2R w KQkq - 0 1",
        "history": [],
    },
]


def run_configuration_profile(
    config_name: str,
    enable_countermoves: bool,
    enable_history_malus: bool,
    enable_rfp: bool,
    target_depth: int = 4,
) -> dict[str, Any]:
    print(f"\n--- Profiling Configuration: {config_name} (depth={target_depth}) ---")
    results = []
    total_nodes = 0
    total_time_ms = 0.0
    total_beta_cutoffs = 0
    total_cm_cutoffs = 0
    total_rfp_cutoffs = 0
    total_tt_hits = 0
    total_tt_probes = 0

    for pos in PROFILING_POSITIONS:
        board = chess.Board(pos["fen"])
        for m_str in pos["history"]:
            board.push(chess.Move.from_uci(m_str))

        engine = JanusSearch(
            enable_countermoves=enable_countermoves,
            enable_history_malus=enable_history_malus,
            enable_rfp=enable_rfp,
        )

        t0 = time.perf_counter()
        res = engine.search(board, max_depth=target_depth)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        total_nodes += res.nodes
        total_time_ms += elapsed_ms
        total_beta_cutoffs += res.beta_cutoffs
        total_cm_cutoffs += res.countermove_cutoffs
        total_rfp_cutoffs += res.rfp_cutoffs
        total_tt_hits += res.tt_hits
        total_tt_probes += res.tt_probes

        nps = (res.nodes / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0.0
        best_uci = res.best_move.uci() if res.best_move else ""
        pv_str = " ".join(m.uci() for m in res.pv)

        results.append({
            "id": pos["id"],
            "best_move": best_uci,
            "score": res.score,
            "depth": res.depth,
            "nodes": res.nodes,
            "elapsed_ms": round(elapsed_ms, 2),
            "nps": round(nps, 1),
            "beta_cutoffs": res.beta_cutoffs,
            "countermove_cutoffs": res.countermove_cutoffs,
            "rfp_cutoffs": res.rfp_cutoffs,
            "tt_hits": res.tt_hits,
            "tt_probes": res.tt_probes,
            "pv": pv_str,
        })
        print(f"  {pos['id']:<20}: {best_uci:>5} | score: {res.score:>5} | nodes: {res.nodes:>6} | {elapsed_ms:>6.1f}ms | {nps:>7.1f} NPS | cutoffs: {res.beta_cutoffs}")

    pooled_nps = (total_nodes / (total_time_ms / 1000.0)) if total_time_ms > 0 else 0.0
    tt_hit_rate = (total_tt_hits / total_tt_probes * 100.0) if total_tt_probes > 0 else 0.0

    summary = {
        "config_name": config_name,
        "enable_countermoves": enable_countermoves,
        "enable_history_malus": enable_history_malus,
        "enable_rfp": enable_rfp,
        "target_depth": target_depth,
        "total_nodes": total_nodes,
        "total_time_ms": round(total_time_ms, 2),
        "pooled_nps": round(pooled_nps, 1),
        "total_beta_cutoffs": total_beta_cutoffs,
        "total_countermove_cutoffs": total_cm_cutoffs,
        "total_rfp_cutoffs": total_rfp_cutoffs,
        "total_tt_hits": total_tt_hits,
        "total_tt_probes": total_tt_probes,
        "tt_hit_rate_pct": round(tt_hit_rate, 2),
        "positions": results,
    }
    print(f"SUMMARY {config_name}: Nodes: {total_nodes:,} | Time: {total_time_ms:.1f}ms | Pooled NPS: {pooled_nps:,.1f} | Beta Cutoffs: {total_beta_cutoffs} | CM Cutoffs: {total_cm_cutoffs} | RFP Cutoffs: {total_rfp_cutoffs}")
    return summary


def main() -> None:
    configs = [
        ("baseline", False, False, False),
        ("ord_malus", False, True, False),
        ("ord_cm", True, False, False),
        ("ord1", True, True, False),
        ("rfp", False, False, True),
    ]

    all_summaries = {}
    for name, cm, malus, rfp in configs:
        summary = run_configuration_profile(name, cm, malus, rfp, target_depth=4)
        all_summaries[name] = summary

    # Comparisons against baseline
    base_nodes = all_summaries["baseline"]["total_nodes"]
    base_time = all_summaries["baseline"]["total_time_ms"]

    print("\n" + "=" * 70)
    print("COMPARATIVE EFFICIENCY ON 8 REPRESENTATIVE POSITIONS (DEPTH 4)")
    print("=" * 70)
    print(f"{'Config':<12} | {'Nodes':>8} | {'Node d%':>8} | {'Time (ms)':>10} | {'Time d%':>8} | {'Pooled NPS':>11} | {'Cutoffs':>8} | {'Special':>10}")
    print("-" * 70)

    for name in all_summaries:
        s = all_summaries[name]
        node_delta = (s["total_nodes"] - base_nodes) / base_nodes * 100.0
        time_delta = (s["total_time_ms"] - base_time) / base_time * 100.0
        special = (
            f"CM={s['total_countermove_cutoffs']}"
            if s["total_countermove_cutoffs"] > 0
            else (f"RFP={s['total_rfp_cutoffs']}" if s["total_rfp_cutoffs"] > 0 else "-")
        )
        print(
            f"{name:<12} | {s['total_nodes']:>8,d} | {node_delta:>+7.2f}% | {s['total_time_ms']:>10.1f} | {time_delta:>+7.2f}% | {s['pooled_nps']:>11.1f} | {s['total_beta_cutoffs']:>8d} | {special:>10}"
        )
    print("=" * 70)

    out_path = ROOT / "analysis" / "v0.40" / "search_enhancement_profiles.json"
    out_path.write_text(json.dumps(all_summaries, indent=2), encoding="utf-8")
    print(f"\nWrote comparative profiles to {out_path}")


if __name__ == "__main__":
    main()
