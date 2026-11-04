"""Project Janus v0.53 - Fixed-Time Ladder Benchmark.

Evaluates N3 (production baseline, UsePVS=false, UseLMR=true) vs
          N4 (candidate, UsePVS=true, UseLMR=true)
across 7 Time Tiers: [50ms, 100ms, 250ms, 500ms, 1000ms, 2000ms, 3000ms]
Corpus: 16-position validation corpus (validation_corpus.json)
Ground Truth: Stockfish 19 x64 AVX2 (E:/ChessXML/tools/stockfish/stockfish.exe)

Metrics per tier:
- Completed nominal depth (mean, median, middlegame mean, endgame mean)
- Total nodes searched & effective NPS
- Actual search duration & clock overshoot (actual - allocated)
- Stockfish 19 move agreement percentage
- Head-to-head N3 vs N4 move agreement percentage
- PVS telemetry: full-window, null-window, re-searches, cutoffs, re-search rate
- LMR telemetry: reduced moves, re-searches, cutoffs, re-search rate
"""

import json
import time
import sys
import statistics
import subprocess
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.53" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v53", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.53" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.53" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

STOCKFISH_PATH = Path("E:/ChessXML/tools/stockfish/stockfish.exe")


def get_stockfish_move(fen: str, movetime_ms: int = 300) -> str:
    """Queries Stockfish 19 for the reference move."""
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

    print(f"Loaded {len(corpus)} validation positions.")
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
        n3_depths = []
        n4_depths = []
        n3_depths_mid = []
        n4_depths_mid = []
        n3_depths_end = []
        n4_depths_end = []

        n3_nodes_tot = 0
        n4_nodes_tot = 0
        n3_time_tot = 0.0
        n4_time_tot = 0.0
        n3_overshoots = []
        n4_overshoots = []

        n3_sf_agreed = 0
        n4_sf_agreed = 0
        head_to_head_agreed = 0

        tot_pvs_full = 0
        tot_pvs_null = 0
        tot_pvs_researches = 0
        tot_pvs_cutoffs = 0

        tot_lmr_reduced = 0
        tot_lmr_researches = 0
        tot_lmr_cutoffs = 0

        for entry in corpus:
            pos_id = entry["id"]
            fen = entry["fen"]
            sf_mv = sf_moves.get(pos_id, "")
            is_endgame = (pos_id in ["val_15", "val_16"])

            # 1. Search N3 (UsePVS=False, UseLMR=True)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(False)
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv_n3, sc_n3, dp_n3, nd_n3, el_n3, pv_n3 = bridge.search(max_depth=64, time_limit=t_alloc)
            t_n3 = time.perf_counter() - t0
            ov_n3 = max(0.0, (t_n3 - t_alloc) * 1000.0)

            # 2. Search N4 (UsePVS=True, UseLMR=True)
            bridge.clear_tt()
            bridge.reset_history()
            bridge.reset_pvs_telemetry()
            bridge.reset_lmr_telemetry()
            bridge.set_pvs_options(True)
            bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
            bridge.set_fen(fen)

            t0 = time.perf_counter()
            mv_n4, sc_n4, dp_n4, nd_n4, el_n4, pv_n4 = bridge.search(max_depth=64, time_limit=t_alloc)
            t_n4 = time.perf_counter() - t0
            ov_n4 = max(0.0, (t_n4 - t_alloc) * 1000.0)

            pvs_telem_n4 = bridge.get_pvs_telemetry()
            lmr_telem_n4 = bridge.get_lmr_telemetry()

            n3_depths.append(dp_n3)
            n4_depths.append(dp_n4)
            if is_endgame:
                n3_depths_end.append(dp_n3)
                n4_depths_end.append(dp_n4)
            else:
                n3_depths_mid.append(dp_n3)
                n4_depths_mid.append(dp_n4)

            n3_nodes_tot += nd_n3
            n4_nodes_tot += nd_n4
            n3_time_tot += t_n3
            n4_time_tot += t_n4
            n3_overshoots.append(ov_n3)
            n4_overshoots.append(ov_n4)

            tot_pvs_full += pvs_telem_n4["full_window_searches"]
            tot_pvs_null += pvs_telem_n4["null_window_searches"]
            tot_pvs_researches += pvs_telem_n4["researches"]
            tot_pvs_cutoffs += pvs_telem_n4["cutoffs"]

            tot_lmr_reduced += lmr_telem_n4["reduced_moves"]
            tot_lmr_researches += lmr_telem_n4["researches"]
            tot_lmr_cutoffs += lmr_telem_n4["cutoffs"]

            if mv_n3 == sf_mv:
                n3_sf_agreed += 1
            if mv_n4 == sf_mv:
                n4_sf_agreed += 1
            if mv_n3 == mv_n4:
                head_to_head_agreed += 1

            tier_positions.append({
                "id": pos_id,
                "fen": fen,
                "category": "endgame" if is_endgame else "middlegame",
                "stockfish_move": sf_mv,
                "n3_move": mv_n3,
                "n3_depth": dp_n3,
                "n3_nodes": nd_n3,
                "n3_time_sec": t_n3,
                "n3_overshoot_ms": ov_n3,
                "n4_move": mv_n4,
                "n4_depth": dp_n4,
                "n4_nodes": nd_n4,
                "n4_time_sec": t_n4,
                "n4_overshoot_ms": ov_n4,
                "depth_gain": dp_n4 - dp_n3,
                "pvs_telemetry": pvs_telem_n4,
                "lmr_telemetry": lmr_telem_n4,
            })

        n_pos = len(corpus)
        mean_dp_n3 = statistics.mean(n3_depths)
        mean_dp_n4 = statistics.mean(n4_depths)
        med_dp_n3 = statistics.median(n3_depths)
        med_dp_n4 = statistics.median(n4_depths)

        mid_mean_dp_n3 = statistics.mean(n3_depths_mid) if n3_depths_mid else 0.0
        mid_mean_dp_n4 = statistics.mean(n4_depths_mid) if n4_depths_mid else 0.0
        end_mean_dp_n3 = statistics.mean(n3_depths_end) if n3_depths_end else 0.0
        end_mean_dp_n4 = statistics.mean(n4_depths_end) if n4_depths_end else 0.0

        max_ov_n3 = max(n3_overshoots)
        max_ov_n4 = max(n4_overshoots)
        avg_ov_n3 = statistics.mean(n3_overshoots)
        avg_ov_n4 = statistics.mean(n4_overshoots)

        sf_agr_n3_pct = (n3_sf_agreed / n_pos) * 100.0
        sf_agr_n4_pct = (n4_sf_agreed / n_pos) * 100.0
        h2h_agr_pct = (head_to_head_agreed / n_pos) * 100.0

        pvs_res_rate = (tot_pvs_researches / tot_pvs_null * 100.0) if tot_pvs_null > 0 else 0.0
        lmr_res_rate = (tot_lmr_researches / tot_lmr_reduced * 100.0) if tot_lmr_reduced > 0 else 0.0

        node_delta_pct = ((n4_nodes_tot - n3_nodes_tot) / n3_nodes_tot * 100.0) if n3_nodes_tot > 0 else 0.0

        summary = {
            "tier_allocated_sec": t_alloc,
            "tier_allocated_ms": tier_ms,
            "positions_count": n_pos,
            "mean_depth_n3": mean_dp_n3,
            "mean_depth_n4": mean_dp_n4,
            "median_depth_n3": med_dp_n3,
            "median_depth_n4": med_dp_n4,
            "middlegame_mean_depth_n3": mid_mean_dp_n3,
            "middlegame_mean_depth_n4": mid_mean_dp_n4,
            "endgame_mean_depth_n3": end_mean_dp_n3,
            "endgame_mean_depth_n4": end_mean_dp_n4,
            "depth_gain_mean": mean_dp_n4 - mean_dp_n3,
            "depth_gain_middlegame": mid_mean_dp_n4 - mid_mean_dp_n3,
            "total_nodes_n3": n3_nodes_tot,
            "total_nodes_n4": n4_nodes_tot,
            "node_delta_pct": node_delta_pct,
            "mean_overshoot_n3_ms": avg_ov_n3,
            "mean_overshoot_n4_ms": avg_ov_n4,
            "max_overshoot_n3_ms": max_ov_n3,
            "max_overshoot_n4_ms": max_ov_n4,
            "stockfish_agreement_n3_pct": sf_agr_n3_pct,
            "stockfish_agreement_n4_pct": sf_agr_n4_pct,
            "head_to_head_agreement_pct": h2h_agr_pct,
            "pvs_full_window_searches": tot_pvs_full,
            "pvs_null_window_searches": tot_pvs_null,
            "pvs_researches": tot_pvs_researches,
            "pvs_research_rate_pct": pvs_res_rate,
            "lmr_reduced_moves": tot_lmr_reduced,
            "lmr_researches": tot_lmr_researches,
            "lmr_research_rate_pct": lmr_res_rate,
        }

        ladder_results[str(tier_ms)] = {
            "summary": summary,
            "positions": tier_positions,
        }

        print(f"Tier {tier_ms} ms Summary:")
        print(f"  Mean Depth: N3={mean_dp_n3:.2f} (Mid: {mid_mean_dp_n3:.2f}) vs N4={mean_dp_n4:.2f} (Mid: {mid_mean_dp_n4:.2f}) | Gain: {mean_dp_n4 - mean_dp_n3:+.2f}")
        print(f"  Median Depth: N3={med_dp_n3:.1f} vs N4={med_dp_n4:.1f}")
        print(f"  Nodes: N3={n3_nodes_tot:,} vs N4={n4_nodes_tot:,} ({node_delta_pct:+.2f}%)")
        print(f"  Max Overshoot: N3={max_ov_n3:.1f}ms vs N4={max_ov_n4:.1f}ms")
        print(f"  Stockfish Agreement: N3={sf_agr_n3_pct:.1f}% vs N4={sf_agr_n4_pct:.1f}%")
        print(f"  Head-to-Head Agreement: {h2h_agr_pct:.1f}%")
        print(f"  PVS Null Windows: {tot_pvs_null:,}, Re-searches: {tot_pvs_researches:,} ({pvs_res_rate:.2f}%)\n")

    out_file = RAW_DIR / "fixed_time_ladder_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ladder_results, f, indent=2)

    print(f"Saved complete fixed-time ladder benchmark data to {out_file}")
    return ladder_results


if __name__ == "__main__":
    run_fixed_time_ladder()

