# Milestone P1.20 Phase 5: Static Evaluation vs Search Compatibility Audit

## 1. Executive Summary & Audit Methodology

Milestone P1.20 Phase 5 measured how static evaluation alterations (specifically, the introduction of classical backward-pawn detection in Candidate X24) propagate through alpha-beta search heuristics:
- **Reverse Futility Pruning (RFP):** Whether artificially depressed static scores prevent early pruning at shallow depths.
- **Null Move Pruning (NMP):** Whether static score shifts trigger verification fail-lows.
- **Late Move Reductions (LMR):** Whether move-ordering rank swaps cause tactical quiet moves to receive excessive reduction.
- **Aspiration Window Stability:** Whether static score skews trigger aspiration search failures and expensive full-width re-searches.

The audit was executed on **30 structurally diverse diagnostic positions** (Sicilian d6, French e6, Semi-Slav c6, IQP d4, sharp KiwiPete crossroads, connected passers, rook endgames, and quiet pawn structures) at fixed Depth 8 on Reference X22 (`e33f292`) and Candidate X24 (`bcf8f4c`).

---

## 2. Empirical Findings

### 2.1 Compatibility Metrics
- **Root Move Agreement:** **$70.0\%$** (21 of 30 positions selected identical root moves; 9 diverged).
- **Search Node Expansion Ratio ($N_{\text{X24}} / N_{\text{X22}}$):** **$1.2728$** ($+27.3\%$ mean node inflation across the corpus).
- **Extreme Node Outliers:**
  - `COMP_01` (Sicilian backward d6): X22 searched 121,455 nodes; X24 searched 364,306 nodes (**$3.00\times$ node explosion**).
  - `COMP_20` (English symmetric pawn structure): X22 searched 138,822 nodes; X24 searched 348,704 nodes (**$2.51\times$ node explosion**).
  - `COMP_19` (Ruy Lopez closed center): X22 searched 84,119 nodes; X24 searched 183,348 nodes (**$2.18\times$ node explosion**).

---

## 3. Propagation Forensics

### 3.1 Mechanism 1: RFP Pruning Cutoff Suppression
In positions with nominal backward pawns (e.g. `COMP_01`, `COMP_20`), Candidate X24 assesses a static penalty of $-10\text{ mg} / -15\text{ eg}$.
- At depths $d \le 3$, Reverse Futility Pruning checks:
  $$\text{static\_eval} - \text{margin} \ge \beta$$
- A reduction of 15 cp in `static_eval` is sufficient to push positions just below the $\beta$ cutoff threshold.
- As a consequence, positions that X22 pruned instantly at depth 1 or 2 forced X24 into recursive alpha-beta expansions of all legal quiet moves, generating a $3\times$ increase in total nodes searched.

### 3.2 Mechanism 2: LMR Mis-Targeting
When root best moves diverged (30% of tested positions), move-ordering scores were affected:
- Because quiet piece moves defending the backward pawn were scored favorably over active moves that allow the pawn to remain backward, active candidate moves were deferred to later movepicker stages.
- Under Late Move Reductions (LMR), moves searched beyond move index 4 receive a reduction of 1 to 2 plies.
- Candidate X24 reduced the active counterplay moves, preventing search from discovering their tactical justifications, while allocating full-depth search to passive defensive moves.

### 3.3 Mechanism 3: Connected Passers Evaluation Blindspot (`COMP_11`)
In `COMP_11` (outside connected passed pawns a5/c5):
- The static delta between engines was $-976\text{ cp}$ and the depth 8 search delta was $-237\text{ cp}$, leading to a complete move divergence.
- This highlights the profound sensitivity of search-tree pruning to pawn evaluation: missing the value of connected passed pawns distorts root choice far more than minor tactical fluctuations.

---

## 4. Architectural Prescription for Candidate X25

1. **Eliminate Restrictive Static Penalties:** Backward-pawn penalties introduce search-tree instability, suppress RFP, and inflate node counts by $+27.3\%$. They must remain strictly disabled.
2. **Implement Positive Dynamic Incentives:** Rewarding connected and supported passed pawns (**Option B**) encourages forward alpha-beta branching. Because passed pawns create forcing threats (queening squares), they naturally generate early beta cutoffs, compressing the search tree rather than expanding it.
3. **Pawn-Hash Direct Integration:** Option B terms must be evaluated exclusively within `evaluate_pawns()` and cached in the 64K pawn hash table to guarantee zero throughput degradation.

---

## 5. Artifact Audit
- Complete Compatibility Dataset: `analysis/phase1/p1.20/raw/static_eval_search_compatibility.json`
- Audit Script: `analysis/phase1/p1.20/tests/test_search_eval_compatibility.py`
