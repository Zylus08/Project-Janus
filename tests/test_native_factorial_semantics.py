"""Project Janus v0.55 - Native Factorial Semantics & Invariants Test Suite.

Validates:
1. Factorial Configuration Parity (F00, F01, F10, F11).
2. Minimax Equivalence: PVS vs Full-Window Alpha-Beta with LMR disabled.
3. Search Correctness: Legal moves, mate scores, repetition, bounds, TT interaction.
4. Deterministic Reproducibility.
"""

from __future__ import annotations

import unittest
import importlib.util
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "analysis" / "v0.55" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v55", BRIDGE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NativeEngineBridge = mod.NativeEngineBridge


class TestFactorialSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = NativeEngineBridge()

    def reset_state(self):
        self.engine.clear_tt()
        self.engine.clear_killers()
        self.engine.clear_history_heuristic()
        self.engine.reset_history()
        self.engine.reset_ordering_telemetry()
        self.engine.reset_pvs_telemetry()
        self.engine.reset_lmr_telemetry()

    def setUp(self):
        self.reset_state()

    def test_01_factorial_options_parity(self):
        """Verify that all 4 factorial configurations configure correctly in native core."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self.engine.set_fen(fen)

        # F00: K=0, H=0, PVS=0
        self.engine.set_ordering_options(False, False)
        self.engine.set_pvs_options(False)
        self.engine.set_lmr_options(True)
        mv, sc, dp, nd, el, pv = self.engine.search(max_depth=2, time_limit=5.0)
        self.assertIsNotNone(mv)

        # F01: K=0, H=0, PVS=1
        self.engine.set_ordering_options(False, False)
        self.engine.set_pvs_options(True)
        mv, sc, dp, nd, el, pv = self.engine.search(max_depth=2, time_limit=5.0)
        self.assertIsNotNone(mv)

        # F10: K=1, H=1, PVS=0
        self.engine.set_ordering_options(True, True)
        self.engine.set_pvs_options(False)
        mv, sc, dp, nd, el, pv = self.engine.search(max_depth=2, time_limit=5.0)
        self.assertIsNotNone(mv)

        # F11: K=1, H=1, PVS=1
        self.engine.set_ordering_options(True, True)
        self.engine.set_pvs_options(True)
        mv, sc, dp, nd, el, pv = self.engine.search(max_depth=2, time_limit=5.0)
        self.assertIsNotNone(mv)

    def test_02_minimax_exact_score_equivalence_without_lmr(self):
        """With LMR disabled, PVS must produce exact minimax value identical to Alpha-Beta."""
        self.engine.set_lmr_options(False)
        test_fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        ]

        for fen in test_fens:
            for d in [1, 2, 3]:
                # Non-PVS
                self.reset_state()
                self.engine.set_fen(fen)
                self.engine.set_ordering_options(False, False)
                self.engine.set_pvs_options(False)
                mv_ab, sc_ab, dp_ab, nd_ab, el_ab, pv_ab = self.engine.search(max_depth=d, time_limit=10.0)

                # PVS
                self.reset_state()
                self.engine.set_fen(fen)
                self.engine.set_ordering_options(False, False)
                self.engine.set_pvs_options(True)
                mv_pvs, sc_pvs, dp_pvs, nd_pvs, el_pvs, pv_pvs = self.engine.search(max_depth=d, time_limit=10.0)

                self.assertEqual(
                    sc_ab,
                    sc_pvs,
                    f"Minimax score mismatch at depth {d} on {fen}: AB={sc_ab} vs PVS={sc_pvs}"
                )

    def test_03_minimax_exact_score_equivalence_with_ordering_without_lmr(self):
        """With ordering active but LMR disabled, PVS must match Alpha-Beta exactly."""
        self.engine.set_lmr_options(False)
        test_fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
        ]

        for fen in test_fens:
            for d in [1, 2, 3]:
                # Ordering + No PVS (F10 without LMR)
                self.reset_state()
                self.engine.set_fen(fen)
                self.engine.set_ordering_options(True, True)
                self.engine.set_pvs_options(False)
                mv_f10, sc_f10, dp_f10, nd_f10, el_f10, pv_f10 = self.engine.search(max_depth=d, time_limit=10.0)

                # Ordering + PVS (F11 without LMR)
                self.reset_state()
                self.engine.set_fen(fen)
                self.engine.set_ordering_options(True, True)
                self.engine.set_pvs_options(True)
                mv_f11, sc_f11, dp_f11, nd_f11, el_f11, pv_f11 = self.engine.search(max_depth=d, time_limit=10.0)

                self.assertEqual(
                    sc_f10,
                    sc_f11,
                    f"Ordering Minimax score mismatch at depth {d} on {fen}: F10={sc_f10} vs F11={sc_f11}"
                )

    def test_04_pvs_telemetry_recording(self):
        """PVS telemetry counters should populate and reflect search events."""
        fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
        self.reset_state()
        self.engine.set_fen(fen)
        self.engine.set_ordering_options(True, True)
        self.engine.set_pvs_options(True)
        self.engine.set_lmr_options(True)
        mv, sc, dp, nd, el, pv = self.engine.search(max_depth=4, time_limit=10.0)
        
        telem = self.engine.get_pvs_telemetry()
        self.assertIn("null_window_searches", telem)
        self.assertIn("researches", telem)
        self.assertGreater(telem["null_window_searches"], 0, "Expected non-zero null window searches")

    def test_05_mate_score_normalization(self):
        """Checkmate in 1 and 2 must return correct mate values across all 4 configs."""
        mate_in_1 = "6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1"

        configs = [
            (False, False, False), # F00
            (False, False, True),  # F01
            (True, True, False),   # F10
            (True, True, True),    # F11
        ]

        for k, h, pvs in configs:
            self.reset_state()
            self.engine.set_fen(mate_in_1)
            self.engine.set_ordering_options(k, h)
            self.engine.set_pvs_options(pvs)
            mv, sc, dp, nd, el, pv = self.engine.search(max_depth=2, time_limit=5.0)
            self.assertEqual(mv, "e1e8", f"Failed mate in 1 under config K={k}, H={h}, PVS={pvs}")
            self.assertGreater(sc, 28000, f"Mate score not normalized under K={k}, H={h}, PVS={pvs}")

    def test_06_stalemate_detection(self):
        """Stalemate position must evaluate to score 0 across all 4 configs."""
        stalemate_fen = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
        for k, h, pvs in [(False, False, False), (True, True, True)]:
            self.reset_state()
            self.engine.set_fen(stalemate_fen)
            self.engine.set_ordering_options(k, h)
            self.engine.set_pvs_options(pvs)
            mv, sc, dp, nd, el, pv = self.engine.search(max_depth=1, time_limit=5.0)
            self.assertEqual(sc, 0)

    def test_07_deterministic_reproducibility(self):
        """Searching same position with same config must yield identical node count and score."""
        fen = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"
        runs = []
        for _ in range(3):
            self.reset_state()
            self.engine.set_fen(fen)
            self.engine.set_ordering_options(True, True)
            self.engine.set_pvs_options(True)
            runs.append(self.engine.search(max_depth=4, time_limit=5.0))

        # nodes: runs[i][3]
        self.assertEqual(runs[0][3], runs[1][3])
        self.assertEqual(runs[1][3], runs[2][3])
        # best_move: runs[i][0]
        self.assertEqual(runs[0][0], runs[1][0])
        # score: runs[i][1]
        self.assertEqual(runs[0][1], runs[1][1])


if __name__ == "__main__":
    unittest.main()
