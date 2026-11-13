# Architectural Priority Decision: MovePicker Stage Reform & Capture Classification
**Milestone:** Phase 1, Milestone P1.14  
**Date:** November 13, 2026  
**Author:** Principal Computer Chess Engine Architect & Alpha-Beta Specialist  
**Governing Charter:** Strictly Non-ML Classical Development  
**Decision Gate:** Selection of at most ONE Primary Classical Architecture Intervention  

---

## 1. Candidate Intervention Evaluation & Ranking Matrix

Following the empirical audits in Phases 1 through 5, six candidate options were evaluated against eight statutory criteria:

| Candidate Option | Description | Causal Evidence Quality | Observed Frequency | Tactical Importance | CPU Overhead | Correctness Risk | Search Compatibility | Overall Rank |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Option C (Selected)** | **MovePicker Stage Reform: Split Good vs Bad Captures & Countermove Staging** | **Tier 1 (Flaw Proven)** | **High (All Tactical Nodes)** | **Critical** | **Negative (Saves Work)** | **Zero (100% Legal Move Invariant)** | **Seamless** | **1** |
| **Option E** | Incremental On-Demand Selection Sort for Quiets | Tier 2 (Profiler Proven) | High (All Cutoff Nodes) | Moderate | Minor reduction in sort cycles | Low | High | **2** |
| **Option B** | Butterfly History Gravity Scale Normalization | Tier 2 (Scale Proven) | Moderate (Shallow Nodes) | Moderate | Negligible | Low | High | **3** |
| **Option A** | Numerical Score Rescaling in `score_move_for_ordering` | Tier 3 (Ineffective alone due to Staged loop) | High | Low (Overridden by Stages) | Zero | Low | High | **4** |
| **Option D** | Explicit RootMove List & Pinned Prior PV | Tier 3 (Root is 99% stable via TT) | Low (< 1% TT collision) | Low | Low | Low | Moderate | **5** |
| **Option F** | No Supported Intervention | N/A | N/A | N/A | Zero | Zero | N/A | **6** |

---

## 2. Selection Rationale for Option C (MovePicker Stage Reform)

### 2.1 The Concrete Problem Solved
In Phase 2, the audit revealed that `MovePicker` in non-check nodes forcefully yielded **all captures** in `STAGE_CAPTURES` before transitioning to `STAGE_KILLERS`.
- A suicidal queen capture ($Q \times P$, $\text{SEE} = -800$, score $\approx 19,200$) was searched *ahead* of Killer 1 ($90,000$), Killer 2 ($80,000$), Countermoves ($75,000$), and high-history quiet moves!
- This directly explains why in tactical and defensive positions, First-Move Cutoff rates collapsed to **$70.93\%$**, causing massive subtree explosions.

### 2.2 The Precise Architectural Specification for Candidate X19
In `MovePicker`, the stage machine is restructured into an 8-stage pipeline:

$$\text{STAGE\_TT} \longrightarrow \text{STAGE\_GOOD\_CAPTURES} \longrightarrow \text{STAGE\_KILLERS} \longrightarrow \text{STAGE\_COUNTERMOVE} \longrightarrow \text{STAGE\_QUIETS} \longrightarrow \text{STAGE\_BAD\_CAPTURES} \longrightarrow \text{STAGE\_DONE}$$

1. **Stage 1 (`STAGE_TT`):** Yield TT move if legal.
2. **Stage 2 (`STAGE_GEN_CAPTURES` & `STAGE_GOOD_CAPTURES`):**  
   Generate all captures and promotions via `native_generate_captures()`. Evaluate $\text{SEE}$:
   - Moves with $\text{SEE} \ge 0$ are classified as **Good Captures** and sorted by $\text{MVV/LVA} + \text{CaptureHistory}$.
   - Moves with $\text{SEE} < 0$ are buffered into `bad_caps`.
   - Yield good captures in descending score order.
3. **Stage 3 (`STAGE_KILLERS`):** Yield Killer 1, then Killer 2 (if distinct and legal).
4. **Stage 4 (`STAGE_COUNTERMOVE`):** If a countermove exists in `g_countermove_table[prev_from][prev_to]`, verify legality and yield immediately before quiet generation.
5. **Stage 5 (`STAGE_GEN_QUIETS` & `STAGE_QUIETS`):** Generate and sort quiet moves by History + Continuation History. Yield quiet moves.
6. **Stage 6 (`STAGE_BAD_CAPTURES`):** Yield deferred losing captures ($\text{SEE} < 0$).
7. **Stage 7 (`STAGE_DONE`):** Terminate search.

---

## 3. Strict Compliance with Governing Charter

1. **Zero New Pruning:** Not a single move is discarded or pruned. The union of yielded moves across all stages is **$100\%$ identical** to the baseline legal move set.
2. **Zero New Evaluation Terms:** Static evaluation is completely untouched.
3. **Zero Automated Parameter Fitting:** No Texel tuning, no SPSA, no machine learning. The stage separation threshold ($\text{SEE} \ge 0$ vs $\text{SEE} < 0$) is an exact, deterministic static exchange boundary.
4. **Independent Switchability:** Controlled via explicit UCI option and variant flag `X19`. When disabled, the engine reverts bit-for-bit to qualified baseline behavior (`X7` / `X12`).

---

## 4. Conclusion & Directive for Phase 7

Candidate **Janus Classical X19** will implement Option C: **MovePicker Stage Reform (Good Captures $\to$ Killers $\to$ Countermove $\to$ Quiets $\to$ Bad Captures)**. Development will proceed immediately to Phase 7.
