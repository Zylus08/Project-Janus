# Milestone P1.21: Classical Architecture Pivot Decision & Milestone P1.22 Specification

**Milestone:** Phase 1, Milestone P1.21 (Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate)  
**Deliverable:** `analysis/phase1/p1.21/P122_ARCHITECTURE_PIVOT_DECISION.md`  
**Phase:** Phase 16 — Classical Architecture Pivot Decision  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-15  

---

## 1. Executive Summary & Historic Milestone Retrospective

Project Janus Phase 1 was chartered with a strict, non-negotiable scientific mandate: **explore the theoretical and practical limits of strictly non-ML computer chess architecture**. Over twenty-one intense engineering milestones (P1.1 through P1.21), the engine evolved from a basic alpha-beta minimax search into a sophisticated multi-threaded classical system equipped with:
- Bitboard move generation with 23M NPS movegen throughput,
- Corrected tactical quiescence search with stand-pat and in-check evasion semantics (P1.16–P1.17),
- Staged capture ordering, killer move heuristics, countermove tables, and 2-ply continuation history (P1.14–P1.15),
- 64K-entry thread-local pawn hash table (P1.10),
- Lockless transposition table clusters supporting scalable 4T SMP search (P1.7, X12),
- Multi-component classical evaluation spanning material, piece-square tables, pawn structure, outposts, king safety, and endgame opposition (P1.2, P1.18, P1.20).

### The Inescapable Experimental Reality:
Despite achieving peak correctness (zero perft bugs, 100% referee pass rate) and exceptional move ordering ($82.5\%\text{–}97.2\%$ first-move cutoffs), **every attempt to advance competitive strength beyond the frozen baselines (X7 on 1T and X12 on 4T) has systematically stalled or regressed**:
- Milestone P1.18 (X23): Adding backward pawns and king file exposure caused slow-TC regression.
- Milestone P1.19 (X24): Isolating backward pawns caused a $-6.0\%$ regression vs X22.
- Milestone P1.20 (X25): Ablating backward pawns and introducing connected passers recovered parity ($49.0\%$) but yielded $0.0\text{ Elo}$ net progress.
- Milestone P1.21 (X26): Auditing the search contract and repairing all four structural defects in Reverse Futility Pruning resulted in a $-50\text{ to }-90\text{ Elo}$ regression ($37.0\%\text{–}42.5\%$ score) due to the "Pruning Paradox".

The scientific conclusion is absolute: **The incremental handcrafted classical paradigm in Janus has reached a hard mathematical and structural ceiling.** 

This document formally terminates incremental tuning and specifies the **Milestone P1.22 Architectural Pivot**.

---

## 2. Comprehensive Retrospective on Phase 1 Classical Development (P1.10–P1.21)

### 2.1 What Succeeded (Foundational Assets Preserved)
1. **Core Move Generation & Game Invariants:**
   - Bitboard move generation, attacks table, make/unmake state transitions, and perft performance are completely rock-solid ($23.6\text{M NPS}$, 0 bugs across all suites).
2. **Quiescence Search Correctness (P1.16–P1.17):**
   - Correcting the illegal stand-pat behavior in check and ensuring checkmate recognition in leaf nodes eliminated catastrophic tactical blunders.
3. **Move Ordering Infrastructure:**
   - Staged move picking, MVV-LVA, killer slots, countermove history, and continuation history deliver near-optimal first-move cutoff rates ($> 90\%$).
4. **Hardware Utilization & Throughput:**
   - Single-thread NPS exceeds $1.3\text{M NPS}$ under full search.
   - Lockless TT clusters and multi-threaded SMP scaling operate cleanly up to 16 threads.

### 2.2 What Failed & Root-Cause Diagnosis
1. **The Handcrafted Evaluation Trap:**
   - Without machine learning, NNUE, Texel tuning, or SPSA, evaluation terms are tuned by human intuition and small diagnostic batteries.
   - Because chess positional features are deeply non-linear, adding a penalty for one feature (e.g., $-15\text{ cp}$ for backward pawns) introduces discontinuities.
   - These discontinuities degrade evaluation smoothness.
2. **Search–Evaluation Coupling (The Fatal Vulnerability):**
   - Forward pruning heuristics (RFP, NMP, LMP, LMR) rely directly on static evaluation thresholds ($\text{StaticEval} - \text{Margin} \ge \beta$).
   - When static evaluation is noisy or discontinuous, pruning cutoffs misfire wildly: quiet branches explode in size ($+20\%\text{–}60\%$ nodes), while critical tactical branches get erroneously clipped.
3. **The Pruning Paradox:**
   - When search contract bugs are fixed to make forward pruning theoretically sound (Option A), the engine loses the aggressive, unsound shortcuts that previously allowed it to reach high nominal search depths.
   - The resulting $1\text{–}2$ ply nominal depth deficit destroys competitive strength under timed match conditions.

---

## 3. Milestone P1.22 Architectural Pivot Specification

Milestone P1.22 will execute a **clean-sheet classical search redesign and structural decoupling**, focusing on search robustness, evaluation smoothing, and decision-making stability rather than adding handcrafted positional terms.

### 3.1 Pillar 1: Search–Evaluation Decoupling (Relative Pruning Gates)
- **Elimination of Raw Centipawn Pruning Inequalities:**
  - Forward pruning must not depend solely on the raw static evaluation magnitude against $\beta$.
  - Implement **relative evaluation deltas**: evaluate change in evaluation relative to parent nodes ($\Delta\text{Eval} = \text{StaticEval} - \text{ParentStaticEval}$).
- **Evaluation Bound Verification:**
  - Replace hard scalar cutoffs with dynamic confidence intervals derived from subtree variance and search depth.
- **Fail-Low / Fail-High Asymmetry Protection:**
  - Prevent asymmetric pruning penalties that induce search tree explosions when a side possesses minor positional weaknesses.

### 3.2 Pillar 2: Clean-Sheet Classical Search Redesign
- **Simplified Core Negamax:**
  - Strip away legacy accumulated flags, ad-hoc tuning knobs, and variant-specific exceptions.
  - Implement an airtight, unified alpha-beta framework with formally verified invariant assertions.
- **Modern Selectivity Architecture:**
  - **Dynamic LMR:** Logarithmic depth/move table modulated by history score confidence and tactical check status, with verified re-search safety.
  - **Safe Pruning Contracts:** Re-architect RFP, NMP, and LMP from the ground up so that selective pruning preserves depth without depending on evaluation artifacts.
  - **Aspiration Window Reform:** Adaptive aspiration windows that widen gracefully upon fail-low/fail-high without thrashing the transposition table.

### 3.3 Pillar 3: Evaluation Smoothing & Calibration
- **Evaluation Smoothing:**
  - Apply non-linear tapering and clamping to prevent extreme evaluation spikes in quiet positions.
- **Phase Interpolation Integrity:**
  - Eliminate game-phase boundary discontinuities between middlegame and endgame terms.
- **Strictly Non-ML Non-Regression Principle:**
  - Zero neural networks, zero NNUE, zero learned parameters. All improvements must remain $100\%$ classical and non-ML, maintaining complete fidelity to the project charter.

---

## 4. Transition Criteria to Phase 2

Milestone P1.22 represents the final, definitive milestone of **Project Janus Phase 1 (Classical Computer Chess)**.
- If the P1.22 clean-sheet search redesign achieves statistically significant superiority over frozen baselines X7 ($+30\text{ Elo}$) and X12 ($+30\text{ Elo}$) under long time controls, it will be crowned the **Ultimate Classical Janus Champion**.
- Regardless of whether P1.22 supersedes X7/X12 or confirms the ultimate asymptotic ceiling of the classical engine, Milestone P1.22 will conclude Phase 1.
- Project Janus will then transition formally to **Phase 2 (Modern Hybrid Architecture)**, where modern evaluation representations will be explored.

---

## 5. Formal Ratification

The Principal Computer Chess Engine Architect, C++17 Search Engineer, Classical Evaluation Specialist, and Statistical Auditor hereby formally ratify this Architectural Pivot Decision.
