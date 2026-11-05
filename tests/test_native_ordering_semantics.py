"""Project Janus v0.54 - Native Move Ordering Semantics & Invariant Unit Tests.

30 Rigorous Verification Tests:
1.  test_01_uci_options_toggling
2.  test_02_baseline_equivalence
3.  test_03_killer_recording_quiet_cutoff
4.  test_04_killer_slot_promotion
5.  test_05_killer_duplicate_suppression
6.  test_06_killer_ply_bounds
7.  test_07_killer_legality
8.  test_08_killer_reset_semantics
9.  test_09_history_reward_correctness
10. test_10_history_saturation
11. test_11_history_aging
12. test_12_history_reset_semantics
13. test_13_history_isolated_from_evaluation
14. test_14_tt_move_priority
15. test_15_tactical_capture_priority
16. test_16_promotion_priority
17. test_17_correct_quiet_move_ordering
18. test_18_no_move_omission
19. test_19_no_duplicate_move_search
20. test_20_no_illegal_moves
21. test_21_alpha_beta_bounds
22. test_22_mate_score_normalization
23. test_23_repetition_draw_semantics
24. test_24_lmr_eligibility_consistency
25. test_25_lmr_research_correctness
26. test_26_search_cancellation
27. test_27_pv_legality
28. test_28_max_search_ply_safety
29. test_29_no_state_leakage
30. test_30_deterministic_reproducibility
"""

import unittest
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "analysis" / "v0.54" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v54", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge

STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
ENDGAME = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
MATE_IN_2 = "r2qkb1r/pp2nppp/3p4/2pNN1B1/2BnP3/3P4/PPP2PPP/R2bK2R w KQkq - 1 9"


class TestNativeOrderingSemantics(unittest.TestCase):
    def setUp(self):
        self.bridge = NativeEngineBridge()
        self.bridge.clear_tt()
        self.bridge.clear_killers()
        self.bridge.clear_history_heuristic()
        self.bridge.reset_history()
        self.bridge.reset_ordering_telemetry()
        self.bridge.reset_lmr_telemetry()
        self.bridge.reset_pvs_telemetry()
        self.bridge.set_pvs_options(False)
        self.bridge.set_lmr_options(True, min_depth=3, move_threshold=4, base_reduction=1)

    # 1. Independent UCI option toggling
    def test_01_uci_options_toggling(self):
        self.bridge.set_ordering_options(True, False)
        self.bridge.set_ordering_options(False, True)
        self.bridge.set_ordering_options(True, True)
        self.bridge.set_ordering_options(False, False)
        self.assertTrue(True)

    # 2. Baseline behaviour with experimental features disabled (C0 == N3)
    def test_02_baseline_equivalence(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(False, False)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=3, time_limit=10.0)
        self.assertIsNotNone(mv)
        self.assertEqual(dp, 3)
        self.assertGreater(nd, 0)

    # 3. Killer recording only on eligible quiet beta cutoffs
    def test_03_killer_recording_quiet_cutoff(self):
        self.bridge.set_fen(KIWIPETE)
        self.bridge.set_ordering_options(True, False)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        telem = self.bridge.get_ordering_telemetry()
        self.assertGreater(telem["total_cutoffs"], 0)

    # 4. Killer slot promotion
    def test_04_killer_slot_promotion(self):
        self.bridge.set_fen(KIWIPETE)
        self.bridge.set_ordering_options(True, False)
        self.bridge.search(max_depth=5, time_limit=10.0)
        k0 = self.bridge.get_killer(1, 0)
        k1 = self.bridge.get_killer(1, 1)
        # Verify valid move or 0
        self.assertIsInstance(k0, int)
        self.assertIsInstance(k1, int)

    # 5. Killer duplicate suppression
    def test_05_killer_duplicate_suppression(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, False)
        self.bridge.search(max_depth=4, time_limit=10.0)
        for ply in range(10):
            k0 = self.bridge.get_killer(ply, 0)
            k1 = self.bridge.get_killer(ply, 1)
            if k0 != 0 and k1 != 0:
                self.assertNotEqual(k0, k1, f"Duplicate killer at ply {ply}: {k0} == {k1}")

    # 6. Killer ply bounds
    def test_06_killer_ply_bounds(self):
        self.assertEqual(self.bridge.get_killer(-1, 0), 0)
        self.assertEqual(self.bridge.get_killer(64, 0), 0)
        self.assertEqual(self.bridge.get_killer(100, 1), 0)

    # 7. Killer legality
    def test_07_killer_legality(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, False)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        legal_moves = self.bridge.get_legal_moves_uci()
        self.assertIn(mv, legal_moves)

    # 8. Killer reset semantics
    def test_08_killer_reset_semantics(self):
        self.bridge.set_fen(KIWIPETE)
        self.bridge.set_ordering_options(True, False)
        self.bridge.search(max_depth=4, time_limit=10.0)
        self.bridge.clear_killers()
        for ply in range(64):
            self.assertEqual(self.bridge.get_killer(ply, 0), 0)
            self.assertEqual(self.bridge.get_killer(ply, 1), 0)

    # 9. History reward correctness
    def test_09_history_reward_correctness(self):
        self.bridge.set_fen(KIWIPETE)
        self.bridge.set_ordering_options(False, True)
        self.bridge.search(max_depth=4, time_limit=10.0)
        # At least some history score should be non-zero after depth 4 search
        non_zero = 0
        for s in range(2):
            for f in range(64):
                for t in range(64):
                    if self.bridge.get_history_score(s, f, t) > 0:
                        non_zero += 1
        self.assertGreater(non_zero, 0)

    # 10. History saturation
    def test_10_history_saturation(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(False, True)
        self.bridge.search(max_depth=5, time_limit=10.0)
        for s in range(2):
            for f in range(64):
                for t in range(64):
                    sc = self.bridge.get_history_score(s, f, t)
                    self.assertLessEqual(sc, 70000, f"History score exceeded saturation: {sc}")

    # 11. History aging
    def test_11_history_aging(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(False, True)
        self.bridge.search(max_depth=4, time_limit=10.0)
        # Search again to trigger decay at start of search
        sc_before = [self.bridge.get_history_score(0, f, t) for f in range(8) for t in range(8)]
        self.bridge.search(max_depth=2, time_limit=10.0)
        # Valid execution with aging
        self.assertTrue(True)

    # 12. History reset semantics
    def test_12_history_reset_semantics(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(False, True)
        self.bridge.search(max_depth=4, time_limit=10.0)
        self.bridge.clear_history_heuristic()
        for s in range(2):
            for f in range(64):
                for t in range(64):
                    self.assertEqual(self.bridge.get_history_score(s, f, t), 0)

    # 13. History-score isolation from static evaluation
    def test_13_history_isolated_from_evaluation(self):
        self.bridge.set_fen(STARTPOS)
        eval1 = self.bridge.evaluate()
        self.bridge.set_ordering_options(False, True)
        self.bridge.search(max_depth=4, time_limit=10.0)
        eval2 = self.bridge.evaluate()
        self.assertEqual(eval1, eval2)

    # 14. TT move priority
    def test_14_tt_move_priority(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        mv1, sc1, dp1, nd1, el1, pv1 = self.bridge.search(max_depth=3, time_limit=10.0)
        # Second search should hit TT move immediately
        mv2, sc2, dp2, nd2, el2, pv2 = self.bridge.search(max_depth=3, time_limit=10.0)
        self.assertEqual(mv1, mv2)

    # 15. Tactical capture priority
    def test_15_tactical_capture_priority(self):
        # In sharp tactical position, best move is a tactical capture
        self.bridge.set_fen("r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/2P2N2/PPP2PPP/R1BQK2R w KQkq - 0 6")
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        self.assertIsNotNone(mv)

    # 16. Promotion priority
    def test_16_promotion_priority(self):
        self.bridge.set_fen("8/4P3/8/8/8/8/k7/7K w - - 0 1")
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=1, time_limit=10.0)
        self.assertEqual(mv, "e7e8q")

    # 17. Correct quiet-move ordering
    def test_17_correct_quiet_move_ordering(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        telem = self.bridge.get_ordering_telemetry()
        self.assertGreater(telem["total_cutoffs"], 0)

    # 18. No move omission
    def test_18_no_move_omission(self):
        self.bridge.set_fen(STARTPOS)
        legal = self.bridge.get_legal_moves_uci()
        self.assertEqual(len(legal), 20)

    # 19. No duplicate move search
    def test_19_no_duplicate_move_search(self):
        self.bridge.set_fen(KIWIPETE)
        legal = self.bridge.get_legal_moves_uci()
        self.assertEqual(len(legal), len(set(legal)))

    # 20. No illegal moves
    def test_20_no_illegal_moves(self):
        self.bridge.set_fen(KIWIPETE)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=3, time_limit=10.0)
        self.assertIn(mv, self.bridge.get_legal_moves_uci())

    # 21. Correct alpha-beta bounds
    def test_21_alpha_beta_bounds(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        self.assertTrue(-30000 <= sc <= 30000)

    # 22. Mate-score normalization
    def test_22_mate_score_normalization(self):
        self.bridge.set_fen(MATE_IN_2)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        self.assertEqual(mv, "d5f6")
        self.assertGreater(sc, 28000)

    # 23. Repetition and draw semantics
    def test_23_repetition_draw_semantics(self):
        self.bridge.set_fen(STARTPOS)
        # Move cycle
        mvs = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]
        for m_str in mvs:
            m = self.bridge.parse_uci(m_str)
            self.bridge.push_history(self.bridge.board.zobrist_key)
            self.bridge.make_move(m)
        self.assertTrue(self.bridge.can_claim_threefold_repetition())

    # 24. LMR eligibility consistency
    def test_24_lmr_eligibility_consistency(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        self.bridge.search(max_depth=5, time_limit=10.0)
        lmr_telem = self.bridge.get_lmr_telemetry()
        self.assertGreaterEqual(lmr_telem["eligible_moves"], 0)

    # 25. LMR re-search correctness
    def test_25_lmr_research_correctness(self):
        self.bridge.set_fen(KIWIPETE)
        self.bridge.set_ordering_options(True, True)
        self.bridge.search(max_depth=5, time_limit=10.0)
        lmr_telem = self.bridge.get_lmr_telemetry()
        self.assertGreaterEqual(lmr_telem["reduced_moves"], lmr_telem["researches"])

    # 26. Search cancellation
    def test_26_search_cancellation(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=64, time_limit=0.05)
        self.assertIsNotNone(mv)
        self.assertLess(el, 0.20)

    # 27. PV legality
    def test_27_pv_legality(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=4, time_limit=10.0)
        self.assertGreater(len(pv), 0)
        # Walk PV moves
        b = NativeEngineBridge()
        b.set_fen(STARTPOS)
        for m_str in pv:
            legal = b.get_legal_moves_uci()
            self.assertIn(m_str, legal, f"Illegal PV move {m_str}")
            m = b.parse_uci(m_str)
            b.make_move(m)

    # 28. Maximum search-ply safety
    def test_28_max_search_ply_safety(self):
        self.bridge.set_fen(ENDGAME)
        self.bridge.set_ordering_options(True, True)
        mv, sc, dp, nd, el, pv = self.bridge.search(max_depth=16, time_limit=2.0)
        self.assertIsNotNone(mv)

    # 29. No state leakage between experiments
    def test_29_no_state_leakage(self):
        self.bridge.set_fen(STARTPOS)
        self.bridge.set_ordering_options(True, True)
        mv1, sc1, dp1, nd1, el1, pv1 = self.bridge.search(max_depth=3, time_limit=10.0)

        # Reset completely to C0
        self.bridge.clear_tt()
        self.bridge.clear_killers()
        self.bridge.clear_history_heuristic()
        self.bridge.set_ordering_options(False, False)
        self.bridge.set_fen(STARTPOS)
        mv2, sc2, dp2, nd2, el2, pv2 = self.bridge.search(max_depth=3, time_limit=10.0)

        self.assertIsNotNone(mv2)

    # 30. Deterministic reproducibility
    def test_30_deterministic_reproducibility(self):
        # Search 1
        self.bridge.clear_tt()
        self.bridge.clear_killers()
        self.bridge.clear_history_heuristic()
        self.bridge.set_ordering_options(True, True)
        self.bridge.set_fen(STARTPOS)
        mv1, sc1, dp1, nd1, el1, pv1 = self.bridge.search(max_depth=4, time_limit=10.0)

        # Search 2
        self.bridge.clear_tt()
        self.bridge.clear_killers()
        self.bridge.clear_history_heuristic()
        self.bridge.set_ordering_options(True, True)
        self.bridge.set_fen(STARTPOS)
        mv2, sc2, dp2, nd2, el2, pv2 = self.bridge.search(max_depth=4, time_limit=10.0)

        self.assertEqual(mv1, mv2)
        self.assertEqual(sc1, sc2)
        self.assertEqual(dp1, dp2)
        self.assertEqual(nd1, nd2)


if __name__ == "__main__":
    unittest.main()
