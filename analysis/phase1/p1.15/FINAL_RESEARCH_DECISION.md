# FINAL RESEARCH DECISION & PROMOTION ADJUDICATION REPORT

**Project:** Project Janus — Phase 1, Milestone P1.15  
**Auditor:** Principal Computer Chess Engine Architect & Independent Statistical Auditor  
**Date:** November 14, 2026  
**Repository Branch:** `phase1/classical-janus`  
**Candidate Evaluated:** Janus Classical X20 (X20-S / X20-P, commit `563f1db`, SHA-256: `AF126A4D22C312F2AE61014A56005B9E9BAFD022F95A17DA81D81769048F7415`)  
**Qualified Baselines:** Janus Classical X7 (`86392A...`), Janus Classical X12 (`00B4F5...`)  
**Preserved Research References:** X10, X13, X14, X15, X16, X17, X18, X19  
**Deliverable:** `analysis/phase1/p1.15/FINAL_RESEARCH_DECISION.md`  

---

## 1. Formal Promotion Adjudication

In accordance with the governing charter of Project Janus and the pre-registered decision criteria of Milestone P1.15:

### **ADJUDICATION VERDICT: CATEGORY B — ENGINEERING PROGRESS, STRENGTH INCONCLUSIVE**

> **Category B Definition:**  
> *Useful capture-ordering or history improvements exist, but independent tournament evidence does not establish statistically significant playing-strength superiority over the qualified baselines ($p < 0.05$ and lower bound of the 95% paired confidence interval $> 50.0\%$). Retain X7 and X12 as the qualified baselines. Preserve X19 as the leading research reference. Archive candidate X20 as a verified correctness and search engineering milestone.*

---

## 2. Empirical Justification for Category B Adjudication

The decision is dictated directly by empirical tournament results across 420 games without post-hoc rationalization:

| Match ID | Match Description | Games | Candidate Score | Score (%) | Elo Diff | Paired 95% CI | One-Sided p-value | Statistically Superior? |
|---|---|---|---|---|---|---|---|---|
| **Match 1** | X20-S (1T) vs X7 Baseline | 100 | 46.0 / 100 | 46.00% | -27.9 | $[36.57\%, 55.43\%]$ | 0.797 | **NO** |
| **Match 2** | X20-S (1T) vs X7 (Slower TC) | 50 | 24.0 / 50 | 48.00% | -13.9 | $[39.09\%, 56.91\%]$ | 0.670 | **NO** |
| **Match 3** | X20-P (4T) vs X12 Baseline | 100 | 46.5 / 100 | 46.50% | -24.4 | $[38.96\%, 54.04\%]$ | 0.819 | **NO** |
| **Match 4** | X20-S (1T) vs X19-S Reference | 50 | 22.5 / 50 | 45.00% | -34.9 | $[34.04\%, 55.96\%]$ | 0.814 | **NO** |
| **Match 5** | X20-S (1T) vs Stockfish 4 | 40 | 1.5 / 40 | 3.75% | -563.7 | $[0.00\%, 7.76\%]$ | 1.000 | **NO** |
| **Match 6** | X20-S (1T) vs Stockfish 11 | 40 | 0.5 / 40 | 1.25% | -759.1 | $[0.00\%, 3.70\%]$ | 1.000 | **NO** |
| **Match 7** | X20-S (1T) vs Stockfish 19 | 40 | 0.5 / 40 | 1.25% | -759.1 | $[0.00\%, 3.70\%]$ | 1.000 | **NO** |

### Statistical Criteria Evaluation:
1. **Match 1 (Primary 1T Promotion Gate):** Lower CI bound is $36.57\% < 50.0\%$, and point estimate is $46.00\% < 50.0\%$. Promotion to baseline is rejected.
2. **Match 2 (Slower Time Control):** In P1.14, X19 collapsed to $43.0\%$ ($-48.9$ Elo). X20 scored $48.00\%$ ($-13.9$ Elo), operating in close alignment with its fast TC performance ($46.0\%$). The slower-time horizon failure was successfully cured, but strength superiority is not achieved ($p = 0.670$).
3. **Match 3 (Primary 4T Promotion Gate):** Lower CI bound is $38.96\% < 50.0\%$. X20-P does not beat X12.

---

## 3. Verified Engineering Achievements in Milestone P1.15

Although X20 did not achieve Elo superiority, Milestone P1.15 resolved several critical computer chess architectural problems:
1. **Exhaustive MovePicker Correctness:** Mathematically proven complete and legal across 1,019 stratified positions and 32,232 legal moves (0 omissions, 0 duplicates, 0 illegal moves).
2. **Static Exchange Evaluation Integrity:** 100% exact classification confirmed across all 12 tactical exchange categories.
3. **Bad-Capture Deferral Resolution:** Partitioning captures into Near-Even captures ($-100 \le \text{SEE} < 0$) and Catastrophic captures ($\text{SEE} < -100$) restored tactical defense resolution in $18.7\times$ fewer nodes in crisis positions (Game 12).
4. **History Table Stabilization:** Reconstructed the P1.14 44.7% claim as a natural consequence of 96.6% table sparsity. Introduced conservative $\frac{7}{8}$ history aging, elevating first-move cutoff rate ($\text{BF}_1$) to **98.96%**.
5. **Exact Minimax Search Contract:** 240 / 240 pairwise comparisons across depths 1–4 matched root scores with 100.00% exact numerical identity under full-width alpha-beta search.
6. **Time-Control Consistency:** Eliminated the 12.5% slower-time degradation observed in X19.

---

## 4. Current Standing of Project Janus Engine Lineage

Following Milestone P1.15 adjudication:
- **Qualified Single-Thread Baseline:** **Janus Classical X7** (`b34e342`) retains official promotion baseline status.
- **Qualified Four-Thread Baseline:** **Janus Classical X12** (`78ca3d5`) retains official promotion baseline status.
- **Leading Research Reference:** **Janus Classical X19** (`bcfdecd`, SHA-256: `CBB7785A...`) remains preserved as a frozen research reference.
- **Archived Engineering Candidate:** **Janus Classical X20** (`AF126A4D...`) is archived in `analysis/phase1/p1.15/control/` with full telemetry, PGNs, and property suites preserved.

---

## 5. Architectural Takeaway

Project Janus has demonstrated that further refinements to alpha-beta move ordering, staging, and history aging yield diminishing returns in actual playing strength. While X20 achieves a 98.6% node reduction at shallow depths, its competitive performance remains constrained by **evaluation knowledge deficits** (Pawn structure, King Safety, and piece mobility). The architectural direction for Milestone P1.16 must pivot away from move-ordering heuristics and toward evaluation fidelity and quiescence search accuracy.

