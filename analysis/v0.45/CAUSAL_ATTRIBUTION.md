# Causal Attribution & Architectural Recommendations — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Status:** COMPLETE

---

## 1. Evaluation of Core Scientific Hypotheses

| Hypothesis | Formulation | Empirical Evaluation | Verdict |
|---|---|---|---|
| **H1** | RFP changes iterative-deepening completion boundaries under constrained time budgets. | Demonstrated directly across the budget ladder in Phase F: at 100ms, 500ms, and 1000ms, RFP shifted the iteration completion boundary relative to K0. | **SUPPORTED** |
| **H2** | Completion-boundary changes explain a meaningful fraction of observed move divergences. | In Phase F, **100% of observed move divergences** (6/6) were classified as Category A (iteration-boundary divergences), while Category B (same-depth divergence) was **0%**. | **SUPPORTED** |
| **H3** | RFP's node reduction translates into a consistent completed-depth advantage. | Across the 259 fixed-time trials, mean completed depth was **$2.02$ plies for RFP vs $2.03$ plies for K0**. A $\sim 10\%$ node reduction is insufficient to overcome the exponential $3.5\times$ branching threshold to reliably complete an extra iteration. | **NOT SUPPORTED** |
| **H4** | Additional completed depth improves decision quality on the evaluated corpus. | Agreement with Stockfish 12 was identical between K0 ($21.6\%$) and RFP ($21.6\%$) at the $180\text{ ms}$ budget. While deeper nominal search expands tactical horizons, move choices flip in $29.7\%$ of iterations without yielding a decisive quality gain at $d \le 3$. | **INCONCLUSIVE** |

---

## 2. Investigation of Alternative Explanations

1. **Transposition Table Contamination:** Audited in Phase B; TT entries stored by interrupted iterations do not corrupt published root PVs or move selection.
2. **Move Ordering Artifacts:** Both configurations share identical MVV-LVA, killer, countermove, and quiet history heuristics.
3. **Host Latency & Execution Jitter:** Reconfirmed from Phase F; small system scheduling delays (a few milliseconds) near the deadline have a larger influence on whether iteration $d=3$ completes than the $\sim 10\%$ node reduction provided by RFP.

---

## 3. Architectural Recommendations

1. **Preserve Iterative Deepening Publication Invariant:**
   - The current implementation in `src/janus/search.py` (lines 1228–1234) guarantees that interrupted iterations never overwrite published completed moves. This design is sound and must be retained.
2. **Retain Baseline K0 as Production Default:**
   - Because RFP's node reduction does not deliver a consistent completed-depth advantage or superior move quality under realistic time constraints, RFP cannot be qualified as a default optimization.
3. **Retain RFP as Experimental Feature:**
   - Accessible via `--enable-rfp` for research and parameter tuning.

---

## 4. Production Decision

**Production Default:** `enable_rfp = False` (Baseline K0 remains default).  
**Experimental Status:** RFP remains experimental.

