"""Project Janus v0.51 - Native Fixed-Depth & Fixed-Time Benchmarks (Phase F).

Evaluates janus_native_engine.exe directly via standard UCI interface:
1. Fixed-Depth Benchmark (Depths 1 to 5):
   - Cold TT vs Warm TT execution
   - Median and mean runtime, nodes, NPS
2. Fixed-Time Ladder (7 Budget Tiers: 50, 100, 180, 250, 500, 1000, 3000 ms):
   - Actual wall-clock time and clock overshoot
   - Completed depth distribution
   - Effective throughput (NPS)
   - Stockfish 19 match rate comparison
"""

import sys
import json
import time
import subprocess
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
ENGINE_EXE = ROOT / "analysis" / "v0.51" / "native" / "janus_native_engine.exe"
DIAG_CORPUS_PATH = ROOT / "analysis" / "v0.50" / "corpus" / "diagnostic_corpus.json"
SF_LADDER_PATH = ROOT / "analysis" / "v0.50" / "reference" / "stockfish_reference_ladder.json"


class UCIBenchClient:
    def __init__(self, path: Path):
        self.p = subprocess.Popen(
            [str(path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self._handshake()

    def _handshake(self):
        self.p.stdin.write("uci\n")
        self.p.stdin.flush()
        while True:
            l = self.p.stdout.readline()
            if not l or l.strip() == "uciok":
                break
        self.p.stdin.write("isready\n")
        self.p.stdin.flush()
        while True:
            l = self.p.stdout.readline()
            if not l or l.strip() == "readyok":
                break

    def ucinewgame(self):
        self.p.stdin.write("ucinewgame\nisready\n")
        self.p.stdin.flush()
        while True:
            l = self.p.stdout.readline()
            if not l or l.strip() == "readyok":
                break

    def position_fen(self, fen: str):
        self.p.stdin.write(f"position fen {fen}\n")
        self.p.stdin.flush()

    def search_depth(self, depth: int):
        t0 = time.perf_counter()
        self.p.stdin.write(f"go depth {depth}\n")
        self.p.stdin.flush()
        bestmove = None
        nodes = 0
        score = 0
        nps = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("info"):
                parts = line.split()
                if "nodes" in parts:
                    idx = parts.index("nodes")
                    if idx + 1 < len(parts): nodes = int(parts[idx + 1])
                if "score" in parts and "cp" in parts:
                    idx = parts.index("cp")
                    if idx + 1 < len(parts): score = int(parts[idx + 1])
                if "nps" in parts:
                    idx = parts.index("nps")
                    if idx + 1 < len(parts): nps = int(parts[idx + 1])
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2: bestmove = parts[1]
                break
        elapsed = time.perf_counter() - t0
        return bestmove, score, nodes, nps, elapsed

    def search_time(self, movetime_ms: int):
        t0 = time.perf_counter()
        self.p.stdin.write(f"go movetime {movetime_ms}\n")
        self.p.stdin.flush()
        bestmove = None
        depth = 0
        nodes = 0
        score = 0
        nps = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("info"):
                parts = line.split()
                if "depth" in parts:
                    idx = parts.index("depth")
                    if idx + 1 < len(parts): depth = int(parts[idx + 1])
                if "nodes" in parts:
                    idx = parts.index("nodes")
                    if idx + 1 < len(parts): nodes = int(parts[idx + 1])
                if "score" in parts and "cp" in parts:
                    idx = parts.index("cp")
                    if idx + 1 < len(parts): score = int(parts[idx + 1])
                if "nps" in parts:
                    idx = parts.index("nps")
                    if idx + 1 < len(parts): nps = int(parts[idx + 1])
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2: bestmove = parts[1]
                break
        elapsed = time.perf_counter() - t0
        return bestmove, score, depth, nodes, nps, elapsed

    def quit(self):
        try:
            if self.p.poll() is None:
                self.p.stdin.write("quit\n")
                self.p.stdin.flush()
                self.p.wait(timeout=2)
            if self.p.stdin and not self.p.stdin.closed:
                self.p.stdin.close()
            if self.p.stdout and not self.p.stdout.closed:
                self.p.stdout.close()
        except Exception:
            self.p.kill()


def run_benchmarks():
    with open(DIAG_CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    with open(SF_LADDER_PATH, "r", encoding="utf-8") as f:
        sf_ladder = json.load(f)

    # 1. FIXED-DEPTH BENCHMARK (Cold vs Warm TT)
    print("=" * 80, flush=True)
    print("PHASE F1: NATIVE FIXED-DEPTH BENCHMARK (Cold vs Warm TT)", flush=True)
    print("=" * 80, flush=True)

    depth_results = {}
    client = UCIBenchClient(ENGINE_EXE)

    for depth in [1, 2, 3, 4, 5]:
        print(f"\n--- Testing Depth {depth} across 37 positions ---", flush=True)

        cold_times = []
        warm_times = []
        all_nodes = []
        pos_records = []

        for item in corpus:
            fen = item["fen"]
            pos_id = item["id"]

            # Cold TT run (clear TT before search)
            client.ucinewgame()
            client.position_fen(fen)
            mv_cold, sc_cold, nd_cold, nps_cold, t_cold = client.search_depth(depth)

            # Warm TT run (re-search same position immediately with populated TT)
            client.position_fen(fen)
            mv_warm, sc_warm, nd_warm, nps_warm, t_warm = client.search_depth(depth)

            cold_times.append(t_cold)
            warm_times.append(t_warm)
            all_nodes.append(nd_cold)

            pos_records.append({
                "id": pos_id,
                "fen": fen,
                "bestmove": mv_cold,
                "score": sc_cold,
                "nodes": nd_cold,
                "cold_time": t_cold,
                "warm_time": t_warm,
            })

        mean_cold = statistics.mean(cold_times)
        median_cold = statistics.median(cold_times)
        mean_warm = statistics.mean(warm_times)
        median_warm = statistics.median(warm_times)
        total_nodes = sum(all_nodes)
        effective_nps = int(total_nodes / sum(cold_times)) if sum(cold_times) > 0 else 0

        summary = {
            "depth": depth,
            "positions": len(corpus),
            "total_nodes": total_nodes,
            "effective_nps": effective_nps,
            "mean_cold_time_sec": round(mean_cold, 4),
            "median_cold_time_sec": round(median_cold, 4),
            "mean_warm_time_sec": round(mean_warm, 4),
            "median_warm_time_sec": round(median_warm, 4),
            "warmup_speedup_pct": round((mean_cold - mean_warm) / mean_cold * 100.0, 1) if mean_cold > 0 else 0.0,
            "records": pos_records
        }
        depth_results[str(depth)] = summary

        print(f"Depth {depth}: Nodes={total_nodes:,} | NPS={effective_nps:,} | "
              f"Cold Time (mean/med)={mean_cold*1000:.1f}ms / {median_cold*1000:.1f}ms | "
              f"Warm Time (mean/med)={mean_warm*1000:.1f}ms / {median_warm*1000:.1f}ms | "
              f"Warmup Speedup={summary['warmup_speedup_pct']}%", flush=True)

    client.quit()

    out_file_d = ROOT / "analysis" / "v0.51" / "raw" / "fixed_depth_benchmark_raw.json"
    with open(out_file_d, "w", encoding="utf-8") as f:
        json.dump(depth_results, f, indent=2)
    print(f"\nSaved fixed-depth raw data to {out_file_d}", flush=True)

    # 2. FIXED-TIME LADDER (7 Budget Tiers)
    print("\n" + "=" * 80, flush=True)
    print("PHASE F2: NATIVE FIXED-TIME LADDER (7 Budget Tiers)", flush=True)
    print("=" * 80, flush=True)

    tiers_ms = [50, 100, 180, 250, 500, 1000, 3000]
    time_results = {}
    client = UCIBenchClient(ENGINE_EXE)

    for budget_ms in tiers_ms:
        print(f"\n--- Testing Budget Tier: {budget_ms} ms ---", flush=True)

        depths = []
        nodes_list = []
        actual_times = []
        overshoots_ms = []
        sf_matches = 0
        records = []

        for item in corpus:
            fen = item["fen"]
            pos_id = item["id"]
            sf_ref = sf_ladder.get(pos_id, {})
            sf_move = sf_ref.get("reference_move_d14") or sf_ref.get("reference_move_d12")

            client.ucinewgame()
            client.position_fen(fen)
            mv, sc, dp, nd, nps, el = client.search_time(budget_ms)

            actual_ms = el * 1000.0
            overshoot = actual_ms - budget_ms

            depths.append(dp)
            nodes_list.append(nd)
            actual_times.append(el)
            overshoots_ms.append(overshoot)

            is_sf_match = (mv == sf_move) if mv and sf_move else False
            if is_sf_match:
                sf_matches += 1

            records.append({
                "id": pos_id,
                "fen": fen,
                "budget_ms": budget_ms,
                "bestmove": mv,
                "sf_move": sf_move,
                "sf_match": is_sf_match,
                "score": sc,
                "completed_depth": dp,
                "nodes": nd,
                "actual_time_ms": round(actual_ms, 1),
                "overshoot_ms": round(overshoot, 1)
            })

        n_pos = len(corpus)
        mean_depth = round(statistics.mean(depths), 2)
        total_nodes = sum(nodes_list)
        total_time = sum(actual_times)
        effective_nps = int(total_nodes / total_time) if total_time > 0 else 0
        mean_overshoot = round(statistics.mean(overshoots_ms), 1)
        sf_pct = round(sf_matches / n_pos * 100.0, 1)

        summary = {
            "budget_ms": budget_ms,
            "positions": n_pos,
            "mean_completed_depth": mean_depth,
            "total_nodes": total_nodes,
            "mean_nodes_per_pos": int(total_nodes / n_pos),
            "effective_nps": effective_nps,
            "total_time_sec": round(total_time, 2),
            "mean_overshoot_ms": mean_overshoot,
            "sf_matches": sf_matches,
            "sf_match_pct": sf_pct,
            "records": records
        }
        time_results[str(budget_ms)] = summary

        print(f"Tier {budget_ms:4d}ms: Mean Depth={mean_depth:.2f} | NPS={effective_nps:,} | "
              f"SF Match={sf_matches}/{n_pos} ({sf_pct}%) | Mean Overshoot={mean_overshoot:+5.1f}ms", flush=True)

    client.quit()

    out_file_t = ROOT / "analysis" / "v0.51" / "raw" / "fixed_time_ladder_raw.json"
    with open(out_file_t, "w", encoding="utf-8") as f:
        json.dump(time_results, f, indent=2)
    print(f"\nSaved fixed-time ladder raw data to {out_file_t}", flush=True)


if __name__ == "__main__":
    run_benchmarks()

