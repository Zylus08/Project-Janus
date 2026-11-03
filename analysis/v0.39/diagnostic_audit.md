# Project Janus v0.39 — Baseline Diagnostic & Statistical Audit

**Audit Timestamp:** 2026-10-31  
**Auditor:** Statistical Validation Lead & Independent Audit Engineer  
**Baseline Evaluated:** Project Janus v0.38 External Engine Benchmark  
**Starting Commit:** `00595a3`  

---

## 1. Audit of v0.38 External Statistical Claims

An independent audit of the statistical calculations and inference reported in `analysis/v0.38/statistical_analysis.json` and `docs/v0.38_external_benchmark_report.md` revealed key findings that must be reconciled:

### 1.1 The Primary Benchmark (0/100 Losses) and Confidence Interval Flaw
- **Reported in v0.38:** Score $0.0\%$, with paired Student's t-interval $[0.0\%, 0.0\%]$ and bootstrap interval $[0.0\%, 0.0\%]$.
- **Critical Methodological Finding:** Reporting a zero-width confidence interval ($[0.0\%, 0.0\%]$) for a $0/100$ outcome is mathematically invalid. It conflates the sample point estimate ($\hat{p} = 0/100 = 0$) with zero uncertainty about the underlying population parameter $p$.
- **Correct Mathematical Formulations for Extreme Binomial Outcomes:**
  1. **Rule of Three (95% upper bound):** For zero events in $n$ trials, the one-sided 95% upper bound is $3/n = 3/100 = \mathbf{3.00\%}$.
  2. **Exact Clopper-Pearson 95% Confidence Interval:** $[0.0\%, 1 - 0.05^{1/100}] = [\mathbf{0.00\%}, \mathbf{3.62\%}]$.
  3. **Wilson Score Interval (continuity-corrected):** $[\mathbf{0.00\%}, \mathbf{3.69\%}]$.
- **Impact on Conclusions:** Janus's true expected score against unconstrained Stockfish 19 under 3000ms+100ms is not provably zero, but bounded strictly within $[0.0\%, 3.6\%]$ with 95% confidence.

### 1.2 The Calibrated Elo 1320 Benchmark (26W / 4D / 20L)
- **Observed Score:** $28.0 / 50 = \mathbf{56.0\%}$.
- **Paired Student's t-test ($df=24$):**
  - $\bar{S}_{pair} = 0.5600$, $s = 0.3905$, $SE = 0.3905 / \sqrt{25} = 0.0781$.
  - $t = (0.56 - 0.50) / 0.0781 = \mathbf{0.7682}$, $p = \mathbf{0.4498}$ (two-tailed vs null hypothesis $H_0: S = 50\%$).
- **Paired 95% t-interval:** $0.56 \pm (2.0639 \times 0.0781) = [\mathbf{39.88\%}, \mathbf{72.12\%}]$.
- **10,000-Resample Pair Bootstrap 95% CI:** $[\mathbf{41.00\%}, \mathbf{71.00\%}]$.
- **Exact Sign Test on Decisive Pairs:** 11 positive pairs vs 7 negative pairs ($N_{decisive} = 18$), $p = \mathbf{0.4807}$.
- **Elo Difference & Rating Anchor:**
  - $\Delta \text{Elo} = -400 \log_{10}(1/0.56 - 1) = \mathbf{+41.9\text{ Elo}}$.
  - 95% t-bounds: $[-71.3\text{ Elo}, +165.1\text{ Elo}]$.
  - Anchored Rating: $1320 + 41.9 = \mathbf{1361.9\text{ Elo}}$ (95% CI: $[1248.7, 1485.1]$).
- **Audit Verdict:** The statistical calculations for the Calibrated Benchmark are mathematically verified and reproducible.

### 1.3 The Historical Fixed Depth-3 Benchmark (3W / 7D / 40L)
- **Observed Score:** $6.5 / 50 = \mathbf{13.0\%}$ ($SE = 4.11\%$).
- **Paired 95% t-interval:** $[\mathbf{4.51\%}, \mathbf{21.49\%}]$.
- **Comparison with Historical v0.5 Baseline (7.5/50 = 15.0%):**
  - Score Delta: $\Delta = 13.0\% - 15.0\% = -2.0\%$ (exactly 1 game outcome difference).
  - Two-sample difference test: $t = -0.4866$, $p = \mathbf{0.6310}$.
- **Audit Verdict:** The v0.38 result is statistically indistinguishable from the v0.5 result ($p > 0.60$). Parity at depth 3 is confirmed.

---

## 2. Audit of the Loss-Forensics Denominator and Methodology

The v0.38 loss analysis reported in `docs/v0.38_external_benchmark_report.md` was subjected to a line-by-line inspection of `scripts/analyze_losses_v038.py`:

### 2.1 Sample Selection and Scope Boundary
- **Match Population:** 100 lost games in the Primary Benchmark.
- **Forensic Sample Analyzed:** Exactly 30 games.
- **Selection Mechanism:** `analyzed_games = (loss_games + draw_games)[:max_games_to_analyze]` where `max_games_to_analyze = 30`.
- **Finding:** The sample was a **sequential prefix** comprising games 1 through 30. It was neither a randomized sample nor chosen based on outcome severity.
- **Denominator Transparency:** Within these 30 games, 116 moves had an evaluation drop $\ge 150\text{ cp}$. All reported failure-mode percentages (e.g. 40.5% shallow search, 26.7% piece passivity, 12.9% king safety) describe the distribution of blunders **within this 30-game sample**, not the full 100-game match.

### 2.2 Flawed Treatment of Mate Sentinels as Centipawn Values
- **Code Inspection:** In `scripts/analyze_losses_v038.py`:
  ```python
  if 'score mate' in line_str:
    mate_score = 30000 if mate_plies > 0 else -30000
    score_cp = mate_score if turn_is_white else -mate_score
  ...
  eval_drop = eval_before - eval_after
```
- **Finding:** Forced mate sentinels ($\pm 30,000$) were treated as ordinary centipawns and subtracted directly (e.g., $-58 - (-30,000) = 29,942\text{ cp}$).
- **Impact:** Reporting "mean evaluation drop of $-6,998\text{ cp}$" or "$-11,662\text{ cp}$" was deeply distorted by discrete mate sentinels.
- **Resolution for v0.39:** Ordinary centipawn positional degradation must be reported separately from forced-mate discovery, forced-mate concession, and mate-distance changes.

