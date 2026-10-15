import sys
import time
from pathlib import Path
import json
from typing import Optional, List, Tuple
from dataclasses import dataclass

import chess

ROOT = Path("e:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, MATE_SCORE, INF, TTEntry, SearchTimeout

class PvsSearch(JanusSearch):
    def __init__(
        self,
        enable_pvs: bool = True,
        pvs_min_depth: int = 1,
        pvs_in_check_gated: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.enable_pvs = enable_pvs
        self.pvs_min_depth = pvs_min_depth
        self.pvs_in_check_gated = pvs_in_check_gated
        
        # Telemetry
        self.scout_searches = 0
        self.scout_fail_highs = 0
        self.researches = 0
        self.beta_cutoffs = 0

    def reset_telemetry(self):
        self.scout_searches = 0
        self.scout_fail_highs = 0
        self.researches = 0
        self.beta_cutoffs = 0

    def _negamax(
        self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int
    ) -> tuple[int, list[chess.Move]]:
        self.nodes += 1
        self._check_stop()

        # Fast rule-mandated draws that do not require move generation
        if (
            board.is_insufficient_material()
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0, []

        if depth <= 0:
            if not any(board.generate_legal_moves()):
                return (-MATE_SCORE + ply if board.is_check() else 0), []
            return self._quiescence(board, alpha, beta, ply), []

        alpha_original = alpha
        beta_original = beta
        key = self._key(board)
        entry = self.tt.get(key)
        tt_move = None

        if entry is not None:
            tt_move = entry.best_move
            tt_score = self._score_from_tt(entry.score, ply)

            if ply > 0 and entry.depth >= depth:
                if (board.halfmove_clock + depth < 150) or entry.score == 0:
                    if entry.flag == "exact":
                        return tt_score, ([] if tt_move is None else [tt_move])
                    if entry.flag == "lower":
                        alpha = max(alpha, tt_score)
                    elif entry.flag == "upper":
                        beta = min(beta, tt_score)
                    if alpha >= beta:
                        return tt_score, ([] if tt_move is None else [tt_move])

        best_score = -INF
        best_move = None
        best_pv: list[chess.Move] = []

        moves = self._ordered_moves(board, tt_move, ply)
        if not moves:
            if board.is_check():
                return -MATE_SCORE + ply, []
            return 0, []

        moves_searched = 0
        in_check = board.is_check()

        for move in moves:
            board.push(move)
            try:
                # PVS decision:
                use_pvs = (
                    self.enable_pvs
                    and moves_searched > 0
                    and depth >= self.pvs_min_depth
                    and not (self.pvs_in_check_gated and in_check)
                )

                if not use_pvs:
                    # Full window search (first move or PVS disabled/gated)
                    child_score, child_pv = self._negamax(
                        board, depth - 1, -beta, -alpha, ply + 1
                    )
                    score = -child_score
                else:
                    # Scout search with null window [-alpha - 1, -alpha]
                    self.scout_searches += 1
                    child_score, child_pv = self._negamax(
                        board, depth - 1, -alpha - 1, -alpha, ply + 1
                    )
                    score = -child_score

                    # Re-search if scout search failed high but didn't cause a beta cutoff
                    if score > alpha:
                        self.scout_fail_highs += 1
                        if score < beta:
                            self.researches += 1
                            child_score, child_pv = self._negamax(
                                board, depth - 1, -beta, -alpha, ply + 1
                            )
                            score = -child_score
            finally:
                board.pop()

            moves_searched += 1

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv

            alpha = max(alpha, score)
            if alpha >= beta:
                self.beta_cutoffs += 1
                if not board.is_capture(move) and move.promotion is None:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                    self._update_history(move, depth)
                break

        if len(self.tt) >= self.tt_max_entries:
            self.tt.clear()

        if best_score <= alpha_original:
            flag = "upper"
        elif best_score >= beta_original:
            flag = "lower"
        else:
            flag = "exact"

        self.tt[key] = TTEntry(
            depth=depth,
            score=self._score_to_tt(best_score, ply),
            flag=flag,
            best_move=best_move,
        )
        return best_score, best_pv

def evaluate_configurations():
    positions_file = ROOT / "benchmarks" / "positions.json"
    positions = json.loads(positions_file.read_text(encoding="utf-8"))

    configs = [
        ("Baseline (PVS Off)", False, 1, False),
        ("Pure PVS (min_d=1, no check gate)", True, 1, False),
        ("PVS (min_d=1, check gated)", True, 1, True),
        ("PVS (min_d=2, no check gate)", True, 2, False),
        ("PVS (min_d=2, check gated)", True, 2, True),
    ]

    for depth in [3, 4, 5]:
        print(f"\n==========================================")
        print(f"EVALUATING DEPTH {depth}")
        print(f"==========================================")
        
        baseline_results = {}

        for name, enable_pvs, min_d, check_gated in configs:
            engine = PvsSearch(
                enable_pvs=enable_pvs,
                pvs_min_depth=min_d,
                pvs_in_check_gated=check_gated,
            )
            total_nodes = 0
            start_t = time.perf_counter()
            pos_results = []

            for pos in positions:
                board = chess.Board(pos["fen"])
                engine.tt.clear()
                engine.reset_telemetry()
                res = engine.search(board, max_depth=depth)
                total_nodes += res.nodes
                pos_results.append((pos["id"], res.score, res.best_move, res.nodes))

            elapsed = time.perf_counter() - start_t

            if not enable_pvs:
                baseline_results[depth] = pos_results

            # Check matches with baseline
            mismatches = 0
            for i, (pid, sc, bm, nd) in enumerate(pos_results):
                base_pid, base_sc, base_bm, base_nd = baseline_results[depth][i]
                if sc != base_sc or bm != base_bm:
                    mismatches += 1
                    print(f"  [MISMATCH] {name} on {pid}: base=({base_sc}, {base_bm}) vs pvs=({sc}, {bm})")

            print(
                f"{name:<35} | Nodes: {total_nodes:<7} | Time: {elapsed:.3f}s | "
                f"Scout: {engine.scout_searches:<6} | FailHigh: {engine.scout_fail_highs:<4} | "
                f"ReSearch: {engine.researches:<4} | BetaCut: {engine.beta_cutoffs:<4} | Mismatch: {mismatches}"
            )

if __name__ == "__main__":
    evaluate_configurations()
