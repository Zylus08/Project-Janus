# PROJECT JANUS v0.54 — MOVE ORDERING CORRECTNESS & INVARIANT REPORT

**Phase:** Phase 5 — Search Correctness & Window Invariant Test Suite  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5  
**Test Suite:** `tests/test_native_ordering_semantics.py`  
**Test Status:** **30 / 30 PASSED (100.0%)** in 2.97s  

---

## 1. Executive Summary

Phase 5 verified the correctness, safety invariants, and behavioral isolation of the native C++17 killer-move and history-heuristic implementations across 30 dedicated unit test gates.

All 30 invariant gates passed cleanly with zero failures, zero errors, and zero memory defects.

---

## 2. Invariant Verification Gate Results

| Gate | Invariant Tested | Verification Mechanism | Status |
| :---: | :--- | :--- | :---: |
| **01** | UCI Options Toggling | Runtime activation of `UseKillerOrdering` and `UseHistoryOrdering` | **PASS** |
| **02** | Baseline Equivalence (C0 == N3) | Bit-identical search when experimental features disabled | **PASS** |
| **03** | Killer Recording on Quiet Cutoff | Verifies quiet move cutoff populates slot 0 | **PASS** |
| **04** | Killer Slot Promotion | Successive quiet cutoffs shift slot 0 to slot 1 | **PASS** |
| **05** | Killer Duplicate Suppression | Same move at slot 0 does not replicate to slot 1 | **PASS** |
| **06** | Killer Ply Bounds | Out-of-bounds plies ($<0$ or $\ge 64$) safely return 0 | **PASS** |
| **07** | Killer Move Legality | Returned best move is guaranteed legal in board state | **PASS** |
| **08** | Killer Reset Semantics | `clear_killers()` zeroes all slots across all plies | **PASS** |
| **09** | History Reward Correctness | Quiet cutoff increases history score by $depth^2$ | **PASS** |
| **10** | History Saturation | Score is strictly capped at `MAX_HISTORY_SCORE = 70,000` | **PASS** |
| **11** | History Aging | Generational decay halves scores across search invocations | **PASS** |
| **12** | History Reset Semantics | `clear_history_heuristic()` zeroes entire 32 KB table | **PASS** |
| **13** | Static Evaluation Isolation | `evaluate()` score is invariant to history table contents | **PASS** |
| **14** | TT Move Priority | Hash move ($10M$) always outranks killers and history | **PASS** |
| **15** | Tactical Capture Priority | Captures ($>99.9k$) always outrank killers and history | **PASS** |
| **16** | Promotion Priority | Pawn promotions ($800k-900k$) outrank quiets | **PASS** |
| **17** | Quiet Move Ordering | Validates tiered hierarchy: $K_1 (90k) > K_2 (80k) > H (1-70k) > Q (0)$ | **PASS** |
| **18** | No Move Omission | All legal moves generated are searched | **PASS** |
| **19** | No Duplicate Move Search | Move generator and sort produce unique move lists | **PASS** |
| **20** | Zero Illegal Moves | Searches in sharp tactical positions yield only legal moves | **PASS** |
| **21** | Correct Alpha-Beta Bounds | Evaluation scores remain within minimax bounds | **PASS** |
| **22** | Mate-Score Normalization | Forced checkmates normalized by ply distance | **PASS** |
| **23** | Repetition & Draw Semantics | Threefold repetition correctly recognized and evaluated | **PASS** |
| **24** | LMR Eligibility Consistency | Early-ordered quiet moves avoid unnecessary reduction | **PASS** |
| **25** | LMR Re-Search Correctness | Refuted reductions trigger full-depth re-search | **PASS** |
| **26** | Search Cancellation Safety | Time limit abort cleanly returns legal best move | **PASS** |
| **27** | PV Line Legality | Every move in the principal variation is sequentially legal | **PASS** |
| **28** | Maximum Search Ply Safety | Deep tree search operates without stack overflow | **PASS** |
| **29** | Zero State Leakage | Switching between C3 and C0 preserves isolated state | **PASS** |
| **30** | Deterministic Reproducibility | Identical search inputs produce identical nodes and scores | **PASS** |

---

## 3. Correctness Gate Clearance

- [x] All 30 invariant gates passed.
- [x] Full test suite (546 tests) passing without regressions.
- [x] Zero memory leaks, zero array out-of-bounds accesses.

**Disposition:** Gate 5 is **PASSED**. Proceed to Phase 6 (Tactical Safety & Search Quality).

