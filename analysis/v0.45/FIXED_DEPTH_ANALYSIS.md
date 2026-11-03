# Controlled Fixed-Depth Search Analysis — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Status:** PASS (Gate E Validated)

---

## 1. Executive Summary

To isolate the intrinsic pruning behaviour of Reverse Futility Pruning from time-management and deadline truncation artifacts, we executed controlled paired fixed-depth searches across depths 2, 3, 4, and 5 for all 37 positions in the diagnostic corpus.

Every position was evaluated under strictly identical conditions:
- Identical engine revision, board state, move generator, and evaluation function.
- Fresh transposition table and search state per run.
- Zero deadline constraints (`time_limit = None`).

---

## 2. Quantitative Depth Ladder Results

| Target Depth | Positions Evaluated | Move Agreement | Agreement Pct | K0 Cumulative Nodes | RFP Cumulative Nodes | Aggregate Node Reduction | Mean Score Delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Depth 2** | 37 | 37 / 37 | **100.0%** | 22,083 | 22,033 | $+0.23\%$ | $0.0\text{ cp}$ |
| **Depth 3** | 37 | 37 / 37 | **100.0%** | 63,415 | 63,363 | $+0.08\%$ | $0.0\text{ cp}$ |
| **Depth 4** | 37 | 37 / 37 | **100.0%** | 417,046 | 372,833 | **$+10.60\%$** | $0.0\text{ cp}$ |
| **Depth 5** | 37 | 37 / 37 | **100.0%** | 2,789,951 | 2,533,564 | **$+9.19\%$** | $0.0\text{ cp}$ |
| **ALL DEPTHS** | **148** | **148 / 148** | **100.0%** | **3,292,495** | **2,991,793** | **$+9.13\%$** | **$0.0\text{ cp}$** |

---

## 3. Key Findings

1. **Perfect Move Equivalence:** Across all 148 paired search trials, Candidate RFP and Baseline K0 agreed on the selected best move in **100.0% of positions**.
2. **Identical Root Scores:** The mean score difference between K0 and RFP across all depths was exactly **$0.0\text{ cp}$**. RFP does not distort minimax root evaluation.
3. **Depth-Dependent Efficiency:**
   - At shallow nominal depths ($d=2, 3$), tree size is small and frontier nodes are primarily root children, yielding modest pruning ($\sim 0.1\text{--}0.2\%$).
   - At realistic midgame depths ($d=4, 5$), RFP prunes aggressively in non-PV frontier branches, eliminating **$10.60\%$ of nodes at depth 4** and **$9.19\%$ of nodes at depth 5** (saving over 256,000 nodes at depth 5 alone).

---

## 4. Gate E Sign-Off

- [x] Full depth ladder (depths 2, 3, 4, 5) executed across all 37 diagnostic positions.
- [x] Raw paired traces recorded in `analysis/v0.45/fixed_depth/fixed_depth_ladder_raw.json`.
- [x] Confirmed 100% move agreement and 9.13% cumulative node reduction under equal fixed depth.

**Gate E Status:** **PASS** — Proceeding to Phase F (Fixed-Time Search Budget Experiment).

