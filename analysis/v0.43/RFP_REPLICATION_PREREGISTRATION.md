# Project Janus v0.43 — RFP Replication Preregistration (Phase D)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Document Type:** Formal Preregistration Protocol  
**Date:** 2026-11-03  
**Status:** PREREGISTERED & FROZEN (Committed Prior to Replication Execution)  

---

## 1. Research Question & Primary Objective

Does the playing strength advantage of Reverse Futility Pruning (RFP) reported in v0.42 ($\bar{\Delta} = +0.58\text{ pts/pair}$, $t = 2.7682$, $p = 0.0053$) replicate in an independent, colour-balanced, matched ablation against Baseline K0 using an expanded master opening suite under strictly controlled Fischer time controls?

---

## 2. Experimental Design & Treatment Arms

### 2.1 Experimental Unit
The experimental unit is a **colour-reversed opening pair**. Each opening position is played twice by each engine against the calibrated benchmark opponent (Stockfish 19 Elo 1320):
1. **White game:** Janus plays White, Stockfish 19 plays Black.
2. **Black game:** Stockfish 19 plays White, Janus plays Black.

Each engine receives a pair score $S_i \in \{0.0, 0.5, 1.0, 1.5, 2.0\}$ representing the sum of points scored across the White and Black game of pair $i$.

### 2.2 Primary Outcome Measure
For each opening pair $i$:
$$\Delta_i = S_{\text{RFP}, i} - S_{\text{K0}, i}$$
where $\Delta_i \in \{-2.0, -1.5, -1.0, -0.5, 0.0, +0.5, +1.0, +1.5, +2.0\}$.

The primary treatment effect is the sample mean of paired differences:
$$\bar{\Delta} = \frac{1}{N}\sum_{i=1}^N \Delta_i$$

### 2.3 Primary Hypotheses & Significance Threshold
- **Null Hypothesis ($H_0$):** The expected paired difference between Candidate RFP and Baseline K0 is non-positive:
  $$H_0: \mu_\Delta \le 0$$
- **Alternative Hypothesis ($H_1$):** Candidate RFP scores higher than Baseline K0:
  $$H_1: \mu_\Delta > 0$$
- **Significance Criterion:** One-tailed Student's paired $t$-test at $\alpha = 0.05$ (df = $N - 1$). The two-tailed $p$-value and 95% confidence interval will also be reported.

---

## 3. Sample Size and Stopping Policy

- **Target Sample Size:** Up to $N = 100$ complete colour-reversed opening pairs (200 games per engine arm, 400 games total), or the maximum completed cohort if constrained by computational time budget.
- **Resource Boundary:** In the event of execution time exhaustion, all completed pairs will be preserved without exclusion, the stopping point will be reported, and the achieved sample size will be analyzed with documented statistical precision.
- **No Early Stopping for Significance:** The match will not be stopped early based on sequential inspection of intermediate $p$-values.

---

## 4. Frozen Opening Suite Manifest

- **Suite File:** `analysis/v0.43/openings_v043_100.json`
- **Total Openings:** 100 distinct ECO master openings (50 classical base openings + 50 newly curated, balanced master lines).
- **Opening Independence:** 100 unique opening positions without reuse.
- **Cryptographic Digest (SHA-256):**
  `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b`

---

## 5. Statistical Analysis Methodology

1. **Primary Parametric Test:** Paired Student's $t$-test on $\vec{\Delta}$:
   $$t = \frac{\bar{\Delta}}{s_\Delta / \sqrt{N}}$$
2. **Confidence Interval:** Parametric 95% confidence interval for $\mu_\Delta$:
   $$\bar{\Delta} \pm t_{N-1, 0.025} \times \frac{s_\Delta}{\sqrt{N}}$$
3. **Non-Parametric Bootstrap:** 10,000 resamples of complete opening pairs to generate a 95% percentile confidence interval. Resampling unit is the complete pair vector $(\Delta_i)$, never individual games.
4. **Subgroup Telemetry:** W/D/L distribution, White score vs Black score, completed search depth, and move-time consumption.

---

## 6. Exclusion and Retry Policy

- **Valid Exclusions:** Technical crashes, protocol timeouts, unrecoverable I/O failures, or corrupted PGNs.
- **Prohibited Exclusions:** Games cannot be excluded due to tactical errors, checkmates, or unfavorable game outcomes.
- **Retry Policy:** Up to 3 automatic retries per slot. Both the failed attempt and replacement game must be logged in `attempt_log.json`.
- **Integrity Validation:** Every completed game must be verified for 100% legal moves via `python-chess`.

