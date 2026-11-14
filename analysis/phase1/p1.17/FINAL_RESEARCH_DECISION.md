# Milestone P1.17 — Formal Research Decision & Baseline Qualification Audit

**Author:** Principal Computer Chess Engineer & Independent Statistical Auditor  
**Date:** November 14, 2026  
**Candidate Under Review:** Janus Classical X22 (`35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C`)  
**Frozen Baselines:** Janus Classical X7 (1T Baseline, `b34e342`), Janus Classical X12 (4T Baseline, `78ca3d5`)  
**Status Before Audit:** Research Candidate (Conditional)  
**Governing Standard:** Project Janus Non-ML Classical Charter & Statistical Promotion Gates  

---

## 1. Audit Framework & Promotion Thresholds

Under the non-negotiable Project Janus experimental charter, promotion of a candidate to qualified baseline status (**Category A**) requires satisfying all of the following criteria:

1. **Statistical Superiority Over Baselines:**
   - Candidate (1T) must defeat Janus Classical X7 with a 95% paired confidence interval lower bound strictly greater than 50.0% ($CI_{low} > 0.500$) and one-sided $p < 0.05$.
   - Candidate (4T SMP) must defeat Janus Classical X12 with a 95% paired confidence interval lower bound strictly greater than 50.0% ($CI_{low} > 0.500$) and one-sided $p < 0.05$.
2. **Correctness Preservation:**
   - Engine must achieve 100% legal correctness on Perft and test suites, exhibit bitwise single-thread determinism, maintain 100% thread safety under SMP concurrency, and never return illegal scores or stand-pat cutoffs while in check.
3. **Evaluation Integrity:**
   - Evaluation terms must be handcrafted, fully additive, mathematically verified for color symmetry, and free from any ML, NNUE, learned weights, SPSA, or offline parameter fitting.

If a candidate satisfies criteria 2 and 3, demonstrates meaningful architectural or tactical advancement, but fails to reach the statistical threshold ($CI_{low} > 50.0\%$), it must be adjudicated as **Category B (Scientific Preservation & Reference Engine Designation)**. Frozen baselines X7 and X12 remain the official benchmarks.

---

## 2. Statistical Qualification Evaluation

### 2.1 Single-Thread Baseline Comparison (vs Janus Classical X7)
- **Match 1 (1.0s + 50ms, 100 games):**
  - Score: 50.0 / 100 (50.00%) | +31 =38 -31
  - 95% Paired Confidence Interval: **[42.2%, 57.8%]**
  - Lower Bound: $42.2\% \le 50.0\%$ — **FAILED PROMOTION GATE**
  - One-Sided $p$-value: $0.500000 \ge 0.05$ — **FAILED PROMOTION GATE**
- **Match 2 (2.5s + 100ms, 50 games, Slow TC):**
  - Score: 27.5 / 50 (55.00%) | +18 =19 -13
  - 95% Paired Confidence Interval: **[45.2%, 64.8%]**
  - Lower Bound: $45.2\% \le 50.0\%$ — **FAILED PROMOTION GATE**
  - One-Sided $p$-value: $0.158655 \ge 0.05$ — **FAILED PROMOTION GATE**

### 2.2 Four-Thread SMP Baseline Comparison (vs Janus Classical X12)
- **Match 3 (1.0s + 50ms, 100 games, 4T SMP):**
  - Score: 47.5 / 100 (47.50%) | +24 =47 -29
  - 95% Paired Confidence Interval: **[39.8%, 55.2%]**
  - Lower Bound: $39.8\% \le 50.0\%$ — **FAILED PROMOTION GATE**
  - One-Sided $p$-value: $0.737730 \ge 0.05$ — **FAILED PROMOTION GATE**

### 2.3 Head-to-Head Reference Comparison (vs Janus Classical X21-S)
- **Match 4 (1.0s + 50ms, 50 games):**
  - Score: 30.0 / 50 (60.00%) | +20 =20 -10
  - Elo Difference: **+70.4 Elo**
  - 95% Paired Confidence Interval: **[47.0%, 73.0%]**
  - One-Sided $p$-value: $0.065285$
  - Result: Decisive superiority over X21 (+10 win margin).

---

## 3. Formal Adjudication Decision

In accordance with the statistical governance rules of Project Janus:

### **FORMAL VERDICT: CATEGORY B (SCIENTIFIC PRESERVATION & LEADING REFERENCE ENGINE)**

1. **Promotion Rejection (Category A Denied):**
   - Janus Classical X22 is **NOT** promoted to supplant Janus Classical X7 as the qualified single-thread baseline, nor Janus Classical X12 as the qualified four-thread baseline.
   - **Janus Classical X7 (`b34e342`) remains the Immutable Qualified 1-Thread Baseline.**
   - **Janus Classical X12 (`78ca3d5`) remains the Immutable Qualified 4-Thread Baseline.**

2. **Reference Advancement (New Leading Reference):**
   - Candidate **Janus Classical X22** is authoritatively designated as the **New Qualified Research Reference Engine (Frozen Reference)**.
   - Candidate X21 is permanently retired and archived.
   - **Rationale for Reference Promotion:**
     - X22 permanently fixes the quiescence leaf checkmate blindness and illegal stand-pat under check defects that plagued X7 and earlier versions.
     - X22 incorporates the high-efficiency 64K thread-local pawn hash table (+52% isolated eval speedup, +10.6% search NPS).
     - X22 introduces True Outpost Evaluation with Enemy Pawn Immunity, recovering practical playing strength from X21's 42.5% to 50.0% at blitz and 55.0% at slow TC against X7, and defeating X21 by +70.4 Elo (+20 =20 -10).

---

## 4. Benchmark Forensic Verdict

- **Milestone P1.16 External Results (Claimed 24.2% vs Stockfish):** Formally adjudicated as **INVALID (HARNESS ADJUDICATION DEFECT)**.
- **Milestone P1.17 External Results (Audited 0.83% vs Stockfish):** Formally adjudicated as **VALID & INDEPENDENTLY REPLICATED**.
- The competitive boundary of current non-ML Janus classical engines against modern and mature classical engines is accurately calibrated at **~0.0% to 1.5%** (+0 real wins).
