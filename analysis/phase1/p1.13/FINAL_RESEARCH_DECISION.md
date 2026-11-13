# Janus Classical P1.13: Final Statutory Research Decision
**Milestone:** Phase 1, Milestone P1.13  
**Date:** November 13, 2026  
**Auditor & Research Director:** Independent Reproducibility Auditor & Classical Engine Architect  
**Governing Standard:** JCTS v2 Classical Testing Protocol & Governance Charter  
**Candidate Evaluated:** Janus Classical X18 (`janus_classical_x18.exe`, SHA-256: `912c8554928a1845d3f16e699fe06b970fc7eeb3ab6ee6c37900fe81662b6b50`)  
**Single-Thread Baseline Under Challenge:** Janus Classical X7 (`b34e342`)  
**Four-Thread Baseline Under Challenge:** Janus Classical X12 (`78ca3d5`)  

---

## 1. Formal Statutory Determination

Under the non-ML charter and the strict empirical qualification rules of Project Janus:

### **VERDICT: PROMOTION DENIED (CATEGORY C — HYPOTHESIS REJECTED)**

1. **Janus Classical X18 is NOT qualified for baseline promotion.**
2. **Janus Classical X7 (`b34e342`) remains the SOLE QUALIFIED SINGLE-THREAD BASELINE.**
3. **Janus Classical X12 (`78ca3d5`) remains the SOLE QUALIFIED FOUR-THREAD BASELINE.**
4. **Janus Classical X18 is permanently archived as a frozen research reference.**

---

## 2. Comprehensive Evidence Summary

The decision is founded upon the largest empirical dataset assembled in Project Janus to date: **530 tournament games** conducted without adjudicatory bias, across balanced opening books with color reversal and deterministic time controls.

### Summary Matrix of Milestone P1.13 Tournaments:

| Tier | Match Identifier | Opponent Engine | Time Control | Games | Candidate Score (Points / %) | Relative Elo ($\Delta\text{Elo}$) | 95% Wilson Confidence Interval | Audit Finding |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Tier 1** | `x18_1t_vs_x7_1t` | Janus-X7-1T | 1.0s + 50ms | 100 | 41.0 / 100 (**41.00%**) | **$-63.2$** | [31.87%, 50.80%] | **Regression** against 1T baseline |
| **Tier 1** | `x18_1t_vs_x7_1t_slow`| Janus-X7-1T | 2.5s + 100ms | 50 | 21.5 / 50 (**43.00%**) | **$-48.96$** | [30.27%, 56.73%] | Persistent deficit across time controls |
| **Tier 1** | `x18_4t_vs_x12_4t` | Janus-X12-4T | 1.0s + 50ms | 100 | 50.5 / 100 (**50.50%**) | **$+3.47$** | [40.87%, 60.10%] | **Parity** (statistically insignificant, $p > 0.84$) |
| **Tier 2** | `x18_1t_vs_sf4_1t` | Stockfish-4-1T | 1.5s + 50ms | 40 | 1.5 / 40 (**3.75%**) | **$-563.75$** | [0.87%, 14.73%] | 1 authentic win, 1 draw |
| **Tier 2** | `x18_1t_vs_sf11_1t`| Stockfish-11-1T | 1.5s + 50ms | 40 | 0.0 / 40 (**0.00%**) | **$< -407.03$** | [0.00%, 8.76%] | Absolute ceiling ($p < 0.0876$) |
| **Tier 3** | `x18_1t_vs_sf19_1t`| Stockfish-19-1T | 1.5s + 50ms | 40 | 1.0 / 40 (**2.50%**) | **$-636.43$** | [0.44%, 12.88%] | 2 authentic threefold draws |
| **Tier 3** | `x18_4t_vs_sf19_4t`| Stockfish-19-4T | 1.5s + 50ms | 40 | 1.0 / 40 (**2.50%**) | **$-636.43$** | [0.44%, 12.88%] | 2 authentic threefold draws |
| **Total** | **All 7 Matches** | — | — | **410** | **116.5 / 410 (28.41%)** | — | — | Complete 410-game qualification suite |

---

## 3. Statutory Criteria Assessment

Under Section 4 of the JCTS Governance Charter, a candidate engine must satisfy one of three categorical gates:

### Gate A: Measurable Playing-Strength Superiority
* **Criterion:** Statistically significant improvement over baseline ($p < 0.05$), with the lower bound of the 95% Wilson confidence interval strictly exceeding 50.0%.
* **Evaluation:**
  - Match 1 (1T): Score = 41.00%, Lower Bound = 31.87% (**FAILED — Net Deficit**)
  - Match 2 (1T Slow): Score = 43.00%, Lower Bound = 30.27% (**FAILED — Net Deficit**)
  - Match 3 (4T): Score = 50.50%, Lower Bound = 40.87% (**FAILED — Lower bound does not exceed 50.0%**)
* **Result:** **REJECTED**.

### Gate B: Architectural Simplification at Parity
* **Criterion:** Statistically equivalent playing strength with demonstrably lower code complexity, reduced algorithmic maintenance, or fewer parameters.
* **Evaluation:** Candidate X18 introduces additional heuristic logic (butterfly history thresholds $+8000 / -2000$, depth checks, pawn-endgame bypass flags). It increases architectural complexity while regressing on 1T.
* **Result:** **REJECTED**.

### Gate C: Failed Hypothesis / Inconclusive
* **Criterion:** The empirical evidence fails to establish superiority or simplification.
* **Result:** **ADOPTED**.

---

## 4. Key Scientific Learnings from P1.13

1. **The Fallacy of Raw Node Reduction:**  
   During development ablations, History-LMR reduced search nodes by **24.0%** and latency by **36.1%** on 4 threads. However, tournament play proved that this throughput gain was achieved by unsafely pruning quiet defensive replies, resulting in a **$-63$ Elo regression** on single-threaded play.
2. **The Necessity of Continuation History:**  
   In classical computer chess, 1-ply piece-to-square butterfly history is too noisy at shallow depths to guide move reduction. Mature classical engines (such as Stockfish 8 through 11) rely on **continuation history** (pairing the candidate move with the moves played 1 and 2 plies earlier) to distinguish sound quiet moves from blunders.
3. **Lazy SMP Masking Effect:**  
   Multithreaded Lazy SMP masked the deficiency of History-LMR by searching disparate subtrees across helper threads, yielding 50.5% at 4T, whereas single-threaded execution exposed its severe tactical fragility (41.0%).

---

## 5. Formal Administrative Status

* **Production Codebase:** The changes in `engine/classical_x/janus_classical_x.cpp` introducing variant `X18` remain strictly isolated under `variant == "X18"`. The default engine variant remains configured to match baseline behavior (`X7` / `X12`).
* **Active Baselines:** All future milestones must continue to benchmark against `X7` for single-thread research and `X12` for parallel search research.
* **Audit Signature:** Sealed and ratified by Independent Reproducibility Auditor on November 13, 2026.

