# Move-Ordering Effectiveness Analysis (v0.46)

## 1. Overview
Using the diagnostic telemetry captured in Phase C and D, this analysis quantifies how effectively Janus sorts candidate moves prior to alpha-beta evaluation and identifies key sources of search inefficiency.

## 2. Quantitative Cutoff Attribution (Depth 5 Baseline, K0)

Across the 37 diagnostic positions evaluated to nominal depth 5 under the K0 production configuration:
- **Total Beta Cutoffs Recorded:** $67,121$
- **First-Move Beta Cutoffs (Index 0):** $50,868$ (**$75.79\%$**)
- **Late-Move Beta Cutoffs (Index $\ge 1$):** $16,253$ (**$24.21\%$**)

### Source Breakdown of Cutoff Moves:
- **Captures (MVV-LVA):** $38,165$ cutoffs (**$56.86\%$** of all cutoffs)
- **Quiet Moves:** $28,956$ cutoffs (**$43.14\%$** of all cutoffs)
- **Transposition Table (TT) Moves:** $14,198$ cutoffs (**$21.15\%$** of all cutoffs)
- **Killer Moves:** $26,817$ cutoffs (**$92.61\%$** of all quiet move cutoffs)

## 3. Structural Move-Ordering Bottlenecks

### Finding 1: High Late-Move Cutoff Rate in Closed/Positional Structures
While sharp tactical positions achieve $\ge 85\%$ first-move cutoffs (e.g. `divergence_p6_black_ply4` at $93.38\%$, `divergence_p54_white_ply6` at $93.24\%$), positions with low tactical tension exhibit severe ordering degradation:
- `divergence_p99_black_ply2`: **$53.97\%$** first-move cutoff rate ($1,147$ late refutations)
- `control_p31_white_ply7`: **$55.65\%$** first-move cutoff rate ($1,637$ late refutations)
- `divergence_p3_white_ply3`: **$58.86\%$** first-move cutoff rate ($532$ late refutations)

In these positions, the search regularly explores $3\text{--}8$ quiet moves before finding a refuting move, multiplying search tree volume by $2\text{--}4\times$.

### Finding 2: Eager Full Move-List Sorting Overhead
As documented in `SEARCH_ARCHITECTURE_AUDIT.md`, `JanusSearch._ordered_moves` calls `moves.sort()` on the complete list of legal moves (~30–40 moves) at every node.
- In $75.8\%$ of cutoff nodes, only the **first move** is ever evaluated.
- Sorting the remaining 29–39 moves represents wasted CPU cycles.
- At depth 5, Python sort lambda comparisons consumed **$14.305$ seconds** across 37 positions (~$7.4\%$ of total CPU search time).

### Finding 3: Quiet Move Discrimination Outside Killer Moves
When killer moves fail to refute ($7.39\%$ of quiet cutoffs), the butterfly history heuristic provides weak discrimination. Unpromising quiet moves are frequently evaluated ahead of the refutation.
