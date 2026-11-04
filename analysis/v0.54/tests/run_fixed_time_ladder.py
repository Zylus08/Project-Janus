"""Project Janus v0.54 - Fixed-Time Ladder Benchmark.

Evaluates 4 configurations (C0, C1, C2, C3) across:
7 Time Tiers: [50ms, 100ms, 250ms, 500ms, 1000ms, 2000ms, 3000ms]
Corpus: 16-position validation corpus (validation_corpus.json)
Ground Truth: Stockfish 19 x64 AVX2 (E:/ChessXML/tools/stockfish/stockfish.exe)

Metrics per tier:
- Completed nominal depth (mean, median, middlegame mean, endgame mean)
- Total nodes searched & effective NPS
- Actual search duration & clock overshoot (actual - allocated)
- Stockfish 19 move agreement percentage
- Head-to-head C3 vs C0 move agreement percentage
- Move ordering telemetry: total cutoffs, first-move cutoff rate, mean cutoff index
- Killer cutoffs & history cutoffs
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
BRIDGE_PATH = ROOT / "analysis" / "v0.54" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v54", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.54" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.54" / "raw"
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

    configs = [
        ("c0", False, False),
        ("c1", True, False),
        ("c2", False, True),
        ("c3", True, True),
    ]

    ladder_results = {}

    for t_alloc in tiers_sec:
        tier_ms = int(t_alloc * 1000)
        print(f"--- Running Time Tier {tier_ms} ms ---")

        tier_positions = []
        depths = {cfg[0]: [] for cfg in configs}
        depths_mid = {cfg[0]: [] for cfg in configs}
        depths_end = {cfg[0]: [] for cfg in configs}

        tot_nodes = {cfg[0]: 0 for cfg in configs}
        tot_time = {cfg[0]: 0.0 for cfg in configs}
        overshoots = {cfg[0]: [] for cfg in configs}
        sf_agreed = {cfg[0]: 0 for cfg in configs}
        agreed_vs_c0 = {cfg[0]: 0 for cfg in configs}

        ordering_telem_totals = {
            cfg[0]: {
                "total_cutoffs": 0, "cutoff_move_1": 0, "cutoff_move_2": 0,
                "cutoff_move_3": 0, "cutoff_move_4plus": 0, "cutoff_tt": 0,
                "cutoff_killer1": 0, "cutoff_killer2": 0, "cutoff_history": 0,
                "cutoff_captures": 0, "cutoff_quiet": 0, "sum_cutoff_index": 0
            }
            for cfg in configs
        }

        lmr_totals = {
            cfg[0]: {"reduced_moves": 0, "researches": 0, "cutoffs": 0}
            for cfg in configs
        }

        for entry in corpus:
            pos_id = entry["id"]
            fen = entry["fen"]
            sf_mv = sf_moves.get(pos_id, "")
            is_endgame = (pos_id in ["val_15", "val_16"])

            pos_data = {
                "id": pos_id, "fen": fen,
                "category": "endgame" if is_endgame else "middlegame",
                "stockfish_move": sf_mv,
                "configs": {}
            }

            c0_mv = None

            for cfg_id, use_k, use_h in configs:
                bridge.clear_tt()
                bridge.clear_killers()
                bridge.clear_history_heuristic()
                bridge.reset_history()
                bridge.reset_ordering_telemetry()
                bridge.reset_lmr_telemetry()
                bridge.reset_pvs_telemetry()
                bridge.set_pvs_options(False)
                bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)
                bridge.set_ordering_options(use_k, use_h)
                bridge.set_fen(fen)

                t0 = time.perf_counter()
                mv, sc, dp, nd, el, pv = bridge.search(max_depth=64, time_limit=t_alloc)
                elapsed = time.perf_counter() - t0
                ov = max(0.0, (elapsed - t_alloc) * 1000.0)

                ord_telem = bridge.get_ordering_telemetry()
                lmr_telem = bridge.get_lmr_telemetry()

                if cfg_id == "c0":
                    c0_mv = mv

                if mv == sf_mv:
                    sf_agreed[cfg_id] += 1
                if mv == c0_mv:
                    agreed_vs_c0[cfg_id] += 1

                depths[cfg_id].append(dp)
                if is_endgame:
                    depths_end[cfg_id].append(dp)
                else:
                    depths_mid[cfg_id].append(dp)

                tot_nodes[cfg_id] += nd
                tot_time[cfg_id] += elapsed
                overshoots[cfg_id].append(ov)

                for k in ["total_cutoffs", "cutoff_move_1", "cutoff_move_2", "cutoff_move_3",
                          "cutoff_move_4plus", "cutoff_tt", "cutoff_killer1", "cutoff_killer2",
                          "cutoff_history", "cutoff_captures", "cutoff_quiet"]:
                    ordering_telem_totals[cfg_id][k] += ord_telem.get(k, 0)
                ordering_telem_totals[cfg_id]["sum_cutoff_index"] += int(ord_telem.get("mean_cutoff_index", 0.0) * ord_telem.get("total_cutoffs", 0))

                for k in ["reduced_moves", "researches", "cutoffs"]:
                    lmr_totals[cfg_id][k] += lmr_telem[k]

                pos_data["configs"][cfg_id] = {
                    "move": mv, "depth": dp, "score": sc, "nodes": nd,
                    "time_sec": elapsed, "overshoot_ms": ov,
                    "telemetry": ord_telem, "lmr_telemetry": lmr_telem
                }

            tier_positions.append(pos_data)

        n_pos = len(corpus)

        # Summaries per configuration
        summary = {
            "tier_allocated_sec": t_alloc,
            "tier_allocated_ms": tier_ms,
            "positions_count": n_pos,
            "configs": {}
        }

        for cfg_id, use_k, use_h in configs:
            m_dp = statistics.mean(depths[cfg_id])
            med_dp = statistics.median(depths[cfg_id])
            mid_dp = statistics.mean(depths_mid[cfg_id]) if depths_mid[cfg_id] else 0.0
            end_dp = statistics.mean(depths_end[cfg_id]) if depths_end[cfg_id] else 0.0
            avg_ov = statistics.mean(overshoots[cfg_id])
            max_ov = max(overshoots[cfg_id])
            sf_pct = (sf_agreed[cfg_id] / n_pos) * 100.0
            agr_c0_pct = (agreed_vs_c0[cfg_id] / n_pos) * 100.0

            tot_cut = ordering_telem_totals[cfg_id]["total_cutoffs"]
            sum_idx = ordering_telem_totals[cfg_id]["sum_cutoff_index"]
            cut_1 = ordering_telem_totals[cfg_id]["cutoff_move_1"]
            first_rate = (cut_1 / tot_cut * 100.0) if tot_cut > 0 else 0.0
            mean_idx = (sum_idx / tot_cut) if tot_cut > 0 else 0.0

            red = lmr_totals[cfg_id]["reduced_moves"]
            res = lmr_totals[cfg_id]["researches"]
            res_rate = (res / red * 100.0) if red > 0 else 0.0

            summary["configs"][cfg_id] = {
                "mean_depth": m_dp,
                "median_depth": med_dp,
                "middlegame_mean_depth": mid_dp,
                "endgame_mean_depth": end_dp,
                "total_nodes": tot_nodes[cfg_id],
                "mean_overshoot_ms": avg_ov,
                "max_overshoot_ms": max_ov,
                "stockfish_agreement_pct": sf_pct,
                "agreement_vs_c0_pct": agr_c0_pct,
                "first_move_cutoff_rate_pct": first_rate,
                "mean_cutoff_index": mean_idx,
                "lmr_reduced_moves": red,
                "lmr_researches": res,
                "lmr_research_rate_pct": res_rate,
                "ordering_telemetry": ordering_telem_totals[cfg_id],
            }

        ladder_results[str(tier_ms)] = {
            "summary": summary,
            "positions": tier_positions,
        }

        c0_s = summary["configs"]["c0"]
        c3_s = summary["configs"]["c3"]
        print(f"Tier {tier_ms} ms Summary:")
        print(f"  Mean Depth: C0={c0_s['mean_depth']:.2f} (Mid: {c0_s['middlegame_mean_depth']:.2f}) vs C3={c3_s['mean_depth']:.2f} (Mid: {c3_s['middlegame_mean_depth']:.2f}) | Gain: {c3_s['mean_depth'] - c0_s['mean_depth']:+.2f}")
        print(f"  Median Depth: C0={c0_s['median_depth']:.1f} vs C3={c3_s['median_depth']:.1f}")
        print(f"  Nodes: C0={c0_s['total_nodes']:,} vs C3={c3_s['total_nodes']:,} (Delta: {((c3_s['total_nodes'] - c0_s['total_nodes'])/c0_s['total_nodes']*100):+.2f}%)")
        print(f"  1st Move Cutoffs: C0={c0_s['first_move_cutoff_rate_pct']:.1f}% vs C3={c3_s['first_move_cutoff_rate_pct']:.1f}%")
        print(f"  Move Agreement C3 vs C0: {c3_s['agreement_vs_c0_pct']:.1f}% | Stockfish Agree: C0={c0_s['stockfish_agreement_pct']:.1f}% vs C3={c3_s['stockfish_agreement_pct']:.1f}%\n")

    out_file = RAW_DIR / "fixed_time_ladder_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ladder_results, f, indent=2)

    print(f"Saved complete fixed-time ladder benchmark data to {out_file}")
    return ladder_results


if __name__ == "__main__":
    run_fixed_time_ladder()

