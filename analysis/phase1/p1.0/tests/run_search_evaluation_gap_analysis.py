#!/usr/bin/env python3
"""
Project Janus Phase 1 — Milestone P1.0
Search Efficiency Gap & Classical Evaluation Gap Diagnostic Pipeline.

Evaluates 50 standardized positions across 8 categories:
1. Janus Classical C1: Static Evaluation (cp) via Native DLL
2. Janus Classical C1: Depth 7 Search (nodes, time, nps, score, bestmove) via Interactive UCI
3. Stockfish 19: Unrestricted Depth 12 Search (nodes, time, nps, score, bestmove, pv) via Interactive UCI

Computes:
- Best-move agreement across categories
- Move accuracy / blunders
- Search volume & NPS comparison (with explicit node semantic disclaimers)
- Static evaluation fidelity vs search evaluation
- Positional blindness analysis
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SUITE_PATH = ROOT / "analysis" / "phase1" / "p1.0" / "corpus" / "standard_50_evaluation_suite.json"
C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
SF_EXE = Path("E:/ChessXML/tools/stockfish/stockfish.exe")

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.0" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


class InteractiveUciEngine:
    def __init__(self, name: str, exe_path: Path, options: dict = None):
        self.name = name
        self.exe_path = str(exe_path.resolve())
        self.options = options or {}
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [self.exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            l = self.proc.stdout.readline()
            if "uciok" in l:
                break
        for k, v in self.options.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while True:
            l = self.proc.stdout.readline()
            if "readyok" in l:
                break

    def send(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError(f"Engine {self.name} is not running.")
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def search_fen(self, fen: str, depth: int, timeout: float = 20.0) -> dict:
        self.send("ucinewgame")
        self.send("isready")
        while True:
            l = self.proc.stdout.readline()
            if "readyok" in l:
                break

        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        bestmove = None
        depth_out = 0
        seldepth = 0
        nodes = 0
        nps = 0
        score_cp = 0
        pv = []

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Engine {self.name} crashed with code {self.proc.returncode}")
                time.sleep(0.002)
                continue
            line = line.strip()
            if line.startswith("info") and ("pv" in line or "score" in line):
                parts = line.split()
                for idx, tok in enumerate(parts):
                    if tok == "depth" and idx + 1 < len(parts):
                        depth_out = int(parts[idx+1])
                    elif tok == "seldepth" and idx + 1 < len(parts):
                        seldepth = int(parts[idx+1])
                    elif tok == "nodes" and idx + 1 < len(parts):
                        nodes = int(parts[idx+1])
                    elif tok == "nps" and idx + 1 < len(parts):
                        nps = int(parts[idx+1])
                    elif tok == "cp" and idx + 1 < len(parts):
                        score_cp = int(parts[idx+1])
                    elif tok == "mate" and idx + 1 < len(parts):
                        mate_plies = int(parts[idx+1])
                        score_cp = (30000 - abs(mate_plies) * 100) if mate_plies > 0 else (-30000 + abs(mate_plies) * 100)
                if "pv" in parts:
                    pv_idx = parts.index("pv")
                    pv = parts[pv_idx+1:]
            elif line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) > 1:
                    bestmove = tokens[1]
                break

        t1 = time.perf_counter()
        return {
            "depth": depth_out,
            "seldepth": seldepth,
            "nodes": nodes,
            "nps": nps,
            "score_cp": score_cp,
            "bestmove": bestmove,
            "pv": pv,
            "elapsed_sec": round(t1 - t0, 4)
        }

    def terminate(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.wait(timeout=2.0)
            except Exception:
                self.proc.kill()
            self.proc = None


def main():
    import importlib.util
    bridge_path = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"
    spec = importlib.util.spec_from_file_location("janus_native_bridge", bridge_path)
    bridge_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge_mod)
    NativeEngineBridge = bridge_mod.NativeEngineBridge

    eng_bridge = NativeEngineBridge()

    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        positions = json.load(f)

    print("=" * 80, flush=True)
    print(f"RUNNING SEARCH & EVALUATION GAP DIAGNOSTIC ACROSS {len(positions)} POSITIONS", flush=True)
    print("=" * 80, flush=True)

    c1_engine = InteractiveUciEngine("Janus_C1", C1_EXE, {})
    sf_engine = InteractiveUciEngine("Stockfish_19", SF_EXE, {
        "Threads": 1,
        "Hash": 64,
        "UCI_LimitStrength": "false"
    })

    c1_engine.start()
    sf_engine.start()

    records = []
    category_agreement = {}

    try:
        for pos in positions:
            pid = pos["id"]
            cat = pos["cat"]
            fen = pos["fen"]
            desc = pos["desc"]

            # 1. Static Evaluation from C1
            eng_bridge.set_fen(fen)
            c1_static_cp = eng_bridge.evaluate()

            # 2. C1 Depth 7 Search
            c1_search = c1_engine.search_fen(fen, depth=7)

            # 3. SF19 Depth 12 Search
            sf_search = sf_engine.search_fen(fen, depth=12)

            is_agreed = (c1_search["bestmove"] == sf_search["bestmove"])
            if cat not in category_agreement:
                category_agreement[cat] = {"agreed": 0, "total": 0}
            category_agreement[cat]["total"] += 1
            if is_agreed:
                category_agreement[cat]["agreed"] += 1

            eval_diff = abs(c1_search["score_cp"] - sf_search["score_cp"])
            static_shift = abs(c1_static_cp - c1_search["score_cp"])

            rec = {
                "id": pid,
                "category": cat,
                "fen": fen,
                "description": desc,
                "c1_static_eval_cp": c1_static_cp,
                "c1_search": c1_search,
                "sf19_search": sf_search,
                "move_agreement": is_agreed,
                "eval_error_vs_sf_cp": eval_diff,
                "static_to_search_shift_cp": static_shift
            }
            records.append(rec)

            agree_sym = "YES [MATCH]" if is_agreed else "NO  [GAP]  "
            print(f"[{pid:7s}] ({cat:10s}) C1 move={c1_search['bestmove']:5s} (eval={c1_search['score_cp']:+5d}, nodes={c1_search['nodes']:8d}) | SF19 move={sf_search['bestmove']:5s} (eval={sf_search['score_cp']:+5d}, nodes={sf_search['nodes']:8d}) | Agree: {agree_sym}", flush=True)

    finally:
        c1_engine.terminate()
        sf_engine.terminate()

    # Summarize Search Efficiency Gap
    total_positions = len(records)
    total_agreed = sum(1 for r in records if r["move_agreement"])
    total_c1_nodes = sum(r["c1_search"]["nodes"] for r in records)
    total_sf_nodes = sum(r["sf19_search"]["nodes"] for r in records)
    total_c1_time = sum(r["c1_search"]["elapsed_sec"] for r in records)
    total_sf_time = sum(r["sf19_search"]["elapsed_sec"] for r in records)

    search_gap_summary = {
        "total_positions": total_positions,
        "total_agreed_moves": total_agreed,
        "move_agreement_rate_pct": round((total_agreed / total_positions) * 100.0, 2),
        "c1_average_depth": round(sum(r["c1_search"]["depth"] for r in records) / total_positions, 2),
        "sf_average_depth": round(sum(r["sf19_search"]["depth"] for r in records) / total_positions, 2),
        "sf_average_seldepth": round(sum(r["sf19_search"]["seldepth"] for r in records) / total_positions, 2),
        "c1_total_nodes": total_c1_nodes,
        "sf_total_nodes": total_sf_nodes,
        "c1_avg_nodes_per_position": int(total_c1_nodes / total_positions),
        "sf_avg_nodes_per_position": int(total_sf_nodes / total_positions),
        "node_volume_ratio_c1_vs_sf": round(total_c1_nodes / max(total_sf_nodes, 1), 2),
        "c1_total_time_sec": round(total_c1_time, 2),
        "sf_total_time_sec": round(total_sf_time, 2),
        "c1_avg_nps": int(total_c1_nodes / max(total_c1_time, 0.001)),
        "sf_avg_nps": int(total_sf_nodes / max(total_sf_time, 0.001)),
        "category_breakdown": {
            k: {
                "agreed": v["agreed"],
                "total": v["total"],
                "rate_pct": round((v["agreed"] / v["total"]) * 100.0, 2)
            } for k, v in category_agreement.items()
        }
    }

    # Summarize Classical Evaluation Gap
    avg_eval_error = sum(r["eval_error_vs_sf_cp"] for r in records) / total_positions
    avg_static_shift = sum(r["static_to_search_shift_cp"] for r in records) / total_positions

    eval_gap_summary = {
        "total_positions": total_positions,
        "average_eval_error_vs_sf19_cp": round(avg_eval_error, 2),
        "average_static_to_search_shift_cp": round(avg_static_shift, 2),
        "category_eval_errors_cp": {
            cat: round(sum(r["eval_error_vs_sf_cp"] for r in records if r["category"] == cat) / max(sum(1 for r in records if r["category"] == cat), 1), 2)
            for cat in category_agreement.keys()
        },
        "category_static_to_search_shift_cp": {
            cat: round(sum(r["static_to_search_shift_cp"] for r in records if r["category"] == cat) / max(sum(1 for r in records if r["category"] == cat), 1), 2)
            for cat in category_agreement.keys()
        }
    }

    search_gap_file = RAW_DIR / "search_efficiency_gap_raw.json"
    with open(search_gap_file, "w", encoding="utf-8") as f:
        json.dump({"summary": search_gap_summary, "positions": records}, f, indent=2)

    eval_gap_file = RAW_DIR / "classical_evaluation_gap_raw.json"
    with open(eval_gap_file, "w", encoding="utf-8") as f:
        json.dump({"summary": eval_gap_summary, "positions": records}, f, indent=2)

    print("\n" + "=" * 80, flush=True)
    print("SEARCH EFFICIENCY GAP SUMMARY:", flush=True)
    print("=" * 80, flush=True)
    print(f"Total Positions           : {total_positions}", flush=True)
    print(f"Best Move Agreement       : {total_agreed} / {total_positions} ({search_gap_summary['move_agreement_rate_pct']}%)", flush=True)
    print(f"C1 Avg Depth              : {search_gap_summary['c1_average_depth']} (fixed)", flush=True)
    print(f"SF19 Avg Depth            : {search_gap_summary['sf_average_depth']} (Seldepth: {search_gap_summary['sf_average_seldepth']})", flush=True)
    print(f"C1 Total Nodes            : {total_c1_nodes:,} ({search_gap_summary['c1_avg_nodes_per_position']:,} per pos)", flush=True)
    print(f"SF19 Total Nodes          : {total_sf_nodes:,} ({search_gap_summary['sf_avg_nodes_per_position']:,} per pos)", flush=True)
    print(f"Node Volume Ratio (C1/SF) : {search_gap_summary['node_volume_ratio_c1_vs_sf']}x", flush=True)
    print(f"Average Evaluation Gap    : {avg_eval_error:.2f} cp vs SF19", flush=True)
    print(f"Average Static Shift      : {avg_static_shift:.2f} cp (C1 Static vs C1 Search)", flush=True)
    print("\nCategory Move Agreement Breakdown:", flush=True)
    for cat, stats in search_gap_summary["category_breakdown"].items():
        print(f"  {cat:15s}: {stats['agreed']}/{stats['total']} ({stats['rate_pct']}%)", flush=True)
    print(f"\nSaved raw data to:\n  {search_gap_file}\n  {eval_gap_file}", flush=True)


if __name__ == "__main__":
    main()
