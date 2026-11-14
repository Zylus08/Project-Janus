import ctypes
import os
import json
import time
import chess

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

def mirror_fen(fen):
    parts = fen.split()
    rows = parts[0].split('/')
    mirrored_rows = []
    for r in reversed(rows):
        new_r = ""
        for ch in r:
            if ch.isalpha():
                new_r += ch.lower() if ch.isupper() else ch.upper()
            else:
                new_r += ch
            mirrored_rows.append(new_r)
    new_board = '/'.join(mirrored_rows)
    new_turn = 'b' if parts[1] == 'w' else 'w'
    cr = parts[2]
    new_cr = ""
    if 'K' in cr: new_cr += 'k'
    if 'Q' in cr: new_cr += 'q'
    if 'k' in cr: new_cr += 'K'
    if 'q' in cr: new_cr += 'Q'
    if not new_cr: new_cr = '-'
    ep = parts[3]
    if ep != '-':
        f = ep[0]
        r = ep[1]
        new_r = str(9 - int(r))
        new_ep = f + new_r
    else:
        new_ep = '-'
    hm = parts[4] if len(parts) > 4 else '0'
    fm = parts[5] if len(parts) > 5 else '1'
    return f"{new_board} {new_turn} {new_cr} {new_ep} {hm} {fm}"

def invert_fen(fen):
    parts = fen.split()
    rows = parts[0].split('/')
    mirrored_rows = []
    for r in reversed(rows):
        new_r = ""
        for ch in r:
            if ch.isalpha():
                new_r += ch.lower() if ch.isupper() else ch.upper()
            else:
                new_r += ch
        mirrored_rows.append(new_r)
    new_board = '/'.join(mirrored_rows)
    new_turn = parts[1]
    cr = parts[2]
    new_cr = ""
    if 'K' in cr: new_cr += 'k'
    if 'Q' in cr: new_cr += 'q'
    if 'k' in cr: new_cr += 'K'
    if 'q' in cr: new_cr += 'Q'
    if not new_cr: new_cr = '-'
    ep = parts[3]
    if ep != '-':
        f = ep[0]
        r = ep[1]
        new_r = str(9 - int(r))
        new_ep = f + new_r
    else:
        new_ep = '-'
    hm = parts[4] if len(parts) > 4 else '0'
    fm = parts[5] if len(parts) > 5 else '1'
    return f"{new_board} {new_turn} {new_cr} {new_ep} {hm} {fm}"

def run_targeted_eval_experiment():
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

    dll.native_get_pawn_hash.restype = ctypes.c_int

    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    dll.native_apply_search_variant.argtypes = [ctypes.c_char_p]
    dll.native_apply_search_variant.restype = None

    dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    dll.native_move_to_uci.restype = None

    # Load Phase 2 225-position corpus
    pos_file = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw\evaluation_correctness_raw.json"
    with open(pos_file, "r") as f:
        corpus = json.load(f)["evaluated_positions"]

    # 4 Targeted Evaluation Configurations on 1T
    configs = [
        {"id": "E5_NoHash", "eval_mode": 5, "pawn_hash": 0, "name": "Baseline X7 1T (E5 Combined Classical, No Pawn Hash)"},
        {"id": "E5_PawnHash", "eval_mode": 5, "pawn_hash": 1, "name": "E5 Classical + 64K Entry Pawn Hash Table"},
        {"id": "E10_NoHash", "eval_mode": 10, "pawn_hash": 0, "name": "E10 Enhanced (V2 Pawns + Outposts + Tarrasch, No Hash)"},
        {"id": "E10_PawnHash", "eval_mode": 10, "pawn_hash": 1, "name": "E10 Enhanced + 64K Entry Pawn Hash Table"}
    ]

    b = NativeBoard()
    b_mir = NativeBoard()
    b_inv = NativeBoard()
    res = NativeSearchResult()
    move_buf = ctypes.create_string_buffer(16)

    print("================================================================================")
    print("PROJECT JANUS — PHASE 6: TARGETED CLASSICAL EVALUATION REPAIR AUDIT")
    print("================================================================================")

    audit_results = {}

    for cfg in configs:
        cid = cfg["id"]
        emode = cfg["eval_mode"]
        phash = cfg["pawn_hash"]
        cname = cfg["name"]

        print(f"\n--- Testing Config: {cid} | Mode: E{emode} | PawnHash: {phash} ---")
        print(f"Description: {cname}")

        dll.native_apply_search_variant(b"X21")
        dll.native_set_eval_mode(emode)
        dll.native_set_pawn_hash(phash)

        # 1. Symmetry Audit across 225 positions
        mirror_sym_passes = 0
        inv_sym_passes = 0

        for item in corpus:
            fen = item["fen"]
            dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
            ev = dll.native_evaluate(ctypes.byref(b))

            # Mirror symmetry (Relative colour symmetry: mirror board and side to move)
            py_b = chess.Board(fen)
            py_mir = py_b.mirror()
            dll.native_set_fen(py_mir.fen().encode('utf-8'), ctypes.byref(b_mir))
            ev_mir = dll.native_evaluate(ctypes.byref(b_mir))
            if ev == ev_mir:
                mirror_sym_passes += 1

            # Invert symmetry (Absolute colour inversion: mirror pieces but keep turn)
            py_inv = py_b.mirror()
            py_inv.turn = py_b.turn
            dll.native_set_fen(py_inv.fen().encode('utf-8'), ctypes.byref(b_inv))
            ev_inv = dll.native_evaluate(ctypes.byref(b_inv))
            if ev == -ev_inv:
                inv_sym_passes += 1

        n_pos = len(corpus)
        mirror_rate = mirror_sym_passes / n_pos
        inv_rate = inv_sym_passes / n_pos

        # 2. Evaluation Throughput Benchmark (10,000 evaluations across corpus)
        t0 = time.perf_counter()
        eval_loops = 45 # 45 * 225 = 10,125 evals
        for _ in range(eval_loops):
            for item in corpus:
                dll.native_set_fen(item["fen"].encode('utf-8'), ctypes.byref(b))
                _ = dll.native_evaluate(ctypes.byref(b))
        t1 = time.perf_counter()
        eval_time = t1 - t0
        evals_per_sec = int((eval_loops * n_pos) / eval_time) if eval_time > 0 else 0

        # 3. Search NPS Benchmark on Startpos (Depth 9)
        dll.native_set_fen(b"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ctypes.byref(b))
        dll.native_search(ctypes.byref(b), 9, 10.0, ctypes.byref(res))
        startpos_nps = int(res.nodes / res.elapsed_seconds) if res.elapsed_seconds > 0 else 0
        startpos_depth = res.depth
        startpos_nodes = res.nodes

        # 4. Search NPS Benchmark on KiwiPete (Depth 8)
        dll.native_set_fen(b"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", ctypes.byref(b))
        dll.native_search(ctypes.byref(b), 8, 10.0, ctypes.byref(res))
        kiwi_nps = int(res.nodes / res.elapsed_seconds) if res.elapsed_seconds > 0 else 0
        kiwi_depth = res.depth
        kiwi_nodes = res.nodes

        combined_nps = int((startpos_nps + kiwi_nps) / 2)

        audit_results[cid] = {
            "config": cfg,
            "symmetry": {
                "mirror_passed": mirror_sym_passes,
                "mirror_rate": mirror_rate,
                "invert_passed": inv_sym_passes,
                "invert_rate": inv_rate
            },
            "eval_throughput_eps": evals_per_sec,
            "search_benchmarks": {
                "startpos_nps": startpos_nps,
                "startpos_depth": startpos_depth,
                "startpos_nodes": startpos_nodes,
                "kiwipete_nps": kiwi_nps,
                "kiwipete_depth": kiwi_depth,
                "kiwipete_nodes": kiwi_nodes,
                "combined_nps": combined_nps
            }
        }

        print(f"  Mirror Symmetry: {mirror_sym_passes}/{n_pos} ({mirror_rate*100:.1f}%) | Inversion: {inv_sym_passes}/{n_pos} ({inv_rate*100:.1f}%)")
        print(f"  Raw Eval Throughput: {evals_per_sec:>9,d} evals/sec")
        print(f"  Startpos D{startpos_depth}: {startpos_nodes:>7,d} nodes | {startpos_nps:>8,d} NPS")
        print(f"  KiwiPete D{kiwi_depth}: {kiwi_nodes:>7,d} nodes | {kiwi_nps:>8,d} NPS")
        print(f"  Combined Search NPS: {combined_nps:>8,d} NPS")

    # Comparative NPS & Gating Analysis
    print("\n--------------------------------------------------------------------------------")
    print("COMPARATIVE EVALUATION AUDIT RELATIVE TO BASELINE (E5_NoHash)")
    print("--------------------------------------------------------------------------------")

    base_nps = audit_results["E5_NoHash"]["search_benchmarks"]["combined_nps"]

    for cid in ["E5_PawnHash", "E10_NoHash", "E10_PawnHash"]:
        cand_nps = audit_results[cid]["search_benchmarks"]["combined_nps"]
        nps_delta_pct = (cand_nps - base_nps) / base_nps * 100.0
        sym_ok = (audit_results[cid]["symmetry"]["mirror_rate"] == 1.0 and audit_results[cid]["symmetry"]["invert_rate"] == 1.0)
        nps_ok = (nps_delta_pct >= -5.0)

        print(f"[{cid}] NPS Delta: {nps_delta_pct:+5.1f}% | Symmetry 100%: {sym_ok} | NPS Safe (>= -5%): {nps_ok}")

    os.makedirs(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw", exist_ok=True)
    out_file = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw\targeted_evaluation_raw.json"
    with open(out_file, "w") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\nRaw results written to {out_file}")

if __name__ == "__main__":
    run_targeted_eval_experiment()
