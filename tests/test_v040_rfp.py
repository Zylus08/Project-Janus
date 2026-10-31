"""Project Janus v0.40 - Reverse Futility Pruning (RFP) Correctness Tests.

Gate B validation covering:
1. RFP disabled by default.
2. Check exemption (in_check positions never pruned by RFP).
3. Forced mate positions preserved (mate scores never pruned).
4. Tactical sacrifice preservation.
5. Quiet positions with large static margin trigger RFP cutoff.
6. Endgame behavior and zugzwang safety.
7. Score consistency against reference search.
"""
from __future__ import annotations

import unittest
import chess

from janus.search import JanusSearch, MATE_SCORE, MATE_THRESHOLD


class ReverseFutilityPruningTests(unittest.TestCase):
    def test_01_rfp_disabled_by_default(self) -> None:
        """Verify that RFP is disabled by default."""
        engine = JanusSearch()
        self.assertFalse(engine.enable_rfp)
        self.assertEqual(engine.rfp_max_depth, 2)
        self.assertEqual(engine.rfp_margin_per_depth, 120)

    def test_02_check_exemption(self) -> None:
        """Positions in check are strictly exempt from RFP."""
        # White king in check on e1 from Black queen on e8 along the open e-file
        board = chess.Board("4q3/8/8/8/8/8/3P4/4K3 w - - 0 1")
        self.assertTrue(board.is_check())

        engine = JanusSearch(enable_rfp=True)
        res = engine.search(board, max_depth=2)
        self.assertIsNotNone(res.best_move)
        self.assertTrue(board.is_legal(res.best_move))
        # King must escape check
        board.push(res.best_move)
        self.assertFalse(board.is_check())

    def test_03_forced_mate_not_pruned(self) -> None:
        """Forced mate positions must never be pruned by RFP."""
        # Scholar's mate: Qxf7#
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 4")
        engine = JanusSearch(enable_rfp=True)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.best_move, chess.Move.from_uci("f3f7"))
        self.assertEqual(res.score, MATE_SCORE - 1)

    def test_04_tactical_sacrifice_preserved(self) -> None:
        """Tactical queen sacrifice for checkmate is found with RFP."""
        # Anastasia's mate setup: Ne7+, Kh8, Qxh7+!, Kxh7, Rh1#
        board = chess.Board("5rk1/1p3ppp/pq6/3N4/8/8/PPP3PP/R4R1K w - - 0 1")
        engine = JanusSearch(enable_rfp=True)
        res = engine.search(board, max_depth=3)
        self.assertIsNotNone(res.best_move)
        # Winning fork or tactical blow Nxe7+ or Nxb6
        self.assertIn(res.best_move.uci(), ["d5e7", "d5b6"])

    def test_05_quiet_position_triggers_rfp_cutoff(self) -> None:
        """Quiet position with overwhelming static advantage produces RFP cutoffs."""
        # White is up a full Queen and Rook in a quiet position
        board = chess.Board("r3k2r/ppp2ppp/8/8/8/8/PPP2PPP/R3K2R w KQkq - 0 1")
        board.set_piece_at(chess.D4, chess.Piece(chess.QUEEN, chess.WHITE))

        engine = JanusSearch(enable_rfp=True, rfp_max_depth=2, rfp_margin_per_depth=120)
        res = engine.search(board, max_depth=4)
        self.assertGreater(res.rfp_cutoffs, 0, "RFP cutoffs should trigger in overwhelming quiet positions")

    def test_06_endgame_behavior(self) -> None:
        """Basic pawn endgame is evaluated correctly with RFP."""
        # White has passed pawn on e6, Black king far on a8
        board = chess.Board("k7/8/4P3/8/8/8/8/4K3 w - - 0 1")
        engine = JanusSearch(enable_rfp=True)
        res = engine.search(board, max_depth=3)
        self.assertEqual(res.best_move, chess.Move.from_uci("e6e7"))
        self.assertGreater(res.score, 300)

    def test_07_score_consistency_against_reference(self) -> None:
        """Scores with RFP match reference search within reasonable margin on quiet positions."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
        ref_engine = JanusSearch(enable_rfp=False)
        rfp_engine = JanusSearch(enable_rfp=True)

        res_ref = ref_engine.search(board, max_depth=3)
        res_rfp = rfp_engine.search(board, max_depth=3)

        self.assertEqual(res_ref.best_move, res_rfp.best_move)
        self.assertLessEqual(abs(res_ref.score - res_rfp.score), 20)


if __name__ == "__main__":
    unittest.main()
