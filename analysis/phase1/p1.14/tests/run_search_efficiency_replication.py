import os
import json
import time
import math
import subprocess
from pathlib import Path

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.14" / "raw" / "search_efficiency_replication_raw.json"

EXE_X7 = ROOT / "analysis" / "phase1" / "p1.3" / "control" / "janus_classical_x7.exe"
EXE_X12 = ROOT / "analysis" / "phase1" / "p1.7" / "control" / "janus_classical_x12.exe"
EXE_SF4 = Path(r"E:\ChessXML\tools\stockfish_4\stockfish_4.exe")
EXE_SF11 = Path(r"E:\ChessXML\tools\stockfish_11\stockfish_11.exe")

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

class UciRunner:
    def __init__(self, exe_path, threads=1, is_x7=False, variant=""):
        self.exe_path = exe_path
        self.threads = threads
        self.is_x7 = is_x7
        self.variant = variant
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        if not self.is_x7:
            if self.threads > 1:
                self.send(f"setoption name Threads value {self.threads}")
            if self.variant:
                self.send(f"setoption name Variant value {self.variant}")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def search_depth(self, fen, target_depth):
        self.send(f"position fen {fen}")
        t0 = time.time()
        self.send(f"go depth {target_depth}")
        
        last_info = {}
        depth_info = {}
        bm = None
        
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("info "):
                tokens = line.split()
                cur_d = None
                cur_nodes = None
                cur_time = None
                cur_nps = None
                cur_score = None
                cur_pv = []
                for i in range(len(tokens)):
                    if tokens[i] == "depth" and i+1 < len(tokens):
                        cur_d = int(tokens[i+1])
                    elif tokens[i] == "nodes" and i+1 < len(tokens):
                        cur_nodes = int(tokens[i+1])
                    elif tokens[i] == "time" and i+1 < len(tokens):
                        cur_time = int(tokens[i+1])
                    elif tokens[i] == "nps" and i+1 < len(tokens):
                        cur_nps = int(tokens[i+1])
                    elif tokens[i] == "cp" and i+1 < len(tokens):
                        cur_score = int(tokens[i+1])
                    elif tokens[i] == "pv":
                        cur_pv = tokens[i+1:]
                if cur_d is not None:
                    depth_info[cur_d] = {
                        "depth": cur_d,
                        "nodes": cur_nodes,
                        "time_ms": cur_time,
                        "nps": cur_nps,
                        "score_cp": cur_score,
                        "pv": cur_pv
                    }
                    last_info = depth_info[cur_d]
            elif line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) >= 2:
                    bm = tokens[1]
                break
                
        elapsed = time.time() - t0
        return {
            "fen": fen,
            "target_depth": target_depth,
            "actual_depth": last_info.get("depth", target_depth),
            "nodes": last_info.get("nodes", 0),
            "time_ms": last_info.get("time_ms", int(elapsed * 1000)),
            "nps": last_info.get("nps", 0),
            "score_cp": last_info.get("score_cp", 0),
            "bestmove": bm,
            "depth_progression": depth_info,
            "wall_clock_s": elapsed
        }

    def search_time(self, fen, movetime_ms):
        self.send(f"position fen {fen}")
        t0 = time.time()
        self.send(f"go movetime {movetime_ms}")
        
        last_info = {}
        depth_info = {}
        bm = None
        
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("info "):
                tokens = line.split()
                cur_d = None
                cur_nodes = None
                cur_time = None
                cur_nps = None
                cur_score = None
                cur_pv = []
                for i in range(len(tokens)):
                    if tokens[i] == "depth" and i+1 < len(tokens):
                        cur_d = int(tokens[i+1])
                    elif tokens[i] == "nodes" and i+1 < len(tokens):
                        cur_nodes = int(tokens[i+1])
                    elif tokens[i] == "time" and i+1 < len(tokens):
                        cur_time = int(tokens[i+1])
                    elif tokens[i] == "nps" and i+1 < len(tokens):
                        cur_nps = int(tokens[i+1])
                    elif tokens[i] == "cp" and i+1 < len(tokens):
                        cur_score = int(tokens[i+1])
                    elif tokens[i] == "pv":
                        cur_pv = tokens[i+1:]
                if cur_d is not None:
                    depth_info[cur_d] = {
                        "depth": cur_d,
                        "nodes": cur_nodes,
                        "time_ms": cur_time,
                        "nps": cur_nps,
                        "score_cp": cur_score,
                        "pv": cur_pv
                    }
                    last_info = depth_info[cur_d]
            elif line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) >= 2:
                    bm = tokens[1]
                break
                
        elapsed = time.time() - t0
        return {
            "fen": fen,
            "movetime_ms": movetime_ms,
            "completed_depth": last_info.get("depth", 0),
            "nodes": last_info.get("nodes", 0),
            "time_ms": last_info.get("time_ms", int(elapsed * 1000)),
            "nps": last_info.get("nps", 0),
            "score_cp": last_info.get("score_cp", 0),
            "bestmove": bm,
            "depth_progression": depth_info,
            "wall_clock_s": elapsed
        }

    def close(self):
        try:
            self.send("quit")
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()
        self.proc = None

def main():
    configs = [
        {"name": "Janus-X7-1T", "exe": EXE_X7, "threads": 1, "is_x7": True, "variant": ""},
        {"name": "Janus-X12-4T", "exe": EXE_X12, "threads": 4, "is_x7": False, "variant": "X12"},
        {"name": "Stockfish-4-1T", "exe": EXE_SF4, "threads": 1, "is_x7": False, "variant": ""},
        {"name": "Stockfish-11-1T", "exe": EXE_SF11, "threads": 1, "is_x7": False, "variant": ""}
    ]

    all_data = {"fixed_depth_8": {}, "fixed_time_1000ms": {}}

    for cfg in configs:
        cname = cfg["name"]
        print(f"Running search efficiency tests for {cname}...", flush=True)
        runner = UciRunner(cfg["exe"], threads=cfg["threads"], is_x7=cfg["is_x7"], variant=cfg["variant"])
        runner.start()
        
        all_data["fixed_depth_8"][cname] = []
        all_data["fixed_time_1000ms"][cname] = []
        
        for pos in TEST_POSITIONS:
            # 1. Fixed depth 8
            res_d8 = runner.search_depth(pos["fen"], target_depth=8)
            res_d8["id"] = pos["id"]
            res_d8["category"] = pos["category"]
            all_data["fixed_depth_8"][cname].append(res_d8)
            
            # 2. Fixed time 1000ms
            res_t1000 = runner.search_time(pos["fen"], movetime_ms=1000)
            res_t1000["id"] = pos["id"]
            res_t1000["category"] = pos["category"]
            all_data["fixed_time_1000ms"][cname].append(res_t1000)
            
        runner.close()

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"Benchmark completed. Data saved to {RAW_OUT}")

if __name__ == "__main__":
    main()
