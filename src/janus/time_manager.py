"""Adaptive Time Management Component for Project Janus v0.35.

Provides deterministic, configurable, and robust time allocation across:
1. Fixed movetime ('go movetime X')
2. Classical clock controls without increment ('go wtime X btime Y [movestogo N]')
3. Fischer increment controls ('go wtime X btime Y winc A binc B [movestogo N]')

Implements safety reserves, emergency allocations under low-clock conditions,
and strict parameter clamping to prevent clock overruns and flagging.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Union

import chess


@dataclass(frozen=True)
class TimeManagerConfig:
    """Configuration parameters for adaptive time allocation."""
    safety_reserve_ms: int = 50
    default_moves_to_go: int = 30
    increment_weight: float = 0.85
    min_allocation_ms: int = 10
    max_allocation_ratio: float = 0.20
    policy_name: str = "adaptive"

    @classmethod
    def reference_baseline(cls) -> TimeManagerConfig:
        """Reference uncalibrated baseline policy (naive clock divisor, ignores increment)."""
        return cls(
            safety_reserve_ms=0,
            default_moves_to_go=40,
            increment_weight=0.0,
            min_allocation_ms=10,
            max_allocation_ratio=0.50,
            policy_name="reference",
        )


class TimeManager:
    """Computes search time budgets according to game clock constraints and UCI parameters."""

    def __init__(self, config: Optional[TimeManagerConfig] = None) -> None:
        self.config = config or TimeManagerConfig()

    def allocate_time(
        self,
        side_to_move: chess.Color,
        wtime: Optional[Union[int, float]] = None,
        btime: Optional[Union[int, float]] = None,
        winc: Optional[Union[int, float]] = None,
        binc: Optional[Union[int, float]] = None,
        movestogo: Optional[Union[int, float]] = None,
        movetime: Optional[Union[int, float]] = None,
    ) -> Optional[float]:
        """Calculate the allocated search time limit in seconds.

        Returns:
            float: Time limit in seconds for the search to execute.
            None: If no time constraint was specified (e.g. depth-only or infinite search).
        """
        # Mode A: Fixed movetime (bypasses clock management entirely)
        if movetime is not None:
            try:
                mt_ms = float(movetime)
                if math.isnan(mt_ms) or math.isinf(mt_ms) or mt_ms <= 0:
                    return 0.001
                return max(0.001, mt_ms / 1000.0)
            except (ValueError, TypeError):
                return 0.001

        # Determine side-to-move clock and increment
        raw_time = wtime if side_to_move == chess.WHITE else btime
        raw_inc = winc if side_to_move == chess.WHITE else binc

        if raw_time is None:
            # No clock specified for active side
            return None

        # Sanitize clock input
        try:
            rem_ms = float(raw_time)
            if math.isnan(rem_ms) or math.isinf(rem_ms):
                rem_ms = 0.0
        except (ValueError, TypeError):
            rem_ms = 0.0

        # Sanitize increment
        try:
            inc_ms = float(raw_inc) if raw_inc is not None else 0.0
            if math.isnan(inc_ms) or math.isinf(inc_ms):
                inc_ms = 0.0
            inc_ms = max(0.0, inc_ms)
        except (ValueError, TypeError):
            inc_ms = 0.0

        # Sanitize movestogo
        try:
            if movestogo is not None:
                mtg = int(movestogo)
                moves_left = mtg if mtg > 0 else self.config.default_moves_to_go
            else:
                moves_left = self.config.default_moves_to_go
        except (ValueError, TypeError):
            moves_left = self.config.default_moves_to_go

        # Handle zero or negative clock (flagged or near-flagging)
        if rem_ms <= 0.0:
            return 0.001  # Immediate emergency cutoff

        # Handle extreme time trouble: remaining clock <= safety reserve
        if rem_ms <= self.config.safety_reserve_ms:
            # Allocate a small fraction of the tiny clock so the engine can emit a legal fallback move
            emergency_alloc = max(1.0, min(rem_ms / 2.0, float(self.config.min_allocation_ms)))
            return emergency_alloc / 1000.0

        # Standard Adaptive Clock Allocation
        usable_time = max(0.0, rem_ms - self.config.safety_reserve_ms)
        base_alloc = usable_time / float(moves_left)
        target_alloc = base_alloc + (self.config.increment_weight * inc_ms)

        # Budget caps:
        # 1. Never allocate more than usable time (remaining - safety reserve)
        # 2. Bound per-move expenditure to a ratio of remaining clock plus increment
        ratio_bound = (rem_ms * self.config.max_allocation_ratio) + inc_ms
        max_budget = max(
            float(self.config.min_allocation_ms),
            min(usable_time, ratio_bound),
        )

        final_alloc = min(target_alloc, max_budget)
        final_alloc = max(float(self.config.min_allocation_ms), final_alloc)

        # Final invariant: never allocate more than the remaining clock
        final_alloc = min(final_alloc, rem_ms)
        final_alloc = max(1.0, final_alloc)

        return final_alloc / 1000.0
