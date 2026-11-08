"""Project Janus v0.63 - Phase 3 Search Failure Forensics.

Identifies decisive turning point positions from v0.62 losses,
runs matched search traces with C1, N1 (Hybrid 50/50), Pure NNUE, and Stockfish 19,
and isolates static evaluation errors vs pruning/search horizon errors.
"""

import json
import math
import subprocess
from pathlib import Path
from typing import Dict, List, Any
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

spec_c1 = importlib.util.spec_from_file_location("bridge_c1", BRIDGE_C1)
mod_c1 = importlib.util.module_from_spec(spec_c1)
spec_c1.loader.exec_module(mod_c1)
NativeEngineC1 = mod_c1.NativeEngineBridge

spec_v61 = importlib.util.spec_from_file_location("bridge_v61", BRIDGE_V61)
mod_v61 = importlib.util.module_from_spec(spec_v61)
spec_v61.loader.exec_module(mod_v61)
NativeEngineV61 = mod_v61.NativeEngineBridge


class StockfishEvaluator:
    def __init__(self, exe_path: Path):
        self.p = subprocess.Popen(
            [str(exe_path.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.p.stdin.write("uci\nisready\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line or line.strip() == "readyok":
                break

    def analyze(self, fen: str, depth: int = 14) -> Dict[str, Any]:
        self.p.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.p.stdin.flush()
        bestmove = None
        score_cp = 0
        pv = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if "score cp" in line:
                tokens = line.split()
                if "cp" in tokens:
                    idx = tokens.index("cp")
                    score_cp = int(tokens[idx + 1])
                if "pv" in tokens:
                    idx = tokens.index("pv")
                    pv = tokens[idx + 1:]
            elif "score mate" in line:
                tokens = line.split()
                if "mate" in tokens:
                    idx = tokens.index("mate")
                    m = int(tokens[idx + 1])
                    score_cp = 10000 if m > 0 else -10000
                if "pv" in tokens:
                    idx = tokens.index("pv")
                    pv = tokens[idx + 1:]
            if line.startswith("bestmove"):
                tokens = line.split()
                if len(tokens) >= 2:
                    bestmove = tokens[1]
                break
        return {"bestmove": bestmove, "score": score_cp, "pv": pv[:5]}

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


def find_critical_loss_positions():
    pgn_path = ROOT / "analysis" / "v0.62" / "pgn" / "v062_confirmatory_match.pgn"
    cases = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        game_id = 0
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            game_id += 1
            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            result = game.headers.get("Result", "")
            opening = game.headers.get("Opening", "")

            # Look for games where C1 won against Candidate
            cand_lost = False
            if "Neural" in white and result == "0-1":
                cand_lost = True
                cand_color = chess.WHITE
            elif "Neural" in black and result == "1-0":
                cand_lost = True
                cand_color = chess.BLACK

            if cand_lost and len(cases) < 6:
                board = game.board()
                moves = list(game.mainline_moves())
                # Sample a position around ply 30-50 where the candidate made a blunder/suboptimal move
                if len(moves) >= 30:
                    for test_ply in (30, 40, 50):
                        if test_ply < len(moves):
                            b_test = game.board()
                            for m in moves[:test_ply]:
                                b_test.push(m)
                            if b_test.turn == cand_color and not b_test.is_check():
                                cases.append({
                                    "game_id": game_id,
                                    "opening": opening,
                                    "ply": test_ply,
                                    "fen": b_test.fen(),
                                    "candidate_color": "white" if cand_color == chess.WHITE else "black",
                                })
                                break
    return cases


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.63 — PHASE 3 SEARCH-LEVEL FAILURE ANALYSIS")
    print("=" * 80)

    cases = find_critical_loss_positions()
    print(f"Identified {len(cases)} critical candidate loss positions from v0.62 PGN.")

    sf = StockfishEvaluator(STOCKFISH_EXE)
    eng_c1 = NativeEngineC1()
    eng_c1.set_ordering_options(True, True)
    eng_c1.set_pvs_options(False)
    eng_c1.set_lmr_options(True, 3, 4, 1)

    eng_n1 = NativeEngineV61()
    eng_n1.set_neural_value_options(True, str(MODEL_PATH), 50, use_avx2=True)
    eng_n1.set_ordering_options(True, True)
    eng_n1.set_pvs_options(False)
    eng_n1.set_lmr_options(True, 3, 4, 1)

    eng_pure = NativeEngineV61()
    eng_pure.set_neural_value_options(True, str(MODEL_PATH), 100, use_avx2=True)
    eng_pure.set_ordering_options(True, True)
    eng_pure.set_pvs_options(False)
    eng_pure.set_lmr_options(True, 3, 4, 1)

    case_studies = []
    for idx, c in enumerate(cases):
        fen = c["fen"]
        board = chess.Board(fen)

        # 1. Stockfish ground truth analysis
        sf_res = sf.analyze(fen, depth=14)

        # 2. Classical C1 Search (depth 6)
        eng_c1.set_fen(fen)
        eng_c1.clear_tt()
        eng_c1.clear_killers()
        eng_c1.clear_history_heuristic()
        c1_static = eng_c1.evaluate()
        bm_c1, sc_c1, d_c1, n_c1, el_c1, pv_c1 = eng_c1.search(max_depth=6, time_limit=5.0)

        # 3. Neural N1 (Hybrid 50/50) Search (depth 6)
        eng_n1.set_fen(fen)
        eng_n1.clear_tt()
        eng_n1.clear_killers()
        eng_n1.clear_history_heuristic()
        n1_static = eng_n1.evaluate_neural()
        bm_n1, sc_n1, d_n1, n_n1, el_n1, pv_n1 = eng_n1.search(max_depth=6, time_limit=5.0)

        # 4. Pure NNUE Search (depth 6)
        eng_pure.set_fen(fen)
        eng_pure.clear_tt()
        eng_pure.clear_killers()
        eng_pure.clear_history_heuristic()
        pure_static = eng_pure.evaluate_neural()
        bm_p, sc_p, d_p, n_p, el_p, pv_p = eng_pure.search(max_depth=6, time_limit=5.0)

        # Categorize failure mode
        disagree = (bm_c1 != bm_n1)
        sf_agrees_c1 = (bm_c1 == sf_res["bestmove"])
        sf_agrees_n1 = (bm_n1 == sf_res["bestmove"])

        if sf_agrees_c1 and not sf_agrees_n1:
            failure_type = "Neural Evaluation Misdirection (Selected Inferior Move)"
        elif not sf_agrees_c1 and not sf_agrees_n1:
            failure_type = "Search Horizon / Pruning Truncation"
        elif sf_agrees_n1:
            failure_type = "Candidate Correct (Loss Occurred Elsewhere)"
        else:
            failure_type = "Tactical Divergence"

        study = {
            "case_id": idx + 1,
            "game_id": c["game_id"],
            "opening": c["opening"],
            "ply": c["ply"],
            "side_to_move": c["candidate_color"],
            "fen": fen,
            "stockfish": sf_res,
            "classical_c1": {
                "static_eval": c1_static,
                "search_score": sc_c1,
                "bestmove": bm_c1,
                "nodes": n_c1,
                "pv": pv_c1[:4],
            },
            "neural_n1_hybrid": {
                "static_eval": n1_static,
                "search_score": sc_n1,
                "bestmove": bm_n1,
                "nodes": n_n1,
                "pv": pv_n1[:4],
            },
            "pure_nnue": {
                "static_eval": pure_static,
                "search_score": sc_p,
                "bestmove": bm_p,
                "nodes": n_p,
                "pv": pv_p[:4],
            },
            "diagnosis": failure_type,
        }
        case_studies.append(study)

        print(f"\nCase {idx+1} [Game {c['game_id']} | Ply {c['ply']} | {c['opening']}]:")
        print(f"  FEN: {fen}")
        print(f"  Stockfish 14: BM={sf_res['bestmove']}, Score={sf_res['score']} cp")
        print(f"  Classical C1: BM={bm_c1}, Static={c1_static}, Score={sc_c1}, Nodes={n_c1}")
        print(f"  Neural N1:    BM={bm_n1}, Static={n1_static}, Score={sc_n1}, Nodes={n_n1}")
        print(f"  Diagnosis:    {failure_type}")

    sf.close()

    out_file = OUT_DIR / "search_failure_cases.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(case_studies, f, indent=2)

    print(f"\nSaved {len(case_studies)} forensic case studies to {out_file}")


if __name__ == "__main__":
    main()
