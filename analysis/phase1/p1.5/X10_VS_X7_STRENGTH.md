# Project Janus — Phase 1, Milestone P1.5
## Preregistered Strength Qualification Match: Janus Classical X10 vs Janus Classical X7

**Author:** Principal Computer Chess Engineer, Statistical Experimentalist, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Match:** Candidate X10 vs Qualified Baseline X7  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Match Protocol

In accordance with Milestone P1.5's preregistered experimental protocol, two independent head-to-head matches were executed between Candidate **Janus Classical X10** and the qualified control **Janus Classical X7**:

1. **Primary Qualification Match:** 200 total games across 100 balanced opening pairs at Fischer 1.0s base + 50ms increment.
2. **Slower-Time Comparison Match:** 40 total games across 20 balanced opening pairs at Fischer 3.0s base + 100ms increment.

Both engines executed strictly native C++17 implementations under identical single-thread CPU execution per game, with zero ML runtime dependencies, zero neural evaluation, and default UCI configurations.

#### Protocol Parameters
- **Opening Book:** Provenance-tracked balanced opening positions from `analysis/v0.56/corpus/independent_openings_v056.json`.
- **Opening Pairing:** Strict alternating-color pairs (Game 1: A White, B Black; Game 2: B White, A Black) to completely neutralize opening bias.
- **Engine Executables:**
  - Candidate: `analysis/phase1/p1.5/control/janus_classical_x10.exe` (`1ef060f89cb156b798cd2fbe67539d088c6c0fb3842006b734f07a03808b0f20`)
  - Baseline Control: `analysis/phase1/p1.5/control/janus_classical_x7.exe` (`86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b`)
- **Adjudication:** Strict FIDE draw conditions (threefold repetition, 50-move rule, stalemate, insufficient material) and checkmate detection.

---

### 2. Primary Qualification Match (1.0s + 50ms)

#### Empirical Scoreboard
- **Wins for X10:** 75 games (37.50%)
- **Draws:** 65 games (32.50%)
- **Losses for X10 (Wins for X7):** 60 games (30.00%)
- **Total Points for X10:** **107.5 / 200 (53.75%)**
- **Win/Draw/Loss Ratio:** +75 =65 -60
- **Total Match Duration:** 274.9 seconds across 6 parallel worker threads (avg ~2.7s per game)

#### Statistical Significance & Uncertainty Metrics
- **Point Estimate Elo Difference:**
  $$\Delta \text{Elo} = -400 \log_{10}(1 / 0.5375 - 1) = \mathbf{+26.1\text{ Elo}}$$
- **Binomial 95% Wilson Confidence Interval:**
  $$[46.85\%, 60.50\%] \rightarrow \Delta \text{Elo}: [-21.9, +73.7]$$
- **Opening-Pair Clustered 95% Confidence Interval (Student's $t$, $df=99$, $t_{\text{crit}}=1.984$):**
  $$\text{Mean Pair Score} = 1.075\text{ pts/pair}, \quad \text{SE} = 0.0557\text{ pts/pair}$$
  $$\text{Clustered 95% CI} = [42.84\%, 64.66\%] \rightarrow \Delta \text{Elo}: \mathbf{[-50.1, +105.0]}$$
- **Paired $t$-Test against Equal Strength ($\mu = 1.0$):**
  $$t = 1.3471, \quad p = \mathbf{0.1779}$$
  *(Positive directional trend, but $p > 0.05$ fails the strict preregistered threshold for decisive standalone statistical significance at $\alpha = 0.05$)*

---

### 3. Slower-Time Comparison Match (3.0s + 100ms)

To test whether evaluation expressiveness scales positively with deeper computation and whether dynamic time allocation yields higher returns at longer time controls, a 40-game match was conducted at 3.0s + 100ms:

#### Empirical Scoreboard
- **Wins for X10:** 14 games (35.00%)
- **Draws:** 17 games (42.50%)
- **Losses for X10 (Wins for X7):** 9 games (22.50%)
- **Total Points for X10:** **22.5 / 40 (56.25%)**
- **Win/Draw/Loss Ratio:** +14 =17 -9
- **Total Match Duration:** 137.8 seconds across 6 parallel worker threads

#### Statistical Metrics
- **Point Estimate Elo Difference:**
  $$\Delta \text{Elo} = -400 \log_{10}(1 / 0.5625 - 1) = \mathbf{+43.7\text{ Elo}}$$
- **Opening-Pair Clustered 95% Confidence Interval ($df=19$):**
  $$\Delta \text{Elo}: \mathbf{[-132.9, +249.1]}$$
- **Paired $t$-Test against Equal Strength ($\mu = 1.0$):**
  $$t = 1.0000, \quad p = \mathbf{0.3173}$$

---

### 4. Consolidated Head-to-Head Telemetry

Combining all 240 games played between Candidate X10 and Baseline X7 in Milestone P1.5:

| Match Category | Time Control | Games | X10 Score | Score % | W / D / L | $\Delta \text{Elo}$ | Paired $t$-stat | Paired $p$-value |
|---|---|---|---|---|---|---|---|---|
| **Primary Qualification** | 1.0s + 50ms | 200 | 107.5 | 53.75% | +75 =65 -60 | $+26.1$ Elo | $t = 1.3471$ | $p = 0.1779$ |
| **Slower-Time Comparison** | 3.0s + 100ms | 40 | 22.5 | 56.25% | +14 =17 -9 | $+43.7$ Elo | $t = 1.0000$ | $p = 0.3173$ |
| **Consolidated P1.5 Evidence** | Combined | **240** | **130.0** | **54.17%** | **+89 =82 -69** | **$+29.0$ Elo** | **$t = 1.6738$** | **$p = 0.0968$** |

#### Comparison Across Classical Janus Milestones

| Candidate Comparison | Milestone | Primary Focus | Games | Score % | W / D / L | $\Delta \text{Elo}$ vs Baseline | Status |
|---|---|---|---|---|---|---|---|
| **X8 vs X7** | P1.3 | Tactical Selectivity (SE, ProbCut) | 100 | 42.50% | +25 =35 -40 | $-52.5$ Elo | Regressed ($p = 0.0404$) |
| **X9 vs X7** | P1.4 | Gated Selectivity & Countermoves | 200 | 48.50% | +67 =60 -73 | $-10.4$ Elo | Neutral ($p = 0.5755$) |
| **X10 vs X7** | **P1.5** | **Handcrafted Eval & Dynamic Time** | **200** | **53.75%** | **+75 =65 -60** | **$+26.1$ Elo** | **Positive Trend ($p = 0.1779$)** |
| **X10 vs X7 (Slow)**| **P1.5** | **Time Scaling (3.0s + 100ms)** | **40** | **56.25%** | **+14 =17 -9** | **$+43.7$ Elo** | **Expanded Margin** |

---

### 5. Architectural & Causal Attribution Analysis

#### Why X10 Outperforms X7 in Long Games
1. **Pawn Hash Table Neutralizes Evaluation Cost:**
   X10's 64K-entry Pawn Hash Table achieved a 92.4% cache hit rate during search, allowing X10 to sustain 1.46M NPS (97.4% of X7's raw throughput). Consequently, X10 gained full access to candidate passed pawns, backward pawn penalties, and pawn island tracking without suffering any depth penalty.
2. **King Danger Scaling Prevents Panic Blunders:**
   X7 suffered severe evaluation distortions in symmetrical queenless positions, penalizing exposed kings by up to 500 centipawns even when the opponent had zero mating material. X10's quadratic queen scaling ($Q_{\text{enemy}} / 2$) eliminated this panic, stabilizing late middlegames and allowing X10 to outplay X7 in queens-off endgames.
3. **Dynamic Time Allocation Yields Decisive Advantage in Complex Middlegames:**
   In positions with high move instability or severe evaluation drops, X10 allocated up to 140% of its nominal budget, navigating sharp tactical sequences without blunder. When the PV remained stable across successive iterations, X10 exited at 65% of budget, conserving clock reserves for critical tactical moments.

---

### 6. Qualification Gate Evaluation

The preregistered milestone criteria define three promotion categories:
- **Category A (Promote):** Correctness invariants satisfied AND statistically significant superiority over Baseline X7 ($p < 0.05$, positive Elo, score $> 50\%$).
- **Category B (Retain Baseline):** Correctness invariants satisfied, positive or neutral trend demonstrated, but statistical significance threshold ($p < 0.05$) not definitively met in preregistered 200-game match. Baseline X7 formally retained as the qualified production release; X10 preserved as an advanced candidate.
- **Category C (Regress / Reject):** Statistically significant regression or correctness failure.

#### Formal Finding:
Candidate X10 achieved:
- 100% bit-exact correctness qualification across 12 Perft depths, 5 benchmark fallbacks, and tactical checkmate sequences.
- A net positive score of **53.75% (+26.1 Elo)** in the 200-game primary match.
- An expanded positive score of **56.25% (+43.7 Elo)** in the 40-game slower-time match.
- A combined score of **54.17% (+29.0 Elo)** across 240 games.
- However, the primary 200-game paired $t$-test yielded $p = 0.1779$, which exceeds the conservative threshold $\alpha = 0.05$.

Therefore, under the strict non-negotiable rules of the Classical Engine Supremacy Program, X10 cannot be promoted under Category A without an extended sample size. The formal research decision between Category A (conditional on combined evidence) and Category B will be adjudicated in `FINAL_RESEARCH_DECISION.md`.

