"""Single-threaded alpha-beta search for Project Janus."""
from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Optional

import chess
import chess.polyglot

from .evaluation import evaluate_side_to_move
from .see import static_exchange_evaluation

MATE_SCORE = 100_000
MATE_THRESHOLD = MATE_SCORE - 1_000
INF = 1_000_000

MVV_LVA_PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 335,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}

MAX_HISTORY_SCORE = 500_000


@dataclass
class TTEntry:
    depth: int
    score: int
    flag: str  # "exact", "lower", "upper"
    best_move: Optional[chess.Move]


class TranspositionTable(dict):
    """Dictionary-compatible transposition table with support for secondary tiers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secondary: Optional[dict[int, TTEntry]] = None

    def clear(self) -> None:
        super().clear()
        if self.secondary is not None:
            self.secondary.clear()


@dataclass
class SearchResult:
    best_move: Optional[chess.Move]
    score: int
    depth: int
    nodes: int
    pv: list[chess.Move]
    elapsed: float
    scout_searches: int = 0
    scout_fail_highs: int = 0
    researches: int = 0
    beta_cutoffs: int = 0
    aspiration_iterations: int = 0
    aspiration_fail_lows: int = 0
    aspiration_fail_highs: int = 0
    aspiration_researches: int = 0
    aspiration_fallbacks: int = 0
    lmr_considered: int = 0
    lmr_reduced_searches: int = 0
    lmr_reduced_plies: int = 0
    lmr_researches: int = 0
    lmr_fail_lows: int = 0
    lmr_fail_highs: int = 0
    lmr_cutoffs: int = 0
    nmp_considered: int = 0
    nmp_attempts: int = 0
    nmp_fail_highs: int = 0
    nmp_fail_lows: int = 0
    nmp_verifications: int = 0
    nmp_verification_failures: int = 0
    nmp_cutoffs: int = 0
    check_extensions_eligible: int = 0
    check_extensions_applied: int = 0
    check_extension_plies: int = 0
    check_extensions_suppressed: int = 0
    check_extensions_multiple_replies: int = 0
    check_extensions_terminal_mates: int = 0
    check_extension_policy: str = "disabled"
    enable_see_ordering: bool = False
    enable_see_pruning: bool = False
    see_evaluations: int = 0
    captures_ordered_see: int = 0
    qsearch_captures_considered: int = 0
    qsearch_captures_pruned: int = 0
    qsearch_captures_exempted: int = 0
    see_cache_hits: int = 0
    tt_replacement_policy: str = "always_replace"
    tt_probes: int = 0
    tt_hits: int = 0
    tt_usable_hits: int = 0
    tt_cutoffs: int = 0
    tt_stores: int = 0
    tt_same_key_updates: int = 0
    tt_same_key_overwrites: int = 0
    tt_same_key_rejected: int = 0
    tt_clears: int = 0


class SearchTimeout(Exception):
    """Raised when a search is stopped or exceeds its time budget."""


class JanusSearch:
    def __init__(
        self,
        tt_max_entries: int = 200_000,
        qsearch_max_ply: int = 12,
        max_killers_ply: int = 64,
        enable_history: bool = True,
        enable_pvs: bool = True,
        enable_aspiration: bool = True,
        aspiration_delta: int = 35,
        max_aspiration_retries: int = 3,
        enable_lmr: bool = True,
        enable_nmp: bool = True,
        nmp_reduction: int = 2,
        enable_nmp_verification: bool = True,
        nmp_verify_min_depth: int = 5,
        check_extension_policy: str = "disabled",
        enable_check_extensions: Optional[bool] = None,
        max_check_extensions: int = 2,
        enable_see_ordering: bool = False,
        enable_see_pruning: bool = False,
        tt_replacement_policy: str = "always_replace",
    ) -> None:
        valid_tt_policies = ("always_replace", "depth_preferred", "two_tier")
        if tt_replacement_policy not in valid_tt_policies:
            raise ValueError(
                f"Unknown tt_replacement_policy {tt_replacement_policy!r}. "
                f"Valid options: {valid_tt_policies}"
            )
        self.tt_replacement_policy = tt_replacement_policy
        self.tt: TranspositionTable = TranspositionTable()
        self.tt_recent: dict[int, TTEntry] = {}
        if self.tt_replacement_policy == "two_tier":
            self.tt.secondary = self.tt_recent
        self.tt_max_entries = tt_max_entries
        self.qsearch_max_ply = qsearch_max_ply
        self.max_killers_ply = max_killers_ply
        self.enable_history = enable_history
        self.enable_pvs = enable_pvs
        self.enable_aspiration = enable_aspiration
        self.aspiration_delta = aspiration_delta
        self.max_aspiration_retries = max_aspiration_retries
        self.enable_lmr = enable_lmr
        self.enable_nmp = enable_nmp
        self.nmp_reduction = nmp_reduction
        self.enable_nmp_verification = enable_nmp_verification
        self.nmp_verify_min_depth = nmp_verify_min_depth
        self.enable_see_ordering = enable_see_ordering
        self.enable_see_pruning = enable_see_pruning

        valid_policies = ("disabled", "bounded_all_checks", "single_reply")
        if check_extension_policy not in valid_policies:
            raise ValueError(
                f"Unknown check extension policy {check_extension_policy!r}. "
                f"Valid options: {valid_policies}"
            )
        if enable_check_extensions is not None:
            if enable_check_extensions:
                self.check_extension_policy = (
                    "bounded_all_checks"
                    if check_extension_policy == "disabled"
                    else check_extension_policy
                )
            else:
                self.check_extension_policy = "disabled"
        else:
            self.check_extension_policy = check_extension_policy
        self.enable_check_extensions = (self.check_extension_policy != "disabled")
        self.max_check_extensions = max_check_extensions
        self._extensions_at_ply: list[int] = [0] * 256
        self.killers: list[list[Optional[chess.Move]]] = [
            [None, None] for _ in range(self.max_killers_ply)
        ]
        self.history: list[list[int]] = [[0] * 64 for _ in range(64)]
        self.nodes = 0
        self.scout_searches = 0
        self.scout_fail_highs = 0
        self.researches = 0
        self.beta_cutoffs = 0
        self.aspiration_iterations = 0
        self.aspiration_fail_lows = 0
        self.aspiration_fail_highs = 0
        self.aspiration_researches = 0
        self.aspiration_fallbacks = 0
        self.lmr_considered = 0
        self.lmr_reduced_searches = 0
        self.lmr_reduced_plies = 0
        self.lmr_researches = 0
        self.lmr_fail_lows = 0
        self.lmr_fail_highs = 0
        self.lmr_cutoffs = 0
        self.nmp_considered = 0
        self.nmp_attempts = 0
        self.nmp_fail_highs = 0
        self.nmp_fail_lows = 0
        self.nmp_verifications = 0
        self.nmp_verification_failures = 0
        self.nmp_cutoffs = 0
        self.check_extensions_eligible = 0
        self.check_extensions_applied = 0
        self.check_extension_plies = 0
        self.check_extensions_suppressed = 0
        self.check_extensions_multiple_replies = 0
        self.check_extensions_terminal_mates = 0
        self.see_evaluations = 0
        self.captures_ordered_see = 0
        self.qsearch_captures_considered = 0
        self.qsearch_captures_pruned = 0
        self.qsearch_captures_exempted = 0
        self.see_cache_hits = 0
        self.tt_probes = 0
        self.tt_hits = 0
        self.tt_usable_hits = 0
        self.tt_cutoffs = 0
        self.tt_stores = 0
        self.tt_same_key_updates = 0
        self.tt_same_key_overwrites = 0
        self.tt_same_key_rejected = 0
        self.tt_clears = 0
        self.deadline: Optional[float] = None
        self.stop_event: Optional[threading.Event] = None

    def _probe_tt(
        self, key: int, effective_depth: int
    ) -> tuple[Optional[TTEntry], Optional[chess.Move]]:
        """Probe transposition table according to configured replacement policy."""
        self.tt_probes += 1

        if self.tt_replacement_policy == "two_tier":
            entry_deep = self.tt.get(key)
            entry_recent = self.tt_recent.get(key)
            if entry_deep is not None and entry_deep.depth >= effective_depth:
                entry = entry_deep
            elif entry_recent is not None and entry_recent.depth >= effective_depth:
                entry = entry_recent
            else:
                entry = entry_deep if entry_deep is not None else entry_recent
            tt_move = (
                entry_deep.best_move if (entry_deep and entry_deep.best_move)
                else (entry_recent.best_move if entry_recent else None)
            )
        else:
            entry = self.tt.get(key)
            tt_move = entry.best_move if entry is not None else None

        if entry is not None:
            self.tt_hits += 1

        return entry, tt_move

    def _store_tt(
        self,
        key: int,
        depth: int,
        score: int,
        flag: str,
        best_move: Optional[chess.Move],
        ply: int,
    ) -> None:
        """Store search result into transposition table using configured replacement policy."""
        self.tt_stores += 1
        tt_score = self._score_to_tt(score, ply)

        if self.tt_replacement_policy == "always_replace":
            if key in self.tt:
                self.tt_same_key_updates += 1
                self.tt_same_key_overwrites += 1
            if len(self.tt) >= self.tt_max_entries and key not in self.tt:
                self.tt.clear()
                self.tt_clears += 1
            self.tt[key] = TTEntry(
                depth=depth,
                score=tt_score,
                flag=flag,
                best_move=best_move,
            )

        elif self.tt_replacement_policy == "depth_preferred":
            if key in self.tt:
                self.tt_same_key_updates += 1
                old = self.tt[key]
                # Protect deeper entries against shallower updates
                replace = (depth >= old.depth)
                if replace:
                    self.tt_same_key_overwrites += 1
                    final_move = best_move if best_move is not None else old.best_move
                    self.tt[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=final_move,
                    )
                else:
                    self.tt_same_key_rejected += 1
                    if old.best_move is None and best_move is not None:
                        old.best_move = best_move
            else:
                if len(self.tt) >= self.tt_max_entries:
                    self.tt.clear()
                    self.tt_clears += 1
                self.tt[key] = TTEntry(
                    depth=depth,
                    score=tt_score,
                    flag=flag,
                    best_move=best_move,
                )

        elif self.tt_replacement_policy == "two_tier":
            tier_capacity = max(1, self.tt_max_entries // 2)
            if key in self.tt:
                self.tt_same_key_updates += 1
                old = self.tt[key]
                replace = (depth >= old.depth)
                if replace:
                    self.tt_same_key_overwrites += 1
                    final_move = best_move if best_move is not None else old.best_move
                    self.tt[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=final_move,
                    )
                else:
                    self.tt_same_key_rejected += 1
                    if old.best_move is None and best_move is not None:
                        old.best_move = best_move
                    if len(self.tt_recent) >= tier_capacity and key not in self.tt_recent:
                        self.tt_recent.clear()
                        self.tt_clears += 1
                    self.tt_recent[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=best_move,
                    )
            elif key in self.tt_recent:
                self.tt_same_key_updates += 1
                if depth >= 2:
                    if len(self.tt) >= tier_capacity and key not in self.tt:
                        dict.clear(self.tt)
                        self.tt_clears += 1
                    self.tt_same_key_overwrites += 1
                    self.tt_recent.pop(key, None)
                    self.tt[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=best_move,
                    )
                else:
                    self.tt_same_key_overwrites += 1
                    self.tt_recent[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=best_move,
                    )
            else:
                if depth >= 2:
                    if len(self.tt) >= tier_capacity:
                        dict.clear(self.tt)
                        self.tt_clears += 1
                    self.tt[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=best_move,
                    )
                else:
                    if len(self.tt_recent) >= tier_capacity:
                        self.tt_recent.clear()
                        self.tt_clears += 1
                    self.tt_recent[key] = TTEntry(
                        depth=depth,
                        score=tt_score,
                        flag=flag,
                        best_move=best_move,
                    )

    def _see(self, board: chess.Board, move: chess.Move) -> int:
        """Evaluate static exchange evaluation with telemetry tracking."""
        self.see_evaluations += 1
        return static_exchange_evaluation(board, move, check_legality=False)

    def _update_history(self, move: chess.Move, depth: int) -> None:
        """Reward a quiet move causing a beta cutoff with a depth-sensitive bonus."""
        if not self.enable_history:
            return
        bonus = depth * depth
        from_sq = move.from_square
        to_sq = move.to_square
        self.history[from_sq][to_sq] = min(
            MAX_HISTORY_SCORE, self.history[from_sq][to_sq] + bonus
        )

    @staticmethod
    def _key(board: chess.Board) -> int:
        """Return a 64-bit integer Polyglot Zobrist hash of the current position."""
        return chess.polyglot.zobrist_hash(board)

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

    def _has_nmp_material(self, board: chess.Board) -> bool:
        """Verify the side to move has sufficient non-pawn material to reduce zugzwang risk.

        Excludes:
        - Pawn-only endgames (K+P vs ...)
        - Single minor piece endgames (K+N or K+B vs ...)

        Requires at least 1 Queen, 1 Rook, or >= 2 minor pieces (Knights/Bishops).
        """
        side = board.turn
        knights = len(board.pieces(chess.KNIGHT, side))
        bishops = len(board.pieces(chess.BISHOP, side))
        rooks = len(board.pieces(chess.ROOK, side))
        queens = len(board.pieces(chess.QUEEN, side))
        return queens >= 1 or rooks >= 1 or (knights + bishops >= 2)

    def _should_verify_nmp(self, board: chess.Board, depth: int) -> bool:
        """Determine whether a candidate NMP fail-high requires a verification search."""
        if not self.enable_nmp_verification:
            return False
        if depth >= self.nmp_verify_min_depth:
            return True
        side = board.turn
        opp = not side
        side_pieces = (
            len(board.pieces(chess.KNIGHT, side))
            + len(board.pieces(chess.BISHOP, side))
            + len(board.pieces(chess.ROOK, side))
            + len(board.pieces(chess.QUEEN, side))
        )
        opp_pieces = (
            len(board.pieces(chess.KNIGHT, opp))
            + len(board.pieces(chess.BISHOP, opp))
            + len(board.pieces(chess.ROOK, opp))
            + len(board.pieces(chess.QUEEN, opp))
        )
        return side_pieces <= 2 or opp_pieces <= 1

    def _check_stop(self) -> None:
        if self.stop_event is not None and self.stop_event.is_set():
            raise SearchTimeout
        if self.deadline is not None and (self.nodes & 255) == 0:
            if time.monotonic() >= self.deadline:
                raise SearchTimeout

    def _terminal_score(self, board: chess.Board, ply: int = 0) -> Optional[int]:
        if (
            board.is_insufficient_material()
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0
        if board.is_check():
            if not any(board.generate_legal_moves()):
                return -MATE_SCORE + ply
        elif not any(board.generate_legal_moves()):
            return 0
        return None

    def _move_order_score(
        self,
        board: chess.Board,
        move: chess.Move,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
        node_see: Optional[dict[chess.Move, int]] = None,
    ) -> int:
        if tt_move is not None and move == tt_move:
            return 10_000_000

        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            victim_value = 100 if board.is_en_passant(move) else (
                0 if victim is None else MVV_LVA_PIECE_VALUES[victim.piece_type]
            )
            attacker = board.piece_at(move.from_square)
            attacker_value = (
                0 if attacker is None else MVV_LVA_PIECE_VALUES[attacker.piece_type]
            )
            mvv_lva = 10 * victim_value - attacker_value

            if self.enable_see_ordering:
                self.captures_ordered_see += 1
                if node_see is not None and move in node_see:
                    self.see_cache_hits += 1
                    see_val = node_see[move]
                else:
                    see_val = self._see(board, move)
                    if node_see is not None:
                        node_see[move] = see_val

                if see_val >= 0:
                    score = 1_000_000 + see_val * 100 + mvv_lva
                else:
                    # Demote losing captures below killers and quiet history moves
                    score = 50_000 + see_val * 10 + mvv_lva
            else:
                score = 1_000_000 + mvv_lva

            if move.promotion:
                score += 800_000 + move.promotion

        if move.promotion:
            return 800_000 + move.promotion

        if score == 0 and ply < len(self.killers):
            if move == self.killers[ply][0]:
                return 700_000
            if move == self.killers[ply][1]:
                return 600_000

        if score == 0 and self.enable_history:
            return self.history[move.from_square][move.to_square]

        return score

    @staticmethod
    def _quiescence_moves(board: chess.Board) -> list[chess.Move]:
        moves = list(board.generate_legal_captures())
        pawn_mask = board.pawns & board.occupied_co[board.turn]
        seventh_rank = chess.BB_RANK_7 if board.turn == chess.WHITE else chess.BB_RANK_2
        candidate_pawns = pawn_mask & seventh_rank
        if candidate_pawns:
            eighth_rank = chess.BB_RANK_8 if board.turn == chess.WHITE else chess.BB_RANK_1
            empty_squares = ~board.occupied
            for move in board.generate_legal_moves(
                from_mask=candidate_pawns, to_mask=eighth_rank & empty_squares
            ):
                if move.promotion is not None:
                    moves.append(move)
        return moves

    def _ordered_moves(
        self,
        board: chess.Board,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
    ) -> list[chess.Move]:
        moves = list(board.legal_moves)
        if len(moves) <= 1:
            return moves

        node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
        moves.sort(
            key=lambda move: self._move_order_score(board, move, tt_move, ply, node_see=node_see),
            reverse=True,
        )
        return moves

    def _quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int) -> int:
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

        node_see: Optional[dict[chess.Move, int]] = (
            {} if (self.enable_see_ordering or self.enable_see_pruning) else None
        )

        if not in_check:
            if not any(board.generate_legal_moves()):
                return 0
            stand_pat = evaluate_side_to_move(board)
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)
            moves = self._quiescence_moves(board)
            moves.sort(
                key=lambda move: self._move_order_score(board, move, None, ply, node_see=node_see),
                reverse=True,
            )
        else:
            moves = self._ordered_moves(board, None, ply)

        if in_check and not moves:
            return -MATE_SCORE + ply

        for move in moves:
            if not in_check and self.enable_see_pruning:
                self.qsearch_captures_considered += 1
                if move.promotion is not None:
                    self.qsearch_captures_exempted += 1
                elif board.gives_check(move):
                    self.qsearch_captures_exempted += 1
                else:
                    if node_see is not None and move in node_see:
                        self.see_cache_hits += 1
                        see_val = node_see[move]
                    else:
                        see_val = self._see(board, move)
                        if node_see is not None:
                            node_see[move] = see_val

                    if see_val < 0:
                        self.qsearch_captures_pruned += 1
                        continue
                    self.qsearch_captures_exempted += 1

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
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        ply: int,
        allow_nmp: bool = True,
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

        in_check = board.is_check()

        # Check Extensions
        extension = 0
        current_ext = self._extensions_at_ply[ply] if ply < len(self._extensions_at_ply) else 0
        next_extensions = current_ext
        if in_check and depth > 0:
            self.check_extensions_eligible += 1
            if self.check_extension_policy == "bounded_all_checks":
                if current_ext < self.max_check_extensions:
                    extension = 1
                    self.check_extensions_applied += 1
                    self.check_extension_plies += 1
                    next_extensions = current_ext + 1
                else:
                    self.check_extensions_suppressed += 1
            elif self.check_extension_policy == "single_reply":
                legal_gen = board.generate_legal_moves()
                first_evasion = next(legal_gen, None)
                if first_evasion is None:
                    # Terminal / checkmate - do not grant continuation extension
                    pass
                else:
                    second_evasion = next(legal_gen, None)
                    if second_evasion is not None:
                        # Multiple legal replies: rejected by single_reply policy
                        self.check_extensions_multiple_replies += 1
                    else:
                        # Exactly one legal reply
                        if current_ext < self.max_check_extensions:
                            extension = 1
                            self.check_extensions_applied += 1
                            self.check_extension_plies += 1
                            next_extensions = current_ext + 1
                        else:
                            self.check_extensions_suppressed += 1

        effective_depth = depth + extension
        if ply + 1 < len(self._extensions_at_ply):
            self._extensions_at_ply[ply + 1] = next_extensions

        alpha_original = alpha
        beta_original = beta
        key = self._key(board)
        entry, tt_move = self._probe_tt(key, effective_depth)

        if entry is not None:
            tt_score = self._score_from_tt(entry.score, ply)

            # Do not let a cached root entry falsely report a new iteration complete.
            # In addition, near the seventy-five-move draw threshold, non-zero cached scores
            # cannot guarantee that a forced draw won't intervene within the search horizon.
            if ply > 0 and entry.depth >= effective_depth:
                if (board.halfmove_clock + effective_depth < 150) or entry.score == 0:
                    self.tt_usable_hits += 1
                    if entry.flag == "exact":
                        self.tt_cutoffs += 1
                        return tt_score, ([] if tt_move is None else [tt_move])
                    if entry.flag == "lower":
                        alpha = max(alpha, tt_score)
                    elif entry.flag == "upper":
                        beta = min(beta, tt_score)
                    if alpha >= beta:
                        self.tt_cutoffs += 1
                        return tt_score, ([] if tt_move is None else [tt_move])

        # Conservative Null Move Pruning (NMP)
        if (
            self.enable_nmp
            and allow_nmp
            and ply > 0
            and depth >= 3
            and not in_check
            and abs(beta) < MATE_THRESHOLD
            and board.halfmove_clock < 140
            and not (len(board.move_stack) > 0 and board.peek() == chess.Move.null())
            and self._has_nmp_material(board)
        ):
            self.nmp_considered += 1
            self.nmp_attempts += 1
            reduced_depth = max(0, depth - 1 - self.nmp_reduction)

            board.push(chess.Move.null())
            try:
                child_score, _ = self._negamax(
                    board, reduced_depth, -beta, -beta + 1, ply + 1, allow_nmp=False
                )
                null_score = -child_score
            finally:
                board.pop()

            if null_score >= beta:
                self.nmp_fail_highs += 1
                verify_cutoff = True
                if self._should_verify_nmp(board, depth):
                    self.nmp_verifications += 1
                    v_depth = max(1, depth - self.nmp_reduction)
                    v_score, _ = self._negamax(
                        board, v_depth, beta - 1, beta, ply, allow_nmp=False
                    )
                    if v_score < beta:
                        self.nmp_verification_failures += 1
                        verify_cutoff = False

                if verify_cutoff:
                    self.nmp_cutoffs += 1
                    self._store_tt(key, depth, beta, "lower", tt_move, ply)
                    return beta, []
            else:
                self.nmp_fail_lows += 1

        best_score = -INF
        best_move = None
        best_pv: list[chess.Move] = []

        moves = self._ordered_moves(board, tt_move, ply)
        if not moves:
            if in_check:
                if extension > 0:
                    self.check_extensions_terminal_mates += 1
                return -MATE_SCORE + ply, []
            return 0, []

        moves_searched = 0

        for move in moves:
            is_capture = board.is_capture(move)
            is_promotion = move.promotion is not None
            gives_check = board.gives_check(move)

            eligible_for_lmr = (
                self.enable_lmr
                and moves_searched >= 3
                and depth >= 3
                and ply > 0
                and not in_check
                and not is_capture
                and not is_promotion
                and not gives_check
                and (
                    ply >= len(self.killers)
                    or (move != self.killers[ply][0] and move != self.killers[ply][1])
                )
            )

            board.push(move)
            try:
                if eligible_for_lmr:
                    self.lmr_considered += 1
                    reduction = 1
                    reduced_depth = max(1, effective_depth - 1 - reduction)
                    self.lmr_reduced_searches += 1
                    self.lmr_reduced_plies += (effective_depth - 1 - reduced_depth)

                    if self.enable_pvs:
                        child_score, child_pv = self._negamax(
                            board, reduced_depth, -alpha - 1, -alpha, ply + 1
                        )
                        score = -child_score

                        if score > alpha:
                            self.lmr_fail_highs += 1
                            self.lmr_researches += 1
                            self.scout_searches += 1
                            child_score, child_pv = self._negamax(
                                board, effective_depth - 1, -alpha - 1, -alpha, ply + 1
                            )
                            score = -child_score
                            if score > alpha:
                                self.scout_fail_highs += 1
                                if score < beta:
                                    self.researches += 1
                                    child_score, child_pv = self._negamax(
                                        board, effective_depth - 1, -beta, -alpha, ply + 1
                                    )
                                    score = -child_score
                        else:
                            self.lmr_fail_lows += 1
                    else:
                        child_score, child_pv = self._negamax(
                            board, reduced_depth, -beta, -alpha, ply + 1
                        )
                        score = -child_score
                        if score > alpha:
                            self.lmr_fail_highs += 1
                            self.lmr_researches += 1
                            child_score, child_pv = self._negamax(
                                board, effective_depth - 1, -beta, -alpha, ply + 1
                            )
                            score = -child_score
                        else:
                            self.lmr_fail_lows += 1

                elif self.enable_pvs and moves_searched > 0 and effective_depth >= 2:
                    # Null-window scout search [-alpha - 1, -alpha]
                    self.scout_searches += 1
                    child_score, child_pv = self._negamax(
                        board, effective_depth - 1, -alpha - 1, -alpha, ply + 1
                    )
                    score = -child_score

                    if score > alpha:
                        self.scout_fail_highs += 1
                        if score < beta:
                            self.researches += 1
                            child_score, child_pv = self._negamax(
                                board, effective_depth - 1, -beta, -alpha, ply + 1
                            )
                            score = -child_score
                else:
                    # Full-window search (first move, shallow depth, or PVS disabled)
                    child_score, child_pv = self._negamax(
                        board, effective_depth - 1, -beta, -alpha, ply + 1
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
                if eligible_for_lmr:
                    self.lmr_cutoffs += 1
                if not is_capture and not is_promotion:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                    self._update_history(move, depth)
                break

        # Bound flags must be compared against the original search window.
        if best_score <= alpha_original:
            flag = "upper"
        elif best_score >= beta_original:
            flag = "lower"
        else:
            flag = "exact"

        self._store_tt(key, effective_depth, best_score, flag, best_move, ply)
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
        self.scout_searches = 0
        self.scout_fail_highs = 0
        self.researches = 0
        self.beta_cutoffs = 0
        self.aspiration_iterations = 0
        self.aspiration_fail_lows = 0
        self.aspiration_fail_highs = 0
        self.aspiration_researches = 0
        self.aspiration_fallbacks = 0
        self.lmr_considered = 0
        self.lmr_reduced_searches = 0
        self.lmr_reduced_plies = 0
        self.lmr_researches = 0
        self.lmr_fail_lows = 0
        self.lmr_fail_highs = 0
        self.lmr_cutoffs = 0
        self.nmp_considered = 0
        self.nmp_attempts = 0
        self.nmp_fail_highs = 0
        self.nmp_fail_lows = 0
        self.nmp_verifications = 0
        self.nmp_verification_failures = 0
        self.nmp_cutoffs = 0
        self.check_extensions_eligible = 0
        self.check_extensions_applied = 0
        self.check_extension_plies = 0
        self.check_extensions_suppressed = 0
        self.check_extensions_multiple_replies = 0
        self.check_extensions_terminal_mates = 0
        self.see_evaluations = 0
        self.captures_ordered_see = 0
        self.qsearch_captures_considered = 0
        self.qsearch_captures_pruned = 0
        self.qsearch_captures_exempted = 0
        self.see_cache_hits = 0
        self.tt_probes = 0
        self.tt_hits = 0
        self.tt_usable_hits = 0
        self.tt_cutoffs = 0
        self.tt_stores = 0
        self.tt_same_key_updates = 0
        self.tt_same_key_overwrites = 0
        self.tt_same_key_rejected = 0
        self.tt_clears = 0
        self._extensions_at_ply = [0] * 256
        self.killers = [[None, None] for _ in range(self.max_killers_ply)]
        self.history = [[0] * 64 for _ in range(64)]

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            score = -MATE_SCORE if board.is_check() else 0
            return SearchResult(
                best_move=None,
                score=score,
                depth=0,
                nodes=0,
                pv=[],
                elapsed=time.monotonic() - start,
                check_extension_policy=self.check_extension_policy,
                enable_see_ordering=self.enable_see_ordering,
                enable_see_pruning=self.enable_see_pruning,
                see_evaluations=0,
                captures_ordered_see=0,
                qsearch_captures_considered=0,
                qsearch_captures_pruned=0,
                qsearch_captures_exempted=0,
                see_cache_hits=0,
                tt_replacement_policy=self.tt_replacement_policy,
                tt_probes=0,
                tt_hits=0,
                tt_usable_hits=0,
                tt_cutoffs=0,
                tt_stores=0,
                tt_same_key_updates=0,
                tt_same_key_overwrites=0,
                tt_same_key_rejected=0,
                tt_clears=0,
            )

        best_move = legal_moves[0]
        best_score = 0
        best_pv: list[chess.Move] = [best_move]
        completed_depth = 0

        for depth in range(1, max_depth + 1):
            use_aspiration = (
                self.enable_aspiration
                and depth >= 2
                and abs(best_score) < MATE_THRESHOLD
            )

            if not use_aspiration:
                try:
                    score, pv = self._negamax(board, depth, -INF, INF, 0)
                except SearchTimeout:
                    break
            else:
                self.aspiration_iterations += 1
                cur_delta = self.aspiration_delta
                alpha = max(-INF, best_score - cur_delta)
                beta = min(INF, best_score + cur_delta)
                retries = 0

                try:
                    while True:
                        score, pv = self._negamax(board, depth, alpha, beta, 0)

                        if score <= alpha:
                            self.aspiration_fail_lows += 1
                            self.aspiration_researches += 1
                            retries += 1
                            if retries >= self.max_aspiration_retries or alpha <= -MATE_THRESHOLD:
                                alpha = -INF
                                beta = INF
                                self.aspiration_fallbacks += 1
                            else:
                                cur_delta *= 2
                                alpha = max(-INF, best_score - cur_delta)
                        elif score >= beta:
                            self.aspiration_fail_highs += 1
                            self.aspiration_researches += 1
                            retries += 1
                            if retries >= self.max_aspiration_retries or beta >= MATE_THRESHOLD:
                                alpha = -INF
                                beta = INF
                                self.aspiration_fallbacks += 1
                            else:
                                cur_delta *= 2
                                beta = min(INF, best_score + cur_delta)
                        else:
                            break
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
            scout_searches=self.scout_searches,
            scout_fail_highs=self.scout_fail_highs,
            researches=self.researches,
            beta_cutoffs=self.beta_cutoffs,
            aspiration_iterations=self.aspiration_iterations,
            aspiration_fail_lows=self.aspiration_fail_lows,
            aspiration_fail_highs=self.aspiration_fail_highs,
            aspiration_researches=self.aspiration_researches,
            aspiration_fallbacks=self.aspiration_fallbacks,
            lmr_considered=self.lmr_considered,
            lmr_reduced_searches=self.lmr_reduced_searches,
            lmr_reduced_plies=self.lmr_reduced_plies,
            lmr_researches=self.lmr_researches,
            lmr_fail_lows=self.lmr_fail_lows,
            lmr_fail_highs=self.lmr_fail_highs,
            lmr_cutoffs=self.lmr_cutoffs,
            nmp_considered=self.nmp_considered,
            nmp_attempts=self.nmp_attempts,
            nmp_fail_highs=self.nmp_fail_highs,
            nmp_fail_lows=self.nmp_fail_lows,
            nmp_verifications=self.nmp_verifications,
            nmp_verification_failures=self.nmp_verification_failures,
            nmp_cutoffs=self.nmp_cutoffs,
            check_extensions_eligible=self.check_extensions_eligible,
            check_extensions_applied=self.check_extensions_applied,
            check_extension_plies=self.check_extension_plies,
            check_extensions_suppressed=self.check_extensions_suppressed,
            check_extensions_multiple_replies=self.check_extensions_multiple_replies,
            check_extensions_terminal_mates=self.check_extensions_terminal_mates,
            check_extension_policy=self.check_extension_policy,
            enable_see_ordering=self.enable_see_ordering,
            enable_see_pruning=self.enable_see_pruning,
            see_evaluations=self.see_evaluations,
            captures_ordered_see=self.captures_ordered_see,
            qsearch_captures_considered=self.qsearch_captures_considered,
            qsearch_captures_pruned=self.qsearch_captures_pruned,
            qsearch_captures_exempted=self.qsearch_captures_exempted,
            see_cache_hits=self.see_cache_hits,
            tt_replacement_policy=self.tt_replacement_policy,
            tt_probes=self.tt_probes,
            tt_hits=self.tt_hits,
            tt_usable_hits=self.tt_usable_hits,
            tt_cutoffs=self.tt_cutoffs,
            tt_stores=self.tt_stores,
            tt_same_key_updates=self.tt_same_key_updates,
            tt_same_key_overwrites=self.tt_same_key_overwrites,
            tt_same_key_rejected=self.tt_same_key_rejected,
            tt_clears=self.tt_clears,
        )
