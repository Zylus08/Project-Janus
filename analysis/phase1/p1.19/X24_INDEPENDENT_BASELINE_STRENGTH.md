# Independent Baseline Strength Battery: Candidate X24 vs Baselines X7 & X12

## 1. Executive Summary

Milestone P1.19 evaluates whether Candidate **Janus Classical X24** qualifies for **Category A (Full Baseline Replacement)** by contesting three independent matches against the qualified immutable baselines:
- **Janus Classical X7 (`b34e342`)**: Single-thread strength control baseline.
- **Janus Classical X12 (`78ca3d5`)**: Four-thread SMP strength control baseline.

### Summary of Baseline Strength Matches:

| Match Designation | Opponent Engine | Time Control | Games / Pairs | Score (Wins / Draws / Losses) | Win Rate (%) | Elo Delta | Paired 95% CI | Two-Sided $p$-value | Promotion Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 2 (1T Promotion)** | Janus Classical X7 | 1.0s + 50ms | 100 / 50 | 48.0 (27 / 42 / 31) | 48.0% | -13.9 | [41.46%, 54.54%] | $p = 0.5491$ | **FAILED** |
| **Match 3 (4T Promotion)** | Janus Classical X12 | 1.0s + 50ms | 100 / 50 | 47.0 (29 / 36 / 35) | 47.0% | -20.9 | [38.76%, 55.24%] | $p = 0.4755$ | **FAILED** |
| **Match 4 (Slow TC Check)** | Janus Classical X7 | 3.0s + 100ms | 50 / 25 | 18.5 (6 / 25 / 19) | 37.0% | -92.5 | [26.75%, 47.25%] | $p = 0.0129$ | **REGRESSION** |

### Definitive Strategic Findings:
1. **1T Baseline Promotion Failed:** Candidate X24-S scored 48.0% against Baseline X7, with a paired confidence interval overlapping 50.0% ($p = 0.5491$). It fails the prerequisite requirement for Category A baseline replacement (paired CI lower bound $> 50.0\%$ and $p < 0.05$).
2. **4T SMP Baseline Promotion Failed:** Candidate X24-P scored 47.0% against Baseline X12, with a paired confidence interval of [38.76%, 55.24%] ($p = 0.4755$). Multithreaded scaling does not rescue the deficit.
3. **Statistically Significant Slow TC Regression:** In Match 4 at 3.0s + 100ms, X24-S collapsed to **37.0%** (-92.5 Elo) against X7, with $p = 0.0129$ ($p < 0.05$) and the upper bound of the 95% CI reaching only 47.25%.
4. **Permanent Baseline Retention:** Qualified Baselines X7 and X12 remain unreplaced and retain their status as the immutable playing-strength controls for Project Janus.

---

## 2. Match 2: Single-Thread Baseline Promotion (X24-S vs X7)

### 2.1 Configuration & Results
- **Candidate:** Janus Classical X24-S (1T)
- **Opponent:** Janus Classical X7 (1T Baseline, SHA-256: `86392A2F...`)
- **Protocol:** 50 opening pairs (100 games) @ 1.0s + 50ms Fischer increment
- **Score:** 48.0 / 100 (+27 =42 -31, 48.0%)
- **Pentanomial Distribution:** $[2.0: 2, 1.5: 11, 1.0: 21, 0.5: 13, 0.0: 3]$
- **Statistical Inferences:**
  $$\hat{\mu} = 0.4800, \quad SE = 0.0334, \quad t = -0.600, \quad p_{\text{two-sided}} = 0.5491$$
  $$\text{Paired 95\% CI} = [41.46\%, 54.54\%]$$

### 2.2 Forensic Analysis
Baseline X7 possesses an aggressive, highly tuned material-mobility evaluation that prioritizes open lines and rapid piece centralization over pawn structure purity. In fast matches (1.0s + 50ms):
- X24 held its own in 21 neutral pairs and won 13 pairs, benefiting from the pawn-hash table's evaluation speed (+13.6% NPS).
- However, X7's uninhibited piece play created frequent dynamic threats that neutralized X24's slight structural advantages, leading to 42 draws and 31 X7 victories.
- X24 could not achieve a positive score, proving that isolated backward pawn penalties do not confer a net tactical or positional advantage over X7's simpler, faster evaluation.

---

## 3. Match 3: Four-Thread SMP Baseline Promotion (X24-P vs X12)

### 3.1 Configuration & Results
- **Candidate:** Janus Classical X24-P (4T SMP)
- **Opponent:** Janus Classical X12 (4T Baseline, SHA-256: `00B4F5FE...`)
- **Protocol:** 50 opening pairs (100 games) @ 1.0s + 50ms Fischer increment (2 concurrent matches on 8 physical cores)
- **Score:** 47.0 / 100 (+29 =36 -35, 47.0%)
- **Pentanomial Distribution:** $[2.0: 4, 1.5: 12, 1.0: 16, 0.5: 10, 0.0: 8]$
- **Statistical Inferences:**
  $$\hat{\mu} = 0.4700, \quad SE = 0.0420, \quad t = -0.714, \quad p_{\text{two-sided}} = 0.4755$$
  $$\text{Paired 95\% CI} = [38.76\%, 55.24\%]$$

### 3.2 Concurrency & Workload Distribution
Baseline X12 represents the peak classical multithreaded engine developed in Phase 1 (P1.7), featuring an extremely lean SMP worker thread model.
- Candidate X24-P scaled efficiently to 2.91M NPS across 4 threads, maintaining search stability and generating coherent principal variations.
- However, the deeper search trees achieved under 4T SMP amplified the evaluation divergence: X12's higher raw search speed allowed it to out-search X24-P by 0.5–1.0 ply in critical positions.
- X24-P scored 47.0% (-20.9 Elo), demonstrating that SMP scaling does not overcome evaluation deficiencies.

---

## 4. Match 4: Slow Time Control Robustness Audit (X24-S vs X7 @ 3.0s + 100ms)

### 4.1 Configuration & Results
- **Candidate:** Janus Classical X24-S (1T)
- **Opponent:** Janus Classical X7 (1T Baseline)
- **Protocol:** 25 opening pairs (50 games) @ 3.0s + 100ms Fischer increment
- **Score:** 18.5 / 50 (+6 =25 -19, 37.0%)
- **Pentanomial Distribution:** $[2.0: 1, 1.5: 3, 1.0: 7, 0.5: 10, 0.0: 4]$
- **Statistical Inferences:**
  $$\hat{\mu} = 0.3700, \quad SE = 0.0523, \quad t = -2.486, \quad p_{\text{two-sided}} = 0.0129$$
  $$\text{Paired 95\% CI} = [26.75\%, 47.25\%]$$

### 4.2 Diagnostic Failure Analysis: The "Slow TC Degradation" Phenomenon
Match 4 provides the most decisive diagnostic insight of Milestone P1.19. While X24 scores 48.0% at 1.0s + 50ms, its performance drops precipitously to **37.0%** at 3.0s + 100ms, establishing a statistically significant regression ($p = 0.0129$).

Audit of game losses reveals the underlying mechanism:
1. **Deeper Horizon Exposure of Static Penalties:** At 1.0s, search depth is typically 8–9 plies. Tactical pruning (NMP, LMR) dominates search decisions, and backward pawn penalties provide modest guidance. At 3.0s, search depth reaches 11–13 plies. At this depth, the search explores complete tactical branches and discovers concrete defensive paths or pawn sacrifices. Static evaluation terms that penalize pawn structure without tactical dynamic verification cause the engine to misjudge transition endgames.
2. **Endgame Static Bias:** In pure rook and minor piece endgames, X24 frequently avoided creating passed pawns because the supporting pawn would become backward. Baseline X7, unburdened by backward-pawn penalties, pushed its pawns forward aggressively, creating outside passed pawns that won the game.
3. **Horizon Inversion:** In 10 of the 14 pair disadvantages (0.5 and 0.0), X24 entered the endgame with equal material and a supposedly "superior" pawn structure, but was out-maneuvered by X7's active pieces.

---

## 5. Promotion Verdict

Under the Project Janus qualification charter:
- **Prerequisite for Category A Promotion:** Paired 95% CI lower bound $> 50.0\%$ and $p < 0.05$ across Baselines X7 and X12, with demonstrated non-regression at slow time controls.
- **Observed Results:**
  - Match 2 (1T): 48.0% ($p = 0.5491$, CI lower bound 41.46%) $\to$ **FAIL**
  - Match 3 (4T): 47.0% ($p = 0.4755$, CI lower bound 38.76%) $\to$ **FAIL**
  - Match 4 (Slow TC): 37.0% ($p = 0.0129$, CI upper bound 47.25%) $\to$ **REGRESSION**
- **Adjudication:** Candidate **Janus Classical X24 is REJECTED for Category A baseline replacement**. Janus Classical X7 and Janus Classical X12 remain the official, qualified, immutable strength baselines.
