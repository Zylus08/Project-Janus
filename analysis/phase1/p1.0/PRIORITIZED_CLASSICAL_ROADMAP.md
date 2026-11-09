# PROJECT JANUS — PHASE 1, MILESTONE P1.0
## Prioritized Classical Development Roadmap (Milestones P1.1 through P1.7)

**Status:** APPROVED & RATIFIED  
**Date:** 2026-11-09  
**Auditor / Principal Engineer:** Principal Computer Chess Engineer & C++17 Systems Architect  
**Worktree Base:** `E:\ChessXML\project-janus-phase1` (Branch: `phase1/classical-janus`)  
**Target Engine Lineage:** Janus Classical X (`engine/classical_x/`)  

---

## 1. Executive Summary & Strategic Program Overview

The Project Janus Classical Engine Supremacy Program is established to engineer a state-of-the-art, strictly non-neural chess engine capable of demonstrating superior playing strength against elite classical benchmarks and systematically closing the gap to unrestricted modern engines.

This document establishes the official engineering roadmap across Milestones P1.1 through P1.7. Each milestone defines explicit:
- Algorithmic architectures and file layouts,
- Target Elo gains with 95% statistical confidence thresholds,
- Correctness, regression, and performance gates,
- Risk mitigations and dependency graphs.

```
+----------------------------------------------------------------------------------------------------+
|                               PROGRAM ARCHITECTURAL DEPENDENCY GRAPH                               |
+----------------------------------------------------------------------------------------------------+

  [P1.0: Baseline Audit & Gap Recovery]
                 |
                 v
  [P1.1: Modern Classical Search] -------------------------------+ (Est. +250 to +350 Elo)
                 |                                               |
                 v                                               |
  [P1.2: Movegen & Board Rep Performance]                        | (Est. +100 to +150 Elo)
                 |                                               |
                 v                                               v
  [P1.3: Advanced Move Ordering & History] ------> [P1.4: Classical Evaluation HCE] (+250 to +350 Elo)
                 |                                               |
                 v                                               v
  [P1.6: Time & Search Control]                    [P1.5: Classical Texel Tuning]   (+80 to +120 Elo)
                 |                                               |
                 +-----------------------+-----------------------+
                                         |
                                         v
                         [P1.7: Parallel Lazy SMP Architecture]   (+150 to +250 Elo)
```

---

## 2. Mandatory Strategic Decision: P1.1 Immediate Priority

### Ratified Decision:
**Milestone P1.1 is prioritized exclusively on Modern Classical Search (Search Architecture Modernization)** — specifically implementing:
1. Null-Move Pruning (NMP),
2. Reverse Futility Pruning (RFP),
3. Aspiration Windows,
4. Quiescence Static Exchange Evaluation (SEE) Pruning.

### Quantitative Justification from P1.0 Measured Telemetry:

1. **The Branching Factor Crisis ($EBF = 6.557$):**
   In the P1.0 search profile, Janus C1 exhibited an Effective Branching Factor of $6.557$. To reach a nominal depth of only 7 plies across the 50 standardized positions, C1 searched **22,657,634 nodes** (an average of $453,152$ nodes per position). In contrast, Stockfish 19 reached depth 12 (seldepth 17) searching only **1,085,614 nodes** ($21,712$ nodes per position). C1 suffers from a **20.87x node volume explosion**.
2. **Evaluation Speed is Not the Bottleneck:**
   C1's handcrafted evaluation takes only **104.2 nanoseconds per call** and accounts for a mere **7.4% of search CPU time**. Enriching the evaluation function first (e.g., adding mobility, king safety, and pawn structure) would increase evaluation cost to $\sim 250\text{ ns}$. If applied to an unpruned tree with $EBF = 6.56$, the search depth would collapse from Depth 7 down to Depth 5 in standard blitz time controls, inducing immediate tactical blindness and catastrophic rating regression.
3. **The Quiescence Search Hemorrhage (74.8% of nodes):**
   C1 spent **3,898,715 out of 5,213,848 nodes (74.8%)** inside quiescence search because it currently explores every capture regardless of exchange value (`UseSEEInQuiescence=false`). Implementing SEE pruning in quiescence directly cuts the search tree by $40\%\text{ to }50\%$.
4. **Conclusion:**
   Search modernization (P1.1) collapses the tree, lowering the EBF from $6.56$ to $\sim 3.0$ and increasing effective search depth by $+2\text{ to }+3$ plies at identical time controls. This establishes the deep, stable search tree required to host advanced classical evaluation terms in subsequent milestones.

---

## 3. Granular Milestone Roadmap Specifications

### Milestone P1.1: Modern Classical Search
- **Primary Objective:** Eliminate astronomical tree bloat via standard forward pruning and aspiration search.
- **Expected Strength Gain:** **+250 to +350 Elo** over Classical Baseline C1.
- **Key Algorithmic Implementations:**
  - *Null-Move Pruning (NMP):* Make null move with reduction $R=3$; skip if in check or side to move has only King + Pawns (zugzwang risk).
  - *Reverse Futility Pruning (RFP):* At pre-frontier nodes ($d \le 3$), if static eval minus margin exceeds $\beta$, return static eval.
  - *Aspiration Windows:* Iterative deepening around root score using dynamic window $[\alpha - \delta, \beta + \delta]$ with $\delta = 25\text{ cp}$.
  - *Quiescence SEE Pruning:* Prune captures where $SEE < 0$ in quiescence.
- **Source Layout:** `engine/classical_x/search/`, updating `janus_classical_x.cpp`.
- **Testing & Qualification Gates:**
  - EBF Reduction Gate: Measured EBF on 10 profile positions must drop from $6.56$ to $\le 3.50$.
  - Perft / Correctness: 100% pass on 6-position perft suite to depth 5; 0 illegal moves.
  - Match Gate: Statistically significant win over frozen C1 across 100 games at 3.0s+0.1s ($\Delta\text{Elo} \ge +200$, $p < 0.001$).

---

### Milestone P1.2: Move Generation & Board Representation Performance
- **Primary Objective:** Optimize move generation throughput to eliminate the 84.3% CPU time bottleneck.
- **Expected Strength Gain:** **+100 to +150 Elo** (via $2.5\times\text{ to }4\times$ NPS speedup).
- **Key Algorithmic Implementations:**
  - *Magic Bitboards:* Precomputed attack lookup tables for Rooks and Bishops using 64-bit magic multipliers.
  - *Deferred Legality Validation:* Generate pseudo-legal moves without upfront `is_square_attacked()` king checks; validate king safety only when move is picked.
  - *Specialized Capture Generation:* Dedicated generator emitting only captures and promotions for quiescence search.
- **Testing & Qualification Gates:**
  - NPS Gate: Move generation speed must exceed 50 million pseudo-legal moves/second in perft.
  - Perft Invariance: 100% bit-exact node count match across depths 1 through 6 against standard perft tables.

---

### Milestone P1.3: Advanced Move Ordering & History Heuristics
- **Primary Objective:** Maximize first-move beta cutoff rate beyond current 78.1%.
- **Expected Strength Gain:** **+120 to +180 Elo**.
- **Key Algorithmic Implementations:**
  - *Staged MovePicker:* Structured generator yielding: 1. TT move $\to$ 2. Good Captures (MVV/LVA + SEE $\ge 0$) $\to$ 3. Killer 1 $\to$ 4. Killer 2 $\to$ 5. Countermove $\to$ 6. Quiet History $\to$ 7. Bad Captures (SEE $< 0$).
  - *Butterfly History Matrix:* 3D table `history[color][from][to]` with gravity aging ($\pm \text{depth}^2$).
  - *Countermove Heuristic:* `countermoves[from][to]` storing best response to opponent's previous move.
- **Testing & Qualification Gates:**
  - Cutoff Gate: First-move beta cutoff rate must increase from 78.1% to $\ge 88.0\%$.

---

### Milestone P1.4: Handcrafted Classical Evaluation (HCE) Enrichment
- **Primary Objective:** Replace basic PST with a deep, principled handcrafted classical evaluation engine.
- **Expected Strength Gain:** **+250 to +350 Elo**.
- **Key Algorithmic Implementations:**
  - *Mobility:* Bitboard safe mobility calculation for Knights, Bishops, Rooks, and Queens.
  - *Pawn Structure:* Dedicated pawn evaluation module tracking passed pawns (rank, protected, free path), isolated, doubled, and backward pawns.
  - *King Safety:* Pawn shield tracking, open files directed at king, and king attack zone accumulation.
  - *Piece Coordination:* Bishop pair bonus (+40 cp), rook on open/semi-open files, rook on 7th rank, knight outposts.
  - *Endgame Knowledge:* Passed pawn race logic, king centralization, and opposition.
- **Testing & Qualification Gates:**
  - 50-Position Suite Gate: Best-move agreement against Stockfish 19 must rise from 26.0% to $\ge 50.0\%$.
  - Closed Position Gate: Move agreement in closed structures must rise from 0.0% to $\ge 40.0\%$.

---

### Milestone P1.5: Classical Parameter Tuning (Texel's Tuning Method)
- **Primary Objective:** Optimize all handcrafted evaluation constants using logistic regression.
- **Expected Strength Gain:** **+80 to +120 Elo**.
- **Key Algorithmic Implementations:**
  - Automated Texel tuning harness minimizing Mean Squared Error (MSE) between evaluation sigmoid $S(\text{eval}, K) = \frac{1}{1 + 10^{-K \cdot \text{eval} / 400}}$ and actual game outcome $R \in \{0, 0.5, 1\}$ over 1,000,000 quiet positions.
  - Zero ML or neural dependencies: purely tunes scalar integer/float weights of handcrafted formulas.
- **Testing & Qualification Gates:**
  - Validation MSE Gate: Evaluation error against held-out grandmaster test set must decrease by $\ge 15\%$.
  - Match Gate: Tuned HCE must defeat untuned HCE by $\ge +60\text{ Elo}$ in 200 games.

---

### Milestone P1.6: Dynamic Time Management & Search Control
- **Primary Objective:** Maximize clock utilization efficiency in tournament play.
- **Expected Strength Gain:** **+50 to +80 Elo**.
- **Key Algorithmic Implementations:**
  - Soft and hard time boundaries per move.
  - Dynamic scaling: extend move time by up to $2.5\times$ when best move flips or score drops between depths.
  - Early move termination when best move commands $>85\%$ of total node count.
- **Testing & Qualification Gates:**
  - Time Forfeit Rate: 0.0% across 500 bullet and blitz games.
  - Time Usage Efficiency: Measurable score gain against fixed-time C1 under sudden death clocks.

---

### Milestone P1.7: Parallel Search Architecture (Lazy SMP)
- **Primary Objective:** Scale Janus Classical across multi-core systems.
- **Expected Strength Gain:** **+150 to +250 Elo** (at 4–8 threads).
- **Key Algorithmic Implementations:**
  - Shared lockless Transposition Table using atomic 128-bit key-data stores.
  - Lazy SMP worker threads executing independent alpha-beta with depth/history jitter.
- **Testing & Qualification Gates:**
  - Scaling Efficiency: Speedup factor of $\ge 3.2\times$ at 4 threads and $\ge 5.5\times$ at 8 threads.
  - Thread Safety: 0 data races detected under thread sanitizer; 0 crashes or deadlocks across 10,000 games.

---

## 4. Risk Assessment & Scientific Mitigation Protocol

| Risk Factor | Severity | Probability | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **Search Instability from Aggressive Pruning** | High | Medium | Implement verification searches for NMP at low depths; enforce conservative RFP margins ($80 \times d$). |
| **Pawn Structure Evaluation Slowdown** | Medium | High | Implement a 16K-entry Pawn Hash Table to cache pawn evaluations across identical pawn structures. |
| **Search Tree Asynchrony in SMP** | High | Low | Enforce lockless XOR-hash verification on all Transposition Table reads and writes. |
| **Regression against Historical Frozen C1** | Critical | Very Low | Run mandatory automated 100-game regression suite against C1 before committing any milestone. |

---

## 5. Audit Verdict & Approval

The Project Janus Phase 1 Development Roadmap is officially ratified. Milestone P1.1 is designated as the active engineering target.
