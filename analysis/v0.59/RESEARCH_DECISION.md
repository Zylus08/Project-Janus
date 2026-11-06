# Project Janus v0.59 — Research Decision & Classification Report

**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Team & Independent Scientific Auditor  
**Milestone Stage:** Phase 7 — Research Decision & Next-Direction Qualification  
**Evaluated Milestone:** Project Janus v0.59 (Neural Policy Effectiveness, Search Interaction & Causal Ablation)

---

## 1. Formal Answers to the Eight Research Questions

### Question 1: Does the neural model materially alter search ordering?
**Empirical Answer:** **Only among quiet non-killer moves; not for the primary searched move.**  
At the root node, MicroPolicyNet reorders $85.3\% - 86.7\%$ of quiet candidate moves. However, for the first-searched move, the neural policy has zero influence: in $80\% - 86\%$ of positions, the first move searched is preserved by classical iterative-deepening transposition table persistence (`tt_move` score $10,000,000$).

### Question 2: How often is its ordering superseded by classical heuristics?
**Empirical Answer:** **80.0% to 86.0% at the root, and 100% in capture/tactical situations.**  
The neural policy score ($20,000 - 70,000$) is capped strictly below killer moves ($80,000 / 90,000$), captures ($100,000+$), promotions ($800,000+$), and the transposition table move ($10,000,000$). Consequently, classical search heuristics supersede neural recommendations in $>80\%$ of root positions and in all tactical situations.

### Question 3: Does learned policy outperform randomized ordering?
**Empirical Answer:** **No. Performance is bit-exact identical.**  
In the Phase 2 causal ablation across 50 positions at depths 4, 5, and 6:
$$\Delta(\text{Nodes}_{\text{C1: Trained}} - \text{Nodes}_{\text{C2: Random}}) = \mathbf{0.0\text{ nodes}} \quad (t = 0.000, \ p = 1.0000)$$
$$\Delta(\text{Nodes}_{\text{C1: Trained}} - \text{Nodes}_{\text{C3: Shuffled}}) = \mathbf{0.0\text{ nodes}} \quad (t = 0.000, \ p = 1.0000)$$
Because the TT move is searched first and establishes alpha, all subsequent quiet moves fail low. In an all-node search, every branch must be fully searched, making tree size mathematically invariant to the permutation of quiet moves at the root.

### Question 4: Which node types benefit from neural guidance?
**Empirical Answer:** **None under current alpha-beta integration.**  
- **Root Nodes:** Dominated by iterative deepening TT persistence.
- **Fail-High (Cutoff) Nodes:** Beta cutoffs are triggered by captures or killer moves in nanoseconds; neural forward passes ($280\ \mu\text{s}$) are far too slow.
- **Fail-Low (All) Nodes:** All moves must be searched regardless of order; reordering quiet moves provides zero pruning benefit.

### Question 5: Does selective internal-node inference justify its computational cost?
**Empirical Answer:** **No.**  
Evaluating the neural policy at internal nodes (G2) or along the principal variation (G3) consumes $40 - 90\text{ ms}$ of CPU time without reducing total nodes ($+1.20\%$ at Depth 6) and without increasing completed nominal depth in fixed-time searches.

### Question 6: Does the model improve tactical search or only quiet positional ordering?
**Empirical Answer:** **It does not improve tactical search; it introduces tactical risk.**  
In the $86\%$ of positions where classical ordering and neural ordering disagreed on the top-ranked move, classical ordering found the true alpha-beta PV move **16 times more frequently** than the neural policy ($74.4\%$ vs $4.7\%$). The neural policy's low standalone accuracy ($14\% - 16\%$ Top-1) makes it an inferior tactical oracle compared to shallow alpha-beta search.

### Question 7: Does any improvement survive fixed-time evaluation?
**Empirical Answer:** **No.**  
Across 50 held-out positions at 50ms and 100ms, completed nominal depth ($5.30$ plies in C1 vs $5.32 - 5.38$ plies in candidates) and effective throughput show no statistically significant improvement.

### Question 8: Is the neural policy architecture worth further development?
**Empirical Answer:** **No, not as a standalone move-ordering heuristic within alpha-beta.**  
Alpha-beta search relies on ultra-cheap node evaluations ($<1\ \mu\text{s}$), whereas a policy forward pass on CPU requires $\approx 280\ \mu\text{s}$. Without a value network, standalone policy ordering cannot overcome the computational overhead and structural dominance of classical search heuristics.

---

## 2. Final Milestone Classification

In strict adherence to the four predefined classification categories:

- [ ] **Category A — Neural benefit demonstrated:** Meaningful, reproducible improvement attributable to learned policy information.
- [ ] **Category B — Neural integration functional, benefit unproven:** Valid neural prototype, but no convincing evidence of improvement.
- [x] **Category C — Neural policy ineffective:** Evidence indicates that this architecture or integration strategy is not competitive under the evaluated conditions.
- [ ] **Category D — Evidence invalid:** Integrity, correctness or reproducibility failures prevent scientific interpretation.

### Formal Classification:
$$\mathbf{CATEGORY\ C\ —\ NEURAL\ POLICY\ INEFFECTIVE}$$

**Rationale:** The evidence collected across Phase 0 through Phase 4 conclusively proves that standalone neural policy move ordering within a classical alpha-beta framework produces zero learned information benefit over randomized controls, is superseded $>80\%$ of the time by the classical transposition table, and is uncompetitive on CPU under tournament time controls.

---

## 3. Mandatory Next-Direction Recommendation

In accordance with Section 7 of the Milestone Specification:

- [ ] **Direction P:** Improve the neural policy architecture or training objective.
- [x] **Direction V:** Investigate learned value evaluation or hybrid evaluation.
- [ ] **Direction H:** Develop a hybrid policy-value search approach.

### Chosen Direction:
$$\mathbf{DIRECTION\ V\ —\ LEARNED\ VALUE\ EVALUATION\ (NNUE)}$$

### Technical & Scientific Justification for Direction V:
1. **The Structural Fallacy of Standalone Policy in Alpha-Beta:** Alpha-beta search is inherently an evaluation-driven algorithm. Move ordering only exists to establish early bounds so that the static evaluation function can prune subtrees. MicroPolicyNet predicted human master moves, not alpha-beta minimax values.
2. **The Success of NNUE:** In contemporary computer chess, the decisive breakthrough was NNUE (Efficiently Updatable Neural Networks). NNUE replaces the handcrafted static evaluation function with a quantized neural network that evaluates positions in $\approx 20 - 50\ \text{ns}$ using SIMD (AVX2/AVX-512).
3. **Synergy with Classical Search:** An NNUE value network directly improves the quality of leaf evaluations without disrupting the highly tuned, nanosecond-fast classical move-ordering pipeline (TT, MVV/LVA, killers, history heuristic).
4. **Conclusion:** Project Janus should immediately pivot to **v0.60: NNUE Architecture Design, Dataset Synthesis & Quantized Native Evaluation Core**.
