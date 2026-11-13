#!/usr/bin/env python3
"""
profile_search_pipeline.py
Phase 2: Comprehensive Classical Search Pipeline Profiling Suite
Project Janus — Phase 1, Milestone P1.13
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X7  = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_X = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
EXE_SF11 = Path("E:/ChessXML/tools/stockfish_11/stockfish_11.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.13" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PROFILING_POSITIONS = [
    {
        "id": "POS_STARTPOS",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "category": "opening"
    },
    {
        "id": "POS_TACTICAL_TACTIC1",
        "fen": "r1bqkb1r/pppp1ppp/2n5/1B2p3/4n3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5",
        "category": "tactical_middlegame"
    },
    {
        "id": "POS_COMPLEX_MIDDLEGAME",
        "fen": "r2q1rk1/1b2bppp/p1np4/1p1Np3/4P3/1B2BN2/PPP2PPP/R2Q1RK1 w - - 4 13",
        "category": "quiet_middlegame"
    },
    {
        "id": "POS_KING_ATTACK",
        "fen": "r1b2rk1/2q1bppp/p2p1n2/np2p3/3PP3/1B2BN1P/PP1N1PP1/R2QR1K1 w - - 1 14",
        "category": "attacking_middlegame"
    },
    {
        "id": "POS_PAWN_ENDGAME",
        "fen": "8/5p2/4k3/4p1p1/4P1P1/4KP2/8/8 w - - 0 45",
        "category": "pawn_endgame"
    },
    {
        "id": "POS_ROOK_ENDGAME",
        "fen": "8/8/1R6/8/8/2k5/r7/2K5 b - - 0 1",
        "category": "rook_endgame"
    }
]

def run_janus_profile(exe_path, variant, threads, fen, fixed_depth=8, fixed_time_ms=None):
    proc = subprocess.Popen(
        [str(exe_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    def send(cmd):
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    send("uci")
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            break

    send(f"setoption name Threads value {threads}")
    send(f"setoption name UCI_Variant value {variant}")
    send("ucinewgame")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break

    send(f"position fen {fen}")
    send("telemetry_reset")
    while True:
        line = proc.stdout.readline()
        if not line or "telemetry_reset_ok" in line:
            break

    if fixed_time_ms:
        cmd = f"go movetime {fixed_time_ms}"
    else:
        cmd = f"go depth {fixed_depth}"

    t0 = time.time()
    send(cmd)
    
    depth = 0
    seldepth = 0
    nodes = 0
    nps = 0
    score_cp = 0
    bestmove = None

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("info"):
            parts = line.split()
            if "depth" in parts:
                try: depth = int(parts[parts.index("depth") + 1])
                except Exception: pass
            if "seldepth" in parts:
                try: seldepth = int(parts[parts.index("seldepth") + 1])
                except Exception: pass
            if "nodes" in parts:
                try: nodes = int(parts[parts.index("nodes") + 1])
                except Exception: pass
            if "nps" in parts:
                try: nps = int(parts[parts.index("nps") + 1])
                except Exception: pass
            if "score" in parts and "cp" in parts:
                try: score_cp = int(parts[parts.index("cp") + 1])
                except Exception: pass
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bestmove = parts[1]
            break
            
    wall_clock_s = time.time() - t0

    # Request telemetry
    telemetry = {}
    send("telemetry_report")
    in_telemetry = False
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line == "TELEMETRY_START":
            in_telemetry = True
            continue
        elif line == "TELEMETRY_END":
            break
        if in_telemetry:
            parts = line.split()
            if len(parts) == 2:
                try:
                    telemetry[parts[0]] = int(parts[1])
                except ValueError:
                    telemetry[parts[0]] = parts[1]

    send("quit")
    try:
        proc.terminate()
        proc.wait(timeout=1.0)
    except Exception:
        proc.kill()

    return {
        "variant": variant,
        "threads": threads,
        "fen": fen,
        "bestmove": bestmove,
        "depth": depth,
        "seldepth": seldepth,
        "nodes": nodes,
        "nps": nps,
        "score_cp": score_cp,
        "wall_clock_s": wall_clock_s,
        "telemetry": telemetry
    }


def run_stockfish_profile(exe_path, threads, fen, fixed_depth=8):
    proc = subprocess.Popen(
        [str(exe_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    def send(cmd):
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    send("uci")
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            break

    send(f"setoption name Threads value {threads}")
    send("setoption name Hash value 32")
    send("ucinewgame")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break

    send(f"position fen {fen}")
    t0 = time.time()
    send(f"go depth {fixed_depth}")

    depth = 0
    seldepth = 0
    nodes = 0
    nps = 0
    score_cp = 0
    bestmove = None

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("info"):
            parts = line.split()
            if "depth" in parts:
                try: depth = int(parts[parts.index("depth") + 1])
                except Exception: pass
            if "seldepth" in parts:
                try: seldepth = int(parts[parts.index("seldepth") + 1])
                except Exception: pass
            if "nodes" in parts:
                try: nodes = int(parts[parts.index("nodes") + 1])
                except Exception: pass
            if "nps" in parts:
                try: nps = int(parts[parts.index("nps") + 1])
                except Exception: pass
            if "score" in parts and "cp" in parts:
                try: score_cp = int(parts[parts.index("cp") + 1])
                except Exception: pass
        elif line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bestmove = parts[1]
            break

    wall_clock_s = time.time() - t0
    send("quit")
    try:
        proc.terminate()
        proc.wait(timeout=1.0)
    except Exception:
        proc.kill()

    return {
        "engine": "Stockfish 11",
        "threads": threads,
        "fen": fen,
        "bestmove": bestmove,
        "depth": depth,
        "seldepth": seldepth,
        "nodes": nodes,
        "nps": nps,
        "score_cp": score_cp,
        "wall_clock_s": wall_clock_s
    }


def main():
    print("================================================================================")
    print("PHASE 2: FULL SEARCH PIPELINE PROFILING")
    print("================================================================================")
    
    results = {
        "X7_1T": [],
        "X12_4T": [],
        "SF11_1T": [],
        "SF11_4T": []
    }

    depth = 9

    for pos in PROFILING_POSITIONS:
        pid = pos["id"]
        fen = pos["fen"]
        print(f"\n--- Profiling Position: {pid} (depth {depth}) ---")
        
        # Profile X7 (1T)
        print("Running Janus X7 (1T)...")
        r_x7 = run_janus_profile(EXE_X, "X7", 1, fen, fixed_depth=depth)
        r_x7["pos_id"] = pid
        results["X7_1T"].append(r_x7)
        print(f"  X7 (1T): bm={r_x7['bestmove']} nodes={r_x7['nodes']} nps={r_x7['nps']} time={r_x7['wall_clock_s']:.3f}s")
        if r_x7["telemetry"]:
            t = r_x7["telemetry"]
            print(f"    Telemetry: movegen={t.get('movegen_calls',0)}, eval={t.get('eval_calls',0)}, "
                  f"cutoffs={t.get('total_cutoffs',0)}, 1st_move_cut={t.get('first_move_cutoffs',0)}, "
                  f"nmp_cut={t.get('nmp_cutoffs',0)}, rfp_cut={t.get('rfp_cutoffs',0)}")

        # Profile X12 (4T)
        print("Running Janus X12 (4T)...")
        r_x12 = run_janus_profile(EXE_X, "X12", 4, fen, fixed_depth=depth)
        r_x12["pos_id"] = pid
        results["X12_4T"].append(r_x12)
        print(f"  X12 (4T): bm={r_x12['bestmove']} nodes={r_x12['nodes']} nps={r_x12['nps']} time={r_x12['wall_clock_s']:.3f}s")

        # Profile Stockfish 11 (1T)
        print("Running Stockfish 11 (1T)...")
        r_sf11_1t = run_stockfish_profile(EXE_SF11, 1, fen, fixed_depth=depth)
        r_sf11_1t["pos_id"] = pid
        results["SF11_1T"].append(r_sf11_1t)
        print(f"  SF11 (1T): bm={r_sf11_1t['bestmove']} nodes={r_sf11_1t['nodes']} nps={r_sf11_1t['nps']} time={r_sf11_1t['wall_clock_s']:.3f}s")

        # Profile Stockfish 11 (4T)
        print("Running Stockfish 11 (4T)...")
        r_sf11_4t = run_stockfish_profile(EXE_SF11, 4, fen, fixed_depth=depth)
        r_sf11_4t["pos_id"] = pid
        results["SF11_4T"].append(r_sf11_4t)
        print(f"  SF11 (4T): bm={r_sf11_4t['bestmove']} nodes={r_sf11_4t['nodes']} nps={r_sf11_4t['nps']} time={r_sf11_4t['wall_clock_s']:.3f}s")

    out_file = RAW_DIR / "search_pipeline_profile.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved profiling results to {out_file}")

if __name__ == "__main__":
    main()

