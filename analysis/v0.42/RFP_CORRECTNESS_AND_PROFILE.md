# Project Janus v0.42 — RFP Correctness and Tactical Regression (Phase E)

**Milestone:** v0.42  
**Scope:** Re-evaluation of RFP correctness invariants, tactical suite accuracy, and profiling efficiency in the current codebase  
**Date:** 2026-11-03  

---

## 1. Unit Test Regression Suite

The full test suite consisting of 444 tests was executed at Phase A baseline:
- **Result:** 444 / 444 tests passed (0 failures, 0 errors).
- **Runtime:** 214.8 seconds.

### 1.1 Invariant Unit Tests (`tests/test_v040_rfp.py`)
All 7 dedicated RFP unit tests passed:
1. `test_01_disabled_by_default`: Confirms RFP is disabled unless explicitly enabled.
2. `test_02_positions_in_check_exempt`: Verifies in-check positions are strictly exempt from pruning.
3. `test_03_forced_mate_not_pruned`: Verifies forced mate positions are never pruned.
4. `test_04_tactical_sacrifice_preserved`: Confirms queen sacrifice for mate is found with RFP.
5. `test_05_quiet_position_triggers_rfp_cutoff`: Confirms cutoff fires when static advantage is overwhelming.
6. `test_06_endgame_behavior`: Confirms basic pawn endgame evaluates correctly.
7. `test_07_score_consistency_against_reference`: Confirms evaluations remain within margin on quiet positions.

### 1.2 Repetition and Quiescence Draw Tests (`tests/test_v041_repetition_quiescence.py`)
All 7 tests passed:
1. `test_01_repetition_at_main_search_entry_returns_zero`: Draw score 0 returned at ply > 0 on 3-fold repetition.
2. `test_02_repetition_at_quiescence_entry_returns_zero`: Repetition detected upon entering quiescence.
3. `test_03_losing_position_prefers_repetition_draw`: Engine chooses repetition when losing.
4. `test_04_winning_position_avoids_repetition_draw`: Engine avoids repetition when winning alternatives exist.
5. `test_05_non_repeating_position_unaffected`: Standard non-repeating positions search normally.
6. `test_06_seventy_five_move_rule_triggers_draw`: halfmove_clock = 150 evaluates as draw.
7. `test_07_board_stack_restored_after_search`: Search leaves board stack intact.

---

## 2. 16-Position Effective-Depth and Tactical Diagnostics

Executed on current codebase at fixed depth 4:
- **Raw Data:** `analysis/v0.42/effective_depth_diagnostics_v042.json`

### 2.1 Diagnostic Summary Comparison

| Configuration | Total Nodes | Time (s) | Mean NPS | Tactical Accuracy | Tactical Count | RFP Cutoffs |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline (K0)** | 86,381 | 4.665 | 18,516 | **81.25%** | **13/16** | 0 |
| **Candidate ORD1** | 85,480 | 4.716 | 18,126 | **81.25%** | **13/16** | 0 |
| **Candidate RFP** | **73,840** | **4.004** | 18,442 | **81.25%** | **13/16** | **1,632** |

### 2.2 Efficiency Analysis
- **Node Reduction:** $\frac{86,381 - 73,840}{86,381} = \mathbf{14.52\%}$ node reduction across the 16 standard positions.
- **Time Saving:** From 4.665s to 4.004s ($\mathbf{-14.18\%}$).
- **Search Throughput:** NPS remained stable at ~18.4k NPS.
- **RFP Cutoffs Fired:** 1,632 cutoffs across shallow plies (depth 1–2).

### 2.3 Tactical Accuracy Integrity
- **Baseline:** 13 / 16 solved correctly.
- **Candidate RFP:** 13 / 16 solved correctly.
- **Delta:** 0 missed tactics. Zero tactical regression observed.

---

## 3. Phase E Verdict

**GATE E1 — Correctness Invariants:** ✓ PASS (7/7 unit tests pass)  
**GATE E2 — Repetition Draw Invariants:** ✓ PASS (7/7 tests pass)  
**GATE E3 — Search Tree Reduction:** ✓ PASS (-14.52% node reduction at depth 4)  
**GATE E4 — Tactical Accuracy Preservation:** ✓ PASS (13/16 solved, 0 regressions)  

**Overall Phase E Status:** ✓ VERIFIED — Candidate RFP preserves tactical safety and improves search efficiency.
