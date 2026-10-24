"""Unit tests for v0.33 candidate evaluation features (Pawn Structure, Rook Files, King Safety)."""
import unittest

import chess
from janus.evaluation import (
    evaluate_white,
    evaluate_side_to_move,
    evaluation_config,
    DOUBLED_PAWN_PENALTY,
    ISOLATED_PAWN_PENALTY,
    PASSED_PAWN_RANK_BONUS,
    ROOK_OPEN_FILE_BONUS,
    ROOK_SEMI_OPEN_FILE_BONUS,
    KING_SHIELD_BONUS,
    KING_OPEN_FILE_PENALTY,
)


class TestCandidateFeaturesV033(unittest.TestCase):
    """Test suite validating isolated evaluation features and their mathematical invariants."""

    def test_pawn_structure_passed_pawn_progression(self):
        """Passed pawn bonuses scale with rank and disappear when blocked by enemy pawns."""
        with evaluation_config(pawn_structure=True):
            # Rank 4 passed pawn on d4 supported by c3 (neither is isolated)
            b_rank4 = chess.Board("8/4k3/8/8/3P4/2P5/8/4K3 w - - 0 1")
            with evaluation_config(pawn_structure=False):
                base_rank4 = evaluate_white(b_rank4)
            # d4 is passed (rank 4, index 3 -> bonus 5 cp), c3 is passed (rank 3, index 2 -> bonus 0 cp)
            self.assertEqual(evaluate_white(b_rank4), base_rank4 + PASSED_PAWN_RANK_BONUS[3] + PASSED_PAWN_RANK_BONUS[2])

            # Rank 6 passed pawn on d6 supported by c5
            b_rank6 = chess.Board("8/4k3/3P4/2P5/8/8/8/4K3 w - - 0 1")
            with evaluation_config(pawn_structure=False):
                base_rank6 = evaluate_white(b_rank6)
            # d6 (rank 6, index 5 -> bonus 20 cp), c5 (rank 5, index 4 -> bonus 10 cp)
            self.assertEqual(
                evaluate_white(b_rank6),
                base_rank6 + PASSED_PAWN_RANK_BONUS[5] + PASSED_PAWN_RANK_BONUS[4],
            )

            # Blocked pawns: Black pawns on c6 and d7 block White c5 and d6
            b_blocked = chess.Board("8/3pk3/2pP4/2P5/8/8/8/4K3 w - - 0 1")
            with evaluation_config(pawn_structure=False):
                base_blocked = evaluate_white(b_blocked)
            # Neither side has passed pawns; no isolated pawns; no doubled pawns
            self.assertEqual(evaluate_white(b_blocked), base_blocked)

    def test_pawn_structure_doubled_and_isolated_pawns(self):
        """Doubled pawns and isolated pawns receive designated penalties."""
        with evaluation_config(pawn_structure=True):
            # Doubled pawns on c-file (c2, c3) with supporting d-pawn on d2
            b_doubled = chess.Board("4k3/8/8/8/8/2P5/2PP4/4K3 w - - 0 1")
            with evaluation_config(pawn_structure=False):
                base_doubled = evaluate_white(b_doubled)
            # 2 pawns on c-file: 1 extra pawn -> -10 cp
            # c2 has adj d2, c3 has adj d2, d2 has adj c2/c3 -> no isolated pawns
            self.assertEqual(evaluate_white(b_doubled), base_doubled - DOUBLED_PAWN_PENALTY)

            # Isolated pawn on d4 (no c or e pawns)
            b_isolated = chess.Board("4k3/8/8/8/3P4/8/8/4K3 w - - 0 1")
            with evaluation_config(pawn_structure=False):
                base_isolated = evaluate_white(b_isolated)
            # Passed pawn bonus +10 cp, isolated penalty -12 cp -> net -2 cp
            self.assertEqual(
                evaluate_white(b_isolated),
                base_isolated + PASSED_PAWN_RANK_BONUS[3] - ISOLATED_PAWN_PENALTY,
            )

    def test_rook_files_open_and_semi_open(self):
        """Rooks on open and semi-open files receive appropriate bonuses."""
        with evaluation_config(rook_files=True):
            # Rook on d1, no pawns on d-file -> open file
            b_open = chess.Board("4k3/8/8/8/8/8/8/3RK3 w - - 0 1")
            with evaluation_config(rook_files=False):
                base_open = evaluate_white(b_open)
            self.assertEqual(evaluate_white(b_open), base_open + ROOK_OPEN_FILE_BONUS)

            # Rook on d1, black pawn on d5 -> semi-open file
            b_semi = chess.Board("4k3/8/8/3p4/8/8/8/3RK3 w - - 0 1")
            with evaluation_config(rook_files=False):
                base_semi = evaluate_white(b_semi)
            self.assertEqual(evaluate_white(b_semi), base_semi + ROOK_SEMI_OPEN_FILE_BONUS)

            # Rook on d1, white pawn on d2 -> closed file
            b_closed = chess.Board("4k3/8/8/8/8/8/3P4/3RK3 w - - 0 1")
            with evaluation_config(rook_files=False):
                base_closed = evaluate_white(b_closed)
            self.assertEqual(evaluate_white(b_closed), base_closed)

    def test_king_safety_shield_and_open_files(self):
        """Castled kings behind intact shields are rewarded; missing shield pawns are penalized."""
        with evaluation_config(king_safety=True):
            # Safely castled king on g1 with intact f2, g2, h2 shield
            b_safe = chess.Board("r1bq1rk1/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 w - - 0 1")
            with evaluation_config(king_safety=False):
                base_safe = evaluate_white(b_safe)
            # White king on g1: 3 pawns (f2, g2, h2) -> +3 * 8 = +24 cp
            # Black king on g8: 3 pawns (f7, g7, h7) -> -3 * 8 = -24 cp
            # Net king safety = 0
            self.assertEqual(evaluate_white(b_safe), base_safe)

            # White king missing g2 pawn (open g-file)
            b_broken = chess.Board("r1bq1rk1/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1P1P/RNBQ1RK1 w - - 0 1")
            with evaluation_config(king_safety=False):
                base_broken = evaluate_white(b_broken)
            # White: 2 shield pawns (f2, h2) = +16 cp, open g-file = -12 cp -> net +4 cp
            # Black: 3 shield pawns = -24 cp
            # Difference from baseline: 4 - 24 = -20 cp
            self.assertEqual(evaluate_white(b_broken), base_broken - 20)

    def test_all_feature_combinations_preserve_color_symmetry(self):
        """Every combination of feature flags (2^3 = 8 configurations) strictly preserves color mirror symmetry."""
        fens = [
            chess.STARTING_FEN,
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
            "4k3/8/8/3P4/8/8/8/4K3 w - - 0 1",
            "r4rk1/pp1q1ppp/2n1pn2/8/3P4/2NB1N2/PP3PPP/R2Q1RK1 w - - 0 12",
            "8/5pk1/4p1p1/4P1P1/5PK1/8/8/8 w - - 0 40",
        ]
        for pawn in (False, True):
            for rook in (False, True):
                for king in (False, True):
                    with evaluation_config(pawn_structure=pawn, rook_files=rook, king_safety=king):
                        for fen in fens:
                            b = chess.Board(fen)
                            mir = b.mirror()
                            score_w = evaluate_white(b)
                            score_mir = evaluate_white(mir)
                            self.assertEqual(
                                score_w,
                                -score_mir,
                                f"Symmetry violated with pawn={pawn}, rook={rook}, king={king} on {fen}: {score_w} vs {score_mir}",
                            )
                            score_stm = evaluate_side_to_move(b)
                            score_stm_mir = evaluate_side_to_move(mir)
                            self.assertEqual(
                                score_stm,
                                score_stm_mir,
                                f"STM symmetry violated with pawn={pawn}, rook={rook}, king={king} on {fen}",
                            )


if __name__ == "__main__":
    unittest.main()
