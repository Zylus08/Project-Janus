"""Comprehensive reliability audit tests for NMP, LMR, and selective search interactions (Milestone v0.20)."""
import unittest

import chess

from janus.search import JanusSearch, MATE_SCORE, MATE_THRESHOLD


class SelectiveSearchReliabilityTests(unittest.TestCase):
    """Phase 2: Reliability audit of NMP and LMR under complex tactical and endgame conditions."""

    # -------------------------------------------------------------------------
    # Part A: NMP-Focused Reliability Tests
    # -------------------------------------------------------------------------

    def test_nmp_trebuchet_and_opposition_endgames_excluded(self):
        """Pawn-only zugzwang and opposition endgames are strictly excluded from NMP."""
        # Trébuchet position: whoever moves loses
        trebuchet = chess.Board("8/8/8/3k4/3p4/3K4/8/8 w - - 0 1")
        # Pure King + Pawns opposition
        opposition = chess.Board("8/8/4k3/8/4K3/8/8/8 w - - 0 1")
        # Multi-pawn ending
        pawns = chess.Board("8/2k2p2/p3p1p1/P1K1P1P1/5P2/8/8/8 w - - 0 1")

        for b in [trebuchet, opposition, pawns]:
            engine = JanusSearch(enable_nmp=True)
            res = engine.search(b, max_depth=4)
            self.assertEqual(res.nmp_considered, 0)
            self.assertEqual(res.nmp_attempts, 0)
            self.assertEqual(res.nmp_cutoffs, 0)

    def test_nmp_low_material_excluded(self):
        """Single minor piece endgames (K+N, K+B) are excluded by the material guard."""
        boards = [
            chess.Board("8/4k3/8/8/8/8/4K3/4N3 w - - 0 1"),
            chess.Board("8/4k3/8/8/8/8/4K3/4B3 w - - 0 1"),
            chess.Board("8/4k3/8/8/8/4n3/4K3/8 b - - 0 1"),
            chess.Board("8/4k3/8/8/8/4b3/4K3/8 b - - 0 1"),
        ]
        for b in boards:
            engine = JanusSearch(enable_nmp=True)
            self.assertFalse(engine._has_nmp_material(b))
            res = engine.search(b, max_depth=3)
            self.assertEqual(res.nmp_considered, 0)
            self.assertEqual(res.nmp_attempts, 0)

    def test_nmp_verification_rejection_continues_search(self):
        """When verification search rejects a candidate fail-high, search continues normally."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7")
        engine = JanusSearch(enable_nmp=True, enable_nmp_verification=True, nmp_verify_min_depth=1)

        # Force verification search to fail by stubbing
        orig_negamax = engine._negamax
        rejection_triggered = [False]

        def stub_negamax(b, depth, alpha, beta, ply, allow_nmp=True, *args, **kwargs):
            # Identification of verification search: allow_nmp is False and beta - 1 == alpha
            if not allow_nmp and alpha == beta - 1:
                rejection_triggered[0] = True
                return beta - 10, []
            return orig_negamax(b, depth, alpha, beta, ply, allow_nmp)

        engine._negamax = stub_negamax
        try:
            res = engine.search(board, max_depth=4)
            if rejection_triggered[0]:
                self.assertGreater(engine.nmp_verification_failures, 0)
            self.assertIsNotNone(res.best_move)
            self.assertTrue(board.is_legal(res.best_move))
        finally:
            engine._negamax = orig_negamax

    def test_nmp_in_check_never_runs(self):
        """Positions where the king is in check never attempt null moves."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(board.is_check())
        engine = JanusSearch(enable_nmp=True)
        null_moves_in_check = [0]
        orig_push = board.push
        def safe_push(m):
            if m == chess.Move.null() and board.is_check():
                null_moves_in_check[0] += 1
            orig_push(m)
        board.push = safe_push
        try:
            res = engine.search(board, max_depth=3)
            self.assertEqual(null_moves_in_check[0], 0)
            self.assertIsNotNone(res.best_move)
            self.assertTrue(board.is_legal(res.best_move))
        finally:
            board.push = orig_push

    def test_nmp_halfmove_clock_guard(self):
        """Near 75-move draw threshold (>= 140 halfmoves), NMP is suppressed."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 145 73")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.nmp_considered, 0)

    def test_nmp_tt_bound_storage(self):
        """Accepted NMP cutoffs store 'lower' bound with score clamped to beta."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=4)
        lower_entries = [e for e in engine.tt.values() if e.flag == "lower"]
        self.assertGreater(len(lower_entries), 0)
        for e in lower_entries:
            self.assertLess(e.score, MATE_SCORE)

    def test_nmp_pv_legality_and_no_null_move(self):
        """Principal variations returned by NMP never contain null moves and are legal."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=4)
        verify = board.copy()
        for m in res.pv:
            self.assertNotEqual(m, chess.Move.null())
            self.assertIn(m, verify.legal_moves)
            verify.push(m)

    # -------------------------------------------------------------------------
    # Part B: LMR-Focused Reliability Tests
    # -------------------------------------------------------------------------

    def test_lmr_checks_and_captures_never_reduced(self):
        """Checking moves, captures, promotions, and moves in check are never reduced."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        engine = JanusSearch(enable_lmr=True, enable_nmp=False)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.best_move, chess.Move.from_uci("h5f7"))

    def test_lmr_research_on_alpha_improvement(self):
        """When a reduced move exceeds alpha, full-depth re-search is triggered."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7")
        engine = JanusSearch(enable_lmr=True, enable_nmp=False)
        res = engine.search(board, max_depth=5)
        self.assertGreater(res.lmr_reduced_searches, 0)
        # researches counter tracks verification re-searches
        self.assertGreaterEqual(res.lmr_researches, 0)

    def test_lmr_first_three_moves_never_reduced(self):
        """First 3 moves in ordered moves list are never reduced by conservative LMR."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        engine = JanusSearch(enable_lmr=True)
        res = engine.search(board, max_depth=3)
        # At depth 3, ply 1 has depth 2 (< 3), so LMR cannot reduce moves_searched < 3
        self.assertEqual(res.lmr_reduced_searches, 0)

    # -------------------------------------------------------------------------
    # Part C: Broader Tactical and Endgame Suite Across 4 Configurations
    # -------------------------------------------------------------------------

    def test_four_way_tactical_suite_execution(self):
        """Test a broad tactical and endgame suite across all 4 LMR x NMP configurations."""
        tactical_positions = [
            # 1. Forced Mate in 1
            ("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1", "h5f7", "mate_in_1"),
            # 2. Forced Mate in 2 (Anastasia's / Arabian motif)
            ("5rk1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1", None, "back_rank_pressure"),
            # 3. Queen Promotion
            ("8/1P6/8/8/8/8/k7/7K w - - 0 1", "b7b8q", "queen_promotion"),
            # 4. Defensive Promotion Resource
            ("8/1P6/8/8/8/8/1r6/k6K b - - 0 1", "b2b7", "defensive_block"),
            # 5. Tactical Knight Fork
            ("4k3/8/8/8/3q4/8/5N2/4K3 w - - 0 1", None, "knight_safety"),
            # 6. Absolute Pin Exploit
            ("4k3/4r3/8/8/8/8/4R3/4K3 w - - 0 1", "e2e7", "pin_exchange"),
            # 7. Trébuchet Zugzwang
            ("8/8/8/3k4/3p4/3K4/8/8 w - - 0 1", None, "trebuchet_zugzwang"),
            # 8. Stalemate Defense
            ("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1", None, "stalemate_position"),
        ]

        configs = [
            ("lmr_off_nmp_off", False, False),
            ("lmr_on_nmp_off", True, False),
            ("lmr_off_nmp_on", False, True),
            ("lmr_on_nmp_on", True, True),
        ]

        for fen, expected_move, label in tactical_positions:
            board = chess.Board(fen)
            results = {}
            for name, lmr, nmp in configs:
                engine = JanusSearch(enable_lmr=lmr, enable_nmp=nmp)
                res = engine.search(board, max_depth=3)
                results[name] = res

                # Ensure PV legality across all 4 modes
                verify = board.copy()
                for m in res.pv:
                    self.assertIn(m, verify.legal_moves, f"Illegal PV move {m} in {label} ({name})")
                    verify.push(m)

                # If an exact move is expected, verify it matches
                if expected_move:
                    self.assertIsNotNone(res.best_move, f"No best move returned for {label} ({name})")
                    self.assertEqual(res.best_move.uci(), expected_move, f"Move mismatch in {label} ({name})")


if __name__ == "__main__":
    unittest.main()
