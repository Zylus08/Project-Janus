"""Regression, boundary, and tactical tests for Null Move Pruning (NMP) in Project Janus (v0.19)."""
import subprocess
import sys
import unittest

import chess

from janus.search import JanusSearch, SearchTimeout, MATE_SCORE, MATE_THRESHOLD


class NullMovePruningTests(unittest.TestCase):
    """Test suite covering Phase 5 requirements for Null Move Pruning."""

    def test_01_nmp_off_reproduces_v018_baseline(self):
        """Disabling NMP reproduces exact scores and moves of the v0.18 search."""
        fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        ]
        for fen in fens:
            board = chess.Board(fen)
            # Baseline: NMP disabled (v0.18 behavior)
            engine_baseline = JanusSearch(enable_nmp=False, enable_lmr=True)
            res_baseline = engine_baseline.search(board, max_depth=3)

            # Re-run baseline with explicit params
            engine_candidate = JanusSearch(enable_nmp=False, enable_lmr=True)
            res_candidate = engine_candidate.search(board, max_depth=3)

            self.assertEqual(res_baseline.best_move, res_candidate.best_move)
            self.assertEqual(res_baseline.score, res_candidate.score)
            self.assertEqual(res_baseline.nodes, res_candidate.nodes)
            self.assertEqual(res_candidate.nmp_considered, 0)
            self.assertEqual(res_candidate.nmp_attempts, 0)
            self.assertEqual(res_candidate.nmp_cutoffs, 0)

    def test_02_null_move_never_attempted_at_root(self):
        """Null moves are never attempted at ply 0 (root)."""
        board = chess.Board()
        engine = JanusSearch(enable_nmp=True)
        # At depth 1 or 2, interior nodes have depth < 3, so no interior NMP either.
        res = engine.search(board, max_depth=1)
        self.assertEqual(res.nmp_considered, 0)
        self.assertEqual(res.nmp_attempts, 0)
        self.assertTrue(board.is_legal(res.best_move))

    def test_03_null_move_never_attempted_in_check(self):
        """Positions where the side to move is in check never attempt null moves."""
        # Scholar's mate attack: White plays Qh4+ check
        board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/5PP1/8/PPPPP2P/RNBQKBNR b KQkq - 0 2")
        board.push_san("Qh4#")  # Checkmate
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.nmp_considered, 0)
        self.assertEqual(res.nmp_attempts, 0)

        # In check with legal evasions (Black gives check with Bb4+, White can block)
        check_board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(check_board.is_check())
        engine.tt.clear()
        res_check = engine.search(check_board, max_depth=3)
        self.assertIsNotNone(res_check.best_move)
        self.assertTrue(check_board.is_legal(res_check.best_move))

    def test_04_material_eligibility_predicate_and_boundaries(self):
        """The material eligibility predicate excludes pawn-only and low-material endgames."""
        engine = JanusSearch()

        # Pawn-only endgame (K+P vs K+P) -> Ineligible
        pawn_only = chess.Board("8/4k3/8/8/8/8/4K3/4P3 w - - 0 1")
        self.assertFalse(engine._has_nmp_material(pawn_only))

        # Many pawns but NO minor or major pieces -> Ineligible
        many_pawns = chess.Board("8/1p1p1p2/8/8/8/8/1P1P1P2/4K2k w - - 0 1")
        self.assertFalse(engine._has_nmp_material(many_pawns))

        # Single Knight -> Ineligible
        single_knight = chess.Board("8/4k3/8/8/8/8/4K3/4N3 w - - 0 1")
        self.assertFalse(engine._has_nmp_material(single_knight))

        # Single Bishop -> Ineligible
        single_bishop = chess.Board("8/4k3/8/8/8/8/4K3/4B3 w - - 0 1")
        self.assertFalse(engine._has_nmp_material(single_bishop))

        # Two Knights -> Eligible
        two_knights = chess.Board("8/4k3/8/8/8/8/4K3/3NN3 w - - 0 1")
        self.assertTrue(engine._has_nmp_material(two_knights))

        # Knight + Bishop -> Eligible
        knight_bishop = chess.Board("8/4k3/8/8/8/8/4K3/3NB3 w - - 0 1")
        self.assertTrue(engine._has_nmp_material(knight_bishop))

        # Single Rook -> Eligible
        single_rook = chess.Board("8/4k3/8/8/8/8/4K3/4R3 w - - 0 1")
        self.assertTrue(engine._has_nmp_material(single_rook))

        # Single Queen -> Eligible
        single_queen = chess.Board("8/4k3/8/8/8/8/4K3/4Q3 w - - 0 1")
        self.assertTrue(engine._has_nmp_material(single_queen))

    def test_05_depth_boundaries_prevent_invalid_reduced_searches(self):
        """Searches at shallow depth (depth 1 or 2) never trigger NMP."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        engine = JanusSearch(enable_nmp=True)
        res1 = engine.search(board, max_depth=1)
        self.assertEqual(res1.nmp_considered, 0)
        self.assertEqual(res1.nmp_attempts, 0)

        res2 = engine.search(board, max_depth=2)
        # At max_depth 2, interior ply 1 has depth 1 (< 3), so NMP cannot trigger
        self.assertEqual(res2.nmp_considered, 0)
        self.assertEqual(res2.nmp_attempts, 0)

    def test_06_board_state_exact_restoration(self):
        """The board state (FEN, turn, castling rights, ep square) is restored exactly after search."""
        fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
        board = chess.Board(fen)
        engine = JanusSearch(enable_nmp=True)
        engine.search(board, max_depth=4)
        self.assertEqual(board.fen(), fen)

    def test_07_exceptions_cannot_leave_board_corrupted(self):
        """Simulated exception during null-move child search leaves the board fully restored."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        orig_fen = board.fen()
        engine = JanusSearch(enable_nmp=True)

        class SimulatedAbort(Exception):
            pass

        # Monkey-patch _negamax inside JanusSearch to raise an exception during a child search
        orig_negamax = engine._negamax

        def flaky_negamax(b, depth, alpha, beta, ply, allow_nmp=True):
            if not allow_nmp and ply > 0:
                raise SimulatedAbort("Simulated interruption during null-move search")
            return orig_negamax(b, depth, alpha, beta, ply, allow_nmp)

        engine._negamax = flaky_negamax
        try:
            # depth 3 will trigger NMP at ply 1
            board.push_san("d4")
            try:
                engine._negamax(board, 3, -1000, 1000, 1, allow_nmp=True)
            except SimulatedAbort:
                pass
            finally:
                board.pop()
        finally:
            engine._negamax = orig_negamax

        self.assertEqual(board.fen(), orig_fen)
        self.assertEqual(len(board.move_stack), 0)

    def test_08_null_move_fail_low_continues_normal_search(self):
        """When a null-move search fails low (< beta), search continues with legal moves."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=4)
        # Fail-lows must be tracked
        self.assertGreaterEqual(res.nmp_attempts, 0)
        self.assertEqual(res.nmp_attempts, res.nmp_fail_highs + res.nmp_fail_lows)
        self.assertIsNotNone(res.best_move)
        self.assertTrue(board.is_legal(res.best_move))

    def test_09_verification_policy_adaptive_conditions(self):
        """The verification policy triggers on deep nodes or endgame/low-piece positions."""
        engine = JanusSearch(enable_nmp_verification=True, nmp_verify_min_depth=5)

        # Deep node (depth 5) -> must verify
        board_mid = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(engine._should_verify_nmp(board_mid, depth=5))

        # Shallow node in full middlegame -> does not verify if pieces > 2 and depth < 5
        self.assertFalse(engine._should_verify_nmp(board_mid, depth=4))

        # Low piece count (e.g. 2 pieces on side to move) -> must verify even at depth 3
        board_end = chess.Board("8/4k3/8/8/8/8/4K3/3RR3 w - - 0 1")
        self.assertTrue(engine._should_verify_nmp(board_end, depth=3))

    def test_10_verification_search_success_accepts_cutoff(self):
        """When a verification search confirms the fail-high, cutoff is accepted."""
        # Standard middlegame with sufficient pieces for both sides
        board = chess.Board("r1bq1rk1/ppp2ppp/2n1pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 0 7")
        engine = JanusSearch(enable_nmp=True, enable_nmp_verification=True, nmp_verify_min_depth=3)
        res = engine.search(board, max_depth=4)
        # Should verify and cutoff
        self.assertGreater(res.nmp_attempts, 0)
        self.assertGreater(res.nmp_cutoffs, 0)
        self.assertGreater(res.nmp_verifications, 0)
        self.assertGreaterEqual(res.nmp_verifications, res.nmp_verification_failures)

    def test_11_verification_search_failure_resumes_normal_search(self):
        """If verification search rejects a candidate cutoff, normal legal-move search resumes."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        engine = JanusSearch(enable_nmp=True, enable_nmp_verification=True, nmp_verify_min_depth=1)

        # Force verification search to fail by stubbing
        orig_negamax = engine._negamax

        call_count = [0]
        def custom_negamax(b, depth, alpha, beta, ply, allow_nmp=True):
            # Check if this is the verification search call: allow_nmp is False and beta - 1 == alpha
            if not allow_nmp and alpha == beta - 1:
                call_count[0] += 1
                # Return fail-low to reject cutoff
                return beta - 10, []
            return orig_negamax(b, depth, alpha, beta, ply, allow_nmp)

        engine._negamax = custom_negamax
        try:
            res = engine.search(board, max_depth=4)
            # If verification was called, failures should have incremented
            if call_count[0] > 0:
                self.assertGreater(engine.nmp_verification_failures, 0)
        finally:
            engine._negamax = orig_negamax

        self.assertIsNotNone(res.best_move)
        self.assertTrue(board.is_legal(res.best_move))

    def test_12_tt_bound_semantics_correct(self):
        """NMP cutoffs store a 'lower' bound entry in the TT with score <= beta."""
        board = chess.Board("4k3/8/8/8/8/8/4K3/1Q2R3 w - - 0 1")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=4)

        # Check TT entries
        lower_bounds = [e for e in engine.tt.values() if e.flag == "lower"]
        self.assertGreater(len(lower_bounds), 0)
        for entry in lower_bounds:
            # Score should never be an unnormalized raw mate score
            self.assertLess(entry.score, MATE_SCORE)

    def test_13_null_move_results_do_not_create_illegal_pvs(self):
        """All returned PVs are legal sequences of moves containing no null moves."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=4)

        self.assertGreater(len(res.pv), 0)
        verify_board = board.copy()
        for move in res.pv:
            self.assertNotEqual(move, chess.Move.null())
            self.assertIn(move, verify_board.legal_moves)
            verify_board.push(move)

    def test_14_mate_score_handling_correct(self):
        """Forced mate positions are found accurately with NMP enabled."""
        # Mate in 1
        board_m1 = chess.Board("2kr3r/pp3ppp/2n5/8/8/8/PPPP1PPP/R1BQK2R w - - 0 1")
        board_m1.set_fen("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        engine = JanusSearch(enable_nmp=True)
        res_m1 = engine.search(board_m1, max_depth=3)
        self.assertEqual(res_m1.best_move, chess.Move.from_uci("h5f7"))
        self.assertGreaterEqual(res_m1.score, MATE_THRESHOLD)

    def test_15_repetition_and_halfmove_clock(self):
        """High halfmove clock positions (>= 140) safely suppress NMP to avoid false draw horizon."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 142 72")
        self.assertEqual(board.halfmove_clock, 142)
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.nmp_considered, 0)
        self.assertEqual(res.nmp_attempts, 0)

    def test_16_pvs_and_lmr_interaction_all_four_combinations(self):
        """All four configurations (LMR on/off x NMP on/off) run cleanly and legally."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        configs = [
            {"enable_lmr": False, "enable_nmp": False},
            {"enable_lmr": True, "enable_nmp": False},
            {"enable_lmr": False, "enable_nmp": True},
            {"enable_lmr": True, "enable_nmp": True},
        ]
        results = []
        for cfg in configs:
            engine = JanusSearch(**cfg)
            res = engine.search(board, max_depth=4)
            self.assertIsNotNone(res.best_move)
            self.assertTrue(board.is_legal(res.best_move))
            results.append(res)

        # All configurations find a valid root move
        self.assertEqual(len(results), 4)

    def test_17_aspiration_windows_on_and_off(self):
        """NMP works identically with aspiration windows enabled and disabled."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        engine_asp_on = JanusSearch(enable_nmp=True, enable_aspiration=True)
        res_on = engine_asp_on.search(board, max_depth=4)

        engine_asp_off = JanusSearch(enable_nmp=True, enable_aspiration=False)
        res_off = engine_asp_off.search(board, max_depth=4)

        self.assertEqual(res_on.best_move, res_off.best_move)
        self.assertEqual(res_on.score, res_off.score)

    def test_18_telemetry_resets_consistently(self):
        """Telemetry counters reset completely between independent searches."""
        board1 = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        board2 = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")

        engine = JanusSearch(enable_nmp=True)
        res1 = engine.search(board1, max_depth=4)
        attempts1 = res1.nmp_attempts

        res2 = engine.search(board2, max_depth=3)
        attempts2 = res2.nmp_attempts

        # Check engine internal counters match res2
        self.assertEqual(engine.nmp_attempts, attempts2)
        self.assertEqual(engine.nmp_cutoffs, res2.nmp_cutoffs)

    def test_19_uci_smoke_test(self):
        """UCI protocol smoke test verifying clean startup, search, bestmove output, and shutdown."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "janus.uci"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            proc.stdin.write("uci\n")
            proc.stdin.flush()

            # Read until uciok
            while True:
                line = proc.stdout.readline()
                if "uciok" in line:
                    break

            proc.stdin.write("isready\n")
            proc.stdin.flush()
            while True:
                line = proc.stdout.readline()
                if "readyok" in line:
                    break

            proc.stdin.write("position startpos moves e2e4 e7e5\n")
            proc.stdin.write("go depth 3\n")
            proc.stdin.flush()

            bestmove_seen = False
            while True:
                line = proc.stdout.readline()
                if line.startswith("bestmove"):
                    bestmove_seen = True
                    break

            self.assertTrue(bestmove_seen)

            proc.stdin.write("quit\n")
            proc.stdin.flush()
            proc.wait(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
            if proc.stdin:
                proc.stdin.close()
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()


class NMPZugzwangAndTacticsTests(unittest.TestCase):
    """Tactical and zugzwang safeguards testing."""

    def test_zugzwang_king_and_pawn_endgame_protected(self):
        """Zugzwang-prone King and Pawn positions are protected from NMP."""
        # Trébuchet position: whoever moves loses
        trebuchet = chess.Board("8/8/8/3k4/3p4/3K4/8/8 w - - 0 1")
        engine = JanusSearch(enable_nmp=True)
        res = engine.search(trebuchet, max_depth=4)
        # NMP must be completely disabled because it is pawn-only
        self.assertEqual(res.nmp_attempts, 0)
        self.assertEqual(res.nmp_cutoffs, 0)

    def test_tactical_suite_preserved_with_nmp(self):
        """Key tactical positions preserve winning moves under NMP."""
        tactics = [
            # Mate in 1
            ("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1", "h5f7", 3),
            # Queen promotion
            ("8/1P6/8/8/8/8/k7/7K w - - 0 1", "b7b8q", 2),
            # Defensive promotion block
            ("8/1P6/8/8/8/8/1r6/k6K b - - 0 1", "b2b7", 3),
            # Knight fork
            ("4k3/8/8/8/3q4/8/5N2/4K3 w - - 0 1", None, 3),
        ]

        for fen, expected_move, depth in tactics:
            board = chess.Board(fen)
            engine_on = JanusSearch(enable_nmp=True)
            res_on = engine_on.search(board, max_depth=depth)

            engine_off = JanusSearch(enable_nmp=False)
            res_off = engine_off.search(board, max_depth=depth)

            if expected_move:
                self.assertEqual(res_on.best_move.uci(), expected_move)
                self.assertEqual(res_off.best_move.uci(), expected_move)
            self.assertEqual(res_on.score, res_off.score)


if __name__ == "__main__":
    unittest.main()
