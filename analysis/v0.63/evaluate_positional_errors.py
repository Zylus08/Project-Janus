"""Project Janus v0.63 - Phase 2 Position-Value Error Analysis.

Evaluates Classical C1, Pure NNUE-V2, and Hybrid 50/50 against Stockfish 19 ground truth
across 500 stratified game positions completely excluded from training.
Analyzes error distributions disaggregated by pawn structure, phase, and tension.
"""

import json
import math
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import chess
import chess.pgn
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis" / "v0.63"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRIDGE_C1 = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"
BRIDGE_V61 = ROOT / "analysis" / "v0.61" / "native" / "janus_native_bridge.py"
MODEL_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"
STOCKFISH_EXE = Path(r"E:\ChessXML\tools\stockfish\stockfish.exe")

# Load C1 and V61 native bridges
spec_c1 = importlib.util.spec_from_file_location("bridge_c1", BRIDGE_C1)
mod_c1 = importlib.util.module_from_spec(spec_c1)
spec_c1.loader.exec_module(mod_c1)
NativeEngineC1 = mod_c1.NativeEngineBridge

spec_v61 = importlib.util.spec_from_file_location("bridge_v61", BRIDGE_V61)
mod_v61 = importlib.util.module_from_spec(spec_v61)
spec_v61.loader.exec_module(mod_v61)
NativeEngineV61 = mod_v61.NativeEngineBridge

from characterize_structures import compute_structural_descriptors


class StockfishEvaluator:
    def __init__(self, exe_path: Path):
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._init_uci()

    def _init_uci(self):
        self.p.stdin.write("uci\nisready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def evaluate_fen(self, fen: str, depth: int = 12) -> int:
        cmd = f"position fen {fen}\ngo depth {depth}\n"
        self.p.stdin.write(cmd)
        self.p.stdin.flush()
        last_score_cp = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "score cp" in line:
                tokens = line.split()
                if "cp" in tokens:
                    idx = tokens.index("cp")
                    if idx + 1 < len(tokens):
                        try:
                            last_score_cp = int(tokens[idx + 1])
                        except ValueError:
                            pass
            elif "score mate" in line:
                tokens = line.split()
                if "mate" in tokens:
                    idx = tokens.index("mate")
                    if idx + 1 < len(tokens):
                        try:
                            m = int(tokens[idx + 1])
                            last_score_cp = 10000 if m > 0 else -10000
                        except ValueError:
                            pass
            if line.startswith("bestmove"):
                break
        return last_score_cp

    def close(self):
        try:
            self.p.stdin.write("quit\n")
            self.p.stdin.flush()
            self.p.wait(timeout=2.0)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


def spearman_rho(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0

    def rank(vals):
        sorted_pairs = sorted(enumerate(vals), key=lambda p: p[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and sorted_pairs[j + 1][1] == sorted_pairs[i][1]:
                j += 1
            avg_rank = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                ranks[sorted_pairs[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = rank(x)
    ry = rank(y)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def sample_excluded_positions(max_positions=500) -> List[Tuple[str, str, int]]:
    # Extract from v0.62 confirmatory tournament games
    pgn_path = ROOT / "analysis" / "v0.62" / "pgn" / "v062_confirmatory_match.pgn"
    positions = []
    seen_fens = set()

    with open(pgn_path, "r", encoding="utf-8") as f:
        game_num = 0
        while len(positions) < max_positions:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            game_num += 1
            board = game.board()
            ply = 0
            for move in game.mainline_moves():
                board.push(move)
                ply += 1
                # Sample middlegame and early endgame plies
                if ply in (14, 20, 26, 32, 38) and not board.is_game_over() and not board.is_check():
                    fen = board.fen()
                    if fen not in seen_fens:
                        seen_fens.add(fen)
                        positions.append((fen, f"game_{game_num}", ply))
                        if len(positions) >= max_positions:
                            break
    return positions


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.63 — PHASE 2 POSITION-VALUE ERROR ANALYSIS")
    print("=" * 80)

    print("Sampling 500 held-out positions from v0.62 tournament games...")
    pos_sample = sample_excluded_positions(500)
    print(f"Sampled {len(pos_sample)} unique positions.")

    sf = StockfishEvaluator(STOCKFISH_EXE)
    eng_c1 = NativeEngineC1()
    eng_v61 = NativeEngineV61()
    eng_v61.set_neural_value_options(True, str(MODEL_PATH), 100, use_avx2=True)

    records = []
    t_start = time.time()
    for idx, (fen, g_id, ply) in enumerate(pos_sample):
        board = chess.Board(fen)
        struct = compute_structural_descriptors(board)

        # Stockfish evaluation (from White's perspective)
        # Note: Stockfish `score cp` is from side to move's perspective
        sf_score_stm = sf.evaluate_fen(fen, depth=12)
        sf_score_white = sf_score_stm if board.turn == chess.WHITE else -sf_score_stm

        # C1 evaluation (from side to move)
        eng_c1.set_fen(fen)
        c1_score_stm = eng_c1.evaluate()
        c1_score_white = c1_score_stm if board.turn == chess.WHITE else -c1_score_stm

        # Pure NNUE evaluation (from side to move)
        eng_v61.set_fen(fen)
        nnue_score_stm = eng_v61.evaluate_neural()
        nnue_score_white = nnue_score_stm if board.turn == chess.WHITE else -nnue_score_stm

        # Hybrid 50/50 evaluation
        hybrid_score_white = int(0.5 * c1_score_white + 0.5 * nnue_score_white)

        records.append({
            "fen": fen,
            "game_id": g_id,
            "ply": ply,
            "turn": "white" if board.turn == chess.WHITE else "black",
            "sf19": sf_score_white,
            "c1": c1_score_white,
            "nnue": nnue_score_white,
            "hybrid": hybrid_score_white,
            "struct": struct,
        })

        if (idx + 1) % 100 == 0 or (idx + 1) == len(pos_sample):
            elapsed = time.time() - t_start
            print(f"[{idx+1}/{len(pos_sample)}] Evaluated positions | Elapsed: {elapsed:.1f}s", flush=True)

    sf.close()

    # Compute overall and disaggregated errors
    def evaluate_subset(recs, subset_name):
        n = len(recs)
        if n == 0:
            return {}
        y_sf = [r["sf19"] for r in recs]
        y_c1 = [r["c1"] for r in recs]
        y_nn = [r["nnue"] for r in recs]
        y_hy = [r["hybrid"] for r in recs]

        mae_c1 = sum(abs(y_c1[i] - y_sf[i]) for i in range(n)) / n
        mae_nn = sum(abs(y_nn[i] - y_sf[i]) for i in range(n)) / n
        mae_hy = sum(abs(y_hy[i] - y_sf[i]) for i in range(n)) / n

        rho_c1 = spearman_rho(y_c1, y_sf)
        rho_nn = spearman_rho(y_nn, y_sf)
        rho_hy = spearman_rho(y_hy, y_sf)

        # Sign agreement (excluding near-zeros [-20, 20])
        def sign_agree(y_pred):
            valid = [(y_pred[i], y_sf[i]) for i in range(n) if abs(y_sf[i]) > 20]
            if not valid:
                return 0.0
            agree = sum(1 for p, s in valid if (p > 0 and s > 0) or (p < 0 and s < 0))
            return (agree / len(valid)) * 100.0

        sign_c1 = sign_agree(y_c1)
        sign_nn = sign_agree(y_nn)
        sign_hy = sign_agree(y_hy)

        return {
            "subset": subset_name,
            "count": n,
            "mae_c1": round(mae_c1, 2),
            "mae_nnue": round(mae_nn, 2),
            "mae_hybrid": round(mae_hy, 2),
            "spearman_c1": round(rho_c1, 4),
            "spearman_nnue": round(rho_nn, 4),
            "spearman_hybrid": round(rho_hy, 4),
            "sign_agree_c1": round(sign_c1, 1),
            "sign_agree_nnue": round(sign_nn, 1),
            "sign_agree_hybrid": round(sign_hy, 1),
        }

    # Stratified subsets
    subsets = {
        "Overall (All 500)": records,
        "Locked Chains (>= 1)": [r for r in records if r["struct"]["locked_headon_pairs"] >= 1],
        "No Locked Chains (0)": [r for r in records if r["struct"]["locked_headon_pairs"] == 0],
        "High Blocked Pawns (>= 4)": [r for r in records if r["struct"]["blocked_pawns"] >= 4],
        "Low Blocked Pawns (< 4)": [r for r in records if r["struct"]["blocked_pawns"] < 4],
        "Zero Open Files (0)": [r for r in records if r["struct"]["open_files"] == 0],
        "Open Files (>= 1)": [r for r in records if r["struct"]["open_files"] >= 1],
        "Central Tension (> 0)": [r for r in records if r["struct"]["central_tension"] > 0],
        "No Central Tension (0)": [r for r in records if r["struct"]["central_tension"] == 0],
        "Middlegame (Phase > 16)": [r for r in records if r["struct"]["material_phase"] > 16],
        "Endgame (Phase <= 16)": [r for r in records if r["struct"]["material_phase"] <= 16],
        "Quiet Eval (|SF| <= 100 cp)": [r for r in records if abs(r["sf19"]) <= 100],
        "Decisive Eval (|SF| > 100 cp)": [r for r in records if abs(r["sf19"]) > 100],
    }

    results = [evaluate_subset(recs, name) for name, recs in subsets.items()]

    print("\n" + "=" * 105)
    print(f"{'Positional Regime':28s} | {'Count':5s} | {'MAE C1':8s} {'MAE NN':8s} {'MAE Hyb':8s} | {'Rho C1':7s} {'Rho NN':7s} {'Rho Hy':7s} | {'Sign NN':7s}")
    print("=" * 105)
    for r in results:
        print(f"{r['subset']:28s} | {r['count']:5d} | {r['mae_c1']:8.1f} {r['mae_nnue']:8.1f} {r['mae_hybrid']:8.1f} | {r['spearman_c1']:7.3f} {r['spearman_nnue']:7.3f} {r['spearman_hybrid']:7.3f} | {r['sign_agree_nnue']:6.1f}%")
    print("=" * 105)

    out_file = OUT_DIR / "positional_error_analysis.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"subsets": results, "raw_sample_count": len(records)}, f, indent=2)

    print(f"\nSaved positional error analysis to {out_file}")


if __name__ == "__main__":
    main()
