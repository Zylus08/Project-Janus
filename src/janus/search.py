"""Single-threaded alpha-beta search for Project Janus."""
from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Optional

import chess

from .evaluation import evaluate_side_to_move

MATE_SCORE = 100_000
MATE_THRESHOLD = MATE_SCORE - 1_000
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
    score: int
    depth: int
    nodes: int
    pv: list[chess.Move]
    elapsed: float


class SearchTimeout(Exception):
    """Raised when a search is stopped or exceeds its time budget."""


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
        self.stop_event: Optional[threading.Event] = None

    @staticmethod
    def _key(board: chess.Board) -> str:
        # Repetition history is path-dependent and is not fully represented by FEN.
        return board.fen(en_passant="legal")

    @staticmethod
    def _score_to_tt(score: int, ply: int) -> int:
        """Normalize mate distance before storing a score in the TT."""
        if score >= MATE_THRESHOLD:
            return score + ply
        if score <= -MATE_THRESHOLD:
            return score - ply
        return score

    @staticmethod
    def _score_from_tt(score: int, ply: int) -> int:
        """Restore mate distance for the current search ply."""
        if score >= MATE_THRESHOLD:
            return score - ply
        if score <= -MATE_THRESHOLD:
            return score + ply
        return score

    def _check_stop(self) -> None:
        if self.stop_event is not None and self.stop_event.is_set():
            raise SearchTimeout
        if self.deadline is not None and (self.nodes & 255) == 0:
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
            values = {
                chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 335,
                chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000,
            }
            victim_value = 100 if board.is_en_passant(move) else (
                0 if victim is None else values[victim.piece_type]
            )
            attacker = board.piece_at(move.from_square)
            attacker_value = 0 if attacker is None else values[attacker.piece_type]
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
        self._check_stop()

        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal

        in_check = board.is_check()
        if ply >= self.qsearch_max_ply and not in_check:
            return evaluate_side_to_move(board)

        if not in_check:
            stand_pat = evaluate_side_to_move(board)
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)

        moves = self._ordered_moves(board)
        if not in_check:
            moves = [
                move for move in moves
                if board.is_capture(move) or move.promotion is not None
            ]

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

    def _negamax(
        self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int
    ) -> tuple[int, list[chess.Move]]:
        self.nodes += 1
        self._check_stop()

        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal, []
        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply), []

        alpha_original = alpha
        beta_original = beta
        key = self._key(board)
        entry = self.tt.get(key)
        tt_move = None

        if entry is not None:
            tt_move = entry.best_move
            tt_score = self._score_from_tt(entry.score, ply)

            # Do not let a cached root entry falsely report a new iteration complete.
            if ply > 0 and entry.depth >= depth:
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

        for move in self._ordered_moves(board, tt_move):
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
                break

        if best_move is None:
            return evaluate_side_to_move(board), []

        if len(self.tt) >= self.tt_max_entries:
            self.tt.clear()

        # Bound flags must be compared against the original search window.
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

    def search(
        self,
        board: chess.Board,
        max_depth: int = 5,
        time_limit: Optional[float] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> SearchResult:
        start = time.monotonic()
        self.deadline = None if time_limit is None else start + max(0.001, time_limit)
        self.stop_event = stop_event
        self.nodes = 0

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            terminal = self._terminal_score(board, 0)
            return SearchResult(
                None, 0 if terminal is None else terminal, 0, 0, [],
                time.monotonic() - start,
            )

        best_move = legal_moves[0]
        best_score = 0
        best_pv: list[chess.Move] = [best_move]
        completed_depth = 0

        for depth in range(1, max_depth + 1):
            try:
                score, pv = self._negamax(board, depth, -INF, INF, 0)
            except SearchTimeout:
                break

            # Only publish results from fully completed iterations.
            if pv:
                best_pv = pv
                best_move = pv[0]
            best_score = score
            completed_depth = depth

        return SearchResult(
            best_move=best_move,
            score=best_score,
            depth=completed_depth,
            nodes=self.nodes,
            pv=best_pv,
            elapsed=time.monotonic() - start,
        )
