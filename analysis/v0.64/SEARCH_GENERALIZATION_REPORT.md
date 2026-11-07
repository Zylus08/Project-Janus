# PROJECT JANUS v0.64 — SEARCH-LEVEL GENERALIZATION AND CANDIDATE SELECTION REPORT

**Author:** Principal Chess Engine Research Scientist & Systems Optimization Specialist  
**Milestone:** v0.64 — Phase 6 Deliverable  
**Status:** Qualified & Verified  
**Date:** 2026-11-08  

---

## 1. Executive Summary

A core lesson from Project Janus v0.61–v0.63 is that offline neural accuracy (MAE / $\rho$) is a necessary, but not sufficient, condition for playing strength. When a neural evaluator interacts with alpha-beta search and quiescence pruning, noisy or inverted evaluation gradients in specific endgames cause tree explosions and tactical blind spots.

In this phase, five distinct search configurations were subjected to controlled depth-6 search evaluation across 20 diagnostic positions representing tactical middlegames, queenless middlegames, rook endgames, and pawn endgames.

---

## 2. Configuration Definitions

| Config ID | Engine Core | Neural Evaluator | Blending Rule | Description |
|---|---|---|---|---|
| **B0** | Native N5 (v0.56) | None | $\alpha = 0.0$ (Pure Classical) | Production Control |
| **B1** | Native N5 + NNUE (v0.61) | NNUE-V2-Small | $\alpha = 0.50$ (Fixed 50/50) | Historical Research Control |
| **B2** | Native N5 + NNUE (v0.64) | NNUE-V2-Small | $\alpha(\Phi) = 0.50 \cdot (\Phi / 24)$ | Tapered Baseline Probe |
| **B3** | Native N5 + NNUE (v0.64) | NNUE-V3 + SEF | $\alpha = 0.50$ (Fixed 50/50) | Architectural Feature Only |
| **B4** | Native N5 + NNUE (v0.64) | **NNUE-V3 + SEF** | **$\alpha(\Phi) = 0.50 \cdot (\Phi / 24)$** | **Primary v0.64 Candidate** |

---

## 3. Empirical Search Results Across Position Types

### 3.1 Node Counts at Depth 6 (N = 20 positions)

| Category | B0 Classical | B1 Neural N1 | B2 V2 Tapered | B3 V3 Fixed | B4 V3 Adaptive (Selected) |
|---|---|---|---|---|---|
| **Tactical Middlegames** | 889,609 | 1,027,916 | 1,039,106 | 1,363,040 | **1,312,462** |
| **Queenless Middlegames**| 778,661 | 1,010,223 | 867,294 | 835,842 | **932,140** |
| **Rook Endgames** | 74,346 | 132,055 | 75,531 | 153,691 | **80,912 (−47.4% vs B3)** |
| **Pawn Endgames** | 6,731 | 7,409 | 6,760 | 7,224 | **6,700 (−7.3% vs B3)** |
| **Total Search Nodes** | **1,749,347** | **2,177,603** | **1,988,691** | **2,359,797** | **2,332,214** |
| **Average Nodes / Pos** | 87,467 | 108,880 | 99,435 | 117,990 | **116,611** |
| **Search Elapsed Time** | 1.125 s | 1.618 s | 1.984 s | 2.479 s | **2.509 s** |

---

## 4. Analytical Findings

1. **The Fixed-Blend Tree Explosion in Endgames:**
   - In rook endgames, fixed-blend configurations (B1 with 132,055 nodes and B3 with 153,691 nodes) more than doubled the search tree compared to Classical B0 (74,346 nodes).
   - This occurs because residual piece-square evaluation noise creates conflicting stand-pat scores in quiescence search, delaying cutoffs.
2. **Pruning Recovery via Adaptive Blending:**
   - Under Phase-Tapered Adaptive Blending (B4), rook endgame search volume contracted to **80,912 nodes** (a **47.4% reduction** vs B3), restoring clean classical alpha-beta cutoffs.
   - In pawn endgames, B4 evaluated **6,700 nodes**, matching the optimal tree size of Classical C1 (6,731 nodes).
3. **Tactical Robustness:**
   - In tactical and queenless positions, B4 maintained rich neural guidance, exploring key tactical branches while pruning quiet lines.

---

## 5. Candidate Selection Decision

Pursuant to the governing scientific preregistration criteria:
- **Selected Candidate:** **Configuration B4 (NNUE-V3 with SEF + Phase-Tapered Adaptive Blending, AVX2)**.
- **Opponent / Control:** **Configuration B0 (Janus Classical Baseline C1 Native N5)**.
- **Match Parameters:** 200 games (100 pairs with color reversal), Fischer 3.0s + 100ms increment, using the newly generated independent opening suite `independent_openings_v064.json`.

