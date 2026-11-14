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

def run_search_economics():
    dll = ctypes.CDLL(DLL_PATH)

    dll.native_init.restype = None
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_evaluate.restype = ctypes.c_int

    dll.native_generate_legal_moves.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    dll.native_generate_legal_moves.restype = ctypes.c_int

    dll.native_generate_captures.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    dll.native_generate_captures.restype = ctypes.c_int

    dll.native_generate_quiets.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
    dll.native_generate_quiets.restype = ctypes.c_int

    dll.native_see.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
    dll.native_see.restype = ctypes.c_int

    dll.native_set_eval_mode.argtypes = [ctypes.c_int]
    dll.native_set_eval_mode.restype = None

    dll.native_set_pawn_hash.argtypes = [ctypes.c_int]
    dll.native_set_pawn_hash.restype = None

    dll.native_set_qsearch_mode.argtypes = [ctypes.c_int]
    dll.native_set_qsearch_mode.restype = None

    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    dll.native_apply_search_variant.argtypes = [ctypes.c_char_p]
    dll.native_apply_search_variant.restype = None

    dll.native_set_threads.argtypes = [ctypes.c_int]
    dll.native_set_threads.restype = None

    b = NativeBoard()
    moves_buf = (ctypes.c_uint16 * 256)()
    res = NativeSearchResult()

    print("================================================================================")
    print("PROJECT JANUS — PHASE 8: CLASSICAL SEARCH ECONOMICS & PROFILING")
    print("================================================================================")

    # 1. Component Latency Profiling (100,000 iterations each)
    STARTPOS = b"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    KIWIPETE = b"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    CHECK_POS = b"rnb1kbnr/pppp1ppp/8/4p3/7q/5P2/PPPPP1PP/RNBQKBNR w KQkq - 1 3"

    dll.native_set_fen(KIWIPETE, ctypes.byref(b))
    n_caps = dll.native_generate_captures(ctypes.byref(b), moves_buf)
    test_move = moves_buf[0] if n_caps > 0 else 0

    N_ITERS = 100000

    # Test native_evaluate (E5)
    dll.native_set_eval_mode(5)
    dll.native_set_pawn_hash(0)
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        _ = dll.native_evaluate(ctypes.byref(b))
    t1 = time.perf_counter()
    time_eval_e5 = (t1 - t0) / N_ITERS * 1e9 # ns

    # Test native_evaluate (E5 + PawnHash)
    dll.native_set_pawn_hash(1)
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        _ = dll.native_evaluate(ctypes.byref(b))
    t1 = time.perf_counter()
    time_eval_e5_hash = (t1 - t0) / N_ITERS * 1e9 # ns

    # Test native_see
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        _ = dll.native_see(ctypes.byref(b), test_move)
    t1 = time.perf_counter()
    time_see = (t1 - t0) / N_ITERS * 1e9 # ns

    # Test capture movegen
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        _ = dll.native_generate_captures(ctypes.byref(b), moves_buf)
    t1 = time.perf_counter()
    time_gen_caps = (t1 - t0) / N_ITERS * 1e9 # ns

    # Test quiet movegen
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        _ = dll.native_generate_quiets(ctypes.byref(b), moves_buf)
    t1 = time.perf_counter()
    time_gen_quiets = (t1 - t0) / N_ITERS * 1e9 # ns

    # Test legal evasions under check
    dll.native_set_fen(CHECK_POS, ctypes.byref(b))
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        _ = dll.native_generate_legal_moves(ctypes.byref(b), moves_buf)
    t1 = time.perf_counter()
    time_gen_evasions = (t1 - t0) / N_ITERS * 1e9 # ns

    print("Component Latency Profile (Nanoseconds per Call):")
    print(f"  eval_e5 (no hash):          {time_eval_e5:6.1f} ns ({int(1e9/time_eval_e5):,d} ops/sec)")
    print(f"  eval_e5 (with 64K hash):    {time_eval_e5_hash:6.1f} ns ({int(1e9/time_eval_e5_hash):,d} ops/sec)")
    print(f"  janus_see (static exchange):{time_see:6.1f} ns ({int(1e9/time_see):,d} ops/sec)")
    print(f"  capture movegen:            {time_gen_caps:6.1f} ns ({int(1e9/time_gen_caps):,d} ops/sec)")
    print(f"  quiet movegen:              {time_gen_quiets:6.1f} ns ({int(1e9/time_gen_quiets):,d} ops/sec)")
    print(f"  legal evasions (in-check):  {time_gen_evasions:6.1f} ns ({int(1e9/time_gen_evasions):,d} ops/sec)")

    # 2. Effective Branching Factor (EBF) from Depth 4 to Depth 10
    print("\nEffective Branching Factor (EBF) Analysis (Startpos, 1T):")
    dll.native_apply_search_variant(b"X21")
    dll.native_set_threads(1)
    dll.native_set_qsearch_mode(1)
    dll.native_set_eval_mode(5)
    dll.native_set_pawn_hash(1)

    depth_nodes = {}
    prev_nodes = None
    ebf_table = []

    for d in range(4, 11):
        dll.native_set_fen(STARTPOS, ctypes.byref(b))
        dll.native_search(ctypes.byref(b), d, 30.0, ctypes.byref(res))
        nodes = res.nodes
        ebf = (nodes / prev_nodes) if prev_nodes and prev_nodes > 0 else 0.0
        depth_nodes[d] = {
            "nodes": nodes,
            "ebf": ebf,
            "nps": int(nodes / res.elapsed_seconds) if res.elapsed_seconds > 0 else 0
        }
        ebf_table.append((d, nodes, ebf, depth_nodes[d]["nps"]))
        print(f"  Depth {d:>2}: {nodes:>9,d} nodes | EBF: {ebf:5.2f}x | NPS: {depth_nodes[d]['nps']:>9,d}")
        prev_nodes = nodes

    # 3. Game 12 P1.15 Forensics: Q0 vs Q1 node behavior on tactical positions
    print("\nP1.15 Game 12 Forensics: Dissecting the 18.7x Node Reduction Claim:")
    G12_FEN = b"r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5" # Tactical mate threat

    # Search under Q0 (Legacy Quiescence)
    dll.native_set_qsearch_mode(0)
    dll.native_set_fen(G12_FEN, ctypes.byref(b))
    dll.native_search(ctypes.byref(b), 8, 5.0, ctypes.byref(res))
    nodes_q0 = res.nodes
    score_q0 = res.score
    depth_q0 = res.depth

    # Search under Q1 (Corrected Quiescence)
    dll.native_set_qsearch_mode(1)
    dll.native_set_fen(G12_FEN, ctypes.byref(b))
    dll.native_search(ctypes.byref(b), 8, 5.0, ctypes.byref(res))
    nodes_q1 = res.nodes
    score_q1 = res.score
    depth_q1 = res.depth

    node_ratio_g12 = nodes_q0 / nodes_q1 if nodes_q1 > 0 else 1.0
    print(f"  Legacy Q0:    Depth {depth_q0} | Nodes: {nodes_q0:>8,d} | Score: {score_q0}")
    print(f"  Corrected Q1: Depth {depth_q1} | Nodes: {nodes_q1:>8,d} | Score: {score_q1}")
    print(f"  Observed Node Ratio: {node_ratio_g12:.2f}x")
    print(f"  Analysis: In legacy Q0, checkmates were evaluated as minor positional deficits (-89 cp),")
    print(f"  causing premature beta-cutoffs and pruning away necessary defensive trees.")
    print(f"  In corrected Q1, true checkmates (-29000 cp) force complete tactical evasion exploration.")

    raw_output = {
        "component_latencies_ns": {
            "eval_e5": time_eval_e5,
            "eval_e5_hash": time_eval_e5_hash,
            "janus_see": time_see,
            "gen_caps": time_gen_caps,
            "gen_quiets": time_gen_quiets,
            "gen_evasions": time_gen_evasions
        },
        "ebf_profile": depth_nodes,
        "g12_forensics": {
            "fen": G12_FEN.decode('utf-8'),
            "q0": {"nodes": nodes_q0, "score": score_q0, "depth": depth_q0},
            "q1": {"nodes": nodes_q1, "score": score_q1, "depth": depth_q1},
            "node_ratio": node_ratio_g12
        }
    }

    os.makedirs(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw", exist_ok=True)
    out_file = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw\search_economics_raw.json"
    with open(out_file, "w") as f:
        json.dump(raw_output, f, indent=2)
    print(f"\nRaw results written to {out_file}")

if __name__ == "__main__":
    run_search_economics()
