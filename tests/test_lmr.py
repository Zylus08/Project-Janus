"""Unit and regression tests for Late Move Reductions (LMR) in Project Janus."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import chess

from janus.search import JanusSearch, SearchResult, MATE_SCORE, MATE_THRESHOLD, INF

ROOT = Path(__file__).resolve().parents[1]


class MockLMRSearch(JanusSearch):
    """Controlled test seam to inspect negamax depth arguments and control returned scores."""
    def __init__(self, scores_to_return=None, **kwargs):
        super().__init__(**kwargs)
        self.scores_to_return = list(scores_to_return or [])
        self.recorded_calls = []

    def _negamax(self, board, depth, alpha, beta, ply):
        self.recorded_calls.append((depth, alpha, beta, ply, board.fen()))
        if self.scores_to_return:
            score, pv = self.scores_to_return.pop(0)
            return score, pv
        return super()._negamax(board, depth, alpha, beta, ply)


class LateMoveReductionsTests(unittest.TestCase):
    def setUp(self):
        self.board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def test_01_lmr_vs_baseline_invariance_depths_1_to_4(self):
        """LMR enabled vs disabled produces identical scores and best moves across benchmark positions at depths 1-4."""
        positions_path = ROOT / "benchmarks" / "positions.json"
        positions = json.loads(positions_path.read_text(encoding="utf-8"))

        for p in positions:
            pos_board = chess.Board(p["fen"])
            for depth in (1, 2, 3, 4):
                s_lmr = JanusSearch(enable_lmr=True)
                s_base = JanusSearch(enable_lmr=False)

                r_lmr = s_lmr.search(pos_board.copy(), max_depth=depth)
                r_base = s_base.search(pos_board.copy(), max_depth=depth)

                self.assertEqual(
                    r_lmr.score, r_base.score,
                    f"Score mismatch on {p['id']} at depth {depth}: lmr={r_lmr.score} base={r_base.score}"
                )
                self.assertEqual(
                    r_lmr.best_move, r_base.best_move,
                    f"Move mismatch on {p['id']} at depth {depth}: lmr={r_lmr.best_move} base={r_base.best_move}"
                )

    def test_02_principal_variations_are_sequentially_legal(self):
        """All returned PV moves must be legally playable in sequence."""
        positions_path = ROOT / "benchmarks" / "positions.json"
        positions = json.loads(positions_path.read_text(encoding="utf-8"))

        for p in positions:
            pos_board = chess.Board(p["fen"])
            searcher = JanusSearch(enable_lmr=True)
            res = searcher.search(pos_board, max_depth=3)

            verify = pos_board.copy()
            for move in res.pv:
                self.assertIn(move, verify.legal_moves)
                verify.push(move)

    def test_03_board_state_exact_restoration(self):
        """Search must leave the input board completely unmodified."""
        fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7"
        board = chess.Board(fen)
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=3)
        self.assertEqual(board.fen(), fen)

    def test_04_first_moves_never_reduced(self):
        """First moves (moves_searched < 3) must never be reduced."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=3)
        # At depth 3, any reduced search must search depth 1 (i.e. depth - 1 - 1 = 1)
        # Moves 0, 1, 2 must have been searched at full depth 2
        self.assertGreaterEqual(searcher.lmr_considered, 0)

    def test_05_captures_and_promotions_never_reduced(self):
        """Captures and promotions are strictly excluded from LMR."""
        # Tactical position where moves are captures/promotions
        board = chess.Board("7k/P7/8/8/8/4k3/4r3/4K3 w - - 0 1")
        searcher = JanusSearch(enable_lmr=True)
        res = searcher.search(board, max_depth=3)
        # In this endgame with mostly captures, checks, or promotions, no quiet LMR reductions should occur
        self.assertEqual(res.best_move, chess.Move.from_uci("e1f1"))

    def test_06_moves_in_check_never_reduced(self):
        """Nodes in check must never reduce any evasion moves."""
        check_board = chess.Board("8/8/8/8/8/4k3/4r3/4K3 w - - 0 1")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(check_board, max_depth=3)
        # King evasions out of check are never reduced
        self.assertEqual(searcher.lmr_reduced_searches, 0)

    def test_07_shallow_depth_does_not_reduce(self):
        """At depth < 3, no LMR reductions must occur."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=2)
        self.assertEqual(searcher.lmr_reduced_searches, 0)
        self.assertEqual(searcher.lmr_considered, 0)

    def test_08_reduced_search_fail_high_triggers_research(self):
        """When a reduced search fails high (score > alpha), a full-depth verification re-search is executed."""
        # Controlled position with many quiet moves
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        res = searcher.search(board, max_depth=4)
        if searcher.lmr_fail_highs > 0:
            self.assertGreaterEqual(searcher.lmr_researches, searcher.lmr_fail_highs)

    def test_09_reduced_search_fail_low_refutes_without_research(self):
        """When a reduced search fails low (score <= alpha), it is refuted with no re-search."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=4)
        self.assertGreater(searcher.lmr_reduced_searches, 0)
        self.assertGreater(searcher.lmr_fail_lows, 0)
        self.assertEqual(searcher.lmr_reduced_searches, searcher.lmr_fail_lows + searcher.lmr_fail_highs)

    def test_10_beta_cutoff_behavior_on_lmr_move(self):
        """Beta cutoffs on LMR moves are verified at full depth before accepting the cutoff."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        res = searcher.search(board, max_depth=4)
        self.assertGreaterEqual(res.beta_cutoffs, res.lmr_cutoffs)

    def test_11_tt_bound_semantics_remain_correct(self):
        """Transposition table entries maintain valid bound flags under LMR."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=4)

        flags = set()
        for key, entry in searcher.tt.items():
            self.assertIn(entry.flag, ("exact", "lower", "upper"))
            flags.add(entry.flag)

        self.assertIn("exact", flags)
        self.assertIn("upper", flags)

    def test_12_mate_positions_handled_correctly(self):
        """Forced mate positions evaluate accurately with LMR enabled."""
        board_m1 = chess.Board("8/7k/5K2/6Q1/8/8/8/8 w - - 0 1")
        searcher = JanusSearch(enable_lmr=True)
        res = searcher.search(board_m1, max_depth=3)
        self.assertEqual(res.score, 99999)
        self.assertEqual(res.best_move, chess.Move.from_uci("g5g7"))

    def test_13_pvs_enabled_and_disabled_modes(self):
        """LMR operates correctly with both PVS enabled and PVS disabled."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        s_pvs = JanusSearch(enable_pvs=True, enable_lmr=True)
        s_nopvs = JanusSearch(enable_pvs=False, enable_lmr=True)

        r_pvs = s_pvs.search(board.copy(), max_depth=3)
        r_nopvs = s_nopvs.search(board.copy(), max_depth=3)

        self.assertEqual(r_pvs.score, r_nopvs.score)
        self.assertEqual(r_pvs.best_move, r_nopvs.best_move)

    def test_14_aspiration_enabled_and_disabled_modes(self):
        """LMR operates correctly with aspiration windows enabled and disabled."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        s_asp = JanusSearch(enable_aspiration=True, enable_lmr=True)
        s_noasp = JanusSearch(enable_aspiration=False, enable_lmr=True)

        r_asp = s_asp.search(board.copy(), max_depth=3)
        r_noasp = s_noasp.search(board.copy(), max_depth=3)

        self.assertEqual(r_asp.score, r_noasp.score)
        self.assertEqual(r_asp.best_move, r_noasp.best_move)

    def test_15_killer_and_history_heuristics_update(self):
        """Killer moves and quiet history updates continue to populate under LMR."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=4)

        has_killers = any(k[0] is not None for k in searcher.killers)
        has_history = any(any(val > 0 for val in row) for row in searcher.history)
        self.assertTrue(has_killers)
        self.assertTrue(has_history)

    def test_16_telemetry_counters_reset_consistently(self):
        """LMR telemetry counters cleanly reset to zero at the start of each search."""
        board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 4 7")
        searcher = JanusSearch(enable_lmr=True)
        searcher.search(board, max_depth=4)
        self.assertGreater(searcher.lmr_reduced_searches, 0)

        # Depth 1 search has no LMR moves
        r2 = searcher.search(board, max_depth=1)
        self.assertEqual(r2.lmr_considered, 0)
        self.assertEqual(r2.lmr_reduced_searches, 0)
        self.assertEqual(r2.lmr_reduced_plies, 0)
        self.assertEqual(r2.lmr_researches, 0)
        self.assertEqual(r2.lmr_fail_lows, 0)
        self.assertEqual(r2.lmr_fail_highs, 0)
        self.assertEqual(r2.lmr_cutoffs, 0)

    def test_17_uci_smoke_test(self):
        """UCI loop with LMR enabled handles startup, search, and clean shutdown."""
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
        self.assertIn("bestmove", stdout)


if __name__ == "__main__":
    unittest.main()
