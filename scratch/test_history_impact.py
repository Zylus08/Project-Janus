import json
import time
from pathlib import Path
import chess

ROOT = Path("E:/ChessXML/project-janus")
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch, INF, TTEntry, MATE_SCORE

MAX_HISTORY = 500_000

class HistorySearch(JanusSearch):
    def __init__(self, *args, enable_history=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_history = enable_history
        self.history = [[0] * 64 for _ in range(64)]

    def _update_history(self, move, depth):
        if not self.enable_history:
            return
        self.history[move.from_square][move.to_square] = min(
            MAX_HISTORY, self.history[move.from_square][move.to_square] + depth * depth
        )

    def _move_order_score(self, board, move, tt_move=None, ply=0):
        if tt_move is not None and move == tt_move:
            return 10_000_000

        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            victim_value = 100 if board.is_en_passant(move) else (
                0 if victim is None else {
                    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 335,
                    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000
                }[victim.piece_type]
            )
            attacker = board.piece_at(move.from_square)
            attacker_value = (
                0 if attacker is None else {
                    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 335,
                    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000
                }[attacker.piece_type]
            )
            score += 1_000_000 + 10 * victim_value - attacker_value

        if move.promotion:
            score += 800_000 + move.promotion

        if score == 0 and ply < len(self.killers):
            if move == self.killers[ply][0]:
                return 700_000
            if move == self.killers[ply][1]:
                return 600_000

        if score == 0 and self.enable_history:
            return self.history[move.from_square][move.to_square]

        return score

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

        for move in moves:
            board.push(move)
            try:
                child_score, child_pv = self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
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

    def search(self, board, max_depth=5, time_limit=None, stop_event=None):
        self.history = [[0] * 64 for _ in range(64)]
        return super().search(board, max_depth=max_depth, time_limit=time_limit, stop_event=stop_event)

positions_data = json.loads((ROOT / "benchmarks" / "positions.json").read_text(encoding="utf-8"))

print("=== DEPTH 3 COMPARISON ===")
for p in positions_data:
    b = chess.Board(p["fen"])
    e_base = HistorySearch(enable_history=False)
    r_base = e_base.search(b, max_depth=3)
    e_hist = HistorySearch(enable_history=True)
    r_hist = e_hist.search(b, max_depth=3)
    print(f"{p['id']:<18}: Base nodes={r_base.nodes:>5} (best={r_base.best_move}), Hist nodes={r_hist.nodes:>5} (best={r_hist.best_move}), delta={r_hist.nodes - r_base.nodes:+d}")

print("\n=== DEPTH 4 COMPARISON ===")
for p in positions_data:
    b = chess.Board(p["fen"])
    e_base = HistorySearch(enable_history=False)
    r_base = e_base.search(b, max_depth=4)
    e_hist = HistorySearch(enable_history=True)
    r_hist = e_hist.search(b, max_depth=4)
    pv_base = " ".join(m.uci() for m in r_base.pv)
    pv_hist = " ".join(m.uci() for m in r_hist.pv)
    print(f"{p['id']:<18}: Base nodes={r_base.nodes:>6} (score={r_base.score}, best={r_base.best_move}), Hist nodes={r_hist.nodes:>6} (score={r_hist.score}, best={r_hist.best_move}), delta={r_hist.nodes - r_base.nodes:+d}")
    if pv_base != pv_hist:
        print(f"  PV Base: {pv_base}")
        print(f"  PV Hist: {pv_hist}")
