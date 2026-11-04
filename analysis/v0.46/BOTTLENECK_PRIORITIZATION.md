# Evidence-Based Bottleneck Prioritization (v0.46)

Based on the empirical findings gathered across Phases B through G, the search and move-ordering bottlenecks in Project Janus are prioritized below by evidence strength and expected performance impact.

---

## 1. Bottleneck Priority 1: Eager Full Move-List Sorting (High Priority / High Confidence)
- **Empirical Evidence:**
  - Audited in `SEARCH_ARCHITECTURE_AUDIT.md`: `_ordered_moves` calls `moves.sort(key=...)` on the entire legal move list ($\approx 35$ moves) at every visited node.
  - Telemetry in `FIXED_DEPTH_EFFICIENCY.md` & `MOVE_ORDERING_FINDINGS.md`: At depth 5, **$75.79\%$ of cutoffs occur on move 0**, yet all 35 moves are scored and sorted up front.
  - Ordering overhead accounted for **$14.305$ seconds** out of ~193s total search time (~$7.4\%$ of total CPU time) purely in Python sort comparison overhead.
- **Search Impact:** Substantial CPU cycles wasted at every beta-cutoff node sorting quiet moves that are never evaluated.
- **Feasibility:** Very high (pure algorithmic refactor to staged/lazy move generation/selection without changing move ordering semantics).

---

## 2. Bottleneck Priority 2: Weak Quiet-Move Discrimination Outside Killer Moves (Medium Priority / High Confidence)
- **Empirical Evidence:**
  - When killer moves fail to produce a cutoff ($7.39\%$ of quiet cutoffs, or in positions with low tactical tension), the first-move cutoff rate plummets to $53.97\%\text{--}58.86\%$ (e.g., `divergence_p99_black_ply2`, `control_p31_white_ply7`).
  - Search tree branching factor spikes by $2\times\text{--}4\times$ in these positions because unpromising quiet moves are evaluated ahead of the refuting quiet move.
  - Butterfly history table currently lacks gravity/aging and countermove history integration.
- **Search Impact:** Node inflation in quiet, non-tactical middlegame and endgame positions.
- **Feasibility:** High (requires disciplined history heuristic tuning and validation).

---

## 3. Bottleneck Priority 3: Fixed-Time Iteration Boundary Quantization (Medium Priority / Medium Confidence)
- **Empirical Evidence:**
  - Detailed in `FIXED_TIME_SEARCH_ANALYSIS.md`: At fixed budgets of 180ms–500ms, between $30\%$ and $55\%$ of search time is frequently consumed inside an uncompleted final iteration whose results are discarded.
  - Engines fail to step up in nominal depth because the remaining budget is deemed insufficient or expires mid-search.
- **Search Impact:** Fixed-depth quantization limits playing strength improvements under tight time controls.
- **Feasibility:** Medium (requires cautious time-management adjustments to avoid timeout forfeits).

