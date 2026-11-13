# Targeted Move-Ordering Intervention: Candidate Janus Classical X19
**Milestone:** Phase 1, Milestone P1.14  
**Date:** November 13, 2026  
**Author:** Principal Computer Chess Engine Architect & C++17 Systems Engineer  
**Governing Standard:** JCTS v2 Classical Testing Protocol  
**Repository Branch:** `phase1/classical-janus`  
**Modified Source File:** `engine/classical_x/janus_classical_x.cpp`  
**Candidate Designation:** Janus Classical X19 (Track S: X19-S, Track P: X19-P)  
**Feature Flag:** `g_movepicker_stage_reform = true;` (Activated under Variant `X19`)  

---

## 1. Executive Summary & Problem Resolution

Milestone P1.14 identified a fatal structural defect in the Janus move-ordering pipeline: the **Staged Capture Leak**.
* In prior variants (X7 through X18), `MovePicker::next_move()` generated and yielded **all captures** in `STAGE_CAPTURES` before moving to `STAGE_KILLERS`.
* Consequently, losing captures ($\text{SEE} < 0$, such as $Q \times P$ with $\text{SEE} = -800$) were evaluated *ahead* of Killer 1, Killer 2, Countermoves, and high-history quiet moves, despite receiving a lower numerical ordering score in `score_move_for_ordering()`.
* In candidate **Janus Classical X19**, this defect is completely resolved by restructuring the stage machine to split captures by static exchange evaluation ($\text{SEE} \ge 0$ vs $\text{SEE} < 0$) and introducing first-class staging for Countermoves.

---

## 2. Technical Specification & Implementation Details

### 2.1 Restructured MovePicker Stage Pipeline
In `engine/classical_x/janus_classical_x.cpp`:
```cpp
enum MovePickerStage {
    STAGE_TT = 0,
    STAGE_GEN_CAPTURES,
    STAGE_CAPTURES,      // Yields Good Captures (SEE >= 0) in X19
    STAGE_KILLERS,       // Yields Killer 1 & Killer 2
    STAGE_COUNTERMOVE,   // NEW: Yields Countermove
    STAGE_GEN_QUIETS,    // Generates & sorts quiet moves
    STAGE_QUIETS,        // Yields History-sorted quiet moves
    STAGE_BAD_CAPTURES,  // NEW: Yields Losing Captures (SEE < 0)
    STAGE_DONE
};
```

### 2.2 Stage Partitioning Logic in `STAGE_GEN_CAPTURES`
When `g_movepicker_stage_reform` is active:
1. `native_generate_captures()` generates all pseudo-legal captures and promotions.
2. Captures are scored and sorted by MVV/LVA and capture history.
3. Captures are partitioned into two dedicated arrays:
   - `good_caps[MAX_MOVES]`: Promotions (`flag == 3`) and captures with $\text{SEE}(b, m) \ge 0$.
   - `bad_caps[MAX_MOVES]`: Losing captures with $\text{SEE}(b, m) < 0$.
4. `STAGE_CAPTURES` yields only `good_caps`.

### 2.3 Countermove Staging in `STAGE_COUNTERMOVE`
Immediately after `STAGE_KILLERS` exhausts Killer 1 and Killer 2:
- If `ply >= 1` and the opponent's previous move is valid, `g_countermove_table[prev_from][prev_to]` is probed.
- If the countermove is non-zero, legal, and has not been yielded, it is yielded immediately **before** `native_generate_quiets()` is called!
- If the countermove produces an immediate beta-cutoff, the engine avoids generating and sorting 30+ quiet moves entirely.

### 2.4 Deferred Search of Losing Captures in `STAGE_BAD_CAPTURES`
- When all quiet moves in `STAGE_QUIETS` fail to produce a beta-cutoff, the engine transitions to `STAGE_BAD_CAPTURES`.
- Losing captures ($\text{SEE} < 0$) are searched as a last resort before returning alpha.

---

## 3. Strict Compliance Invariants

1. **Move Set Completeness Invariant:**  
   The union of moves yielded across all stages:
   $$\text{Yielded} = \text{TT} \cup \text{GoodCaps} \cup \text{Killers} \cup \text{Countermove} \cup \text{Quiets} \cup \text{BadCaps}$$
   is **$100\%$ identical** to the baseline legal move set. Zero legal moves are omitted or lost.
2. **Deterministic Fallback Invariant:**  
   When `g_movepicker_stage_reform == false` (Variants `X7`, `X12`, `X17`, `X18`), the engine executes the legacy stage sequence, ensuring bit-for-bit equivalence with the frozen controls.
3. **Thread Safety & Race Freedom:**  
   All arrays (`good_caps`, `bad_caps`, `yielded`) reside inside the thread-local `MovePicker` instance on the search stack. No shared mutable state is accessed without synchronization.
