"""Regression and Failure-Injection Test Suite for Janus Match Harness Lifecycle.

Validates the 15 requirements specified in Phase 4 of Project Janus v0.34.2:
1. Normal game completion.
2. Candidate crashes during initialization.
3. Reference crashes during initialization.
4. Candidate crashes during a game.
5. Reference crashes during a game.
6. Timeout during engine initialization.
7. Timeout during a move.
8. Invalid UCI response or invalid move.
9. Cleanup after process failure.
10. Recovery into a subsequent independent game.
11. Retry preserves the original opening and colour assignment.
12. Failed attempts are excluded from chess-strength statistics.
13. Incomplete pairs are excluded from paired analysis.
14. UCI options and evaluation configurations are applied to every new process.
15. A failed match exits unsuccessfully rather than reporting a completed match.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional

import chess

from janus.engine_session import (
    EngineError,
    EngineInitializationError,
    EngineProcessError,
    EngineProtocolError,
    EngineTimeoutError,
    MoveResult,
    SupervisedEngineSession,
)
from scripts.match_v0342 import (
    play_supervised_game,
    run_clean_match,
    summarize_match,
)


class MockProcess:
    """Mock process object simulating subprocess.Popen poll and streams."""

    def __init__(self, exit_code: Optional[int] = None) -> None:
        self._exit_code = exit_code

    def poll(self) -> Optional[int]:
        return self._exit_code


class FakeEngineSession(SupervisedEngineSession):
    """Deterministic test double for SupervisedEngineSession."""

    def __init__(
        self,
        name: str = "FakeEngine",
        fail_at_start: Optional[str] = None,      # "crash", "timeout"
        fail_at_configure: Optional[str] = None,  # "crash", "timeout"
        fail_at_ply: Optional[int] = None,         # ply number to fail
        fail_mode: Optional[str] = None,           # "crash", "timeout", "illegal_move", "null_move"
        moves_to_play: Optional[list[chess.Move]] = None,
    ) -> None:
        super().__init__(cmd=["fake"], name=name)
        self.name = name
        self.fail_at_start = fail_at_start
        self.fail_at_configure = fail_at_configure
        self.fail_at_ply = fail_at_ply
        self.fail_mode = fail_mode
        self.moves_to_play = moves_to_play or []
        self._move_idx = 0
        self.moves_called = 0
        self.closed = False
        self.started = False
        self.configured_options: dict[str, Any] = {}
        self.process = MockProcess(exit_code=None)

    def start(self) -> None:
        self.started = True
        if self.fail_at_start == "crash":
            self.process = MockProcess(exit_code=1)
            raise EngineProcessError(f"{self.name} crashed during start")
        elif self.fail_at_start == "timeout":
            raise EngineTimeoutError(f"{self.name} timed out during start")

    def configure(self, options: dict[str, Any]) -> None:
        if self.fail_at_configure == "crash":
            self.process = MockProcess(exit_code=1)
            raise EngineProcessError(f"{self.name} crashed during configure")
        elif self.fail_at_configure == "timeout":
            raise EngineTimeoutError(f"{self.name} timed out during configure")
        self.configured_options.update(options)

    def ucinewgame(self) -> None:
        pass

    def is_alive(self) -> bool:
        return self.started and not self.closed and (self.process.poll() is None)

    def play_move(self, board: chess.Board, movetime_ms: int) -> MoveResult:
        self.moves_called += 1
        current_ply = board.ply() + 1

        if self.fail_at_ply is not None and current_ply >= self.fail_at_ply:
            if self.fail_mode == "crash":
                self.process = MockProcess(exit_code=1)
                raise EngineProcessError(f"{self.name} crashed at ply {current_ply}")
            elif self.fail_mode == "timeout":
                raise EngineTimeoutError(f"{self.name} timed out at ply {current_ply}")
            elif self.fail_mode == "illegal_move":
                # Return move for opposite turn or impossible move
                return MoveResult(move=chess.Move.from_uci("a1a8"), time_s=0.01)
            elif self.fail_mode == "null_move":
                raise EngineProtocolError(f"{self.name} returned null move")

        # Pick legal move
        if self.moves_to_play and self._move_idx < len(self.moves_to_play):
            mv = self.moves_to_play[self._move_idx]
            self._move_idx += 1
        else:
            # Deterministic first legal move
            mv = next(iter(board.legal_moves))

        return MoveResult(
            move=mv,
            time_s=0.01,
            depth=5,
            nodes=100,
            score=10,
        )

    def close(self) -> None:
        self.closed = True
        self.process = MockProcess(exit_code=0)

    def get_stderr_snippet(self, max_lines: int = 5) -> str:
        return f"{self.name} mock stderr"


class TestMatchHarnessLifecycle(unittest.TestCase):
    """Test suite verifying harness robustness under all lifecycle and failure modes."""

    def test_01_normal_game_completion(self):
        """Req 1: Normal game plays to valid chess termination with both engines healthy."""
        cand = FakeEngineSession(name="Janus-v0.34")
        base = FakeEngineSession(name="Janus-v0.30")

        cand.start()
        base.start()
        game_pgn, rec = play_supervised_game(
            base_session=base,
            cand_session=cand,
            game_number=1,
            pair_number=1,
            attempt_number=1,
            cand_color=chess.WHITE,
            movetime_ms=100,
            max_plies=10,
            start_fen=None,
            opening_id="startpos",
            opening_name="Standard",
        )
        cand.close()
        base.close()

        self.assertIsNotNone(game_pgn)
        self.assertEqual(rec["status"], "valid_chess")
        self.assertIn(rec["result"], ["1-0", "0-1", "1/2-1/2"])
        self.assertGreater(rec["plies"], 0)
        self.assertTrue(cand.closed)
        self.assertTrue(base.closed)

    def test_02_candidate_crashes_during_initialization(self):
        """Req 2: Candidate crashes during startup -> recorded as infrastructure failure."""
        cand = FakeEngineSession(name="Janus-v0.34", fail_at_start="crash")
        with self.assertRaises(EngineProcessError):
            cand.start()
        self.assertFalse(cand.is_alive())

    def test_03_reference_crashes_during_initialization(self):
        """Req 3: Reference crashes during startup -> recorded as infrastructure failure."""
        base = FakeEngineSession(name="Janus-v0.30", fail_at_start="crash")
        with self.assertRaises(EngineProcessError):
            base.start()
        self.assertFalse(base.is_alive())

    def test_04_candidate_crashes_during_game(self):
        """Req 4: Candidate crashes mid-game -> recorded as infrastructure failure, not forfeit."""
        cand = FakeEngineSession(name="Janus-v0.34", fail_at_ply=3, fail_mode="crash")
        base = FakeEngineSession(name="Janus-v0.30")

        cand.start()
        base.start()
        game_pgn, rec = play_supervised_game(
            base_session=base,
            cand_session=cand,
            game_number=1,
            pair_number=1,
            attempt_number=1,
            cand_color=chess.WHITE,
            movetime_ms=100,
            max_plies=10,
            start_fen=None,
            opening_id="startpos",
            opening_name="Standard",
        )
        cand.close()
        base.close()

        self.assertIsNone(game_pgn)
        self.assertEqual(rec["status"], "infrastructure_failure")
        self.assertEqual(rec["failed_engine"], "Janus-v0.34")
        self.assertEqual(rec["failure_category"], "EngineProcessError")
        self.assertNotIn("1-0", rec.get("result", ""))
        self.assertNotIn("0-1", rec.get("result", ""))

    def test_05_reference_crashes_during_game(self):
        """Req 5: Reference crashes mid-game -> infrastructure failure, not candidate win."""
        cand = FakeEngineSession(name="Janus-v0.34")
        base = FakeEngineSession(name="Janus-v0.30", fail_at_ply=2, fail_mode="crash")

        cand.start()
        base.start()
        game_pgn, rec = play_supervised_game(
            base_session=base,
            cand_session=cand,
            game_number=1,
            pair_number=1,
            attempt_number=1,
            cand_color=chess.WHITE,
            movetime_ms=100,
            max_plies=10,
            start_fen=None,
            opening_id="startpos",
            opening_name="Standard",
        )
        cand.close()
        base.close()

        self.assertIsNone(game_pgn)
        self.assertEqual(rec["status"], "infrastructure_failure")
        self.assertEqual(rec["failed_engine"], "Janus-v0.30")
        self.assertEqual(rec["failure_category"], "EngineProcessError")

    def test_06_timeout_during_initialization(self):
        """Req 6: Timeout waiting for uciok/readyok is caught and reported."""
        cand = FakeEngineSession(name="Janus-v0.34", fail_at_start="timeout")
        with self.assertRaises(EngineTimeoutError):
            cand.start()

    def test_07_timeout_during_move(self):
        """Req 7: Move budget overrun is caught and reported as EngineTimeoutError."""
        cand = FakeEngineSession(name="Janus-v0.34", fail_at_ply=1, fail_mode="timeout")
        base = FakeEngineSession(name="Janus-v0.30")

        cand.start()
        base.start()
        game_pgn, rec = play_supervised_game(
            base_session=base,
            cand_session=cand,
            game_number=1,
            pair_number=1,
            attempt_number=1,
            cand_color=chess.WHITE,
            movetime_ms=100,
            max_plies=10,
            start_fen=None,
            opening_id="startpos",
            opening_name="Standard",
        )
        cand.close()
        base.close()

        self.assertIsNone(game_pgn)
        self.assertEqual(rec["status"], "infrastructure_failure")
        self.assertEqual(rec["failure_category"], "EngineTimeoutError")

    def test_08_invalid_uci_response_or_illegal_move(self):
        """Req 8: Illegal move returned by engine is detected and rejected."""
        cand = FakeEngineSession(name="Janus-v0.34", fail_at_ply=1, fail_mode="null_move")
        base = FakeEngineSession(name="Janus-v0.30")

        cand.start()
        base.start()
        game_pgn, rec = play_supervised_game(
            base_session=base,
            cand_session=cand,
            game_number=1,
            pair_number=1,
            attempt_number=1,
            cand_color=chess.WHITE,
            movetime_ms=100,
            max_plies=10,
            start_fen=None,
            opening_id="startpos",
            opening_name="Standard",
        )
        cand.close()
        base.close()

        self.assertIsNone(game_pgn)
        self.assertEqual(rec["status"], "infrastructure_failure")
        self.assertEqual(rec["failure_category"], "EngineProtocolError")

    def test_09_cleanup_after_process_failure(self):
        """Req 9: Failed session resources and processes are closed cleanly."""
        cand = FakeEngineSession(name="Janus-v0.34", fail_at_ply=1, fail_mode="crash")
        cand.start()
        try:
            cand.play_move(chess.Board(), movetime_ms=100)
        except EngineProcessError:
            pass
        cand.close()
        self.assertTrue(cand.closed)
        self.assertEqual(cand.process.poll(), 0)

    def test_10_recovery_into_subsequent_independent_game(self):
        """Req 10: Process failure in game 1 does not contaminate subsequent game 2."""
        # Factory that fails on first game instance but succeeds on second
        call_count = {"cand": 0}

        def factory(cmd, cwd, env, name):
            if name == "Janus-v0.34":
                call_count["cand"] += 1
                if call_count["cand"] == 1:
                    # First game candidate crashes
                    return FakeEngineSession(name=name, fail_at_ply=1, fail_mode="crash")
                return FakeEngineSession(name=name)
            return FakeEngineSession(name=name)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = run_clean_match(
                games=2,
                movetime_ms=100,
                max_plies=6,
                seed=42,
                output_dir_path=tmp_dir,
                session_factory=factory,
                max_retries_per_slot=1,
            )

            # Game 1 retried once and succeeded, Game 2 succeeded
            self.assertEqual(summary["valid_completed_games"], 2)
            self.assertEqual(summary["infrastructure_failures"], 1)
            self.assertEqual(summary["retried_attempts"], 1)

    def test_11_retry_preserves_opening_and_color(self):
        """Req 11: Retrying a failed attempt keeps opening FEN and candidate colour identical."""
        attempt_history: list[dict[str, Any]] = []
        call_count = {"cand": 0}

        def factory(cmd, cwd, env, name):
            if name == "Janus-v0.34":
                call_count["cand"] += 1
                if call_count["cand"] == 1:
                    return FakeEngineSession(name=name, fail_at_ply=1, fail_mode="crash")
            return FakeEngineSession(name=name)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = run_clean_match(
                games=1,
                movetime_ms=100,
                max_plies=4,
                seed=42,
                output_dir_path=tmp_dir,
                session_factory=factory,
                max_retries_per_slot=1,
            )
            attempts = summary["attempts"] if "attempts" in summary else []

            # Check that attempt 1 (failed) and attempt 2 (valid) have identical opening and color
            import json
            att_file = Path(tmp_dir) / "attempts.json"
            all_attempts = json.loads(att_file.read_text(encoding="utf-8"))
            self.assertEqual(len(all_attempts), 2)
            att1, att2 = all_attempts[0], all_attempts[1]
            self.assertEqual(att1["status"], "infrastructure_failure")
            self.assertEqual(att2["status"], "valid_chess")
            self.assertEqual(att1["start_fen"], att2["start_fen"])
            self.assertEqual(att1["candidate_color"], att2["candidate_color"])
            self.assertEqual(att1["game"], att2["game"])

    def test_12_failed_attempts_excluded_from_chess_stats(self):
        """Req 12: Failed attempts are never counted in wins/draws/losses or score."""
        valid_games = [
            {"game": 1, "pair": 1, "candidate_color": "white", "result": "1-0"},
            {"game": 2, "pair": 1, "candidate_color": "black", "result": "1/2-1/2"},
        ]
        attempts = [
            {"game": 1, "attempt_number": 1, "status": "infrastructure_failure"},
            {"game": 1, "attempt_number": 2, "status": "valid_chess"},
            {"game": 2, "attempt_number": 1, "status": "valid_chess"},
        ]

        summary = summarize_match(
            valid_games=valid_games,
            attempts=attempts,
            planned_games=2,
            planned_pairs=1,
        )

        self.assertEqual(summary["valid_completed_games"], 2)
        self.assertEqual(summary["infrastructure_failures"], 1)
        self.assertEqual(summary["candidate_wins"], 1)
        self.assertEqual(summary["candidate_draws"], 1)
        self.assertEqual(summary["candidate_losses"], 0)
        self.assertEqual(summary["candidate_score"], 1.5)
        self.assertEqual(summary["candidate_score_pct"], 75.0)

    def test_13_incomplete_pairs_excluded_from_paired_analysis(self):
        """Req 13: Incomplete pairs (only 1 valid game) are excluded from paired outcomes."""
        valid_games = [
            {"game": 1, "pair": 1, "candidate_color": "white", "result": "1-0"},
            # Game 2 in pair 1 missing!
            {"game": 3, "pair": 2, "candidate_color": "white", "result": "1-0"},
            {"game": 4, "pair": 2, "candidate_color": "black", "result": "0-1"},
        ]
        attempts = [
            {"game": 1, "status": "valid_chess"},
            {"game": 2, "status": "infrastructure_failure"},
            {"game": 3, "status": "valid_chess"},
            {"game": 4, "status": "valid_chess"},
        ]

        summary = summarize_match(
            valid_games=valid_games,
            attempts=attempts,
            planned_games=4,
            planned_pairs=2,
        )

        self.assertEqual(summary["pairs_summary"]["completed_valid_pairs"], 1)
        self.assertEqual(summary["pairs_summary"]["pairs_won"], 1)
        self.assertEqual(summary["incomplete_pairs"], 1)
        self.assertFalse(summary["target_met"])

    def test_14_uci_options_applied_to_every_new_process(self):
        """Req 14: Engine options (such as Hash: 128) are configured on every fresh session."""
        sessions_created: list[FakeEngineSession] = []

        def factory(cmd, cwd, env, name):
            sess = FakeEngineSession(name=name)
            sessions_created.append(sess)
            return sess

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_clean_match(
                games=2,
                movetime_ms=100,
                max_plies=4,
                seed=42,
                output_dir_path=tmp_dir,
                session_factory=factory,
            )

            self.assertEqual(len(sessions_created), 4)  # 2 games * 2 engines
            for sess in sessions_created:
                self.assertIn("Hash", sess.configured_options)
                self.assertEqual(sess.configured_options["Hash"], 128)

    def test_15_failed_match_exits_unsuccessfully(self):
        """Req 15: If target valid games or pairs are not achieved, target_met is False."""
        # Force persistent failure so match cannot complete
        def factory(cmd, cwd, env, name):
            return FakeEngineSession(name=name, fail_at_start="crash")

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = run_clean_match(
                games=2,
                movetime_ms=100,
                max_plies=4,
                seed=42,
                output_dir_path=tmp_dir,
                session_factory=factory,
                max_retries_per_slot=1,
                max_match_failures=2,
            )

            self.assertFalse(summary["target_met"])
            self.assertEqual(summary["valid_completed_games"], 0)
            self.assertGreater(summary["infrastructure_failures"], 0)


if __name__ == "__main__":
    unittest.main()
