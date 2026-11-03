"""Instrument src/janus/search.py and src/janus/uci.py with move-ordering telemetry."""
from pathlib import Path

def update_search():
    search_path = Path("src/janus/search.py")
    content = search_path.read_text(encoding="utf-8")
    crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")

    # 1. SearchResult dataclass: add ordering_stats and ordering_events
    s1 = "    iteration_records: list[dict] = field(default_factory=list)\n"
    r1 = s1 + "    ordering_stats: dict = field(default_factory=dict)\n    ordering_events: list[dict] = field(default_factory=list)\n"
    assert s1 in content, "s1 not found"
    content = content.replace(s1, r1, 1)

    # 2. JanusSearch.__init__ signature: add diagnostic_ordering
    s2 = "        diagnostic_iterations: bool = False,\n    ) -> None:"
    r2 = "        diagnostic_iterations: bool = False,\n        diagnostic_ordering: bool = False,\n    ) -> None:"
    assert s2 in content, "s2 not found"
    content = content.replace(s2, r2, 1)

    # 3. JanusSearch.__init__ assignments
    s3 = "        self.diagnostic_iterations = diagnostic_iterations\n        self.iteration_records: list[dict] = []"
    r3 = """        self.diagnostic_iterations = diagnostic_iterations
        self.iteration_records: list[dict] = []
        self.diagnostic_ordering = diagnostic_ordering
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
        self.total_ordering_time = 0.0"""
    assert s3 in content, "s3 not found"
    content = content.replace(s3, r3, 1)

    # 4. Helper flush_ordering_telemetry method
    s4 = "    def flush_iteration_telemetry(self, filepath: str) -> int:"
    r4 = """    def flush_ordering_telemetry(self, filepath: str) -> int:
        \"\"\"Flush recorded move ordering telemetry records to a JSONL file and clear buffer.\"\"\"
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = len(self.ordering_events)
        with open(p, "a", encoding="utf-8") as f:
            for rec in self.ordering_events:
                f.write(json.dumps(rec) + "\\n")
        self.ordering_events.clear()
        return count

    def flush_iteration_telemetry(self, filepath: str) -> int:"""
    assert s4 in content, "s4 not found"
    content = content.replace(s4, r4, 1)

    # 5. Search reset in search()
    s5 = "        self.iteration_records = []\n\n        legal_moves = list(board.legal_moves)"
    r5 = """        self.iteration_records = []
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

        legal_moves = list(board.legal_moves)"""
    assert s5 in content, "s5 not found"
    content = content.replace(s5, r5, 1)

    # 6. Instrument _ordered_moves with timing when diagnostic_ordering is True
    s6 = """        node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
        moves.sort(
            key=lambda move: self._move_order_score(
                board, move, tt_move, ply, node_see=node_see, prev_move=prev_move
            ),
            reverse=True,
        )
        return moves"""

    r6 = """        node_see: Optional[dict[chess.Move, int]] = {} if self.enable_see_ordering else None
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
    assert s6 in content, "s6 not found"
    content = content.replace(s6, r6, 1)

    # 7. Record total_legal_count in _negamax move loop
    s7 = "        moves = self._ordered_moves(board, tt_move, ply, prev_move=prev_move)\n        searched_quiets: list[chess.Move] = []"
    r7 = "        moves = self._ordered_moves(board, tt_move, ply, prev_move=prev_move)\n        total_legal_count = len(moves)\n        searched_quiets: list[chess.Move] = []"
    assert s7 in content, "s7 not found"
    content = content.replace(s7, r7, 1)

    # 8. Instrument beta cutoffs in _negamax
    s8 = """            alpha = max(alpha, score)
            if alpha >= beta:
                self.beta_cutoffs += 1
                if eligible_for_lmr:
                    self.lmr_cutoffs += 1
                if not is_capture and not is_promotion:
                    if ply < len(self.killers) and self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                    self._update_history(move, depth)"""

    r8 = """            alpha = max(alpha, score)
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
                    self._update_history(move, depth)"""
    assert s8 in content, "s8 not found"
    content = content.replace(s8, r8, 1)

    # 9. SearchResult construction
    s9 = "            iteration_records=list(self.iteration_records) if self.diagnostic_iterations else [],\n        )"
    r9 = """            iteration_records=list(self.iteration_records) if self.diagnostic_iterations else [],
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
            } if self.diagnostic_ordering else {},
            ordering_events=list(self.ordering_events) if self.diagnostic_ordering else [],
        )"""
    assert s9 in content, "s9 not found"
    content = content.replace(s9, r9, 1)

    if crlf:
        content = content.replace("\n", "\r\n")
    search_path.write_text(content, encoding="utf-8")
    print("Updated src/janus/search.py with move-ordering telemetry successfully.")

def update_uci():
    uci_path = Path("src/janus/uci.py")
    content = uci_path.read_text(encoding="utf-8")
    crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")

    # Add CLI flag
    s1 = '    parser.add_argument("--diag-iterations", action="store_true", help="Enable iteration-level search telemetry")\n'
    r1 = s1 + '    parser.add_argument("--diag-ordering", action="store_true", help="Enable move-ordering diagnostic telemetry")\n'
    assert s1 in content, "uci s1 not found"
    content = content.replace(s1, r1, 1)

    # Pass to JanusSearch
    s2 = "        diagnostic_iterations=args.diag_iterations,\n        time_manager=tm,"
    r2 = "        diagnostic_iterations=args.diag_iterations,\n        diagnostic_ordering=args.diag_ordering,\n        time_manager=tm,"
    assert s2 in content, "uci s2 not found"
    content = content.replace(s2, r2, 1)

    if crlf:
        content = content.replace("\n", "\r\n")
    uci_path.write_text(content, encoding="utf-8")
    print("Updated src/janus/uci.py with move-ordering telemetry successfully.")

if __name__ == "__main__":
    update_search()
    update_uci()
