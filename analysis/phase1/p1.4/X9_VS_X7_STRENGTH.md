# Project Janus — Phase 1, Milestone P1.4
## Preregistered Strength Qualification Match: Janus Classical X9 vs Janus Classical X7

**Author:** Principal Computer Chess Engineer, Statistical Experimentalist, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Match:** Candidate X9 vs Qualified Baseline X7  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Match Protocol

In accordance with Milestone P1.4's preregistered qualification gate, a full **200-game head-to-head match** was executed between Candidate **Janus Classical X9** and the qualified control **Janus Classical X7**.

#### Protocol Parameters
- **Games:** 200 total games across 100 balanced opening pairs from `independent_openings_v056.json`.
- **Pair Structure:** Each opening played twice with alternating colors (Game 1: X9 White, X7 Black; Game 2: X7 White, X9 Black).
- **Time Control:** Fischer 1.0s base + 50ms increment per move.
- **Hardware:** Identical single-thread dedicated CPU execution.
- **Engine Binaries:**
  - Candidate: `analysis/phase1/p1.4/control/janus_classical_x9.exe` (`f61376a2...`)
  - Baseline Control: `analysis/phase1/p1.3/control/janus_classical_x7.exe` (`86392a2f...`)
- **Adjudication:** Standard FIDE draw conditions (threefold repetition, 50-move rule, stalemate, insufficient material).

---

### 2. Empirical Match Scoreboard & Results

- **Wins for X9:** 67 games (33.50%)
- **Draws:** 60 games (30.00%)
- **Losses for X9 (Wins for X7):** 73 games (36.50%)
- **Total Points for X9:** **97.0 / 200 (48.50%)**
- **Win/Draw/Loss Ratio:** +67 =60 -73
- **Match Duration:** 1565.7s (26.1 minutes)

#### Statistical Significance & Uncertainty Metrics
- **Point Estimate Elo Difference:** $\Delta \text{Elo} = -400 \log_{10}(1 / 0.485 - 1) = \mathbf{-10.4\text{ Elo}}$
- **Binomial 95% Wilson Confidence Interval:** $[41.67\%, 55.39\%] \rightarrow \Delta \text{Elo}: [-58.4, +37.6]$
- **Opening-Pair Clustered 95% Confidence Interval (Student's $t$, $df=99$, $t_{\text{crit}}=1.984$):**
  $$\text{Mean Pair Score} = 0.970\text{ pts/pair}, \quad \text{SE} = 0.0536\text{ pts/pair}$$
  $$\text{Clustered 95% CI} = [43.19\%, 53.81\%] \rightarrow \Delta \text{Elo}: \mathbf{[-47.6, +26.6]}$$
- **Paired $t$-Test against Equal Strength ($\mu = 1.0$):**
  $$t = -0.5600, \quad p = \mathbf{0.5755}$$
  *(Statistically indistinguishable from equal playing strength at $\alpha = 0.05$)*

---

### 3. Comparison with the Historical X8 vs X7 Deficit

| Benchmark Match | Milestone | Games | Score % | W / D / L | $\Delta \text{Elo}$ Estimate | Clustered 95% CI | Paired $p$-value | Conclusion |
|---|---|---|---|---|---|---|---|---|
| **X8 vs X7** | P1.3 | 100 | 42.50% | +25 =35 -40 | $-52.5$ Elo | $[-106.4, -1.0]$ | $p = 0.0404$ | Statistically Significant Regression |
| **X9 vs X7** | **P1.4** | **200** | **48.50%** | **+67 =60 -73** | **$-10.4$ Elo** | **$[-47.6, +26.6]$** | **$p = 0.5755$** | **Net Recovery +42.1 Elo; Statistically Neutral** |

#### Causal Analysis of the Recovery
1. **Elimination of the Verification Search Depth Tax:**
   - Disabling unconstrained Singular Extensions and ProbCut recovered the $-1.9$ ply depth collapse suffered by X8.
   - X9 completed an average depth of 14.80 plies at 1s, matching and slightly exceeding X7's nominal search pace.
2. **Countermove Heuristic Impact:**
   - The Countermove Heuristic allowed X9 to win 67 games against X7 (a 33.5% win rate), performing substantially better than X8's 25% win rate in P1.3.
3. **The Limits of Move Ordering without Positional Upgrades:**
   - While countermoves accelerate alpha-beta pruning, they do not alter leaf evaluation. Against X7's deep positional evaluation (E5 pawn structure, king safety, mobility), X9 and X7 trade blows evenly across 100 opening pairs.

---

### 4. Promotion Gate Verdict

The milestone guidelines preregister the following promotion requirement:
> *"Promote X9 only if:
> 1. Correctness passes.
> 2. The independent primary strength test supports superiority over X7 at the preregistered confidence threshold ($p < 0.05$, positive Elo).
> 3. No critical safety or reliability regression is present.
> If superiority is uncertain, retain X7."*

#### Finding:
Candidate X9 successfully recovered $+42.1$ Elo over X8 and achieved statistical parity with X7 ($p = 0.5755$), but did not demonstrate statistically significant superiority over Baseline X7.

**Official Verdict:** **CATEGORY B / C: PROMOTION REJECTED. JANUS CLASSICAL X7 IS FORMALLY RETAINED AS THE QUALIFIED BASELINE.**

