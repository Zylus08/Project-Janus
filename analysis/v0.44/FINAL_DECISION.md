# Final Engineering & Production Decision — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Auditor:** Autonomous Senior Chess-Engine Researcher & Search Algorithm Engineer  
**Final Production Decision:** **CATEGORY B**

---

## 1. Decision Category Selection

Per the Project Janus v0.44 mandate, exactly one decision category must be selected:

> ### **CATEGORY B: RFP is theoretically sound and provides substantial search efficiency, but exhibits structural vulnerabilities in sharp defensive contexts that require specific algorithmic refinement prior to production qualification.**
> **Production Default:** `enable_rfp = False` (Baseline K0 remains the production standard).  
> **Experimental Status:** RFP remains experimental and disabled by default.

---

## 2. Empirical & Theoretical Justification

This decision is backed by four independent lines of scientific evidence established during v0.44:

1. **Exact Parity in Controlled Fixed-Depth Search (Zero Blunders):**
   - Counterfactual search experiments on 37 critical diagnostic positions ([`analysis/v0.44/COUNTERFACTUAL_ANALYSIS.md`](file:///E:/ChessXML/project-janus/analysis/v0.44/COUNTERFACTUAL_ANALYSIS.md)) established that under identical search horizons, RFP chose the **exact same best move** as K0 in $100\%$ of cases ($37/37$).
   - RFP delivered an average node reduction of $10.2\%$ (reaching up to $42.8\%$), with zero Category 4 or Category 5 tactical regressions.

2. **Resolution of Match Timing Anomaly:**
   - Forensic audit of 32,826 match plies ([`analysis/v0.44/SEARCH_EFFICIENCY_AUDIT.md`](file:///E:/ChessXML/project-janus/analysis/v0.44/SEARCH_EFFICIENCY_AUDIT.md)) proved that both engines received identical compute budgets ($144.55\text{ ms}$ vs $145.46\text{ ms}$ trimmed mean; $143.5\text{ ms}$ vs $144.7\text{ ms}$ median).
   - Match move divergences were caused by iterative deepening boundary cutoffs under shallow Fischer timing ($180\text{ ms}$ allocation), not static pruning blunders.

3. **Taxonomic Stratification Identifies the Failure Mode:**
   - Stratification across 100 opening pairs ([`analysis/v0.44/STRATIFICATION_ANALYSIS.md`](file:///E:/ChessXML/project-janus/analysis/v0.44/STRATIFICATION_ANALYSIS.md)) revealed that RFP outperformed K0 in Closed, Flank, and Indian openings ($+3.0$ game points across 65 pairs).
   - The entire net deficit of RFP was isolated to a single tactical vulnerability: **Black defending against 1.e4 in Semi-Open structures** (French, Sicilian, Caro-Kann), where static evaluation overestimates Black's safety and shallow margins ($120\text{ cp}$) prune necessary defensive calculation.

4. **Preservation of Sound Production Architecture:**
   - Baseline K0 remains the production default.
   - Non-intrusive diagnostic telemetry (`diagnostic_rfp`, `--diag-rfp`) has been integrated with zero performance overhead when disabled, enabling precise forensic telemetry for future search tuning.

---

## 3. Mandatory Operating Status for Janus v0.44+

- `JanusSearch` defaults `enable_rfp = False`.
- `janus.uci` defaults `enable_rfp = False`.
- RFP is available via `--enable-rfp` for research and experimental benchmarking.
- All 456 unit tests pass.

