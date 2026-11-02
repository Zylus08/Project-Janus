# Project Janus v0.42 — v0.41 Statistical Audit (Phase B)

**Milestone:** v0.42  
**Scope:** Independent statistical audit of all v0.41 quantitative claims  
**Auditor:** v0.42 Statistical Audit Engineer  
**Date:** 2026-11-02  

---

## 1. Audit Methodology

Each v0.41 statistical claim is independently verified:
1. By rerunning `scripts/audit_v041_pipeline.py` (confirmed: no changes to the pipeline or data)
2. By independent Python computation from the raw `attempt_log.json`
3. By analytic verification of statistical formulas

---

## 2. Raw Data Verification

**Source:** `analysis/v0.41/match_rfp/attempt_log.json`

| Item | v0.41 Claim | Independent Recount | Verdict |
|:---|:---:|:---:|:---:|
| Total records | 50 | 50 | ✓ MATCH |
| Completed games | 50 | 50 | ✓ MATCH |
| Infrastructure failures | 0 | 0 | ✓ MATCH |
| Wins | 33 | 33 | ✓ MATCH |
| Draws | 8 | 8 | ✓ MATCH |
| Losses | 9 | 9 | ✓ MATCH |
| Total score | 37.0 / 50 | 37.0 / 50 | ✓ MATCH |
| Score % | 74.0% | 74.000% | ✓ MATCH |

---

## 3. PGN Legality Audit

**Source:** `analysis/v0.41/match_rfp/match_results.pgn`

| Item | Value |
|:---|:---|
| Games parsed | 50 |
| Total plies | 4,671 |
| Illegal moves | **0** |
| Verdict | ✓ ALL MOVES LEGAL |

---

## 4. Clock Compliance Audit

**Source:** `analysis/v0.41/match_rfp/match_moves.csv`

| Item | Value |
|:---|:---|
| Total move rows | 4,671 |
| Negative clock readings | **0** |
| Verdict | ✓ CLOCK NON-NEGATIVE THROUGHOUT |

---

## 5. Paired Statistics Audit

### 5.1 Mean Pair Difference

The audit pipeline computes pair differences as:
```
diff_i = score_white_i + score_black_i - 1.0
```

This centers on expectation 0 (neutral pair = 1 total point = 0 diff). It tests whether Janus outperforms the "break-even" baseline.

| Quantity | v0.41 Claim | Recomputed | Formula |
|:---|:---:|:---:|:---|
| Mean diff $\bar{d}$ | +0.48 | +0.4800 | ✓ MATCH |
| SE | 0.1241 | 0.1241 | $s/\sqrt{n}$ |
| t-statistic | 3.8680 | 3.8680 | $\bar{d}/SE$ |
| p-value (two-tailed, df=24) | ≈ 0.00073 | ≈ 0.00073 | t=3.868, df=24 |

**Note:** The p-value 0.00073 corresponds to a two-tailed test. One-tailed p ≈ 0.000365 — even more decisive.

### 5.2 Bootstrap Confidence Interval

**Implementation review:**
- Resamples `pair_scores` (total per pair ∈ {0, 0.5, 1.0, 1.5, 2.0}) not pair diffs
- Bootstrap mean = sum(sample) / (2 × n_pairs) → converts to score %
- 10,000 bootstrap iterations, seed=42
- 2.5th percentile → lower bound, 97.5th percentile → upper bound

| Bound | v0.41 Claim | Recomputed |
|:---|:---:|:---:|
| 95% CI lower | 61.0% | 61.0% |
| 95% CI upper | 85.0% | 85.0% |

**Verdict:** ✓ MATCH. The CI is for the score %, not for the pair-score delta. This is a correct and standard presentation; the CI for score % directly tests that RFP scores above 50% (and above K0's 45%).

---

## 6. Elo Estimate Audit

### 6.1 Formula Applied

$$\text{Elo estimate (vs SF 1320)} = 400 \cdot \log_{10}\!\left(\frac{p}{1-p}\right)$$

| Configuration | Score % | Elo Estimate | Independent Calculation |
|:---|:---:|:---:|:---:|
| K0 (v0.40) | 45.0% | -34.9 | 400·log₁₀(0.45/0.55) = **-34.86** ✓ |
| RFP (v0.41) | 74.0% | +181.7 | 400·log₁₀(0.74/0.26) = **181.70** ✓ |

**Correction from summary:** The context summary speculated the formula might give 177 Elo for 74%. This was incorrect — it arose from rounding 74% to 0.74 and using 0.26 as the complement. The exact calculation gives **181.70 Elo**, which matches the v0.41 report precisely.

### 6.2 Reported Delta (+216.6 Elo)

$$\Delta_\text{Elo} = 181.70 - (-34.86) = 216.56 \approx +216.6 \text{ Elo}$$

**Independent calculation: ✓ MATCH**

### 6.3 Interpretation Caveat (CRITICAL)

The +216.6 Elo figure is **the difference of two independent noisy Elo estimates**, each with substantial uncertainty:

- K0 Elo estimate: -34.9 ± ~97 Elo (Wilson 95% CI based on 50 games)
- RFP Elo estimate: +181.7 ± ~97 Elo (same uncertainty)
- The difference has uncertainty of approximately ±137 Elo (propagated)

This means the true Elo gain from RFP over K0 could plausibly be anywhere from ~+80 to ~+350 Elo at 95% confidence based on these independent estimates alone. The direct causal measurement requires the paired Phase F ablation.

---

## 7. Claim-by-Claim Audit Table

| # | v0.41 Claim | Verification Method | Verdict | Notes |
|:---:|:---|:---|:---:|:---|
| 1 | 33W/8D/9L in 50 games | Raw count from attempt_log.json | ✓ VERIFIED | Exact match |
| 2 | Score 37.0/50 (74.0%) | Arithmetic | ✓ VERIFIED | Exact match |
| 3 | Mean pair diff = +0.48 | Recomputed from pairs | ✓ VERIFIED | Exact match |
| 4 | SE = 0.1241 | Recomputed | ✓ VERIFIED | Exact match |
| 5 | t = 3.8680 | Recomputed | ✓ VERIFIED | Exact match |
| 6 | p ≈ 0.00073 | t=3.868, df=24, two-tailed | ✓ VERIFIED | Standard tables |
| 7 | 95% bootstrap CI [61%, 85%] | Recomputed (seed=42) | ✓ VERIFIED | Exact match |
| 8 | RFP Elo ≈ +181.7 | 400·log₁₀(0.74/0.26) | ✓ VERIFIED | 181.70 |
| 9 | K0 Elo ≈ -34.9 | 400·log₁₀(0.45/0.55) | ✓ VERIFIED | -34.86 |
| 10 | Delta = +216.6 Elo | 181.70 − (−34.86) | ✓ VERIFIED | 216.56 |
| 11 | 0 illegal moves in PGN | PGN replay | ✓ VERIFIED | 4671 plies |
| 12 | 0 negative clocks | CSV audit | ✓ VERIFIED | 4671 rows |
| 13 | 50/50 games completed | attempt_log.json | ✓ VERIFIED | 0 failures |

---

## 8. Identified Limitations (Not Errors)

1. **Independent estimates vs. causal comparison:** The +216.6 Elo figure describes two separate experiments, not a controlled ablation. The v0.42 Phase F experiment provides the direct causal measurement.

2. **Bootstrap CI scope:** The bootstrap CI [61%, 85%] is computed on the pair-score distribution, not on the delta distribution. It correctly answers "Where does RFP score against Stockfish 1320?" but not "How much better than K0 is RFP?"

3. **Single-session match:** All 50 games were played in a single session without session-level randomization. The ordering could introduce a sequential bias (e.g., system warm-up effects). This is a minor limitation given the paired design.

4. **Opening sample size:** 25 opening pairs is a relatively small sample for Elo estimation. The uncertainty is accordingly large (~±97 Elo per configuration at 95%).

---

## 9. Phase B Verdict

**GATE B1 — Raw Data Integrity:** ✓ PASS  
**GATE B2 — Statistical Correctness:** ✓ PASS (all formulas verified)  
**GATE B3 — Elo Formula Accuracy:** ✓ PASS (181.70 confirmed)  
**GATE B4 — Delta Interpretation:** ✓ PASS (with documented caveat)

**Overall Phase B Status:** ✓ VERIFIED — No statistical errors found in v0.41 claims.

The v0.41 RFP qualification result is statistically valid. The Phase F ablation is still required to establish direct causal attribution.

