"""Project Janus v0.56 - Fixed-Time SEE Ladder Benchmark.

Evaluates 4 configurations (S0, S1, S2, S3) across 7 Time Tiers:
[50ms, 100ms, 250ms, 500ms, 1000ms, 2000ms, 3000ms]
Corpus: 16-position validation corpus (validation_corpus.json)
Reference Oracle: Stockfish 19 x64 AVX2 (E:/ChessXML/tools/stockfish/stockfish.exe)

Metrics per tier:
- Completed depth (mean, median)
- Total nodes searched & effective NPS
- Search duration & clock overshoot
- Stockfish 19 move agreement percentage
- Candidate S3 vs Baseline S0 move agreement percentage
- Tactical move selection differences and forensics
- Ordering telemetry: first-move cutoff rate, mean cutoff index
- SEE telemetry: evaluations, positive, neutral, negative, inversions
"""

from __future__ import annotations

import json
import time
import sys
import statistics
import subprocess
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v56", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.56" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.56" / "raw"
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
        "s0": {"see_main": False, "see_q": False, "desc": "S0: Baseline N5"},
        "s1": {"see_main": True,  "see_q": False, "desc": "S1: Main SEE Only"},
        "s2": {"see_main": False, "see_q": True,  "desc": "S2: Q-Search SEE Only"},
        "s3": {"see_main": True,  "see_q": True,  "desc": "S3: Candidate N7"},
    }

    all_results = {}

    for t_ms in tiers:
        t_sec = t_ms / 1000.0
        print(f"\n==========================================", flush=True)
        print(f"Evaluating Fixed-Time Tier: {t_ms} ms ({t_sec}s)...", flush=True)
        print(f"==========================================", flush=True)

        tier_records = []
        cfg_metrics = {
            c: {
                "depths": [],
                "nodes": [],
                "elapsed": [],
                "sf_agreements": 0,
                "s0_agreements": 0,
                "first_move_cutoffs": 0,
                "total_cutoffs": 0,
                "see_evals": 0,
                "see_pos": 0,
                "see_neu": 0,
                "see_neg": 0,
                "see_inv": 0,
            }
            for c in configs
        }

        for idx, pos in enumerate(positions):
            pos_id = pos["id"]
            fen = pos["fen"]
            sf_ref = sf_moves.get(pos_id, "")
            pos_record = {"id": pos_id, "fen": fen, "sf_move": sf_ref}

            s0_best_move = None

            for c_name, c_cfg in configs.items():
                bridge.clear_tt()
                bridge.clear_killers()
                bridge.clear_history_heuristic()
                bridge.reset_history()
                bridge.reset_ordering_telemetry()
                bridge.reset_pvs_telemetry()
                bridge.reset_lmr_telemetry()
                bridge.reset_see_telemetry()

                bridge.set_ordering_options(use_killer=True, use_history=True)
                bridge.set_pvs_options(use_pvs=False)
                bridge.set_lmr_options(use_lmr=True, min_depth=3, move_threshold=4, base_reduction=1)
                bridge.set_see_options(c_cfg["see_main"], c_cfg["see_q"])

                bridge.set_fen(fen)

                t0 = time.perf_counter()
                best_move, score_cp, depth_completed, nodes, elapsed_s, pv = bridge.search(
                    max_depth=64, time_limit=t_sec
                )
                t1 = time.perf_counter()
                actual_duration = t1 - t0

                if c_name == "s0":
                    s0_best_move = best_move

                ordering_telem = bridge.get_ordering_telemetry()
                see_telem = bridge.get_see_telemetry()

                matches_sf = (best_move == sf_ref) if sf_ref else False
                matches_s0 = (best_move == s0_best_move) if s0_best_move else True

                pos_record[c_name] = {
                    "best_move": best_move,
                    "score_cp": score_cp,
                    "depth": depth_completed,
                    "nodes": nodes,
                    "elapsed_s": actual_duration,
                    "overshoot_ms": max(0.0, (actual_duration - t_sec) * 1000.0),
                    "matches_sf": matches_sf,
                    "matches_s0": matches_s0,
                    "ordering": ordering_telem,
                    "see": see_telem,
                }

                cfg_metrics[c_name]["depths"].append(depth_completed)
                cfg_metrics[c_name]["nodes"].append(nodes)
                cfg_metrics[c_name]["elapsed"].append(actual_duration)
                if matches_sf:
                    cfg_metrics[c_name]["sf_agreements"] += 1
                if matches_s0:
                    cfg_metrics[c_name]["s0_agreements"] += 1
                cfg_metrics[c_name]["first_move_cutoffs"] += ordering_telem["cutoff_move_1"]
                cfg_metrics[c_name]["total_cutoffs"] += ordering_telem["total_cutoffs"]
                cfg_metrics[c_name]["see_evals"] += see_telem["total_evaluations"]
                cfg_metrics[c_name]["see_pos"] += see_telem["positive_captures"]
                cfg_metrics[c_name]["see_neu"] += see_telem["neutral_captures"]
                cfg_metrics[c_name]["see_neg"] += see_telem["negative_captures"]
                cfg_metrics[c_name]["see_inv"] += see_telem["ordering_inversions"]

            tier_records.append(pos_record)

        # Tier summary
        tier_summary = {}
        n_pos = len(positions)
        for c_name, m in cfg_metrics.items():
            tot_cut = m["total_cutoffs"]
            first_pct = (m["first_move_cutoffs"] / tot_cut * 100.0) if tot_cut > 0 else 0.0
            tier_summary[c_name] = {
                "mean_depth": statistics.mean(m["depths"]),
                "median_depth": statistics.median(m["depths"]),
                "total_nodes": sum(m["nodes"]),
                "mean_nodes": statistics.mean(m["nodes"]),
                "mean_elapsed_s": statistics.mean(m["elapsed"]),
                "mean_overshoot_ms": max(0.0, (statistics.mean(m["elapsed"]) - t_sec) * 1000.0),
                "sf_agreement_pct": (m["sf_agreements"] / n_pos) * 100.0,
                "s0_agreement_pct": (m["s0_agreements"] / n_pos) * 100.0,
                "first_move_cutoff_rate": first_pct,
                "see_evaluations": m["see_evals"],
                "see_positive": m["see_pos"],
                "see_neutral": m["see_neu"],
                "see_negative": m["see_neg"],
                "ordering_inversions": m["see_inv"],
            }

        print(f"--- Tier {t_ms} ms Summary ---", flush=True)
        for c_name, s in tier_summary.items():
            print(f"  {configs[c_name]['desc']}: MedDepth={s['median_depth']:.1f}, MeanDepth={s['mean_depth']:.2f}, Nodes={s['total_nodes']:,}, SF Agree={s['sf_agreement_pct']:.1f}%, S0 Agree={s['s0_agreement_pct']:.1f}%, 1stCut={s['first_move_cutoff_rate']:.1f}%", flush=True)

        all_results[f"tier_{t_ms}ms"] = {
            "time_budget_ms": t_ms,
            "summary": tier_summary,
            "positions": tier_records,
        }

    raw_path = RAW_DIR / "fixed_time_ladder_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n[OK] Saved complete raw fixed-time benchmark to {raw_path}", flush=True)
    return all_results


if __name__ == "__main__":
    run_ladder()
