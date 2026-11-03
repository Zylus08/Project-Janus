# Final Decision & Production Disposition (v0.47 Phase J)

## 1. Selected Decision Category

**Category B: Retained as Configurable Experimental Feature**

- **Production Default:** K0 baseline (`enable_lazy_move_selection = False`, `enable_rfp = False`) remains the immutable default production configuration.
- **Experimental Feature:** Candidate L1 (Lazy Move Selection) is retained in the codebase behind the explicit configuration flag `enable_lazy_move_selection = True` and UCI command-line option `--enable-lazy-move-selection`.

---

## 2. Scientific & Engineering Justification

### A. Substantial Computational Efficiency Gains (Phase F)
- Candidate L1 successfully confirmed Hypothesis H1 by deferring full move list scoring and sorting until after evaluating the TT move.
- At nominal depth 5 on the 37-position diagnostic corpus, L1 eliminated **14,510 sorting operations**, cutting search execution runtime by **20.41%** (from 201.33s to 160.23s) and increasing effective search throughput from 6,217 NPS to 7,815 NPS (**+25.7% NPS gain**).
- Tactical and endgame positions exhibited over **21% runtime reductions** due to first-move cutoff rates exceeding 80–85%.

### B. Decision-Quality Preservation (Phase G)
- Under fixed-time constraints (50ms to 3000ms), Candidate L1 exhibited high practical move agreement with K0 (mean agreement: 96.6%).
- Alignment with Stockfish 19 reference moves was identical or slightly superior to K0 (13/37 matches for L1 vs 12/37 for K0 at 3000ms budget).

### C. Controlled Playing-Strength Evidence (Phase H)
- In the 50-game head-to-head match qualification against K0:
  - Score: K0 27.0 / 50 (54.0%), L1 23.0 / 50 (46.0%)
  - Mean paired delta: -0.1600 points per opening pair
  - Paired t-statistic: -1.1628 ($p = 0.2562$, two-tailed)
  - 95% Pair-Bootstrap Confidence Interval: `[-0.4400, +0.0800]` points per pair
- Because the 95% confidence interval spans zero, the playing strength difference is not statistically significant. However, because Candidate L1 did not demonstrate statistically significant playing strength superiority over K0, promoting it to default production status (Category A) would violate the project's empirical charter.

---

## 3. Production Deployment Rules

1. `JanusSearch` defaults to `enable_lazy_move_selection = False`.
2. When `enable_lazy_move_selection = False`, search execution executes the clean eager-sorting path with zero generator overhead.
3. Candidate L1 can be activated at runtime via `--enable-lazy-move-selection` for fixed-depth research, high-throughput analysis, or resource-constrained benchmarking.
4. All 473 tests in the Project Janus regression test suite pass cleanly.

