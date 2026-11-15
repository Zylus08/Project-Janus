#!/usr/bin/env python3
"""
profile_search_cost_attribution.py
Milestone P1.21 Phase 7: Search-Cost Attribution & Selectivity Profile.

Profiles:
1. Microbenchmark of static evaluation subsystems (Material, PST, Pawns, King Safety, Mobility, Endgame).
2. Main-search vs Quiescence-search node distribution across depths 4, 6, and 8.
3. Pruning cutoff breakdown: RFP cutoff rate, NMP cutoff rate, LMR re-search rate, first-move cutoffs.
4. Cross-engine NPS comparison between X22, X24, X25, and active engine.
"""

import os
import sys
import json
import time
import ctypes
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
ACTIVE_EXE = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
X22_EXE = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
X24_EXE = ROOT / "analysis" / "phase1" / "p1.19" / "control" / "janus_classical_x24.exe"
X25_EXE = ROOT / "analysis" / "phase1" / "p1.20" / "control" / "janus_classical_x25.exe"

OUT_RAW = ROOT / "analysis" / "phase1" / "p1.21" / "raw" / "search_cost_selectivity_raw.json"
OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

# Diagnostic test positions
POSITIONS = [
    {"id": "P01_START", "name": "Standard Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"id": "P02_SEMI_SLAV", "name": "Semi-Slav Complex", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQ - 0 7"},
    {"id": "P03_SIC_TACT", "name": "Sicilian Scheveningen", "fen": "2r2rk1/1bq1bppp/p2pp3/1p2P3/3N1P2/P1NR4/1PP1Q1PP/5R1K w - - 0 18"},
    {"id": "P04_FRENCH_ADV", "name": "French Advance", "fen": "r1bqk2r/pp1nbppp/2n1p3/2ppP3/3P1P2/2N1BN2/PPP3PP/R2QKB1R w KQkq - 1 8"},
    {"id": "P05_ROOK_END", "name": "Rook 4v3 Endgame", "fen": "8/5pk1/4p1p1/1R5p/8/6P1/r4PKP/8 w - - 0 35"},
    {"id": "P06_PAWN_RACE", "name": "Passed Pawn Race", "fen": "8/1P6/8/8/8/8/p7/k6K w - - 0 1"}
]

# Ctypes NativeBoard definition
class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]

def benchmark_eval_subsystems(iterations: int = 100_000) -> Dict[str, Any]:
    print(f"\n--- Part 1: Microbenchmarking Static Evaluation Subsystems ({iterations:,} iterations/pos) ---")
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    
    # Subsystem modes in native_evaluate_detail:
    # 0 = Material + PST only
    # 6 = Pawn structure v2
    # 7 = King safety v2
    # 8 = Mobility v2
    # 9 = Endgame v2
    # 15 = Full calibrated classical eval (X22)
    
    subsystems = {
        "material_pst": 0,
        "pawn_structure": 6,
        "king_safety": 7,
        "mobility": 8,
        "endgame": 9,
        "full_x22_e0": 15
    }
    
    board = NativeBoard()
    timings = {}
    
    for sub_name, emode in subsystems.items():
        # Set default flags
        dll.native_set_backward_pawns_mode(0)
        dll.native_set_connected_pawns_mode(1)
        
        total_time = 0.0
        for pos in POSITIONS[:3]: # Opening, middlegame, tactical
            dll.native_set_fen(pos["fen"].encode("ascii"), ctypes.byref(board))
            t0 = time.perf_counter()
            for _ in range(iterations):
                dll.native_evaluate_detail(ctypes.byref(board), emode)
            t1 = time.perf_counter()
            total_time += (t1 - t0)
            
        avg_ns = (total_time / (3 * iterations)) * 1e9
        timings[sub_name] = {
            "total_sec": total_time,
            "ns_per_call": round(avg_ns, 2),
            "calls_per_sec": int(1e9 / avg_ns) if avg_ns > 0 else 0
        }
        print(f"  Subsystem [{sub_name:<16}]: {avg_ns:>6.1f} ns/call ({timings[sub_name]['calls_per_sec']:,} calls/sec)")
        
    # Benchmark E1 (backward pawns enabled) vs E0 (legacy) vs E2 (connected pawns enabled)
    eval_variants = {}
    for ev_name, (bp, cp) in [("E0_Legacy", (0, 0)), ("E1_BackwardPawns", (1, 0)), ("E2_ConnectedPawns", (0, 1))]:
        dll.native_set_backward_pawns_mode(bp)
        dll.native_set_connected_pawns_mode(cp)
        total_time = 0.0
        for pos in POSITIONS[:3]:
            dll.native_set_fen(pos["fen"].encode("ascii"), ctypes.byref(board))
            t0 = time.perf_counter()
            for _ in range(iterations):
                dll.native_evaluate_detail(ctypes.byref(board), 15)
            t1 = time.perf_counter()
            total_time += (t1 - t0)
        avg_ns = (total_time / (3 * iterations)) * 1e9
        eval_variants[ev_name] = {
            "ns_per_call": round(avg_ns, 2),
            "calls_per_sec": int(1e9 / avg_ns) if avg_ns > 0 else 0
        }
        print(f"  Variant   [{ev_name:<16}]: {avg_ns:>6.1f} ns/call ({eval_variants[ev_name]['calls_per_sec']:,} calls/sec)")
        
    return {
        "subsystems": timings,
        "eval_variants": eval_variants
    }

def run_uci_search_telemetry(exe: Path, fen: str, depth: int, options: Dict[str, str] = None) -> Dict[str, Any]:
    proc = subprocess.Popen(
        [str(exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    def send(c):
        proc.stdin.write(c + "\n")
        proc.stdin.flush()
        
    send("uci")
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            break
            
    send("ucinewgame")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break
            
    if options:
        for k, v in options.items():
            send(f"setoption name {k} value {v}")
            
    send("setoption name Hash value 64")
    send("telemetry_reset")
    send("isready")
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            break
            
    send(f"position fen {fen}")
    
    t0 = time.perf_counter()
    send(f"go depth {depth}")
    
    bestmove = ""
    nodes = 0
    score = None
    nps = 0
    pv = ""
    
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line_str = line.strip()
        if "score cp" in line_str:
            parts = line_str.split()
            try:
                score = int(parts[parts.index("cp") + 1])
            except Exception:
                pass
        if "nodes" in line_str:
            parts = line_str.split()
            try:
                nodes = int(parts[parts.index("nodes") + 1])
            except Exception:
                pass
        if "nps" in line_str:
            parts = line_str.split()
            try:
                nps = int(parts[parts.index("nps") + 1])
            except Exception:
                pass
        if " pv " in line_str:
            pv = line_str.split(" pv ")[-1]
        if line_str.startswith("bestmove"):
            bestmove = line_str.split()[1]
            break
            
    t1 = time.perf_counter()
    wall_ms = round((t1 - t0) * 1000.0, 2)
    
    # Query telemetry
    telemetry = {}
    try:
        send("telemetry_report")
        send("isready")
        in_telem = False
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if "TELEMETRY_START" in line_str:
                in_telem = True
                continue
            if "TELEMETRY_END" in line_str:
                break
            if in_telem:
                parts = line_str.split()
                if len(parts) == 2:
                    k, v = parts[0], parts[1]
                    try:
                        telemetry[k] = int(v)
                    except ValueError:
                        telemetry[k] = v
    except Exception as e:
        telemetry["error"] = str(e)
        
    try:
        send("quit")
        proc.wait(timeout=1.0)
    except Exception:
        proc.kill()
        
    return {
        "bestmove": bestmove,
        "score": score,
        "nodes": nodes,
        "nps": nps,
        "wall_ms": wall_ms,
        "pv": pv,
        "telemetry": telemetry
    }

def benchmark_selectivity_and_node_distribution() -> Dict[str, Any]:
    print("\n--- Part 2: Main-Search vs Quiescence-Search Node Distribution & Cutoff Profile ---")
    data = []
    
    for pos in POSITIONS:
        pid = pos["id"]
        pname = pos["name"]
        fen = pos["fen"]
        print(f"\nAnalyzing [{pid}] {pname}")
        
        pos_entry = {
            "id": pid,
            "name": pname,
            "fen": fen,
            "depths": {}
        }
        
        for d in [4, 6, 8]:
            res = run_uci_search_telemetry(ACTIVE_EXE, fen, d)
            telem = res.get("telemetry", {})
            
            nodes = res.get("nodes", 0)
            main_nodes = telem.get("main_nodes", 0)
            q_nodes = telem.get("qsearch_nodes", 0)
            
            q_pct = round((q_nodes / nodes * 100.0), 1) if nodes > 0 else 0.0
            
            rfp_p = telem.get("rfp_probes", 0)
            rfp_c = telem.get("rfp_cutoffs", 0)
            rfp_pct = round((rfp_c / rfp_p * 100.0), 1) if rfp_p > 0 else 0.0
            
            nmp_p = telem.get("nmp_probes", 0)
            nmp_c = telem.get("nmp_cutoffs", 0)
            nmp_pct = round((nmp_c / nmp_p * 100.0), 1) if nmp_p > 0 else 0.0
            
            first_c = telem.get("first_move_cutoffs", 0)
            tot_c = telem.get("total_cutoffs", 0)
            first_pct = round((first_c / tot_c * 100.0), 1) if tot_c > 0 else 0.0
            
            d_entry = {
                "depth": d,
                "bestmove": res["bestmove"],
                "score": res["score"],
                "nodes": nodes,
                "main_nodes": main_nodes,
                "qsearch_nodes": q_nodes,
                "qsearch_ratio_pct": q_pct,
                "rfp_probes": rfp_p,
                "rfp_cutoffs": rfp_c,
                "rfp_cutoff_pct": rfp_pct,
                "nmp_probes": nmp_p,
                "nmp_cutoffs": nmp_c,
                "nmp_cutoff_pct": nmp_pct,
                "first_move_cutoff_pct": first_pct,
                "eval_calls": telem.get("eval_calls", 0),
                "wall_ms": res["wall_ms"]
            }
            pos_entry["depths"][f"d{d}"] = d_entry
            print(f"  Depth {d}: TotalNodes={nodes:>7,d} | Main={main_nodes:>6,d} | Qsearch={q_nodes:>6,d} ({q_pct:>4.1f}%) | RFP={rfp_c}/{rfp_p} ({rfp_pct}%) | NMP={nmp_c}/{nmp_p} ({nmp_pct}%) | 1stCutoff={first_pct}% | Wall={res['wall_ms']}ms")
            
        data.append(pos_entry)
        
    return data

def benchmark_cross_engine_nps() -> Dict[str, Any]:
    print("\n--- Part 3: Cross-Engine NPS Comparison (X22 vs X24 vs X25 vs Active) ---")
    engines = {
        "Janus_X22": X22_EXE,
        "Janus_X24": X24_EXE,
        "Janus_X25": X25_EXE,
        "Active_Engine": ACTIVE_EXE
    }
    
    comparisons = {}
    depth = 8
    
    for eng_name, exe_path in engines.items():
        print(f"\nBenchmarking Engine [{eng_name}] at Depth {depth}...")
        eng_nodes = 0
        eng_wall_ms = 0.0
        pos_results = []
        
        for pos in POSITIONS:
            res = run_uci_search_telemetry(exe_path, pos["fen"], depth)
            eng_nodes += res["nodes"]
            eng_wall_ms += res["wall_ms"]
            pos_results.append({
                "pos_id": pos["id"],
                "bestmove": res["bestmove"],
                "score": res["score"],
                "nodes": res["nodes"],
                "wall_ms": res["wall_ms"],
                "nps": res["nps"]
            })
            
        overall_nps = int(eng_nodes / (eng_wall_ms / 1000.0)) if eng_wall_ms > 0 else 0
        comparisons[eng_name] = {
            "total_nodes": eng_nodes,
            "total_wall_ms": round(eng_wall_ms, 2),
            "aggregate_nps": overall_nps,
            "positions": pos_results
        }
        print(f"  Engine [{eng_name}]: AggNodes={eng_nodes:,d} | AggWall={eng_wall_ms:.1f}ms | Aggregate NPS={overall_nps:,d}")
        
    return comparisons

def main():
    print("Starting Milestone P1.21 Phase 7 Search-Cost & Selectivity Profiling...")
    
    # 1. Microbenchmarking evaluation
    eval_benchmarks = benchmark_eval_subsystems(iterations=100_000)
    
    # 2. Selectivity and Node Distribution
    node_dist = benchmark_selectivity_and_node_distribution()
    
    # 3. Cross-Engine NPS Comparison
    cross_engine = benchmark_cross_engine_nps()
    
    full_report = {
        "eval_microbenchmarks": eval_benchmarks,
        "selectivity_and_node_distribution": node_dist,
        "cross_engine_nps": cross_engine
    }
    
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
        
    print(f"\nAll search-cost and selectivity telemetry saved to: {OUT_RAW}")

if __name__ == "__main__":
    main()
