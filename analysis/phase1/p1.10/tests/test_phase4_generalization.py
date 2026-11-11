#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.10
Phase 4: Generalized Positional Validation Across 240 Failure Atlas Positions
Tests:
  - Tactical Correctness (52 positions)
  - Endgame Conversion & Oracle Outcomes (37 positions)
  - Human Positional Concepts (151 positions)
Configurations:
  1. X7_1T: Frozen Single-Thread Baseline (1T, E5 Eval, No LMP, Fixed Time)
  2. X12_4T: Frozen Multithreaded Baseline (4T, E10 Eval, LMP L1, Dynamic Time)
  3. X14_4T: Frozen P1.9 Candidate (4T, Refined E11, LMP L1, Dynamic Time)
  4. CAND_S_1T: Candidate S Prototype (1T, X7 Search Core + Lean E13 Endgame)
  5. CAND_P_4T: Candidate P Prototype (4T, X12 Search Core + E13 Endgame + 16K PawnHash)
"""

import os
import sys
import json
import time
import re
import subprocess
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path("E:/ChessXML/project-janus-phase1")
ATLAS_PATH = ROOT / "analysis" / "phase1" / "p1.9" / "corpus" / "generalized_failure_atlas_240.json"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.10" / "raw" / "generalization_validation_raw.json"
RAW_OUT.parent.mkdir(parents=True, exist_ok=True)

EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X14 = ROOT / "analysis" / "phase1" / "p1.9" / "control" / "janus_classical_x14.exe"
EXE_ABL = ROOT / "analysis" / "phase1" / "p1.9" / "tests" / "engine_eval_ablation.exe"

CONFIGS = [
    {
        "id": "X7_1T",
        "name": "Frozen X7 Baseline (1T)",
        "exe": str(EXE_X7),
        "threads": 1,
        "uci_opts": {}
    },
    {
        "id": "X12_4T",
        "name": "Frozen X12 Baseline (4T)",
        "exe": str(EXE_X12),
        "threads": 4,
        "uci_opts": {}
    },
    {
        "id": "X14_4T",
        "name": "Frozen X14 Platform (4T)",
        "exe": str(EXE_X14),
        "threads": 4,
        "uci_opts": {}
    },
    {
        "id": "CAND_S_1T",
        "name": "Candidate S Prototype (1T, X7 Core + E13 Endgame)",
        "exe": str(EXE_ABL),
        "threads": 1,
        "uci_opts": {
            "UCI_Variant": "X7",
            "UCI_ClassicalEval": "E13",
            "UCI_LMP": "L0",
            "UCI_DynamicTime": "false"
        }
    },
    {
        "id": "CAND_P_4T",
        "name": "Candidate P Prototype (4T, X12 Core + E13 Endgame + PawnHash)",
        "exe": str(EXE_ABL),
        "threads": 4,
        "uci_opts": {
            "UCI_Variant": "X12",
            "UCI_ClassicalEval": "E13",
            "UCI_LMP": "L1",
            "UCI_DynamicTime": "true",
            "UCI_PawnHash": "true"
        }
    }
]

def classify_position(pos):
    theme = pos.get("theme", "").lower()
    cluster = pos.get("cluster", "").lower()
    desc = pos.get("description", "").lower()

    tactical_kw = ["tactic", "fork", "pin", "sacrifice", "mate", "deflection", "attack", "skewer", "hanging", "check"]
    endgame_kw = ["endgame", "pawn_eg", "rook_eg", "minor_eg", "opposition", "race", "zugzwang", "fortress", "kp_vs_k", "lucena"]

    if any(k in theme or k in cluster or k in desc for k in tactical_kw):
        return "TACTICAL"
    elif any(k in theme or k in cluster or k in desc for k in endgame_kw):
        return "ENDGAME"
    else:
        return "POSITIONAL"

def run_single_engine(exe_path, fen, movetime_ms, threads, uci_opts):
    cmds = [
        "uci",
        f"setoption name Threads value {threads}"
    ]
    for opt, val in uci_opts.items():
        cmds.append(f"setoption name {opt} value {val}")
    cmds.extend([
        "isready",
        f"position fen {fen}",
        f"go movetime {movetime_ms}",
        "quit\n"
    ])

    t0 = time.perf_counter()
    try:
        p = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, _ = p.communicate("\n".join(cmds), timeout=8)
        dur = time.perf_counter() - t0
    except Exception:
        return {"depth": 0, "nodes": 0, "nps": 0, "score_cp": 0, "bestmove": None, "elapsed_s": 0.0}

    depth = 0
    nodes = 0
    bestmove = None
    score_cp = 0

    for line in out.splitlines():
        if "info depth" in line:
            m_d = re.search(r'depth (\d+)', line)
            m_n = re.search(r'nodes (\d+)', line)
            m_s = re.search(r'score cp (-?\d+)', line)
            m_m = re.search(r'score mate (-?\d+)', line)
            if m_d: depth = int(m_d.group(1))
            if m_n: nodes = int(m_n.group(1))
            if m_s: score_cp = int(m_s.group(1))
            elif m_m: score_cp = 10000 if int(m_m.group(1)) > 0 else -10000
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bestmove = parts[1]

    nps = int(nodes / dur) if dur > 0 else 0
    return {
        "depth": depth,
        "nodes": nodes,
        "nps": nps,
        "score_cp": score_cp,
        "bestmove": bestmove,
        "elapsed_s": round(dur, 4)
    }

def eval_position_worker(pos):
    pid = pos["id"]
    fen = pos["fen"]
    ptype = classify_position(pos)
    expected = pos.get("solution")

    engine_results = {}
    for cfg in CONFIGS:
        cid = cfg["id"]
        res = run_single_engine(cfg["exe"], fen, 200, cfg["threads"], cfg["uci_opts"])
        engine_results[cid] = res

    return {
        "id": pid,
        "fen": fen,
        "partition": pos.get("partition", "DEV"),
        "category": ptype,
        "expected": expected,
        "results": engine_results
    }

def main():
    print("=== PROJECT JANUS P1.10: PHASE 4 GENERALIZED POSITIONAL VALIDATION (240 POSITIONS) ===")
    with open(ATLAS_PATH, "r", encoding="utf-8") as f:
        atlas = json.load(f)

    all_positions = atlas["dev_positions"] + atlas["held_out_positions"]
    print(f"Loaded {len(all_positions)} positions from atlas.")

    categories = Counter(classify_position(p) for p in all_positions)
    print(f"Categories: {dict(categories)}")

    t0 = time.time()
    results_by_id = {}

    print(f"Evaluating across 5 configurations using 6 parallel workers (200ms movetime)...")
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(eval_position_worker, pos): pos["id"] for pos in all_positions}
        completed = 0
        for fut in as_completed(futures):
            res = fut.result()
            results_by_id[res["id"]] = res
            completed += 1
            if completed % 30 == 0 or completed == len(all_positions):
                print(f"  Completed {completed}/{len(all_positions)} positions [{(time.time()-t0):.1f}s]")

    total_time = round(time.time() - t0, 2)
    print(f"All positions evaluated in {total_time}s.")

    # Compute comparative metrics
    # Baseline moves
    x7_moves = {pid: data["results"]["X7_1T"]["bestmove"] for pid, data in results_by_id.items()}
    x12_moves = {pid: data["results"]["X12_4T"]["bestmove"] for pid, data in results_by_id.items()}

    configs_summary = {}
    for cfg in CONFIGS:
        cid = cfg["id"]
        cname = cfg["name"]

        cat_metrics = defaultdict(lambda: {"count": 0, "nodes": 0, "depth_sum": 0, "solved_expected": 0, "expected_count": 0, "agree_x7": 0, "agree_x12": 0})

        for pid, pos_data in results_by_id.items():
            cat = pos_data["category"]
            r = pos_data["results"][cid]
            bm = r["bestmove"]
            exp = pos_data["expected"]

            m = cat_metrics[cat]
            m["count"] += 1
            m["nodes"] += r["nodes"]
            m["depth_sum"] += r["depth"]

            if exp:
                m["expected_count"] += 1
                if bm == exp:
                    m["solved_expected"] += 1

            if bm == x7_moves.get(pid):
                m["agree_x7"] += 1
            if bm == x12_moves.get(pid):
                m["agree_x12"] += 1

        cfg_summary = {
            "name": cname,
            "categories": {}
        }
        for cat, m in cat_metrics.items():
            cnt = m["count"]
            cfg_summary["categories"][cat] = {
                "count": cnt,
                "avg_depth": round(m["depth_sum"] / cnt, 2) if cnt > 0 else 0,
                "avg_nodes": int(m["nodes"] / cnt) if cnt > 0 else 0,
                "solve_rate": f"{m['solved_expected']}/{m['expected_count']} ({m['solved_expected']/m['expected_count']*100:.1f}%)" if m["expected_count"] > 0 else "N/A",
                "agree_x7": f"{m['agree_x7']}/{cnt} ({m['agree_x7']/cnt*100:.1f}%)",
                "agree_x12": f"{m['agree_x12']}/{cnt} ({m['agree_x12']/cnt*100:.1f}%)"
            }
        configs_summary[cid] = cfg_summary

    output_payload = {
        "metadata": {
            "title": "Phase 4 Generalized Positional Validation Across 240 Positions",
            "total_positions": len(all_positions),
            "categories": dict(categories),
            "evaluation_movetime_ms": 200,
            "total_wallclock_s": total_time
        },
        "summary": configs_summary,
        "positions": results_by_id
    }

    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\nSaved raw results to {RAW_OUT}")
    print("\nSummary Results:")
    for cid, s in configs_summary.items():
        print(f"\n--- {cid}: {s['name']} ---")
        for cat, data in s["categories"].items():
            print(f"  [{cat}] Avg Depth: {data['avg_depth']} | Avg Nodes: {data['avg_nodes']} | Solved: {data['solve_rate']} | Agree X7: {data['agree_x7']} | Agree X12: {data['agree_x12']}")

if __name__ == "__main__":
    main()
