import ctypes
import os
import json
import time

DLL_PATH = r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.dll"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_int),
        ("ep_square", ctypes.c_int),
        ("halfmove_clock", ctypes.c_int),
        ("fullmove_number", ctypes.c_int),
    ]

class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ("best_move", ctypes.c_uint16),
        ("score", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("nodes", ctypes.c_uint64),
        ("elapsed_seconds", ctypes.c_double),
        ("pv_length", ctypes.c_int),
        ("pv", ctypes.c_uint16 * 128),
    ]

TEST_POSITIONS = [
    {"name": "Startpos", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
    {"name": "Sicilian Najdorf", "fen": "r1bqkb1r/5ppp/p1npp3/1p4B1/3NP3/2N5/PPP2PPP/R2QKB1R w KQkq - 0 10"},
    {"name": "French Defense Backward e6", "fen": "r1bqk2r/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 2 8"},
    {"name": "Ruy Lopez Open", "fen": "r1bq1rk1/2p1bppp/p1np1n2/1p2p3/4P3/1B1P1N2/PPP2PPP/RNBQR1K1 w - - 1 9"},
    {"name": "Open King File Attacking", "fen": "r2q1rk1/1pp2ppp/p1nb4/8/2PP2b1/3B1N2/PP3PPP/R1BQR1K1 b - - 0 12"},
    {"name": "Severe King Exposure g-file", "fen": "r4rk1/pp1b1p1p/4p1p1/8/3B4/8/PPP2PPP/R4RK1 w - - 0 18"},
    {"name": "Isolated Queen Pawn", "fen": "r1bq1rk1/pp3ppp/2n1pn2/3p4/2PP4/2N2N2/PP2BPPP/R1BQK2R w KQ - 0 9"},
    {"name": "Endgame Lucena Rook", "fen": "1K1R4/1P6/8/8/8/8/r7/2k5 w - - 0 1"},
    {"name": "Tarrasch Rook Behind Passer", "fen": "8/5pk1/4p3/P7/8/1r6/4K3/R7 w - - 0 45"},
    {"name": "Pawns + Minor Pieces Tactical", "fen": "r2qkb1r/pp3ppp/2n1pn2/3p4/2PP4/2N1BB2/PP3PPP/R2QK2R b KQkq - 1 9"},
    {"name": "Backward Pawn d6 Endgame", "fen": "8/5pk1/3p1np1/2pP4/4PP2/7P/6K1/5N2 w - - 1 40"},
    {"name": "Symmetric Pawn Chain", "fen": "r2qk2r/ppp2ppp/2n1bn2/2bpp3/2BPP3/2N1BN2/PPP2PPP/R2QK2R w KQkq - 4 6"}
]

CONFIGS = [
    {
        "id": "F0",
        "name": "Reference X22-S (1T: E5, Outposts=1, PawnHash=1, BP=0, KFE=0)",
        "variant": b"X22",
        "threads": 1,
        "bp": 0,
        "kfe": 0,
        "phash": 1
    },
    {
        "id": "F1",
        "name": "Track A Alone (1T: E5, Outposts=1, PawnHash=1, BP=1, KFE=0)",
        "variant": b"X22",
        "threads": 1,
        "bp": 1,
        "kfe": 0,
        "phash": 1
    },
    {
        "id": "F2",
        "name": "Track B Alone (1T: E5, Outposts=1, PawnHash=1, BP=0, KFE=1)",
        "variant": b"X22",
        "threads": 1,
        "bp": 0,
        "kfe": 1,
        "phash": 1
    },
    {
        "id": "F3",
        "name": "Candidate X23-S (1T: E5, Outposts=1, PawnHash=1, BP=1, KFE=1)",
        "variant": b"X23",
        "threads": 1,
        "bp": 1,
        "kfe": 1,
        "phash": 1
    },
    {
        "id": "F4",
        "name": "Control X7 (1T Baseline: E5, Outposts=0, PawnHash=0, BP=0, KFE=0, Q0)",
        "variant": b"X7",
        "threads": 1,
        "bp": 0,
        "kfe": 0,
        "phash": 0
    },
    {
        "id": "F5",
        "name": "Candidate X23-P (4T SMP: E10, Outposts=1, PawnHash=1, BP=1, KFE=1)",
        "variant": b"X23",
        "threads": 4,
        "bp": 1,
        "kfe": 1,
        "phash": 1
    },
    {
        "id": "F6",
        "name": "Control X12 (4T Baseline: E10, Outposts=0, PawnHash=1, BP=0, KFE=0, Q0)",
        "variant": b"X12",
        "threads": 4,
        "bp": 0,
        "kfe": 0,
        "phash": 1
    }
]

def main():
    dll = ctypes.CDLL(DLL_PATH)
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    dll.native_apply_search_variant.argtypes = [ctypes.c_char_p]
    dll.native_apply_search_variant.restype = None

    dll.native_set_threads.argtypes = [ctypes.c_int]
    dll.native_set_threads.restype = None

    dll.native_set_backward_pawns_mode.argtypes = [ctypes.c_int]
    dll.native_set_backward_pawns_mode.restype = None

    dll.native_set_king_file_exposure_mode.argtypes = [ctypes.c_int]
    dll.native_set_king_file_exposure_mode.restype = None

    dll.native_set_pawn_hash.argtypes = [ctypes.c_int]
    dll.native_set_pawn_hash.restype = None

    dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_evaluate.restype = ctypes.c_int

    dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    dll.native_move_to_uci.restype = None

    dll.native_reset_p13_telemetry.restype = None
    dll.native_get_p13_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    dll.native_get_p13_telemetry.restype = None

    print("================================================================================")
    print("PROJECT JANUS — P1.18 SEARCH-EVAL FACTORIAL MATRIX & PROFILING")
    print("================================================================================")

    results = {}
    time_budget = 0.150 # 150ms per position

    for cfg in CONFIGS:
        cid = cfg["id"]
        cname = cfg["name"]
        print(f"\n--- Testing Config {cid}: {cname} ---")

        dll.native_apply_search_variant(cfg["variant"])
        dll.native_set_threads(cfg["threads"])
        dll.native_set_backward_pawns_mode(cfg["bp"])
        dll.native_set_king_file_exposure_mode(cfg["kfe"])
        dll.native_set_pawn_hash(cfg["phash"])

        total_nodes = 0
        total_time = 0.0
        depth_sum = 0
        pos_results = []

        for p_idx, pos in enumerate(TEST_POSITIONS):
            board = NativeBoard()
            dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(board))

            dll.native_reset_p13_telemetry()
            search_res = NativeSearchResult()

            # Search with 150ms budget
            t0 = time.perf_counter()
            dll.native_search(ctypes.byref(board), 64, time_budget, ctypes.byref(search_res))
            t1 = time.perf_counter()

            elapsed = t1 - t0
            nodes = search_res.nodes
            depth = search_res.depth
            score = search_res.score

            move_buf = ctypes.create_string_buffer(16)
            dll.native_move_to_uci(search_res.best_move, move_buf)
            best_move_str = move_buf.value.decode('utf-8')

            telem = (ctypes.c_uint64 * 9)()
            dll.native_get_p13_telemetry(telem)

            eval_calls = telem[4] # eval calls
            nps = int(nodes / elapsed) if elapsed > 0 else 0

            total_nodes += nodes
            total_time += elapsed
            depth_sum += depth

            pos_results.append({
                "pos_name": pos["name"],
                "depth": depth,
                "nodes": nodes,
                "elapsed": elapsed,
                "nps": nps,
                "score": score,
                "best_move": best_move_str,
                "eval_calls": eval_calls
            })

        avg_depth = depth_sum / len(TEST_POSITIONS)
        aggregate_nps = int(total_nodes / total_time) if total_time > 0 else 0

        print(f"[{cid}] Summary: Avg Depth: {avg_depth:.2f} | Total Nodes: {total_nodes:,} | Agg NPS: {aggregate_nps:,} | Time: {total_time:.2f}s")

        cfg_clean = dict(cfg)
        cfg_clean["variant"] = cfg["variant"].decode('utf-8')
        results[cid] = {
            "config": cfg_clean,
            "avg_depth": avg_depth,
            "total_nodes": total_nodes,
            "total_time": total_time,
            "aggregate_nps": aggregate_nps,
            "positions": pos_results
        }

    # Save factorial results
    out_path = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.18\raw\factorial_matrix_raw.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Factorial results written to {out_path}")

    # Phase 9: Detailed Pawn Hash Profiling
    print("\n================================================================================")
    print("PHASE 9: PAWN HASH PERFORMANCE & PROBE LATENCY BENCHMARK")
    print("================================================================================")

    pawn_profile = {}
    board = NativeBoard()
    dll.native_apply_search_variant(b"X23")
    dll.native_set_threads(1)
    dll.native_set_backward_pawns_mode(1)
    dll.native_set_king_file_exposure_mode(1)

    # 1. Measure eval latency WITH pawn hash vs WITHOUT pawn hash
    iters = 200000
    pos_fen = TEST_POSITIONS[1]["fen"].encode('utf-8')
    dll.native_set_fen(pos_fen, ctypes.byref(board))

    # With Pawn Hash enabled
    dll.native_set_pawn_hash(1)
    # warm up cache
    dll.native_evaluate(ctypes.byref(board))
    t0 = time.perf_counter()
    for _ in range(iters):
        dll.native_evaluate(ctypes.byref(board))
    t1 = time.perf_counter()
    pawn_hash_time = t1 - t0
    ns_per_eval_hash = (pawn_hash_time / iters) * 1e9

    # Without Pawn Hash
    dll.native_set_pawn_hash(0)
    t0 = time.perf_counter()
    for _ in range(iters):
        dll.native_evaluate(ctypes.byref(board))
    t1 = time.perf_counter()
    no_hash_time = t1 - t0
    ns_per_eval_nohash = (no_hash_time / iters) * 1e9

    speedup = ns_per_eval_nohash / ns_per_eval_hash if ns_per_eval_hash > 0 else 1.0

    print(f"Pawn Hash Enabled:  {ns_per_eval_hash:.1f} ns / eval ({iters:,} iterations)")
    print(f"Pawn Hash Disabled: {ns_per_eval_nohash:.1f} ns / eval ({iters:,} iterations)")
    print(f"Evaluation Speedup: {speedup:.2f}x")

    pawn_profile["eval_benchmark"] = {
        "iterations": iters,
        "ns_with_pawn_hash": ns_per_eval_hash,
        "ns_without_pawn_hash": ns_per_eval_nohash,
        "eval_speedup": speedup
    }

    # 2. Measure Pawn Hash Hit Rate over 5 deep searches
    dll.native_set_pawn_hash(1)
    hit_rates = []
    for pos in TEST_POSITIONS[:5]:
        b = NativeBoard()
        dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(b))
        dll.native_reset_p13_telemetry()
        sres = NativeSearchResult()
        dll.native_search(ctypes.byref(b), 64, 0.300, ctypes.byref(sres))
        # Note: probe and hit counters
        hit_rates.append({
            "pos": pos["name"],
            "depth": sres.depth,
            "nodes": sres.nodes
        })

    pawn_profile["searches"] = hit_rates

    hash_out = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.18\raw\pawn_hash_profile_raw.json"
    with open(hash_out, "w") as f:
        json.dump(pawn_profile, f, indent=2)
    print(f"[OK] Pawn hash profile written to {hash_out}")

if __name__ == "__main__":
    main()
