import os
import json
import ctypes
from pathlib import Path

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.14" / "raw" / "quiet_move_cutoff_economics_raw.json"

TEST_POSITIONS = [
    # 1. Tactical Middlegame
    {"id": "tactical_1", "category": "tactical_middlegame", "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"},
    {"id": "tactical_2", "category": "tactical_middlegame", "fen": "r1b2rk1/pp1p1ppp/2n1pn2/q1b5/2P5/2N1PN2/PP1B1PPP/R2QKB1R w KQ - 3 8"},
    # 2. Quiet Middlegame
    {"id": "quiet_1", "category": "quiet_middlegame", "fen": "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8"},
    {"id": "quiet_2", "category": "quiet_middlegame", "fen": "r2q1rk1/1bp1bppp/p1np1n2/1p2p3/4P3/1B1P1N2/PPP2PPP/RNBQR1K1 w - - 0 10"},
    # 3. Open Position
    {"id": "open_1", "category": "open_position", "fen": "r1b1k2r/ppp2ppp/2n5/3qp3/1b1P4/5N2/PPP2PPP/R1BQKB1R w KQkq - 1 8"},
    {"id": "open_2", "category": "open_position", "fen": "r2q1rk1/ppp2ppp/2np1n2/4p3/1b1PP1b1/2NB1N2/PPP2PPP/R1BQ1RK1 w - - 2 8"},
    # 4. Closed Position
    {"id": "closed_1", "category": "closed_position", "fen": "r1bqr1k1/pp1n1pbp/2pp1np1/4p3/2PPP3/2N1BN2/PP2BPPP/R2Q1RK1 w - - 0 10"},
    {"id": "closed_2", "category": "closed_position", "fen": "rnbq1rk1/pp2ppbp/3p1np1/8/2PNP3/2N1B3/PP3PPP/R2QKB1R w KQ - 0 8"},
    # 5. Queenless Position
    {"id": "queenless_1", "category": "queenless_position", "fen": "r1b1k2r/ppp2ppp/2n5/4p3/1b1P4/5N2/PPP2PPP/R1B1KB1R w KQkq - 1 8"},
    {"id": "queenless_2", "category": "queenless_position", "fen": "r4rk1/pp2bppp/2n1pn2/2p5/2PP4/2N1PN2/PP2BPPP/R4RK1 w - - 0 10"},
    # 6. Endgame
    {"id": "endgame_1", "category": "endgame", "fen": "8/5pk1/p4p2/1p6/1P4P1/P4PK1/8/8 w - - 0 40"},
    {"id": "endgame_2", "category": "endgame", "fen": "8/2p2pk1/p1p2p2/8/1P4P1/P4PK1/8/8 w - - 0 42"},
    # 7. Difficult Defensive Position
    {"id": "defensive_1", "category": "defensive_position", "fen": "r1b2rk1/ppqn1ppp/2p1p3/3p4/2PP4/1PN1PN2/P1Q2PPP/R3KB1R w KQ - 1 11"},
    {"id": "defensive_2", "category": "defensive_position", "fen": "r2q1rk1/ppp2pbp/3p2p1/3Pn3/2P5/1PN1B3/P4PPP/R2Q1RK1 w - - 0 14"}
]

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_uint8),
        ('castling_rights', ctypes.c_uint8),
        ('ep_square', ctypes.c_uint8),
        ('halfmove_clock', ctypes.c_uint16),
        ('fullmove_number', ctypes.c_uint16),
        ('zobrist_key', ctypes.c_uint64)
    ]

class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ('best_move', ctypes.c_uint16),
        ('score', ctypes.c_int),
        ('depth', ctypes.c_int),
        ('nodes', ctypes.c_uint64),
        ('elapsed_seconds', ctypes.c_double),
        ('pv_length', ctypes.c_int),
        ('pv', ctypes.c_uint16 * 128)
    ]

def run_telemetry_audit():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    results = []

    configs = [
        ("X7_1T", b"X7", 1),
        ("X12_4T", b"X12", 4)
    ]

    for cname, variant, threads in configs:
        dll.native_apply_search_variant(variant)
        
        for pos in TEST_POSITIONS:
            for depth in [6, 8]:
                board = NativeBoard()
                dll.native_set_fen(pos["fen"].encode('utf-8'), ctypes.byref(board))
                dll.native_reset_ordering_telemetry()
                
                res = NativeSearchResult()
                dll.native_search(ctypes.byref(board), depth, 5.0, ctypes.byref(res))
                
                telemetry = (ctypes.c_uint64 * 16)()
                dll.native_get_ordering_telemetry(telemetry)
                
                total_cutoffs = telemetry[0]
                sum_index = telemetry[1]
                m1 = telemetry[2]
                m2 = telemetry[3]
                m3 = telemetry[4]
                m4plus = telemetry[5]
                tt = telemetry[6]
                k1 = telemetry[7]
                k2 = telemetry[8]
                hist = telemetry[9]
                caps = telemetry[10]
                quiets = telemetry[11]
                
                avg_index = (sum_index / total_cutoffs) if total_cutoffs > 0 else 0.0
                bf1_pct = (m1 / total_cutoffs * 100.0) if total_cutoffs > 0 else 0.0
                
                entry = {
                    "config": cname,
                    "id": pos["id"],
                    "category": pos["category"],
                    "depth": depth,
                    "nodes": res.nodes,
                    "time_s": res.elapsed_seconds,
                    "score": res.score,
                    "total_cutoffs": total_cutoffs,
                    "avg_cutoff_index": avg_index,
                    "bf1_pct": bf1_pct,
                    "cutoffs_move_1": m1,
                    "cutoffs_move_2": m2,
                    "cutoffs_move_3": m3,
                    "cutoffs_move_4plus": m4plus,
                    "cutoffs_tt": tt,
                    "cutoffs_killer1": k1,
                    "cutoffs_killer2": k2,
                    "cutoffs_history": hist,
                    "cutoffs_captures": caps,
                    "cutoffs_quiets": quiets
                }
                results.append(entry)

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Recorded {len(results)} ordering economics profiles to {RAW_OUT}")

if __name__ == "__main__":
    run_telemetry_audit()

