# PROJECT JANUS v0.64 — PHASE-BALANCED SUPERVISED DATASET GENERALIZATION REPORT

**Author:** Principal Chess Engine Research Scientist & ML Training Engineer  
**Milestone:** v0.64 — Phase 1 Deliverable  
**Status:** Qualified & Verified  
**Date:** 2026-11-08  

---

## 1. Executive Summary

In Project Janus v0.63, systematic forensic analysis revealed that the 113 positions labeled $\text{Phase} \le 16$ in historical datasets were severely skewed: **67.3% were queenless middlegames** and **32.7% were other simplified positions**, with **zero pure pawn endgames, zero rook endgames, and zero minor-piece endgames**. Consequently, the neural network trained on this corpus suffered severe rank degradation ($\rho = -0.125$) in actual endgame play.

To establish true endgame generalization and robust positional representation, Project Janus v0.64 expands the training corpus to **150,000 supervised positions**, incorporating **50,000 newly sampled, targeted positions** with dedicated 50% coverage of pure endgames (pawn, rook, minor-piece, opposite-bishop) and 50% coverage of simplified/queenless and closed pawn structures.

---

## 2. Dataset Composition and Stratification

The final unified dataset partitions are structured as follows:

| Partition | Historical v0.61 Positions | New v0.64 Targeted Positions | Total Positions | Game Source Range |
|---|---|---|---|---|
| **Train (`train_v3.json`)** | 80,000 | 40,000 | **120,000** | Games 0..4,500 & Games 15,000..37,000 |
| **Validation (`val_v3.json`)** | 10,000 | 5,000 | **15,000** | Games 5,000..5,700 & Games 38,000..44,000 |
| **Test (`test_v3.json`)** | 10,000 | 5,000 | **15,000** | Games 6,000..6,700 & Games 45,000..51,000 |
| **Total** | **100,000** | **50,000** | **150,000** | Disjoint Game Partitions |

### 2.1 Subtype Breakdown of the 50,000 New Positions

| Category | Structural Subtype | Train (40k) | Val (5k) | Test (5k) | Total (50k) | Percentage |
|---|---|---|---|---|---|---|
| **Pure Endgames** | Pawn Endgame ($\text{Phase} = 0$) | 4,000 | 500 | 500 | **5,000** | 10.0% |
| | Rook Endgame (Rooks only) | 8,000 | 1,000 | 1,000 | **10,000** | 20.0% |
| | Minor Piece Endgame (Knights/Bishops) | 6,000 | 750 | 750 | **7,500** | 15.0% |
| | Opposite-Colored Bishops | 2,000 | 250 | 250 | **2,500** | 5.0% |
| **Structures & Simplified**| Queenless Middlegame ($\text{Phase} \le 12$) | 10,000 | 1,250 | 1,250 | **12,500** | 25.0% |
| | Locked Pawn Structures (Fixed Chains) | 10,000 | 1,250 | 1,250 | **12,500** | 25.0% |
| **Total** | | **40,000** | **5,000** | **5,000** | **50,000** | **100.0%** |

---

## 3. Strict Provenance and Zero-Leakage Guarantee

To prevent data contamination and optimistic evaluation:
1. **Game-Level Isolation:** All candidate positions were drawn from strictly disjoint ranges of `lichess_elite_2020-06.zip`. No game from train appears in val, test, or the confirmatory tournament suite.
2. **Global FEN Deduplication:** The canonical position key `canon_key` (board piece placement, active color, castling availability, en-passant square) was hashed into a global set across all 150,000 positions:
   $$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$
   Bit-exact intersection was verified to be strictly 0.
3. **Disjoint Tournament Suite:** The 100-pair confirmatory tournament suite (`independent_openings_v064.json`) was sampled from games 55,000+, guaranteeing 0% overlap with all training data and past milestones.

---

## 4. Teacher Ground Truth Specification

- **Teacher Engine:** Stockfish 19 x64 AVX2
- **Binary Hash (SHA-256):** `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- **Search Parameters:** Depth 10, Hash 16 MB, Threads 1 per worker (10 concurrent workers).
- **Target Value:** Centipawn score normalized to side-to-move, clamped to $[-2000, +2000]$ cp.
- **WDL Probability Target:**
  $$\text{wdl} = \frac{1}{1 + 10^{-\text{cp} / 400.0}}$$
  where $\text{cp}$ is the centipawn score from the perspective of the side to move.

---

## 5. Summary Conclusion

The v0.64 dataset expansion directly remedies the empirical vulnerabilities diagnosed in v0.63. The supervised training set now covers 120,000 positions with balanced representation of true endgames, queenless middlegames, and pawn-chain structures, providing the rigorous foundation needed for training NNUE-V3.

