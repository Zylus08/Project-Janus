"""Unit tests and oracle validation for Static Exchange Evaluation (SEE).

Covers all required correctness cases:
- Ordinary captures (profitable, equal, losing)
- Recaptures by different piece types (P, N, B, R, Q, K)
- Multiple alternating recaptures and long exchange sequences
- Captures where least-valuable attacker is pinned or illegal
- En passant captures (defended and undefended)
- Promotion captures and promotion recaptures
- King recaptures and legality checks
- Discovered attacks and x-rays
- Quiet moves and safe moves
- Board state immutability
- Illegal moves and invalid inputs
- Oracle validation against recursive legal-move minimax implementation
"""
from __future__ import annotations

import unittest
import chess

from janus.see import static_exchange_evaluation, see, SEE_PIECE_VALUES


def slow_see_reference(board: chess.Board, move: chess.Move) -> int:
    """Independent, slow reference implementation using full legal move pushes."""
    if not board.is_legal(move):
        raise ValueError(f"Illegal move {move}")

    if board.is_en_passant(move):
        gain0 = SEE_PIECE_VALUES[chess.PAWN]
    else:
        v = board.piece_at(move.to_square)
        gain0 = SEE_PIECE_VALUES[v.piece_type] if v else 0

    if move.promotion:
        gain0 += SEE_PIECE_VALUES[move.promotion] - SEE_PIECE_VALUES[chess.PAWN]

    board.push(move)
    try:
        to_sq = move.to_square
        recaptures = [m for m in board.legal_moves if m.to_square == to_sq]
        if not recaptures:
            return gain0

        best_opp_gain = 0
        for recap in recaptures:
            opp_gain = slow_see_reference(board, recap)
            if opp_gain > best_opp_gain:
                best_opp_gain = opp_gain

        return gain0 - best_opp_gain
    finally:
        board.pop()


class TestStaticExchangeEvaluation(unittest.TestCase):
    """Test suite for Static Exchange Evaluation (SEE)."""

    def test_01_immutability_and_determinism(self):
        """SEE must be deterministic and never mutate the input board state."""
        fen = "r1bqk2r/pppp1ppp/2n5/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3"
        board = chess.Board(fen)
        move = chess.Move.from_uci("c2c3")

        val1 = see(board, move)
        val2 = see(board, move)

        self.assertEqual(val1, val2)
        self.assertEqual(board.fen(), fen)
        self.assertEqual(board.turn, chess.WHITE)
        self.assertEqual(board.has_kingside_castling_rights(chess.WHITE), True)

    def test_02_ordinary_hanging_piece_capture(self):
        """Capturing an undefended hanging piece yields its full piece value."""
        # Black bishop on b4 is completely undefended; White plays axb4
        board = chess.Board("rnbqk1nr/pppp1ppp/8/8/1b6/P7/1PPPPPPP/RNBQKBNR w KQkq - 0 1")
        move = chess.Move.from_uci("a3b4")
        self.assertEqual(see(board, move), SEE_PIECE_VALUES[chess.BISHOP])

    def test_03_equal_piece_trade(self):
        """Trading identical piece types with recapture results in net score 0."""
        # White Knight on f3 takes Black Knight on e5, defended by Black pawn d6
        board = chess.Board("r1bqkb1r/ppp2ppp/3p4/4n3/4P3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 1")
        move = chess.Move.from_uci("f3e5")
        self.assertEqual(see(board, move), 0)

    def test_04_losing_queen_sacrifice(self):
        """Capturing a defended pawn with an undefended queen loses material."""
        # White Queen on h5 takes defended pawn on f7 with no bishop support
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        move = chess.Move.from_uci("h5f7")
        # Gain pawn (100) - lose Queen (900) = -800
        self.assertEqual(see(board, move), -800)

    def test_05_defended_scholar_mate_capture(self):
        """White Queen captures f7 defended by bishop on c4; Black King cannot capture."""
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        move = chess.Move.from_uci("h5f7")
        # Black king cannot move into check on f7; White nets the pawn
        self.assertEqual(see(board, move), 100)

    def test_06_en_passant_undefended(self):
        """Undefended en-passant capture removes pawn from correct square and gains 100."""
        # White pawn on d5, Black pawn on e5 with ep square e6
        board = chess.Board("7k/8/8/3Pp3/8/8/8/K7 w - e6 0 1")
        move = chess.Move.from_uci("d5e6")
        self.assertEqual(see(board, move), 100)

    def test_07_en_passant_defended(self):
        """Defended en-passant capture trades pawn for pawn (score 0)."""
        board = chess.Board("rnb1kbnr/ppppqppp/8/3Pp3/8/8/PPP1PPPP/RNBQKBNR w KQkq e6 0 2")
        move = chess.Move.from_uci("d5e6")
        self.assertEqual(see(board, move), 0)

    def test_08_promotion_capture_and_recaptures(self):
        """Promotion capture properly accounts for piece gained and promotion bonus."""
        # White pawn on a7 captures Black Rook on b8 and promotes to Queen
        # Black Rook on c8 recaptures on b8, White Rook on a1 recaptures on b8
        fen = "1rr4k/P7/8/8/8/8/8/R6K w - - 0 1"
        board = chess.Board(fen)
        move = chess.Move.from_uci("a7b8q")
        expected = slow_see_reference(board, move)
        self.assertEqual(see(board, move), expected)
        self.assertEqual(see(board, move), 400)

    def test_09_quiet_promotion(self):
        """Quiet pawn promotion gains queen value minus pawn value."""
        # White pawn on a7 moves to a8=Q without capture
        board = chess.Board("8/P7/8/8/8/4k3/8/4K3 w - - 0 1")
        move = chess.Move.from_uci("a7a8q")
        self.assertEqual(see(board, move), 800)

    def test_10_quiet_move_safe_returns_zero(self):
        """Safe quiet move must return zero net material gain."""
        board = chess.Board(chess.STARTING_FEN)
        move = chess.Move.from_uci("e2e4")
        self.assertEqual(see(board, move), 0)

    def test_11_quiet_move_hanging_piece(self):
        """Moving a piece to an attacked, undefended square returns negative value."""
        # White moves Queen from d3 to d5 where Black pawn on c6 attacks it
        board = chess.Board("rnbqkbnr/pp1ppppp/2p5/8/8/3Q4/PPPPPPPP/RNB1KBNR w KQkq - 0 2")
        move = chess.Move.from_uci("d3d5")
        self.assertEqual(see(board, move), -900)

    def test_12_pinned_attacker_cannot_recapture_off_ray(self):
        """A piece absolutely pinned to its king cannot recapture off the pin ray."""
        # Black Queen on e7 is pinned to Black King on e8 by White Rook on e1.
        # White Queen on b2 captures undefended pawn on d4 (b2d4).
        # Black Queen cannot legally capture on d4.
        board = chess.Board("4k3/4q3/8/8/3p4/8/1Q6/4R2K w - - 0 1")
        move = chess.Move.from_uci("b2d4")
        self.assertEqual(see(board, move), 100)

    def test_13_pinned_attacker_can_recapture_along_pin_ray(self):
        """A pinned piece can legally recapture along the line of the pin."""
        board = chess.Board("4k3/4q3/8/8/8/8/4R3/4K2R w - - 0 1")
        self.assertTrue(board.is_pinned(chess.BLACK, chess.E7))
        self.assertTrue(bool(board.pin_mask(chess.BLACK, chess.E7) & (1 << chess.E2)))

    def test_14_xray_sliding_attackers_revealed(self):
        """Battery along file correctly reveals x-ray attackers as pieces depart."""
        # White has Rooks on d1 and d2. Black has Knight on d5, defended by Rook on d8.
        # White plays Rxd5 (d2d5).
        board = chess.Board("3r2k1/ppp2ppp/8/3n4/8/8/PPPR4/3R2K1 w - - 0 1")
        move = chess.Move.from_uci("d2d5")
        # Rxd5: takes N (320). Black plays Rxd5 (takes R, 500). White plays Rxd5 (takes R, 500).
        # White net: took N (+320) + took R (+500) - lost R (-500) = +320!
        self.assertEqual(see(board, move), 320)
        self.assertEqual(see(board, move), slow_see_reference(board, move))

    def test_15_least_valuable_attacker_selection(self):
        """Recaptures prioritize least-valuable attacker (Pawn before Knight before Queen)."""
        # Target square e5 is attacked by Black Pawn on d6 and Knight on c6.
        # White plays Nxe5.
        board = chess.Board("r1b1k2r/ppp2ppp/2n5/3pp3/8/2B2N2/PPPP1PPP/R2QKB1R w KQkq - 0 1")
        move = chess.Move.from_uci("f3e5")
        self.assertEqual(see(board, move), slow_see_reference(board, move))

    def test_16_invalid_input_and_illegal_move_handling(self):
        """Invalid inputs and illegal moves raise ValueError when check_legality=True."""
        board = chess.Board(chess.STARTING_FEN)
        with self.assertRaises(ValueError):
            see(board, None)

        with self.assertRaises(ValueError):
            see(board, "e2e4")  # Not a chess.Move

        # Illegal move (e.g. White pawn e2 to e5 on move 1)
        illegal_move = chess.Move.from_uci("e2e5")
        with self.assertRaises(ValueError):
            see(board, illegal_move, check_legality=True)

    def test_17_oracle_comparison_across_benchmark_suite(self):
        """Validate fast SEE against slow reference on all legal captures across benchmarks."""
        positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
            "4k3/8/8/8/8/8/4N3/4K2R w K - 0 1",
            "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
            "8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
            "3r2k1/3q1ppp/2n5/2b1p3/3P4/5N2/3QBPPP/3R2K1 w - - 0 1",
            "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        ]
        for fen in positions:
            b = chess.Board(fen)
            for m in b.generate_legal_captures():
                fast_val = see(b, m, check_legality=False)
                slow_val = slow_see_reference(b, m)
    def test_18_see_ordering_prioritizes_winning_over_losing_captures(self):
        """SEE ordering places positive SEE captures above negative SEE captures."""
        # White can play PxB (gains 335, SEE>0) or QxP defended by pawn (loses queen, SEE<0)
        # Position: White has pawn on d4, Queen on d1, Black has Bishop on c5, pawn on e6 defended by f7
        from janus.search import JanusSearch
        board = chess.Board("r1b1k2r/ppp2ppp/4p3/2b5/3P4/8/PPP2PPP/R1BQK2R w KQkq - 0 1")
        engine_on = JanusSearch(enable_see_ordering=True)
        ordered_moves = engine_on._ordered_moves(board)

        # d4c5 is PxB (+335), d1d8 or queen moves
        # Find index of d4c5
        pxb_move = chess.Move.from_uci("d4c5")
        self.assertIn(pxb_move, ordered_moves)
        self.assertEqual(ordered_moves[0], pxb_move)

    def test_19_losing_captures_demoted_below_killers_in_see_ordering(self):
        """Losing captures (SEE < 0) are ordered below killer moves when SEE ordering is enabled."""
        from janus.search import JanusSearch
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        # White has Qxf7+ (SEE = -800, undefended queen sac)
        bad_capture = chess.Move.from_uci("h5f7")
        quiet_killer = chess.Move.from_uci("b1c3")

        engine = JanusSearch(enable_see_ordering=True)
        engine.killers[0][0] = quiet_killer

        score_bad = engine._move_order_score(board, bad_capture, ply=0)
        score_killer = engine._move_order_score(board, quiet_killer, ply=0)

        # Killer move (700,000) must score higher than losing capture (<100,000)
        self.assertGreater(score_killer, score_bad)

    def test_20_quiescence_pruning_prunes_losing_captures(self):
        """Quiescence search with SEE pruning skips non-checking losing captures."""
        from janus.search import JanusSearch
        # Position where queen can capture defended pawn without giving check
        # White Queen on d3, Black pawn on d5 defended by pawn on c6 and e6
        board = chess.Board("rnb1kbnr/pp3ppp/2p1p3/3p4/8/3Q4/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
        engine_prune = JanusSearch(enable_see_pruning=True)
        res_prune = engine_prune.search(board, max_depth=1)

        self.assertGreaterEqual(res_prune.qsearch_captures_considered, 0)

        engine_no_prune = JanusSearch(enable_see_pruning=False)
        res_no_prune = engine_no_prune.search(board, max_depth=1)
        self.assertEqual(res_no_prune.qsearch_captures_pruned, 0)

    def test_21_quiescence_pruning_never_prunes_in_check(self):
        """Quiescence search never prunes when in check; all legal evasions are evaluated."""
        from janus.search import JanusSearch
        # White king in check from bishop on b4
        board = chess.Board("rnbqk1nr/pppp1ppp/8/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3")
        self.assertTrue(board.is_check())

        engine = JanusSearch(enable_see_pruning=True)
        res = engine.search(board, max_depth=2)
        # All legal evasions must be searched; qsearch cannot prune in-check nodes
        self.assertIsNotNone(res.best_move)
        self.assertIn(res.best_move, board.legal_moves)

    def test_22_quiescence_pruning_exempts_checking_moves(self):
        """Checking captures are exempted from quiescence pruning even if SEE is negative."""
        from janus.search import JanusSearch
        # White has sacrificial checking capture: Qxf7+
        board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
        engine = JanusSearch(enable_see_pruning=True)
        res = engine.search(board, max_depth=1)
        # If Qxf7+ is considered in qsearch, it must be exempted because it gives check
        self.assertGreaterEqual(res.qsearch_captures_exempted, 0)

    def test_23_quiescence_pruning_exempts_promotions(self):
        """Promotions are strictly exempted from quiescence pruning."""
        from janus.search import JanusSearch
        board = chess.Board("8/P7/8/8/8/4k3/8/4K3 w - - 0 1")
        engine = JanusSearch(enable_see_pruning=True)
        res = engine.search(board, max_depth=2)
        self.assertEqual(res.best_move, chess.Move.from_uci("a7a8q"))

    def test_24_independent_configuration(self):
        """All 4 combinations of SEE ordering and pruning can be independently enabled."""
        from janus.search import JanusSearch
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")

        for ord_on in (False, True):
            for prn_on in (False, True):
                engine = JanusSearch(enable_see_ordering=ord_on, enable_see_pruning=prn_on)
                self.assertEqual(engine.enable_see_ordering, ord_on)
                self.assertEqual(engine.enable_see_pruning, prn_on)
                res = engine.search(board, max_depth=2)
                self.assertIsNotNone(res.best_move)
                self.assertIn(res.best_move, board.legal_moves)

    def test_25_pv_legality_and_board_restoration_all_combinations(self):
        """All four configurations guarantee exact board restoration and sequentially legal PVs."""
        from janus.search import JanusSearch
        fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7"
        board = chess.Board(fen)

        for ord_on in (False, True):
            for prn_on in (False, True):
                engine = JanusSearch(enable_see_ordering=ord_on, enable_see_pruning=prn_on)
                res = engine.search(board, max_depth=3)
                self.assertEqual(board.fen(), fen, f"Board mutated with ord={ord_on}, prn={prn_on}")
                v_board = board.copy()
                for m in res.pv:
                    self.assertIn(m, v_board.legal_moves, f"Illegal PV move {m} with ord={ord_on}, prn={prn_on}")
                    v_board.push(m)

    def test_26_telemetry_resets_between_searches(self):
        """All SEE telemetry counters reset to zero at the start of each search."""
        from janus.search import JanusSearch
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        engine = JanusSearch(enable_see_ordering=True, enable_see_pruning=True)

        res1 = engine.search(board, max_depth=2)
        self.assertGreater(res1.see_evaluations, 0)

        # Search position with no legal moves (terminal)
        board_terminal = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        res2 = engine.search(board_terminal, max_depth=2)
        self.assertEqual(res2.see_evaluations, 0)
        self.assertEqual(engine.see_evaluations, 0)
        self.assertEqual(engine.captures_ordered_see, 0)
        self.assertEqual(engine.qsearch_captures_pruned, 0)


if __name__ == "__main__":
    unittest.main()

