# History Heuristic Computational & Decision Analysis (v0.48 Phase D)

## 1. Executive Summary

Phase D investigates the computational cost and ordering utility of the butterfly history heuristic in Project Janus:
- In v0.47, suppressing history lookups reduced ordering runtime by 72% with only a 1.71% node expansion.
- Phase D instruments the exact ratio of history score computations to useful beta cutoffs to establish why history scoring in Python incurs such high overhead relative to its ordering yield.

## 2. Empirical Findings at Nominal Depth 4

- **Total Nodes Searched:** 405,197 nodes.
- **Total Beta Cutoffs:** 26,634 cutoffs.
- **Total Quiet Moves Scored:** **975,344 quiet moves**.
- **Total History Lookups:** **975,344 table lookups** (2.41 lookups per search node).
- **Quiet Move Cutoffs:** **8,326 cutoffs** (31.26% of all beta cutoffs).
- **History Lookups per Quiet Cutoff:** **117.1 lookups per cutoff**.

## 3. Computational Waste vs Ordering Utility

### A. The 99.1% Wasted Computation Ratio
Out of 975,344 quiet move history lookups performed at Depth 4:
- Only 8,326 moves actually generated a beta cutoff.
- Over **967,000 history lookups (99.15%)** were executed on candidate moves that were either:
  1. Never searched because an earlier move (such as the TT move or a capture) produced an immediate cutoff.
  2. Searched but failed to produce a beta cutoff.

### B. Structural Source of Overhead in Python
1. **Representation:** `self.history: list[list[int]]` (a 64x64 nested Python list).
2. **Access Cost:** In C, a 2D array lookup `history[from][to]` compiles into a single memory offset instruction `base + (from << 6) + to`. In CPython, `self.history[from][to]` requires:
   - Python bytecode `LOAD_FAST self`
   - `LOAD_ATTR history`
   - `BINARY_SUBSCR` (bounds-checking and pointer dereference for row `from`)
   - `BINARY_SUBSCR` (bounds-checking and pointer dereference for element `to`)
   - Integer comparison and arithmetic
3. **Repeated Evaluation:** Because eager sorting invokes Python's Timsort (`moves.sort(key=lambda ...)`), the lambda closure is evaluated for all 30+ legal moves at *every single node in the tree*.

### C. Ordering Contribution
Despite the high lookup waste, the history heuristic is not useless:
- Suppressing history expands the tree by +1.71% (+6,921 nodes at depth 4) and lowers late-move ordering quality.
- However, because TT moves account for ~76% of cutoffs, deferring history scoring until *after* evaluating the TT move eliminates the vast majority of these redundant 975,000 lookups without degrading move ordering when quiet moves actually need to be searched.

