#!/usr/bin/env python3
"""
profile_inference_costs.py
Phase 6: Neural Inference Cost Attribution & Wall-Clock Profiling.
Measures:
1. Micro-benchmarks: latency of full_recompute, update_move, forward_pass, classical_eval.
2. Latency percentiles: Mean, P50, P95, P99 across 10,000 invocations.
3. Search economics at Depth 6 across 4 test positions for R1, H1, H2.
"""

import sys
import ctypes
import time
import json
import statistics
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
DLL_PATH = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.dll"
dll = ctypes.CDLL(str(DLL_PATH))

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupied", ctypes.c_uint64 * 2),
        ("all_occupied", ctypes.c_uint64),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_int8),
        ("halfmove_clock", ctypes.c_uint8),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
        ("pawn_key", ctypes.c_uint64),
    ]

class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ("best_move", ctypes.c_uint16),
        ("score", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("nodes", ctypes.c_uint64),
        ("elapsed_seconds", ctypes.c_double),
        ("pv", ctypes.c_uint16 * 64),
        ("pv_length", ctypes.c_int),
    ]

dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
dll.native_set_fen.restype = ctypes.c_bool
dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_evaluate.restype = ctypes.c_int
dll.native_r1_evaluate_nnue.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_r1_evaluate_nnue.restype = ctypes.c_int
dll.native_r1_set_eval_mode.argtypes = [ctypes.c_int, ctypes.c_int]
dll.native_r1_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
dll.native_r1_search.restype = ctypes.c_int

TEST_POSITIONS = [
    ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("KiwiPete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("Middlegame", "r2q1rk1/1b2bppp/p1n1pn2/1p1p4/3P4/1PN1PN2/P1BB1PPP/R2Q1RK1 w - - 0 12"),
    ("Endgame", "8/5k2/8/p1pP4/P1P5/8/5K2/8 w - - 0 1"),
]

def benchmark_micro_latency(n_samples=20000):
    print("=" * 80)
    print("PHASE 6: INFERENCE LATENCY & MICRO-BENCHMARKING")
    print("=" * 80)

    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    nb = NativeBoard()
    dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))

    # Benchmark 1: Classical Native Evaluate
    latencies_classical = []
    # Warmup
    for _ in range(500): dll.native_evaluate(ctypes.byref(nb))
    t0 = time.perf_counter()
    for _ in range(n_samples):
        t_start = time.perf_counter_ns()
        dll.native_evaluate(ctypes.byref(nb))
        latencies_classical.append(time.perf_counter_ns() - t_start)
    dur_classical = time.perf_counter() - t0

    # Benchmark 2: NNUE Full Recompute + Forward Evaluation
    latencies_nnue = []
    for _ in range(500): dll.native_r1_evaluate_nnue(ctypes.byref(nb))
    t0 = time.perf_counter()
    for _ in range(n_samples):
        t_start = time.perf_counter_ns()
        dll.native_r1_evaluate_nnue(ctypes.byref(nb))
        latencies_nnue.append(time.perf_counter_ns() - t_start)
    dur_nnue = time.perf_counter() - t0

    def stats_ns(l):
        mean_ns = statistics.mean(l)
        median_ns = statistics.median(l)
        p95_ns = statistics.quantiles(l, n=20)[18] if len(l) >= 20 else median_ns
        p99_ns = statistics.quantiles(l, n=100)[98] if len(l) >= 100 else p95_ns
        return {
            "mean_ns": round(mean_ns, 1),
            "median_ns": round(median_ns, 1),
            "p95_ns": round(p95_ns, 1),
            "p99_ns": round(p99_ns, 1),
            "mean_us": round(mean_ns / 1000.0, 3),
            "median_us": round(median_ns / 1000.0, 3),
            "p95_us": round(p95_ns / 1000.0, 3),
            "evals_per_sec": int(1e9 / mean_ns) if mean_ns > 0 else 0
        }

    stat_c = stats_ns(latencies_classical)
    stat_n = stats_ns(latencies_nnue)

    print(f"\n1. Classical Evaluation Latency ({n_samples} calls):")
    print(f"   Mean: {stat_c['mean_us']} us | P50: {stat_c['median_us']} us | P95: {stat_c['p95_us']} us | Throughput: {stat_c['evals_per_sec']:,} evals/sec")
    print(f"\n2. NNUE Full Evaluation Latency ({n_samples} calls):")
    print(f"   Mean: {stat_n['mean_us']} us | P50: {stat_n['median_us']} us | P95: {stat_n['p95_us']} us | Throughput: {stat_n['evals_per_sec']:,} evals/sec")
    print(f"\nLatency Ratio: NNUE is {stat_n['mean_ns'] / stat_c['mean_ns']:.2f}x slower than Classical per full leaf evaluation.")

    return {"classical": stat_c, "nnue": stat_n, "latency_ratio": round(stat_n['mean_ns'] / stat_c['mean_ns'], 2)}

def benchmark_search_economics(depth=6):
    print("\n" + "=" * 80)
    print(f"PHASE 6: SEARCH ECONOMICS & THROUGHPUT PROFILING (DEPTH {depth})")
    print("=" * 80)
    print(f"{'Position':12s} | {'Mode':10s} | {'Nodes':10s} | {'Time (ms)':10s} | {'NPS':10s} | {'Score (cp)':10s} | {'Best Move'}")
    print("-" * 80)

    modes = [("Classical R1", 0, 50), ("NNUE H1", 1, 100), ("Hybrid H2", 2, 50)]
    search_data = []

    for pos_name, fen in TEST_POSITIONS:
        for mode_name, emode, weight in modes:
            dll.native_r1_set_eval_mode(emode, weight)
            nb = NativeBoard()
            dll.native_set_fen(fen.encode("ascii"), ctypes.byref(nb))
            res = NativeSearchResult()

            # Execute search
            dll.native_r1_search(ctypes.byref(nb), depth, 10.0, ctypes.byref(res))

            nodes = res.nodes
            ms = res.elapsed_seconds * 1000.0
            nps = int(nodes / res.elapsed_seconds) if res.elapsed_seconds > 0 else 0
            score = res.score
            bm = f"m_{res.best_move}"

            print(f"{pos_name:12s} | {mode_name:10s} | {nodes:10d} | {ms:10.1f} | {nps:10d} | {score:10d} | {bm}")

            search_data.append({
                "position": pos_name,
                "mode": mode_name,
                "emode": emode,
                "weight": weight,
                "nodes": nodes,
                "time_ms": round(ms, 1),
                "nps": nps,
                "score_cp": score
            })

    return search_data

def main():
    micro_res = benchmark_micro_latency(20000)
    search_res = benchmark_search_economics(6)

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "inference_cost_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "micro_benchmarks": micro_res,
            "search_economics": search_res
        }, f, indent=2)
    print(f"\nInference cost audit saved to: {out_file}")

if __name__ == "__main__":
    main()
