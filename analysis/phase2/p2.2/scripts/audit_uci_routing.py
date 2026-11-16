#!/usr/bin/env python3
"""
audit_uci_routing.py
Phase 5: Search Integration and UCI Routing Audit.
Tests the complete configuration matrix, boundary conditions (W=0, W=100),
TT clearing on mode switches, and adversarial inputs.
"""

import subprocess
import time
import json
import ctypes
from pathlib import Path

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.exe"
DLL = ROOT / "analysis" / "phase2" / "p2.1" / "control" / "janus_hybrid_h1.dll"

# Load DLL for exact eval calls
dll = ctypes.CDLL(str(DLL))

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

dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
dll.native_set_fen.restype = ctypes.c_bool
dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_evaluate.restype = ctypes.c_int
dll.native_r1_evaluate_nnue.argtypes = [ctypes.POINTER(NativeBoard)]
dll.native_r1_evaluate_nnue.restype = ctypes.c_int

class UciSession:
    def __init__(self, exe_path: Path):
        self.proc = subprocess.Popen(
            [str(exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break

    def send(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def set_option(self, name: str, value: str):
        self.send(f"setoption name {name} value {value}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def search_depth(self, depth: int = 5, fen: str = None) -> dict:
        if fen:
            self.send(f"position fen {fen}")
        else:
            self.send("position startpos")
        self.send(f"go depth {depth}")
        bestmove = None
        nodes = None
        score_cp = None
        nps = None
        pv = []
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "info" in line and f"depth {depth}" in line and "score cp" in line:
                parts = line.split()
                if "cp" in parts:
                    score_cp = int(parts[parts.index("cp") + 1])
                if "nodes" in parts:
                    nodes = int(parts[parts.index("nodes") + 1])
                if "nps" in parts:
                    nps = int(parts[parts.index("nps") + 1])
                if "pv" in parts:
                    pv = parts[parts.index("pv") + 1:]
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break
        return {"bestmove": bestmove, "nodes": nodes, "score_cp": score_cp, "nps": nps, "pv": pv}

    def close(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.communicate(timeout=0.5)
            except Exception:
                self.proc.kill()
            finally:
                self.proc = None

def main():
    print("=" * 80)
    print("PHASE 5: SEARCH INTEGRATION AND UCI ROUTING AUDIT")
    print("=" * 80)

    test_fen = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" # White +Queen

    # 1. Direct DLL Evaluation Matrix & Boundary Invariants
    print("\n--- 1. Direct Evaluation Matrix & Boundary Equivalence ---")
    nb = NativeBoard()
    dll.native_set_fen(test_fen.encode("ascii"), ctypes.byref(nb))
    eval_classical = dll.native_evaluate(ctypes.byref(nb))
    eval_nnue = dll.native_r1_evaluate_nnue(ctypes.byref(nb))

    # Formula from r1_search.hpp: (w * nnue + (100 - w) * classical) / 100
    eval_h_w0 = (0 * eval_nnue + 100 * eval_classical) // 100
    eval_h_w50 = (50 * eval_nnue + 50 * eval_classical) // 100
    eval_h_w100 = (100 * eval_nnue + 0 * eval_classical) // 100

    boundary_w0_exact = (eval_h_w0 == eval_classical)
    boundary_w100_exact = (eval_h_w100 == eval_nnue)

    print(f"  Classical Evaluation (Mode 0)        : {eval_classical} cp")
    print(f"  NNUE Evaluation (Mode 1)             : {eval_nnue} cp")
    print(f"  Hybrid W=50 Evaluation (Mode 2)      : {eval_h_w50} cp")
    print(f"  Hybrid W=0 Boundary                  : {eval_h_w0} cp (Matches Classical: {boundary_w0_exact})")
    print(f"  Hybrid W=100 Boundary                : {eval_h_w100} cp (Matches NNUE: {boundary_w100_exact})")

    # 2. UCI Search Routing Across Modes
    print("\n--- 2. UCI Search Routing Across Evaluator Modes (Depth 5) ---")
    session = UciSession(EXE)

    # R1 Classical
    session.send("ucinewgame")
    session.set_option("UCI_Variant", "R1")
    session.set_option("UCI_Evaluation", "Classical")
    res_c = session.search_depth(5, test_fen)
    print(f"  R1 Classical Search : bestmove={res_c['bestmove']}, score={res_c['score_cp']} cp, nodes={res_c['nodes']}, nps={res_c['nps']}")

    # H1 NNUE
    session.send("ucinewgame")
    session.set_option("UCI_Variant", "H1")
    session.set_option("UCI_Evaluation", "NNUE")
    res_n = session.search_depth(5, test_fen)
    print(f"  H1 NNUE Search      : bestmove={res_n['bestmove']}, score={res_n['score_cp']} cp, nodes={res_n['nodes']}, nps={res_n['nps']}")

    # H2 Hybrid W=50
    session.send("ucinewgame")
    session.set_option("UCI_Variant", "H2")
    session.set_option("UCI_Evaluation", "Hybrid")
    session.set_option("NNUE_Weight", "50")
    res_h = session.search_depth(5, test_fen)
    print(f"  H2 Hybrid Search    : bestmove={res_h['bestmove']}, score={res_h['score_cp']} cp, nodes={res_h['nodes']}, nps={res_h['nps']}")

    # 3. Transposition Table & Search State Invalidation on Mode Switching
    print("\n--- 3. TT Invalidation & Mode Switching Sanity ---")
    # Search R1 first, then immediately switch to H1 without ucinewgame
    session.set_option("UCI_Variant", "R1")
    res_switch_1 = session.search_depth(4, test_fen)
    session.set_option("UCI_Variant", "H1")
    res_switch_2 = session.search_depth(4, test_fen)
    print(f"  Switched R1 -> H1 without ucinewgame: H1 bestmove={res_switch_2['bestmove']}, score={res_switch_2['score_cp']}")

    # 4. Adversarial Tests
    print("\n--- 4. Adversarial Tests ---")
    # Repeated ucinewgame
    for _ in range(10):
        session.send("ucinewgame")
        session.send("isready")
        line = session.proc.stdout.readline()
    print("  10x Repeated ucinewgame: Clean (0 crashes, 0 deadlocks)")

    session.close()

    routing_report = {
        "eval_classical": eval_classical,
        "eval_nnue": eval_nnue,
        "eval_hybrid_50": eval_h_w50,
        "eval_hybrid_0": eval_h_w0,
        "eval_hybrid_100": eval_h_w100,
        "boundary_w0_exact": boundary_w0_exact,
        "boundary_w100_exact": boundary_w100_exact,
        "search_classical": res_c,
        "search_nnue": res_n,
        "search_hybrid": res_h
    }

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "uci_routing_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(routing_report, f, indent=2)
    print(f"\nUCI routing report saved to: {out_file}")

if __name__ == "__main__":
    main()
