# Project Janus v0.51.1 — Independent Statistical Reconciliation Report

## 1. Executive Summary & Audited Claim Reconciliation

This audit independently recalculated every statistical metric of the v0.51 match using [`analysis/v0.51.1/scripts/recompute_match_statistics.py`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/scripts/recompute_match_statistics.py).

While the central conclusion (overwhelming statistical superiority of Native N2 over Python K0) is **fully confirmed**, the audit discovered two significant mathematical discrepancies in the v0.51 report:
1. **$p$-Value Mathematical Error:** The reported two-tailed $p$-value ($3.80 \times 10^{-238}$) was calculated using the standard normal distribution approximation (`math.erfc`), underestimating the Student-t tail probability by 183 orders of magnitude. The exact Student-t value ($df = 99$) is **$3.61 \times 10^{-55}$**.
2. **Elo Confidence Interval Distortion:** The reported Elo interval ($[+51.1, +904.9]$) was derived using a linear symmetric delta-method approximation ($478.0 \pm 1.96 \times 217.8$). The true empirical percentile bootstrap Elo interval is **$[+407.3, +576.2]$**.

---

## 2. Comprehensive Metric Reconciliation Matrix

| Metric | Original v0.51 Report | Audited Recomputation | Discrepancy | Forensic Root Cause | Impact on Scientific Conclusion |
|---|:---:|:---:|:---:|---|---|
| **Opening Pairs ($N$)** | 100 | **100** | $0$ | Verified exact | None |
| **Total Games** | 200 | **200** | $0$ | Verified exact | None |
| **N2 Points** | 188.0 | **188.0** | $0.0$ | Verified exact | None |
| **K0 Points** | 12.0 | **12.0** | $0.0$ | Verified exact | None |
| **Score Percentage** | 94.00% | **94.00%** | $0.00\%$ | Verified exact | None |
| **Mean Paired Delta ($\bar{\Delta}$)** | $+1.760$ | **$+1.760$** | $0.000$ | Verified exact | None |
| **Sample Standard Deviation ($s_\Delta$)** | $0.5341$ | **$0.5341$** | $0.0000$ | Verified exact | None |
| **Standard Error ($SE_\Delta$)** | $0.0534$ | **$0.0534$** | $0.0000$ | Verified exact | None |
| **Paired $t$-Statistic** | $32.9532$ | **$32.9532$** | $0.0000$ | Verified exact | None |
| **Degrees of Freedom ($df$)** | 99 (narrative) | **99** | $0$ | Verified exact | None |
| **Two-tailed $p$-Value** | $3.80 \times 10^{-238}$ | **$3.61 \times 10^{-55}$** | $\times 10^{183}$ | Used `math.erfc` (Gaussian tail) instead of Student-t survival function | **Corrected.** Both $p \ll 10^{-6}$; null hypothesis decisively rejected |
| **One-tailed $p$-Value** | $1.90 \times 10^{-238}$ | **$1.81 \times 10^{-55}$** | $\times 10^{183}$ | Same as above | **Corrected.** Decisively significant |
| **Delta 95% Bootstrap CI** | $[+1.650, +1.860]$ | **$[+1.650, +1.860]$** | $0.000$ | Confirmed at 100,000 resamples | None |
| **Score % 95% Bootstrap CI** | — | **$[91.25\%, 96.50\%]$** | Added | Newly reported | None |
| **Point Elo Estimate** | $+478.0$ | **$+478.0$** ($+477.99$) | $0.0$ | Verified exact | None |
| **Elo 95% Confidence Interval** | $[+51.1, +904.9]$ | **$[+407.3, +576.2]$** | Vastly tightened | Original used naive linear delta method ($478 \pm 427$); audit used empirical percentile bootstrap | **Corrected.** Confirms N2 advantage is tightly bounded $> +400$ Elo |

---

## 3. Mathematical Analysis of the Identified Discrepancies

### 3.1 The $p$-Value Discrepancy
In `run_preregistered_match.py`, lines 340–342 computed the $p$-value as:
```python
p_val_two = math.erfc(abs(t_stat) / math.sqrt(2.0))
```
This is the standard formula for a two-tailed tail probability of a **Standard Normal distribution**:
$$P(|Z| \ge 32.9532) = \text{erfc}\left(\frac{32.9532}{\sqrt{2}}\right) \approx 3.8036 \times 10^{-238}$$

However, the paired test has sample size $N = 100$ pairs ($df = 99$). Student's $t$-distribution has polynomial tails ($O(t^{-99})$), which decay much more slowly than the exponential tails of the normal distribution ($O(e^{-t^2/2})$). 

The exact survival function of Student's $t$ with $df = 99$:
$$P(T_{99} \ge 32.9532) = \frac{1}{2} I_{x}\left(\frac{99}{2}, \frac{1}{2}\right) \quad \text{where } x = \frac{99}{99 + 32.9532^2} \approx 0.08355$$
Evaluated via the continued fraction expansion of the regularized incomplete beta function, the exact probability is:
$$p_{\text{exact}} = 2 \times 1.80707 \times 10^{-55} = \mathbf{3.61415 \times 10^{-55}}$$

While $10^{-55}$ remains astronomical in its statistical significance (the probability of this occurring by chance is less than one in $10^{54}$), reporting $10^{-238}$ was mathematically unjustified.

### 3.2 The Elo Confidence Interval Discrepancy
In `run_preregistered_match.py`, lines 348–350 derived the Elo confidence interval using the linear delta method:
$$SE_{\text{elo}} = \frac{400}{\ln(10) \times p \times (1 - p) \times \sqrt{N}} = \frac{400}{2.3026 \times 0.94 \times 0.06 \times \sqrt{200}} \approx 217.80\text{ Elo}$$
$$\text{Elo CI} = 478.0 \pm 1.96 \times 217.80 = [+51.1, +904.9]$$

This formula is a first-order Taylor expansion of $\text{Elo}(p) = 400 \log_{10}(p / (1-p))$. Because the derivative $\text{Elo}'(p) \propto \frac{1}{p(1-p)}$ explodes as $p \to 1.0$, linear approximation fails catastrophically near $p = 0.94$, creating an unphysically wide, symmetric interval ($478 \pm 427$ Elo) that spans almost 1,000 Elo points!

In the audit's 100,000-sample paired bootstrap, the empirical distribution of win percentages has a $95\%$ interval of $[91.25\%, 96.50\%]$. Transforming these empirical quantiles directly through the logistic Elo function yields:
$$\text{Elo}(0.9125) = 400 \times \log_{10}\left(\frac{0.9125}{0.0875}\right) = \mathbf{+407.29\text{ Elo}}$$
$$\text{Elo}(0.9650) = 400 \times \log_{10}\left(\frac{0.9650}{0.0350}\right) = \mathbf{+576.18\text{ Elo}}$$

**Audited Result:** The true $95\%$ confidence interval for N2's playing strength is **$[+407.3, +576.2]$ Elo**. The engine's true superiority is far more tightly bounded than the original report indicated.

---

## 4. Sensitivity Analyses on the 9 Horizon Games

To ensure the final scientific conclusion does not depend on the controller's artificial 150-ply cutoff, three counterfactual sensitivity models were evaluated:

```
+-------------------------------------------------------------------------------------------------------------+
|                                        SENSITIVITY ANALYSIS SUMMARY                                         |
+-------------------------------------------+---------+------------+----------+-------------+-----------------+
| Sensitivity Scenario                      | Games   | N2 Score % | Elo Diff | Paired t    | Exact p-Value   |
+-------------------------------------------+---------+------------+----------+-------------+-----------------+
| Baseline Audited (All 200 games)          | 200     | 94.00%     | +478.0   | 32.95       | 3.61 x 10^-55   |
| S1: Exclude 9 pairs with horizon games    | 182     | 96.43%     | +572.5   | 40.59       | 1.19 x 10^-59   |
| S2: Conservative (4 K0 material wins)     | 200     | 93.00%     | +449.4   | 27.01       | 1.84 x 10^-47   |
| S3: Adversarial Worst-Case (9 K0 wins)    | 200     | 91.75%     | +418.5   | 22.59       | 7.53 x 10^-41   |
+-------------------------------------------+---------+------------+----------+-------------+-----------------+
```

- In **Scenario S1**, excluding the truncated games actually *increases* N2's score to **$96.43\%$ (+572.5 Elo)** because N2 was up massive material in 5 of those games.
- In **Scenario S3**, even under the most hostile possible adjudication imaginable—where every single one of the 9 horizon games is credited as a win to Python K0—N2 still achieves **$91.75\%$ (+418.5 Elo)** with $p < 10^{-40}$.

The playing-strength dominance of Candidate N2 is utterly invariant to game-length adjudication rules.
