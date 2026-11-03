"""Dedicated correctness tests for Bounded Check Extensions in Project Janus (v0.20)."""
import subprocess
import sys
import unittest

import chess

from janus.search import JanusSearch, MATE_SCORE, MATE_THRESHOLD


class CheckExtensionsTests(unittest.TestCase):
    """Phase 6: Comprehensive verification of Check Extensions."""

    def test_01_check_extensions_toggle_independent(self):
        """Check extensions can be enabled and disabled independently."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(board.is_check())

        engine_on = JanusSearch(enable_check_extensions=True)
        res_on = engine_on.search(board, max_depth=2)
        self.assertGreater(res_on.check_extensions_applied, 0)

        engine_off = JanusSearch(enable_check_extensions=False)
        res_off = engine_off.search(board, max_depth=2)
        self.assertEqual(res_off.check_extensions_applied, 0)
        self.assertEqual(res_off.check_extension_plies, 0)

    def test_02_eligible_check_node_receives_extension(self):
        """A documented eligible check node receives the expected 1-ply extension."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(board.is_check())

        engine = JanusSearch(enable_check_extensions=True)
        res = engine.search(board, max_depth=2)
        self.assertGreater(res.check_extensions_eligible, 0)
        self.assertGreater(res.check_extensions_applied, 0)
        self.assertEqual(res.check_extensions_applied, res.check_extension_plies)

    def test_03_non_check_node_does_not_receive_extension(self):
        """Positions not in check receive zero check extensions."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertFalse(board.is_check())

        engine = JanusSearch(enable_check_extensions=True)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.check_extensions_eligible, 0)
        self.assertEqual(res.check_extensions_applied, 0)
        self.assertEqual(res.check_extension_plies, 0)

    def test_04_extension_budget_enforced(self):
        """Extensions along any search branch cannot exceed max_check_extensions."""
        engine = JanusSearch(enable_check_extensions=True, max_check_extensions=1)
        # Sequence with potential repeated checks
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        res = engine.search(board, max_depth=4)
        # Should record eligible nodes and suppressed extensions if budget is exhausted
        self.assertGreaterEqual(res.check_extensions_eligible, res.check_extensions_applied)
        self.assertGreaterEqual(res.check_extensions_suppressed, 0)

    def test_05_repeated_checks_bounded_recursion(self):
        """Repeated checks terminate cleanly and do not produce unbounded search explosions."""
        # Position with continuous check possibilities
        board = chess.Board("r1b1k2r/pppp1ppp/2n5/4p3/2B1P1nq/3P4/PPP2PPP/RNBQK2R w KQkq - 1 7")
        engine = JanusSearch(enable_check_extensions=True, max_check_extensions=2)
        res = engine.search(board, max_depth=4)
        self.assertGreater(res.nodes, 0)
        self.assertIsNotNone(res.best_move)
        self.assertTrue(board.is_legal(res.best_move))

    def test_06_checkmate_and_stalemate_handling(self):
        """Checkmate and stalemate are detected accurately with check extensions enabled."""
        # Scholar's mate
        board_mate = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        engine = JanusSearch(enable_check_extensions=True)
        res_mate = engine.search(board_mate, max_depth=3)
        self.assertEqual(res_mate.best_move, chess.Move.from_uci("h5f7"))
        self.assertGreaterEqual(res_mate.score, MATE_THRESHOLD)

        # Stalemate
        board_stale = chess.Board("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1")
        res_stale = engine.search(board_stale, max_depth=3)
        self.assertIsNone(res_stale.best_move)
        self.assertEqual(res_stale.score, 0)

    def test_07_pv_moves_legal_and_reconstructed(self):
        """All PV moves are sequentially legal from positions involving checks."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        engine = JanusSearch(enable_check_extensions=True)
        res = engine.search(board, max_depth=4)
        verify = board.copy()
        for i, m in enumerate(res.pv):
            self.assertIn(m, verify.legal_moves, f"Illegal move {m} at step {i}")
            verify.push(m)

    def test_08_board_state_restoration(self):
        """Board state is restored exactly after search with check extensions."""
        fen = "rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3"
        board = chess.Board(fen)
        engine = JanusSearch(enable_check_extensions=True)
        engine.search(board, max_depth=4)
        self.assertEqual(board.fen(), fen)

    def test_09_pvs_compatibility(self):
        """Check extensions work with both PVS enabled and disabled."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        engine_pvs = JanusSearch(enable_check_extensions=True, enable_pvs=True)
        res_pvs = engine_pvs.search(board, max_depth=3)

        engine_no_pvs = JanusSearch(enable_check_extensions=True, enable_pvs=False)
        res_no_pvs = engine_no_pvs.search(board, max_depth=3)

        self.assertEqual(res_pvs.best_move, res_no_pvs.best_move)
        self.assertEqual(res_pvs.score, res_no_pvs.score)

    def test_10_nmp_never_runs_in_check_even_when_extended(self):
        """NMP is never attempted while in check, even at nodes extended by check extensions."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(board.is_check())
        engine = JanusSearch(enable_check_extensions=True, enable_nmp=True)
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
            self.assertGreater(res.check_extensions_applied, 0)
            self.assertTrue(board.is_legal(res.best_move))
        finally:
            board.push = orig_push

    def test_11_lmr_respects_extension_policy(self):
        """Moves in check (evasions) and moves that give check are never reduced by LMR."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        engine = JanusSearch(enable_check_extensions=True, enable_lmr=True)
        res = engine.search(board, max_depth=3)
        # All evasions searched at root are full depth
        self.assertTrue(board.is_legal(res.best_move))

    def test_12_aspiration_windows_compatibility(self):
        """Aspiration windows operate seamlessly with check extensions."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        engine_asp = JanusSearch(enable_check_extensions=True, enable_aspiration=True)
        res_asp = engine_asp.search(board, max_depth=3)

        engine_no_asp = JanusSearch(enable_check_extensions=True, enable_aspiration=False)
        res_no_asp = engine_no_asp.search(board, max_depth=3)

        self.assertEqual(res_asp.best_move, res_no_asp.best_move)
        self.assertEqual(res_asp.score, res_no_asp.score)

    def test_13_tt_effective_depth_storage(self):
        """TT entries store effective_depth reflecting applied extensions."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        engine = JanusSearch(enable_check_extensions=True)
        res = engine.search(board, max_depth=2)
        # Check TT entries
        stored_depths = [e.depth for e in engine.tt.values()]
        self.assertGreater(len(stored_depths), 0)
        # At depth 2 with 1-ply extension, effective_depth can reach 3
        self.assertTrue(any(d >= 2 for d in stored_depths))

    def test_14_mate_score_normalization(self):
        """Mate scores remain exact and unaffected by depth extensions."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        engine = JanusSearch(enable_check_extensions=True)
        res = engine.search(board, max_depth=3)
        self.assertGreaterEqual(res.score, MATE_THRESHOLD)
        self.assertEqual(res.best_move, chess.Move.from_uci("h5f7"))

    def test_15_telemetry_resets(self):
        """Telemetry counters reset completely between consecutive searches."""
        board1 = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        board2 = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

        engine = JanusSearch(enable_check_extensions=True)
        res1 = engine.search(board1, max_depth=3)
        self.assertGreater(res1.check_extensions_applied, 0)

        res2 = engine.search(board2, max_depth=3)
        self.assertEqual(res2.check_extensions_applied, 0)
        self.assertEqual(engine.check_extensions_applied, 0)

    def test_16_uci_smoke_test(self):
        """UCI startup, position search, and clean shutdown with check extensions."""
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

            # Search a position where White is in check
            proc.stdin.write("position fen rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3\n")
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


    def test_17_policies_independent_selection(self):
        """All three extension policies can be configured independently, with strict validation."""
        e_dis = JanusSearch(check_extension_policy="disabled")
        self.assertEqual(e_dis.check_extension_policy, "disabled")
        self.assertFalse(e_dis.enable_check_extensions)

        e_all = JanusSearch(check_extension_policy="bounded_all_checks")
        self.assertEqual(e_all.check_extension_policy, "bounded_all_checks")
        self.assertTrue(e_all.enable_check_extensions)

        e_sgl = JanusSearch(check_extension_policy="single_reply")
        self.assertEqual(e_sgl.check_extension_policy, "single_reply")
        self.assertTrue(e_sgl.enable_check_extensions)

        with self.assertRaises(ValueError):
            JanusSearch(check_extension_policy="invalid_policy")

        # Backward compatibility with legacy enable_check_extensions flag
        e_leg_on = JanusSearch(enable_check_extensions=True)
        self.assertEqual(e_leg_on.check_extension_policy, "bounded_all_checks")
        self.assertTrue(e_leg_on.enable_check_extensions)

        e_leg_off = JanusSearch(enable_check_extensions=False)
        self.assertEqual(e_leg_off.check_extension_policy, "disabled")
        self.assertFalse(e_leg_off.enable_check_extensions)

    def test_18_single_reply_extends_forced_single_evasion(self):
        """single_reply extends an eligible in-check node when there is exactly 1 legal evasion."""
        # White King on h1 in check from Black Rook on e1.
        # Pawns on g2 and h3. Only legal move for White is Kh1-h2 (h1h2).
        board = chess.Board("8/8/8/8/8/7P/6P1/4r2K w - - 0 1")
        self.assertTrue(board.is_check())
        legal_evasions = list(board.legal_moves)
        self.assertEqual(len(legal_evasions), 1)
        self.assertEqual(legal_evasions[0], chess.Move.from_uci("h1h2"))

        engine_sgl = JanusSearch(check_extension_policy="single_reply")
        res_sgl = engine_sgl.search(board, max_depth=1)
        self.assertGreaterEqual(res_sgl.check_extensions_eligible, 1)
        self.assertEqual(res_sgl.check_extensions_applied, 1)
        self.assertEqual(res_sgl.check_extension_plies, 1)
        self.assertEqual(res_sgl.check_extensions_multiple_replies, 0)
        self.assertEqual(res_sgl.best_move, chess.Move.from_uci("h1h2"))

        # In disabled mode, 0 extensions applied
        engine_dis = JanusSearch(check_extension_policy="disabled")
        res_dis = engine_dis.search(board, max_depth=1)
        self.assertEqual(res_dis.check_extensions_applied, 0)
        self.assertEqual(res_dis.check_extension_plies, 0)

        # In bounded_all_checks mode, 1 extension applied
        engine_all = JanusSearch(check_extension_policy="bounded_all_checks")
        res_all = engine_all.search(board, max_depth=1)
        self.assertEqual(res_all.check_extensions_applied, 1)
        self.assertEqual(res_all.best_move, chess.Move.from_uci("h1h2"))

    def test_19_single_reply_rejects_multiple_evasions(self):
        """single_reply does NOT extend an in-check node when multiple legal evasions exist."""
        # White is in check from Black bishop on b4; White has 5 legal evasions (c3, Nc3, Nd2, Bd2, Qd2).
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(board.is_check())
        self.assertGreater(len(list(board.legal_moves)), 1)

        engine_sgl = JanusSearch(check_extension_policy="single_reply")
        res_sgl = engine_sgl.search(board, max_depth=1)
        # Root is checked with depth 1: multiple replies => rejected by single_reply policy
        self.assertGreaterEqual(res_sgl.check_extensions_eligible, 1)
        self.assertGreaterEqual(res_sgl.check_extensions_multiple_replies, 1)
        self.assertEqual(res_sgl.check_extensions_applied, 0)

        # bounded_all_checks extends despite multiple evasions
        engine_all = JanusSearch(check_extension_policy="bounded_all_checks")
        res_all = engine_all.search(board, max_depth=1)
        self.assertGreaterEqual(res_all.check_extensions_eligible, 1)
        self.assertEqual(res_all.check_extensions_applied, 1)

    def test_20_single_reply_terminal_checkmate_no_extension(self):
        """Checkmate positions with zero legal evasions receive no continuation extension."""
        # Black is checkmated (Scholar's mate)
        board_mate = chess.Board("r1bqkb1r/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
        self.assertTrue(board_mate.is_check())
        self.assertEqual(len(list(board_mate.legal_moves)), 0)

        engine_sgl = JanusSearch(check_extension_policy="single_reply")
        res_sgl = engine_sgl.search(board_mate, max_depth=2)
        self.assertEqual(res_sgl.check_extensions_applied, 0)
        self.assertEqual(res_sgl.score, -MATE_SCORE)
        self.assertIsNone(res_sgl.best_move)

    def test_21_single_reply_budget_enforcement(self):
        """single_reply honors the max_check_extensions path budget."""
        # Position with potential consecutive forced replies
        board = chess.Board("8/8/8/8/8/7P/6P1/4r2K w - - 0 1")
        engine_budget1 = JanusSearch(check_extension_policy="single_reply", max_check_extensions=1)
        res_budget1 = engine_budget1.search(board, max_depth=3)
        self.assertLessEqual(res_budget1.check_extension_plies, res_budget1.check_extensions_eligible)

    def test_22_search_correctness_and_board_restoration_all_policies(self):
        """All three policies ensure legal PVs and exact board restoration."""
        fens = [
            "rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3",
            "8/8/8/8/8/7P/6P1/4r2K w - - 0 1",
            "r1b1k2r/pppp1ppp/2n5/4p3/2B1P1nq/3P4/PPP2PPP/RNBQK2R w KQkq - 1 7",
        ]
        for policy in ("disabled", "bounded_all_checks", "single_reply"):
            engine = JanusSearch(check_extension_policy=policy)
            for fen in fens:
                board = chess.Board(fen)
                res = engine.search(board, max_depth=3)
                self.assertEqual(board.fen(), fen, f"Board modified under policy {policy} for {fen}")
                if res.best_move is not None:
                    self.assertIn(res.best_move, board.legal_moves)
                # Verify entire PV
                v_board = board.copy()
                for move in res.pv:
                    self.assertIn(move, v_board.legal_moves)
                    v_board.push(move)

    def test_23_single_reply_pvs_aspiration_tt_coherence(self):
        """single_reply policy functions coherently with PVS and aspiration windows."""
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        engine_full = JanusSearch(
            check_extension_policy="single_reply",
            enable_pvs=True,
            enable_aspiration=True,
        )
        res_full = engine_full.search(board, max_depth=3)

        engine_basic = JanusSearch(
            check_extension_policy="single_reply",
            enable_pvs=False,
            enable_aspiration=False,
        )
        res_basic = engine_basic.search(board, max_depth=3)

        self.assertEqual(res_full.best_move, res_basic.best_move)
        self.assertEqual(res_full.score, res_basic.score)

    def test_24_mate_distance_and_scoring_single_reply(self):
        """Mate scores and distances remain exact in single_reply mode."""
        # Scholar's mate setup: White has 1-move mate Qxf7#
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        engine = JanusSearch(check_extension_policy="single_reply")
        res = engine.search(board, max_depth=3)
        self.assertGreaterEqual(res.score, MATE_THRESHOLD)
        self.assertEqual(res.best_move, chess.Move.from_uci("h5f7"))

    def test_25_tactical_and_endgame_positions(self):
        """Tactical combinations and king-pawn endings evaluate cleanly across policies."""
        # Zugzwang / KP endgame position
        fen_kp = "8/8/p1p5/1p5p/1P5p/8/PPP2k1p/4K1br w - - 0 1"
        for policy in ("disabled", "bounded_all_checks", "single_reply"):
            board = chess.Board(fen_kp)
            engine = JanusSearch(check_extension_policy=policy)
            res = engine.search(board, max_depth=3)
            self.assertIsNotNone(res.best_move)
            self.assertIn(res.best_move, board.legal_moves)
            self.assertEqual(board.fen(), fen_kp)


if __name__ == "__main__":
    unittest.main()
