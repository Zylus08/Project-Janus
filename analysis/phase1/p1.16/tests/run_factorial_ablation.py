import ctypes
import os
import json
import time

DLL_PATH = r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.dll"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupied", ctypes.c_uint64 * 2),
        ("all_occupied", ctypes.c_uint64),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_int),
        ("en_passant_square", ctypes.c_int),
        ("halfmove_clock", ctypes.c_int),
        ("fullmove_number", ctypes.c_int),
        ("hash_key", ctypes.c_uint64),
        ("pawn_hash_key", ctypes.c_uint64),
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

def run_factorial_ablation():
    dll = ctypes.CDLL(DLL_PATH)

    dll.native_init.restype = None
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_evaluate.restype = ctypes.c_int

    dll.native_set_eval_mode.argtypes = [ctypes.c_int]
    dll.native_set_eval_mode.restype = None

    dll.native_set_pawn_hash.argtypes = [ctypes.c_int]
    dll.native_set_pawn_hash.restype = None

    dll.native_set_qsearch_mode.argtypes = [ctypes.c_int]
    dll.native_set_qsearch_mode.restype = None

    dll.native_reset_qsearch_telemetry.restype = None

    dll.native_get_qsearch_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    dll.native_get_qsearch_telemetry.restype = None

    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    dll.native_apply_search_variant.argtypes = [ctypes.c_char_p]
    dll.native_apply_search_variant.restype = None

    dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    dll.native_move_to_uci.restype = None

    dll.native_set_threads.argtypes = [ctypes.c_int]
    dll.native_set_threads.restype = None

    # Load 30 tactical positions from Phase 5
    from test_selective_checking import TACTICAL_SUITE

    # 10 Checkmate positions from Phase 4
    MATE_POSITIONS = [
        "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
        "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",
        "4R1k1/5ppp/8/8/8/8/8/6K1 b - - 1 1",
        "6nk/5Npp/8/8/8/8/8/7K b - - 1 1",
        "7k/7R/5N2/8/8/8/8/6K1 b - - 1 1",
        "r1b1kbnr/pppp1Qpp/8/4p3/2B1P3/8/PPPP1PPP/RNB1K2R b KQkq - 0 5",
        "5k2/5Q2/5K2/8/8/8/8/8 b - - 1 1",
        "7R/6R1/8/8/8/8/8/4K2k b - - 1 1",
        "8/8/8/8/8/5k2/4q3/4K3 w - - 0 1",
        "k7/2Q5/1K6/8/8/8/8/8 b - - 0 1" # Stalemate test
    ]

    # 8 Configurations of Factorial Ablation Matrix:
    # B0: X7 1T | Q0 | E5 (NoHash)
    # B1: X7 1T | Q1 | E5 (NoHash)
    # B2: X7 1T | Q2 | E5 (NoHash)
    # B3: X7 1T | Q0 | E5 (PawnHash)
    # B4: X7 1T | Q1 | E5 (PawnHash) [Candidate X21-S]
    # B5: X12 4T | Q0 | E10 (PawnHash) [Frozen X12 Baseline]
    # B6: X12 4T | Q1 | E10 (PawnHash) [Candidate X21-P]
    # B7: X12 4T | Q2 | E10 (PawnHash)
    configs = [
        {"id": "B0", "threads": 1, "qmode": 0, "emode": 5, "phash": 0, "name": "X7 1T | Q0 (Legacy) | E5 (Baseline Control)"},
        {"id": "B1", "threads": 1, "qmode": 1, "emode": 5, "phash": 0, "name": "X7 1T | Q1 (Corrected QSearch) | E5 (Baseline Eval)"},
        {"id": "B2", "threads": 1, "qmode": 2, "emode": 5, "phash": 0, "name": "X7 1T | Q2 (Quiet Checks) | E5 (Baseline Eval)"},
        {"id": "B3", "threads": 1, "qmode": 0, "emode": 5, "phash": 1, "name": "X7 1T | Q0 (Legacy) | E5 + 64K Pawn Hash"},
        {"id": "B4", "threads": 1, "qmode": 1, "emode": 5, "phash": 1, "name": "X7 1T | Q1 (Corrected) | E5 + 64K Pawn Hash [Candidate X21-S]"},
        {"id": "B5", "threads": 4, "qmode": 0, "emode": 10, "phash": 1, "name": "X12 4T | Q0 (Legacy) | E10 (Baseline Control)"},
        {"id": "B6", "threads": 4, "qmode": 1, "emode": 10, "phash": 1, "name": "X12 4T | Q1 (Corrected) | E10 [Candidate X21-P]"},
        {"id": "B7", "threads": 4, "qmode": 2, "emode": 10, "phash": 1, "name": "X12 4T | Q2 (Quiet Checks) | E10"}
    ]

    b = NativeBoard()
    res = NativeSearchResult()
    move_buf = ctypes.create_string_buffer(16)
    telem = (ctypes.c_uint64 * 3)()

    print("================================================================================")
    print("PROJECT JANUS — PHASE 7: CONTROLLED FACTORIAL ABLATION MATRIX (B0 - B7)")
    print("================================================================================")

    matrix_results = {}

    for cfg in configs:
        cid = cfg["id"]
        threads = cfg["threads"]
        qmode = cfg["qmode"]
        emode = cfg["emode"]
        phash = cfg["phash"]
        cname = cfg["name"]

        print(f"\n[{cid}] Running: {cname}")

        dll.native_apply_search_variant(b"X21")
        dll.native_set_threads(threads)
        dll.native_set_qsearch_mode(qmode)
        dll.native_set_eval_mode(emode)
        dll.native_set_pawn_hash(phash)

        # 1. Checkmate Detection Rate (10 positions, depth 1 search)
        mates_solved = 0
        for m_fen in MATE_POSITIONS:
            dll.native_set_fen(m_fen.encode('utf-8'), ctypes.byref(b))
            dll.native_search(ctypes.byref(b), 1, 0.05, ctypes.byref(res))
            # If mate detected or score is mate/draw
            if res.score <= -28000 or res.score >= 28000 or res.score == 0:
                mates_solved += 1
        mate_rate = mates_solved / len(MATE_POSITIONS)

        # 2. Tactical Benchmark (30 positions at 150ms per move)
        tactical_solved = 0
        total_nodes = 0
        total_depth = 0
        total_time = 0.0

        for item in TACTICAL_SUITE:
            fen = item["fen"]
            expected = item["solution"]
            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
            dll.native_search(ctypes.byref(b), 64, 0.15, ctypes.byref(res))
            dll.native_move_to_uci(res.best_move, move_buf)
            best_uci = move_buf.value.decode('utf-8')
            if best_uci == expected:
                tactical_solved += 1
            total_nodes += res.nodes
            total_depth += res.depth
            total_time += res.elapsed_seconds

        n_tactical = len(TACTICAL_SUITE)
        solve_rate = tactical_solved / n_tactical
        avg_depth = total_depth / n_tactical
        nps = int(total_nodes / total_time) if total_time > 0 else 0

        # 3. Fixed Depth NPS Benchmark on Startpos (Depth 9)
        dll.native_set_fen(b"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ctypes.byref(b))
        dll.native_search(ctypes.byref(b), 9, 5.0, ctypes.byref(res))
        startpos_nps = int(res.nodes / res.elapsed_seconds) if res.elapsed_seconds > 0 else 0
        startpos_nodes = res.nodes

        matrix_results[cid] = {
            "config": cfg,
            "mate_detection_rate": mate_rate,
            "mate_solved": mates_solved,
            "tactical_solve_rate": solve_rate,
            "tactical_solved": tactical_solved,
            "avg_depth": avg_depth,
            "total_nodes": total_nodes,
            "search_nps": nps,
            "startpos_nps": startpos_nps,
            "startpos_nodes": startpos_nodes
        }

        print(f"  Checkmate Rate: {mates_solved:>2}/10 ({mate_rate*100:5.1f}%) | Tactical Solved: {tactical_solved:>2}/30 ({solve_rate*100:5.1f}%) | Avg Depth: {avg_depth:4.1f} | NPS: {nps:>9,d}")

    # Print Factorial Matrix Table
    print("\n--------------------------------------------------------------------------------")
    print("FACTORIAL ABLATION SUMMARY TABLE")
    print("--------------------------------------------------------------------------------")
    print(f"{'Config':<6} | {'Threads':<7} | {'QMode':<5} | {'EMode':<5} | {'PawnHash':<8} | {'Mate Rate':<10} | {'Tac Solved':<10} | {'Depth':<6} | {'NPS':<10}")
    print("-" * 80)
    for cid in ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7"]:
        r = matrix_results[cid]
        c = r["config"]
        print(f"{cid:<6} | {c['threads']:<7} | Q{c['qmode']:<4} | E{c['emode']:<4} | {c['phash']!s:<8} | {r['mate_detection_rate']*100:5.1f}%     | {r['tactical_solve_rate']*100:5.1f}%     | {r['avg_depth']:5.1f}  | {r['search_nps']:>9,d}")
    print("================================================================================")

    os.makedirs(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw", exist_ok=True)
    out_file = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw\factorial_ablation_raw.json"
    with open(out_file, "w") as f:
        json.dump(matrix_results, f, indent=2)
    print(f"\nRaw results written to {out_file}")

if __name__ == "__main__":
    run_factorial_ablation()
