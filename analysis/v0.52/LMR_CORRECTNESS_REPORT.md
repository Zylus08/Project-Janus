# Project Janus v0.52 — Late Move Reductions (LMR) Correctness Report

**Date:** 2026-11-04  
**Milestone:** v0.52  
**Target Architecture:** Janus Native Search Core C++17 (`janus_native.cpp`, `janus_native.dll`, `janus_native_engine.exe`)  
**Test Suite:** `tests/test_native_lmr_semantics.py` (20 Invariant Gates)  
**Status:** **100% PASS (20/20 Passing, 0.288s)**  

---

## 1. Executive Summary

Phase 3 and Phase 4 of Project Janus v0.52 implemented and verified Late Move Reductions (LMR) within the compiled C++17 native search engine. 

To ensure complete correctness and guard against tactical blindness or unverified score corruptions, twenty rigorous invariant gates were authored and evaluated. All twenty tests executed cleanly and passed without exception.

---

## 2. Invariant Verification Matrix

| Gate | Target Semantic Invariant | Implementation Guard | Test Result |
|---|---|---|---|
| **01** | Default Disabled State | `g_use_lmr == false` by default; 0 telemetry | **PASS** |
| **02** | Runtime Option Toggling | `set_lmr_options()` toggles cleanly with 0 leak | **PASS** |
| **03** | Root Node Immunity | `ply > 0` condition protects all root moves | **PASS** |
| **04** | Minimum Depth Floor | `depth >= g_lmr_min_depth` (default 3) | **PASS** |
| **05** | Move Ordering Floor | `moves_searched >= g_lmr_move_threshold` (default 4) | **PASS** |
| **06** | In-Check Position Immunity | `!in_check` protects positions where king is in check | **PASS** |
| **07** | Capture Move Immunity | `undo.captured_piece == NO_PIECE` protects all captures | **PASS** |
| **08** | Promotion Move Immunity | `move_flag(m) != 3` protects all pawn promotions | **PASS** |
| **09** | Checking Move Immunity | `native_is_check(b) == 0` protects check-giving moves | **PASS** |
| **10** | TT Hash Move Immunity | `m != tt_move` protects best move from previous iter | **PASS** |
| **11** | Reduction Depth Allocation | $d_{\text{reduced}} = \max(1, d - 1 - R)$ | **PASS** |
| **12** | Re-Search on Alpha Beat | Triggers full-depth re-search whenever $score > \alpha$ | **PASS** |
| **13** | Score & PV Integrity | PV table and scores preserved through re-search | **PASS** |
| **14** | Fail-Low Efficiency | Fail-low moves prune subtree without re-searching | **PASS** |
| **15** | Beta Cutoff Telemetry | `g_lmr_cutoffs` tracks cutoffs on reduced branches | **PASS** |
| **16** | Baseline Bit-Equivalence | `UseLMR=false` produces bit-identical results to N2 | **PASS** |
| **17** | Telemetry Reset | `native_reset_lmr_telemetry()` zeroes all 4 counters | **PASS** |
| **18** | TT Replacement Integrity | Warm TT lookup remains sound and improves speed | **PASS** |
| **19** | UCI Protocol Integration | Parses `setoption name UseLMR/min/thresh/red` | **PASS** |
| **20** | Parameter Sweep Stability | Validated across combinations of min_depth/threshold/reduction | **PASS** |

---

## 3. Quantitative Demonstration on Initial Position (Depth 5)

Comparing the search of the initial starting position at Nominal Depth 5:

```
Baseline N2 (LMR Off):
- Best Move: b1c3
- Evaluation: +40 cp
- Nominal Depth: 5
- Total Nodes: 94,571
- Search Time: 0.0554 s (55.4 ms)
- NPS: 1,707,057

Candidate N3 (LMR On):
- Best Move: b1c3 (100% agreement with N2)
- Evaluation: +40 cp (Exact score match)
- Nominal Depth: 5
- Total Nodes: 15,191 (-83.94% tree size reduction)
- Search Time: 0.0104 s (10.4 ms, 5.3x speedup)
- Telemetry: 417 eligible moves, 417 reduced moves, 5 re-searches (1.20% re-search rate)
```

---

## 4. Conclusion

The C++17 LMR implementation fulfills every architectural and semantic invariant preregistered in `LMR_DESIGN_SPECIFICATION.md`. Candidate N3 is cleared for tactical safety benchmarking and differential ablation.

