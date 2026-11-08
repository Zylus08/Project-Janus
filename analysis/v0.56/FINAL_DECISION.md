# Project Janus v0.56 — Final Release Decision & Architectural Disposition

**Milestone:** Project Janus v0.56  
**Document Classification:** Milestone Closeout & Governance Disposition  
**Author:** Principal Chess Engine Research Architect & Independent Verification Lead  
**Date:** 2026-11-06  
**Repository Branch:** `v0.3-benchmark-harness`  
**Parent Commit:** `a80ba2a` (HEAD `f6025c3`)  
**Production Baseline:** Janus Native N5  
**Candidate Evaluated:** Janus Native N7 (N5 + Static Exchange Evaluation Capture Ordering)  

---

## 1. Executive Disposition Summary

| Criterion | Preregistered Requirement | Empirical Result | Gate Status |
| :--- | :--- | :--- | :---: |
| **Statistical Superiority** | $p < 0.05$ and lower 95% bootstrap Elo $> 0.0$ | $p = 0.2808$, 95% CI: [-43.66, +12.17] | **Failed (Category A Not Met)** |
| **Absence of Significant Regression** | $p \ge 0.05$ or score $\ge 48.0\%$ | $p = 0.2808$ (Null not rejected), Score: 47.75% | **Passed (Category B Satisfied)** |
| **Search Tree Compression** | Node reduction $> 5.0\%$ at Depth 6 | **-7.35% nodes** (6,519,414 vs 7,036,590) | **Passed** |
| **First-Move Cutoff Elevation** | Quantifiable ordering improvement | **+11.8%** (84.5% to 96.3% at Depth 6) | **Passed** |
| **Tactical Safety** | Zero dropped tactical solutions | **16/16 solved retained (100%), 0 dropped** | **Passed** |
| **Benchmark Move Agreement** | Move agreement $> 90\%$ | **64/64 (100.0%)** on tactical corpus | **Passed** |
| **Engine & Harness Stability** | 0 crashes, 0 stalls, 0 illegal moves | **0 crashes, 0 stalls, 0 illegal moves** (200 games) | **Passed** |

### **FORMAL RELEASE DISPOSITION: CATEGORY B — NEUTRAL RETENTION BEHIND UCI CONFIGURATION OPTIONS**

---

## 2. Governance Justification & Detailed Analysis

Under the strict scientific governance of Project Janus:
1. **Production Default Protection:** A candidate feature is granted production promotion (Category A) *only* when empirical playing-strength superiority is established with statistical significance ($p < 0.05$) under paired tournament controls. Because Candidate N7 achieved a score of $95.5 / 200$ ($47.75\%$, $t = -1.0844$, $p = 0.2808$), the null hypothesis cannot be rejected. Promoting N7 to production default would violate our evidence-based governance principles.
2. **Production Baseline Preservation:** The frozen production engine remains **Janus Native N5**:
   - `UseKillerOrdering = true`
   - `UseHistoryOrdering = true`
   - `UsePVS = false`
   - `UseLMR = true`
   - `UseSEEOrdering = false` (Default)
   - `UseSEEInQuiescence = false` (Default)
3. **Retention of Native SEE Subsystem:** Although capture ordering alone did not translate into a statistically significant Elo gain at fast blitz time controls, the native bitboard SEE implementation demonstrated exceptional search-theoretic qualities:
   - Evaluated up to 11.4 million exchanges with negligible runtime cost ($\approx 1.1\%$).
   - Successfully eliminated over **517,000 nodes (-7.35%)** at Depth 6 across 69 test positions.
   - Boosted first-move beta cutoffs by **+11.8 percentage points** (from 84.5% to 96.3%) by correctly demoting blundering captures below quiet killer moves.
   - Solved 100% of tactical positions with **-9.05% fewer nodes** and 100% move agreement.
   - Passed all 25/25 formal oracle tests with zero discrepancies against minimax truth.
4. **Strategic Role for Future Milestones:** SEE capture ordering was deliberately evaluated in isolation from SEE-based pruning. Pruning losing captures in quiescence search and main search is where engines typically realize massive playing-strength leaps. Having verified the mathematical correctness, bit-exact regression parity, and C++17 bitboard efficiency of SEE in v0.56, this subsystem is permanently retained as an experimental UCI feature, serving as the essential foundation for future pruning milestones.

---

## 3. Configuration & Deployment Instructions

The compiled C++17 engine executable (`analysis/v0.56/native/janus_native_engine.exe`) and shared library (`analysis/v0.56/native/janus_native.dll`) support the following UCI parameters:

| Option Name | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `UseKillerOrdering` | `check` | `true` | Enables 2-slot killer move quiet ordering |
| `UseHistoryOrdering` | `check` | `true` | Enables butterfly history heuristic table |
| `UsePVS` | `check` | `false` | Principal Variation Search (v0.55 Category B) |
| `UseLMR` | `check` | `true` | Late Move Reductions (v0.52 Category A) |
| `UseSEEOrdering` | `check` | **`false`** | **SEE-based capture ordering in main search (v0.56 Category B)** |
| `UseSEEInQuiescence` | `check` | **`false`** | **SEE-based capture ordering in quiescence search (v0.56 Category B)** |

Users and research harnesses can enable the v0.56 candidate at any time via:
```text
setoption name UseSEEOrdering value true
setoption name UseSEEInQuiescence value true
```
Production deployments remain at the audited, frozen N5 defaults.

