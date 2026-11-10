import subprocess
import time
import json
import os
import re

TEST_SUITE = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
    "r1b1k2r/pppp1ppp/8/4n3/1b1NP2q/2N5/PPP2PPP/R1BQKB1R w KQkq - 1 8",
    "r1b2rk1/pp1p1ppp/2n1pn2/q5B1/1bPP4/2N2N2/PP2BPPP/R2QK2R w KQ - 3 9",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r1bq1rk1/pp1n1ppp/4pn2/2pp4/3P4/2NBPN2/PPP2PPP/R1BQ1RK1 w - - 0 9",
    "2r2rk1/1p1q1ppp/p3pn2/3p4/3P4/bP1BP3/P2B1PPP/R2Q1RK1 w - - 0 15",
    "r1b1kb1r/ppp2ppp/2p5/4Pn2/8/5N2/PPP2PPP/RNB2RK1 w kq - 0 9"
]

def run_config(exe, options, movetime_ms=1000):
    total_nodes = 0
    total_depth = 0
    start_time = time.time()
    
    for fen in TEST_SUITE:
        cmds = "uci\n"
        for k, v in options.items():
            cmds += f"setoption name {k} value {v}\n"
        cmds += "isready\n"
        cmds += f"position fen {fen}\n"
        cmds += f"go movetime {movetime_ms}\n"
        cmds += "quit\n"
        
        p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = p.communicate(cmds, timeout=10)
        
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
    avg_d = total_depth / len(TEST_SUITE)
    nps = int(total_nodes / elapsed) if elapsed > 0 else 0
    return {
        "nodes": total_nodes,
        "elapsed_sec": elapsed,
        "avg_depth": avg_d,
        "nps": nps
    }

def main():
    exe = "E:/ChessXML/project-janus-phase1/engine/classical_x/janus_classical_x.exe"
    results = {}

    print("Running Phase 6 Factorial Ablations across 8 benchmark positions...")

    # Principal Configurations
    configs = {
        "B0_Frozen_X7": {"UCI_Variant": "X7"},
        "B1_Eval_Only": {"UCI_Variant": "X10", "UCI_DynamicTime": "false"},
        "B2_Time_Only": {"UCI_Variant": "X7", "UCI_DynamicTime": "true"},
        "B3_Full_X10":  {"UCI_Variant": "X10"},
        # Isolated Eval Configurations
        "E6_Pawn_Only": {"UCI_Variant": "X7", "UCI_ClassicalEval": "E6"},
        "E7_King_Only": {"UCI_Variant": "X7", "UCI_ClassicalEval": "E7"},
        "E8_Mob_Only":  {"UCI_Variant": "X7", "UCI_ClassicalEval": "E8"},
        "E9_Endgame_Only": {"UCI_Variant": "X7", "UCI_ClassicalEval": "E9"},
        "E10_Combined_Eval": {"UCI_Variant": "X7", "UCI_ClassicalEval": "E10"}
    }

    for name, opts in configs.items():
        t0 = time.time()
        res = run_config(exe, opts, movetime_ms=500)
        results[name] = res
        print(f"[{name:18s}] Avg Depth: {res['avg_depth']:.2f} | Nodes: {res['nodes']:,} | NPS: {res['nps']:,} ({res['elapsed_sec']:.2f}s)")

    out_file = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.5/raw/factorial_ablation_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAblation results written to {out_file}")

if __name__ == "__main__":
    main()

