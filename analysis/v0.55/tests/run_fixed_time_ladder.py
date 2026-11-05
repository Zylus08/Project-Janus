"""Project Janus v0.55 - Fixed-Time Factorial Ladder Benchmark.

Evaluates 4 configurations (F00, F01, F10, F11) across:
7 Time Tiers: [50ms, 100ms, 250ms, 500ms, 1000ms, 2000ms, 3000ms]
Corpus: 16-position validation corpus (validation_corpus.json)
Reference Oracle: Stockfish 19 x64 AVX2 (E:/ChessXML/tools/stockfish/stockfish.exe)

Metrics per tier:
- Completed depth (mean, median, middlegame mean, endgame mean)
- Total nodes searched & effective NPS
- Search duration & clock overshoot
- Stockfish 19 move agreement percentage
- Head-to-head F11 vs F10 move agreement percentage
- Ordering telemetry: cutoffs, first-move cutoff rate, mean cutoff index
- PVS telemetry: null-window searches, re-searches, re-search rate
- LMR telemetry: reduced moves, re-searches, re-search rate
"""

import json
import time
import sys
import statistics
import subprocess
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.55" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v55", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.55" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.55" / "raw"
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
                tokens = line.split()
                if len(tokens) >= 2:
                    return tokens[1]
    except Exception as e:
        print(f"Warning: Stockfish query failed for {fen}: {e}")
    return ""


def run_ladder(tiers=(50, 100, 250, 500, 1000, 2000, 3000)):
    with open(CORPUS_DIR / "validation_corpus.json", "r", encoding="utf-8") as f:
        positions = json.load(f)
    print(f"Loaded {len(positions)} positions from validation corpus.")

    # Pre-cache Stockfish moves
    print("Pre-fetching Stockfish 19 ground truth moves...")
    sf_moves = {}
    for p in positions:
        sf_moves[p["id"]] = get_stockfish_move(p["fen"], movetime_ms=300)
    print("Stockfish pre-fetch complete.")

    bridge = NativeEngineBridge()

    configs = {
        "f00": {"killer": False, "history": False, "pvs": False, "name": "N3 (K=0, H=0, PVS=0)"},
        "f01": {"killer": False, "history": False, "pvs": True,  "name": "N4 (K=0, H=0, PVS=1)"},
        "f10": {"killer": True,  "history": True,  "pvs": False, "name": "N5 (K=1, H=1, PVS=0)"},
        "f11": {"killer": True,  "history": True,  "pvs": True,  "name": "N6 (K=1, H=1, PVS=1)"},
    }

    all_results = {}

    for t_ms in tiers:
        t_sec = t_ms / 1000.0
        print(f"\n==========================================")
        print(f"Evaluating Fixed-Time Tier: {t_ms} ms ({t_sec}s)...")
        print(f"==========================================")

        tier_records = []
        cfg_metrics = {
            c: {
                "depths": [],
                "nodes": [],
                "overshoots_ms": [],
                "sf_matches": 0,
                "f10_matches": 0,
                "cutoffs": 0,
                "first_cutoffs": 0,
                "sum_cutoff_index": 0,
                "pvs_null": 0,
                "pvs_research": 0,
                "lmr_reduced": 0,
                "lmr_research": 0,
            }
            for c in configs
        }

        for idx, pos in enumerate(positions):
            pos_id = pos["id"]
            fen = pos["fen"]
            is_endgame = "endgame" in pos_id.lower() or "kp" in pos_id.lower() or ("category" in pos and "endgame" in pos["category"].lower())
            sf_bm = sf_moves.get(pos_id, "")

            pos_entry = {
                "id": pos_id,
                "fen": fen,
                "is_endgame": is_endgame,
                "sf_reference_move": sf_bm,
                "configs": {}
            }

            f10_move = None

            # First run F10 to get reference move for agreement
            for c_name in ["f10", "f00", "f01", "f11"]:
                c_cfg = configs[c_name]

                bridge.clear_tt()
                bridge.clear_killers()
                bridge.clear_history_heuristic()
                bridge.reset_history()
                bridge.reset_ordering_telemetry()
                bridge.reset_pvs_telemetry()
                bridge.reset_lmr_telemetry()

                bridge.set_ordering_options(c_cfg["killer"], c_cfg["history"])
                bridge.set_pvs_options(c_cfg["pvs"])
                bridge.set_lmr_options(True)

                bridge.set_fen(fen)

                t0 = time.perf_counter()
                best_move, score_cp, depth_reached, nodes, elapsed_sec, pv = bridge.search(max_depth=64, time_limit=t_sec)
                t1 = time.perf_counter()

                actual_ms = (t1 - t0) * 1000.0
                overshoot_ms = actual_ms - t_ms

                ord_telem = bridge.get_ordering_telemetry()
                pvs_telem = bridge.get_pvs_telemetry()
                lmr_telem = bridge.get_lmr_telemetry()

                if c_name == "f10":
                    f10_move = best_move

                pos_entry["configs"][c_name] = {
                    "best_move": best_move,
                    "score_cp": score_cp,
                    "depth_reached": depth_reached,
                    "nodes": nodes,
                    "actual_ms": actual_ms,
                    "overshoot_ms": overshoot_ms,
                    "pv": pv,
                    "ordering_telemetry": ord_telem,
                    "pvs_telemetry": pvs_telem,
                    "lmr_telemetry": lmr_telem,
                }

                # Accumulate
                cfg_metrics[c_name]["depths"].append(depth_reached)
                cfg_metrics[c_name]["nodes"].append(nodes)
                cfg_metrics[c_name]["overshoots_ms"].append(overshoot_ms)
                if best_move == sf_bm and sf_bm != "":
                    cfg_metrics[c_name]["sf_matches"] += 1
                if f10_move is not None and best_move == f10_move:
                    cfg_metrics[c_name]["f10_matches"] += 1

                cfg_metrics[c_name]["cutoffs"] += ord_telem.get("total_cutoffs", 0)
                cfg_metrics[c_name]["first_cutoffs"] += ord_telem.get("cutoff_move_1", 0)
                cfg_metrics[c_name]["sum_cutoff_index"] += ord_telem.get("sum_cutoff_index", 0)

                cfg_metrics[c_name]["pvs_null"] += pvs_telem.get("null_window_searches", 0)
                cfg_metrics[c_name]["pvs_research"] += pvs_telem.get("researches", 0)

                cfg_metrics[c_name]["lmr_reduced"] += lmr_telem.get("reduced_moves", 0)
                cfg_metrics[c_name]["lmr_research"] += lmr_telem.get("researches", 0)

            tier_records.append(pos_entry)

        # Summary for tier
        tier_summary = {
            "tier_allocated_ms": t_ms,
            "positions_count": len(positions),
            "configs": {}
        }

        for c in configs:
            d_list = cfg_metrics[c]["depths"]
            n_list = cfg_metrics[c]["nodes"]
            ov_list = cfg_metrics[c]["overshoots_ms"]
            tc = cfg_metrics[c]["cutoffs"]
            fc = cfg_metrics[c]["first_cutoffs"]
            pvs_null = cfg_metrics[c]["pvs_null"]
            pvs_res = cfg_metrics[c]["pvs_research"]
            lmr_red = cfg_metrics[c]["lmr_reduced"]
            lmr_res = cfg_metrics[c]["lmr_research"]

            tier_summary["configs"][c] = {
                "mean_depth": statistics.mean(d_list),
                "median_depth": statistics.median(d_list),
                "total_nodes": sum(n_list),
                "mean_overshoot_ms": statistics.mean(ov_list),
                "max_overshoot_ms": max(ov_list),
                "stockfish_agreement_pct": cfg_metrics[c]["sf_matches"] / len(positions) * 100,
                "agreement_vs_f10_pct": cfg_metrics[c]["f10_matches"] / len(positions) * 100,
                "first_move_cutoff_rate_pct": (fc / tc * 100) if tc > 0 else 0,
                "mean_cutoff_index": (cfg_metrics[c]["sum_cutoff_index"] / tc) if tc > 0 else 0,
                "pvs_null_searches": pvs_null,
                "pvs_researches": pvs_res,
                "pvs_research_rate_pct": (pvs_res / pvs_null * 100) if pvs_null > 0 else 0,
                "lmr_reduced_moves": lmr_red,
                "lmr_researches": lmr_res,
                "lmr_research_rate_pct": (lmr_res / lmr_red * 100) if lmr_red > 0 else 0,
            }

        print(f"\n--- Tier {t_ms}ms Summary ---")
        for c in configs:
            sc = tier_summary["configs"][c]
            print(f"  {c.upper()} ({configs[c]['name']}): med_depth={sc['median_depth']:.1f}, mean_depth={sc['mean_depth']:.2f}, nodes={sc['total_nodes']:,}, 1st-cut={sc['first_move_cutoff_rate_pct']:.1f}%, sf_agree={sc['stockfish_agreement_pct']:.1f}%, vs_f10={sc['agreement_vs_f10_pct']:.1f}%")

        all_results[str(t_ms)] = {
            "summary": tier_summary,
            "positions": tier_records
        }

    out_file = RAW_DIR / "fixed_time_ladder_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved full fixed-time ladder telemetry to {out_file}")


if __name__ == "__main__":
    run_ladder()

