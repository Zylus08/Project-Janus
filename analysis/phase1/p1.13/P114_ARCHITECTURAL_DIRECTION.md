# Project Janus: Milestone P1.14 Strategic Architectural Direction
**Document ID:** `analysis/phase1/p1.13/P114_ARCHITECTURAL_DIRECTION.md`  
**Date:** November 13, 2026  
**Author:** Classical Computer Chess Engine Architect & C++17 Systems Specialist  
**Governing Charter:** Strictly Non-ML Classical Development  
**Parent Baselines:** Janus Classical X7 (`b34e342`, 1T), Janus Classical X12 (`78ca3d5`, 4T)  
**Historical Anchors:** Stockfish 4 (Floor), Stockfish 11 (Ceiling)  

---

## 1. Executive Direction & Problem Statement

Milestone P1.13 achieved two decisive scientific outcomes:
1. **The Diagnostic Atlas:** Using a 60-position stratified test corpus and deep profiling against Stockfish 11, we established that **53.3% of Janus's suboptimal decisions stem from Q2 (Quiet Horizon Instability, 30.0%) and Q3 (Move Ordering Inversions, 23.3%)**, rather than outright tactical blunders (Q1, only 8.3%).
2. **The LMR Lesson:** Candidate X18 proved that aggressively pruning nodes via raw 1-ply butterfly history ($H > 8000 \to R-1$; $H < -2000 \to R+1$) cuts search tree volume by 24% but produces an unmitigated **$-63$ Elo regression on 1 thread**.

The strategic mandate for Milestone P1.14 is clear: **We must transition from primitive, static heuristic cutoffs to principled, structurally stable search selectivity.**

---

## 2. Core Architectural Lessons from P1.13

### Lesson A: Butterfly History Alone Is Too Noisy for Quiet Pruning
* A simple $64 \times 64$ piece-to-square table records whether a move caused a beta-cutoff *anywhere* in the tree.
* It lacks context: a knight move to `f3` may be fantastic after `1.e4 e5 2.Nf3`, but suicidal after `1.d4 Nf6 2.c4 e6 3.Nf3`.
* By applying an extra reduction $R = R + 1$ to quiet moves with negative butterfly history, X18 reduced crucial defensive replies that were tactically sound in their specific local context.

### Lesson B: Static Integer Thresholds Fail Across Varying Depths
* Hardcoded thresholds like $+8000$ and $-2000$ behave erratically when the search depth shifts from ply 6 to ply 12.
* At ply 6, history values rarely exceed 2000; at ply 12, bonuses of $d^2 = 144$ accumulate rapidly to 15,000.
* Mature classical engines (such as Stockfish 8 through 11) compute reductions dynamically using continuous linear scaling:
  $$R_{\text{effective}} = R_{\text{base}} - \text{round}\left(\frac{\text{history}}{\text{scalingFactor}}\right)$$

### Lesson C: Multithreading Masks Selective Fragility
* In 4-thread Lazy SMP, helper threads searching with staggered depth offsets search different branches and rescue blunders caused by excessive pruning.
* Single-threaded play is the true litmus test for classical search selectivity. An intervention that regresses on 1T must never be accepted simply because it survives on 4T.

---

## 3. Targeted Strategic Recommendations for Milestone P1.14

To systematically address the Q2 (quiet horizon instability) and Q3 (move ordering) bottlenecks identified in P1.13, P1.14 should investigate **at most one** of the following three tightly bounded classical search interventions:

### Option 1 (Primary Recommendation): 2-Ply Continuation History Table
* **Architecture:**  
  Maintain a continuation history table `continuation_history[piece][to_sq][prev_piece][prev_to_sq]`.
* **Mechanism:**  
  When evaluating quiet moves at ply $n$, index the history bonus not just by the current move, but by the opponent's previous move (ply $n-1$).
* **Benefit:**  
  Directly addresses Q3 (move ordering inversions) by prioritizing quiet moves that respond appropriately to the opponent's immediate threat, avoiding premature LMR reductions on tactical defenses.
* **Charter Compliance:** Strictly non-ML; standard $O(1)$ tabular array indexing in C++17.

### Option 2 (Alternative): Dynamic Depth-Scaled LMR with Soft History Damping
* **Architecture:**  
  Replace static boolean threshold checks with a continuous logarithmic LMR table and dynamic history adjustment:
  $$R = \text{LMR\_Table}[\text{depth}][\text{moveCount}] - \frac{\text{History}[from][to]}{4096}$$
* **Constraint:**  
  Clamp reduction adjustments to $[-1, +1]$ to prevent runaway pruning. Ensure no reduction is applied if the move gives check, is in check, or if the node is in an endgame.

### Option 3 (Move Ordering): Counter-Move Heuristic & Killer Separation
* **Architecture:**  
  Store a counter-move table `counter_moves[prev_from][prev_to]`.
* **Mechanism:**  
  If the move that previously refuted `prev_move` is legal, order it immediately after the transposition table move and primary killer move.
* **Benefit:**  
  Reduces effective branching factor without discarding search tree volume.

---

## 4. Strict Anti-Patterns to Prohibit in P1.14

1. **PROHIBITED:** Introducing another handcrafted evaluation feature pack (pawn structure, king safety, bishop pairs) before search decision stability is restored. P1.10 and P1.12 proved that evaluation enhancements without search selectivity stability lead to immediate regressions.
2. **PROHIBITED:** Static, unscaled pruning cutoffs that trigger indiscriminately regardless of nominal search depth.
3. **PROHIBITED:** Tuning parameters via SPSA, Texel tuning, or gradient descent against external game databases. All parameters must remain handcrafted, rationalized, and grounded in domain knowledge.
4. **PROHIBITED:** Modifying time management heuristics in the same milestone as search selectivity changes. Conflating time allocation with alpha-beta pruning destroys causal attribution.

---

## 5. Conclusion & Transition Plan

Milestone P1.13 successfully identified the quantitative mechanism behind Janus's search inefficiency. Milestone P1.14 has a concrete, empirically verified target: replace noisy 1-ply butterfly reductions with **principled 2-ply continuation history and soft dynamic scaling**, targeting a measurable reduction in Q2/Q3 decision defects while safeguarding tactical stability on 1 thread.

