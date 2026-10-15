import json
import time
import sys
import chess

sys.path.insert(0, 'src')
from janus.search import JanusSearch, MATE_SCORE, INF, TTEntry
from janus.evaluation import evaluate_side_to_move

positions = json.load(open('benchmarks/positions.json'))

class PreciseSearch(JanusSearch):
    def _negamax(self, board, depth, alpha, beta, ply):
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
                if entry.flag == 'exact':
                    return tt_score, ([] if tt_move is None else [tt_move])
                if entry.flag == 'lower':
                    alpha = max(alpha, tt_score)
                elif entry.flag == 'upper':
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

        for move in moves:
            board.push(move)
            try:
                child_score, child_pv = self._negamax(
                    board, depth - 1, -beta, -alpha, ply + 1
                )
                score = -child_score
            finally:
                board.pop()

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv

            alpha = max(alpha, score)
            if alpha >= beta:
                if not board.is_capture(move) and move.promotion is None:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                break

        if len(self.tt) >= self.tt_max_entries:
            self.tt.clear()

        if best_score <= alpha_original:
            flag = 'upper'
        elif best_score >= beta_original:
            flag = 'lower'
        else:
            flag = 'exact'

        self.tt[key] = TTEntry(
            depth=depth,
            score=self._score_to_tt(best_score, ply),
            flag=flag,
            best_move=best_move,
        )
        return best_score, best_pv

    def _quiescence(self, board, alpha, beta, ply):
        self.nodes += 1
        self._check_stop()

        if (
            board.is_insufficient_material()
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0

        in_check = board.is_check()
        if ply >= self.qsearch_max_ply and not in_check:
            return evaluate_side_to_move(board)

        if not in_check:
            if not any(board.generate_legal_moves()):
                return 0
            stand_pat = evaluate_side_to_move(board)
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)
            moves = self._quiescence_moves(board)
            moves.sort(
                key=lambda move: self._move_order_score(board, move, None, ply),
                reverse=True,
            )
        else:
            moves = self._ordered_moves(board, None, ply)

        if in_check and not moves:
            return -MATE_SCORE + ply

        for move in moves:
            board.push(move)
            try:
                score = -self._quiescence(board, -beta, -alpha, ply + 1)
            finally:
                board.pop()

            if score >= beta:
                return beta
            alpha = max(alpha, score)

        return alpha

print("Measuring Depth 4 single run comparison:")
s_orig = JanusSearch()
t0 = time.perf_counter()
for p in positions:
    s_orig.tt.clear()
    s_orig.search(chess.Board(p['fen']), max_depth=4)
dt_orig = time.perf_counter() - t0
print(f"Original JanusSearch Depth 4: {dt_orig:.3f}s (nodes: {s_orig.nodes})")

s_opt = PreciseSearch()
t0 = time.perf_counter()
for p in positions:
    s_opt.tt.clear()
    s_opt.search(chess.Board(p['fen']), max_depth=4)
dt_opt = time.perf_counter() - t0
print(f"PreciseSearch Depth 4:         {dt_opt:.3f}s (nodes: {s_opt.nodes})")

speedup = (dt_orig - dt_opt) / dt_orig * 100
print(f"Speedup: {speedup:.1f}% ({dt_orig - dt_opt:.3f}s faster)")
