from pathlib import Path

p = Path("src/janus/search.py")
text = p.read_text(encoding="utf-8")

# Update __init__
text = text.replace(
    "self.enable_lazy_move_selection = enable_lazy_move_selection\n        self.lazy_sorts_saved = 0",
    "self.enable_lazy_move_selection = enable_lazy_move_selection\n        self.lazy_sorts_deferred = 0\n        self.lazy_sorts_executed = 0\n        self.lazy_sorts_saved = 0"
)

# Update reset in search()
text = text.replace(
    "self.total_ordering_time = 0.0\n        self.lazy_sorts_saved = 0",
    "self.total_ordering_time = 0.0\n        self.lazy_sorts_deferred = 0\n        self.lazy_sorts_executed = 0\n        self.lazy_sorts_saved = 0"
)

# Update _select_ordered_moves
old_sel = """        # Lazy Candidate (L1):
        if tt_move is not None and tt_move in moves:
            rem = [m for m in moves if m != tt_move]
            def rest_provider():"""

new_sel = """        # Lazy Candidate (L1):
        if tt_move is not None and tt_move in moves:
            self.lazy_sorts_deferred += 1
            rem = [m for m in moves if m != tt_move]
            def rest_provider():
                self.lazy_sorts_executed += 1"""
assert old_sel in text, "old_sel not found"
text = text.replace(old_sel, new_sel, 1)

# Update _negamax loop
old_nm = """        prev_move = board.peek() if board.move_stack and board.peek() != chess.Move.null() else None
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

new_nm = """        prev_move = board.peek() if board.move_stack and board.peek() != chess.Move.null() else None
        searched_quiets: list[chess.Move] = []
        if not self.enable_lazy_move_selection:
            candidate_iter = self._ordered_moves(board, tt_move, ply, prev_move=prev_move)
            if not candidate_iter:
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

        for move in candidate_iter:"""
assert old_nm in text, "old_nm not found"
text = text.replace(old_nm, new_nm, 1)

# Update ordering stats dictionary
old_stats = """                "total_ordering_time_s": self.total_ordering_time,
                "lazy_selection_enabled": self.enable_lazy_move_selection,"""

new_stats = """                "total_ordering_time_s": self.total_ordering_time,
                "lazy_selection_enabled": self.enable_lazy_move_selection,
                "lazy_sorts_deferred": self.lazy_sorts_deferred,
                "lazy_sorts_executed": self.lazy_sorts_executed,
                "lazy_sorts_saved": self.lazy_sorts_deferred - self.lazy_sorts_executed,"""
assert old_stats in text, "old_stats not found"
text = text.replace(old_stats, new_stats, 1)

p.write_text(text, encoding="utf-8")
print("Refinement applied successfully!")

