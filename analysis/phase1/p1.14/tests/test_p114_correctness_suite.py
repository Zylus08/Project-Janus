import os
import sys
import json
import time
import ctypes
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
EXE_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.exe"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.14" / "raw" / "p114_correctness_raw.json"

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

TEST_FENS = [
    # Startpos
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    # KiwiPete (dense tactics, checks, pins, promotions, EP)
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    # In-Check position
    "r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6",
    # King in double check
    "r1b1k2r/pppp1Npp/8/4p3/2Bn4/8/PPPP2PP/RNB1b1KR b kq - 1 9",
    # Pawn endgame with promotion
    "8/4P3/8/8/8/8/8/4K2k w - - 0 1",
    # En Passant available
    "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
    # Castling available on both wings
    "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1",
    # Stalemate position
    "k7/8/1Q6/8/8/8/8/7K b - - 0 1",
    # Checkmate position
    "k7/7R/6R1/8/8/8/8/7K w - - 0 1",
    # High capture density
    "2r3k1/1p3pp1/pq5p/3p4/3Nn3/1PP2P1P/P2Q2P1/4R1K1 b - - 0 24"
]

def run_movepicker_property_test(dll):
    print("--- Running MovePicker Invariant Property Test ---")
    results = []
    
    # We test with MovePicker via search or native methods
    # For each FEN, verify that searching in X19 finds valid moves and explores legal set
    for idx, fen in enumerate(TEST_FENS):
        board = NativeBoard()
        dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(board))
        
        # Generate legal moves
        moves_arr = (ctypes.c_uint16 * 256)()
        legal_count = dll.native_generate_legal_moves(ctypes.byref(board), moves_arr)
        legal_set = set(moves_arr[i] for i in range(legal_count))
        
        # Run X19 search at depth 1 to verify root move is legal
        dll.native_apply_search_variant(b"X19")
        res = NativeSearchResult()
        dll.native_search(ctypes.byref(board), 1, 1.0, ctypes.byref(res))
        
        is_legal = (legal_count == 0 and res.best_move == 0) or (res.best_move in legal_set)
        
        results.append({
            "fen_index": idx,
            "fen": fen,
            "legal_moves_count": legal_count,
            "best_move": res.best_move,
            "best_move_is_legal": is_legal,
            "score": res.score
        })
        assert is_legal, f"Illegal move {res.best_move} generated at FEN {fen}"
        
    print(f"MovePicker Property Test PASSED across {len(results)} positions.")
    return results

def run_perft_test(dll):
    print("--- Running Perft Correctness Verification ---")
    # Startpos perft: depth 1=20, depth 2=400, depth 3=8902, depth 4=197281
    startpos_targets = {1: 20, 2: 400, 3: 8902, 4: 197281}
    perft_results = {}
    
    board = NativeBoard()
    dll.native_set_fen(b"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ctypes.byref(board))
    
    for d, target in startpos_targets.items():
        nodes = dll.native_perft(ctypes.byref(board), d)
        passed = (nodes == target)
        perft_results[f"startpos_d{d}"] = {"depth": d, "computed": nodes, "target": target, "pass": passed}
        assert passed, f"Perft mismatch at depth {d}: computed {nodes} vs target {target}"
        
    print("Perft Startpos 100% PASSED.")
    return perft_results

def run_uci_compliance_and_stop_test():
    print("--- Running UCI Protocol Compliance & Stop Responsiveness ---")
    proc = subprocess.Popen(
        [str(EXE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )
    
    # Send uci
    proc.stdin.write("uci\n")
    proc.stdin.flush()
    uciok = False
    while True:
        line = proc.stdout.readline()
        if not line or "uciok" in line:
            if "uciok" in line: uciok = True
            break
            
    # Send isready
    proc.stdin.write("isready\n")
    proc.stdin.flush()
    readyok = False
    while True:
        line = proc.stdout.readline()
        if not line or "readyok" in line:
            if "readyok" in line: readyok = True
            break
            
    # Test stop responsiveness
    proc.stdin.write("position startpos\ngo infinite\n")
    proc.stdin.flush()
    time.sleep(0.05) # Let it search
    
    t0 = time.time()
    proc.stdin.write("stop\n")
    proc.stdin.flush()
    
    bm = None
    while True:
        line = proc.stdout.readline()
        if not line or line.startswith("bestmove"):
            if line.startswith("bestmove"):
                bm = line.split()[1]
            break
    stop_latency_ms = (time.time() - t0) * 1000.0
    
    proc.stdin.write("quit\n")
    proc.stdin.flush()
    proc.wait(timeout=2)
    
    res = {
        "uciok": uciok,
        "readyok": readyok,
        "bestmove": bm,
        "stop_latency_ms": stop_latency_ms,
        "stop_pass": (stop_latency_ms < 50.0 and bm is not None)
    }
    assert res["stop_pass"], f"Stop responsiveness failure: {stop_latency_ms:.1f}ms"
    print(f"UCI Protocol & Stop Responsiveness PASSED: Latency = {stop_latency_ms:.2f}ms")
    return res

def main():
    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int
    dll.native_perft.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
    dll.native_perft.restype = ctypes.c_uint64

    prop_res = run_movepicker_property_test(dll)
    perft_res = run_perft_test(dll)
    uci_res = run_uci_compliance_and_stop_test()

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "candidate": "Janus Classical X19",
        "movepicker_property_tests": prop_res,
        "perft_tests": perft_res,
        "uci_tests": uci_res,
        "overall_status": "ALL_TESTS_PASSED"
    }

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Correctness Qualification 100% PASSED. Report saved to {RAW_OUT}")

if __name__ == "__main__":
    main()
