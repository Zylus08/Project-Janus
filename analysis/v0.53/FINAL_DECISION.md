# PROJECT JANUS v0.53 — FINAL DISPOSITION & RELEASE DECISION

**Milestone:** v0.53 — Principal Variation Search, Window Correctness & Controlled Strength Ablation  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N4 (`UsePVS=true`, `UseLMR=true`)  
**Baseline Engine:** Janus Native N3 (`UsePVS=false`, `UseLMR=true`)  
**Decision Classification:** **CATEGORY B — Search-Efficiency Qualified, Strength-Neutral / Codebase Integration with Baseline Default Retained (`UsePVS=false`)**  

---

## 1. Decision Criteria & Evidentiary Findings

Under Project Janus governance, a candidate search algorithm must be evaluated across three tiers of evidence:

```
Tier 1: Implementation Correctness & Invariant Preservation
Tier 2: Algorithmic Efficiency & Tree Pruning
Tier 3: Empirical Playing Strength under Controlled Tournament Conditions
```

### 1.1 Tier 1: Invariant Correctness (PASS)
- **Unit Test Suite:** 30 / 30 tests passed (`test_native_pvs_semantics.py`).
- **Mathematical Equivalence:** Pure PVS (`N2+PVS`) matched standard alpha-beta (`N2`) on **53 / 53 moves (100.0%)** across Depths 3, 4, 5, and 6.
- **Tactical Safety:** Evaluated across 48 positions (12 tactical regression, 16 validation, 20 independent tactical). N4 matched N3 on **48 / 48 moves (100.0%)** with **zero dropped solutions**.
- **Adjudication Integrity:** 200 / 200 match games terminated cleanly under sound FIDE rules with zero illegal moves, forfeits, crashes, or emergency horizon hits. All 120 threefold repetitions were independently audited and verified.

### 1.2 Tier 2: Algorithmic Efficiency (PASS)
- **Node Reduction:** N4 reduced Depth 6 search nodes by **9.89%** over N3 (and by **66.73%** over N2).
- **Wall-Clock Speedup:** N4 delivered a **1.21x speedup** at Depth 6 over N3.
- **Fixed-Time Scaling:** N4 achieved systematic nominal depth gains of up to **+0.44 plies** in complex middlegame positions.
- **Re-Search Overhead:** Null-window re-searches occurred on only **0.076%** of searches at Depth 6, and **0.02%** at 3000ms fixed time, confirming superior move ordering.

### 1.3 Tier 3: Empirical Playing Strength (NEUTRAL / PARITY)
- **Preregistered Match Result:** 97.5 / 200 (48.75%, +36 =123 -41).
- **Paired $t$-Test:** $t = -0.5754$, $df = 99$, **$p = 0.5663$**.
- **Bootstrap 95% Confidence Interval:** $[-38.4, +20.9]$ Elo.
- **Conclusion:** The Elo difference of $-8.7$ is statistically indistinguishable from zero ($p \gg 0.05$). Under Fischer 3.0s + 100ms, PVS confers search-tree efficiency but does not produce a statistically significant playing-strength improvement.

---

## 2. Category Assessment & Selection

Project Janus establishes four definitive release categories:

- **Category A (Promote to Production Default):** Statistically significant playing-strength improvement ($p < 0.05$, CI lower bound $> 0$).  
  *Assessment: NOT MET. The strength gain is not statistically significant ($p = 0.5663$).*
- **Category B (Codebase Integration, Retain Baseline Default):** Search efficiency improvement and correctness verified, but playing strength is statistically indistinguishable from baseline (parity / neutral, $p \ge 0.05$, CI encompasses zero, no significant regression). Feature retained in native engine as a configurable UCI option (`UsePVS=false` default), fully tested, and qualified for future search architectures.  
  *Assessment: **MET IN FULL**.*
- **Category C (Neutral / Indeterminate with Regressions Requiring Rework):** Correctness flaws, dropped tactical solutions, or implementation defects.  
  *Assessment: NOT APPLICABLE. Zero regressions, 100.0% move agreement, 0 dropped tactics.*
- **Category D (Reject):** Statistically significant playing-strength regression ($p < 0.05$, CI upper bound $< 0$) or severe architectural flaws.  
  *Assessment: NOT APPLICABLE. No statistically significant regression observed.*

---

## 3. Formal Verdict & Action Plan

1. **Production Engine Default:** The production default configuration of Janus remains **Native N3** (`UseLMR=true`, `UsePVS=false`).
2. **Codebase Integration:** PVS remains fully integrated into `analysis/v0.53/native/janus_native.cpp` and `janus_native_engine.exe` as a verified, supported UCI option (`option name UsePVS type check default false`).
3. **Engineering Justification:** PVS provides proven ~10% tree pruning and 1.21x speedup at higher depths, with a sub-0.1% re-search rate. Retaining PVS in the codebase provides the foundational window-search infrastructure required for upcoming search enhancements (such as aspiration windows, null-move pruning, and dynamic LMR) where narrow window probing is essential.
4. **Git Operations:** The local repository state is clean, verified, and committed. Zero remote pushes performed.

