"""Supervised UCI Engine Process Session for Project Janus.

Provides robust process lifecycle supervision, timeout enforcement, UCI handshake
verification, stderr capture, and deterministic process cleanup.
"""
from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import chess


class EngineError(Exception):
    """Base exception for supervised engine session failures."""
    pass


class EngineInitializationError(EngineError):
    """Raised when engine fails to start or complete UCI handshake."""
    pass


class EngineProcessError(EngineError):
    """Raised when engine process crashes, terminates unexpectedly, or breaks pipe."""
    pass


class EngineTimeoutError(EngineError):
    """Raised when engine exceeds its allocated time budget for handshake or move."""
    pass


class EngineProtocolError(EngineError):
    """Raised when engine outputs malformed UCI or an illegal move."""
    pass


@dataclass
class MoveResult:
    """Telemetry and outcome of an engine move search."""
    move: chess.Move
    time_s: float
    depth: int = 0
    score: Optional[int] = None
    nodes: int = 0
    pv: list[chess.Move] = field(default_factory=list)


class SupervisedEngineSession:
    """Supervised subprocess wrapper for a single chess engine game lifecycle."""

    def __init__(
        self,
        cmd: list[str],
        cwd: Optional[str | Path] = None,
        env: Optional[dict[str, str]] = None,
        name: str = "Engine",
        startup_timeout: float = 5.0,
        move_timeout_padding: float = 5.0,
    ) -> None:
        self.cmd = cmd
        self.cwd = str(cwd) if cwd else None
        self.env = env
        self.name = name
        self.startup_timeout = startup_timeout
        self.move_timeout_padding = move_timeout_padding

        self.process: Optional[subprocess.Popen[str]] = None
        self.options: dict[str, Any] = {}
        self.stderr_captured: list[str] = []
        self._is_ready = False

        self._stdout_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None

    def __enter__(self) -> SupervisedEngineSession:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def is_alive(self) -> bool:
        """Check whether the underlying subprocess is currently running."""
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        """Launch subprocess and complete UCI handshake."""
        try:
            self.process = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                env=self.env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line-buffered
            )
        except Exception as exc:
            raise EngineInitializationError(
                f"Failed to spawn {self.name} with cmd {self.cmd}: {exc}"
            ) from exc

        # Spawn non-blocking reader threads for Windows pipe safety
        def _read_stdout():
            try:
                for line in self.process.stdout:
                    self._stdout_queue.put(line.strip())
            except Exception:
                pass
            self._stdout_queue.put(None)  # Sentinel for EOF

        def _read_stderr():
            try:
                for line in self.process.stderr:
                    self.stderr_captured.append(line.strip())
            except Exception:
                pass

        self._stdout_thread = threading.Thread(target=_read_stdout, daemon=True)
        self._stdout_thread.start()

        self._stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
        self._stderr_thread.start()

        # Send UCI command
        self._send_line("uci")
        deadline = time.monotonic() + self.startup_timeout
        saw_uciok = False

        while time.monotonic() < deadline:
            line = self._read_line(timeout=max(0.01, deadline - time.monotonic()))
            if line is None:
                if not self.is_alive():
                    exit_code = self.process.poll()
                    raise EngineProcessError(
                        f"{self.name} died during UCI startup with exit code {exit_code}. "
                        f"Stderr: {self.get_stderr_snippet()}"
                    )
                continue
            if line == "uciok":
                saw_uciok = True
                break

        if not saw_uciok:
            self.close()
            raise EngineTimeoutError(
                f"{self.name} timed out waiting for 'uciok' ({self.startup_timeout}s)"
            )

    def configure(self, options: dict[str, Any]) -> None:
        """Apply UCI options and verify engine readiness with isready."""
        if not self.is_alive():
            raise EngineProcessError(f"{self.name} is not alive to receive configuration")

        for name, val in options.items():
            if isinstance(val, bool):
                val_str = "true" if val else "false"
            else:
                val_str = str(val)
            self._send_line(f"setoption name {name} value {val_str}")
            self.options[name] = val

        # Verify readiness
        self._send_line("isready")
        deadline = time.monotonic() + self.startup_timeout
        saw_readyok = False

        while time.monotonic() < deadline:
            line = self._read_line(timeout=max(0.01, deadline - time.monotonic()))
            if line is None:
                if not self.is_alive():
                    exit_code = self.process.poll()
                    raise EngineProcessError(
                        f"{self.name} died during isready with exit code {exit_code}. "
                        f"Stderr: {self.get_stderr_snippet()}"
                    )
                continue
            if line == "readyok":
                saw_readyok = True
                break

        if not saw_readyok:
            self.close()
            raise EngineTimeoutError(
                f"{self.name} timed out waiting for 'readyok' ({self.startup_timeout}s)"
            )
        self._is_ready = True

    def ucinewgame(self) -> None:
        """Send ucinewgame and wait for isready/readyok sync."""
        if not self.is_alive():
            raise EngineProcessError(f"{self.name} is not alive for ucinewgame")
        self._send_line("ucinewgame")
        self._send_line("isready")
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            line = self._read_line(timeout=max(0.01, deadline - time.monotonic()))
            if line == "readyok":
                return
        raise EngineTimeoutError(f"{self.name} timed out waiting for readyok after ucinewgame")

    def play_move(
        self,
        board: chess.Board,
        movetime_ms: Optional[int] = None,
        wtime: Optional[int] = None,
        btime: Optional[int] = None,
        winc: Optional[int] = None,
        binc: Optional[int] = None,
        movestogo: Optional[int] = None,
    ) -> MoveResult:
        """Instruct engine to search from board position and return legal bestmove."""
        if not self.is_alive():
            raise EngineProcessError(f"{self.name} is not running")

        # Construct position command
        start_fen = board.root().fen() if hasattr(board, "root") else chess.STARTING_FEN
        if board.move_stack:
            moves_str = " ".join(m.uci() for m in board.move_stack)
            if start_fen == chess.STARTING_FEN:
                self._send_line(f"position startpos moves {moves_str}")
            else:
                self._send_line(f"position fen {start_fen} moves {moves_str}")
        else:
            if board.fen() == chess.STARTING_FEN:
                self._send_line("position startpos")
            else:
                self._send_line(f"position fen {board.fen()}")

        t_start = time.monotonic()
        if movetime_ms is not None:
            self._send_line(f"go movetime {movetime_ms}")
            time_budget_s = (movetime_ms / 1000.0) + self.move_timeout_padding
        else:
            parts = ["go"]
            if wtime is not None:
                parts.extend(["wtime", str(int(wtime))])
            if btime is not None:
                parts.extend(["btime", str(int(btime))])
            if winc is not None:
                parts.extend(["winc", str(int(winc))])
            if binc is not None:
                parts.extend(["binc", str(int(binc))])
            if movestogo is not None:
                parts.extend(["movestogo", str(int(movestogo))])
            self._send_line(" ".join(parts))
            active_clock = wtime if board.turn == chess.WHITE else btime
            clock_s = (float(active_clock) / 1000.0) if active_clock is not None else 10.0
            time_budget_s = clock_s + self.move_timeout_padding

        deadline = t_start + time_budget_s

        bestmove_str: Optional[str] = None
        depth = 0
        score = None
        nodes = 0
        pv: list[chess.Move] = []

        while time.monotonic() < deadline:
            line = self._read_line(timeout=max(0.01, deadline - time.monotonic()))
            if line is None:
                if not self.is_alive():
                    exit_code = self.process.poll()
                    raise EngineProcessError(
                        f"{self.name} died during search with exit code {exit_code}. "
                        f"Stderr: {self.get_stderr_snippet()}"
                    )
                continue

            parts = line.split()
            if not parts:
                continue

            if parts[0] == "info":
                for i, token in enumerate(parts):
                    if token == "depth" and i + 1 < len(parts):
                        try:
                            depth = int(parts[i + 1])
                        except ValueError:
                            pass
                    elif token == "nodes" and i + 1 < len(parts):
                        try:
                            nodes = int(parts[i + 1])
                        except ValueError:
                            pass
                    elif token == "score" and i + 2 < len(parts):
                        stype, sval = parts[i + 1], parts[i + 2]
                        try:
                            if stype == "cp":
                                score = int(sval)
                            elif stype == "mate":
                                mate_moves = int(sval)
                                score = 100_000 - abs(mate_moves) if mate_moves > 0 else -100_000 + abs(mate_moves)
                        except ValueError:
                            pass

            elif parts[0] == "bestmove":
                bestmove_str = parts[1]
                break

        elapsed = time.monotonic() - t_start

        if bestmove_str is None:
            # Attempt graceful stop before terminating
            try:
                self._send_line("stop")
            except Exception:
                pass

            stop_deadline = time.monotonic() + 1.0
            while time.monotonic() < stop_deadline:
                l = self._read_line(timeout=0.1)
                if l and l.startswith("bestmove"):
                    parts = l.split()
                    if len(parts) >= 2:
                        bestmove_str = parts[1]
                        break

            if bestmove_str is None:
                self.close()
                raise EngineTimeoutError(
                    f"{self.name} exceeded time limit ({time_budget_s:.1f}s) without bestmove"
                )

        if bestmove_str in ("(none)", "0000", "null"):
            raise EngineProtocolError(f"{self.name} returned null/none bestmove in legal position")

        try:
            move_obj = chess.Move.from_uci(bestmove_str)
        except ValueError as exc:
            raise EngineProtocolError(f"Malformed UCI move from {self.name}: {bestmove_str}") from exc

        if move_obj not in board.legal_moves:
            raise EngineProtocolError(
                f"{self.name} returned illegal move {bestmove_str} in FEN {board.fen()}"
            )

        return MoveResult(
            move=move_obj,
            time_s=elapsed,
            depth=depth,
            score=score,
            nodes=nodes,
            pv=pv,
        )

    def close(self) -> None:
        """Safely terminate engine subprocess and close all open pipes."""
        if self.process is None:
            return

        # Attempt graceful quit
        if self.is_alive():
            try:
                self._send_line("quit")
            except Exception:
                pass

            try:
                self.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                # Escalate to terminate
                try:
                    self.process.terminate()
                    self.process.wait(timeout=1.0)
                except Exception:
                    pass

                # Force kill if still hanging
                if self.is_alive():
                    try:
                        self.process.kill()
                        self.process.wait(timeout=1.0)
                    except Exception:
                        pass

        # Close all streams
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

        self.process = None

    def _send_line(self, line: str) -> None:
        if self.process is None or self.process.stdin is None or not self.is_alive():
            raise EngineProcessError(f"Cannot write to {self.name}: process not alive")
        try:
            self.process.stdin.write(line + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise EngineProcessError(f"Broken pipe writing to {self.name}: {exc}") from exc

    def _read_line(self, timeout: float = 0.1) -> Optional[str]:
        """Read single line from non-blocking queue with deadline."""
        try:
            return self._stdout_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_stderr_snippet(self, max_lines: int = 5) -> str:
        if not self.stderr_captured:
            return "<no stderr captured>"
        return "\n".join(self.stderr_captured[-max_lines:])
