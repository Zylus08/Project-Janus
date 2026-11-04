"""Single-threaded alpha-beta search for Project Janus."""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Optional

import chess
import chess.polyglot

from .evaluation import evaluate_side_to_move, EvaluationConfig
from .see import static_exchange_evaluation
from .time_manager import TimeManager, TimeManagerConfig

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
    countermove_cutoffs: int = 0
    rfp_considered: int = 0
    rfp_cutoffs: int = 0
    rfp_events: list[dict] = field(default_factory=list)
    iteration_records: list[dict] = field(default_factory=list)
    ordering_stats: dict = field(default_factory=dict)
    ordering_events: list[dict] = field(default_factory=list)


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
        enable_qsearch_checks: bool = False,
        qsearch_checks_max_ply: int = 1,
        tt_replacement_policy: str = "always_replace",
        eval_config: Optional[EvaluationConfig] = None,
        time_manager: Optional[TimeManager] = None,
        enable_countermoves: bool = False,
        enable_history_malus: bool = False,
        enable_rfp: bool = False,
        rfp_max_depth: int = 2,
        rfp_margin_per_depth: int = 120,
        diagnostic_rfp: bool = False,
        diagnostic_iterations: bool = False,
        diagnostic_ordering: bool = False,
        enable_lazy_move_selection: bool = False,
    ) -> None:
        self.time_manager = time_manager or TimeManager()
        self.eval_config = eval_config
        self.enable_qsearch_checks = enable_qsearch_checks
        self.qsearch_checks_max_ply = qsearch_checks_max_ply
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
        self.enable_countermoves = enable_countermoves
        self.enable_history_malus = enable_history_malus
        self.enable_rfp = enable_rfp
        self.rfp_max_depth = rfp_max_depth
        self.rfp_margin_per_depth = rfp_margin_per_depth
        self.diagnostic_rfp = diagnostic_rfp
        self.rfp_events: list[dict] = []
        self.diagnostic_iterations = diagnostic_iterations
        self.iteration_records: list[dict] = []
        self.diagnostic_ordering = diagnostic_ordering
        self.enable_lazy_move_selection = enable_lazy_move_selection
        self.lazy_sorts_deferred = 0
        self.lazy_sorts_executed = 0
        self.lazy_sorts_saved = 0
        self.ordering_events: list[dict] = []
        self.ordering_total_cutoffs = 0
        self.first_move_cutoffs = 0
        self.late_move_cutoffs = 0
        self.tt_cutoffs_count = 0
        self.killer_cutoffs = 0
        self.countermove_cutoffs_count = 0
        self.capture_cutoffs = 0
        self.quiet_cutoffs = 0
        self.total_movegen_time = 0.0
        self.total_ordering_time = 0.0
        self.countermoves: list[list[Optional[chess.Move]]] = [
            [None] * 64 for _ in range(64)
        ]
        self.countermove_cutoffs = 0
        self.rfp_considered = 0
        self.rfp_cutoffs = 0
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

    def flush_ordering_telemetry(self, filepath: str) -> int:
        """Flush recorded move ordering telemetry records to a JSONL file and clear buffer."""
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = len(self.ordering_events)
        with open(p, "a", encoding="utf-8") as f:
            for rec in self.ordering_events:
                f.write(json.dumps(rec) + "\n")
        self.ordering_events.clear()
        return count

    def flush_iteration_telemetry(self, filepath: str) -> int:
        """Flush recorded iteration telemetry records to a JSONL file and clear buffer."""
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = len(self.iteration_records)
        with open(p, "a", encoding="utf-8") as f:
            for rec in self.iteration_records:
                f.write(json.dumps(rec) + "\n")
        self.iteration_records.clear()
        return count

    def _record_iteration(
        self, depth: int, start_t: float, end_t: float, nodes_start: int,
        score: int, pv: list[chess.Move], completed: bool, aborted: bool,
        abort_reason: Optional[str], published: bool, prev_depth: int, retries: int
    ) -> None:
        elapsed = end_t - start_t
        nodes_consumed = self.nodes - nodes_start
        nps = int(nodes_consumed / elapsed) if elapsed > 0 else 0
        self.iteration_records.append({
            "iteration_depth": depth,
            "iteration_start_time": start_t,
            "iteration_end_time": end_t,
            "iteration_elapsed_s": elapsed,
            "nodes_consumed": nodes_consumed,
            "cumulative_nodes": self.nodes,
            "nps": nps,
            "best_move": pv[0].uci() if pv else None,
            "pv": [m.uci() for m in pv],
            "score": score,
            "aspiration_retries": retries,
            "completed": completed,
            "aborted": aborted,
            "abort_reason": abort_reason,
            "published": published,
            "prev_completed_depth": prev_depth,
            "rfp_enabled": self.enable_rfp,
        })

    def flush_rfp_telemetry(self, filepath: str) -> int:
        """Flush recorded RFP diagnostic events to a JSONL file and clear buffer."""
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = len(self.rfp_events)
        with open(p, "a", encoding="utf-8") as f:
            for ev in self.rfp_events:
                f.write(json.dumps(ev) + "\n")
        self.rfp_events.clear()
        return count

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
        if self.deadline is not None and (self.nodes & 127) == 0:
            if time.monotonic() >= self.deadline:
                raise SearchTimeout

    def _terminal_score(self, board: chess.Board, ply: int = 0) -> Optional[int]:
        if (
            board.is_insufficient_material()
            or (ply > 0 and board.is_repetition(3))
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
        prev_move: Optional[chess.Move] = None,
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

        if score == 0 and self.enable_countermoves and prev_move is not None:
            if move == self.countermoves[prev_move.from_square][prev_move.to_square]:
                return 550_000

        if score == 0 and self.enable_history:
            return self.history[move.from_square][move.to_square]

        return score

    def _quiescence_moves(self, board: chess.Board, include_checks: bool = False) -> list[chess.Move]:
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
        if include_checks:
            cap_set = set(moves)
            for move in board.legal_moves:
                if move not in cap_set and board.gives_check(move):
                    if not self.enable_see_pruning or self._see(board, move) >= 0:
                        moves.append(move)
        return moves

    def _ordered_moves(
        self,
        board: chess.Board,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
        prev_move: Optional[chess.Move] = None,
    ) -> list[chess.Move]:
        moves = list(board.legal_moves)
        if len(moves) <= 1:
            return moves

        node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
        if self.diagnostic_ordering:
            t0 = time.perf_counter()
            moves.sort(
                key=lambda move: self._move_order_score(
                    board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
                ),
                reverse=True,
            )
            self.total_ordering_time += (time.perf_counter() - t0)
        else:
            moves.sort(
                key=lambda move: self._move_order_score(
                    board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
                ),
                reverse=True,
            )
        return moves

    def _select_ordered_moves(
        self,
        board: chess.Board,
        tt_move: Optional[chess.Move] = None,
        ply: int = 0,
        prev_move: Optional[chess.Move] = None,
    ):
        moves = list(board.legal_moves)
        total_legal_count = len(moves)
        if total_legal_count <= 1:
            return moves, None, total_legal_count

        if not self.enable_lazy_move_selection:
            node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
            if self.diagnostic_ordering:
                t0 = time.perf_counter()
                moves.sort(
                    key=lambda move: self._move_order_score(
                        board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
                    ),
                    reverse=True,
                )
                self.total_ordering_time += (time.perf_counter() - t0)
            else:
                moves.sort(
                    key=lambda move: self._move_order_score(
                        board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
                    ),
                    reverse=True,
                )
            return moves, None, total_legal_count

        # Lazy Candidate (L1):
        if tt_move is not None and tt_move in moves:
            self.lazy_sorts_deferred += 1
            rem = [m for m in moves if m != tt_move]
            def rest_provider():
                self.lazy_sorts_executed += 1
                node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
                if self.diagnostic_ordering:
                    t0 = time.perf_counter()
                    rem.sort(
                        key=lambda move: self._move_order_score(
                            board, move, None, ply, node_see=node_see, prev_move=prev_move
                        ),
                        reverse=True,
                    )
                    self.total_ordering_time += (time.perf_counter() - t0)
                else:
                    rem.sort(
                        key=lambda move: self._move_order_score(
                            board, move, None, ply, node_see=node_see, prev_move=prev_move
                        ),
                        reverse=True,
                    )
                return rem
            return [tt_move], rest_provider, total_legal_count
        else:
            node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
            if self.diagnostic_ordering:
                t0 = time.perf_counter()
                moves.sort(
                    key=lambda move: self._move_order_score(
                        board, move, None, ply, node_see=node_see, prev_move=prev_move
                    ),
                    reverse=True,
                )
                self.total_ordering_time += (time.perf_counter() - t0)
            else:
                moves.sort(
                    key=lambda move: self._move_order_score(
                        board, move, None, ply, node_see=node_see, prev_move=prev_move
                    ),
                    reverse=True,
                )
            return moves, None, total_legal_count

    def _quiescence(
        self,
        board: chess.Board,
        alpha: int,
        beta: int,
        ply: int,
        check_stalemate: bool = True,
        qply: int = 0,
    ) -> int:
        self.nodes += 1
        self._check_stop()

        if (
            board.is_insufficient_material()
            or (ply > 0 and board.is_repetition(3))
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0

        in_check = board.is_check()

        # Hard ply ceiling to prevent unbounded check evasion recursion
        qsearch_hard_limit = self.qsearch_max_ply + 8
        if ply >= qsearch_hard_limit:
            return evaluate_side_to_move(board, config=self.eval_config)

        if ply >= self.qsearch_max_ply and not in_check:
            return evaluate_side_to_move(board, config=self.eval_config)

        node_see: Optional[dict[chess.Move, int]] = (
            {} if (self.enable_see_ordering or self.enable_see_pruning) else None
        )

        if not in_check:
            if check_stalemate and not any(board.generate_legal_moves()):
                return 0
            stand_pat = evaluate_side_to_move(board, config=self.eval_config)
            if stand_pat >= beta:
                return stand_pat
            alpha = max(alpha, stand_pat)
            moves = self._quiescence_moves(
                board,
                include_checks=(self.enable_qsearch_checks and qply < self.qsearch_checks_max_ply),
            )
            moves.sort(
                key=lambda move: self._move_order_score(board, move, None, ply, node_see=node_see),
                reverse=True,
            )
        else:
            moves = self._ordered_moves(board, None, ply)

        if in_check and not moves:
            return -MATE_SCORE + ply

        best_score = -INF if in_check else alpha

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
                if self.enable_qsearch_checks:
                    score = -self._quiescence(board, -beta, -alpha, ply + 1, check_stalemate=False, qply=qply + 1)
                else:
                    score = -self._quiescence(board, -beta, -alpha, ply + 1, check_stalemate=False)
            finally:
                board.pop()

            if score > best_score:
                best_score = score
            if score >= beta:
                return score
            if score > alpha:
                alpha = score

        return best_score if in_check else alpha

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
            or (ply > 0 and board.is_repetition(3))
            or board.is_fivefold_repetition()
            or board.is_seventyfive_moves()
        ):
            return 0, []

        if depth <= 0:
            if not any(board.generate_legal_moves()):
                return (-MATE_SCORE + ply if board.is_check() else 0), []
            return self._quiescence(board, alpha, beta, ply, check_stalemate=False), []

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

        # Reverse Futility Pruning (RFP / Static Null Move Pruning)
        if (
            (self.enable_rfp or self.diagnostic_rfp)
            and ply > 0
            and not in_check
            and depth <= self.rfp_max_depth
            and abs(beta) < MATE_THRESHOLD
            and abs(alpha) < MATE_THRESHOLD
            and board.halfmove_clock < 140
        ):
            if self.enable_rfp:
                self.rfp_considered += 1
            static_eval = evaluate_side_to_move(board, config=self.eval_config)
            rfp_margin = self.rfp_margin_per_depth * depth
            cutoff_eligible = (static_eval - rfp_margin >= beta)
            if self.diagnostic_rfp:
                self.rfp_events.append({
                    "fen": board.fen(),
                    "ply": ply,
                    "depth": depth,
                    "static_eval": static_eval,
                    "beta": beta,
                    "alpha": alpha,
                    "margin": rfp_margin,
                    "cutoff": cutoff_eligible,
                    "reason": "static_eval_ge_beta_plus_margin" if cutoff_eligible else "below_margin",
                    "best_move": tt_move.uci() if tt_move else None,
                    "rfp_enabled": self.enable_rfp,
                })
            if self.enable_rfp and cutoff_eligible:
                self.rfp_cutoffs += 1
                self._store_tt(key, depth, beta, "lower", tt_move, ply)
                return beta, []

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

        prev_move = board.peek() if board.move_stack and board.peek() != chess.Move.null() else None
        searched_quiets: list[chess.Move] = []
        if not self.enable_lazy_move_selection:
            candidate_iter = self._ordered_moves(board, tt_move, ply, prev_move=prev_move)
            total_legal_count = len(candidate_iter)
            if total_legal_count == 0:
                if in_check:
                    if extension > 0:
                        self.check_extensions_terminal_mates += 1
                    return -MATE_SCORE + ply, []
                return 0, []
        else:
            phase1_moves, rest_provider, total_legal_count = self._select_ordered_moves(board, tt_move, ply, prev_move=prev_move)
            if total_legal_count == 0:
                if in_check:
                    if extension > 0:
                        self.check_extensions_terminal_mates += 1
                    return -MATE_SCORE + ply, []
                return 0, []
            def _lazy_iter():
                yield from phase1_moves
                if rest_provider is not None:
                    yield from rest_provider()
            candidate_iter = _lazy_iter()

        moves_searched = 0

        for move in candidate_iter:
            is_capture = board.is_capture(move)
            is_promotion = move.promotion is not None

            eligible_for_lmr = (
                self.enable_lmr
                and moves_searched >= 3
                and depth >= 3
                and ply > 0
                and not in_check
                and not is_capture
                and not is_promotion
                and (
                    ply >= len(self.killers)
                    or (move != self.killers[ply][0] and move != self.killers[ply][1])
                )
                and not board.gives_check(move)
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
                if self.diagnostic_ordering:
                    self.ordering_total_cutoffs += 1
                    cutoff_idx = moves_searched - 1
                    if cutoff_idx == 0:
                        self.first_move_cutoffs += 1
                    else:
                        self.late_move_cutoffs += 1
                    if tt_move is not None and move == tt_move:
                        self.tt_cutoffs_count += 1
                    if is_capture:
                        self.capture_cutoffs += 1
                    else:
                        self.quiet_cutoffs += 1
                        if ply < len(self.killers) and (move == self.killers[ply][0] or move == self.killers[ply][1]):
                            self.killer_cutoffs += 1
                    self.ordering_events.append({
                        "depth": depth,
                        "ply": ply,
                        "legal_moves": total_legal_count,
                        "searched_moves": moves_searched,
                        "cutoff_index": cutoff_idx,
                        "is_first_move": (cutoff_idx == 0),
                        "move": move.uci(),
                        "is_capture": is_capture,
                        "is_tt_move": (tt_move is not None and move == tt_move),
                    })

                if eligible_for_lmr:
                    self.lmr_cutoffs += 1
                if not is_capture and not is_promotion:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                    self._update_history(move, depth)
                    if self.enable_countermoves and prev_move is not None:
                        if move == self.countermoves[prev_move.from_square][prev_move.to_square]:
                            self.countermove_cutoffs += 1
                        self.countermoves[prev_move.from_square][prev_move.to_square] = move
                    if self.enable_history_malus:
                        bonus = depth * depth
                        for bad_move in searched_quiets:
                            bf = bad_move.from_square
                            bt = bad_move.to_square
                            self.history[bf][bt] = max(-MAX_HISTORY_SCORE, self.history[bf][bt] - bonus)
                break

            if not is_capture and not is_promotion:
                searched_quiets.append(move)

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
        wtime: Optional[int | float] = None,
        btime: Optional[int | float] = None,
        winc: Optional[int | float] = None,
        binc: Optional[int | float] = None,
        movestogo: Optional[int | float] = None,
    ) -> SearchResult:
        if time_limit is None and (wtime is not None or btime is not None):
            time_limit = self.time_manager.allocate_time(
                board.turn,
                wtime=wtime,
                btime=btime,
                winc=winc,
                binc=binc,
                movestogo=movestogo,
            )
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
        self.countermoves = [[None] * 64 for _ in range(64)]
        self.countermove_cutoffs = 0
        self.rfp_considered = 0
        self.rfp_cutoffs = 0
        self.rfp_events = []
        self.iteration_records = []
        self.ordering_events = []
        self.ordering_total_cutoffs = 0
        self.first_move_cutoffs = 0
        self.late_move_cutoffs = 0
        self.tt_cutoffs_count = 0
        self.killer_cutoffs = 0
        self.countermove_cutoffs_count = 0
        self.capture_cutoffs = 0
        self.quiet_cutoffs = 0
        self.total_movegen_time = 0.0
        self.total_ordering_time = 0.0
        self.lazy_sorts_deferred = 0
        self.lazy_sorts_executed = 0
        self.lazy_sorts_saved = 0

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

        ordered_root = self._ordered_moves(board, None, 0)
        best_move = ordered_root[0] if ordered_root else legal_moves[0]
        best_score = 0
        best_pv: list[chess.Move] = [best_move]
        completed_depth = 0

        for depth in range(1, max_depth + 1):
            iter_start = time.monotonic()
            iter_nodes_start = self.nodes
            retries = 0

            if self.stop_event is not None and self.stop_event.is_set():
                if self.diagnostic_iterations:
                    self._record_iteration(
                        depth=depth, start_t=iter_start, end_t=time.monotonic(),
                        nodes_start=iter_nodes_start, score=best_score, pv=best_pv,
                        completed=False, aborted=True, abort_reason="stop_event",
                        published=False, prev_depth=completed_depth, retries=0
                    )
                break
            if self.deadline is not None and time.monotonic() >= self.deadline:
                if self.diagnostic_iterations:
                    self._record_iteration(
                        depth=depth, start_t=iter_start, end_t=time.monotonic(),
                        nodes_start=iter_nodes_start, score=best_score, pv=best_pv,
                        completed=False, aborted=True, abort_reason="timeout",
                        published=False, prev_depth=completed_depth, retries=0
                    )
                break
            use_aspiration = (
                self.enable_aspiration
                and depth >= 2
                and abs(best_score) < MATE_THRESHOLD
            )

            if not use_aspiration:
                try:
                    score, pv = self._negamax(board, depth, -INF, INF, 0)
                except SearchTimeout:
                    if self.diagnostic_iterations:
                        self._record_iteration(
                            depth=depth, start_t=iter_start, end_t=time.monotonic(),
                            nodes_start=iter_nodes_start, score=best_score, pv=best_pv,
                            completed=False, aborted=True, abort_reason="timeout",
                            published=False, prev_depth=completed_depth, retries=0
                        )
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
                    if self.diagnostic_iterations:
                        self._record_iteration(
                            depth=depth, start_t=iter_start, end_t=time.monotonic(),
                            nodes_start=iter_nodes_start, score=best_score, pv=best_pv,
                            completed=False, aborted=True, abort_reason="timeout",
                            published=False, prev_depth=completed_depth, retries=retries
                        )
                    break

            # Only publish results from fully completed iterations.
            iter_end = time.monotonic()
            if pv:
                best_pv = pv
                best_move = pv[0]
            best_score = score
            prev_comp = completed_depth
            completed_depth = depth

            if self.diagnostic_iterations:
                self._record_iteration(
                    depth=depth, start_t=iter_start, end_t=iter_end,
                    nodes_start=iter_nodes_start, score=best_score, pv=best_pv,
                    completed=True, aborted=False, abort_reason=None,
                    published=True, prev_depth=prev_comp, retries=retries
                )

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
            countermove_cutoffs=self.countermove_cutoffs,
            rfp_considered=self.rfp_considered,
            rfp_cutoffs=self.rfp_cutoffs,
            rfp_events=list(self.rfp_events) if self.diagnostic_rfp else [],
            iteration_records=list(self.iteration_records) if self.diagnostic_iterations else [],
            ordering_stats={
                "total_cutoffs": self.ordering_total_cutoffs,
                "first_move_cutoffs": self.first_move_cutoffs,
                "late_move_cutoffs": self.late_move_cutoffs,
                "first_move_cutoff_rate": (self.first_move_cutoffs / self.ordering_total_cutoffs) if self.ordering_total_cutoffs > 0 else 0.0,
                "tt_cutoffs": self.tt_cutoffs_count,
                "killer_cutoffs": self.killer_cutoffs,
                "countermove_cutoffs": self.countermove_cutoffs,
                "capture_cutoffs": self.capture_cutoffs,
                "quiet_cutoffs": self.quiet_cutoffs,
                "total_ordering_time_s": self.total_ordering_time,
                "lazy_selection_enabled": self.enable_lazy_move_selection,
                "lazy_sorts_deferred": self.lazy_sorts_deferred,
                "lazy_sorts_executed": self.lazy_sorts_executed,
                "lazy_sorts_saved": self.lazy_sorts_deferred - self.lazy_sorts_executed,
            } if self.diagnostic_ordering else {},
            ordering_events=list(self.ordering_events) if self.diagnostic_ordering else [],
        )
