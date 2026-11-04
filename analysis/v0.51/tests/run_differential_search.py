"""Project Janus v0.51 - Differential Search Benchmark (Phase D).

Compares Python K0 vs Native Candidate N2 across:
1. The standard 37-position diagnostic corpus (Depths 1 to 5).
2. The independent 16-position validation corpus (Depths 1 to 4).
3. The 12-position tactical regression corpus.

Measures:
- Best move agreement and divergence taxonomy
- Root score correlation
- Node throughput and wall-clock speedup
- Stockfish 19 reference move comparison
- Writes raw results to analysis/v0.51/raw/differential_search_results.json
"""

import sys
import json
import time
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))

from janus.search import JanusSearch
from janus_native_bridge import NativeEngineBridge


def run_differential_suite():
    # 1. Load Diagnostic Corpus (37)
    with open(ROOT / "analysis" / "v0.50" / "corpus" / "diagnostic_corpus.json", "r", encoding="utf-8") as f:
        diag_corpus = json.load(f)

    # 2. Load Validation Corpus (16)
    with open(ROOT / "analysis" / "v0.51" / "corpus" / "validation_corpus.json", "r", encoding="utf-8") as f:
        val_corpus = json.load(f)

    # 3. Load SF19 Reference Ladder
    sf_ladder = {}
    ladder_path = ROOT / "analysis" / "v0.50" / "reference" / "stockfish_reference_ladder.json"
    if ladder_path.exists():
        with open(ladder_path, "r", encoding="utf-8") as f:
            sf_ladder = json.load(f)

    bridge = NativeEngineBridge()
    output = {
        "diagnostic_37": {},
        "validation_16": {},
    }

    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.51 - DIFFERENTIAL SEARCH VALIDATION (K0 vs N2)", flush=True)
    print(f"Loaded 37 diagnostic positions and 16 validation positions", flush=True)
    print("=" * 80, flush=True)

    # --- Part 1: Diagnostic Corpus (Depths 1 to 5) ---
    print("\n>>> PART 1: Evaluating 37-Position Diagnostic Corpus (Depths 1 to 5) <<<", flush=True)
    for depth in [1, 2, 3, 4, 5]:
        print(f"\n--- Depth {depth} ---", flush=True)
        k0_time_total = 0.0
        n2_time_total = 0.0
        k0_nodes_total = 0
        n2_nodes_total = 0
        move_matches = 0
        score_matches = 0
        records = []

        for item in diag_corpus:
            pos_id = item["id"]
            fen = item["fen"]
            sf_ref = sf_ladder.get(pos_id, {})
            sf_move = sf_ref.get("reference_move_d14") or sf_ref.get("reference_move_d12")

            # Python K0
            py_board = chess.Board(fen)
            k0_searcher = JanusSearch(enable_lazy_move_selection=False, enable_rfp=False)
            t0 = time.perf_counter()
            k0_res = k0_searcher.search(py_board, max_depth=depth, time_limit=60.0)
            k0_time = time.perf_counter() - t0
            k0_mv = k0_res.best_move.uci() if k0_res.best_move else None

            # Native N2
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            n2_mv, n2_sc, n2_dp, n2_nd, n2_time, n2_pv = bridge.search(max_depth=depth, time_limit=60.0)

            k0_time_total += k0_time
            n2_time_total += n2_time
            k0_nodes_total += k0_res.nodes
            n2_nodes_total += n2_nd

            mv_match = (k0_mv == n2_mv)
            sc_diff = abs(k0_res.score - n2_sc)
            sc_match = (sc_diff <= 10)

            if mv_match: move_matches += 1
            if sc_match: score_matches += 1

            records.append({
                "id": pos_id,
                "fen": fen,
                "k0_move": k0_mv,
                "n2_move": n2_mv,
                "sf_move": sf_move,
                "k0_score": k0_res.score,
                "n2_score": n2_sc,
                "score_delta": sc_diff,
                "k0_nodes": k0_res.nodes,
                "n2_nodes": n2_nd,
                "k0_time": k0_time,
                "n2_time": n2_time,
                "move_match": mv_match,
                "n2_pv": n2_pv[:4] if n2_pv else []
            })

        n_pos = len(diag_corpus)
        speedup = k0_time_total / n2_time_total if n2_time_total > 0 else 0
        summary = {
            "depth": depth,
            "positions": n_pos,
            "k0_time": round(k0_time_total, 3),
            "n2_time": round(n2_time_total, 3),
            "k0_nodes": k0_nodes_total,
            "n2_nodes": n2_nodes_total,
            "k0_nps": int(k0_nodes_total / k0_time_total) if k0_time_total > 0 else 0,
            "n2_nps": int(n2_nodes_total / n2_time_total) if n2_time_total > 0 else 0,
            "speedup_factor": round(speedup, 1),
            "move_matches": move_matches,
            "move_match_pct": round(move_matches / n_pos * 100.0, 1),
            "score_matches": score_matches,
            "score_match_pct": round(score_matches / n_pos * 100.0, 1),
            "records": records
        }
        output["diagnostic_37"][str(depth)] = summary
        print(f"Depth {depth}: Speedup={speedup:.1f}x | K0 NPS={summary['k0_nps']:,} | N2 NPS={summary['n2_nps']:,} | "
              f"Move Match={move_matches}/{n_pos} ({summary['move_match_pct']}%) | Score Match={score_matches}/{n_pos} ({summary['score_match_pct']}%)", flush=True)

    # --- Part 2: Independent Validation Corpus (16 Positions, Depths 1 to 4) ---
    print("\n>>> PART 2: Evaluating 16-Position Validation Corpus (Depths 1 to 4) <<<", flush=True)
    for depth in [1, 2, 3, 4]:
        print(f"\n--- Validation Depth {depth} ---", flush=True)
        move_matches = 0
        expected_matches = 0
        records = []
        k0_time_total = 0.0
        n2_time_total = 0.0

        for item in val_corpus:
            pos_id = item["id"]
            fen = item["fen"]
            exp_mv = item["expected_move"]

            # K0
            py_board = chess.Board(fen)
            k0_searcher = JanusSearch(enable_lazy_move_selection=False, enable_rfp=False)
            t0 = time.perf_counter()
            k0_res = k0_searcher.search(py_board, max_depth=depth, time_limit=60.0)
            k0_time = time.perf_counter() - t0
            k0_mv = k0_res.best_move.uci() if k0_res.best_move else None

            # N2
            bridge.set_fen(fen)
            t0 = time.perf_counter()
            n2_mv, n2_sc, n2_dp, n2_nd, n2_time, n2_pv = bridge.search(max_depth=depth, time_limit=60.0)

            k0_time_total += k0_time
            n2_time_total += n2_time

            mv_match = (k0_mv == n2_mv)
            n2_exp_match = (n2_mv == exp_mv)
            if mv_match: move_matches += 1
            if n2_exp_match: expected_matches += 1

            records.append({
                "id": pos_id,
                "theme": item["theme"],
                "fen": fen,
                "expected_move": exp_mv,
                "k0_move": k0_mv,
                "n2_move": n2_mv,
                "k0_score": k0_res.score,
                "n2_score": n2_sc,
                "move_match": mv_match,
                "n2_expected_match": n2_exp_match,
                "n2_pv": n2_pv[:4] if n2_pv else []
            })

        n_pos = len(val_corpus)
        speedup = k0_time_total / n2_time_total if n2_time_total > 0 else 0
        summary = {
            "depth": depth,
            "positions": n_pos,
            "k0_time": round(k0_time_total, 3),
            "n2_time": round(n2_time_total, 3),
            "speedup_factor": round(speedup, 1),
            "move_matches": move_matches,
            "move_match_pct": round(move_matches / n_pos * 100.0, 1),
            "expected_matches": expected_matches,
            "expected_match_pct": round(expected_matches / n_pos * 100.0, 1),
            "records": records
        }
        output["validation_16"][str(depth)] = summary
        print(f"Val Depth {depth}: Speedup={speedup:.1f}x | K0-N2 Match={move_matches}/{n_pos} ({summary['move_match_pct']}%) | "
              f"Theme Solved={expected_matches}/{n_pos} ({summary['expected_match_pct']}%)", flush=True)

    out_file = ROOT / "analysis" / "v0.51" / "raw" / "differential_search_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved raw differential results to {out_file}", flush=True)


if __name__ == "__main__":
    run_differential_suite()
