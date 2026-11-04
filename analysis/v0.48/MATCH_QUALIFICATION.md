# Project Janus v0.48 — Match Qualification Disposition

**Milestone:** Project Janus v0.48  
**Parent Baseline Commit:** `0446ae3` (v0.47 Final)  
**Evaluated Candidates:**
- **Candidate L1:** Lazy Move Selection (`enable_lazy_move_selection=True`)
- **Candidate L2:** Stable Entry-Scored Incremental Selection

---

## 1. Executive Disposition: NO NEW MATCH QUALIFIED

Following the rigorous diagnostic investigations in Phases B through G of Project Janus v0.48, **no candidate qualifies for a new competitive match in this milestone**.

### Summary of Candidate Status:
1. **Candidate L1 (`enable_lazy_move_selection=True`):**
   - **Prior Match Record (v0.47):** Already subjected to a full 50-game controlled paired match against baseline K0 at 180 ms/move. Result: 23.0 / 50.0 (46.0%), mean paired difference $-0.1600$ points/pair, paired $t$-statistic $-1.1610$, two-tailed $p = 0.2563$, 95% bootstrap CI $[-0.4400, +0.0800]$.
   - **v0.48 Diagnostic Findings:** Confirmed that L1 reduces search execution runtime by $-17.68\%$ at Depth 5 (saving 14,510 complete move-list sorts and bypassing 99.1% of unnecessary quiet history lookups). Confirmed that search divergences from K0 are benign (95.95% exact move+score agreement, zero blunders, zero tactical regressions).
   - **Match Justification:** Running a duplicate paired match under identical conditions without algorithmic changes would be statistically redundant and an uninformative expenditure of compute. L1's playing strength is already established as indistinguishable from K0 under practical time controls.
   - **Disposition:** Retained as an experimental option; disqualified from immediate re-matching.

2. **Candidate L2 (Stable Entry-Scored Incremental Selection):**
   - **Diagnostic Findings (Phase F):** Successfully achieved 100.0% node-for-node and score-for-score equivalence to K0 (405,197 nodes vs 405,197 nodes at Depth 4). However, the overhead of constructing and pre-scoring move wrapper objects in interpreted Python increased search runtime from 32.48s to 37.98s ($+16.9\%$ runtime overhead, $-14.5\%$ NPS degradation).
   - **Match Justification:** Fails the primary prerequisite of search efficiency improvement. Incurring a $-14.5\%$ speed penalty without any search quality enhancement would strictly handicap the engine in fixed-time play.
   - **Disposition:** Disqualified from match testing; retained purely as a diagnostic reference proving K0 semantic equivalence.

---

## 2. Preregistered Qualification Criteria Audit

| Preregistered Criterion | Candidate L1 | Candidate L2 | Evaluation Status |
|---|---|---|---|
| **Criterion 1: Statistically significant search-efficiency improvement** | **PASS** ($-17.7\%$ runtime at D5, 14,510 sorts avoided) | **FAIL** ($+16.9\%$ runtime, $-14.5\%$ NPS) | Only L1 demonstrates net computational efficiency. |
| **Criterion 2: Search correctness and tactical preservation** | **PASS** (0 tactical refutations, 0 blunders, 95.95% exact match) | **PASS** (100.0% node-identical to K0) | Both preserve tactical safety. |
| **Criterion 3: Fixed-time decision-quality benefit or neutrality** | **PASS** (Maintains high agreement and depth equivalence across budget tiers) | **FAIL** (Lower NPS causes lower search depth under fixed time) | L2 fails fixed-time criteria. |
| **Criterion 4: Unresolved playing-strength hypothesis** | **FAIL** (Playing strength already measured in v0.47: $p=0.256$) | **FAIL** (NPS regression precludes competitive test) | Neither candidate warrants a new match. |

---

## 3. Scientific Rationale Against Premature Re-Matching

A playing-strength match is an expensive statistical instrument designed to detect whether an efficiency improvement translates into an Elo gain under clock conditions. 

In the case of L1:
1. **The measurement already exists:** v0.47 conducted a 50-game preregistered match against K0. The confidence interval $[-0.44, +0.08]$ clearly bounds the treatment effect around neutral to slightly negative (likely due to Python garbage collection jitter or minor search divergence in quiet endgames).
2. **v0.48 did not alter L1's search semantics:** The purpose of v0.48 was diagnostic decomposition (answering *why* L1 is faster and *why* it occasionally diverges), not the introduction of a new heuristic. Conducting another 50-game match on the exact same engine binary would merely produce another drawish estimate with no new information.
3. **Focus on high-leverage bottlenecks:** v0.48's diagnostic discoveries (such as the 99.1% quiet history lookup waste and TT hit rates) provide the empirical blueprint for future compiled (C-extension/Cython) move pickers or killer-move heuristics, which *will* justify dedicated match qualification.

