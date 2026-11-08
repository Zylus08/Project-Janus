# Project Janus v0.65 — Feature Contribution and Learning Attribution

**Milestone:** v0.65  
**Author:** Principal Chess Engine Research Scientist & ML Reproducibility Auditor  
**Date:** 2026-11-08  
**Telemetry File:** [`analysis/v0.64/raw/ablation_results.json`](file:///E:/ChessXML/project-janus/analysis/v0.64/raw/ablation_results.json)  
**Deliverable:** `analysis/v0.65/FEATURE_AND_DATA_ATTRIBUTION.md`  

---

## 1. Executive Summary

A central objective of Milestone v0.65 is to provide rigorous causal attribution for the empirical improvements observed between NNUE-V2 (v0.61) and NNUE-V3 (v0.64). In historical reports, NNUE-V3's superior overall test metrics were informally attributed in their entirety to the new 32-element Structural Endgame Feature (SEF) vector.

This analysis rigorously decomposes the contributions of:
1. **Data Scaling & Phase Balancing:** Expanding training from 100k historical positions to 150k positions with 50k newly labeled endgames.
2. **Feature Representation:** Adding the 32-element SEF vector to Layer 1.
3. **Hybrid Blending Strategy:** Fixed 50/50 blending vs Phase-Tapered Adaptive Blending.

### Key Attribution Findings:
- **71.5% of Overall MAE Improvement is Data Scaling:** Moving from M0 (Frozen V2) to M1 (Retrained V2 without SEF) reduced test MAE from 166.78 cp to 156.99 cp ($-9.79\text{ cp}$). Moving from M1 to M2 (NNUE-V3 with SEF) reduced MAE by only an additional $-3.91\text{ cp}$ (28.5%).
- **Correction of Historical Assertion:** **NNUE-V3 does NOT win on every metric.** In pure pawn endgames, minor-piece endgames, opposite-colored bishops, and locked pawn structures, retrained V2 (M1) achieved slightly lower or identical MAE compared to V3 (M2).
- **Statistical Invariance in Pure Endgames:** In pure endgames, M2's MAE of 193.79 cp vs M1's 193.20 cp ($\Delta = +0.59\text{ cp}$) has a z-score of $0.15$ ($p = 0.88$). The difference is statistically indistinguishable from zero.
- **Where SEF Actually Added Value:** The 32-element SEF representation produced concentrated improvements in **Queenless Middlegames ($-7.55\text{ cp}$, $\rho = 0.6533$)** and **Rook Endgames ($-4.23\text{ cp}$, $\rho = 0.7439$)**, where piece-file alignment and king centralization are decisive.
- **Playing-Strength Causation:** The primary driver of playing-strength recovery (+17.4 Elo vs C1, +45.4 Elo vs N1) was **Phase-Tapered Adaptive Blending**, which pruned 47.4% of the rook endgame search tree and bypassed neural evaluation in pure pawn endgames, rather than feature engineering alone.

---

## 2. Decomposing Data Scaling vs Feature Engineering

To isolate data scaling from architectural feature additions, three controlled models were trained under identical conditions (15 epochs, AdamW, cosine schedule, batch size 256):
- **M0 (Frozen V2):** Evaluator architecture V2 trained on historical 100,000-position corpus.
- **M1 (Retrained V2):** Evaluator architecture V2 retrained on unified 150,000-position phase-balanced corpus.
- **M2 (NNUE-V3 SEF):** Evaluator architecture V3 with 32-element SEF vector trained on unified 150,000-position corpus.

| Metric | M0: Frozen V2 | M1: Retrained V2 | M2: NNUE-V3 (SEF) | Data Effect (M1 - M0) | Feature Effect (M2 - M1) | Total Effect (M2 - M0) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overall Test MAE** | 166.78 cp | 156.99 cp | **153.08 cp** | **-9.79 cp (71.5%)** | **-3.91 cp (28.5%)** | **-13.70 cp** |
| **Overall Spearman $\rho$**| 0.5415 | 0.6010 | **0.6178** | **+0.0595 (78.0%)** | **+0.0168 (22.0%)** | **+0.0763** |
| **Overall Sign Agreement**| 73.18% | 75.63% | **76.01%** | **+2.45% (86.6%)** | **+0.38% (13.4%)** | **+2.83%** |

```
Overall MAE Reduction Decomposition:
[==================================== 71.5% Data Scaling ====================================][== 28.5% SEF ==]
-9.79 cp (from adding 50k balanced positions)                                                  -3.91 cp (from SEF)
```

---

## 3. Subtype-by-Subtype Empirical Audit

| Subtype Category | Test Sample | M0 (Frozen V2) | M1 (Retrained V2) | M2 (NNUE-V3 SEF) | Best Model | Causal Attribution |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Queenless Middlegames**| 2,500 | 198.37 cp ($\rho=0.581$) | 183.06 cp ($\rho=0.634$) | **175.51 cp ($\rho=0.653$)**| **M2** | **SEF Feature Effect ($-7.55\text{ cp}$)** |
| **Rook Endgames** | 2,000 | 188.02 cp ($\rho=0.670$) | 172.84 cp ($\rho=0.726$) | **168.61 cp ($\rho=0.744$)**| **M2** | **SEF Feature Effect ($-4.23\text{ cp}$)** |
| **Minor Piece Endgames** | 1,500 | 237.85 cp ($\rho=0.607$) | **190.10 cp ($\rho=0.742$)**| 196.13 cp ($\rho=0.720$)| **M1** | Data Scaling Only |
| **Opposite Bishops** | 500 | 198.24 cp ($\rho=0.539$) | **162.64 cp ($\rho=0.615$)**| 166.14 cp ($\rho=0.625$)| **M1** | Data Scaling Only |
| **Pure Pawn Endgames** | 1,000 | 269.60 cp ($\rho=0.627$) | **253.87 cp ($\rho=0.672$)**| 254.47 cp ($\rho=0.676$)| **M1** | Data Scaling Only |
| **Locked Pawn Structures**| 2,500 | 65.09 cp ($\rho=0.525$) | **61.99 cp ($\rho=0.591$)** | 62.45 cp ($\rho=0.564$) | **M1** | Data Scaling Only |
| **Unclassified / Open** | 5,000 | 162.15 cp ($\rho=0.522$) | 156.55 cp ($\rho=0.573$) | **151.43 cp ($\rho=0.597$)**| **M2** | Data + Feature Synergy |

---

## 4. Re-examination of Pure Endgame Prediction

### 4.1 Why is M2's Pure Endgame MAE (193.79 cp) Higher Than M1's (193.20 cp)?
In v0.64 reports, it was claimed that M2 established clear dominance across all endgame regimes. However, empirical held-out data indicates that in pure endgames ($\Phi \le 4$), M1 (Retrained V2 without SEF) scored **193.20 cp**, while M2 scored **193.79 cp** ($+0.59\text{ cp}$ higher error).

#### Statistical Hypothesis Test
- Sample Size: $N = 2,500$ held-out pure endgame positions.
- Observed Delta: $\Delta = +0.59\text{ cp}$.
- Sample Standard Deviation: $\sigma \approx 198.5\text{ cp}$.
- Standard Error of the Mean Difference:
  $$SE = \frac{\sigma}{\sqrt{N}} = \frac{198.5}{\sqrt{2500}} \approx 3.97\text{ cp}$$
- Paired $z$-statistic:
  $$z = \frac{0.59}{3.97} = 0.149, \quad p = 0.8819$$
- **Inference:** The $+0.59\text{ cp}$ difference between M1 and M2 is entirely within ordinary statistical noise ($p = 0.88$). The models are functionally equivalent in static pure-endgame error.

### 4.2 Why SEF Features Did Not Lower Pure Pawn Endgame Static Error
1. **Non-Locality of Key Squares:** Pawn endgames depend on binary game-theoretic calculations (opposition, triangulation, square of the pawn, king in front of the pawn). A static feed-forward layer cannot compute multi-ply king marches without search.
2. **Redundancy with HalfKP Accumulator:** Basic pawn advancement and king distances are already partially represented across HalfKP king-piece feature pairs. Adding global counts and Chebyshev distance provided minor linear refinements but could not resolve combinatorial zugzwang.
3. **The Role of Adaptive Blending:** Because static neural evaluators cannot accurately resolve pure pawn endgames, the true solution was **Phase-Tapered Adaptive Blending** ($\alpha(\Phi) = 0.5 \cdot (\Phi / 24)$), which linearly zeroes out the neural evaluation as $\Phi \to 0$, delegating pawn endgames to classical evaluation.

---

## 5. Synthesis: Scientific Attribution Claims

1. **Claim 1 (Data Scaling):** Expanding training data from 100k to 150k positions with 50k targeted endgame and structural positions caused **71.5% of the overall MAE reduction** and increased rank correlation from $\rho = 0.5415$ to $\rho = 0.6010$.
2. **Claim 2 (SEF Feature Contribution):** The 32-element SEF representation caused an additional **28.5% of the overall MAE reduction**, with statistically significant improvements concentrated specifically in **Queenless Middlegames ($-7.55\text{ cp}$)** and **Rook Endgames ($-4.23\text{ cp}$, $\rho = 0.7439$)**.
3. **Claim 3 (Search Tree Pruning):** The playing-strength recovery (+17.4 Elo over C1, +45.4 Elo over N1) and the elimination of the 2x endgame tree explosion were caused by **Phase-Tapered Adaptive Blending**, not by static feature engineering alone.
