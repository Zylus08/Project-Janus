# Final Decision & Milestone Qualification (v0.46)

## 1. Chosen Milestone Outcome Category
In accordance with Phase L of the v0.46 specification, the final decision category selected based on experimental evidence is:

**Category A: Optimization Opportunity Confirmed**

---

## 2. Evidence Supporting Category A Selection

### Evidence 1: Move-Ordering Overhead Quantified
- Diagnostic telemetry recorded across 37 positions established that **$75.79\%$ of all cutoffs occur on move 0**.
- Despite this high first-move cutoff rate, `JanusSearch` eagerly computes scores and sorts the entire legal move list ($\approx 35$ moves) at every visited node.
- Python lambda sort comparisons consumed **$14.305$ seconds** at depth 5 alone (~$7.4\%$ of total engine execution time), demonstrating a clear structural optimization opportunity via lazy move generation.

### Evidence 2: Quiet Move Discrimination Deficit in Positional Positions
- In quiet positions without sharp tactical tension, the first-move cutoff rate degrades to **$53.97\%\text{--}58.86\%$** (e.g. `divergence_p99_black_ply2` at $53.97\%$).
- When killer moves fail to refute, the search evaluates $3\text{--}8$ quiet moves before finding a refutation, multiplying subtree volume. A decayed, depth-scaled history heuristic represents a high-probability opportunity to regain search efficiency.

### Evidence 3: RFP Pruning Invariance Confirmed
- RFP pruned $10.60\%$ of nodes at depth 4 and $9.19\%$ of nodes at depth 5 across all 37 diagnostic positions.
- Across 148 position-depth trials ($37 \times 4$), RFP produced **zero move disagreements** with K0 ($100\%$ move agreement).
- Decision quality relative to Stockfish 14 was identical to K0 ($40.5\%$ at depth 4, $37.8\%$ at depth 5).

---

## 3. Production Configuration Status
- **Production Default:** **K0 (`enable_rfp=False`) remains the production default.**
- **RFP Status:** Retained in codebase, disabled by default.
- **Next Milestone Focus:** Implement a staged/lazy move selection architecture (`MovePicker`) and evaluate history aging to address the confirmed bottlenecks without altering search semantics.

