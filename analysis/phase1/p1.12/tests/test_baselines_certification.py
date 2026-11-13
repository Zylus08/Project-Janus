#!/usr/bin/env python3
"""
Certification Diagnostics for Qualified Classical Baselines (Milestone P1.12):
Track S: Janus Classical X7 (Single-Thread Baseline)
Track P: Janus Classical X12 (Four-Thread Baseline)
"""

import time
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
OUT_RAW = ROOT / "analysis" / "phase1" / "p1.12" / "raw" / "baseline_certification_raw.json"

TEST_POSITIONS = [
    {"id": "STARTPOS", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "KIWIPETE", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"},
    {"id": "TACTICAL_01", "fen": "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"},
    {"id": "ENDGAME_01", "fen": "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1"}
]


def run_uci(exe_path: Path, cmds: list) -> str:
    proc = subprocess.Popen(
        [str(exe_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    cmd_str = "\n".join(cmds) + "\nquit\n"
    stdout, _ = proc.communicate(cmd_str)
    return stdout


def parse_search_info(stdout: str):
    bm = ""
    nodes = 0
    nps = 0
    depth = 0
    score = 0
    for line in stdout.splitlines():
        line = line.strip()
        if "info" in line and "depth" in line:
            parts = line.split()
            if "depth" in parts:
                depth = int(parts[parts.index("depth") + 1])
            if "nodes" in parts:
                nodes = int(parts[parts.index("nodes") + 1])
            if "nps" in parts:
                nps = int(parts[parts.index("nps") + 1])
            if "score" in parts and "cp" in parts:
                score = int(parts[parts.index("cp") + 1])
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bm = parts[1]
    return bm, depth, nodes, nps, score


def certify_engine(exe_path: Path, name: str, threads: int, extra_opts: dict) -> Dict[str, Any]:
    print(f"Certifying {name} ({threads}T)...")
    
    # 1. UCI Options query
    uci_out = run_uci(exe_path, ["uci"])
    options = [line for line in uci_out.splitlines() if line.startswith("option name")]
    
    # 2. Setup command lines
    setup_cmds = ["uci"]
    setup_cmds.append(f"setoption name Threads value {threads}")
    for k, v in extra_opts.items():
        setup_cmds.append(f"setoption name {k} value {v}")
    setup_cmds.extend(["isready", "ucinewgame"])
    
    # 3. Test positions across fixed-depth and fixed-time
    bench_results = []
    for pos in TEST_POSITIONS:
        # Fixed depth 7
        t0 = time.time()
        out_d7 = run_uci(exe_path, setup_cmds + [f"position fen {pos['fen']}", "go depth 7"])
        el_d7 = time.time() - t0
        bm_d7, d_d7, nodes_d7, nps_d7, s_d7 = parse_search_info(out_d7)
        
        # Fixed depth 8
        t0 = time.time()
        out_d8 = run_uci(exe_path, setup_cmds + [f"position fen {pos['fen']}", "go depth 8"])
        el_d8 = time.time() - t0
        bm_d8, d_d8, nodes_d8, nps_d8, s_d8 = parse_search_info(out_d8)
        
        # Fixed time 100ms
        t0 = time.time()
        out_t100ms = run_uci(exe_path, setup_cmds + [f"position fen {pos['fen']}", "go movetime 100"])
        el_t100ms = time.time() - t0
        bm_t100ms, d_t100ms, nodes_t100ms, nps_t100ms, s_t100ms = parse_search_info(out_t100ms)

        # Fixed time 250ms
        t0 = time.time()
        out_t250ms = run_uci(exe_path, setup_cmds + [f"position fen {pos['fen']}", "go movetime 250"])
        el_t250ms = time.time() - t0
        bm_t250ms, d_t250ms, nodes_t250ms, nps_t250ms, s_t250ms = parse_search_info(out_t250ms)
        
        bench_results.append({
            "id": pos["id"],
            "fen": pos["fen"],
            "depth_7": {"best_move": bm_d7, "depth": d_d7, "nodes": nodes_d7, "nps": nps_d7, "score_cp": s_d7, "wall_s": round(el_d7, 3)},
            "depth_8": {"best_move": bm_d8, "depth": d_d8, "nodes": nodes_d8, "nps": nps_d8, "score_cp": s_d8, "wall_s": round(el_d8, 3)},
            "movetime_100ms": {"best_move": bm_t100ms, "depth": d_t100ms, "nodes": nodes_t100ms, "nps": nps_t100ms, "score_cp": s_t100ms, "wall_s": round(el_t100ms, 3)},
            "movetime_250ms": {"best_move": bm_t250ms, "depth": d_t250ms, "nodes": nodes_t250ms, "nps": nps_t250ms, "score_cp": s_t250ms, "wall_s": round(el_t250ms, 3)}
        })
        
    return {
        "name": name,
        "threads": threads,
        "exe_path": str(exe_path),
        "options_count": len(options),
        "benchmark": bench_results
    }


def main():
    print("=" * 80)
    print("QUALIFIED CLASSICAL BASELINE CERTIFICATION (P1.12)")
    print("=" * 80)
    
    cert_x7 = certify_engine(EXE_X7, "Janus Classical X7 (Track S)", threads=1, extra_opts={"UCI_Variant": "X7", "UCI_DynamicTime": "false"})
    cert_x12 = certify_engine(EXE_X12, "Janus Classical X12 (Track P)", threads=4, extra_opts={"UCI_Variant": "X12", "UCI_ClassicalEval": "E10"})
    
    results = {
        "track_s_x7": cert_x7,
        "track_p_x12": cert_x12
    }
    
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved certification results to {OUT_RAW}")


if __name__ == "__main__":
    main()
