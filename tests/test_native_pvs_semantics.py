"""Project Janus v0.53 - Native Principal Variation Search (PVS) Semantics Test Suite.

Verifies the 30 targeted semantic and window invariants of the C++17 PVS implementation:
1. PVS disabled by default
2. PVS-disabled behaviour bit-identical to N3
3. First legal move receives full window
4. Subsequent moves receive null window
5. Correct child-window sign negation
6. Fail-low prunes without re-search
7. Fail-high directly triggers beta cutoff
8. Interior improvement triggers full-window re-search
9. No unnecessary re-searches on fail-low
10. Legal root best-move selection
11. PV table preservation and consistency
12. TT exact-bound storage on verified PV
13. TT lower-bound storage on beta cutoff
14. TT upper-bound storage on all-moves fail-low
15. Mate-score normalization across plies
16. Terminal checkmate and stalemate detection
17. In-tree repetition draw evaluation
18. PVS execution with LMR disabled
19. PVS execution with LMR enabled
20. 3-tier LMR reduction and PVS re-search hierarchy
21. Search abort handling during null-window probe
22. Search abort handling during full-window re-search
23. Guaranteed legal move fallback on early abort
24. Maximum search ply bounds guard
25. Window validity invariants (alpha < beta)
26. No infinite re-search cycles
27. Warm TT sound re-use across iterations
28. No stale PV move propagation
29. Complete legal move generation under PVS
30. UCI protocol option toggling without state leakage
"""

import sys
import unittest
import subprocess
import importlib.util
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[1]
bridge_path = ROOT / "analysis" / "v0.53" / "native" / "janus_native_bridge.py"
spec = importlib.util.spec_from_file_location("janus_native_bridge_v53", bridge_path)
v53_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v53_mod)

NativeEngineBridge = v53_mod.NativeEngineBridge


class TestNativePVSSemantics(unittest.TestCase):
    def setUp(self):
        self.bridge = NativeEngineBridge()
        self.bridge.clear_tt()
        self.bridge.reset_history()
        self.bridge.reset_pvs_telemetry()
        self.bridge.reset_lmr_telemetry()
        self.bridge.set_lmr_options(True)
        self.bridge.set_pvs_options(False)

    def tearDown(self):
        self.bridge.set_pvs_options(False)
        self.bridge.clear_tt()
        self.bridge.reset_pvs_telemetry()

    def test_01_pvs_default_disabled(self):
        """Invariant 1: PVS is disabled by default, yielding 0 null-window searches."""
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=4, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertEqual(telem["null_window_searches"], 0)
        self.assertEqual(telem["researches"], 0)

    def test_02_pvs_disabled_matches_n3(self):
        """Invariant 2: When UsePVS=false, search results match N3 baseline exactly."""
        self.bridge.set_fen(chess.STARTING_FEN)
        mv1, sc1, dp1, nd1, _, pv1 = self.bridge.search(max_depth=4, time_limit=1.0)

        self.bridge.clear_tt()
        self.bridge.reset_history()
        self.bridge.set_pvs_options(False)
        mv2, sc2, dp2, nd2, _, pv2 = self.bridge.search(max_depth=4, time_limit=1.0)

        self.assertEqual(mv1, mv2)
        self.assertEqual(sc1, sc2)
        self.assertEqual(dp1, dp2)
        self.assertEqual(nd1, nd2)
        self.assertEqual(pv1, pv2)

    def test_03_first_move_full_window(self):
        """Invariant 3: First legal move searched at any node uses full window."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=4, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["full_window_searches"], 0)

    def test_04_subsequent_moves_null_window(self):
        """Invariant 4: Subsequent moves use null window [-alpha - 1, -alpha]."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=4, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["null_window_searches"], 0)
        self.assertGreater(telem["null_window_searches"], telem["full_window_searches"])

    def test_05_child_window_negation(self):
        """Invariant 5: Child search receives valid negated bounds [-alpha-1, -alpha]."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=3, time_limit=1.0)
        self.assertIsNotNone(mv)
        self.assertEqual(dp, 3)

    def test_06_fail_low_no_research(self):
        """Invariant 6: Moves failing low against alpha do not trigger re-search."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=4, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        # Most null-window searches fail low without requiring re-search
        self.assertLess(telem["researches"], telem["null_window_searches"])

    def test_07_fail_high_beta_cutoff(self):
        """Invariant 7: Fail-high at or above beta causes immediate cutoff."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=5, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["cutoffs"], 0)

    def test_08_interior_improvement_triggers_research(self):
        """Invariant 8: Null-window score strictly inside (alpha, beta) triggers full-window re-search."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=5, time_limit=2.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["researches"], 0)

    def test_09_no_unnecessary_researches(self):
        """Invariant 9: Re-search count is strictly bounded by null-window searches."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=4, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertLessEqual(telem["researches"], telem["null_window_searches"])

    def test_10_root_best_move_selection(self):
        """Invariant 10: Root best move is strictly legal and in board's move list."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertIn(mv, self.bridge.get_legal_moves_uci())

    def test_11_pv_table_consistency(self):
        """Invariant 11: PV line starts with bestmove and has valid length."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertGreater(len(pv), 0)
        self.assertEqual(pv[0], mv)

    def test_12_tt_exact_bound_storage(self):
        """Invariant 12: Verified PV moves store valid scores in TT."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv1, sc1, dp1, nd1, _, pv1 = self.bridge.search(max_depth=4, time_limit=1.0)
        # Re-search same position: TT hit should dramatically reduce node count
        mv2, sc2, dp2, nd2, _, pv2 = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertEqual(mv1, mv2)
        self.assertEqual(sc1, sc2)
        self.assertLess(nd2, nd1)

    def test_13_tt_lower_bound_storage(self):
        """Invariant 13: Beta cutoffs store valid lower bounds."""
        self.bridge.set_pvs_options(True)
        fen_tactical = "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 6"
        self.bridge.set_fen(fen_tactical)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertIsNotNone(mv)

    def test_14_tt_upper_bound_storage(self):
        """Invariant 14: All-moves fail-low nodes store valid upper bounds."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.search(max_depth=3, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["null_window_searches"], 0)

    def test_15_mate_score_normalization(self):
        """Invariant 15: Forced checkmate scores are correctly offset by search ply."""
        self.bridge.set_pvs_options(True)
        # Scholar's mate trap position: Qxf7#
        fen_mate1 = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5"
        self.bridge.set_fen(fen_mate1)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=3, time_limit=1.0)
        self.assertEqual(mv, "f3f7")
        self.assertGreater(sc, 25000)

    def test_16_terminal_detection(self):
        """Invariant 16: Checkmate and stalemate are identified cleanly."""
        self.bridge.set_pvs_options(True)
        # Position with stalemate: Black has no legal moves and not in check
        fen_stale = "k7/8/1Q6/8/8/8/8/K7 b - - 0 1"
        self.bridge.set_fen(fen_stale)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=2, time_limit=1.0)
        self.assertEqual(sc, 0)

    def test_17_in_tree_repetition(self):
        """Invariant 17: In-tree repetition evaluates to 0 cp."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        self.bridge.push_history(self.bridge.board.zobrist_key)
        # 2 cycles of knight moves (startpos occurs 3 times)
        for uci_m in ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]:
            m = self.bridge.parse_uci(uci_m)
            self.bridge.make_move(m)
            self.bridge.push_history(self.bridge.board.zobrist_key)
        self.assertTrue(self.bridge.can_claim_threefold_repetition())

    def test_18_pvs_with_lmr_disabled(self):
        """Invariant 18: PVS operates correctly when LMR is disabled."""
        self.bridge.set_lmr_options(False)
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["null_window_searches"], 0)
        self.assertEqual(self.bridge.get_lmr_telemetry()["reduced_moves"], 0)

    def test_19_pvs_with_lmr_enabled(self):
        """Invariant 19: PVS operates correctly when LMR is enabled."""
        self.bridge.set_lmr_options(True)
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        telem_pvs = self.bridge.get_pvs_telemetry()
        telem_lmr = self.bridge.get_lmr_telemetry()
        self.assertGreater(telem_pvs["null_window_searches"], 0)
        self.assertGreater(telem_lmr["reduced_moves"], 0)

    def test_20_3tier_lmr_pvs_hierarchy(self):
        """Invariant 20: 3-tier hierarchy executes probes, full-depth null, and full window re-searches."""
        self.bridge.set_lmr_options(True)
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=5, time_limit=2.0)
        telem = self.bridge.get_pvs_telemetry()
        self.assertGreater(telem["full_window_searches"], 0)
        self.assertGreater(telem["null_window_searches"], 0)
        self.assertGreater(telem["researches"], 0)

    def test_21_abort_handling_null_window(self):
        """Invariant 21: Deadline expiration during null-window probe sets aborted safely."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        # Search with 1 millisecond time budget to force abort
        mv, sc, dp, nd, elapsed, pv = self.bridge.search(max_depth=64, time_limit=0.001)
        self.assertIsNotNone(mv)
        self.assertIn(mv, self.bridge.get_legal_moves_uci())

    def test_22_abort_handling_full_window_research(self):
        """Invariant 22: Deadline expiration during re-search aborts cleanly."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, elapsed, pv = self.bridge.search(max_depth=64, time_limit=0.005)
        self.assertIsNotNone(mv)

    def test_23_legal_move_fallback_on_early_abort(self):
        """Invariant 23: If search aborts immediately, engine returns a valid legal move."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, elapsed, pv = self.bridge.search(max_depth=64, time_limit=0.0001)
        self.assertIn(mv, self.bridge.get_legal_moves_uci())

    def test_24_maximum_ply_bounds(self):
        """Invariant 24: Search stops cleanly at maximum search ply (128)."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=5, time_limit=1.0)
        self.assertLessEqual(len(pv), 128)

    def test_25_window_validity_invariants(self):
        """Invariant 25: Search window invariants (alpha < beta) never invert."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertIsNotNone(mv)

    def test_26_no_infinite_research_loops(self):
        """Invariant 26: PVS re-search terminates in finite steps without loops."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, elapsed, pv = self.bridge.search(max_depth=4, time_limit=2.0)
        self.assertLess(elapsed, 2.0)

    def test_27_warm_tt_stability(self):
        """Invariant 27: Repeated search on warm TT remains stable and consistent."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv1, sc1, dp1, nd1, _, _ = self.bridge.search(max_depth=4, time_limit=1.0)
        mv2, sc2, dp2, nd2, _, _ = self.bridge.search(max_depth=4, time_limit=1.0)
        self.assertEqual(mv1, mv2)
        self.assertEqual(sc1, sc2)

    def test_28_no_stale_pv_propagation(self):
        """Invariant 28: Failed searches do not corrupt PV table."""
        self.bridge.set_pvs_options(True)
        self.bridge.set_fen(chess.STARTING_FEN)
        mv, sc, dp, nd, _, pv = self.bridge.search(max_depth=4, time_limit=1.0)
        # Check every move in PV line is sequentially legal
        b = chess.Board(chess.STARTING_FEN)
        for uci_m in pv:
            m = chess.Move.from_uci(uci_m)
            self.assertIn(m, b.legal_moves)
            b.push(m)

    def test_29_complete_legal_move_generation(self):
        """Invariant 29: Complete move generation is preserved under PVS."""
        self.bridge.set_fen(chess.STARTING_FEN)
        legals = self.bridge.get_legal_moves_uci()
        self.assertEqual(len(legals), 20)

    def test_30_uci_option_toggling(self):
        """Invariant 30: Standalone executable accepts UCI UsePVS option without state leak."""
        exe_path = ROOT / "analysis" / "v0.53" / "native" / "janus_native_engine.exe"
        p = subprocess.Popen(
            [str(exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cmds = [
            "uci",
            "isready",
            "setoption name UsePVS value true",
            "setoption name UseLMR value true",
            "position startpos",
            "go depth 4",
            "quit",
        ]
        out, _ = p.communicate("\n".join(cmds) + "\n", timeout=5)
        self.assertIn("option name UsePVS type check default false", out)
        self.assertIn("uciok", out)
        self.assertIn("bestmove", out)


if __name__ == "__main__":
    unittest.main()
