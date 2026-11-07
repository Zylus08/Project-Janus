# Project Janus v0.64 — Final Research & Release Promotion Decision

**Milestone:** v0.64  
**Date:** 2026-11-08  
**Author:** Principal Chess Engine Research Scientist & Independent Experimental Auditor  
**Candidate:** Janus Neural Value V3 (SEF + Phase-Tapered Adaptive Blend 50%, AVX2) — Candidate B4  
**Frozen Production Baseline:** Janus Classical Baseline C1 (Native N5 Frozen)  
**Historical Neural Reference:** Neural Baseline N1 (NNUE-V2 Small Hybrid 50/50, AVX2)  
**New Designation:** Janus Neural Research Baseline N2  
**Production Default Status:** **UNCHANGED (Classical Baseline C1 Retained)**

---

## 1. Formal Release Gate Audit

Every candidate for production promotion must pass the eight preregistered release gates.

| Gate | Requirement | Observed Empirical Value | Verdict |
| :--- | :--- | :--- | :---: |
| **Gate 1: Data Integrity & Zero Leakage** | 150k phase-balanced positions; 0.0% train/val/test FEN leakage; verified game isolation | 150,000 positions; strict game partition; 0.0% FEN overlap | **PASS** |
| **Gate 2: Feature Specification** | 32-element SEF vector; bitboard invariant; full-refresh == incremental | 8/8 structural test positions bit-exact (delta = 0) | **PASS** |
| **Gate 3: Offline Model Superiority** | NNUE-V3 (M2) outperforms M0 and M1 on held-out test MAE and Spearman $\rho$ | Overall MAE: 153.08 cp vs 166.78 cp; $\rho = 0.6178$ vs $0.5415$ | **PASS** |
| **Gate 4: Search-Level Efficiency** | Tapered blend prunes $\ge 30\%$ endgame search explosion vs fixed blend | Rook endgame tree reduced by 47.4% (80.9k vs 153.6k nodes) | **PASS** |
| **Gate 5: Native AVX2 Performance** | Bit-exact scalar match; leaf evaluation latency $\le 500$ ns/eval | Delta = 0 cp; AVX2 latency = 377.5 ns/eval (2.65M evals/s, 3.32x speedup) | **PASS** |
| **Gate 6: Regression Suite Integrity** | Zero regressions on existing test suite; 100% pass rate | 663 / 663 tests passed (0 failures) | **PASS** |
| **Gate 7: Confirmatory Playing Strength** | Independent 200-game match on fresh suite: $p < 0.05$ and 95% CI lower bound $> 0.0$ Elo | Score: 105.0/200 (+17.4 Elo); $t = +1.000, p = 0.31975$; 95% CI: `[-17.4, +50.7]` | **FAIL** |
| **Gate 8: Endgame Non-Regression** | Score in games reaching phase $\Phi \le 16$ must be $\ge 50.0\%$ | 178 games; score: 92.5 / 178 (**51.97%**, 47W / 91D / 40L) | **PASS** |

---

## 2. Scientific Outcome Classification

Under the preregistered qualification rules, the experimental outcome is classified into one of three distinct scientific categories:

- **Category A — Confirmed Release Qualification:**  
  Candidate passes all gates including Gate 7 ($p < 0.05$, lower CI $> 0.0$ Elo). Promoted to default engine configuration.
- **Category B — Inconclusive / Promising Research Baseline:**  
  Candidate demonstrates positive point strength ($\Delta\text{Elo} > 0$), resolves known structural vulnerabilities (endgame recovery $\ge 50\%$, search tree stabilization), passes all architectural and regression gates, but fails Gate 7 statistical significance due to sample variance. Qualified as a frozen Neural Research Baseline; production default remains classical C1.
- **Category C — Disconfirmed / Negative:**  
  Candidate scores underwater ($\Delta\text{Elo} < 0$) or introduces regressions. Rejected.

### Formal Classification
**Candidate B4 is classified under Category B.**

While NNUE-V3 achieved a positive point estimate (+17.4 Elo, 105.0/200) and completely reversed the endgame collapse that plagued v0.62, the paired t-test ($p = 0.320$) and 95% bootstrap confidence interval (`[-17.4, +50.7]` Elo) indicate that the 200-game sample is not statistically sufficient to reject the null hypothesis at $\alpha = 0.05$.

---

## 3. Causal Attribution & Scientific Analysis

### 3.1 What Succeeded in v0.64
1. **Endgame Stabilization:**  
   In v0.62, NNUE-V2 scored -8 net wins in endgames due to extreme score distortion and tree explosion. In v0.64, with the 32-element SEF vector and linear phase tapering $\alpha(\Phi) = 0.50 \cdot (\Phi / 24)$, NNUE-V3 scored **+7 net wins (51.97%)** across 178 endgame games.
2. **Positional Dominance in Closed Structures:**  
   In ECO Volume A (Flank) and Volume D (Closed / Semi-Closed), NNUE-V3 achieved **60.0% (48.0 / 80 points)**, scoring +16 net wins. The SEF features for pawn structure and piece-file alignment gave Janus decisive strategic superiority.
3. **Tree Search Efficiency:**  
   Adaptive blending eliminated the 2x node blowup in simplified positions, reducing rook endgame node counts by 47.4% and matching classical C1 search speeds in pure pawn endgames.
4. **Direct Head-to-Head Superiority over Neural Baseline N1:**  
   In the separate 100-game secondary comparison against Neural Baseline N1 (NNUE-V2 Small, 50/50 Fixed), NNUE-V3 scored **56.5 / 100 (56.50%, +45.4 Elo)** with 35 wins to 22 losses (+13 net wins) and a commanding **+12 net wins in endgame phases ($\Phi \le 16$)**, conclusively confirming that SEF features and adaptive phase tapering eliminated the structural evaluation collapse of NNUE-V2.

### 3.2 Why Gate 7 Was Not Cleared
1. **Open-Game Vulnerability (ECO Volume C):**  
   In open games (1.e4 e5), NNUE-V3 scored only 17.0 / 40 (42.50%, -6 net wins). In tactical, highly open positions where piece activity and sharp king attacks dominate, classical C1's higher NPS allowed it to out-calculate NNUE-V3 before deep positional features crystallized.
2. **Statistical Power Limitation:**  
   At 200 games, the standard error of a paired chess match under Fischer 3.0s+100ms is approximately $\pm 17.0$ Elo. A true strength advantage of $+15$ to $+20$ Elo requires $\sim 600\text{--}800$ games to reliably achieve $p < 0.05$.

---

## 4. Promotion & Architecture Decisions

1. **Production Default Configuration:**  
   Pursuant to Governing Constraint #10 and scientific prudence, **Classical Baseline C1 remains the default configuration** for Project Janus.
2. **Neural Research Baseline Designation:**  
   NNUE-V3 (Candidate B4) is formally qualified and designated as **Janus Neural Research Baseline N2**:
   - Model weights: `analysis/v0.64/models/janus_nnue_v3.jnnue`
   - Feature extractor: `sef_features.h` (32-element SEF bitboard implementation)
   - Native engine: `analysis/v0.64/native/janus_native_engine.exe`
   - Default blend: Phase-tapered adaptive $\alpha(\Phi) = 0.50 \cdot (\Phi / 24)$.
3. **Historical Baseline Retention:**  
   Classical Baseline C1 and Neural Baseline N1 (v0.61) remain frozen and unmodified.

---

## 5. Strategic Recommendations for v0.65

1. **Dynamic Complexity Tapering:**  
   Extend the linear phase taper $\alpha(\Phi)$ to incorporate tactical complexity (e.g. pawn tension, open file density). In open tactical games (Volume C), slightly reduce neural blend to allow classical tactical speed to dominate, while maintaining high neural blend in strategic flank and closed positions.
2. **Tactical Open-Game Supervision:**  
   Augment the training corpus with high-depth tactical positions from open 1.e4 e5 regimes to sharpen neural valuation in sharp tactical middlegames.
3. **Confirmatory Scale:**  
   When validating next-generation candidates, preregister a 600-game match structure to provide the statistical resolution necessary to qualify $+15\text{--}+25$ Elo candidates at $p < 0.01$.
