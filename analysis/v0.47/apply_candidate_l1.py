"""Script to apply Candidate L1 (Lazy Move Selection) to src/janus/search.py and src/janus/uci.py."""

from pathlib import Path

search_file = Path("src/janus/search.py")
content = search_file.read_text(encoding="utf-8")

# 1. Add enable_lazy_move_selection to __init__ arguments
target1 = "        diagnostic_ordering: bool = False,\n    ) -> None:"
repl1 = "        diagnostic_ordering: bool = False,\n        enable_lazy_move_selection: bool = False,\n    ) -> None:"
assert target1 in content, "target1 not found"
content = content.replace(target1, repl1, 1)

# 2. Add self.enable_lazy_move_selection attribute and lazy_sorts_saved
target2 = "        self.diagnostic_ordering = diagnostic_ordering\n        self.ordering_events: list[dict] = []"
repl2 = "        self.diagnostic_ordering = diagnostic_ordering\n        self.enable_lazy_move_selection = enable_lazy_move_selection\n        self.lazy_sorts_saved = 0\n        self.ordering_events: list[dict] = []"
assert target2 in content, "target2 not found"
content = content.replace(target2, repl2, 1)

# 3. Add self.lazy_sorts_saved reset in search()
target3 = "        self.total_movegen_time = 0.0\n        self.total_ordering_time = 0.0\n\n        legal_moves = list(board.legal_moves)"
repl3 = "        self.total_movegen_time = 0.0\n        self.total_ordering_time = 0.0\n        self.lazy_sorts_saved = 0\n\n        legal_moves = list(board.legal_moves)"
assert target3 in content, "target3 not found"
content = content.replace(target3, repl3, 1)

# 4. Add _select_ordered_moves method right below _ordered_moves
target4 = """    def _ordered_moves(
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
        return moves"""

repl4 = """    def _ordered_moves(
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
            rem = [m for m in moves if m != tt_move]
            def rest_provider():
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
            return moves, None, total_legal_count"""
assert target4 in content, "target4 not found"
content = content.replace(target4, repl4, 1)

# 5. Update _negamax move loop to use _select_ordered_moves
target5 = """        prev_move = board.peek() if board.move_stack and board.peek() != chess.Move.null() else None
        moves = self._ordered_moves(board, tt_move, ply, prev_move=prev_move)
        total_legal_count = len(moves)
        searched_quiets: list[chess.Move] = []
        if not moves:
            if in_check:
                if extension > 0:
                    self.check_extensions_terminal_mates += 1
                return -MATE_SCORE + ply, []
            return 0, []

        moves_searched = 0

        for move in moves:"""

repl5 = """        prev_move = board.peek() if board.move_stack and board.peek() != chess.Move.null() else None
        phase1_moves, rest_provider, total_legal_count = self._select_ordered_moves(board, tt_move, ply, prev_move=prev_move)
        searched_quiets: list[chess.Move] = []
        if total_legal_count == 0:
            if in_check:
                if extension > 0:
                    self.check_extensions_terminal_mates += 1
                return -MATE_SCORE + ply, []
            return 0, []

        moves_searched = 0

        def _candidate_moves_stream():
            yield from phase1_moves
            if rest_provider is not None:
                yield from rest_provider()

        for move in _candidate_moves_stream():"""
assert target5 in content, "target5 not found"
content = content.replace(target5, repl5, 1)

# 6. Add lazy_sorts_saved to ordering_stats
target6 = """                "total_ordering_time_s": self.total_ordering_time,
            } if self.diagnostic_ordering else {},"""
repl6 = """                "total_ordering_time_s": self.total_ordering_time,
                "lazy_selection_enabled": self.enable_lazy_move_selection,
            } if self.diagnostic_ordering else {},"""
assert target6 in content, "target6 not found"
content = content.replace(target6, repl6, 1)

search_file.write_text(content, encoding="utf-8")
print("Updated src/janus/search.py successfully.")

# Now update src/janus/uci.py
uci_file = Path("src/janus/uci.py")
uci_content = uci_file.read_text(encoding="utf-8")

target_uci_arg = '    parser.add_argument("--diag-ordering", action="store_true", help="Enable move-ordering diagnostic telemetry")'
repl_uci_arg = '    parser.add_argument("--diag-ordering", action="store_true", help="Enable move-ordering diagnostic telemetry")\n    parser.add_argument("--enable-lazy-move-selection", action="store_true", help="Enable candidate L1 lazy move selection")'
assert target_uci_arg in uci_content, "target_uci_arg not found"
uci_content = uci_content.replace(target_uci_arg, repl_uci_arg, 1)

target_uci_engine = "        diagnostic_ordering=args.diag_ordering,\n        time_manager=tm,"
repl_uci_engine = "        diagnostic_ordering=args.diag_ordering,\n        enable_lazy_move_selection=args.enable_lazy_move_selection,\n        time_manager=tm,"
assert target_uci_engine in uci_content, "target_uci_engine not found"
uci_content = uci_content.replace(target_uci_engine, repl_uci_engine, 1)

uci_file.write_text(uci_content, encoding="utf-8")
print("Updated src/janus/uci.py successfully.")

