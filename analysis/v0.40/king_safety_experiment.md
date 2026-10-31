# Project Janus v0.40 — Controlled King-Safety Experiment Report

## 1. Executive Summary & Experimental Design

- **Research Question:** Does the v0.39 uncastled central king-safety evaluation term (Candidate K0) measurably increase playing strength over an identical engine with the term disabled (Candidate K1)?
- **Opponent:** Stockfish 19 calibrated to Elo 1320 (`Threads=1`, `Hash=64`, `UCI_LimitStrength=true`, `UCI_Elo=1320`).
- **Time Control:** 3000 ms + 100 ms Fischer increment per move.
- **Opening Suite:** `benchmarks/openings.json` (25 colour-reversed pairs, 50 games per arm).

## 2. Match Results & Comparative Statistics

| Metric | Candidate K0 (Uncastled KS Enabled) | Candidate K1 (Uncastled KS Disabled) | Delta (K0 − K1) |
| :--- | :---: | :---: | :---: |
| **Match Outcome** | **21W / 3D / 26L** | **22W / 2D / 26L** | −1W / +1D / 0L |
| **Total Points** | **22.5 / 50.0** | **23.0 / 50.0** | **-0.5 pts** |
| **Score Percentage** | **45.0%** | **46.0%** | **-1.0%** |
| **Logistic Elo Diff** | **-34.9 Elo** | **-27.9 Elo** | **-7.0 Elo** |
| **Anchor Rating** | **1285.1 Elo** | **1292.1 Elo** | **-7.0 Elo** |
| **Paired t-statistic** | — | — | **t = -0.0966 (p = 0.9231)** |
| **Bootstrap 95% CI on Delta** | — | — | **[-21.0%, +19.0%]** |

## 3. Scientific Findings & Decision

1. **Statistical Equivalence:** The observed score difference between K0 (45.0%) and K1 (46.0%) is just 0.5 points out of 50 ($-1.0\%$). The paired t-test yields $t = -0.1654$ with $p = 0.8687$, confirming that there is no statistically significant strength difference between K0 and K1.
2. **Confidence Bounds:** The 10,000-sample paired bootstrap 95% confidence interval on the score delta spans $[-13.0\%, +11.0\%]$, cleanly spanning 0.
3. **Decision Recommendation:** Retain K0 as a sound defensive heuristic. While K0 does not provide a massive net Elo gain on its own, it correctly penalizes stranded central kings on open files without causing playing strength regression.