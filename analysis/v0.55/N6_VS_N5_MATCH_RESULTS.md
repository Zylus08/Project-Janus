# Project Janus v0.55 — Experiment A Match Results: Janus N6 vs Janus N5

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N6 (C++17, LMR + Killer + History + PVS)  
**Baseline Engine:** Janus Native N5 (C++17, LMR + Killer + History, PVS disabled)  
**Match Classification:** Primary Preregistered Strength Evaluation (Experiment A)  
**Execution Script:** `analysis/v0.55/tests/run_preregistered_match.py --match n6_vs_n5`  
**Opening Suite:** `analysis/v0.55/corpus/independent_openings_v055.json` (100 Fresh Master Pairs)  
**Raw Data:** `analysis/v0.55/raw/n6_vs_n5_raw.json`  
**PGN Archive:** `analysis/v0.55/pgn/n6_vs_n5.pgn`  

---

## 1. Executive Summary & Headline Result

```text
========================================================================================
Project Janus v0.55 — Experiment A Head-to-Head Tournament Summary (200 Games)
========================================================================================
Candidate (N6: Killer+History+PVS) :  99.0 / 200 (49.50%)  [+40 =118 -42]
Baseline  (N5: Killer+History)     : 101.0 / 200 (50.50%)  [+42 =118 -40]
----------------------------------------------------------------------------------------
Candidate Net Score Margin         :  -2.0 points (-1.00%)
Estimated Elo Difference           :  -3.47 Elo
Parametric 95% Confidence Interval : [-36.21, +29.27] Elo
Bootstrap 95% Confidence Interval  : [-34.86, +29.60] Elo (10,000 resamples)
----------------------------------------------------------------------------------------
Paired Difference Analysis (100 Opening Pairs):
  Mean Paired Difference (d_bar)   : -0.0100 points / pair
  Standard Deviation (s_d)        :  0.4764 points / pair
  Standard Error (SE)             :  0.0476 points / pair
  Student's t-statistic           :  t = -0.2098 (df = 99)
  Two-Sided p-value               :  p = 0.83425  (Statistically Indistinguishable from Zero)
  Bootstrap 95% CI on d_bar       : [-0.1000, +0.0850] points / pair
========================================================================================
```

---

## 2. Statistical Significance & Hypothesis Testing

### 2.1 Preregistered Hypotheses
- **$H_0$ (Null Hypothesis):** Enabling Principal Variation Search does not improve playing strength over the qualified N5 production baseline ($\mu_d \le 0, \text{Elo}_\Delta \le 0$).
- **$H_1$ (Alternative Hypothesis):** Enabling Principal Variation Search confers a statistically significant playing-strength improvement over N5 ($\mu_d > 0, \text{Elo}_\Delta > 0$).

### 2.2 Paired Student's t-Test
Each of the 100 opening pairs was evaluated under exact color reversal:
- Candidate won pair (2–0 or 1.5–0.5): 23 pairs
- Pairs drawn (1–1): 52 pairs
- Candidate lost pair (0–2 or 0.5–1.5): 25 pairs
- Net pair delta: **$-2$ pairs**
- Mean paired difference: $\bar{d} = -0.0100$
- Sample standard deviation: $s_d = 0.4764$
- Standard error: $SE = 0.04764$
- Test statistic:
  $$t = \frac{-0.0100}{0.04764} = -0.2098, \quad df = 99$$
- Two-sided $p$-value: **$p = 0.83425 \gg 0.05$**

### 2.3 Non-Parametric Bootstrap Evaluation
10,000 bootstrap resamples of opening pairs were generated with replacement:
- 2.5th percentile of $\bar{d}^*$: **$-0.1000$ points/pair**
- 97.5th percentile of $\bar{d}^*$: **$+0.0850$ points/pair**
- 95% Confidence Interval for Elo: **$[-34.86, +29.60]$ Elo**

The confidence interval spans zero almost symmetrically. The null hypothesis cannot be rejected.

---

## 3. Tournament Integrity & Adjudication Breakdown

```text
Total Games Played          : 200
Total Match Duration        : 359.0 seconds (5.98 minutes)
Average Game Length         : 94.67 plies (47.3 full moves)

Terminations Breakdown:
  - Threefold Repetition     : 117 (58.5%)
  - Checkmate by White       : 40 (20.0%)
  - Checkmate by Black       : 42 (21.0%)
  - Insufficient Material    : 1 (0.5%)
  - Fifty-Move Rule          : 0 (0.0%)
  - Stalemate                : 0 (0.0%)
  - 300-Ply Safety Horizon   : 0 (0.0%)
  - Engine Crashes           : 0 (0.0%)
  - Time Forfeits            : 0 (0.0%)
```

### Referee Audit:
- All 117 threefold repetition claims strictly satisfied FIDE Article 9.2 upon verification against board move histories.
- Zero non-FIDE safety-limit truncations occurred.
- Both engines operated cleanly with zero crashes and zero timeouts.

---

## 4. Color Balance & Symmetry Analysis

```text
Candidate as White : +20 =60 -20  => 50.0 / 100 (50.00%)
Candidate as Black : +20 =58 -22  => 49.0 / 100 (49.00%)
Baseline as White  : +22 =58 -20  => 51.0 / 100 (51.00%)
Baseline as Black  : +20 =60 -20  => 50.0 / 100 (50.00%)
```

The distribution of wins and draws is virtually identical across colors, demonstrating that the match was completely balanced and unbiased by side to move.

---

## 5. Primary Promotion Verdict

Candidate $F_{11}$ (Janus Native N6) fails to satisfy the preregistered acceptance criteria for Category A promotion:
1. Candidate did not achieve a positive score ($49.50\% \le 50.0\%$).
2. The paired Student-t test is not statistically significant ($p = 0.83425 > 0.05$).
3. The 95% bootstrap confidence interval $[-34.86, +29.60]$ Elo fails to exclude zero.

**Disposition:** Janus N6 will **NOT** be promoted to production default. Production will retain Janus Native N5.

