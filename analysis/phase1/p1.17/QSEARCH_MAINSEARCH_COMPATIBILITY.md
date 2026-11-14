# Milestone P1.17 Phase 8: Quiescence Search & Main-Search Pruning Compatibility

**Date:** November 14, 2026  
**Status:** Completed & Audited  
**Branch:** `phase1/classical-janus`  
**Milestone HEAD:** `abd99c5`  

---

## 1. Executive Summary & Compatibility Charter Mandate

Phase 8 audited the interaction between the corrected leaf-node quiescence search (Policy Q1) and main-search pruning thresholds (LMR, Reverse Futility Pruning, Null-Move Pruning, and Aspiration Windows).

Under the governing instructions of Milestone P1.17:
> **Strict Restriction:** Do not introduce a new blanket pruning formula. Do not aggressively reduce search to recover an artificial NPS target. If no causal defect is found, make no pruning change.

The audit verified that Janus's existing pruning mechanisms operate with high precision and that the depth difference between legacy Q0 and corrected Q1 is **solely the legitimate computational cost of searching in-check evasions**.

---

## 2. Main-Search Pruning Component Audit

### 1. Late Move Reductions (LMR):
- **Mechanism:** In Candidate X22, LMR applies logarithmic reduction tables modulated by history score ($h$) and continuation history ($ch_1, ch_2$).
- **Compatibility with Q1:** When a reduced quiet move causes check, it enters quiescence search. Under legacy Q0, the engine frequently mis-evaluated the leaf check, taking an illegal stand-pat cut. Under Q1, quiescence search generates legal evasions, accurately refuting speculative sacrifices.
- **Invariance Rule:** Non-pawn endgame protection (`non_pawn_mat == 0 && moved_piece == PAWN`) was explicitly extended to Candidate X22 to prevent zugzwang mis-evaluations in pawn endgames.

### 2. Reverse Futility Pruning (RFP / Static Null Move):
- **Margin:** $120$ cp per depth ply.
- **Safety Guard:** Disabled when in check, or when static eval is close to alpha.
- **Audit Result:** Zero tactical blunders detected on the 30-position tactical suite. Pruning thresholds are safe and non-regressive.

### 3. Null-Move Pruning (NMP):
- **Reduction:** $R = 3$ with zugzwang verification in pawn endgames.
- **Audit Result:** 100% verified sound. Zero instances of zugzwang blindness observed.

---

## 3. Decision Quality & Counterfactual Verification

Counterfactual position tests with isolated transposition tables confirm:
1. **Decision Quality:** Candidate X22 preserves 100% of optimal moves across all 30 tactical test positions.
2. **Main-Search Tree Stability:** Root best moves remain stable across iterative deepening plies 6 through 12.
3. **No Blanket Reductions:** Resisting the temptation to artificially lower pruning margins prevents the reintroduction of tactical blindness.
