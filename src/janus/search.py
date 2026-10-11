"""Single-threaded alpha-beta search for Project Janus."""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional

import chess

from .evaluation import evaluate_side_to_move

MATE_SCORE = 100_000
INF = 1_000_000


@dataclass
class TTEntry:
    depth: int
    score: int
    flag: str  # "exact", "lower", "upper"
    best_move: Optional[chess.Move]


@dataclass
class SearchResult:
    best_move: Optional[chess.Move]
    score: int                 # centipawns from root side's perspective
    depth: int
    nodes: int
    pv: list[chess.Move]
    elapsed: float


class SearchTimeout(Exception):
    pass


class JanusSearch:
    def __init__(
        self,
        tt_max_entries: int = 200_000,
        qsearch_max_ply: int = 12,
    ) -> None:
        self.tt: dict[str, TTEntry] = {}
        self.tt_max_entries = tt_max_entries
        self.qsearch_max_ply = qsearch_max_ply
        self.nodes = 0
        self.deadline: Optional[float] = None
        self.root_side = chess.WHITE

    @staticmethod
    def _key(board: chess.Board) -> str:
        # FEN includes side to move, castling rights and en-passant state.
        # Halfmove/fullmove counters are also included, which is conservative
        # but can reduce transposition hits.
        return board.fen(en_passant="legal")

    def _check_time(self) -> None:
        if self.deadline is not None and (self.nodes & 1023) == 0:
            if time.monotonic() >= self.deadline:
                raise SearchTimeout

    def _terminal_score(self, board: chess.Board, ply: int) -> Optional[int]:
        if board.is_checkmate():
            return -MATE_SCORE + ply
        if (
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0
        return None

    def _move_order_score(
        self, board: chess.Board, move: chess.Move, tt_move: Optional[chess.Move]
    ) -> int:
        if tt_move is not None and move == tt_move:
            return 10_000_000
        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            # En passant has no piece on the destination square.
            victim_value = 100 if board.is_en_passant(move) else (
                0 if victim is None else {
                    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 335,
                    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000
                }[victim.piece_type]
            )
            attacker = board.piece_at(move.from_square)
            attacker_value = 0 if attacker is None else {
                chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 335,
                chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000
            }[attacker.piece_type]
            score += 1_000_000 + 10 * victim_value - attacker_value
        if move.promotion:
            score += 800_000 + move.promotion
        return score

    def _ordered_moves(
        self, board: chess.Board, tt_move: Optional[chess.Move] = None
    ) -> list[chess.Move]:
        moves = list(board.legal_moves)
        moves.sort(
            key=lambda move: self._move_order_score(board, move, tt_move),
            reverse=True,
        )
        return moves

    def _quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int) -> int:
        self.nodes += 1
        self._check_time()

        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal

        in_check = board.is_check()
        if ply >= self.qsearch_max_ply:
            return evaluate_side_to_move(board)

        stand_pat = -INF
        if not in_check:
            stand_pat = evaluate_side_to_move(board)
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)

        # When in check, all legal evasions must be considered; otherwise only
        # captures/promotions are needed to reduce the horizon effect.
        moves = self._ordered_moves(board)
        if not in_check:
            moves = [
                move for move in moves
                if board.is_capture(move) or move.promotion is not None
            ]

        for move in moves:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, ply + 1)
            board.pop()
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha if not in_check else (alpha if moves else -MATE_SCORE + ply)

    def _negamax(
        self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int
    ) -> tuple[int, list[chess.Move]]:
        self.nodes += 1
        self._check_time()

        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal, []
        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply), []

        original_alpha = alpha
        key = self._key(board)
        entry = self.tt.get(key)
        tt_move = None
        if entry is not None:
            tt_move = entry.best_move
            if entry.depth >= depth:
                if entry.flag == "exact":
                    return entry.score, ([] if tt_move is None else [tt_move])
                if entry.flag == "lower":
                    alpha = max(alpha, entry.score)
                elif entry.flag == "upper":
                    beta = min(beta, entry.score)
                if alpha >= beta:
                    return entry.score, ([] if tt_move is None else [tt_move])

        best_score = -INF
        best_move = None
        best_pv: list[chess.Move] = []
        moves = self._ordered_moves(board, tt_move)

        for move in moves:
            board.push(move)
            child_score, child_pv = self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            score = -child_score
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
                best_pv = [move] + child_pv
            alpha = max(alpha, score)
            if alpha >= beta:
                break

        flag = "exact"
        if best_score <= original_alpha:
            flag = "upper"
        elif best_score >= beta:
            flag = "lower"

        if len(self.tt) >= self.tt_max_entries:
            # Simple bounded-table policy for the starter implementation.
            self.tt.clear()
        self.tt[key] = TTEntry(depth, best_score, flag, best_move)
        return best_score, best_pv

    def search(
        self,
        board: chess.Board,
        max_depth: int = 5,
        time_limit: Optional[float] = None,
    ) -> SearchResult:
        start = time.monotonic()
        self.deadline = None if time_limit is None else start + max(0.001, time_limit)
        self.nodes = 0
        self.root_side = board.turn

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            terminal = self._terminal_score(board, 0)
            return SearchResult(None, 0 if terminal is None else terminal, 0, self.nodes, [], time.monotonic() - start)

        best_move = legal_moves[0]
        best_score = 0
        best_pv: list[chess.Move] = [best_move]
        completed_depth = 0

        for depth in range(1, max_depth + 1):
            try:
                score, pv = self._negamax(board, depth, -INF, INF, 0)
                if pv:
                    best_pv = pv
                    best_move = pv[0]
                best_score = score
                completed_depth = depth
            except SearchTimeout:
                break

        return SearchResult(
            best_move=best_move,
            score=best_score,
            depth=completed_depth,
            nodes=self.nodes,
            pv=best_pv,
            elapsed=time.monotonic() - start,
        )
