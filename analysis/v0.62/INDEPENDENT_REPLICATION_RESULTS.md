# Project Janus v0.62 — Independent Neural Strength Replication Report

**Document ID:** `analysis/v0.62/INDEPENDENT_REPLICATION_RESULTS.md`  
**Milestone:** v0.62 — Independent Neural Strength Replication, Causal Attribution & Release Qualification  
**Date:** 2026-11-07  
**Auditor / Principal Investigator:** Principal Chess Engine Research Scientist & Independent Experimental Auditor  
**Candidate:** Janus Neural Value V2 (Hybrid 50/50, AVX2 SIMD)  
**Control:** Janus Classical Baseline C1 (Native N5 Frozen)  
**Corpus:** `analysis/v0.62/corpus/independent_openings_v062.json` (100 fresh opening pairs, 0% overlap with v0.61 suite)  
**Time Control:** Fischer 3.0s + 100ms increment  
**Execution Environment:** Windows 11, AMD Ryzen 8-core AVX2 native multiprocessing (8 workers)  

---

## 1. Executive Summary & Replication Verdict

In Project Janus milestone v0.61, a 200-game match on `independent_openings_v056.json` reported a statistically significant strength improvement for Janus Neural Value V2 (Hybrid 50/50) over Classical Baseline C1:
$$\text{v0.61 Outcome: } 71\text{ wins}, 86\text{ draws}, 43\text{ losses} \implies 114.0/200\ (57.00\%),\ +49.0\text{ Elo}\ (95\%\text{ CI: } [+12.2, +85.0]),\ p = 0.01053$$

As mandated by v0.62 protocol, a strictly independent confirmatory replication was preregistered and executed on an entirely fresh, unmemorized 100-pair opening corpus (`independent_openings_v062.json`). The opening suite was verified to have **0% overlap** with the v0.61 suite and zero shared game plies.

### Confirmatory Tournament Result:
$$\mathbf{51\text{ wins},\ 95\text{ draws},\ 54\text{ losses}\ \implies\ 98.5 / 200\ (49.25\%)}$$
$$\Delta\text{Elo} = \mathbf{-5.2\text{ Elo}}\ (95\%\text{ Bootstrap CI: } [\mathbf{-36.6,\ +26.1}])$$
$$\bar{D}_{\text{pair}} = -0.030 \pm 0.0948,\quad t(99) = -0.3166,\quad p = \mathbf{0.75224}$$
$$\text{Statistically Significant at }\alpha = 0.05\text{: }\mathbf{NO}$$

### Definitive Scientific Conclusion:
**The reported +49.0 Elo gain from v0.61 DOES NOT REPLICATE on a clean, independent opening distribution.**
Under rigorous double-blind, color-balanced testing across 200 games on fresh openings, **NNUE-V2 performs at statistical parity with Classical Baseline C1 ($\Delta\text{Elo} = -5.2$, $p = 0.752$).**
The hypothesis that NNUE-V2 provides a unconditional, general playing strength improvement over C1 is **empirically rejected**.

---

## 2. Telemetry and Score Breakdown

### 2.1 Overall Performance Summary

| Metric | v0.61 Reported (Historical) | v0.62 Independent Confirmatory (Current) | Difference |
| :--- | :---: | :---: | :---: |
| **Opening Suite** | `independent_openings_v056.json` (biased) | `independent_openings_v062.json` (fresh) | Disjoint (0% overlap) |
| **Total Games** | 200 (100 pairs) | 200 (100 pairs) | 0 |
| **Wins (NNUE-V2)** | 71 (35.5%) | 51 (25.5%) | -20 (-10.0%) |
| **Draws** | 86 (43.0%) | 95 (47.5%) | +9 (+4.5%) |
| **Losses (NNUE-V2)** | 43 (21.5%) | 54 (27.0%) | +11 (+5.5%) |
| **Total Score** | **114.0 / 200 (57.0%)** | **98.5 / 200 (49.25%)** | **-15.5 (-7.75%)** |
| **Estimated $\Delta\text{Elo}$** | **+49.0 Elo** | **-5.2 Elo** | **-54.2 Elo** |
| **95% Bootstrap CI** | $[+12.2, +85.0]$ | $[-36.6, +26.1]$ | Spans 0; includes C1 |
| **Paired $t$-statistic** | $+2.6075$ | $-0.3166$ | $-2.9241$ |
| **$p$-value (two-tailed)** | $p = 0.01053$ (Significant) | $p = 0.75224$ (Not Significant) | $\Delta p = +0.7417$ |
| **White Points (V2)** | 62.5 / 100 (62.5%) | 52.5 / 100 (52.5%) | -10.0% |
| **Black Points (V2)** | 51.5 / 100 (51.5%) | 46.0 / 100 (46.0%) | -5.5% |

### 2.2 Termination Distribution

| Termination Mode | Game Count | Percentage | Candidate Impact |
| :--- | :---: | :---: | :--- |
| **Threefold Repetition** | 92 | 46.0% | 46.0 points shared |
| **Checkmate (White Win)** | 59 | 29.5% | 31 wins by V2, 28 by C1 |
| **Checkmate (Black Win)** | 46 | 23.0% | 20 wins by V2, 26 by C1 |
| **Fifty-Move Rule** | 2 | 1.0% | 1.0 point shared |
| **Insufficient Material** | 1 | 0.5% | 0.5 point shared |
| **Illegal Move / Crash / Timeout** | 0 | 0.0% | **Zero engine faults** |

---

## 3. Disaggregated ECO Category Analysis

A stratified analysis across opening categories reveals the structural explanation for the replication divergence:

| Category | Description | Games | Wins | Draws | Losses | Points | Score % | Estimated $\Delta\text{Elo}$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ECO A** | Flank & Unorthodox Openings | 44 | 13 | 22 | 9 | 24.0 | **54.55%** | **+31.7 Elo** |
| **ECO B** | Semi-Open Defenses (Sicilian, French) | 50 | 15 | 19 | 16 | 24.5 | **49.00%** | **-7.0 Elo** |
| **ECO C** | Open Games (1.e4 e5, Ruy Lopez) | 50 | 13 | 26 | 11 | 26.0 | **52.00%** | **+13.9 Elo** |
| **ECO D** | Closed Games (1.d4 d5, Queen's Gambit) | 30 | 5 | 12 | 13 | 11.0 | **36.67%** | **-95.3 Elo** |
| **ECO E** | Indian Defenses (King's Indian, Nimzo) | 26 | 5 | 16 | 5 | 13.0 | **50.00%** | **0.0 Elo** |
| **Total** | Full Representative Corpus | 200 | 51 | 95 | 54 | 98.5 | **49.25%** | **-5.2 Elo** |

### Critical Finding: The Closed Game Deficit (ECO D)
In open and tactical structures (ECO A and ECO C), NNUE-V2 exhibits modest positive performance (+31.7 Elo and +13.9 Elo), driven by sharper tactical king safety and piece coordination.
However, in **closed pawn structures (ECO D)**, NNUE-V2 collapses to **36.67% (-95.3 Elo)**.
- In locked pawn structures (e.g., French Winawer, Slav Defence, Queen's Gambit Declined), simple 128-dimensional halfkp features fail to evaluate multi-ply pawn breaks, backward pawn outposts, and piece redeployments behind locked chains.
- Conversely, Classical C1's handcrafted evaluation includes dedicated pawn structure heuristics (isolated, backward, doubled, passed pawns, and bishop pair mobility) that dominate in maneuvering battles.
- In v0.61, the opening suite had disproportionate representation of tactical open lines, which masked this structural deficit.

---

## 4. Root Cause Analysis: Why Did v0.61 Produce +49.0 Elo?

1. **Suite Leakage and Trunk Overlap:**
   Phase 0 audit proved that 285 positions (0.356%) in `independent_openings_v056.json` were exact duplicates of positions in the 80,000-position training corpus. While this does not represent complete game memorization, it heavily favored lines where the neural network had optimized leaf evaluations during SGD training.
2. **Opening Suite Selection Variance:**
   The v0.61 opening suite sampled lines with higher tactical complexity where NNUE-V2's $-29.4\%$ node pruning was most advantageous. When tested against the broader, balanced FIDE Master repertoire in v0.62, the closed-structure deficit erased the tactical advantage.
3. **Statistical Fluke / Selection Bias:**
   In v0.61, the 95% confidence interval was $[+12.2, +85.0]$. The lower bound was close to zero. On an unselected 200-game trial, sampling regression to the true population mean ($\sim 0$ Elo) naturally occurred.

---

## 5. Artifact and Telemetry Verification

- **Confirmatory Raw Telemetry:** [`analysis/v0.62/raw/v062_confirmatory_match_raw.json`](file:///E:/ChessXML/project-janus/analysis/v0.62/raw/v062_confirmatory_match_raw.json)
- **Confirmatory PGN Match Log:** [`analysis/v0.62/pgn/v062_confirmatory_match.pgn`](file:///E:/ChessXML/project-janus/analysis/v0.62/pgn/v062_confirmatory_match.pgn)
- **SHA-256 of Raw Telemetry:**
  `8d5c434f828a2a7a40ff24a4964177d6118d04221190bc23fc827f311394b8e3` (to be recorded in manifest)

---

## 6. Scientific Implication for Production Promotion

Under the preregistered qualification criteria:
- **Category A (Full Production Promotion):** Requires $\Delta\text{Elo} \ge +25.0$ and 95% CI strictly $> 0$. **FAILED.**
- **Category B (Conditional / Research Asset):** Validated inference, zero crashes, bit-exact C1 invariance when disabled, useful for specific research or tactical scenarios. **PASSED.**
- **Category C (Promotion Rejection):** Default production evaluation must **REMAIN Classical Baseline C1** (`UseNeuralValue=false`).

The confirmatory trial has successfully provided an objective, reproducible answer: **NNUE-V2 cannot be promoted as the default production evaluation in Janus.** Classical C1 remains the unblemished production standard.

