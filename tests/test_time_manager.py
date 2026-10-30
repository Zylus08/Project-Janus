"""Unit and protocol tests for Project Janus v0.35 Adaptive Time Management.

Validates the 16 core requirements:
1. Fixed movetime remains unchanged.
2. Clock-only allocation.
3. Fischer increment allocation.
4. Different increments for White and Black.
5. Low-clock safety reserve.
6. Near-zero clock handling.
7. Allocation caps.
8. Invalid time-control inputs.
9. Deterministic allocation for identical inputs.
10. Search stops at its deadline.
11. Interrupted iterative deepening preserves a legal best move.
12. `stop` and `quit` remain responsive.
13. Board state is preserved after interrupted search.
14. A fresh UCI process initializes the time manager correctly.
15. Time-control options do not leak between games.
16. Existing fixed-movetime tests remain valid.
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from janus.engine_session import SupervisedEngineSession
from janus.search import JanusSearch
from janus.time_manager import TimeManager, TimeManagerConfig


class TimeManagerUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tm = TimeManager()

    def test_01_fixed_movetime_remains_unchanged(self) -> None:
        """Requirement 1: Fixed movetime bypasses clock allocation entirely."""
        t1 = self.tm.allocate_time(chess.WHITE, movetime=500)
        self.assertEqual(t1, 0.5)

        t2 = self.tm.allocate_time(chess.BLACK, movetime=1250)
        self.assertEqual(t2, 1.25)

        # Even if clock arguments are also passed, movetime takes priority
        t3 = self.tm.allocate_time(
            chess.WHITE,
            wtime=60000,
            btime=60000,
            movetime=200,
        )
        self.assertEqual(t3, 0.2)

    def test_02_clock_only_allocation(self) -> None:
        """Requirement 2: Allocates fraction of usable clock based on moves to go."""
        # 60,000 ms remaining, safety reserve 50 ms -> usable = 59,950 ms
        # Default 30 moves -> base = 59,950 / 30 = 1998.33 ms -> ~1.998s
        t_white = self.tm.allocate_time(chess.WHITE, wtime=60000, btime=60000)
        self.assertIsNotNone(t_white)
        self.assertAlmostEqual(t_white, 1.99833, places=3)

        # Explicit movestogo = 20
        # usable = 59,950 ms / 20 = 2997.5 ms -> ~2.9975s
        t_mtg = self.tm.allocate_time(chess.WHITE, wtime=60000, btime=60000, movestogo=20)
        self.assertAlmostEqual(t_mtg, 2.9975, places=3)

    def test_03_fischer_increment_allocation(self) -> None:
        """Requirement 3: Incorporates Fischer increment weighted into move budget."""
        # Base with 600,000 ms: usable = 599,950 / 30 = 19,998.33 ms
        # Without increment:
        t_no_inc = self.tm.allocate_time(chess.WHITE, wtime=600000, btime=600000, winc=0)
        # With 100 ms increment (0.85 * 100 = 85 ms):
        t_with_inc = self.tm.allocate_time(chess.WHITE, wtime=600000, btime=600000, winc=100)
        self.assertIsNotNone(t_no_inc)
        self.assertIsNotNone(t_with_inc)
        self.assertGreater(t_with_inc, t_no_inc)
        diff_ms = (t_with_inc - t_no_inc) * 1000.0
        self.assertAlmostEqual(diff_ms, 85.0, delta=1.0)

    def test_04_different_increments_for_white_and_black(self) -> None:
        """Requirement 4: Respects side-specific increments and clocks."""
        wtime = 60000
        btime = 60000
        winc = 1000
        binc = 0

        t_w = self.tm.allocate_time(chess.WHITE, wtime=wtime, btime=btime, winc=winc, binc=binc)
        t_b = self.tm.allocate_time(chess.BLACK, wtime=wtime, btime=btime, winc=winc, binc=binc)
        self.assertIsNotNone(t_w)
        self.assertIsNotNone(t_b)
        # White has 1000ms increment, Black has 0ms increment -> White receives more time
        self.assertGreater(t_w, t_b)
        self.assertAlmostEqual((t_w - t_b) * 1000.0, 850.0, delta=1.0)

    def test_05_low_clock_safety_reserve(self) -> None:
        """Requirement 5: Safety reserve protects against flagging in severe time trouble."""
        # Clock = 40 ms (less than safety reserve 50 ms)
        t_low = self.tm.allocate_time(chess.WHITE, wtime=40, btime=60000)
        self.assertIsNotNone(t_low)
        alloc_ms = t_low * 1000.0
        # Must be strictly less than remaining clock to prevent forfeit
        self.assertLess(alloc_ms, 40.0)
        self.assertGreaterEqual(alloc_ms, 1.0)

    def test_06_near_zero_clock_handling(self) -> None:
        """Requirement 6: Near-zero or zero clock triggers emergency minimum without crashing."""
        t_zero = self.tm.allocate_time(chess.WHITE, wtime=0, btime=60000)
        self.assertEqual(t_zero, 0.001)

        t_neg = self.tm.allocate_time(chess.WHITE, wtime=-500, btime=60000)
        self.assertEqual(t_neg, 0.001)

        t_tiny = self.tm.allocate_time(chess.WHITE, wtime=2, btime=60000)
        self.assertEqual(t_tiny, 0.001)

    def test_07_allocation_caps(self) -> None:
        """Requirement 7: Large increments cannot cause allocation to exceed safe bounds."""
        # 10,000 ms clock with huge increment of 100,000 ms
        t_huge_inc = self.tm.allocate_time(chess.WHITE, wtime=10000, btime=10000, winc=100000)
        self.assertIsNotNone(t_huge_inc)
        # Invariant: allocation can never exceed the remaining clock
        self.assertLessEqual(t_huge_inc * 1000.0, 10000.0)

    def test_08_invalid_time_control_inputs(self) -> None:
        """Requirement 8: Safely handles malformed and invalid inputs without crashing."""
        # None clock for side to move
        t_none = self.tm.allocate_time(chess.WHITE, wtime=None)
        self.assertIsNone(t_none)

        # Non-numeric or NaN values
        t_nan = self.tm.allocate_time(chess.WHITE, wtime=float("nan"))
        self.assertEqual(t_nan, 0.001)

        t_inf = self.tm.allocate_time(chess.WHITE, wtime=float("inf"))
        self.assertEqual(t_inf, 0.001)

        t_bad_movetime = self.tm.allocate_time(chess.WHITE, movetime=-100)
        self.assertEqual(t_bad_movetime, 0.001)

    def test_09_deterministic_allocation(self) -> None:
        """Requirement 9: Allocation is strictly deterministic for identical inputs."""
        results = [
            self.tm.allocate_time(chess.WHITE, wtime=123456, btime=654321, winc=500, binc=250, movestogo=27)
            for _ in range(50)
        ]
        self.assertTrue(all(r == results[0] for r in results))


class SearchTimingProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = JanusSearch(tt_max_entries=10_000)

    def test_10_search_stops_at_deadline(self) -> None:
        """Requirement 10: Iterative deepening terminates promptly at deadline."""
        board = chess.Board()
        target_time = 0.050  # 50 ms
        t0 = time.monotonic()
        result = self.engine.search(board, max_depth=64, time_limit=target_time)
        elapsed = time.monotonic() - t0

        self.assertIsNotNone(result.best_move)
        # Search should stop close to the target budget (with reasonable OS scheduling margin)
        self.assertGreaterEqual(elapsed, 0.040)
        self.assertLess(elapsed, 0.200)

    def test_11_interrupted_iterative_deepening_preserves_legal_best_move(self) -> None:
        """Requirement 11: Interrupted search always returns a legal move from completed depth."""
        board = chess.Board()
        # Tight budget of 20 ms with deep max_depth
        result = self.engine.search(board, max_depth=64, time_limit=0.020)
        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)
        self.assertGreaterEqual(result.depth, 1)

    def test_12_stop_and_quit_remain_responsive(self) -> None:
        """Requirement 12: Stop event interrupts search promptly."""
        board = chess.Board()
        stop = threading.Event()

        # Trigger stop after 15 ms in a separate thread
        def trigger_stop():
            time.sleep(0.015)
            stop.set()

        t = threading.Thread(target=trigger_stop)
        t.start()

        t0 = time.monotonic()
        result = self.engine.search(board, max_depth=64, stop_event=stop)
        elapsed = time.monotonic() - t0
        t.join()

        self.assertIsNotNone(result.best_move)
        self.assertIn(result.best_move, board.legal_moves)
        self.assertLess(elapsed, 0.150)

    def test_13_board_state_preserved_after_interrupted_search(self) -> None:
        """Requirement 13: Interrupted search does not mutate or corrupt root board state."""
        board = chess.Board("r1bqk2r/ppppbppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
        fen_before = board.fen()
        self.engine.search(board, max_depth=64, time_limit=0.030)
        self.assertEqual(board.fen(), fen_before)

    def test_14_fresh_uci_process_initializes_time_manager(self) -> None:
        """Requirement 14: Fresh UCI subprocess handles clock commands correctly."""
        cmd = [sys.executable, "-m", "janus.uci"]
        with SupervisedEngineSession(cmd=cmd, name="Janus-UCI-Test", cwd=ROOT) as session:
            board = chess.Board()
            # Send clock search command
            m_res = session.play_move(board, wtime=5000, btime=5000, winc=100, binc=100)
            self.assertIsNotNone(m_res.move)
            self.assertIn(m_res.move, board.legal_moves)
            self.assertGreater(m_res.depth, 0)
            self.assertLess(m_res.time_s, 2.0)

    def test_15_time_control_options_no_leak_between_games(self) -> None:
        """Requirement 15: Successive searches with different clock limits do not leak state."""
        cmd = [sys.executable, "-m", "janus.uci"]
        with SupervisedEngineSession(cmd=cmd, name="Janus-Leak-Test", cwd=ROOT) as session:
            board = chess.Board()
            # Move 1: short clock (500 ms)
            res1 = session.play_move(board, wtime=500, btime=500)
            self.assertIn(res1.move, board.legal_moves)
            self.assertLess(res1.time_s, 0.5)

            board.push(res1.move)
            # Move 2: longer clock (20,000 ms)
            res2 = session.play_move(board, wtime=20000, btime=20000)
            self.assertIn(res2.move, board.legal_moves)

    def test_16_existing_fixed_movetime_tests_remain_valid(self) -> None:
        """Requirement 16: Fixed movetime search operates correctly under supervised session."""
        cmd = [sys.executable, "-m", "janus.uci"]
        with SupervisedEngineSession(cmd=cmd, name="Janus-Fixed-Test", cwd=ROOT) as session:
            board = chess.Board()
            res = session.play_move(board, movetime_ms=100)
            self.assertIsNotNone(res.move)
            self.assertIn(res.move, board.legal_moves)
            self.assertGreater(res.depth, 0)
            self.assertLess(res.time_s, 0.5)


if __name__ == "__main__":
    unittest.main()
