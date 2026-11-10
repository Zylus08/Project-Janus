# Project Janus — Phase 1, Milestone P1.6
## Next Classical Engineering Priority Roadmap (P1.7+)

**Date:** 2026-11-10  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Author:** Principal Computer Chess Engineer & Concurrency Architect  
**Scope:** Identifying and ranking the highest-leverage non-ML classical enhancements for Milestone P1.7.

---

### 1. Diagnosis of the Current Performance Frontier

Milestones P1.0 through P1.6 have established:
1. **Search Foundations:** Bitboard move generation, staged move ordering, quiescence search with delta pruning, iterative deepening with aspiration windows, null-move pruning, reverse futility pruning, and dynamic Late Move Reductions (LMR).
2. **Positional Understanding:** Pawn structure evaluation, passed pawn bonuses, king safety, open files, mobility, and a 64K pawn hash table (P1.5 E10).
3. **Hardware Scaling:** Thread-safe lockless cluster Transposition Table and Lazy SMP delivering **3.26x NPS speedup (81.5% efficiency)** at 4 threads (P1.6 X11).
4. **Current Elo Baseline:** X7 remains the incumbent production baseline (+242 Elo over C1, holding 5% score / resilient draws against unrestricted Stockfish 19 NNUE).

#### The Identified Architectural Bottlenecks:
- **Bottleneck A: Handcrafted Parameter Suboptimality (The "Intuition Ceiling").**  
  Janus currently utilizes over 120 handcrafted numerical constants across evaluation and search (e.g., LMR base formula, LMP quadratic threshold $3 + 3d^2$, pawn shield penalty, passed pawn rank bonuses). These values were selected based on human chess intuition and literature heuristics, rather than mathematical optimization against actual self-play game outcomes.
- **Bottleneck B: Multithreaded History Dispersion.**  
  While Lazy SMP scales raw nodes cleanly, helper threads operating with isolated history tables experience divergent move ordering, which pollutes the shared TT under fast blitz time controls.
- **Bottleneck C: Endgame Precision & Tablebase Absence.**  
  The engine spends critical clock time re-calculating known tablebase endgames (e.g., KRP vs KR, KBN vs K), occasionally conceding draws in winning positions.

---

### 2. Ranked Strategic Priorities for P1.7

```
+------------------------------------------------------------------------------------+
| RANK 1: Classical Parameter Optimization via Non-ML SPSA (Highest Leverage)        |
| - Expected Gain: +50 to +100 Elo                                                   |
| - Scope: Simultaneously optimize ~100 eval terms & search constants via self-play  |
| - Strictly Non-ML: Mathematical stochastic gradient descent on classical integers  |
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
| RANK 2: Multithreaded Shared History & Pruning Synchronization                     |
| - Expected Gain: +30 to +60 Elo in multithreaded play                              |
| - Scope: Cooperative history table updates to align worker move ordering           |
| - Eliminates the blitz TT pollution observed in P1.6 Match 2                       |
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
| RANK 3: Syzygy Tablebase Integration (3-4-5 Piece WDL / DTZ Probing)               |
| - Expected Gain: +15 to +25 Elo (and guaranteed zero endgame conversion blunders)  |
| - Scope: Zero-search instant endgame resolution via Fathom/Syzygy C++ library      |
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
| RANK 4: Advanced Tactical Pruning & Countermove History                            |
| - Expected Gain: +15 to +30 Elo                                                    |
| - Scope: Static Exchange Evaluation (SEE) pruning in alpha-beta, History pruning   |
+------------------------------------------------------------------------------------+
```

---

### 3. Detailed Specifications for High-Priority Tracks

#### Track 1: Non-ML SPSA Classical Parameter Tuning (Recommended P1.7 Focus)
- **Why SPSA?**  
  Simultaneous Perturbation Stochastic Approximation (SPSA) is the gold standard classical tuning technique used by top non-neural and hybrid engines (Stockfish pre-NNUE, Ethereal, Berserk, Rebel). It does not use neural networks, gradient backpropagation, or learned weights; it simply perturbs classical integer evaluation values, simulates paired self-play matches, and walks the parameter landscape toward higher win rates.
- **Tuning Targets:**
  1. *Material & Piece-Square Tables:* Midgame and Endgame values for Knights, Bishops, Rooks, and Queens.
  2. *Pawn Structure:* Doubled pawn penalty, isolated pawn penalty, backward pawn penalty, passed pawn bonuses by rank ($2..7$).
  3. *Search Parameters:* LMR divisor and base constants; LMP depth limit and threshold constants ($A + B \cdot d^2$); Null Move reduction formulas ($R = 3 + d/6$).
- **Methodology:**
  A lightweight Python-orchestrated SPSA loop running 20,000–50,000 fast games (100ms + 10ms) across all 16 cores will produce mathematically optimal handcrafted weights.

#### Track 2: Shared History Heuristics for Lazy SMP
- **Problem Solved:**  
  In P1.6 Match 2, helper threads searched divergent moves because their history tables were isolated (`thread_local`).
- **Solution:**  
  1. Maintain a master history table updated periodically by the main thread.
  2. Implement a lockless or atomic cooperative history update mechanism so all worker threads share information on which quiet moves fail high.
  3. This ensures helper threads prune the same unpromising subtrees and reinforce master thread alpha-beta cutoffs.

#### Track 3: Syzygy Tablebase Integration
- **Implementation:**  
  Integrate standard open-source C++ Syzygy probing (e.g. `fathom` or native bitboard probing) for 3-4-5 piece endgames.
- **Benefit:**  
  Instantaneous evaluation ($MATE$ or $DRAW$) at the root and leaf nodes, saving millions of nodes in simplified endgames and ensuring perfect endgame play.

---

### 4. Recommended P1.7 Roadmap Summary

The recommended course of action for Milestone P1.7 is:
1. **P1.7A:** Implement SPSA Classical Parameter Tuning to mathematically optimize the E10 evaluation terms and search pruning parameters.
2. **P1.7B:** Enhance Lazy SMP with cooperative history sharing to unlock the full competitive power of 4-thread parallel search.
3. **P1.7C:** Integrate 5-piece Syzygy tablebases for deterministic endgame perfection.

