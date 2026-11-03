"""Unit and regression tests for Aspiration Windows in Project Janus."""
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest

import chess

from janus.search import JanusSearch, SearchResult, MATE_SCORE, MATE_THRESHOLD, INF
from janus.uci import main as uci_main

ROOT = Path(__file__).resolve().parents[1]


class MockAspirationSearch(JanusSearch):
    """Controlled test seam to inject exact negamax scores and verify aspiration window dynamics."""
    def __init__(self, scores_to_return=None, **kwargs):
        super().__init__(**kwargs)
        self.scores_to_return = list(scores_to_return or [])
        self.recorded_calls = []

    def _negamax(self, board, depth, alpha, beta, ply):
        self.recorded_calls.append((depth, alpha, beta, ply))
        if self.scores_to_return:
            score, pv = self.scores_to_return.pop(0)
            return score, pv
        return super()._negamax(board, depth, alpha, beta, ply)


class AspirationWindowsTests(unittest.TestCase):
    def setUp(self):
        self.board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def test_01_aspiration_vs_full_window_invariance(self):
        """Aspiration disabled vs enabled produces identical root scores and best moves."""
        positions_path = ROOT / "benchmarks" / "positions.json"
        positions = json.loads(positions_path.read_text(encoding="utf-8"))

        for p in positions:
            pos_board = chess.Board(p["fen"])
            for depth in (1, 2, 3, 4):
                s_asp = JanusSearch(enable_aspiration=True)
                s_full = JanusSearch(enable_aspiration=False)

                r_asp = s_asp.search(pos_board.copy(), max_depth=depth)
                r_full = s_full.search(pos_board.copy(), max_depth=depth)

                self.assertEqual(
                    r_asp.score, r_full.score,
                    f"Score mismatch on {p['id']} at depth {depth}: asp={r_asp.score} full={r_full.score}"
                )
                self.assertEqual(
                    r_asp.best_move, r_full.best_move,
                    f"Move mismatch on {p['id']} at depth {depth}: asp={r_asp.best_move} full={r_full.best_move}"
                )

    def test_02_principal_variations_are_sequentially_legal(self):
        """All returned PV moves must be legally playable in sequence."""
        positions_path = ROOT / "benchmarks" / "positions.json"
        positions = json.loads(positions_path.read_text(encoding="utf-8"))

        for p in positions:
            pos_board = chess.Board(p["fen"])
            searcher = JanusSearch(enable_aspiration=True)
            res = searcher.search(pos_board, max_depth=3)

            verify = pos_board.copy()
            for move in res.pv:
                self.assertIn(move, verify.legal_moves)
                verify.push(move)

    def test_03_board_state_exact_restoration(self):
        """Search must leave the input board completely unmodified."""
        fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7"
        board = chess.Board(fen)
        searcher = JanusSearch(enable_aspiration=True)
        searcher.search(board, max_depth=3)
        self.assertEqual(board.fen(), fen)

    def test_04_first_iteration_full_window(self):
        """Depth 1 must always be full-window [-INF, INF] and not count as an aspiration iteration."""
        searcher = JanusSearch(enable_aspiration=True)
        res = searcher.search(self.board, max_depth=1)
        self.assertEqual(res.depth, 1)
        self.assertEqual(res.aspiration_iterations, 0)
        self.assertEqual(res.aspiration_fail_lows, 0)
        self.assertEqual(res.aspiration_fail_highs, 0)
        self.assertEqual(res.aspiration_researches, 0)
        self.assertEqual(res.aspiration_fallbacks, 0)

    def test_05_fail_low_causes_widening_and_research(self):
        """Failing low widens the lower bound and executes a re-search."""
        m = list(self.board.legal_moves)[0]
        # Depth 1 returns 100.
        # Depth 2 initial window [65, 135].
        # First call returns 50 (fail-low).
        # Widened call returns 50 with alpha = 100 - 70 = 30.
        mock = MockAspirationSearch(
            scores_to_return=[
                (100, [m]),  # depth 1
                (50, [m]),   # depth 2 attempt 1 (fail-low)
                (50, [m]),   # depth 2 attempt 2 (inside [30, 135])
            ],
            enable_aspiration=True,
            aspiration_delta=35,
        )
        res = mock.search(self.board, max_depth=2)
        self.assertEqual(res.score, 50)
        self.assertEqual(res.aspiration_iterations, 1)
        self.assertEqual(res.aspiration_fail_lows, 1)
        self.assertEqual(res.aspiration_fail_highs, 0)
        self.assertEqual(res.aspiration_researches, 1)
        self.assertEqual(res.aspiration_fallbacks, 0)

        # Verify call windows
        # call 0: depth 1 [-INF, INF]
        # call 1: depth 2 [65, 135]
        # call 2: depth 2 [30, 135] (alpha widened by 2*delta)
        self.assertEqual(mock.recorded_calls[0][1:], (-INF, INF, 0))
        self.assertEqual(mock.recorded_calls[1][1:], (65, 135, 0))
        self.assertEqual(mock.recorded_calls[2][1:], (30, 135, 0))

    def test_06_fail_high_causes_widening_and_research(self):
        """Failing high widens the upper bound and executes a re-search."""
        m = list(self.board.legal_moves)[0]
        mock = MockAspirationSearch(
            scores_to_return=[
                (100, [m]),  # depth 1
                (150, [m]),  # depth 2 attempt 1 (fail-high: 150 >= 135)
                (140, [m]),  # depth 2 attempt 2 (inside [65, 170])
            ],
            enable_aspiration=True,
            aspiration_delta=35,
        )
        res = mock.search(self.board, max_depth=2)
        self.assertEqual(res.score, 140)
        self.assertEqual(res.aspiration_iterations, 1)
        self.assertEqual(res.aspiration_fail_lows, 0)
        self.assertEqual(res.aspiration_fail_highs, 1)
        self.assertEqual(res.aspiration_researches, 1)
        self.assertEqual(res.aspiration_fallbacks, 0)

        # call 1: depth 2 [65, 135]
        # call 2: depth 2 [65, 170] (beta widened by 2*delta)
        self.assertEqual(mock.recorded_calls[1][1:], (65, 135, 0))
        self.assertEqual(mock.recorded_calls[2][1:], (65, 170, 0))

    def test_07_multiple_failures_terminate_safely(self):
        """Alternating or repeated failures widen repeatedly and resolve safely."""
        m = list(self.board.legal_moves)[0]
        mock = MockAspirationSearch(
            scores_to_return=[
                (100, [m]),  # depth 1
                (50, [m]),   # depth 2 attempt 1 (fail-low: 50 <= 65) -> alpha becomes 30
                (180, [m]),  # depth 2 attempt 2 (fail-high: 180 >= 135) -> beta becomes 240
                (120, [m]),  # depth 2 attempt 3 (inside [30, 240])
            ],
            enable_aspiration=True,
            aspiration_delta=35,
        )
        res = mock.search(self.board, max_depth=2)
        self.assertEqual(res.score, 120)
        self.assertEqual(res.aspiration_iterations, 1)
        self.assertEqual(res.aspiration_fail_lows, 1)
        self.assertEqual(res.aspiration_fail_highs, 1)
        self.assertEqual(res.aspiration_researches, 2)
        self.assertEqual(res.aspiration_fallbacks, 0)

    def test_08_full_window_fallback_on_max_retries(self):
        """When retries reach max_aspiration_retries, full-window [-INF, INF] fallback triggers."""
        m = list(self.board.legal_moves)[0]
        mock = MockAspirationSearch(
            scores_to_return=[
                (100, [m]),   # depth 1
                (50, [m]),    # attempt 1 fail-low (retry 1)
                (20, [m]),    # attempt 2 fail-low (retry 2)
                (-50, [m]),   # attempt 3 fail-low (retry 3 -> triggers fallback)
                (-50, [m]),   # attempt 4 full-window fallback
            ],
            enable_aspiration=True,
            aspiration_delta=35,
            max_aspiration_retries=3,
        )
        res = mock.search(self.board, max_depth=2)
        self.assertEqual(res.score, -50)
        self.assertEqual(res.aspiration_iterations, 1)
        self.assertEqual(res.aspiration_fail_lows, 3)
        self.assertEqual(res.aspiration_researches, 3)
        self.assertEqual(res.aspiration_fallbacks, 1)
        # Attempt 4 must have been called with [-INF, INF]
        self.assertEqual(mock.recorded_calls[4][1:], (-INF, INF, 0))

    def test_09_mate_positions_handled_correctly(self):
        """Positions with mate scores bypass aspiration windows or handle them soundly."""
        # Mate in 1
        board_m1 = chess.Board("8/7k/5K2/6Q1/8/8/8/8 w - - 0 1")
        searcher = JanusSearch(enable_aspiration=True)
        res = searcher.search(board_m1, max_depth=3)
        self.assertEqual(res.score, 99999)
        self.assertEqual(res.best_move, chess.Move.from_uci("g5g7"))
        # Since depth 1 returned 99999 (>= MATE_THRESHOLD), depths 2 and 3 bypass aspiration window
        self.assertEqual(res.aspiration_iterations, 0)

    def test_10_stalemate_check_tactics_promotions(self):
        """Terminal, check evasion, and tactical positions are evaluated accurately."""
        # Stalemate
        st_board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        s = JanusSearch(enable_aspiration=True)
        r = s.search(st_board, max_depth=3)
        self.assertEqual(r.score, 0)
        self.assertIsNone(r.best_move)

        # Promotion tactic
        promo_board = chess.Board("7k/P7/8/8/8/8/8/K7 w - - 0 1")
        r_promo = s.search(promo_board, max_depth=3)
        self.assertEqual(r_promo.best_move, chess.Move.from_uci("a7a8q"))

    def test_11_pvs_enabled_and_disabled_modes(self):
        """Aspiration works properly with both PVS enabled and PVS disabled."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        s_pvs_asp = JanusSearch(enable_pvs=True, enable_aspiration=True)
        s_nopvs_asp = JanusSearch(enable_pvs=False, enable_aspiration=True)

        r1 = s_pvs_asp.search(board.copy(), max_depth=3)
        r2 = s_nopvs_asp.search(board.copy(), max_depth=3)

        self.assertEqual(r1.score, r2.score)
        self.assertEqual(r1.best_move, r2.best_move)

    def test_12_telemetry_counters_reset_consistently(self):
        """Telemetry counters must be cleanly reset at the start of each search."""
        searcher = JanusSearch(enable_aspiration=True)
        searcher.search(self.board, max_depth=3)
        self.assertGreater(searcher.nodes, 0)
        self.assertGreater(searcher.aspiration_iterations, 0)

        # Second search on depth 1 should have 0 aspiration iterations
        r2 = searcher.search(self.board, max_depth=1)
        self.assertEqual(r2.aspiration_iterations, 0)
        self.assertEqual(r2.aspiration_fail_lows, 0)
        self.assertEqual(r2.aspiration_fail_highs, 0)
        self.assertEqual(r2.aspiration_researches, 0)
        self.assertEqual(r2.aspiration_fallbacks, 0)

    def test_13_killer_history_and_tt_bound_semantics(self):
        """Transposition table entries maintain sound bound flags under aspiration searches."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_aspiration=True)
        searcher.search(board, max_depth=3)

        flags = set()
        for key, entry in searcher.tt.items():
            self.assertIn(entry.flag, ("exact", "lower", "upper"))
            flags.add(entry.flag)

        self.assertIn("exact", flags)
        self.assertIn("upper", flags)

    def test_14_uci_startup_search_and_shutdown(self):
        """UCI loop handles startpos search and emits valid bestmove and info tokens."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "janus.uci"],
            cwd=str(ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        proc.stdin.write("uci\nisready\nposition startpos\ngo depth 2\n")
        proc.stdin.flush()
        lines = []
        for line in proc.stdout:
            lines.append(line)
            if line.startswith("bestmove"):
                break
        proc.stdin.write("quit\n")
        proc.stdin.flush()
        proc.wait(timeout=5)
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
        stdout = "".join(lines)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("uciok", stdout)
        self.assertIn("readyok", stdout)
        self.assertIn("info depth 2", stdout)
        self.assertIn("bestmove", stdout)


if __name__ == "__main__":
    unittest.main()
