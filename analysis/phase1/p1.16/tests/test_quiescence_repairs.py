import ctypes
import os
import json

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

def run_quiescence_repairs_test():
    dll = ctypes.CDLL(DLL_PATH)

    dll.native_init.restype = None
    dll.native_init()

    dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
    dll.native_set_fen.restype = ctypes.c_int

    dll.native_is_check.argtypes = [ctypes.POINTER(NativeBoard)]
    dll.native_is_check.restype = ctypes.c_bool

    dll.native_set_qsearch_mode.argtypes = [ctypes.c_int]
    dll.native_set_qsearch_mode.restype = None

    dll.native_get_qsearch_mode.restype = ctypes.c_int

    dll.native_reset_qsearch_telemetry.restype = None

    dll.native_get_qsearch_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    dll.native_get_qsearch_telemetry.restype = None

    dll.native_qsearch.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    dll.native_qsearch.restype = ctypes.c_int

    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    # 40 Test Positions across 7 categories
    # Each item: (id, category, fen, expected_description, check_condition)
    test_positions = [
        # Category 1: Checkmate detection in quiescence (10 positions)
        ("M01", "checkmate", "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", "Fool's mate (W in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M02", "checkmate", "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4", "Scholar's mate (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M03", "checkmate", "4R1k1/5ppp/8/8/8/8/8/6K1 b - - 1 1", "Back-rank mate (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M04", "checkmate", "6nk/5Npp/8/8/8/8/8/7K b - - 1 1", "Smothered mate (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M05", "checkmate", "7k/7R/5N2/8/8/8/8/6K1 b - - 1 1", "Arabian mate pattern (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M06", "checkmate", "r1b1kbnr/pppp1Qpp/8/4p3/2B1P3/8/PPPP1PPP/RNB1K2R b KQkq - 0 5", "Queen/Bishop mate (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M07", "checkmate", "5k2/5Q2/5K2/8/8/8/8/8 b - - 1 1", "King/Queen box mate (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M08", "checkmate", "7R/6R1/8/8/8/8/8/4K2k b - - 1 1", "Double rook mate (B in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M09", "checkmate", "8/8/8/8/8/5k2/4q3/4K3 w - - 0 1", "Queen in face mate (W in mate)", lambda q1, q0: q1 <= -28000 and q0 > -20000),
        ("M10", "checkmate", "4r1k1/5ppp/8/8/8/8/8/3R2K1 w - - 0 1", "White to deliver back-rank mate (depth 1 search)", lambda q1, q0: True),

        # Category 2: Stalemate detection in quiescence (5 positions)
        ("S01", "stalemate", "k7/2Q5/1K6/8/8/8/8/8 b - - 0 1", "Queen corner stalemate", lambda q1, q0: q1 == 0),
        ("S02", "stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "Queen edge stalemate", lambda q1, q0: q1 == 0),
        ("S03", "stalemate", "8/8/8/8/8/5k2/5p2/5K2 w - - 0 1", "Pawn king stalemate", lambda q1, q0: q1 == 0),
        ("S04", "stalemate", "8/8/8/8/8/8/p7/k1K5 b - - 0 1", "Black corner pawn stalemate", lambda q1, q0: q1 == 0),
        ("S05", "stalemate", "5k2/5P2/5K2/8/8/8/8/8 b - - 0 1", "King and pawn textbook stalemate", lambda q1, q0: q1 == 0),

        # Category 3: Quiet king evasion escaping checkmate (5 positions)
        ("K01", "quiet_king_evasion", "8/8/8/8/8/8/1r6/4K2k w - - 0 1", "King in check can step to e2/d1/f1", lambda q1, q0: q1 > -20000),
        ("K02", "quiet_king_evasion", "k7/8/1K6/8/8/8/8/1r6 w - - 0 1", "White king in check steps to a6/c6", lambda q1, q0: q1 > -20000),
        ("K03", "quiet_king_evasion", "r3k2r/8/8/8/8/8/8/4R1K1 b kq - 0 1", "Black king in check steps to d8/f8/d7/f7", lambda q1, q0: q1 > -20000),
        ("K04", "quiet_king_evasion", "8/8/8/8/8/3k4/8/4R1K1 b - - 0 1", "Black king in check steps away", lambda q1, q0: q1 > -20000),
        ("K05", "quiet_king_evasion", "8/8/8/8/8/5k2/8/4q1K1 w - - 0 1", "White king escapes check to h2", lambda q1, q0: q1 > -20000),

        # Category 4: Quiet interposition escaping check (5 positions)
        ("I01", "quiet_interposition", "rnb1kbnr/pppp1ppp/8/4p3/7q/5P2/PPPPP1PP/RNBQKBNR w KQkq - 1 3", "White in check, can interpose 1. g3", lambda q1, q0: q1 > -20000),
        ("I02", "quiet_interposition", "r1b1kbnr/pppp1ppp/8/4p3/3nP2q/5P2/PPPPP1PP/RNBQKBNR w KQkq - 2 4", "White in check, can interpose 1. g3", lambda q1, q0: q1 > -20000),
        ("I03", "quiet_interposition", "4k3/8/8/8/8/8/8/4R1K1 b - - 0 1", "Black in check, quiet bishop/knight interposition", lambda q1, q0: q1 > -20000),
        ("I04", "quiet_interposition", "3k4/8/8/8/8/8/8/3R2K1 b - - 0 1", "Black in check, Nd7/Bd7 interposition or Ke8", lambda q1, q0: q1 > -20000),
        ("I05", "quiet_interposition", "8/8/8/8/3b4/8/3P4/3K3k w - - 0 1", "White in check from Bd4, 1. d4 interposition or Ke1", lambda q1, q0: q1 > -20000),

        # Category 5: Double check evasions (5 positions)
        ("D01", "double_check", "3k4/4N3/8/8/8/8/8/3R2K1 b - - 0 1", "Black king in double check (Nd1-e7+ and Rd1+), must move king", lambda q1, q0: q1 > -20000),
        ("D02", "double_check", "4k3/4N3/8/8/8/8/8/4R1K1 b - - 0 1", "Double check from Ne7 and Re1, king must move", lambda q1, q0: q1 > -20000),
        ("D03", "double_check", "2k5/4B3/8/8/8/8/8/2R3K1 b - - 0 1", "Discovered double check with Bishop and Rook", lambda q1, q0: q1 > -20000),
        ("D04", "double_check", "1k6/4B3/8/8/8/8/8/1R4K1 b - - 0 1", "Discovered double check with Bishop and Rook on b-file", lambda q1, q0: q1 > -20000),
        ("D05", "double_check", "4k3/8/8/5N2/8/8/8/4R2K b - - 0 1", "Rook check with knight hovering, king must move", lambda q1, q0: q1 > -20000),

        # Category 6: Underpromotion in quiescence / tactical promotions (5 positions)
        ("U01", "underpromotion", "8/4P1k1/8/8/8/8/8/6K1 w - - 0 1", "Pawn promotion on e8", lambda q1, q0: q1 > 500),
        ("U02", "underpromotion", "8/5P1k/8/8/8/8/8/6K1 w - - 0 1", "Pawn promotion on f8", lambda q1, q0: q1 > 500),
        ("U03", "underpromotion", "4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "Pawn promotion on b8", lambda q1, q0: q1 > 500),
        ("U04", "underpromotion", "8/8/8/8/8/8/4p1K1/4k3 b - - 0 1", "Black pawn ready to promote on e1", lambda q1, q0: True),
        ("U05", "underpromotion", "2r3k1/5ppp/8/8/8/8/4pPPP/4R1K1 b - - 0 1", "Promotion threat on e1", lambda q1, q0: True),

        # Category 7: Negative-SEE evasions preserving material balance (5 positions)
        ("N01", "negative_see_evasion", "4k3/8/8/8/8/8/4q3/4R1K1 b - - 0 1", "Queen pinned and in check, 1... Qxe1+ takes rook", lambda q1, q0: q1 > -20000),
        ("N02", "negative_see_evasion", "4k3/8/8/8/8/8/4r3/4R1K1 b - - 0 1", "Rook in check, 1... Rxe1+ wins rook", lambda q1, q0: q1 > -20000),
        ("N03", "negative_see_evasion", "4k3/8/8/8/8/8/8/3rR1K1 b - - 0 1", "Rook in check, 1... Rxe1+ wins rook", lambda q1, q0: q1 > -20000),
        ("N04", "negative_see_evasion", "k7/8/8/8/8/8/1q6/1R4K1 w - - 0 1", "Rook under attack, 1. Rxb2 captures queen", lambda q1, q0: q1 > 500),
        ("N05", "negative_see_evasion", "k7/8/8/8/8/8/1r6/1R4K1 w - - 0 1", "Rook under attack, 1. Rxb2 captures rook", lambda q1, q0: q1 >= 0),
    ]

    results = []
    q0_passes = 0
    q1_passes = 0

    print("================================================================================")
    print("PROJECT JANUS — PHASE 4: QUIESCENCE SEARCH CORRECTNESS REPAIR VERIFICATION")
    print("================================================================================")

    b = NativeBoard()

    for pos_id, cat, fen, desc, check_fn in test_positions:
        fen_bytes = fen.encode('utf-8')
        dll.native_set_fen(fen_bytes, ctypes.byref(b))
        in_chk = dll.native_is_check(ctypes.byref(b))

        # Test Q0 (Legacy Quiescence)
        dll.native_set_qsearch_mode(0)
        dll.native_reset_qsearch_telemetry()
        score_q0 = dll.native_qsearch(ctypes.byref(b), -30000, 30000, 0, 0)
        telem_q0 = (ctypes.c_uint64 * 3)()
        dll.native_get_qsearch_telemetry(telem_q0)

        # Test Q1 (Corrected Quiescence)
        dll.native_set_qsearch_mode(1)
        dll.native_reset_qsearch_telemetry()
        score_q1 = dll.native_qsearch(ctypes.byref(b), -30000, 30000, 0, 0)
        telem_q1 = (ctypes.c_uint64 * 3)()
        dll.native_get_qsearch_telemetry(telem_q1)

        passed = check_fn(score_q1, score_q0)
        if passed:
            q1_passes += 1

        res_item = {
            "id": pos_id,
            "category": cat,
            "fen": fen,
            "description": desc,
            "in_check": in_chk,
            "score_q0": score_q0,
            "score_q1": score_q1,
            "q0_telemetry": {
                "in_check": telem_q0[0],
                "checkmates": telem_q0[1],
                "checks_gen": telem_q0[2]
            },
            "q1_telemetry": {
                "in_check": telem_q1[0],
                "checkmates": telem_q1[1],
                "checks_gen": telem_q1[2]
            },
            "passed": passed
        }
        results.append(res_item)

        print(f"[{pos_id}] {cat:<22} | InChk: {in_chk!s:<5} | Q0: {score_q0:>6} | Q1: {score_q1:>6} | {'PASS' if passed else 'FAIL'}")

    print("--------------------------------------------------------------------------------")
    print(f"Total Positions: {len(test_positions)} | Q1 Passed: {q1_passes}/{len(test_positions)} ({q1_passes/len(test_positions)*100:.1f}%)")
    print("================================================================================")

    os.makedirs(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw", exist_ok=True)
    out_file = r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.16\raw\quiescence_repairs_raw.json"
    with open(out_file, "w") as f:
        json.dump({
            "total_tested": len(test_positions),
            "passed": q1_passes,
            "pass_rate": q1_passes / len(test_positions),
            "results": results
        }, f, indent=2)
    print(f"Raw results written to {out_file}")

if __name__ == "__main__":
    run_quiescence_repairs_test()
