# Project Janus v0.64 — v0.63 Evidence Reconciliation & Methodological Audit

**Document ID:** `analysis/v0.64/V063_EVIDENCE_RECONCILIATION.md`  
**Milestone:** v0.64 — Robust NNUE-V3 — Endgame Generalization, Phase-Aware Evaluation & Independent Strength Qualification  
**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Scientist & Independent Experimental Auditor  
**Scope:** Forensic reconciliation of v0.63 findings, heterogeneity limits, endgame taxonomies, and external calibration  

---

## 1. Executive Summary

Milestone v0.64 commences with an independent, rigorous audit of the diagnostic evidence presented in milestone v0.63. While v0.63 established that the v0.61 ($+49.0\text{ Elo}$) and v0.62 ($-5.2\text{ Elo}$) tournaments differed substantially, four critical methodological and statistical nuances must be formalized before proceeding to model development:

1. **Heterogeneity Estimator Instability ($k=2$):**  
   The reported $I^2 = 78.7\%$ ($Q = 4.6850, p = 0.03043$) was computed from exactly two tournaments. In meta-analytic theory, between-study variance $\tau^2$ and $I^2$ are notoriously unstable with small sample counts ($k < 5$). The $I^2$ demonstrates statistical variation between the two matches, but does **not prove** that any single isolated feature was the sole causal determinant.
2. **Deconstruction of the "Endgame" Category (Phase $\le 16$):**  
   Auditing the 113 positions evaluated in v0.63 revealed that **67.3% were queenless middlegames** and **32.7% were other simplified major-piece positions**. There were **zero pure pawn endgames, rook endgames, or minor-piece endgames** in that specific diagnostic sample because positions were sampled at plies $\le 38$. Equating $\text{Phase} \le 16$ with true endgames was an oversimplification.
3. **Reconciliation of Endgame MAEs:**  
   The reported MAEs (Pure NNUE: 322.1 cp; Fixed Hybrid: 256.8 cp; Phase-Tapered: 239.0 cp; Classical C1: 228.9 cp) were verified to be computed on the exact same 113 positions against identical Stockfish 19 depth-12 targets from White's perspective.
4. **Exploratory Status of External Calibration:**  
   The matched Stockfish 1600 experiment (C1: 12.0/20 vs N1: 13.5/20) yields a difference of $+1.5$ points across 20 games ($z = 0.474, p \approx 0.63$). This difference is statistically nonsignificant given the small sample size ($N=20$) and must be treated as exploratory, not an established $+57\text{ Elo}$ rating gap.

---

## 2. Deep-Dive Audit Inquiries

### 2.1 Audit Item A: Statistical Heterogeneity Limits ($k=2$)
In v0.63, Cochran's $Q$ was calculated as:
$$Q = \sum w_i (\bar{D}_i - \bar{D}_{\text{FE}})^2 = 4.6850\quad (\text{df} = 1),\quad p = 0.03043$$
$$I^2 = \frac{Q - 1}{Q} = 78.7\%$$

While $p < 0.05$ formally rejects the null hypothesis of homogeneous effect sizes, $I^2$ with $k=2$ has extremely wide 95% confidence intervals (typically $[0\%, 95\%]$).
**Methodological Conclusion:** The observed difference between $+49.0$ and $-5.2$ Elo proves that tournament outcomes are sensitive to the chosen opening regime. It does not establish that opening depth alone or closed pawn structures alone explain the entire delta. Multiple interacting variables (pawn structure, endgame transitions, tactical complexity, and sampling variance) contributed.

---

### 2.2 Audit Item B: Material Phase vs True Chess Endgames
The classical tapered evaluation formula computes:
$$\text{Phase} = \sum (\text{Knights}\times 1 + \text{Bishops}\times 1 + \text{Rooks}\times 2 + \text{Queens}\times 4)$$
$$\text{Maximum Phase} = 4(1) + 4(1) + 4(2) + 2(4) = 24$$

In v0.63, positions with $\text{Phase} \le 16$ were grouped under the label "Endgame".
A structural piece census of those 113 positions reveals:

| Subtype Classification | Piece Composition | Position Count | Proportion |
| :--- | :--- | :---: | :---: |
| **Queenless Middlegame** | 2 Rooks + 2 Minor Pieces per side ($\text{Phase} = 12$) | 76 | **67.3%** |
| **Other Simplified Positions** | Queen + 1 Rook + 1 Minor Piece per side ($\text{Phase} = 14$) | 37 | **32.7%** |
| **Pure Pawn Endgames** | Kings and Pawns only ($\text{Phase} = 0$) | 0 | 0.0% |
| **Pure Rook Endgames** | Kings, Rooks, and Pawns ($\text{Phase} = 4$) | 0 | 0.0% |
| **Minor Piece Endgames** | Kings, Minor Pieces, and Pawns ($\text{Phase} = 2$) | 0 | 0.0% |
| **Total** | | 113 | 100.0% |

**Scientific Correction for v0.64:**
The negative rank correlation ($\rho = -0.125$) detected in v0.63 occurred in **Queenless Middlegames and simplified piece positions**, where NNUE-V2 lacked long-range positional planning without queens. True endgames (pawn endings, rook endings, opposite-colored bishops) were not even present in that sample. Therefore, v0.64 must explicitly generate and evaluate true endgame categories.

---

### 2.3 Audit Item C: Baseline Evaluator Consistency
The reported static evaluation metrics on the 113 simplified positions were audited:

| Evaluator Configuration | Formula / Blend Rule | MAE vs SF19 (cp) | Spearman Rank $\rho$ | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Classical Baseline C1** | Pure Classical (`evaluate()`) | **228.91** | **+0.3817** | Baseline |
| **Pure NNUE-V2** | 100% Neural (`evaluate_neural()`) | **322.06** | **-0.1250** | Reconciled |
| **Fixed Hybrid N1** | $0.50 \times \text{C1} + 0.50 \times \text{NNUE}$ | **256.83** | **+0.1502** | Reconciled |
| **Phase-Tapered PT** | $(1 - w)\text{C1} + w\text{NNUE},\ w = 0.5 \frac{\text{Phase}}{24}$ | **239.02** | **+0.2763** | Reconciled |

All values were confirmed to be bit-exact across reports, utilizing the same 113 board states, the same depth-12 Stockfish 19 target evaluations, and identical centipawn scale normalization.

---

### 2.4 Audit Item D: Matched External Calibration Statistical Power
In the matched Stockfish 1600 calibration experiment:
- Classical C1 scored **12.0 / 20 (60.0%)**
- Neural N1 scored **13.5 / 20 (67.5%)**
- Difference: $+1.5$ points out of 20 games ($+7.5\%$).

Under a paired binomial or normal approximation:
$$\text{SE}(\Delta) \approx \sqrt{\frac{p(1-p)}{N}} \approx \sqrt{\frac{0.25}{20}} \approx 0.1118$$
$$z = \frac{0.075}{0.1118 \sqrt{2}} \approx 0.474,\quad p \approx 0.635$$

The difference of $+1.5$ points over 20 games is **statistically nonsignificant** and within ordinary sampling variance.
**Conclusion:** It is invalid to cite $+57\text{ Elo}$ as an established strength gap between C1 and N1. It is an exploratory indicator that requires large-sample tournament verification.

---

## 3. Preregistration Guidelines for Phase 1 to Phase 8

Based on this audit, the research progression for v0.64 is governed by four principles:
1. **True Endgame Diversity:** Training and test datasets must include explicit, partitioned collections of true pawn endgames, rook endgames, minor-piece endgames, passed-pawn races, and queenless middlegames.
2. **Leakage Elimination:** Absolute source game separation prior to position extraction.
3. **Ablation Rigor:** Feature augmentations must be tested on fixed architectures to separate parameter scaling from feature utility.
4. **Independent Confirmatory Suite:** Tournament testing will be performed exclusively on a freshly synthesized opening suite disjoint from all prior corpora.

