"""Script to instrument src/janus/search.py and src/janus/uci.py with RFP diagnostics."""
from pathlib import Path

def update_search():
    search_path = Path("src/janus/search.py")
    content = search_path.read_text(encoding="utf-8")
    # Normalize CRLF to LF for reliable string matching
    crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")

    # 1. dataclasses import
    s1 = "from dataclasses import dataclass\n"
    r1 = "from dataclasses import dataclass, field\n"
    assert s1 in content, "s1 not found"
    content = content.replace(s1, r1, 1)

    # 2. SearchResult dataclass
    s2 = "    rfp_cutoffs: int = 0\n"
    r2 = "    rfp_cutoffs: int = 0\n    rfp_events: list[dict] = field(default_factory=list)\n"
    assert s2 in content, "s2 not found"
    content = content.replace(s2, r2, 1)

    # 3. JanusSearch.__init__ signature
    s3 = "        enable_rfp: bool = False,\n        rfp_max_depth: int = 2,\n        rfp_margin_per_depth: int = 120,\n    ) -> None:"
    r3 = "        enable_rfp: bool = False,\n        rfp_max_depth: int = 2,\n        rfp_margin_per_depth: int = 120,\n        diagnostic_rfp: bool = False,\n    ) -> None:"
    assert s3 in content, "s3 not found"
    content = content.replace(s3, r3, 1)

    # 4. JanusSearch.__init__ assignments
    s4 = "        self.enable_rfp = enable_rfp\n        self.rfp_max_depth = rfp_max_depth\n        self.rfp_margin_per_depth = rfp_margin_per_depth"
    r4 = "        self.enable_rfp = enable_rfp\n        self.rfp_max_depth = rfp_max_depth\n        self.rfp_margin_per_depth = rfp_margin_per_depth\n        self.diagnostic_rfp = diagnostic_rfp\n        self.rfp_events: list[dict] = []"
    assert s4 in content, "s4 not found"
    content = content.replace(s4, r4, 1)

    # 5. Search reset in search()
    s5 = "        self.rfp_considered = 0\n        self.rfp_cutoffs = 0\n\n        legal_moves = list(board.legal_moves)"
    r5 = "        self.rfp_considered = 0\n        self.rfp_cutoffs = 0\n        self.rfp_events = []\n\n        legal_moves = list(board.legal_moves)"
    assert s5 in content, "s5 not found"
    content = content.replace(s5, r5, 1)

    # 6. SearchResult construction at line 1259
    s7 = "            rfp_considered=self.rfp_considered,\n            rfp_cutoffs=self.rfp_cutoffs,\n        )"
    r7 = "            rfp_considered=self.rfp_considered,\n            rfp_cutoffs=self.rfp_cutoffs,\n            rfp_events=list(self.rfp_events) if self.diagnostic_rfp else [],\n        )"
    assert s7 in content, "s7 not found"
    content = content.replace(s7, r7, 1)

    # 7. RFP logic in _negamax
    s8 = """        # Reverse Futility Pruning (RFP / Static Null Move Pruning)
        if (
            self.enable_rfp
            and ply > 0
            and not in_check
            and depth <= self.rfp_max_depth
            and abs(beta) < MATE_THRESHOLD
            and abs(alpha) < MATE_THRESHOLD
            and board.halfmove_clock < 140
        ):
            self.rfp_considered += 1
            static_eval = evaluate_side_to_move(board, config=self.eval_config)
            rfp_margin = self.rfp_margin_per_depth * depth
            if static_eval - rfp_margin >= beta:
                self.rfp_cutoffs += 1
                self._store_tt(key, depth, beta, "lower", tt_move, ply)
                return beta, []"""

    r8 = """        # Reverse Futility Pruning (RFP / Static Null Move Pruning)
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
                return beta, []"""

    assert s8 in content, "s8 not found"
    content = content.replace(s8, r8, 1)

    # 8. flush_rfp_telemetry method
    s9 = "    def _probe_tt("
    r9 = """    def flush_rfp_telemetry(self, filepath: str) -> int:
        \"\"\"Flush recorded RFP diagnostic events to a JSONL file and clear buffer.\"\"\"
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = len(self.rfp_events)
        with open(p, "a", encoding="utf-8") as f:
            for ev in self.rfp_events:
                f.write(json.dumps(ev) + "\\n")
        self.rfp_events.clear()
        return count

    def _probe_tt("""

    assert s9 in content, "s9 not found"
    content = content.replace(s9, r9, 1)

    if crlf:
        content = content.replace("\n", "\r\n")
    search_path.write_text(content, encoding="utf-8")
    print("Updated src/janus/search.py successfully.")

def update_uci():
    uci_path = Path("src/janus/uci.py")
    content = uci_path.read_text(encoding="utf-8")
    crlf = "\r\n" in content
    content = content.replace("\r\n", "\n")

    # Add CLI flag
    s1 = '    parser.add_argument("--enable-rfp", action="store_true", help="Enable reverse futility pruning")\n'
    r1 = s1 + '    parser.add_argument("--diag-rfp", action="store_true", help="Enable reverse futility pruning diagnostics")\n'
    assert s1 in content, "uci s1 not found"
    content = content.replace(s1, r1, 1)

    # Pass to JanusSearch
    s2 = "        enable_rfp=enable_rfp,\n        rfp_max_depth=args.rfp_max_depth,\n        rfp_margin_per_depth=args.rfp_margin,"
    r2 = "        enable_rfp=enable_rfp,\n        rfp_max_depth=args.rfp_max_depth,\n        rfp_margin_per_depth=args.rfp_margin,\n        diagnostic_rfp=args.diag_rfp,"
    assert s2 in content, "uci s2 not found"
    content = content.replace(s2, r2, 1)

    if crlf:
        content = content.replace("\n", "\r\n")
    uci_path.write_text(content, encoding="utf-8")
    print("Updated src/janus/uci.py successfully.")

if __name__ == "__main__":
    update_search()
    update_uci()
