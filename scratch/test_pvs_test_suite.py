import sys
import unittest
from pathlib import Path
import chess

ROOT = Path("e:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import janus.search
from janus.search import JanusSearch, MATE_SCORE, INF, TTEntry

def patch_search(condition_type):
    # condition_type: 'none', 'depth2', 'depth2_check'
    orig_negamax = JanusSearch._negamax

    def new_negamax(self, board, depth, alpha, beta, ply):
        self.nodes += 1
        self._check_stop()

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
        best_pv = []

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
                if not getattr(self, "enable_pvs", True):
                    use_pvs = False
                elif condition_type == "none":
                    use_pvs = moves_searched > 0
                elif condition_type == "depth2":
                    use_pvs = moves_searched > 0 and depth >= 2
                elif condition_type == "depth2_check":
                    use_pvs = moves_searched > 0 and depth >= 2 and not in_check
                else:
                    use_pvs = False

                if not use_pvs:
                    child_score, child_pv = self._negamax(
                        board, depth - 1, -beta, -alpha, ply + 1
                    )
                    score = -child_score
                else:
                    if hasattr(self, "scout_searches"):
                        self.scout_searches += 1
                    child_score, child_pv = self._negamax(
                        board, depth - 1, -alpha - 1, -alpha, ply + 1
                    )
                    score = -child_score

                    if score > alpha:
                        if hasattr(self, "scout_fail_highs"):
                            self.scout_fail_highs += 1
                        if score < beta:
                            if hasattr(self, "researches"):
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
                if hasattr(self, "beta_cutoffs"):
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

    JanusSearch._negamax = new_negamax

def run_tests_with(cond):
    patch_search(cond)
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print(f"Condition {cond:<15}: Ran {result.testsRun} tests, errors={len(result.errors)}, failures={len(result.failures)}")

if __name__ == "__main__":
    for cond in ["none", "depth2", "depth2_check"]:
        run_tests_with(cond)
