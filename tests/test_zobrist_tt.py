"""Targeted regression tests for Zobrist transposition table hashing in Project Janus."""
import unittest
import chess
import chess.polyglot

from janus.search import JanusSearch, TTEntry, MATE_SCORE, MATE_THRESHOLD, INF


class ZobristTTTests(unittest.TestCase):
    def setUp(self):
        self.engine = JanusSearch(tt_max_entries=10_000)

    def test_identical_positions_produce_identical_hashes(self):
        fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7"
        b1 = chess.Board(fen)
        b2 = chess.Board(fen)
        k1 = self.engine._key(b1)
        k2 = self.engine._key(b2)
        self.assertIsInstance(k1, int)
        self.assertIsInstance(k2, int)
        self.assertEqual(k1, k2)

    def test_side_to_move_changes_hash(self):
        fen_white = "4k3/8/8/8/8/8/4N3/4K2R w - - 0 1"
        fen_black = "4k3/8/8/8/8/8/4N3/4K2R b - - 0 1"
        b_white = chess.Board(fen_white)
        b_black = chess.Board(fen_black)
        self.assertNotEqual(self.engine._key(b_white), self.engine._key(b_black))

    def test_castling_rights_change_hash(self):
        fen_all = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        fen_white_k = "r3k2r/8/8/8/8/8/8/R3K2R w K - 0 1"
        fen_none = "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1"
        k_all = self.engine._key(chess.Board(fen_all))
        k_white_k = self.engine._key(chess.Board(fen_white_k))
        k_none = self.engine._key(chess.Board(fen_none))
        self.assertNotEqual(k_all, k_white_k)
        self.assertNotEqual(k_all, k_none)
        self.assertNotEqual(k_white_k, k_none)

    def test_relevant_en_passant_state_changes_hash(self):
        # Position where Black pawn on d4 can legally capture e3 en-passant
        b_legal_ep = chess.Board("rnbqkbnr/ppp1pppp/8/8/3pP3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        # Position where no Black pawn can capture e3 en-passant
        b_no_capture_ep = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        # Position with no en-passant square
        b_no_ep = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

        k_legal = self.engine._key(b_legal_ep)
        k_no_capture = self.engine._key(b_no_capture_ep)
        k_none = self.engine._key(b_no_ep)

        # Legal EP possibility must produce a distinct hash
        self.assertNotEqual(k_legal, k_none)
        # When no capture is possible, Polyglot correctly considers the position equivalent to no EP
        self.assertEqual(k_no_capture, k_none)

    def test_transposition_across_different_halfmove_clocks_and_fullmove(self):
        # Two boards with identical piece arrangement, turn, and castling rights,
        # but different halfmove clocks and fullmove numbers reached via transposition
        fen_clock0 = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 5"
        fen_clock4 = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 7"
        b1 = chess.Board(fen_clock0)
        b2 = chess.Board(fen_clock4)
        k1 = self.engine._key(b1)
        k2 = self.engine._key(b2)
        # Zobrist hash matches, enabling transposition reuse
        self.assertEqual(k1, k2)

        # Store in TT using b1, probe using b2
        self.engine.tt.clear()
        self.engine.tt[k1] = TTEntry(depth=3, score=150, flag="exact", best_move=chess.Move.from_uci("e1g1"))
        self.assertIn(k2, self.engine.tt)
        retrieved = self.engine.tt[k2]
        self.assertEqual(retrieved.score, 150)
        self.assertEqual(retrieved.best_move, chess.Move.from_uci("e1g1"))

    def test_tt_hit_and_miss_behavior(self):
        b1 = chess.Board()
        b2 = chess.Board()
        b2.push_san("e4")

        k1 = self.engine._key(b1)
        k2 = self.engine._key(b2)

        self.engine.tt.clear()
        self.engine.tt[k1] = TTEntry(depth=2, score=25, flag="exact", best_move=chess.Move.from_uci("e2e4"))

        # Hit on b1
        self.assertIn(k1, self.engine.tt)
        self.assertEqual(self.engine.tt.get(k1).best_move, chess.Move.from_uci("e2e4"))

        # Miss on b2
        self.assertNotIn(k2, self.engine.tt)
        self.assertIsNone(self.engine.tt.get(k2))

    def test_exact_bound_cutoff(self):
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        key = self.engine._key(board)
        move = chess.Move.from_uci("f1b5")
        self.engine.tt[key] = TTEntry(depth=3, score=45, flag="exact", best_move=move)

        score, pv = self.engine._negamax(board, depth=2, alpha=-INF, beta=INF, ply=1)
        self.assertEqual(score, 45)
        self.assertEqual(pv, [move])

    def test_lower_bound_beta_cutoff(self):
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        key = self.engine._key(board)
        move = chess.Move.from_uci("f1b5")
        # Lower bound score of 100 exceeds beta=50
        self.engine.tt[key] = TTEntry(depth=3, score=100, flag="lower", best_move=move)

        score, pv = self.engine._negamax(board, depth=2, alpha=0, beta=50, ply=1)
        self.assertEqual(score, 100)
        self.assertEqual(pv, [move])

    def test_upper_bound_alpha_cutoff(self):
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        key = self.engine._key(board)
        move = chess.Move.from_uci("f1b5")
        # Upper bound score of -50 is below alpha=0
        self.engine.tt[key] = TTEntry(depth=3, score=-50, flag="upper", best_move=move)

        score, pv = self.engine._negamax(board, depth=2, alpha=0, beta=50, ply=1)
        self.assertEqual(score, -50)
        self.assertEqual(pv, [move])

    def test_insufficient_depth_entry_does_not_cutoff(self):
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        key = self.engine._key(board)
        move = chess.Move.from_uci("f1b5")
        # Cached entry has depth=1, but search requests depth=3
        self.engine.tt[key] = TTEntry(depth=1, score=200, flag="exact", best_move=move)

        nodes_before = self.engine.nodes
        score, pv = self.engine._negamax(board, depth=3, alpha=-INF, beta=INF, ply=1)
        # Search must expand children rather than taking immediate TT cutoff
        self.assertGreater(self.engine.nodes - nodes_before, 1)

    def test_mate_score_normalization_in_tt(self):
        # At ply 2, engine detects mate in 1 (score = MATE_SCORE - 3)
        raw_score = MATE_SCORE - 3
        stored = self.engine._score_to_tt(raw_score, ply=2)
        # Stored score should be normalized to root perspective: raw_score + ply = MATE_SCORE - 1
        self.assertEqual(stored, MATE_SCORE - 1)

        # Probing at ply 4: score_from_tt should subtract ply 4, yielding MATE_SCORE - 5
        probed = self.engine._score_from_tt(stored, ply=4)
        self.assertEqual(probed, MATE_SCORE - 5)

        # Negative mate score normalization
        neg_raw = -MATE_SCORE + 3
        neg_stored = self.engine._score_to_tt(neg_raw, ply=2)
        self.assertEqual(neg_stored, -MATE_SCORE + 1)
        neg_probed = self.engine._score_from_tt(neg_stored, ply=4)
        self.assertEqual(neg_probed, -MATE_SCORE + 5)

    def test_seventyfive_move_guard_suppresses_nonzero_tt_cutoff(self):
        # Board at halfmove clock 148, search depth 3 (148 + 3 = 151 >= 150)
        # Position has a pawn to ensure insufficient material does not trigger
        board = chess.Board("8/8/4k3/8/8/4K3/4P3/8 w - - 148 100")
        key = self.engine._key(board)
        # TT contains a non-zero winning score from a low halfmove clock path
        self.engine.tt[key] = TTEntry(depth=3, score=500, flag="exact", best_move=chess.Move.from_uci("e3e4"))

        # In _negamax at ply=1, halfmove_clock + depth >= 150, so non-zero cutoff is suppressed
        # Search must expand moves rather than taking an immediate 1-node cutoff
        nodes_before = self.engine.nodes
        score, _ = self.engine._negamax(board, depth=3, alpha=-INF, beta=INF, ply=1)
        self.assertGreater(self.engine.nodes - nodes_before, 1)

    def test_seventyfive_move_guard_allows_zero_tt_cutoff(self):
        # Board at halfmove clock 148, search depth 3, TT contains score=0 (draw)
        board = chess.Board("8/8/4k3/8/8/4K3/4P3/8 w - - 148 100")
        key = self.engine._key(board)
        self.engine.tt[key] = TTEntry(depth=3, score=0, flag="exact", best_move=chess.Move.from_uci("e3e4"))

        nodes_before = self.engine.nodes
        score, pv = self.engine._negamax(board, depth=3, alpha=-INF, beta=INF, ply=1)
        self.assertEqual(score, 0)
        self.assertEqual(pv, [chess.Move.from_uci("e3e4")])
        # Took immediate cutoff: exactly 1 node visited
        self.assertEqual(self.engine.nodes - nodes_before, 1)

    def test_fivefold_repetition_overrides_tt(self):
        # Play a sequence that repeats moves 5 times
        board = chess.Board()
        moves = [
            chess.Move.from_uci("g1f3"), chess.Move.from_uci("g8f6"),
            chess.Move.from_uci("f3g1"), chess.Move.from_uci("f6g8"),
        ]
        for _ in range(4):
            for m in moves:
                board.push(m)

        # Populate TT with a winning score for startpos
        key = self.engine._key(board)
        self.engine.tt[key] = TTEntry(depth=3, score=800, flag="exact", best_move=chess.Move.from_uci("e2e4"))

        self.assertTrue(board.is_fivefold_repetition())
        # Search must recognize fivefold repetition draw immediately despite winning TT entry
        result = self.engine.search(board, max_depth=2)
        self.assertEqual(result.score, 0)

    def test_board_push_pop_state_restoration(self):
        fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7",
            "4k3/8/8/8/8/8/4N3/4K2R w K - 0 1",
            "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
            "8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
        ]
        for fen in fens:
            board = chess.Board(fen)
            expected_fen = board.fen()
            self.engine.search(board, max_depth=3)
            self.assertEqual(board.fen(), expected_fen)

    def test_no_illegal_move_returned_after_tt_probe(self):
        # Seed TT with an arbitrary move and verify engine always returns a legal move
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        result = self.engine.search(board, max_depth=3)
        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)
        for m in result.pv:
            self.assertIn(m, board.legal_moves)
            board.push(m)


if __name__ == "__main__":
    unittest.main()
