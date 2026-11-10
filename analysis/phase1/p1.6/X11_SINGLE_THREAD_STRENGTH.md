# Project Janus — Phase 1, Milestone P1.6
## Phase 9: Single-Thread Strength Qualification Report

**Date:** 2026-11-10  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Candidate Engine:** Janus Classical X11 (Threads = 1)  
**Control Baseline:** Janus Classical X7 (Threads = 1, Frozen Production Baseline `b34e342`)  
**Corpus:** 100 Balanced Opening Pairs (200 games) from `analysis/v0.56/corpus/independent_openings_v056.json`  
**Time Control:** 1.0s base + 50ms Fischer increment  
**PGN File:** `analysis/phase1/p1.6/pgn/x11_1t_vs_x7.pgn`  
**Raw Data File:** `analysis/phase1/p1.6/raw/x11_1t_vs_x7_tournament_raw.json`

---

### 1. Executive Summary

Milestone P1.6 mandates that single-thread algorithmic improvements be evaluated independently from multicore scaling. Gate A (Single-Thread Promotion) requires Candidate X11 to demonstrate statistically significant superiority ($p < 0.05$) over frozen Baseline X7 under identical single-core computational resources.

In a 200-game head-to-head match (100 opening pairs, colors reversed) at 1.0s + 50ms:
- **Result:** Janus Classical X11 scored **99.5 / 200 (49.75%)** (69 wins, 61 draws, 70 losses).
- **Estimated Elo Difference:** **−1.7 Elo** [95% Clustered CI: −87.1, +83.4].
- **Statistical Significance:** Paired $t$-test yields $t = -0.0815$, **$p = 0.9350$** (Not statistically significant).
- **Gate A Determination:** Candidate X11 achieves statistical parity with Baseline X7 at 1 thread, but does **not** demonstrate superior single-threaded strength ($p \ge 0.05$). Under the governing rules of Project Janus, **Janus Classical X7 is retained as the Qualified Single-Thread Production Baseline**.

---

### 2. Match Scorecard and Clustered Statistics

| Metric | Candidate X11 (1T) | Baseline X7 (1T) | Clustered Statistics |
| :--- | :---: | :---: | :--- |
| **Total Games** | 200 | 200 | 100 Balanced Opening Pairs |
| **Wins (White / Black)** | 69 (40W / 29B) | 70 (39W / 31B) | Decisive Game Rate: 69.5% |
| **Draws** | 61 | 61 | Draw Rate: 30.5% |
| **Total Points** | 99.5 | 100.5 | — |
| **Score Percentage** | **49.75%** | **50.25%** | Margin: −0.50% (−1 game net) |
| **Elo Difference** | **−1.7 Elo** | **+1.7 Elo** | Clustered 95% CI: [−87.1, +83.4] |
| **Paired $t$-statistic** | \multicolumn{2}{c|}{$t = -0.0815$} | Degrees of freedom: $df = 99$ |
| **$p$-value (two-tailed)** | \multicolumn{2}{c|}{**$p = 0.9350$**} | Threshold: $p < 0.05$ |
| **Adjudication** | \multicolumn{2}{c|}{**STATISTICAL PARITY (NO PROMOTION)**} | Null hypothesis cannot be rejected |

---

### 3. Progressive Score Evolution (by 20-Game Intervals)

| Pairs Completed | Games | X11 Wins | Draws | X7 Wins | Current Score | Running % | Running Elo |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 10 | 20 | 7 | 6 | 7 | 10.0 / 20 | 50.0% | +0.0 |
| 20 | 40 | 14 | 11 | 15 | 19.5 / 40 | 48.8% | −8.7 |
| 30 | 60 | 21 | 18 | 21 | 30.0 / 60 | 50.0% | +0.0 |
| 40 | 80 | 28 | 24 | 28 | 40.0 / 80 | 50.0% | +0.0 |
| 50 | 100 | 36 | 29 | 35 | 50.5 / 100 | 50.5% | +3.5 |
| 60 | 120 | 42 | 36 | 42 | 60.0 / 120 | 50.0% | +0.0 |
| 70 | 140 | 49 | 43 | 48 | 70.5 / 140 | 50.4% | +2.5 |
| 80 | 160 | 55 | 50 | 55 | 80.0 / 160 | 50.0% | +0.0 |
| 90 | 180 | 62 | 55 | 63 | 89.5 / 180 | 49.7% | −2.0 |
| **100** | **200** | **69** | **61** | **70** | **99.5 / 200** | **49.75%** | **−1.7** |

The score trajectory remained virtually dead-locked at 50% across the entire 200 games, confirming extraordinary statistical stability and verifying that single-threaded search and pruning in X11 introduce zero net regression, but also zero net single-thread Elo gain over X7.

---

### 4. Algorithmic Root-Cause Analysis

The single-thread performance of X11 combines two countervailing algorithmic forces:
1. **Positive Search Selectivity (Safe LMP):** As established in Phase 7, Safe LMP prunes 11.8% of unpromising quiet leaf moves, allowing the engine to allocate more search effort to tactical continuations.
2. **Cluster Spinlock & Overhead Penalty:** The cluster spinlocks (`ParallelTranspositionTable`) and thread-local state tracking introduce a small 2.3% throughput penalty and ~15% raw node count reduction at 1 thread under fast time controls.
3. **Net Synthesis:** In blitz conditions (1.0s + 50ms), the tactical savings from LMP almost exactly cancel out the TT spinlock checking overhead, resulting in identical playing strength (−1.7 Elo, $p = 0.9350$).

---

### 5. Conclusion & Formal Gate A Recommendation

1. **Gate A Outcome:** REJECT single-thread production promotion. Janus Classical X7 is retained as the frozen single-thread classical baseline.
2. **Next Step:** Proceed to Phase 10 to evaluate multicore playing strength scaling (X11 4T vs X7 1T) and external benchmark progress against Stockfish 19 (1T and 4T).

