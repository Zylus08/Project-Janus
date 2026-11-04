"""Project Janus v0.52 - Fixed-Time Ladder Benchmark.

Evaluates N2 (control, UseLMR=false) vs N3 (candidate, UseLMR=true) across:
7 Time Tiers: [50ms, 100ms, 250ms, 500ms, 1000ms, 2000ms, 3000ms]
Corpus: 16-position validation corpus (validation_corpus.json)
Ground Truth: Stockfish 19 x64 AVX2 (E:/ChessXML/tools/stockfish/stockfish.exe)

Metrics per tier:
- Completed nominal depth (mean & max)
- Total nodes searched & effective NPS
- Actual search duration & clock overshoot (actual - allocated)
- Stockfish 19 move agreement percentage
- Head-to-head N2 vs N3 move agreement percentage
- LMR telemetry: reduced moves, re-searches, re-search rate, beta cutoffs
"""

import json
import time
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "v0.52" / "native"))

from janus_native_bridge import NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.52" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.52" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

STOCKFISH_PATH = Path("E:/ChessXML/tools/stockfish/stockfish.exe")


def get_stockfish_move(fen: str, movetime_ms: int = 200) -> str:
    """Queries Stockfish 19 for the ground-truth reference move."""
    try:
        p = subprocess.Popen(
            [str(STOCKFISH_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cmds = [
            "uci",
            "isready",
            f"position fen {fen}",
            f"go movetime {movetime_ms}",
            "quit",
        ]
        out, _ = p.communicate("\n".join(cmds) + "\n", timeout=5)
        for line in out.splitlines():
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
    except Exception as e:
        print(f"Stockfish query failed: {e}")
    return ""


def run_fixed_time_ladder():
    with open(CORPUS_DIR / "validation_corpus.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)

    tiers_sec = [0.05, 0.10, 0.25, 0.50, 1.0, 2.0, 3.0]
    bridge = NativeEngineBridge()

    # Pre-compute Stockfish reference moves for the 16 positions
    print("Pre-computing Stockfish 19 reference moves...")
    sf_moves = {}
    for entry in corpus:
        fen = entry["fen"]
        sf_moves[entry["id"]] = get_stockfish_move(fen, movetime_ms=300)
    print("Stockfish 19 moves computed.\n")

    ladder_results = {}

    for t_alloc in tiers_sec:
        tier_ms = int(t_alloc * 1000)
        print(f"--- Running Time Tier {tier_ms} ms ---")

        tier_positions = []
        n2_depths = []
        n3_depths = []
        n2_nodes_tot = 0
        n3_nodes_tot = 0
        n2_time_tot = 0.0
        n3_time_tot = 0.0
        n2_overshoots = []
        n3_overshoots = []

        n2_sf_agreed = 0
        n3_sf_agreed = 0
        head_to_head_agreed = 0

        tot_reduced = 0
        tot_researches = 0
        tot_cutoffs = 0

        for entry in corpus:
            pos_id = entry["id"]
            fen = entry["fen"]
            sf_mv = sf_moves.get(pos_id, "")

            # 1. Search N2 (UseLMR=false)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_lmr_telemetry()
            bridge.set_lmr_options(False)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv_n2, sc_n2, dp_n2, nd_n2, el_n2, pv_n2 = bridge.search(max_depth=64, time_limit=t_alloc)
            t_n2 = time.perf_counter() - t0
            ov_n2 = max(0.0, (t_n2 - t_alloc) * 1000.0)

            # 2. Search N3 (UseLMR=true)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_lmr_telemetry()
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv_n3, sc_n3, dp_n3, nd_n3, el_n3, pv_n3 = bridge.search(max_depth=64, time_limit=t_alloc)
            t_n3 = time.perf_counter() - t0
            ov_n3 = max(0.0, (t_n3 - t_alloc) * 1000.0)
            telem_n3 = bridge.get_lmr_telemetry()

            n2_depths.append(dp_n2)
            n3_depths.append(dp_n3)
            n2_nodes_tot += nd_n2
            n3_nodes_tot += nd_n3
            n2_time_tot += t_n2
            n3_time_tot += t_n3
            n2_overshoots.append(ov_n2)
            n3_overshoots.append(ov_n3)

            tot_reduced += telem_n3["reduced_moves"]
            tot_researches += telem_n3["researches"]
            tot_cutoffs += telem_n3["cutoffs"]

            if mv_n2 == sf_mv:
                n2_sf_agreed += 1
            if mv_n3 == sf_mv:
                n3_sf_agreed += 1
            if mv_n2 == mv_n3:
                head_to_head_agreed += 1

            tier_positions.append({
                "id": pos_id,
                "fen": fen,
                "stockfish_move": sf_mv,
                "n2_move": mv_n2,
                "n2_depth": dp_n2,
                "n2_nodes": nd_n2,
                "n2_time_sec": t_n2,
                "n2_overshoot_ms": ov_n2,
                "n3_move": mv_n3,
                "n3_depth": dp_n3,
                "n3_nodes": nd_n3,
                "n3_time_sec": t_n3,
                "n3_overshoot_ms": ov_n3,
                "depth_gain": dp_n3 - dp_n2,
                "telemetry": telem_n3,
            })

        n_pos = len(corpus)
        avg_dp_n2 = sum(n2_depths) / n_pos
        avg_dp_n3 = sum(n3_depths) / n_pos
        depth_gain = avg_dp_n3 - avg_dp_n2
        max_ov_n2 = max(n2_overshoots)
        max_ov_n3 = max(n3_overshoots)
        avg_ov_n2 = sum(n2_overshoots) / n_pos
        avg_ov_n3 = sum(n3_overshoots) / n_pos

        sf_agr_n2_pct = (n2_sf_agreed / n_pos) * 100.0
        sf_agr_n3_pct = (n3_sf_agreed / n_pos) * 100.0
        h2h_agr_pct = (head_to_head_agreed / n_pos) * 100.0
        res_rate = (tot_researches / tot_reduced * 100.0) if tot_reduced > 0 else 0.0

        summary = {
            "tier_allocated_sec": t_alloc,
            "tier_allocated_ms": tier_ms,
            "positions_count": n_pos,
            "mean_depth_n2": avg_dp_n2,
            "mean_depth_n3": avg_dp_n3,
            "depth_gain": depth_gain,
            "total_nodes_n2": n2_nodes_tot,
            "total_nodes_n3": n3_nodes_tot,
            "mean_overshoot_n2_ms": avg_ov_n2,
            "mean_overshoot_n3_ms": avg_ov_n3,
            "max_overshoot_n2_ms": max_ov_n2,
            "max_overshoot_n3_ms": max_ov_n3,
            "stockfish_agreement_n2_pct": sf_agr_n2_pct,
            "stockfish_agreement_n3_pct": sf_agr_n3_pct,
            "head_to_head_agreement_pct": h2h_agr_pct,
            "total_reduced_moves": tot_reduced,
            "total_researches": tot_researches,
            "research_rate_pct": res_rate,
            "total_cutoffs": tot_cutoffs,
        }

        ladder_results[str(tier_ms)] = {
            "summary": summary,
            "positions": tier_positions,
        }

        print(f"Tier {tier_ms} ms Summary:")
        print(f"  Mean Completed Depth: N2={avg_dp_n2:.2f} vs N3={avg_dp_n3:.2f} (Gain: {depth_gain:+.2f} plies)")
        print(f"  Nodes: N2={n2_nodes_tot:,} vs N3={n3_nodes_tot:,}")
        print(f"  Max Overshoot: N2={max_ov_n2:.1f}ms vs N3={max_ov_n3:.1f}ms")
        print(f"  Stockfish Agreement: N2={sf_agr_n2_pct:.1f}% vs N3={sf_agr_n3_pct:.1f}%")
        print(f"  Head-to-Head Move Agreement: {h2h_agr_pct:.1f}%")
        print(f"  LMR Reduced: {tot_reduced:,}, Re-searches: {tot_researches:,} ({res_rate:.2f}%)\n")

    out_file = RAW_DIR / "fixed_time_ladder_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ladder_results, f, indent=2)

    print(f"Saved complete fixed-time ladder benchmark data to {out_file}")
    return ladder_results


if __name__ == "__main__":
    run_fixed_time_ladder()

