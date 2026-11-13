# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Janus Classical Tournament Standard Version 2 (JCTS v2)

**Document ID:** `analysis/phase1/p1.12/JCTS_2_COMPETITIVE_VALIDATION.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Status:** Certified Standard Operating Procedure & Statistical Protocol  
**Date:** 2026-11-12  
**Auditor:** Principal Computer Chess Engineer & Independent Statistical Auditor  

---

## 1. Motivation & Historical Auditing of Experimental Failures

Throughout Milestones P1.8 through P1.11, Project Janus experienced recurring cycles of candidate introduction, apparent tactical improvement, and subsequent competitive collapse in head-to-head tournament play. A rigorous audit of tournament data in P1.10 and P1.11 revealed three critical structural vulnerabilities in the legacy testing methodology:

1. **Severe Statistical Underpowering (The $\pm 50\text{ Elo}$ Noise Trap):**  
   Previous tournament matches were conducted at sample sizes of $N = 40$ to $N = 200$ games. In a 200-game match with an empirical draw rate of $35\%$, the standard error of the score is $\sigma / \sqrt{N} \approx \sqrt{0.325} / \sqrt{200} \approx 0.0403$. The resulting $95\%$ confidence margin of error is $\pm 1.96 \times 0.0403 \approx \pm 0.079$ in win percentage, which corresponds to **$\pm 55.4\text{ Elo}$**. A candidate that was actually $-15\text{ Elo}$ worse than baseline had a ~15% chance of appearing $+15\text{ Elo}$ better simply due to stochastic game variance.
2. **Time-Control Inversion (Speed Distortions):**  
   Candidates were evaluated almost exclusively at ultra-fast time controls (e.g., $100\text{ms}$ to $500\text{ms}$ fixed per move, or $5\text{s}+0.05\text{s}$). At ultra-fast time controls, search overheads (e.g., continuous static evaluation calls, complex history table updates, stack allocations) destroy $25\%\text{--}40\%$ of tree throughput, dropping search depth by 1 to 2 plies. When tested at slower time controls, search depth increases, and the cost-benefit curve of pruning heuristics shifts fundamentally. Legacy protocols lacked a mandatory slower-TC replication requirement.
3. **Unadjusted Multiple Comparisons:**  
   Multiple candidate variants (e.g., X8, X9, X10, X11, X13, X14, X15, X16) were tested across ad-hoc position suites and short matches without controlling family-wise error rates ($\alpha$). Testing multiple hypotheses at $\alpha = 0.05$ without correction virtually guaranteed false positives (Type I error).

The **Janus Classical Tournament Standard v2 (JCTS v2)** is established to resolve these deficiencies with preregistered sample sizes, rigorous sequential validation, statistical power bounds, and mandatory slower-TC replication.

---

## 2. Statistical Framework & Sample Size Requirements

### 2.1 The Mathematics of Chess Elo Power Analysis
Let game results be scored as $W = 1.0$ (win), $D = 0.5$ (draw), and $L = 0.0$ (loss). Let $s$ denote the average score:
$$s = \frac{W + 0.5 D}{N}$$
The Elo difference $\Delta$ is related to expected score $E$ by the logistic function:
$$E = \frac{1}{1 + 10^{-\Delta / 400}}$$
For a target effect size of $\Delta = +15\text{ Elo}$, the expected score is:
$$E_{15} = \frac{1}{1 + 10^{-15/400}} \approx 0.52157 \quad (\delta = E - 0.5 = +0.02157)$$
The sample variance of individual game outcomes is:
$$V = \frac{W + 0.25 D}{N} - s^2 \approx \frac{1 - D_{rate}}{4}$$
For a typical computer chess draw rate of $D_{rate} \approx 30\%$, $V \approx \frac{0.70}{4} + \text{covariance term} \approx 0.30$.

To detect an Elo advantage $\Delta$ at significance level $\alpha$ (Type I error probability) and statistical power $1 - \beta$ (where $\beta$ is Type II error probability), the required two-sided sample size $N$ is:
$$N = \frac{\left(Z_{\alpha/2} + Z_{\beta}\right)^2 \cdot 2 V}{\delta^2}$$
For standard experimental parameters $\alpha = 0.05$ ($Z_{\alpha/2} = 1.96$) and $1 - \beta = 0.80$ ($Z_{\beta} = 0.8416$):
$$\left(1.96 + 0.8416\right)^2 = (2.8016)^2 \approx 7.849$$
$$N_{15\text{ Elo}} = \frac{7.849 \times 2 \times 0.30}{(0.02157)^2} = \frac{4.7094}{0.0004653} \approx 10,121 \text{ games (two-sided)}$$
For a directional one-sided test ($H_0: \Delta \le 0$ vs $H_1: \Delta > 0$):
$$\left(Z_{0.05} + Z_{0.20}\right)^2 = (1.645 + 0.8416)^2 = (2.4866)^2 \approx 6.183$$
$$N_{15\text{ Elo, one-sided}} = \frac{6.183 \times 2 \times 0.30}{0.0004653} \approx 7,973 \text{ games}$$

### 2.2 Feasible Tournament Allocations & Effect Size Boundaries
Because generating 10,000 games per experimental branch is computationally infeasible on local hardware during iterative research, JCTS v2 defines explicit, preregistered effect-size detection floors based on allocated sample sizes:

| Sample Size ($N$) | 95% Confidence Interval ($s \pm$) | Elo Margin of Error ($\pm \text{Elo}$) | Minimum Detectable $\Delta$ ($\text{Power} = 80\%$) | Protocol Classification |
| :---: | :---: | :---: | :---: | :--- |
| **80** | $\pm 0.120$ | $\pm 84.5\text{ Elo}$ | $\ge 90.0\text{ Elo}$ | Diagnostic Smoke Test Only |
| **200** | $\pm 0.076$ | $\pm 53.2\text{ Elo}$ | $\ge 55.0\text{ Elo}$ | Screening Phase Gating |
| **400** | $\pm 0.054$ | $\pm 37.6\text{ Elo}$ | $\ge 38.0\text{ Elo}$ | Confirmatory Tournament |
| **1,000** | $\pm 0.034$ | $\pm 23.7\text{ Elo}$ | $\ge 24.5\text{ Elo}$ | Official Baseline Gating |

**Preregistered Stopping Rule:** Any candidate claiming promotion based on an observed difference that falls inside the $95\%$ confidence margin of error is **strictly rejected**. The null hypothesis of zero improvement cannot be rejected.

---

## 3. Sequential Validation Protocol (Three-Stage Gate)

Under JCTS v2, every proposed engine candidate must progress through three discrete sequential stages before promotion can be certified. Failure at any stage results in immediate candidate termination.

```
+-----------------------------------------------------------------------------+
| STAGE 1: DIAGNOSTIC CORRECTNESS & SEARCH HARMONY (100% PASS REQUIRED)       |
| - Perft 1-6 correctness, zero illegal move generation                       |
| - Low-clock survival test (100 positions @ 10ms-50ms, zero crashes/timeouts)|
| - Mate precision suite (100% mate-in-1, mate-in-2, mate-in-3 found)        |
+-----------------------------------------------------------------------------+
                                       | Pass
                                       v
+-----------------------------------------------------------------------------+
| STAGE 2: FAST-TC SCREENING MATCH (SPRT GATED)                               |
| - Time control: 5s + 0.05s increment (or 10s + 0.1s)                        |
| - Opponent: Exact Tier 1 Baseline (X7 for 1T, X12 for 4T)                  |
| - Sample size: SPRT [0, +25 Elo] with maximum sample N = 200 games          |
| - Early rejection boundary: LLR <= ln(0.05 / 0.95) -> Terminate immediately |
+-----------------------------------------------------------------------------+
                                       | Pass (LLR >= ln(0.95 / 0.05))
                                       v
+-----------------------------------------------------------------------------+
| STAGE 3: MANDATORY SLOWER-TC REPLICATION MATCH                              |
| - Time control: >= 20s + 0.2s increment (or >= 40s + 0.4s)                  |
| - Minimum sample size: N = 100 paired games (color reversed)                |
| - Promotion hurdle: Score >= 50.0% AND lower 95% CI >= -15.0 Elo            |
| - Slower-TC Regression Invariant: If candidate loses Elo at slower TC,      |
|   it is formally REJECTED regardless of Stage 2 score.                      |
+-----------------------------------------------------------------------------+
```

---

## 4. Match Configuration Controls

### 4.1 Strict Opening Pairing
All tournament games must be played in opening pairs:
- Every opening FEN is contested exactly twice: once with Candidate playing White (Control playing Black), and once with Control playing White (Candidate playing Black).
- This strictly eliminates first-move advantage bias and book-selection variance from the score difference.

### 4.2 Standardized Adjudication Rules
To prevent wasted compute on settled positions or endless drawn endgames:
1. **Resignation Adjudication:** An engine resigns if the opponent's search evaluation exceeds $+600\text{ cp}$ (or $-600\text{ cp}$ from player perspective) for 4 consecutive plies, provided move number $\ge 20$.
2. **Draw Adjudication:**
   - Standard 3-fold repetition and 50-move rule enforced by tournament manager.
   - Evaluation draw: If move count $\ge 40$, material count $\le 10$ pieces, and both engines evaluate within $[-15\text{ cp}, +15\text{ cp}]$ for 6 consecutive plies.
   - Insufficient material: Automatically adjudicated as draw.

### 4.3 Clock Telemetry & Time Management Invariants
1. **Zero-Forfeit Rule:** Any crash, illegal move, or clock flag forfeit constitutes an immediate loss for that game. If an engine incurs $\ge 2$ forfeits in a match, the match is aborted and the engine fails certification.
2. **Clock Utilization Tracking:** The tournament manager must log:
   - Average move duration ($\text{ms}$)
   - Peak move duration ($\text{ms}$)
   - Remaining time at move 40
   - Number of emergency time-trouble moves ($< 10\%\text{ of increment remaining}$)

---

## 5. Multiple-Comparison Controls

When testing a causal feature grid (e.g., evaluating variants F1, F2, F3, F4 against baseline F0), testing each at nominal $\alpha = 0.05$ produces an inflated family-wise error rate:
$$\alpha_{family} = 1 - (1 - 0.05)^k$$
For $k = 4$ feature variants, $\alpha_{family} = 1 - (0.95)^4 \approx 18.5\%$.

To control Type I error:
1. **Bonferroni Correction:** When testing $k$ candidate variants simultaneously, the significance threshold per test is reduced to:
   $$\alpha' = \frac{\alpha}{k} = \frac{0.05}{4} = 0.0125$$
2. **False Discovery Rate (FDR):** For exploratory parameter sweeps, the Benjamini-Hochberg procedure must be applied to rank-ordered $p$-values.

---

## 6. Promotion Invariants

A candidate engine is declared promoted to production status if and only if:
1. It passes Stage 1 correctness with $100\%$ compliance.
2. It achieves a statistically significant victory ($p < 0.05$, or SPRT upper bound hit) in Stage 2 against its qualified Tier 1 baseline.
3. It replicates non-negative performance ($\text{score} \ge 50.0\%$) in Stage 3 slower-TC verification.
4. It does not regress in execution throughput (NPS) by $> 15\%$ unless compensated by a measurable reduction in effective branching factor.

**Certification:** The JCTS v2 standard is now formally adopted as the official testing protocol for Project Janus.
