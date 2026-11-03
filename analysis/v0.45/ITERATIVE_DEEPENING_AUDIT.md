# Iterative-Deepening Implementation Audit — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Auditor:** Autonomous Senior Chess-Engine Researcher & Search Algorithm Engineer  
**Status:** COMPLETE (Gate B Validated)

---

## 1. Executive Summary

Iterative deepening is the central control loop of `JanusSearch`. Under practical game conditions with constrained time budgets (such as the $3.0\text{s} + 0.1\text{s}$ Fischer time control in v0.43/v0.44), the decision of which move to play is determined by the intersection between nominal search speed and the hard deadline.

This audit examines the exact implementation of iterative deepening, deadline checks, search interruption semantics, state restoration, and move publication in [`src/janus/search.py`](file:///E:/ChessXML/project-janus/src/janus/search.py) and [`src/janus/uci.py`](file:///E:/ChessXML/project-janus/src/janus/uci.py).

---

## 2. Search Lifecycle Reconstruction

The search lifecycle in `JanusSearch.search()` (lines 1059–1260) follows an explicit 11-step pipeline:

```
[1] Receive root state (board, time_limit, wtime/btime, stop_event)
      │
[2] Allocate time budget (self.time_manager.allocate_time)
      │
[3] Compute deadline: self.deadline = start + max(0.001, time_limit)
      │
[4] Reset counters & order root moves: ordered_root = _ordered_moves(board, None, 0)
    Set baseline fallback: best_move = ordered_root[0], completed_depth = 0
      │
[5] Loop depth = 1 ... max_depth:
      ├─ Check pre-iteration deadline: time.monotonic() >= self.deadline -> break
      ├─ Check stop_event: self.stop_event.is_set() -> break
      ├─ Configure aspiration window if depth >= 2: [best_score - delta, best_score + delta]
      ├─ Execute Negamax: _negamax(board, depth, alpha, beta, ply=0)
      │     ├─ Recursive nodes call _check_stop() every 128 nodes (self.nodes & 127 == 0)
      │     └─ If deadline exceeded -> raise SearchTimeout
      │
[6] Interruption Handling:
      ├─ If SearchTimeout raised: loop terminates via 'break'
      └─ Published best_move, best_score, completed_depth, and best_pv are NOT updated
      │
[7] Completion Handling (if iteration finishes fully):
      ├─ best_pv = pv
      ├─ best_move = pv[0]
      ├─ best_score = score
      └─ completed_depth = depth
      │
[8] Return SearchResult(best_move, score, depth=completed_depth, pv=best_pv, ...)
```

---

## 3. Deadline Semantics & Check Granularity

### 3.1 Deadline Computation
- If `time_limit` is explicitly provided, `self.deadline = time.monotonic() + max(0.001, time_limit)`.
- If clock parameters (`wtime`, `btime`, `winc`, `binc`) are provided without `time_limit`, `self.time_manager.allocate_time(...)` calculates a target duration based on moves-to-go and remaining time reserve.

### 3.2 Check Frequency
The stop check is implemented at line 515:
```python
def _check_stop(self) -> None:
    if self.stop_event is not None and self.stop_event.is_set():
        raise SearchTimeout
    if self.deadline is not None and (self.nodes & 127) == 0:
        if time.monotonic() >= self.deadline:
            raise SearchTimeout
```
- Checks occur every $128$ nodes (`self.nodes & 127 == 0`) inside both `_negamax` (line 747) and `_quiescence` (line 651).
- At Janus's average search speed of $\sim 20,000\text{ NPS}$, 128 nodes corresponds to approximately $6.4\text{ ms}$ of wall-clock time.
- Move generation does not check the clock directly, ensuring that no move generator enters a corrupt state mid-generation.

### 3.3 Publication Invariant: Partial Iterations Cannot Overwrite Completed Results
A critical architectural property was verified at lines 1186–1234:
- When `SearchTimeout` is raised within `_negamax`, the exception unwinds the recursive search stack.
- The `try...except SearchTimeout: break` block intercepts the exception and breaks out of the iteration loop immediately.
- The publishing assignment lines (1229–1233):
  ```python
  if pv:
      best_pv = pv
      best_move = pv[0]
  best_score = score
  completed_depth = depth
  ```
  are **bypassed entirely** upon a timeout!
- **Confirmed Fact:** Interrupted iterations are discarded. The engine strictly returns the move, score, PV, and depth from the last fully completed iteration.
- If iteration 1 is interrupted before completion, the engine falls back to `completed_depth = 0` and the root move ordered by static evaluation (`ordered_root[0]`).

---

## 4. Search-State Integrity & Exception Safety

### 4.1 Board State Restoration
- In both `_negamax` and `_quiescence`, all move pushes are wrapped in structured exception blocks:
  ```python
  board.push(move)
  try:
      ...
  finally:
      board.pop()
  ```
- Null-move pruning similarly wraps `board.push(chess.Move.null())` in `try...finally: board.pop()`.
- When `SearchTimeout` unwinds the stack, every active ply executes `board.pop()`. The root board state is 100% restored with zero move leakage.

### 4.2 Transposition Table Interaction Across Iterations
- Completed iterations populate the Transposition Table with depth-$d$ exact scores and best moves.
- When iteration $d+1$ begins, `_probe_tt` retrieves the stored TT move, placing it first in root move ordering (`_ordered_moves`).
- If an iteration is interrupted mid-search, nodes searched before the timeout may have updated the TT with lower or upper bounds, but root move publication remains unaffected.

---

## 5. Gate B Conclusion & Sign-Off

The search lifecycle, deadline checks, exception handling, and result publication logic in `src/janus/search.py` are verified to be mathematically and procedurally sound:
1. Interrupted iterations **never** overwrite completed iteration results.
2. Board state is strictly preserved via `try...finally: board.pop()`.
3. Check granularity of 128 nodes ($\sim 6.4\text{ ms}$) provides responsive deadline termination.

**Gate B Status:** **PASS** — Proceeding to Phase C (Iteration-Level Search Telemetry).

