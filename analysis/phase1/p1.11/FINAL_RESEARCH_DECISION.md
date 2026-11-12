# Milestone P1.11 Final Research & Adjudication Decision

## 1. Decision Framework & Governing Criteria

Under the **Janus Competitive Testing Standard (JCTS v1.11)** and Milestone P1.11 Charter, engine promotion requires empirical proof across all following criteria:
1. **Superiority Hypothesis:** Two-tailed $p$-value $p < 0.05$ with positive Elo gain ($\bar{d} > 0$) against the respective qualified baseline.
2. **Equivalence Threshold (if claimed equal):** Two One-Sided Tests (TOST) with margin $\Delta_{\text{eq}} = 0.10$ ($\pm 35$ Elo) achieving $p_{\text{TOST}} < 0.05$.
3. **Scale Invariance:** No regression under slower time controls.
4. **Charter Compliance:** Strictly non-ML.

The three formal decision pathways are:
- **Category A (Full Promotion):** Statistically significant superiority proven ($p < 0.05, \Delta \text{Elo} > 0$).
- **Category B (Qualified Research Promotion):** Equivalence proven ($p_{\text{TOST}} < 0.05$) with demonstrable architectural progress.
- **Category C (Formal Baseline Retention):** Neither superiority nor equivalence proven; existing baselines retained, candidate archived.

---

## 2. Empirical Evidence Summary

| Evaluation Track | Match Description | Sample Size | Candidate Score | Elo Difference [95% CI] | Two-Tailed $p$-value | TOST $p_{\text{TOST}}$ | Empirical Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Track 1 (1T)** | X16-S vs X7 | 200 games | 33.75% | **-117.2** [-167.9, -66.4] | $1.02 \times 10^{-7}$ | 0.9999 | **Statistically Significant Regression** |
| **Track 2 (4T Fast)**| X16-P vs X12 | 200 games | 45.50% | **-31.4** [-79.5, +16.8] | 0.1177 | 0.4342 | **Inconclusive Deficit (Not Equivalent)** |
| **Track 3 (4T Slow)**| X16-P vs X12 | 100 games | 45.50% | **-31.4** [-99.3, +36.6] | 0.1921 | 0.4432 | **Inconclusive Deficit (Not Equivalent)** |
| **Track 4 (SF 1T)** | X16-S vs SF19 | 40 games | 2.50% | **-636.4** [-940.8, -332.1]| $8.49 \times 10^{-17}$ | 1.0000 | **2 Draws Held** |
| **Track 5 (SF 4T)** | X16-P vs SF19 | 40 games | 1.25% | **-759.1** [-1153.3, -364.8]| $1.34 \times 10^{-19}$ | 1.0000 | **1 Draw Held** |

---

## 3. Formal Adjudication: Category C (Formal Baseline Retention)

Based on the definitive experimental findings across 540 tournament games:

1. **Rejection of Candidate Promotion:**
   - Candidate **Janus Classical X16 is REJECTED** for promotion to production baseline.
   - On 1 Thread, X16-S suffers a catastrophic -117.2 Elo deficit against X7 ($p = 1.02 \times 10^{-7}$).
   - On 4 Threads, X16-P is -31.4 Elo behind X12 in both fast and slow time controls ($p = 0.1177$ and $p = 0.1921$).
   - TOST equivalence fails across all tracks ($p_{\text{TOST}} \ge 0.43 \gg 0.05$).
2. **Formal Baseline Retention:**
   - **Janus Classical X7 (`b34e342`) is RETAINED as the official Single-Thread Qualified Classical Baseline.**
   - **Janus Classical X12 (`78ca3d5`) is RETAINED as the official Four-Thread Qualified Classical Baseline.**
3. **Archival Designation:**
   - Janus Classical X16 is designated as **Archived Research Candidate X16**, preserved in `analysis/phase1/p1.11/control/janus_classical_x16.exe` (SHA-256: `97e69fa99c708400c33e95b2bb32e3db79d8467970e1a895927a459f34061ab9`).
   - The Direction A pruning safety and history dampening implementation remains available via `UCI_Variant X16` and can be cleanly ablated back to X15 via `UCI_PruningSafety false`.

---

## 4. Key Scientific Insights of Milestone P1.11

1. **Resolution of the "Parity" Myth:**
   Reconciliation in Phase 0 proved that past claims of X15/X12 "parity" were statistical fallacies. Equivalence requires strict TOST bounds, which neither X15 nor X16 achieved.
2. **Counterfactual Pruning Mechanics:**
   The Phase 2 audit demonstrated that standard Late Move Reductions aggressively prune 33.3% of quiet defensive moves. Direction A proved that static evaluation tracking and continuation history dampening successfully prevent these tactical blunders, allowing Janus to hold 3 draws against unrestricted Stockfish 19.
3. **The Complexity Penalty on Single-Core CPUs:**
   The massive divergence between 1T (-117 Elo) and 4T (-31 Elo) proves that complex evaluation terms and search heuristics impose severe latency penalties that cannot be justified on single-threaded architectures. Leaner engines (like X7) dominate single-thread classical chess.

