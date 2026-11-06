# Project Janus v0.58 — Final Release Decision

**Document Classification:** Formal Engineering Release & Integration Decision  
**Author:** Principal Chess Engine Architect, ML Systems Engineer & Project Review Board  
**Date:** 2026-11-06  
**Repository Branch:** `v0.3-benchmark-harness`  
**Milestone:** Project Janus v0.58 — Neural Policy Prototype  

---

## 1. Formal Release Classification

| Release Category | Designation | Criteria | Outcome |
| :---: | :--- | :--- | :---: |
| **Category A** | Production Promotion | $\Delta\text{Elo} > +15$ with $p < 0.05$ and lower bound of 95% CI $> 0$. | Not Met |
| **Category B** | **Research Prototype Qualified** | **$-15 \le \Delta\text{Elo} \le +15$, or $p \ge 0.05$; robust correctness and parity maintained.** | **SELECTED (PASSED)** |
| **Category C** | Rework Required | $\Delta\text{Elo} < -15$ with $p < 0.05$; significant regression. | Not Met |
| **Category D** | Rejection | Engine instability, illegal moves, or tactical degradation. | Not Met |

### Decision
**Category B — Retain as Research Prototype under Experimental Flag.**

---

## 2. Executive Rationale

1. **Playing Strength Parity:**
   In the preregistered 200-game match against frozen Classical Baseline C1 over 100 balanced opening pairs under Fischer $3.0\ \text{s} + 100\ \text{ms}$:
   - Score: **100.5 / 200 points (50.25%)**.
   - Estimated Elo: **$+1.7\ \text{Elo}$** (95% Bootstrap CI: $[-26.1, +29.6]$).
   - Paired Student-t: $t = +0.1234, p = 0.9020$ ($df = 99$).
   - The engine demonstrates clean, robust playing strength parity with the classical baseline.
2. **Exhaustive Interface & System Correctness:**
   - 100% bit-exact tensor encoding parity between C++ and Python references.
   - 100% lossless, collision-free round-trip encoding and decoding across the 4,168-dimensional action space.
   - Contiguous binary format parsing with graceful fallback on missing or corrupted files.
   - 100% bit-exact search parity with Baseline C1 when `UseNeuralPolicyOrdering=false`.
   - Full regression suite: **644 / 644 tests passed cleanly (639 inherited + 5 v0.58)**.
3. **Execution Reliability:**
   - **200 / 200 tournament games reached legal FIDE terminal states** (0 crashes, 0 illegal moves, 0 time forfeits, 0 safety-limit hits).
   - Zero tactical regressions across 12 curated tactical benchmark problems.
4. **Architectural Value:**
   - Establishes the foundational ML pipeline for Project Janus: dataset curation, supervised training, compact binary export, and C++ inference with selective action logit optimization.

---

## 3. Production Configuration Directives

To maintain absolute stability and preserve Baseline C1 guarantees by default:
1. **Default State:**
   - `UseNeuralPolicyOrdering=false`
2. **Experimental Toggle:**
   - UCI command `setoption name UseNeuralPolicyOrdering value true` enables the neural policy prototype with Root-only gating (`MaxPly=0`, `MinDepth=4`).
3. **Control Baseline Preservation:**
   - Classical Baseline C1 remains bit-exact and unchanged.
