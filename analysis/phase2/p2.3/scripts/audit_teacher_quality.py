import os
import sys
import json
import time
import subprocess
import chess

REPO_ROOT = r"E:\ChessXML\project-janus-phase1"
R1_EXE = os.path.join(REPO_ROOT, "analysis/phase1/p1.22/control/janus_classical_r1.exe")
X22_EXE = os.path.join(REPO_ROOT, "analysis/phase1/p1.17/control/janus_classical_x22.exe")

class SimpleUciSession:
    def __init__(self, exe_path, options=None):
        self.proc = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        if options:
            for k, v in options.items():
                self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def evaluate_depth(self, fen, depth):
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        score_cp = 0
        mate_score = None
        nodes = 0
        elapsed_ms = 0
        
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if f"depth {depth}" in line and "score" in line:
                parts = line.split()
                if "cp" in parts:
                    idx = parts.index("cp")
                    score_cp = int(parts[idx + 1])
                elif "mate" in parts:
                    idx = parts.index("mate")
                    mate_score = int(parts[idx + 1])
                    score_cp = 2000 if mate_score > 0 else -2000
                if "nodes" in parts:
                    nodes = int(parts[parts.index("nodes") + 1])
                if "time" in parts:
                    elapsed_ms = int(parts[parts.index("time") + 1])
            if line.startswith("bestmove"):
                break
        return score_cp, mate_score, nodes, elapsed_ms

    def close(self):
        try:
            self.send("quit")
            self.proc.kill()
        except Exception:
            pass

def audit_teachers():
    print("=== PHASE 5: TEACHER SEARCH SCORE QUALITY AUDIT ===")
    
    # Curated diagnostic suite covering all phases
    positions = [
        # 1. Startpos & Opening
        ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "opening"),
        ("italian_game", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3", "opening"),
        ("french_defense", "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "opening"),
        ("sicilian_najdorf", "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6", "opening"),
        
        # 2. Tactical Middlegames & Pins
        ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "tactical"),
        ("hanging_piece", "r1bq1rk1/ppp2ppp/2np4/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 8", "middlegame"),
        ("f7_attack", "r1bqk2r/pppp1ppp/2n5/2b1p3/2B1P1n1/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5", "tactical"),
        ("tactical_sacrifice", "r1b2rk1/pp1p1ppp/2n1pn2/q1b5/2B1P3/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9", "tactical"),
        
        # 3. Positional & King Safety
        ("damaged_king_pawn_shield", "r1bq1rk1/pppp1p1p/2n3p1/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 8", "positional"),
        ("passed_pawn_middlegame", "r1bq1rk1/1pp2ppp/p1np4/4P3/2B5/2NP1N2/PPP2PPP/R1BQ1RK1 b - - 0 9", "positional"),
        
        # 4. Major / Minor Piece Endgames
        ("rook_endgame_lucena", "1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1", "endgame"),
        ("rook_endgame_philidor", "8/4k3/8/8/8/4R3/r7/4K3 b - - 0 1", "endgame"),
        ("bishop_endgame_opposite", "8/4k3/2b5/8/8/5B2/4K3/8 w - - 0 1", "endgame"),
        ("knight_endgame", "8/4k3/2n5/8/8/5N2/4K3/8 w - - 0 1", "endgame"),
        ("pawn_endgame_opposition", "8/8/8/4k3/8/4P3/4K3/8 w - - 0 1", "endgame"),
        ("drawn_kp_k", "8/8/8/8/4k3/8/4P3/4K3 w - - 0 1", "endgame"),
        ("queen_endgame", "8/4k3/8/4q3/4Q3/8/4K3/8 w - - 0 1", "endgame")
    ]
    
    t0_sess = SimpleUciSession(R1_EXE) # T0: R1 Depth 5
    t1_sess = SimpleUciSession(R1_EXE) # T1: R1 Depth 7
    t2_sess = SimpleUciSession(X22_EXE) # T2: X22 Depth 6
    
    audit_data = []
    
    try:
        for name, fen, phase in positions:
            # T0: R1 Depth 5
            cp_t0, mate_t0, nodes_t0, time_t0 = t0_sess.evaluate_depth(fen, 5)
            # T1: R1 Depth 7
            cp_t1, mate_t1, nodes_t1, time_t1 = t1_sess.evaluate_depth(fen, 7)
            # T2: X22 Depth 6
            cp_t2, mate_t2, nodes_t2, time_t2 = t2_sess.evaluate_depth(fen, 6)
            
            delta_t0_t1 = abs(cp_t1 - cp_t0)
            delta_r1_x22 = abs(cp_t1 - cp_t2)
            
            audit_data.append({
                "name": name,
                "phase": phase,
                "fen": fen,
                "T0_R1_D5": {"cp": cp_t0, "nodes": nodes_t0, "ms": time_t0},
                "T1_R1_D7": {"cp": cp_t1, "nodes": nodes_t1, "ms": time_t1},
                "T2_X22_D6": {"cp": cp_t2, "nodes": nodes_t2, "ms": time_t2},
                "stability_d5_d7": delta_t0_t1,
                "disagreement_r1_x22": delta_r1_x22
            })
            print(f"[{name:25s}] T0(D5): {cp_t0:+4d}cp | T1(D7): {cp_t1:+4d}cp (Δ={delta_t0_t1:2d}) | T2(X22): {cp_t2:+4d}cp (Δ={delta_r1_x22:2d})")
            
    finally:
        t0_sess.close()
        t1_sess.close()
        t2_sess.close()
        
    # Statistical analysis of teacher scores
    avg_delta_depth = sum(x["stability_d5_d7"] for x in audit_data) / len(audit_data)
    avg_delta_x22 = sum(x["disagreement_r1_x22"] for x in audit_data) / len(audit_data)
    avg_ms_t0 = sum(x["T0_R1_D5"]["ms"] for x in audit_data) / len(audit_data)
    avg_ms_t1 = sum(x["T1_R1_D7"]["ms"] for x in audit_data) / len(audit_data)
    avg_ms_t2 = sum(x["T2_X22_D6"]["ms"] for x in audit_data) / len(audit_data)
    
    print("\n--- TEACHER QUALITY AUDIT SUMMARY ---")
    print(f"Mean Score Shift with Depth (D5 -> D7): {avg_delta_depth:.1f} cp")
    print(f"Mean Disagreement between R1 and X22: {avg_delta_x22:.1f} cp")
    print(f"Average Runtime per Position: T0(D5)={avg_ms_t0:.1f}ms | T1(D7)={avg_ms_t1:.1f}ms | T2(D6)={avg_ms_t2:.1f}ms")
    
    report = {
        "positions_evaluated": len(audit_data),
        "mean_shift_d5_to_d7_cp": round(avg_delta_depth, 2),
        "mean_disagreement_r1_x22_cp": round(avg_delta_x22, 2),
        "timing_ms": {
            "T0_R1_D5": round(avg_ms_t0, 1),
            "T1_R1_D7": round(avg_ms_t1, 1),
            "T2_X22_D6": round(avg_ms_t2, 1)
        },
        "compute_budget_estimate_50k_positions_hours": round((50000 * (avg_ms_t0 / 1000.0)) / 3600.0, 2),
        "audit_data": audit_data
    }
    
    out_json = os.path.join(REPO_ROOT, "analysis/phase2/p2.3/raw/teacher_quality_audit.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Audit report saved to {out_json}")

if __name__ == "__main__":
    audit_teachers()
