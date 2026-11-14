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

# 30 Curated Tactical Benchmark Positions (WAC, STS, Classic Combinations)
TACTICAL_SUITE = [
    {"id": "TAC_01", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5", "solution": "f3f7", "desc": "Scholar's mate Qxf7#"},
    {"id": "TAC_02", "fen": "3r2k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", "solution": "d1d8", "desc": "Back-rank rook mate on d8"},
    {"id": "TAC_03", "fen": "6k1/5ppp/8/8/8/8/1q4PP/4Q1K1 w - - 0 1", "solution": "e1e8", "desc": "Back rank queen mate e1e8#"},
    {"id": "TAC_04", "fen": "r1b2rk1/pp1p1ppp/2n1p3/q5N1/2P5/2bB4/P1Q2PPP/1RB2RK1 w - - 0 13", "solution": "d3h7", "desc": "Bxh7+ greek gift check"},
    {"id": "TAC_05", "fen": "4kb1r/p2rqppp/5n2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 14", "solution": "b5d7", "desc": "Bxd7+ Morphy opera mate deflection"},
    {"id": "TAC_06", "fen": "r1b2rk1/pp3ppp/2n1p3/3pP3/3P4/2PB1N2/P4PPP/R3K2R w KQ - 0 13", "solution": "d3h7", "desc": "Classic Bxh7+ Greek gift sacrifice"},
    {"id": "TAC_07", "fen": "rn2kb1r/pp3ppp/4p3/1qp1N3/3P4/8/PPP2PPP/R1BQK2R w KQkq - 0 11", "solution": "d1h5", "desc": "Queen penetration on h5 attacking f7"},
    {"id": "TAC_08", "fen": "r1b1k2r/pppp1ppp/8/4N3/1b1qn3/8/PPP2PPP/RNBQKB1R w KQkq - 0 8", "solution": "c2c3", "desc": "c3 blocking check defending mate"},
    {"id": "TAC_09", "fen": "r1b1kb1r/pppp1ppp/5q2/4n3/3PP1n1/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6", "solution": "d1d2", "desc": "Qd2 defending f2 against mate"},
    {"id": "TAC_10", "fen": "r1bqk2r/ppp2ppp/2n5/1B1pP3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7", "solution": "c1d2", "desc": "Bd2 unpinning knight"},
    {"id": "TAC_11", "fen": "r1bqkb1r/pp2pppp/2np1n2/8/3NP3/2N1B3/PPP2PPP/R2QKB1R b KQkq - 2 6", "solution": "f6g4", "desc": "Ng4 attacking bishop pair"},
    {"id": "TAC_12", "fen": "r1b1kb1r/ppppqppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5", "solution": "f3g5", "desc": "Ng5 targeting f7 weakness"},
    {"id": "TAC_13", "fen": "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", "solution": "c2c3", "desc": "c3 preparing d4 center break"},
    {"id": "TAC_14", "fen": "r1bqk1nr/pppp1ppp/2n5/4p3/1bB1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 2 4", "solution": "e1g1", "desc": "O-O kingside safety castle"},
    {"id": "TAC_15", "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 1 4", "solution": "c2c3", "desc": "c3 solidifying center"},
    {"id": "TAC_16", "fen": "r2qkb1r/pp1bpppp/2n2n2/1B1p4/3NP3/2N5/PPP2PPP/R1BQK2R w KQkq - 1 7", "solution": "e4d5", "desc": "exd5 opening position with tempo"},
    {"id": "TAC_17", "fen": "r1b1k2r/ppppqppp/2n5/b3P3/2B5/1QP2N2/P4PPP/RNB2RK1 b kq - 0 9", "solution": "e8g8", "desc": "O-O king safety under pressure"},
    {"id": "TAC_18", "fen": "r1bqkb1r/pp1ppppp/2n2n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5", "solution": "b1c3", "desc": "Nc3 classical development"},
    {"id": "TAC_19", "fen": "r1b1k1nr/pppp1ppp/2n5/4p3/1b1PP2q/2P2N2/PP3PPP/RNBQKB1R b KQkq - 0 5", "solution": "h4e4", "desc": "Qxe4+ taking pawn with check"},
    {"id": "TAC_20", "fen": "r1bqk2r/pppp1ppp/2n2n2/4p3/1b2P3/2NP1N2/PPP2PPP/R1BQKB1R w KQkq - 1 5", "solution": "c1d2", "desc": "Bd2 breaking pin"},
    {"id": "TAC_21", "fen": "r2qkb1r/pp2pppp/2n1bn2/2pp4/3P4/2PBPN2/PP3PPP/RNBQK2R w KQkq - 3 6", "solution": "d4c5", "desc": "dxc5 taking pawn"},
    {"id": "TAC_22", "fen": "r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R w KQ - 1 6", "solution": "c1g5", "desc": "Bg5 active pin"},
    {"id": "TAC_23", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 5", "solution": "c3e4", "desc": "Nxe4 regaining piece"},
    {"id": "TAC_24", "fen": "r1bqkb1r/pppp1ppp/2n5/4P3/3pn3/5N2/PPP2PPP/RNBQKB1R w KQkq - 1 6", "solution": "f1d3", "desc": "Bd3 attacking active knight"},
    {"id": "TAC_25", "fen": "r2qkb1r/ppp1pppp/2n2n2/3p4/3P1Bb1/4PN2/PPP2PPP/RN1QKB1R w KQkq - 1 5", "solution": "f1e2", "desc": "Be2 breaking pin developing"},
    {"id": "TAC_26", "fen": "r1bqkb1r/1pp2ppp/p1np1n2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R w KQkq - 0 6", "solution": "f3g5", "desc": "Ng5 double attack on f7"},
    {"id": "TAC_27", "fen": "r1bqk2r/ppp2ppp/2n1pn2/3p4/1bPP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 1 6", "solution": "f1d3", "desc": "Bd3 standard development"},
    {"id": "TAC_28", "fen": "r1b1k2r/ppppqppp/2n2n2/4p3/1bPP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 3 6", "solution": "d4d5", "desc": "d5 kicking knight gaining space"},
    {"id": "TAC_29", "fen": "r1bqkb1r/ppp2ppp/2np1n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5", "solution": "f3g5", "desc": "Ng5 targeting f7 weakness"},
    {"id": "TAC_30", "fen": "r1bqkb1r/ppp1pppp/2n5/3p4/3Pn3/2N1PN2/PPP2PPP/R1BQKB1R w KQkq - 1 5", "solution": "c3e4", "desc": "Nxe4 trading active knight"}
]

def run_selective_checking_experiment():
    dll = ctypes.CDLL(DLL_PATH)

    dll.native_init.restype = None
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_set_qsearch_mode.argtypes = [ctypes.c_int]
    dll.native_set_qsearch_mode.restype = None

    dll.native_get_qsearch_mode.restype = ctypes.c_int

    dll.native_reset_qsearch_telemetry.restype = None

    dll.native_get_qsearch_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    dll.native_get_qsearch_telemetry.restype = None

    dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
    dll.native_move_to_uci.restype = None

    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    dll.native_apply_search_variant.argtypes = [ctypes.c_char_p]
    dll.native_apply_search_variant.restype = None

    # Apply X21 baseline configuration
    dll.native_apply_search_variant(b"X21")

    policies = [
        (0, "Q0", "Frozen Legacy (Captures only, stand-pat always)"),
        (1, "Q1", "Corrected Quiescence (In-check evasions & mate detection)"),
        (2, "Q2", "Q1 + Quiet Checks at qply 0"),
        (3, "Q3", "Q2 + Conservative Check Filter (SEE >= 0 checks)")
    ]

    time_limits = [0.10, 0.50] # 100ms and 500ms fixed search budgets

    b = NativeBoard()
    res = NativeSearchResult()
    move_buf = ctypes.create_string_buffer(16)
    telem = (ctypes.c_uint64 * 3)()

    print("================================================================================")
    print("PROJECT JANUS — PHASE 5: SELECTIVE CHECKING-MOVE QUIESCENCE RESEARCH")
    print("================================================================================")

    master_results = {}

    for mode, code, desc in policies:
        print(f"\nEvaluating Policy {code}: {desc}")
        dll.native_set_qsearch_mode(mode)
        master_results[code] = {
            "mode": mode,
            "description": desc,
            "time_controls": {}
        }

        for tl in time_limits:
            tl_ms = int(tl * 1000)
            total_solved = 0
            total_nodes = 0
            total_time = 0.0
            total_depth = 0
            checks_generated = 0
            pos_details = []

            for item in TACTICAL_SUITE:
                fen = item["fen"]
                expected = item["solution"]

                dll.native_reset_qsearch_telemetry()
                dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))

                dll.native_search(ctypes.byref(b), 64, tl, ctypes.byref(res))
                dll.native_move_to_uci(res.best_move, move_buf)
                dll.native_get_qsearch_telemetry(telem)

                best_uci = move_buf.value.decode('utf-8')
                is_solved = (best_uci == expected)

                if is_solved:
                    total_solved += 1
                total_nodes += res.nodes
                total_time += res.elapsed_seconds
                total_depth += res.depth
                checks_generated += telem[2]

                pos_details.append({
                    "id": item["id"],
                    "expected": expected,
                    "found": best_uci,
                    "solved": is_solved,
                    "score": res.score,
                    "depth": res.depth,
                    "nodes": res.nodes,
                    "checks_gen": telem[2]
                })

            n_pos = len(TACTICAL_SUITE)
            solve_rate = total_solved / n_pos
            avg_depth = total_depth / n_pos
            avg_nodes = total_nodes / n_pos
            nps = int(total_nodes / total_time) if total_time > 0 else 0

            master_results[code]["time_controls"][f"{tl_ms}ms"] = {
                "solved": total_solved,
                "total_positions": n_pos,
                "solve_rate": solve_rate,
                "avg_depth": avg_depth,
                "total_nodes": total_nodes,
                "avg_nodes": avg_nodes,
                "nps": nps,
                "checks_generated": checks_generated,
                "positions": pos_details
            }

            print(f"  [{tl_ms}ms] Solved: {total_solved:>2}/{n_pos} ({solve_rate*100:5.1f}%) | Avg Depth: {avg_depth:4.1f} | Avg Nodes: {avg_nodes:>7.0f} | NPS: {nps:>8} | Checks Gen: {checks_generated}")

    # Comparative Analysis & Gate Adjudication
    print("\n--------------------------------------------------------------------------------")
    print("COMPARATIVE EVALUATION & GATING CRITERIA (500ms)")
    print("--------------------------------------------------------------------------------")

    q1_500 = master_results["Q1"]["time_controls"]["500ms"]
    q1_solved = q1_500["solved"]
    q1_depth = q1_500["avg_depth"]
    q1_nodes = q1_500["total_nodes"]

    gate_verdicts = {}

    for code in ["Q0", "Q2", "Q3"]:
        cand = master_results[code]["time_controls"]["500ms"]
        delta_solved = (cand["solved"] - q1_solved) / len(TACTICAL_SUITE) * 100.0
        delta_depth = cand["avg_depth"] - q1_depth
        node_ratio = cand["total_nodes"] / q1_nodes if q1_nodes > 0 else 1.0

        # Gating rules:
        # 1. Tactical solve rate improves by >= 5.0% over Q1
        # 2. Search nodes / quiescence explosion <= 25% (node_ratio <= 1.25)
        # 3. Effective depth does not regress by >= 1.0 ply
        crit1 = delta_solved >= 5.0
        crit2 = node_ratio <= 1.25
        crit3 = delta_depth >= -1.0

        gate_pass = crit1 and crit2 and crit3
        gate_verdicts[code] = {
            "delta_solved_pct": delta_solved,
            "delta_depth_ply": delta_depth,
            "node_ratio": node_ratio,
            "crit1_solve_rate": crit1,
            "crit2_node_budget": crit2,
            "crit3_depth_preserved": crit3,
            "gate_adopted": gate_pass
        }

        print(f"Policy {code} vs Q1: dSolved={delta_solved:+5.1f}% | dDepth={delta_depth:+4.1f} | NodeRatio={node_ratio:5.2f}x | Adopted: {gate_pass}")

    # Selection decision
    selected_policy = "Q1"
    if gate_verdicts["Q3"]["gate_adopted"]:
        selected_policy = "Q3"
    elif gate_verdicts["Q2"]["gate_adopted"]:
        selected_policy = "Q2"

    print(f"\nAuthoritative Selected Quiescence Architecture: {selected_policy}")
    print("================================================================================")

    os.makedirs(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw", exist_ok=True)
    out_file = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw\selective_checking_raw.json"
    with open(out_file, "w") as f:
        json.dump({
            "selected_policy": selected_policy,
            "gate_verdicts": gate_verdicts,
            "master_results": master_results
        }, f, indent=2)
    print(f"Raw results written to {out_file}")

if __name__ == "__main__":
    run_selective_checking_experiment()
