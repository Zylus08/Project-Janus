# Project Janus v0.39 — Statistical Strength Analysis Report

## 1. Executive Summary

- **Candidate Under Test:** Janus v0.39 (`Candidate Q0_K0`)
- **Calibrated Anchor Opponent:** Stockfish 19 calibrated to Elo 1320 (`UCI_LimitStrength=true`, `UCI_Elo=1320`)
- **Time Control:** 3000 ms base + 100 ms Fischer increment (50 valid games, 25 complete colour-reversed pairs).
- **Match Score:** **21W - 3D - 26L** => **22.5/50 points (45.0%)**.
- **Paired Bootstrap 95% Confidence Interval:** **[31.0%, 58.0%]**.
- **Performance Rating Difference:** **-34.9 Elo** vs Stockfish 1320 (95% CI: [-139.0, +56.1] Elo).
- **Calibrated Engine Anchor Rating:** **1285.1 Elo** (Baseline v0.38: 1361.9 Elo).
- **Comparative Verdict:** **`STRENGTH_REGRESSED`**.

## 2. Paired Match Performance & Color Breakdown

| Dimension | White Performance | Black Performance | Combined Total |
| :--- | :---: | :---: | :---: |
| **Points Scored** | 9.5 / 25 | 13.0 / 25 | **22.5 / 50** |
| **Score Percentage** | 38.0% | 52.0% | **45.0%** |

## 3. Inferential Statistics

| Metric | Value | Interpretation |
| :--- | :---: | :--- |
| **Paired Unit Mean (D)** | 0.9000 pts / pair | Null expectation $\mu_D = 1.00$ |
| **Sample Std Deviation ($s_D$)** | 0.7217 | Paired variance across opening books |
| **Paired Student's t-statistic** | -0.6928 | Degrees of freedom $\nu = 24$ |
| **Two-tailed p-value** | 4.8842e-01 | Probability under null hypothesis |
| **Paired Sign Outcomes** | 6 won / 10 drawn / 9 lost | Qualitative pair dominance |
| **Bootstrap 95% CI (10k iterations)** | [31.0%, 58.0%] | Non-parametric empirical confidence bounds |

## 4. Benchmark Reconciliation vs v0.38 Baseline

| Metric | v0.38 Baseline Anchor | v0.39 Candidate | Net Delta | Evaluation |
| :--- | :---: | :---: | :---: | :--- |
| **Match Score** | 56.0% (28.0/50) | 45.0% (22.5/50) | -11.0% | Deficit |
| **Elo Differential** | +41.9 Elo | -34.9 Elo | -76.8 Elo | Verified anchor calibration |
| **Effective Rating** | 1361.9 Elo | 1285.1 Elo | -76.8 Elo | Standard logistic formula |
| **Horizon Mate Concessions** | Present (e.g. `f4c7`) | 0 Conceded | 100% Resolved | Hardened against shallow fallbacks |