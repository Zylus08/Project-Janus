import subprocess
import time
import json
import os
import re

TEST_POSITIONS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
    "r1b1k2r/pppp1ppp/8/4n3/1b1NP2q/2N5/PPP2PPP/R1BQKB1R w KQkq - 1 8",
    "r1b2rk1/pp1p1ppp/2n1pn2/q5B1/1bPP4/2N2N2/PP2BPPP/R2QK2R w KQ - 3 9",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
]

def run_uci_command(exe, commands, timeout_sec=15):
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def test_pawn_hash_correctness(exe):
    # Test pawn hash consistency across make/unmake and en passant
    # Using UCI move sequences
    moves_seq = "position startpos moves e2e4 e7e5 g1f3 b8c6 d2d4 e5d4 c2c3 d4c3 f1c4 c3b2 c1b2 d7d6"
    cmd = f"uci\nisready\n{moves_seq}\ngo depth 6\nquit\n"
    out = run_uci_command(exe, cmd)
    nodes = 0
    score = 0
    for line in out.splitlines():
        if "info depth 6" in line:
            m_nodes = re.search(r'nodes (\d+)', line)
            m_score = re.search(r'score cp (-?\d+)', line)
            if m_nodes: nodes = int(m_nodes.group(1))
            if m_score: score = int(m_score.group(1))
    
    # En passant sequence
    ep_seq = "position startpos moves e2e4 g8f6 e4e5 d7d5"
    cmd_ep = f"uci\nisready\n{ep_seq}\ngo depth 6\nquit\n"
    out_ep = run_uci_command(exe, cmd_ep)
    ep_nodes = 0
    for line in out_ep.splitlines():
        if "info depth 6" in line:
            m_nodes = re.search(r'nodes (\d+)', line)
            if m_nodes: ep_nodes = int(m_nodes.group(1))

    return {
        "regular_nodes": nodes,
        "regular_score": score,
        "ep_nodes": ep_nodes,
        "pawn_hash_stable": (nodes > 0 and ep_nodes > 0)
    }

def benchmark_variant(exe, var_name, movetime_ms=1000):
    total_nodes = 0
    total_depth = 0
    start_time = time.time()
    
    for fen in TEST_POSITIONS:
        cmds = f"uci\nsetoption name UCI_Variant value {var_name}\nisready\nposition fen {fen}\ngo movetime {movetime_ms}\nquit\n"
        out = run_uci_command(exe, cmds, timeout_sec=10)
        
        last_d = 0
        last_n = 0
        for line in out.splitlines():
            if "info depth" in line and "score cp" in line:
                m_d = re.search(r'depth (\d+)', line)
                m_n = re.search(r'nodes (\d+)', line)
                if m_d: last_d = int(m_d.group(1))
                if m_n: last_n = int(m_n.group(1))
        total_depth += last_d
        total_nodes += last_n

    elapsed = time.time() - start_time
    avg_depth = total_depth / len(TEST_POSITIONS)
    avg_nps = int(total_nodes / elapsed) if elapsed > 0 else 0

    return {
        "variant": var_name,
        "positions": len(TEST_POSITIONS),
        "total_nodes": total_nodes,
        "elapsed_sec": elapsed,
        "avg_depth": avg_depth,
        "effective_nps": avg_nps
    }

def main():
    exe = "E:/ChessXML/project-janus-phase1/engine/classical_x/janus_classical_x.exe"
    
    print("1. Auditing Pawn Hash correctness...")
    pawn_audit = test_pawn_hash_correctness(exe)
    print("Pawn Hash Audit:", pawn_audit)
    
    print("\n2. Benchmarking Evaluation Variants...")
    # Compare X7 (Baseline E5), X9 (M2 + E5), X10 (E10 + Pawn Hash + Dynamic Time)
    bench_x7 = benchmark_variant(exe, "X7", movetime_ms=1000)
    print("X7 Baseline:", bench_x7)
    
    bench_x9 = benchmark_variant(exe, "X9", movetime_ms=1000)
    print("X9 Recovery:", bench_x9)
    
    bench_x10 = benchmark_variant(exe, "X10", movetime_ms=1000)
    print("X10 Candidate:", bench_x10)

    results = {
        "pawn_hash_correctness": pawn_audit,
        "benchmarks": {
            "X7": bench_x7,
            "X9": bench_x9,
            "X10": bench_x10
        },
        "depth_delta_x10_vs_x7": bench_x10["avg_depth"] - bench_x7["avg_depth"],
        "nps_ratio_x10_vs_x7": bench_x10["effective_nps"] / bench_x7["effective_nps"] if bench_x7["effective_nps"] > 0 else 1.0
    }

    out_file = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.5/raw/evaluation_efficiency_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw results written to {out_file}")

if __name__ == "__main__":
    main()

