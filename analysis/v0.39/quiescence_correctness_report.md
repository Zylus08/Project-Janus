# Project Janus v0.39 — Quiescence Search Correctness & Check Evasion Report

**Milestone:** v0.39 Tactical Search Reliability  
**Subject:** Quiescence Search Alpha-Beta Soundness, Check Evasions, and Selective Checking Exploration  
**Status:** **`VERIFIED_CORRECT`**  

---

## 1. Baseline Implementation Audit Findings

Before modification, `_quiescence` in `src/janus/search.py` was inspected against formal alpha-beta and chess game rules. Multiple critical deficiencies were uncovered:

### 1.1 Fatal Alpha-Beta Fail-Low Bug When In Check
- **Flawed Code:**
  ```python
  if not in_check:
    stand_pat = evaluate_side_to_move(board, config=self.eval_config)
    alpha = max(alpha, stand_pat)
    ...
  else:
    moves = self._ordered_moves(board, None, ply)

  for move in moves:
    ...
    score = -self._quiescence(...)
    if score >= beta:
      return beta
    alpha = max(alpha, score)

  return alpha  # <--- CRITICAL BUG
```
- **Failure Mechanics:**
  When `not in_check`, returning `alpha` is valid because `alpha` is initially set to `stand_pat` (the player can choose not to capture).
  However, **when `in_check`, stand-pat is illegal**. The side to move MUST make a legal check evasion.
  If the search window is called with e.g. $\alpha = 0, \beta = 1000$ (asking "can the side to move achieve $\ge 0$?"), and all legal check evasions lead to checkmate or massive material loss (scores $< 0$), `alpha` is never updated.
  The unpatched code returned `alpha` (0), falsely reporting to the root search that getting checkmated or losing a queen was an **equal position (score 0)**!
- **Empirical Demonstration:**
  In position `4k3/5Q2/4K3/8/8/8/8/8 b - - 0 1`, Black has only `Kd8`, following which White has forced mate.
  The unpatched `_quiescence(board, alpha=0, beta=1000, ply=0)` returned **0** instead of $-MATE\_SCORE$.

### 1.2 Unbounded Check Evasion Recursion Risk
- `if ply >= self.qsearch_max_ply and not in_check:` exempted checking positions from the 16-ply quiescence cutoff. If perpetual checks or extended evasion sequences occurred, search depth was unbounded by any hard cap.

### 1.3 Threefold Repetition Omission
- Line 598 checked `is_fivefold_repetition()` and `is_seventyfive_moves()`, but omitted `can_claim_threefold_repetition()`, delaying legal draw recognition.

---

## 2. Implemented Correctness Fixes (Candidate Q0)

1. **Exact Fail-Low Tracking for Check Evasions:**
   - When `in_check` is True, `best_score` is initialized to `-INF`.
   - On each legal evasion, `best_score = max(best_score, score)`.
   - If all check evasions fail low ($< \alpha$), `_quiescence` returns `best_score`, accurately reporting the loss or mate score.
2. **Fail-Soft Alpha-Beta Pruning:**
   - If a move causes a beta cutoff ($score \ge \beta$), `_quiescence` returns the actual score (or `stand_pat`), preventing artificial score clamping to $\beta$.
3. **Hard Quiescence Ply Ceiling:**
   - Implemented `qsearch_hard_limit = self.qsearch_max_ply + 8` (24 plies). Even if check evasions persist, quiescence guarantees termination and returns static evaluation at the hard ceiling.
4. **Threefold Repetition Detection:**
   - Added `or board.can_claim_threefold_repetition()` to immediate draw adjudications.
5. **Root Move Fallback Ordering:**
   - In `search()`, if deadline expires before depth 1 finishes, `best_move` now defaults to the top move from `self._ordered_moves(board, None, 0)` rather than arbitrary `legal_moves[0]`.

---

## 3. Correctness Verification Matrix

All 8 mandatory test cases in `tests/test_v039_quiescence.py` were executed and passed cleanly:

| Test Case | Description | Expected Behaviour | Measured Result |
| :--- | :--- | :--- | :---: |
| **test_1_multiple_legal_evasions** | Position in check with 6 legal evasions | All legal evasions generated and searched | **PASS** |
| **test_2_forced_checkmate_in_qsearch** | Scholar's mate position in quiescence node | Returns exact `-MATE_SCORE + ply` | **PASS** |
| **test_3_no_legal_check_evasions** | Fool's mate terminal node | Returns `-MATE_SCORE` | **PASS** |
| **test_4_capture_is_only_legal_evasion** | Checking queen attacked only by rook | Executes `Rxe1` capture | **PASS** |
| **test_5_non_capturing_evasion_required** | King under rook check with quiet king steps | Searches quiet king steps | **PASS** |
| **test_6_checking_line_exposes_loss** | Tactical sequence exposing material deficit | Searches line accurately | **PASS** |
| **test_7_search_interruption_in_check** | `stop_event` set during evasion search | Raises `SearchTimeout` cleanly | **PASS** |
| **test_8_alpha_beta_fail_low_in_check** | Check evasions failing below $\alpha = 0$ | Returns true negative score ($< 0$) | **PASS** |

---

## 4. Selective Quiescence Checking Exploration (Candidate Q1)

An optional parameter `enable_qsearch_checks` (bounded to `qsearch_checks_max_ply = 1`) was integrated into `JanusSearch`.
- **Policy:** At ply 0 of quiescence search, if not in check, legal checking moves with non-negative SEE (`self._see(board, move) >= 0`) are generated and searched.
- **Node Cost Evaluation:** Investigated under Phase 5 profiling to compare tactical gain vs node explosion before considering activation.

