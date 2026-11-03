"""Instrument src/janus/search.py and src/janus/uci.py with iteration-level telemetry."""
from pathlib import Path

def update_search():
    search_path = Path("src/janus/search.py")
    content = search_path.read_text(encoding="utf-8")
    crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")

    # 1. SearchResult dataclass: add iteration_records
    s1 = "    rfp_events: list[dict] = field(default_factory=list)\n"
    r1 = "    rfp_events: list[dict] = field(default_factory=list)\n    iteration_records: list[dict] = field(default_factory=list)\n"
    assert s1 in content, "s1 not found"
    content = content.replace(s1, r1, 1)

    # 2. JanusSearch.__init__ signature: add diagnostic_iterations
    s2 = "        diagnostic_rfp: bool = False,\n    ) -> None:"
    r2 = "        diagnostic_rfp: bool = False,\n        diagnostic_iterations: bool = False,\n    ) -> None:"
    assert s2 in content, "s2 not found"
    content = content.replace(s2, r2, 1)

    # 3. JanusSearch.__init__ assignments
    s3 = "        self.diagnostic_rfp = diagnostic_rfp\n        self.rfp_events: list[dict] = []"
    r3 = "        self.diagnostic_rfp = diagnostic_rfp\n        self.rfp_events: list[dict] = []\n        self.diagnostic_iterations = diagnostic_iterations\n        self.iteration_records: list[dict] = []"
    assert s3 in content, "s3 not found"
    content = content.replace(s3, r3, 1)

    # 4. Helper methods: flush_iteration_telemetry and _record_iteration
    s4 = "    def flush_rfp_telemetry(self, filepath: str) -> int:"
    r4 = """    def flush_iteration_telemetry(self, filepath: str) -> int:
        \"\"\"Flush recorded iteration telemetry records to a JSONL file and clear buffer.\"\"\"
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = len(self.iteration_records)
        with open(p, "a", encoding="utf-8") as f:
            for rec in self.iteration_records:
                f.write(json.dumps(rec) + "\\n")
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

    def flush_rfp_telemetry(self, filepath: str) -> int:"""
    assert s4 in content, "s4 not found"
    content = content.replace(s4, r4, 1)

    # 5. Reset in search()
    s5 = "        self.rfp_cutoffs = 0\n        self.rfp_events = []"
    r5 = "        self.rfp_cutoffs = 0\n        self.rfp_events = []\n        self.iteration_records = []"
    assert s5 in content, "s5 not found"
    content = content.replace(s5, r5, 1)

    # 6. SearchResult construction at line 1259
    s6 = "            rfp_events=list(self.rfp_events) if self.diagnostic_rfp else [],\n        )"
    r6 = "            rfp_events=list(self.rfp_events) if self.diagnostic_rfp else [],\n            iteration_records=list(self.iteration_records) if self.diagnostic_iterations else [],\n        )"
    assert s6 in content, "s6 not found"
    content = content.replace(s6, r6, 1)

    # 7. Iteration loop instrumentation
    s7 = """        for depth in range(1, max_depth + 1):
            if self.stop_event is not None and self.stop_event.is_set():
                break
            if self.deadline is not None and time.monotonic() >= self.deadline:
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
            completed_depth = depth"""

    r7 = """        for depth in range(1, max_depth + 1):
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
                )"""
    assert s7 in content, "s7 not found"
    content = content.replace(s7, r7, 1)

    if crlf:
        content = content.replace("\n", "\r\n")
    search_path.write_text(content, encoding="utf-8")
    print("Updated src/janus/search.py with iteration telemetry successfully.")

def update_uci():
    uci_path = Path("src/janus/uci.py")
    content = uci_path.read_text(encoding="utf-8")
    crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")

    # Add CLI flag
    s1 = '    parser.add_argument("--diag-rfp", action="store_true", help="Enable reverse futility pruning diagnostics")\n'
    r1 = s1 + '    parser.add_argument("--diag-iterations", action="store_true", help="Enable iteration-level search telemetry")\n'
    assert s1 in content, "uci s1 not found"
    content = content.replace(s1, r1, 1)

    # Pass to JanusSearch
    s2 = "        diagnostic_rfp=args.diag_rfp,\n        time_manager=tm,"
    r2 = "        diagnostic_rfp=args.diag_rfp,\n        diagnostic_iterations=args.diag_iterations,\n        time_manager=tm,"
    assert s2 in content, "uci s2 not found"
    content = content.replace(s2, r2, 1)

    if crlf:
        content = content.replace("\n", "\r\n")
    uci_path.write_text(content, encoding="utf-8")
    print("Updated src/janus/uci.py with iteration telemetry successfully.")

if __name__ == "__main__":
    update_search()
    update_uci()

