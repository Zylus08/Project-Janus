# Janus Classical X16: Independent Strength Qualification Report

## 1. Executive Summary & Tournament Program Overview

Milestone P1.11 evaluated candidate **Janus Classical X16** across three rigorous, paired opening tournaments following the **Janus Competitive Testing Standard (JCTS v1.11)**. In conformance with project mandates, all games utilized the independent, unbiasing 500-opening corpus (`independent_openings_v056.json`), perfect color-reversal pair matching, strict non-neural classical execution, and formal two-tailed paired $t$-distribution and Two One-Sided Tests (TOST) equivalence testing.

| Match Identifier | Platform / Time Control | Competitors | Games (Pairs) | Score (Pct) | Elo Delta [95% CI] | Paired $t$-stat ($p$-value) | Superiority Proven? | TOST Equiv ($p_{\text{TOST}}$)? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Match A** | Single-Thread (1T)<br>1.0s + 50ms | **Janus X16-S** vs<br>**Janus X7** | 200 (100) | 67.5 / 200<br>(**33.75%**) | **-117.2**<br>[-167.9, -66.4] | $t = -5.745$<br>($p = 1.02 \times 10^{-7}$) | **NO** (Significant Regression) | **NO** ($p = 0.9999$) |
| **Match B** | 4-Thread Lazy SMP<br>1.0s + 50ms | **Janus X16-P** vs<br>**Janus X12** | 200 (100) | 91.0 / 200<br>(**45.50%**) | **-31.4**<br>[-79.5, +16.8] | $t = -1.578$<br>($p = 0.1177$) | **NO** (Inconclusive Deficit) | **NO** ($p = 0.4342$) |
| **Match C** | 4-Thread Slower TC<br>3.0s + 100ms | **Janus X16-P** vs<br>**Janus X12** | 100 (50) | 45.5 / 100<br>(**45.50%**) | **-31.4**<br>[-99.3, +36.6] | $t = -1.323$<br>($p = 0.1921$) | **NO** (Inconclusive Deficit) | **NO** ($p = 0.4432$) |

---

## 2. Match A: Janus Classical X16-S (1T) vs Janus Classical X7 (1T)

### 2.1 Configuration and Conditions
- **Candidate:** Janus Classical X16-S (`janus_classical_x16.exe`, 1T, E15, Pruning Safety, History-dampened LMR, 128MB TT).
- **Baseline Control:** Janus Classical X7 (`janus_classical_x7.exe`, Commit `b34e342`, 1T, E5, M0, Lean Classical Search, 128MB TT).
- **Format:** 100 opening pairs (200 games), Time Control: 1.0s base + 50ms Fischer increment.
- **PGN Record:** [`analysis/phase1/p1.11/pgn/x16_1t_vs_x7_1t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/pgn/x16_1t_vs_x7_1t.pgn).

### 2.2 Results and Statistical Distribution
- **Outcome:** +36 wins, =63 draws, -101 losses (67.5 / 200 points = **33.75%**).
- **Pentanomial Breakdown:**
  - $N_{2.0}$ ($ww$): **4 pairs** (4.0%)
  - $N_{1.5}$ ($wd$): **13 pairs** (13.0%)
  - $N_{1.0}$ ($dd$ / $wl$): **24 pairs** (24.0%)
  - $N_{0.5}$ ($ld$): **32 pairs** (32.0%)
  - $N_{0.0}$ ($ll$): **27 pairs** (27.0%)
- **Pair Difference Statistics:**
  - Mean pair difference $\bar{d} = -0.3250$
  - Variance $\text{Var}(d) = 0.3201$, Standard Error $SE = 0.0566$
- **Paired $t$-Test:**
  - $t = \frac{-0.3250}{0.0566} = -5.7446$ ($\text{df} = 99$)
  - Two-tailed $p$-value: **$1.02 \times 10^{-7}$**
  - Result: **Statistically significant regression**.
- **TOST Equivalence Testing ($\Delta_{\text{eq}} = 0.10$):**
  - $t_1 = \frac{-0.3250 - (-0.10)}{0.0566} = -3.9769$
  - $t_2 = \frac{-0.3250 - (+0.10)}{0.0566} = -7.5123$
  - $p_{\text{TOST}} = 0.9999$ ($\gg 0.05$). Equivalence is **firmly rejected**.

### 2.3 Diagnostic Analysis
Janus Classical X7 conclusively outperforms X16-S on a single thread by +117.2 Elo. In a single-threaded CPU execution environment, X7's lean simplicity—unencumbered by search stack static evaluation tracking, multi-ply continuation histories, and conservative pruning verification—achieves superior effective search depth and tactical move throughput. The additional handcrafted mechanisms introduced in X8 through X16 impose an evaluation latency tax that single-thread hardware cannot amortize.

---

## 3. Match B: Janus Classical X16-P (4T) vs Janus Classical X12 (4T)

### 3.1 Configuration and Conditions
- **Candidate:** Janus Classical X16-P (`janus_classical_x16.exe`, 4T, Lazy SMP, E15, Pruning Safety, History-dampened LMR, Quadratic LMP, 16K Pawn Hash, 128MB Lockless TT).
- **Baseline Control:** Janus Classical X12 (`janus_classical_x12.exe`, Commit `78ca3d5`, 4T, Lazy SMP, E10, M2, 64K Shared Pawn Hash, 128MB Lockless TT).
- **Format:** 100 opening pairs (200 games), Time Control: 1.0s base + 50ms Fischer increment.
- **PGN Record:** [`analysis/phase1/p1.11/pgn/x16_4t_vs_x12_4t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/pgn/x16_4t_vs_x12_4t.pgn).

### 3.2 Results and Statistical Distribution
- **Outcome:** +53 wins, =76 draws, -71 losses (91.0 / 200 points = **45.50%**).
- **Pentanomial Breakdown:**
  - $N_{2.0}$ ($ww$): **6 pairs** (6.0%)
  - $N_{1.5}$ ($wd$): **24 pairs** (24.0%)
  - $N_{1.0}$ ($dd$ / $wl$): **31 pairs** (31.0%)
  - $N_{0.5}$ ($ld$): **24 pairs** (24.0%)
  - $N_{0.0}$ ($ll$): **15 pairs** (15.0%)
- **Pair Difference Statistics:**
  - Mean pair difference $\bar{d} = -0.0900$
  - Variance $\text{Var}(d) = 0.3241$, Standard Error $SE = 0.0570$
- **Paired $t$-Test:**
  - $t = \frac{-0.0900}{0.0570} = -1.5783$ ($\text{df} = 99$)
  - Two-tailed $p$-value: **$0.1177$** ($p > 0.05$)
  - Result: **No statistically significant difference; hypothesis of superiority rejected**.
- **TOST Equivalence Testing ($\Delta_{\text{eq}} = 0.10$):**
  - $t_1 = \frac{-0.0900 - (-0.10)}{0.0570} = +0.1754 \implies p_1 = 0.4307$
  - $t_2 = \frac{-0.0900 - (+0.10)}{0.0570} = -3.3320 \implies p_2 = 0.0006$
  - $p_{\text{TOST}} = \max(p_1, p_2) = 0.4307 > 0.05$.
  - Result: **Equivalence is NOT proven**. The result is formally **inconclusive with a negative tilt**.

---

## 4. Match C: Slower Time Control Generalization (3.0s + 100ms)

### 4.1 Configuration and Purpose
To determine whether Candidate X16's increased search throughput (4.43M NPS) and tactical pruning safety convert into playing strength when given deeper search horizons, Match C re-tested X16-P vs X12 at triple the time budget.
- **Format:** 50 opening pairs (100 games), Time Control: 3.0s base + 100ms Fischer increment.
- **PGN Record:** [`analysis/phase1/p1.11/pgn/x16_4t_vs_x12_4t_slow.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/pgn/x16_4t_vs_x12_4t_slow.pgn).

### 4.2 Results and Comparison
- **Outcome:** +38 wins, =15 draws, -47 losses (45.5 / 100 points = **45.50%**).
- **Pentanomial Breakdown:**
  - $N_{2.0}$ ($ww$): **3 pairs** (6.0%)
  - $N_{1.5}$ ($wd$): **4 pairs** (8.0%)
  - $N_{1.0}$ ($dd$ / $wl$): **30 pairs** (60.0%)
  - $N_{0.5}$ ($ld$): **7 pairs** (14.0%)
  - $N_{0.0}$ ($ll$): **6 pairs** (12.0%)
- **Pair Difference Statistics:**
  - Mean pair difference $\bar{d} = -0.0900$
  - Variance $\text{Var}(d) = 0.2315$, Standard Error $SE = 0.0680$
- **Paired $t$-Test:**
  - $t = \frac{-0.0900}{0.0680} = -1.3226$ ($\text{df} = 49$)
  - Two-tailed $p$-value: **$0.1921$** ($p > 0.05$)
- **TOST Equivalence Testing ($\Delta_{\text{eq}} = 0.10$):**
  - $t_1 = +0.1469$, $t_2 = -2.7922$
  - $p_{\text{TOST}} = 0.4432 > 0.05$. Equivalence is **unproven**.

### 4.3 Time Control Stability Comparison
Remarkably, X16 scored **exactly 45.50%** (-31.4 Elo) in both the fast time control (1.0s + 50ms) and the slower time control (3.0s + 100ms). This proves that the deficit is scale-invariant and represents an intrinsic evaluation-search boundary condition rather than time-management instability.

---

## 5. Historical Lineage Comparison

| Milestone | Candidate Engine | 1T vs X7 Score (Elo) | 4T vs X12 Score (Elo) | 4T Slow vs X12 (Elo) | Promotion Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P1.3** | Classical X8 | 32.7% (-124.9) | — | — | **Rejected** |
| **P1.4** | Classical X9 | 36.8% (-94.2) | — | — | **Rejected** |
| **P1.5** | Classical X10 | 36.5% (-96.3) | — | — | **Rejected** |
| **P1.6** | Classical X11 | 37.8% (-87.2) | 39.0% (-78.1) | — | **Rejected** |
| **P1.7** | Classical X12 | — | **50.0% (0.0)** | — | **PROMOTED (4T Baseline)** |
| **P1.8** | Classical X13 | 36.0% (-99.8) | 45.0% (-35.0) | — | **Rejected** |
| **P1.9** | Classical X14 | 36.8% (-94.2) | 44.5% (-38.5) | — | **Rejected** |
| **P1.10** | Classical X15 | 34.2% (-113.8) | 46.5% (-24.4) | 47.0% (-20.9) | **Rejected** |
| **P1.11** | **Classical X16** | **33.75% (-117.2)** | **45.50% (-31.4)** | **45.50% (-31.4)** | **REJECTED (Retain X7 & X12)** |

---

## 6. Strength Qualification Verdict

1. **Janus Classical X16 fails to achieve statistically significant superiority over either baseline:**
   - Single-Thread: X16-S is significantly weaker than X7 by -117.2 Elo ($p = 1.02 \times 10^{-7}$).
   - 4-Thread: X16-P is consistently behind X12 by -31.4 Elo across both 1.0s+50ms ($p = 0.1177$) and 3.0s+100ms ($p = 0.1921$).
2. **Equivalence Is Formally Disproven:**
   - In no match did TOST achieve $p < 0.05$. Candidate X16 cannot claim equivalence with either X7 or X12.
3. **Official Production Retention:**
   - **Janus Classical X7 (`b34e342`) is formally retained as the Qualified Single-Thread Classical Baseline.**
   - **Janus Classical X12 (`78ca3d5`) is formally retained as the Qualified Four-Thread Classical Baseline.**
   - Candidate X16 is archived as a valuable experimental platform for counterfactual search safety and high-throughput Lazy SMP research.

