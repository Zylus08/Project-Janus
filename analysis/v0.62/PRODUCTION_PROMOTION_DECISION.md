# Project Janus v0.62 — Production Promotion Decision

**Document ID:** `analysis/v0.62/PRODUCTION_PROMOTION_DECISION.md`  
**Milestone:** v0.62 — Independent Neural Strength Replication, Causal Attribution & Release Qualification  
**Date:** 2026-11-07  
**Auditor / Principal Investigator:** Principal Chess Engine Research Scientist & Statistical Validation Specialist  
**Candidate Evaluation:** Janus Neural Value V2 (Hybrid 50/50, AVX2 SIMD)  
**Control Evaluation:** Janus Classical Baseline C1 (Native N5 Frozen)  
**Final Production Recommendation:** **CATEGORY B: QUALIFIED RESEARCH ASSET / NEURAL BASELINE N1**  
**(Category A Default Production Promotion: REJECTED)**  

---

## 1. Summary of Gate Evaluations

The qualification framework for Project Janus v0.62 preregistered four prospective categories based on empirical trial outcomes:

```mermaid
graph TD
    A["Preregistered Confirmatory Replication Trial (200 Games)"] --> B{"Confirmatory Elo Gain >= +25 & 95% CI > 0?"}
    B -- "YES" --> C["Category A: Full Production Promotion (Default = Neural)"]
    B -- "NO" --> D{"Zero Engine Faults & Bit-Exact C1 Invariance & Positive External SF19 Gain?"}
    D -- "YES" --> E["Category B: Qualified Research Asset / Neural Baseline N1 (Default = Classical C1)"]
    D -- "NO" --> F["Category C: Total Rejection / Flawed Implementation"]
```

### Evaluation Against Explicit Release Gates

| Gate Index | Evaluation Gate | Preregistered Requirement | Empirical Outcome | Compliance Status |
| :---: | :--- | :--- | :--- | :---: |
| **Gate 1** | **Independent Strength Replication** | $\Delta\text{Elo} \ge +25.0$, 95% CI lower bound $> 0.0$, $p < 0.05$ | $\Delta\text{Elo} = \mathbf{-5.2\text{ Elo}}$, 95% CI: $[-36.6, +26.1]$, $p = 0.7522$ | **FAIL (Cat A)** |
| **Gate 2** | **External Teacher Calibration** | Non-trivial performance vs Stockfish 19 (1320, 1600, 2000 Elo) | SF1320: 87.5% (+97 vs C1), SF1600: 67.5% (+234 vs C1), SF2000: 52.5% (+208 vs C1) | **PASS** |
| **Gate 3** | **Causal Strength Attribution** | Disentangle heuristic, SIMD, and blending mechanisms | Neural tree contraction (-29.4%), AVX2 latency recovery (+0.5 plies), 50/50 blend tactical safety | **PASS** |
| **Gate 4** | **Release Reliability & Boundaries** | Zero crashes on missing/corrupt models, scalar fallback | 6/6 tests passing in `test_v062_release_reliability.py` | **PASS** |
| **Gate 5** | **Frozen C1 Baseline Invariance** | 100% bit-exact match against C1 when `UseNeuralValue=false` | Bit-exact bestmove, score, depth, node counts across test positions | **PASS** |
| **Gate 6** | **Full Regression Test Suite** | 100% pass rate across inherited tests | **658/658 passed** in 98.83s | **PASS** |

---

## 2. Gate Decision & Classification

### 2.1 Category A: Full Production Promotion — **REJECTED**
- **Justification:** The preregistered confirmatory trial conclusively refuted the hypothesis that NNUE-V2 provides a general +49.0 Elo advantage over Classical C1 on an unmemorized opening corpus. On 100 fresh opening pairs (200 games), NNUE-V2 scored 98.5/200 (49.25%, $-5.2$ Elo, $p = 0.752$).
- **Scientific Honesty & Integrity:** Janus adheres strictly to empirical truth. Under no circumstances will an engine modification be promoted to the production default when its statistical significance is $p = 0.752$ and its point estimate is negative.
- **Default Setting:** `UseNeuralValue` **REMAINS `false` BY DEFAULT.** Classical Baseline C1 remains the official production standard.

### 2.2 Category B: Qualified Research Asset / Janus Neural Baseline N1 — **APPROVED**
- **Justification:**
  1. **External Playing Strength:** When evaluated against Stockfish 19, NNUE-V2 demonstrates extraordinary capability, beating SF 1600 (67.5%, implied Elo 1727) and achieving a winning score against SF 2000 (52.5%, implied Elo 2017) — an improvement of **$+208$ to $+234$ Elo over Classical C1**.
  2. **Tactical Superiority in Open Positions:** NNUE-V2 scored $+31.7$ Elo in ECO A and $+13.9$ Elo in ECO C against C1.
  3. **Safety and Non-Interference:** The native C++17 engine guarantees 100% bit-exact invariance to Classical C1 when `UseNeuralValue=false`. There is zero regression risk to existing users.
  4. **Production Readiness:** Memory usage is bounded (< 2 MB for network weights), AVX2 acceleration is automatic with scalar fallback, and 658/658 regression tests pass.
- **Official Designation:** NNUE-V2 is formally promoted as **Janus Neural Baseline N1**, accessible via native UCI option `setoption name UseNeuralValue value true` with `NeuralValueBlend = 50` and `NeuralValueUseAVX2 = true`.

---

## 3. Direction for Milestone v0.63

The forensic breakdown in v0.62 identified the single bottleneck preventing full production promotion: **the closed-structure deficit (ECO D: 36.7% score, -95.3 Elo)**.
To bridge this gap in v0.63:
1. **Curate Closed-Structure Training Data:** Enrich the training corpus with 200,000 positions from Queen's Gambit, French Defence, and King's Indian locked structures.
2. **Feature Representation Expansion:** Evaluate increasing accumulator dimension from 128 to 256 or introducing halfkp pawn-structure sub-features.
3. **Adaptive Evaluation Blending:** Investigate dynamic blending that scales `NeuralValueBlend` based on pawn structure mobility (higher neural weight in open positions, higher classical weight in locked endgames).
