# Project Janus v0.58 — Tournament Preregistration Document

**Milestone:** Project Janus v0.58 — Neural Policy Prototype  
**Experiment:** Preregistered Playing-Strength Tournament: Candidate N8-A vs Classical Baseline C1  
**Classification:** Scientific Preregistration & Methodological Invariant Specification  
**Date:** 2026-11-06  
**Repository Branch:** `v0.3-benchmark-harness`  
**Anchor Parent Commit:** `2b24d13`  

---

## 1. Primary Research Question

> Under identical hardware, time controls (Fischer 3.0s + 100ms), and opening conditions, does learned grandmaster move-ordering guidance at the root node (Janus Neural N8-A) improve engine playing strength or preserve parity with the frozen classical baseline (Janus Classical C1)?

---

## 2. Experimental Protocol & Invariants

1. **Tournament Size:** Exactly 200 games across 100 balanced opening pairs from `analysis/v0.56/corpus/independent_openings_v056.json`.
2. **Color Balance:**
   - Game $2i-1$: Candidate N8-A plays White, Baseline C1 plays Black.
   - Game $2i$: Baseline C1 plays White, Candidate N8-A plays Black.
3. **Time Control:** Fischer $3.0\ \text{s} + 100\ \text{ms}$ per move. Time allocations and increments strictly managed by the native engine and tournament controller.
4. **Adjudication Standards:**
   - FIDE Article 1.2: Checkmate ($1-0$ / $0-1$).
   - FIDE Article 5.2.1: Stalemate ($1/2 - 1/2$).
   - FIDE Article 5.2.2 / 9.6: Insufficient Material ($1/2 - 1/2$).
   - FIDE Article 9.2: Claimable Threefold Repetition ($1/2 - 1/2$).
   - FIDE Article 9.6.1: Mandatory Fivefold Repetition ($1/2 - 1/2$).
   - FIDE Article 9.3: Claimable 50-Move Rule ($1/2 - 1/2$).
   - FIDE Article 9.6.2: Mandatory 75-Move Rule ($1/2 - 1/2$).
   - Emergency Safety Cap: 300 plies ($1/2 - 1/2$, logged as `safety_limit_300_plies`).
5. **Engine Configurations:**
   - **Candidate N8-A:**
     `analysis/v0.58/native/janus_native_engine.exe`
     `UseNeuralPolicyOrdering=true`
     `NeuralPolicyModelPath="analysis/v0.58/models/janus_policy_v1.bin"`
     `NeuralPolicyMaxPly=0`
     `NeuralPolicyMinDepth=4`
     `NeuralPolicyScoreWeight=50000`
     `UseKillerOrdering=true`, `UseHistoryOrdering=true`, `UseLMR=true`, `UsePVS=false`, `UseSEEOrdering=false`, `UseSEEInQuiescence=false`.
   - **Control Baseline C1:**
     `analysis/v0.56/native/janus_native_engine.exe` (Frozen v0.57 baseline)
     `UseKillerOrdering=true`, `UseHistoryOrdering=true`, `UseLMR=true`, `UsePVS=false`, `UseSEEOrdering=false`, `UseSEEInQuiescence=false`.
6. **Hardware & Execution:**
   - Identical host execution environment with 8 parallel worker processes.
   - Zero remote network dependencies.

---

## 3. Statistical Analysis Plan

1. **Primary Metric:** Net Score ($W + 0.5 \times D$) and Win Percentage.
2. **Paired Unit of Analysis:** The paired difference per opening:
   $$\Delta_i = S_{N8}(i) - S_{C1}(i) \in \{-2.0, -1.5, -1.0, -0.5, 0.0, +0.5, +1.0, +1.5, +2.0\}$$
   across $N = 100$ independent opening pairs.
3. **Hypothesis Testing:**
   - Null Hypothesis $H_0: \mu_\Delta = 0$ (No difference in playing strength).
   - Alternative Hypothesis $H_1: \mu_\Delta \neq 0$ (Two-sided test, $\alpha = 0.05$).
   - Paired Student's t-test with $df = 99$.
4. **Estimation:**
   - 95% Bootstrap Confidence Interval ($B = 10,000$ paired resamples).
   - Elo advantage estimation: $\Delta\text{Elo} = -400 \log_{10}(1/P - 1)$.

---

## 4. Release Decision Categories

- **Category A (Promote Neural Policy Ordering):**
  $\Delta\text{Elo} > +15$ with $p < 0.05$ and lower bound of 95% CI $> 0$.
- **Category B (Retain as Research Prototype / Experimental Flag):**
  $-15 \le \Delta\text{Elo} \le +15$, or $p \ge 0.05$ (neutral playing strength, functional prototype qualified).
- **Category C (Rework Policy / Search Integration):**
  $\Delta\text{Elo} < -15$ with $p < 0.05$ (statistically significant regression due to inference latency or move selection).
- **Category D (Reject):**
  Catastrophic engine instability, illegal moves, or unrecoverable tactical degradation.
