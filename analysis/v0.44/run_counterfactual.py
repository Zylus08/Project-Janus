"""Run counterfactual search experiments on the v0.44 diagnostic corpus."""
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
import chess

from janus.search import JanusSearch

STOCKFISH_PATH = r"E:\ChessXML\tools\stockfish\stockfish.exe"

class StockfishOracle:
    def __init__(self, depth: int = 10):
        self.depth = depth
        self.process = subprocess.Popen(
            [STOCKFISH_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._send("uci")
        self._read_until("uciok")
        self._send("setoption name Threads value 1")
        self._send("setoption name Hash value 64")
        self._send("isready")
        self._read_until("readyok")

    def _send(self, cmd: str) -> None:
        if self.process and self.process.stdin:
            self.process.stdin.write(f"{cmd}\n")
            self.process.stdin.flush()

    def _read_until(self, target: str) -> list[str]:
        lines = []
        if not self.process or not self.process.stdout:
            return lines
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            lines.append(line_str)
            if line_str == target or line_str.startswith(target):
                break
        return lines

    def eval_position(self, fen: str) -> Tuple[int, Optional[str]]:
        """Return score in centipawns from perspective of side to move in fen, and best move."""
        self._send(f"position fen {fen}")
        self._send(f"go depth {self.depth}")
        score_side = 0
        best_move = None
        turn_is_white = (" w " in fen or fen.endswith(" w"))
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if "score cp" in line_str:
                parts = line_str.split()
                try:
                    idx = parts.index("cp")
                    cp = int(parts[idx + 1])
                    score_side = cp
                except (ValueError, IndexError):
                    pass
            elif "score mate" in line_str:
                parts = line_str.split()
                try:
                    idx = parts.index("mate")
                    mate_plies = int(parts[idx + 1])
                    score_side = 30000 if mate_plies > 0 else -30000
                except (ValueError, IndexError):
                    pass
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    best_move = parts[1]
                break
        return score_side, best_move

    def close(self):
        try:
            self._send("quit")
            self.process.terminate()
            self.process.wait(timeout=1.0)
        except Exception:
            pass

def run():
    corpus_path = Path("analysis/v0.44/diagnostic_positions.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        positions = json.load(f)

    print(f"Loaded {len(positions)} diagnostic positions. Initializing engines...")
    oracle = StockfishOracle(depth=10)

    results = []
    category_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for idx, pos in enumerate(positions, 1):
        fen = pos["fen"]
        board = chess.Board(fen)
        is_white_turn = board.turn == chess.WHITE

        # 1. K0 Search (depth 4)
        engine_k0 = JanusSearch(enable_rfp=False, diagnostic_rfp=False)
        t0 = time.perf_counter()
        res_k0 = engine_k0.search(board.copy(), max_depth=4)
        k0_time = time.perf_counter() - t0
        k0_move_uci = res_k0.best_move.uci() if res_k0.best_move else None

        # 2. RFP Search (depth 4) with telemetry
        engine_rfp = JanusSearch(enable_rfp=True, diagnostic_rfp=True, rfp_max_depth=2, rfp_margin_per_depth=120)
        t0 = time.perf_counter()
        res_rfp = engine_rfp.search(board.copy(), max_depth=4)
        rfp_time = time.perf_counter() - t0
        rfp_move_uci = res_rfp.best_move.uci() if res_rfp.best_move else None

        # 3. Stockfish Reference Evaluation
        # Eval board before
        sf_eval_before, sf_best_before = oracle.eval_position(fen)

        # Eval after K0 move
        b_k0 = board.copy()
        if res_k0.best_move and res_k0.best_move in b_k0.legal_moves:
            b_k0.push(res_k0.best_move)
            # score from opponent perspective, so invert
            sf_after_k0_opp, _ = oracle.eval_position(b_k0.fen())
            sf_after_k0 = -sf_after_k0_opp
        else:
            sf_after_k0 = -9999

        # Eval after RFP move
        b_rfp = board.copy()
        if res_rfp.best_move and res_rfp.best_move in b_rfp.legal_moves:
            b_rfp.push(res_rfp.best_move)
            sf_after_rfp_opp, _ = oracle.eval_position(b_rfp.fen())
            sf_after_rfp = -sf_after_rfp_opp
        else:
            sf_after_rfp = -9999

        # Evaluate move quality delta from side-to-move perspective:
        # delta = sf_after_k0 - sf_after_rfp
        # Positive delta means K0's move is better than RFP's move
        eval_delta = sf_after_k0 - sf_after_rfp

        # Node reduction %
        node_diff_pct = ((res_k0.nodes - res_rfp.nodes) / res_k0.nodes * 100.0) if res_k0.nodes > 0 else 0.0

        # Categorize
        if k0_move_uci == rfp_move_uci:
            if abs(res_k0.score - res_rfp.score) <= 15:
                if node_diff_pct > 2.0:
                    cat = 2  # Efficiency benefit
                else:
                    cat = 1  # No material search difference
            else:
                cat = 1
        else:
            if eval_delta < 30:
                cat = 3  # Disagreement without established harm
            elif 30 <= eval_delta < 100:
                cat = 4  # Potential false cutoff
            else:
                cat = 5  # Confirmed tactical regression

        category_counts[cat] += 1

        record = {
            "id": pos["id"],
            "category": cat,
            "category_name": {
                1: "No material search difference",
                2: "Efficiency benefit",
                3: "Disagreement without established harm",
                4: "Potential false cutoff",
                5: "Confirmed tactical regression",
            }[cat],
            "pair": pos["pair"],
            "color": pos["color"],
            "opening": pos["opening"],
            "ply": pos["ply"],
            "fen": fen,
            "k0": {
                "move": k0_move_uci,
                "score": res_k0.score,
                "nodes": res_k0.nodes,
                "time_s": k0_time,
                "sf_eval": sf_after_k0,
            },
            "rfp": {
                "move": rfp_move_uci,
                "score": res_rfp.score,
                "nodes": res_rfp.nodes,
                "time_s": rfp_time,
                "rfp_considered": res_rfp.rfp_considered,
                "rfp_cutoffs": res_rfp.rfp_cutoffs,
                "sf_eval": sf_after_rfp,
                "cutoff_events_count": len(res_rfp.rfp_events),
            },
            "eval_delta_cp": eval_delta,
            "node_reduction_pct": node_diff_pct,
            "stockfish_best_move": sf_best_before,
            "rfp_events_sample": res_rfp.rfp_events[:5],
        }
        results.append(record)

        print(f"[{idx:2d}/{len(positions)}] Pair {pos['pair']:2d} ({pos['color']:5s}) -> Cat {cat}: K0={k0_move_uci} (eval={sf_after_k0:+4d}), RFP={rfp_move_uci} (eval={sf_after_rfp:+4d}) | Delta={eval_delta:+4d} cp, Nodes: {res_k0.nodes}->{res_rfp.nodes} ({node_diff_pct:+.1f}%)")

    oracle.close()

    out_file = Path("analysis/v0.44/counterfactual_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_positions": len(positions),
                "category_counts": category_counts,
                "mean_node_reduction_pct": sum(r["node_reduction_pct"] for r in results) / len(results) if results else 0,
            },
            "positions": results,
        }, f, indent=2)

    print("\n--- Counterfactual Experiment Complete ---")
    print("Category Breakdown:")
    for c in range(1, 6):
        desc = {
            1: "Category 1: No material search difference",
            2: "Category 2: Efficiency benefit (same move, fewer nodes)",
            3: "Category 3: Disagreement without established harm",
            4: "Category 4: Potential false cutoff (30-99 cp loss)",
            5: "Category 5: Confirmed tactical regression (>=100 cp blunder)",
        }[c]
        print(f"  {desc}: {category_counts[c]} ({category_counts[c]/len(positions)*100:.1f}%)")

if __name__ == "__main__":
    run()

