# Final Engineering & Production Decision — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Auditor:** Autonomous Senior Chess-Engine Researcher & Search Algorithm Engineer  
**Final Production Decision:** **CATEGORY B**

---

## 1. Decision Category Selection

Per the Project Janus v0.45 mandate, exactly one decision category must be selected:

> ### **CATEGORY B: RFP improves search efficiency but practical decision benefit remains unconfirmed.**
> **Production Default:** `enable_rfp = False` (Baseline K0 remains the production standard).  
> **Experimental Status:** RFP remains experimental and disabled by default.

---

## 2. Empirical & Theoretical Justification

This decision is substantiated by five independent lines of empirical evidence established in v0.45:

1. **Established Search Efficiency in Fixed-Depth Search:**
   - Controlled paired fixed-depth experiments across depths 2, 3, 4, and 5 ([`analysis/v0.45/FIXED_DEPTH_ANALYSIS.md`](file:///E:/ChessXML/project-janus/analysis/v0.45/FIXED_DEPTH_ANALYSIS.md)) confirmed that RFP delivers an aggregate node reduction of **$10.60\%$ at depth 4** and **$9.19\%$ at depth 5** with $100.0\%$ move agreement ($148/148$ trials) and $0.0\text{ cp}$ score deviation.

2. **Resolution of Fixed-Time Move Divergences:**
   - In 259 fixed-time trials spanning budgets from $50\text{ ms}$ to $1,000\text{ ms}$ ([`analysis/v0.45/FIXED_TIME_ANALYSIS.md`](file:///E:/ChessXML/project-janus/analysis/v0.45/FIXED_TIME_ANALYSIS.md)), **100% of observed move divergences were Category A (Iteration-boundary divergences)**.
   - There was **0% Category B divergence**: whenever both configurations completed the same depth, they chose the identical best move in $100\%$ of cases.

3. **Unconfirmed Practical Decision Benefit Under Real Budgets:**
   - Across the budget ladder, RFP's mean completed depth ($2.02$ plies) did not exceed K0's mean completed depth ($2.03$ plies). A $\sim 10\%$ node reduction is too small to overcome the exponential $3.5\times$ branching threshold to reliably complete an extra iteration under tight Fischer timing ($180\text{ ms}$).
   - External decision quality evaluated against Stockfish 19 at depth 12 ([`analysis/v0.45/MOVE_STABILITY_ANALYSIS.md`](file:///E:/ChessXML/project-janus/analysis/v0.45/MOVE_STABILITY_ANALYSIS.md)) showed exact parity: $21.6\%$ agreement for K0 and $21.6\%$ for RFP.

4. **Resolution of Subgroup Reporting Ellipsis:**
   - The apparent discrepancy in the v0.44 narrative was formally reconciled ([`analysis/v0.45/V044_STRATIFICATION_RECONCILIATION.md`](file:///E:/ChessXML/project-janus/analysis/v0.45/V044_STRATIFICATION_RECONCILIATION.md)): the Non-Semi-Open total ($+3.0\text{ pts}$) plus the complete Semi-Open total ($-6.5\text{ pts}$, comprising $-1.0$ White and $-5.5$ Black) equals exactly the observed $-3.5\text{ pts}$.

5. **Search Invariant Verification:**
   - Automated tests ([`tests/test_v045_iteration_telemetry.py`](file:///E:/ChessXML/project-janus/tests/test_v045_iteration_telemetry.py)) proved that interrupted iterations never overwrite completed iteration results.

---

## 3. Production Status

- In `JanusSearch` and `janus.uci`, `enable_rfp = False` remains the hard-coded default.
- RFP remains available via `--enable-rfp` for experimental research.
- Promotion to production default is denied until a statistically significant playing strength gain is independently demonstrated in a controlled tournament replication.

