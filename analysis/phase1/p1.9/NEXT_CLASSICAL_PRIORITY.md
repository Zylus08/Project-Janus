# Phase 12: Next Classical Research Priorities (Roadmap for Milestone P1.10)

**Milestone:** Phase 1, Milestone P1.9  
**Charter:** Classical Search Modernization & Strategic Engineering Roadmap  
**Target Milestone:** Phase 1, Milestone P1.10  
**Authors:** Principal Computer Chess Engineer & Search Architecture Group  

---

## 1. Retrospective: The Classical Handcrafting Ceiling

Milestones P1.5 through P1.9 have firmly established the empirical limits of pure manual heuristic engineering:
1. **The Handcrafting Asymptote:** Handcrafted chess features (passed pawn blockades, phalanx bonuses, central king open file penalties, king opposition) are theoretically sound and solve specific diagnostic failures (improving tactical depth by $+0.08$ plies and endgame conversion from $70\%$ to $75\%$).
2. **The Tournament Equilibrium:** In competitive play against X12 across 300 games (Matches B and C), Candidate X14 scored $48.75\%$ and $50.50\%$. The net Elo gain is $\approx 0$. Manually adjusted weights (e.g. $\pm 12$ to $\pm 25$ cp) inevitably over-penalize certain positions while under-penalizing others.
3. **The Single-Thread Paradox:** While multithreaded Lazy SMP can absorb evaluation complexity through parallel node throughput, single-threaded search suffers severe depth penalties when evaluation complexity rises ($40.25\%$ for X14 vs X7).

---

## 2. Priority 1: Large-Scale Non-ML Parameter Optimization (SPSA)

To convert rich classical evaluation terms into measurable tournament Elo, parameter weights must be calibrated across hundreds of thousands of games:
- **Technique:** Simultaneous Perturbation Stochastic Approximation (SPSA) applied strictly to handcrafted classical evaluation terms and search reduction parameters.
- **Strict Non-ML Compliance:** SPSA is an algorithmic numerical optimization method for classical scalar coefficients; it introduces zero neural networks, zero tensor operations, and zero learned feature representations.
- **Target Parameters:**
  - Game phase interpolation boundaries ($MG \to EG$).
  - Passed pawn rank bonuses and blockade penalties.
  - King safety danger multipliers and pawn storm penalties.
  - LMR base reductions and depth thresholds.

---

## 3. Priority 2: History-Directed Search Selectivity

Analysis of the 240-position Failure Atlas revealed that $63.4\%$ of failures are multi-causal ($F7$), where search reductions are applied to quiet moves that actually hold defensive resources:
- **Capture History Table:** Maintain a dedicated $6 \times 64$ capture history matrix to differentiate winning tactical captures from losing sacrificial blunders during quiet move sorting.
- **Continuation History Extensions:** Expand continuation history to 2-ply and 4-ply ancestors to dynamically inform Late Move Reductions (reducing LMR depth reductions for moves with strong historical refutation scores).
- **History-Pruning Synergy:** Prune quiet moves late in the move list only if their history score falls below a dynamically calibrated negative threshold.

---

## 4. Priority 3: Tablebase-Directed Search Pruning

With Ronald de Man Syzygy tablebase support fully integrated into the Janus architecture:
- **Search-Time WDL Probing:** Probe tablebases at interior search nodes when total piece count $\le 5$ and remaining search depth $\ge 2$.
- **Sub-Tree Pruning on Proven Outcomes:**
  - Cut off subtrees immediately upon finding a proven Win or Loss in tablebase.
  - Zero search expansion on theoretical dead draws when searching to secure a draw.
- **Prefetching & Memory-Mapped Tablebase Files:** Implement asynchronous tablebase prefetching on worker threads to eliminate I/O stalls during parallel search.

---

## 5. Proposed Qualification Framework for P1.10

- **Baseline Controls:** Janus Classical X7 (1T) and Janus Classical X12 (4T).
- **Candidate Target:** Janus Classical X15.
- **Minimum Match Power:** All head-to-head matches must feature a minimum of 100 opening pairs (200 games) at both fast (1.0s + 50ms) and slow (3.0s + 100ms) time controls.
- **Preregistered Gate:** A candidate must demonstrate a statistically significant positive Elo delta ($p < 0.05$) across both time controls to qualify for promotion.
