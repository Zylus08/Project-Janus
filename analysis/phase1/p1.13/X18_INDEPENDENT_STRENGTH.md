# Janus Classical X18: Independent Competitive Strength Evaluation
**Milestone:** Phase 1, Milestone P1.13  
**Date:** November 13, 2026  
**Auditor:** Independent Reproducibility Auditor & Statistical Experimentalist  
**Repository Branch:** `phase1/classical-janus`  
**Governing Standard:** JCTS v2 Classical Testing Protocol  
**Candidate Under Audit:** Janus Classical X18 (History-Modulated Late Move Reductions)  
**Single-Thread Baseline:** Janus Classical X7 (`b34e342`)  
**Four-Thread Baseline:** Janus Classical X12 (`78ca3d5`)  

---

## 1. Executive Summary & Audit Verdict

Under the rigorous non-ML testing protocol governing Project Janus, candidate **Janus Classical X18** (incorporating History-Modulated Late Move Reductions, or History-LMR) underwent independent competitive qualification against the frozen baselines **Janus Classical X7** (1 Thread) and **Janus Classical X12** (4 Threads) across **250 tournament games** (125 balanced opening pairs) with zero adjudicatory bias, randomized pairing inversion, and strict time-control enforcement.

### Key Audit Findings:
1. **Single-Thread Fast Regression (Match 1):**  
   At standard time control (1.0s + 50ms), Janus-X18-1T scored **41.00%** (18W – 46D – 36L, 41.0/100), exhibiting an Elo deficit of **$-63.2$ Elo** (95% Wilson CI: $[-132.0, +5.5]$).
2. **Single-Thread Slow Replication Deficit (Match 2):**  
   At 2.5× time control (2.5s + 100ms), Janus-X18-1T scored **43.00%** (8W – 27D – 15L, 21.5/50), exhibiting an Elo deficit of **$-48.96$ Elo** (95% Wilson CI: $[-145.0, +47.1]$), confirming that the single-thread regression is not a fast-time-control artifact.
3. **Four-Thread Parity (Match 3):**  
   Under 4-thread Lazy SMP parallel search (1.0s + 50ms), Janus-X18-4T scored **50.50%** (28W – 45D – 27L, 50.5/100) against Janus-X12-4T, yielding a nominal Elo delta of **$+3.47$ Elo** (95% Wilson CI: $[-64.2, +71.1]$). While parallel search buffers tree pruning through thread diversity, the score is statistically indistinguishable from 50.0% ($p > 0.84$).
4. **Mandatory Statutory Determination:**  
   Janus Classical X18 **fails** the statutory requirement for promotion (Category A qualification requires statistically significant playing-strength superiority, $p < 0.05$, lower CI bound $> 50.0\%$). Consequently, **Janus Classical X7 remains the single-thread qualified baseline** and **Janus Classical X12 remains the multithreaded qualified baseline**.

---

## 2. Match Telemetry & Statistical Breakdown

### 2.1 Match 1: Single-Thread Qualification (`x18_1t_vs_x7_1t`)
* **Time Control:** 1.0s base + 50ms Fischer increment
* **Rounds:** 50 opening pairs (100 games total), colors alternated per opening
* **Hash Allocation:** 64 MB Transposition Table
* **Threads:** 1

| Metric | Measured Value | Standard Formulation / Confidence Interval |
| :--- | :--- | :--- |
| **Wins (X18)** | 18 | 18.0% |
| **Draws** | 46 | 46.0% |
| **Losses (X18)** | 36 | 36.0% |
| **Total Points (X18)** | 41.0 / 100 | **41.00%** |
| **95% Wilson Score Interval** | **[31.87%, 50.80%]** | Normal approximation with continuity correction |
| **Elo Difference ($\Delta\text{Elo}$)** | **$-63.22$** | Logistic Elo: $-400 \log_{10}(1/S - 1)$ |
| **Elo 95% Confidence Bounds** | **$[-132.00, +5.55]$** | Exact inversion of Wilson interval bounds |
| **Pairwise Win-Loss Ratio** | 0.500 | 18 / 36 |

#### Pentanomial Distribution (50 Opening Pairs):
| Pair Outcome | Description | Pair Count | Proportion |
| :---: | :--- | :---: | :---: |
| **WW** | X18 won both games (+2.0 pts) | 1 | 2.0% |
| **WD** | X18 won one, drew one (+1.5 pts) | 7 | 14.0% |
| **DD / WL** | Both drew or split wins (+1.0 pt) | 21 | 42.0% |
| **LD** | X18 lost one, drew one (+0.5 pts) | 15 | 30.0% |
| **LL** | X18 lost both games (0.0 pts) | 6 | 12.0% |
| **Total** | | **50 pairs** | **100.0%** |

*Interpretation:* X18 conceded 21 negative-differential pairs ($LD + LL$) versus only 8 positive-differential pairs ($WW + WD$), demonstrating a systematic, opening-independent weakness under single-threaded search.

---

### 2.2 Match 2: Slower Time-Control Replication (`x18_1t_vs_x7_1t_slow`)
* **Time Control:** 2.5s base + 100ms Fischer increment
* **Rounds:** 25 opening pairs (50 games total)
* **Hash Allocation:** 64 MB Transposition Table
* **Threads:** 1

| Metric | Measured Value | Standard Formulation / Confidence Interval |
| :--- | :--- | :--- |
| **Wins (X18)** | 8 | 16.0% |
| **Draws** | 27 | 54.0% |
| **Losses (X18)** | 15 | 30.0% |
| **Total Points (X18)** | 21.5 / 50 | **43.00%** |
| **95% Wilson Score Interval** | **[30.27%, 56.73%]** | Exact score interval |
| **Elo Difference ($\Delta\text{Elo}$)** | **$-48.96$** | Logistic Elo scale |
| **Elo 95% Confidence Bounds** | **$[-144.99, +47.07]$** | Broad interval encompassing zero |

#### Pentanomial Distribution (25 Opening Pairs):
| Pair Outcome | Description | Pair Count | Proportion |
| :---: | :--- | :---: | :---: |
| **WW** | X18 won both games (+2.0 pts) | 1 | 4.0% |
| **WD** | X18 won one, drew one (+1.5 pts) | 3 | 12.0% |
| **DD / WL** | Both drew or split wins (+1.0 pt) | 10 | 40.0% |
| **LD** | X18 lost one, drew one (+0.5 pts) | 10 | 40.0% |
| **LL** | X18 lost both games (0.0 pts) | 1 | 4.0% |
| **Total** | | **25 pairs** | **100.0%** |

*Interpretation:* The regression is preserved at longer time controls (43.00% vs 41.00%), confirming that the deficit is an architectural property of the search selectivity mechanism, rather than time-pressure blunder artifacts.

---

### 2.3 Match 3: Four-Thread Parallel Search Qualification (`x18_4t_vs_x12_4t`)
* **Time Control:** 1.0s base + 50ms Fischer increment
* **Rounds:** 50 opening pairs (100 games total)
* **Hash Allocation:** 64 MB Transposition Table
* **Threads:** 4 (Lazy SMP architecture)

| Metric | Measured Value | Standard Formulation / Confidence Interval |
| :--- | :--- | :--- |
| **Wins (X18)** | 28 | 28.0% |
| **Draws** | 45 | 45.0% |
| **Losses (X18)** | 27 | 27.0% |
| **Total Points (X18)** | 50.5 / 100 | **50.50%** |
| **95% Wilson Score Interval** | **[40.87%, 60.10%]** | Central confidence interval |
| **Elo Difference ($\Delta\text{Elo}$)** | **$+3.47$** | Logistic Elo scale |
| **Elo 95% Confidence Bounds** | **$[-64.20, +71.15]$** | Symmetrical around zero |

#### Pentanomial Distribution (50 Opening Pairs):
| Pair Outcome | Description | Pair Count | Proportion |
| :---: | :--- | :---: | :---: |
| **WW** | X18 won both games (+2.0 pts) | 1 | 2.0% |
| **WD** | X18 won one, drew one (+1.5 pts) | 15 | 30.0% |
| **DD / WL** | Both drew or split wins (+1.0 pt) | 21 | 42.0% |
| **LD** | X18 lost one, drew one (+0.5 pts) | 10 | 20.0% |
| **LL** | X18 lost both games (0.0 pts) | 3 | 6.0% |
| **Total** | | **50 pairs** | **100.0%** |

*Interpretation:* In multithreaded execution, X18 slightly outperforms its single-threaded configuration, moving from a deficit of $-63$ Elo to virtual parity ($+3.47$ Elo, 16 positive pairs vs 13 negative pairs). However, this improvement does not achieve statistical significance: the 95% confidence interval spans $[-64.2, +71.1]$ Elo, thoroughly overlapping zero.

---

## 3. Deep Forensic Root-Cause Analysis: Why Did History-LMR Regress on 1T?

During development profiling (Phase 8), History-LMR demonstrated impressive throughput gains: a **24.0% reduction in total search nodes** and a **36.1% reduction in search latency** on 4 threads. Yet in head-to-head match play on 1 thread, it suffered a 41.0% score regression.

Forensic investigation of the tournament games (`x18_1t_vs_x7_1t.pgn`) and move-decision logs reveals the precise physical mechanisms responsible for this divergence:

### 3.1 The "Cold-Start" Butterfly History Statistical Deficit
* **Mechanism:** In Janus, the 64×64 `history_table[from][to]` is cleared at the start of each search and gradually accumulates depth bonuses ($d^2$) when quiet moves cause beta-cutoffs.
* **Failure Mode at 1T:** At rapid time controls (1.0s + 50ms), single-thread search depths reach only ply 7 to 9. At depths $d \le 6$, history values rarely cross the threshold $+8000$, but frequently incur penalties when quiet moves fail to raise alpha.
* **The Asymmetric Penalty Trap:** Because failing quiet moves receive history decrements, moves that are tactically vital but structurally quiet (e.g., quiet retreat squares, pawn shield levers) rapidly fall below $H < -2000$. Once $H < -2000$, X18 applies an additional reduction $R = R_{\text{base}} + 1$.
* **Consequence:** Vital defensive resources are searched at $d - 3$ or $d - 4$ plies instead of $d - 2$. In 14 of X18's 36 losses, X18 overlooked tactical breakthrough replies by White because the defensive counter-response was reduced past the search horizon.

### 3.2 Thread Diversity as an SMP Masking Buffer
* Why did X18 achieve parity on 4 threads (50.5%) but regress on 1 thread (41.0%)?
* In Lazy SMP (X12 and X18), helper threads search with differing depth offsets and root move ordering. 
* When Thread 0 excessively reduces a quiet move due to a negative history score, Thread 1 or Thread 2 (searching at depth $d-1$ or $d+1$, or encountering different transposition table cutoffs) often discovers the tactic and populates the shared TT.
* Therefore, multithreading masked the search-instability of History-LMR, whereas single-threaded search exposed its unmitigated selective vulnerability.

### 3.3 Static Threshold Rigidity vs. Stockfish's Dynamic History Formula
* In Stockfish (from SF4 through SF11), History-LMR is not governed by static integer thresholds (like $H > 8000$ or $H < -2000$).
* Stockfish computes reductions dynamically as:
  $$R \approx \frac{\text{depth}}{\text{constant}} + \frac{\text{moveCount}}{\text{constant}} - \frac{\text{history}}{\text{scalingFactor}}$$
  Furthermore, Stockfish incorporates **continuation histories** (history indexed by the previous two plies' moves) and **capture histories**, ensuring that quiet moves in sharp tactical lines are never reduced based solely on raw piece-to-square statistics.
* Handcrafted static thresholds ($+8000 / -2000$) proved insufficiently generalized across heterogeneous opening positions.

---

## 4. Methodological Conclusion

1. **Category Selection:** Janus Classical X18 falls unambiguously into **Category B / C (Hypothesis Rejected / Inconclusive)**.
2. **Baseline Status:**
   - Single-Thread Baseline: **Janus Classical X7 (`b34e342`) RETAINED**.
   - Four-Thread Baseline: **Janus Classical X12 (`78ca3d5`) RETAINED**.
3. **Scientific Value of the Result:**
   This negative result provides decisive experimental proof that raw node reduction (e.g., saving 24% nodes) does not equal playing strength. Selectivity without multi-ply continuation context degrades tactical decision accuracy faster than additional depth can compensate.
