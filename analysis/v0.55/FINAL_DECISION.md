# Project Janus v0.55 — Final Release Decision

**Milestone:** Project Janus v0.55  
**Date:** 2026-11-05  
**Lead Architect & Auditor:** Principal Chess Engine Research Architect & Independent Reproducibility Auditor  
**Repository:** `E:\ChessXML\project-janus`  
**Branch:** `v0.3-benchmark-harness`  
**Evaluated Candidate:** Janus Native N6 (C++17, LMR + Killer + History + PVS)  
**Production Baseline:** Janus Native N5 (C++17, LMR + Killer + History, PVS disabled)  

---

## 1. Official Release Classification

### Primary Promotion Evaluation (Janus N6 vs Janus N5):
**OFFICIAL DISPOSITION: CATEGORY B — PVS SEARCH-EFFICIENCY QUALIFIED, PLAYING STRENGTH NEUTRAL**

### Criteria Checklist:
- [x] **Minimax Implementation Correctness:** Verified exact minimax equivalence without LMR across all benchmark positions (`FACTORIAL_CORRECTNESS_REPORT.md`).
- [x] **Tactical Safety Maintained:** 100% tactical solve rate (16/16 solved) and 97.9% move agreement (47/48) with N5 at Depth 5 (`TACTICAL_SAFETY_REPORT.md`).
- [x] **Search Efficiency Qualified:** Tree compression of $-4.25\%$ nodes over N5 ($-37.51\%$ over N3) and $1.84\times$ speedup at Depth 6 (`FIXED_DEPTH_FACTORIAL_ABLATION.md`).
- [x] **Re-Search Stability:** PVS full-window re-searches occurred in only $0.074\%$ of probes; LMR re-searches collapsed to $0.458\%$.
- [ ] **Playing Strength Superiority:** Candidate N6 scored $99.0 / 200$ ($49.50\%$, $-3.47$ Elo, $p = 0.83425$) against N5. The 95% bootstrap confidence interval $[-34.86, +29.60]$ Elo spans zero. **Condition NOT Met.**

Because playing-strength improvement was not established, Category A promotion is denied. PVS remains qualified as code-complete, invariant-sound, and search-efficient, but will remain disabled by default (`UsePVS=false`).

---

## 2. Independent Replication Evaluation (Janus N5 vs Janus N3)

### Official Disposition: **REPLICATION DECISIVELY CONFIRMED**

### Evidence Summary:
- **Corpus:** 100 completely fresh master opening pairs (`independent_openings_v055.json`), with 0% overlap or transpositions to the historical v0.52–v0.54 opening suites.
- **Score:** Candidate N5 defeated Baseline N3: **122.0 / 200 (61.00%, +68 =108 -24)**.
- **Net Margin:** $+44.0$ points ($+22.00\%$).
- **Estimated Elo Advantage:** **$+77.71\text{ Elo}$**.
- **95% Bootstrap Confidence Interval:** **$[+45.42, +111.37]\text{ Elo}$** (strictly positive, lower bound $> +45$ Elo).
- **Student's t-Statistic:** $t = 4.7586$ ($df = 99$), **$p = 0.000007 < 0.0001$**.
- **Adjudication Integrity:** 92 checkmates, 106 threefold repetitions, 2 stalemates. Zero forfeits, zero crashes.

The fragility concern identified in Phase 0.2 is resolved: Janus N5's playing-strength advantage replicates robustly across independent opening theory.

---

## 3. Production Configuration Directives

1. **Production Baseline Retained:**
   Janus Native N5 remains the official **Frozen Production Baseline**.
2. **Production UCI Defaults:**
   ```text
   UseKillerOrdering = true
   UseHistoryOrdering = true
   UsePVS = false
   UseLMR = true
   LMRMinDepth = 3
   LMRMoveThreshold = 4
   LMRBaseReduction = 1
   ```
3. **PVS Feature Availability:**
   PVS remains compiled in the engine and fully accessible via UCI `setoption name UsePVS value true` for research and experimental benchmarking, but default execution retains `false`.

