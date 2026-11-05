# Project Janus v0.55 — v0.54 Evidence Audit & Replication Readiness

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Auditor:** Principal Chess Engine Research Architect & Independent Reproducibility Auditor  
**Scope:** Exhaustive Audit of v0.54 Playing-Strength Match Data, Adjudications, Sampling Validity & Statistical Fragility  
**Subject Match:** Candidate $C_3$ (Janus Native N5) vs Control $C_0$ (Janus Native N3)  
**Data Sources Audited:**
- `analysis/v0.54/raw/c3_vs_c0_primary_raw.json`
- `analysis/v0.54/pgn/c3_vs_c0_primary.pgn`
- `analysis/v0.54/MATCH_RESULTS.md`

---

## 1. Complete Statistical Reconstruction

An independent reconstruction was executed directly from the raw game logs and pair ledgers without relying on summary text:

$$\begin{array}{|l|r|r|c|}
\hline
\textbf{Metric} & \textbf{v0.54 Reported} & \textbf{v0.55 Audit Reconstruction} & \textbf{Reconciliation Status} \\
\hline
\text{Total Games} & 200 & 200 & \text{EXACT MATCH} \\
\text{Opening Pairs} & 100 & 100 & \text{EXACT MATCH} \\
\text{Candidate Wins } (W) & 45 & 45 & \text{EXACT MATCH} \\
\text{Candidate Draws } (D) & 127 & 127 & \text{EXACT MATCH} \\
\text{Candidate Losses } (L) & 28 & 28 & \text{EXACT MATCH} \\
\text{Candidate Total Points} & 108.5 & 108.5 & \text{EXACT MATCH} \\
\text{Candidate Score \%} & 54.25\% & 54.25\% & \text{EXACT MATCH} \\
\text{Net Score Margin} & +17.0\text{ pts} & +17.0\text{ pts} & \text{EXACT MATCH} \\
\hline
\text{Mean Paired Delta } (\bar{d}) & +0.0850 & +0.085000 & \text{EXACT MATCH} \\
\text{Sample Std Dev } (s_d) & 0.4086 & 0.408588 & \text{EXACT MATCH} \\
\text{Standard Error } (SE) & 0.0409 & 0.040859 & \text{EXACT MATCH} \\
\text{Student's } t\text{-Statistic} & 2.0803 & 2.080333 & \text{EXACT MATCH} \\
\text{Degrees of Freedom } (df) & 99 & 99 & \text{EXACT MATCH} \\
\text{Two-Sided } p\text{-Value} & 0.04008 & 0.040078 & \text{EXACT MATCH} \\
\text{Estimated Elo Advantage} & +29.60\text{ Elo} & +29.6035\text{ Elo} & \text{EXACT MATCH} \\
\text{Bootstrap 95\% Elo CI} & [+1.74, +57.86] & [+1.74, +57.86] & \text{EXACT MATCH} \\
\hline
\end{array}$$

### 1.1 Bootstrap Sampling Unit Audit
The bootstrap algorithm was verified:
- **Unit of Resampling:** Resampling was performed on the **100 opening pairs** ($N=100$), preserving the paired structure and color-reversal symmetry of each opening.
- **Game-level pooling was NOT used.**
- 10,000 resamples with replacement confirmed that the empirical 2.5th and 97.5th percentiles are $[+0.0050, +0.1650]$ in pair score difference, corresponding to $[+1.74, +57.86]$ Elo.

### 1.2 Tournament Protocol Integrity
- **Color Reversal:** Every opening pair $i \in [1, 100]$ consisted of exactly two games where Candidate played White in Game 1 and Black in Game 2.
- **Color Outcomes:** Candidate scored $54.5\%$ as White ($+22 =65 -13$) and $54.0\%$ as Black ($+23 =62 -15$), confirming absence of color-asymmetry artifacts.
- **Clock Accounting:** No clock negative-runaway or timeout forfeiture occurred across the 19,489 total plies.
- **Adjudication Legality:**
  - Checkmates: 73 (37 White, 36 Black).
  - Threefold Repetitions: 126 (all 126 independently verified on board move history as strictly meeting FIDE Article 9.2).
  - Insufficient Material: 1 (Game 173).
  - 300-Ply Safety Horizon: 0 triggers.
  - Engine Crashes: 0.

---

## 2. Statistical Fragility & Sensitivity Audit (Phase 0.2)

Because the two-sided p-value ($p = 0.04008$) is relatively close to the standard significance threshold $\alpha = 0.05$, a formal fragility audit was conducted.

### 2.1 Distribution of Paired Score Differences

Each opening pair yields a net score delta $d_i = \text{score}_{\text{cand}, i} - 1.0 \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$:

$$\begin{array}{|c|c|c|l|}
\hline
\textbf{Pair Delta } (d_i) & \textbf{Pair Count} & \textbf{Percentage} & \textbf{Pair Outcome} \\
\hline
-1.0\text{ pts} & 2 & 2.0\% & \text{Candidate lost both games (0--2)} \\
-0.5\text{ pts} & 15 & 15.0\% & \text{Candidate scored 0.5--1.5 (1 Loss, 1 Draw)} \\
0.0\text{ pts} & 52 & 52.0\% & \text{Drawn pair (1--1: either 2 draws or 1W-1L)} \\
+0.5\text{ pts} & 26 & 26.0\% & \text{Candidate scored 1.5--0.5 (1 Win, 1 Draw)} \\
+1.0\text{ pts} & 5 & 5.0\% & \text{Candidate swept both games (2--0)} \\
\hline
\textbf{Total} & \mathbf{100} & \mathbf{100.0\%} & \mathbf{Candidate \ Won \ 31, \ Drawn \ 52, \ Lost \ 17 \ (+14 \ net)} \\
\hline
\end{array}$$

### 2.2 Leave-One-Pair-Out (LOO) Sensitivity Analysis
To assess the stability of the statistical conclusion against single-pair perturbations, an exhaustive leave-one-pair-out analysis was computed for all 100 opening pairs:

```text
Full Sample (N=100) : Mean = +0.0850, t = 2.0803, p = 0.04008
LOO Mean Difference : Min = +0.0758, Max = +0.0960, Median = +0.0859
LOO t-Statistic     : Min = 1.8843,  Max = 2.4134,  Median = 2.0838
LOO p-Value         : Min = 0.01766, Max = 0.06248, Median = 0.04007
```

#### Fragility Threshold Breakdown:
1. **Removal of a $+1.0$ pair (5 pairs):**
   - New sample mean: $+0.0758$
   - $t = 1.8843$, $p = 0.06248$ ($p > 0.05$).
2. **Removal of a $+0.5$ pair (26 pairs):**
   - New sample mean: $+0.0808$
   - $t = 1.9682$, $p = 0.05187$ ($p > 0.05$).
3. **Removal of a $0.0$ pair (52 pairs):**
   - New sample mean: $+0.0859$
   - $t = 2.0838$, $p = 0.03975$ ($p < 0.05$).
4. **Removal of a $-0.5$ pair (15 pairs):**
   - New sample mean: $+0.0909$
   - $t = 2.2032$, $p = 0.02996$ ($p < 0.05$).
5. **Removal of a $-1.0$ pair (2 pairs):**
   - New sample mean: $+0.0960$
   - $t = 2.4134$, $p = 0.01766$ ($p < 0.05$).

### 2.3 Fragility Verdict & Scientific Implications
- **No Manipulation or Optional Stopping:** There is zero evidence of post-hoc exclusion or optional stopping. The tournament ran continuously to its preregistered 100-pair quota.
- **Inherent Finite-Sample Sensitivity:** Because the true underlying effect size is $+29.6$ Elo (corresponding to a win rate of $54.25\%$), a 200-game match has statistical power of approximately $55\%$ at $\alpha = 0.05$. Removing any single one of the 31 positive pairs moves the empirical p-value slightly above $0.05$ (to $0.052$ or $0.062$), while removing any single negative pair lowers $p$ down to $0.018$.
- **Replication Mandate:** This sensitivity is a normal property of finite-sample empirical trials, but it confirms the necessity of **Phase 9: Independent Replication of N5 vs N3** on a fresh, previously unseen opening corpus in Milestone v0.55.

---

## 3. Replication Readiness Checklist

- [x] Full v0.54 dataset independently reconstructed and verified.
- [x] Paired difference calculations, standard error, Student-t and bootstrap methods confirmed.
- [x] 100% legal FIDE adjudications verified without exception.
- [x] Statistical fragility characterized and documented.
- [x] Control N5 binary verified and ready for independent replication testing.

**Conclusion:** The baseline is fully audited and qualified for v0.55 experimental execution.

