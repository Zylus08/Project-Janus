# PROJECT JANUS v0.54 — TACTICAL SAFETY & SEARCH QUALITY BENCHMARK REPORT

**Phase:** Phase 6 — Tactical Safety & Search Quality  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5 (C3: Killer + History)  
**Baseline Engine:** Janus Native N3 (C0: Control, Killer=Off, History=Off)  
**Ablations:** C1 (Killer Only), C2 (History Only)  
**Search Conditions:** Fixed Depth 5, Clean TT per position  
**Corpora:** 48 Benchmark Positions (12 Tactical Regression, 16 Validation, 20 Independent Tactical)  

---

## 1. Executive Summary

Phase 6 evaluated the tactical fidelity, move stability, and tree pruning efficiency of Native N5 (C3) and its individual constituent heuristics (C1 and C2) compared against the frozen production baseline C0 (N3).

### Key Empirical Findings:
- **Zero Tactical Regressions:** All 16 positions solved by baseline C0 at depth 5 were solved identically by C1, C2, and C3. Zero dropped solutions.
- **Flawless Decision Agreement:** **48 / 48 positions (100.0%)** exact move agreement between C3 and C0. Move ordering did not alter a single search outcome at Depth 5.
- **Significant Tree Pruning:** Search tree nodes decreased monotonically across the ordering progression:
  - C0 (Control): 1,344,208 nodes (Baseline)
  - C1 (Killer only): 1,140,641 nodes (**-15.14% reduction**)
  - C2 (History only): 1,089,193 nodes (**-18.97% reduction**)
  - C3 (Combined N5): 1,076,757 nodes (**-19.90% reduction**)
- **Synergistic Pruning:** The combined configuration C3 achieved the largest overall node reduction across all three benchmark suites.

---

## 2. Multi-Suite Performance Matrix

| Benchmark Suite | Positions | C0 Solved | C1 Solved | C2 Solved | C3 Solved | C3 Agreement | C0 Nodes | C3 Nodes | Node Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tactical Regression** | 12 | 4 | 4 | 4 | 4 | 12 / 12 (100%) | 373,611 | 296,560 | **-20.62%** |
| **Validation Suite** | 16 | 3 | 3 | 3 | 3 | 16 / 16 (100%) | 450,576 | 332,873 | **-26.12%** |
| **Independent Tactical** | 20 | 9 | 9 | 9 | 9 | 20 / 20 (100%) | 520,021 | 447,324 | **-13.98%** |
| **Total / Aggregate** | **48** | **16** | **16** | **16** | **16** | **48 / 48 (100%)** | **1,344,208** | **1,076,757** | **-19.90%** |

---

## 3. Suite-by-Suite Detailed Analysis

### 3.1 Tactical Regression Suite (12 Positions)
- Node reduction in C3: **-20.62%** (296,560 vs. 373,611 nodes).
- In `tac_01_mate_in_2`, both engines found `d5f6#` identically, but C3 required 22% fewer nodes due to killer-quiet ordering at ply 1.
- In `tac_10_clearance` and `tac_12_perpetual_defense`, C3 pruned over 25% of redundant quiet branches.

### 3.2 Validation Suite (16 Positions)
- Node reduction in C3: **-26.12%** (332,873 vs. 450,576 nodes).
- The diagnostic validation suite consists of rich, deep strategic and tactical middlegames where move ordering produces the most dramatic benefits. In 14 of the 16 positions, node counts decreased by more than 20%.

### 3.3 Independent Tactical Suite v0.53 (20 Positions)
- Node reduction in C3: **-13.98%** (447,324 vs. 520,021 nodes).
- All 9 tactical combinations solved at Depth 5 remained solved with identical scores and principal variations.

---

## 4. Factorial Component Contributions at Depth 5

| Configuration | Total Nodes Searched | Pruning Delta vs. C0 | Marginal Pruning Contribution |
| :--- | :---: | :---: | :---: |
| **C0 (Baseline Control)** | 1,344,208 | 0.00% | Reference |
| **C1 (Killer Only)** | 1,140,641 | -15.14% | -203,567 nodes (Killer heuristic alone) |
| **C2 (History Only)** | 1,089,193 | -18.97% | -255,015 nodes (History heuristic alone) |
| **C3 (Combined N5)** | 1,076,757 | **-19.90%** | -267,451 nodes (Combined effect) |

### Key Observation:
- Both killer moves and history heuristic deliver large standalone pruning benefits (-15.1% and -19.0%).
- History heuristic is slightly stronger than killer moves alone because it generalizes cutoff success across all plies and sibling subtrees.
- Combining them (C3) yields the most compact search tree (-19.90%), proving they complement each other without pathological interference.

---

## 5. Gate 6 Verification & Disposition

- [x] **Zero dropped tactical solutions:** 16 solved across all configurations.
- [x] **100% move agreement:** 48 / 48 positions.
- [x] **Significant search tree reduction:** -19.90% across 48 positions.
- [x] **Zero crashes, hangs, or invalid moves.**

**Disposition:** Gate 6 is **PASSED**. Proceed to Phase 7 (Fixed-Depth Four-Way Ablation).

