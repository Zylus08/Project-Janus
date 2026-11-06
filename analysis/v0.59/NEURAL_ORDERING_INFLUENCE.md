# Project Janus v0.59 — Neural Move-Ordering Influence & Root Overrides

**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Team & Independent Scientific Auditor  
**Experiment:** Phase 1 — Root Ordering Telemetry, Disagreement Resolution & Override Analysis  
**Corpus:** 50 Phase-Stratified Validation Positions (Development Set)  
**Evaluated Depths:** Nominal Iterative Deepening Depths 4, 5, and 6

---

## 1. Executive Summary

To determine the causal mechanism behind the neutral result in v0.58 ($+1.7$ Elo, $p = 0.9020$), search move ordering was instrumented at the root node (`ply == 0`) across 50 validation positions at depths 4, 5, and 6.

### Key Empirical Findings:
1. **The TT Override Bottleneck:** In iterative deepening at depths $\ge 4$, the neural policy's top recommendation is overridden **80.0% of the time at Depth 4, and 86.0% of the time at Depths 5 and 6**. In **100.0% of these override cases**, the overriding move is the transposition table (`tt_move`) preserved from iteration $d-1$ ($10,000,000$ score tier).
2. **Move Ordering Inversion Mechanics:** The neural policy reorders **$85.3\% - 86.7\%$** of quiet root moves relative to classical history ordering, but because its maximum score ($70,000$) is strictly lower than killer moves ($80,000 / 90,000$), captures ($100,000+$), promotions ($800,000+$), and the TT move ($10,000,000$), it **never** alters the first-searched move unless its recommendation happens to coincide with the TT move.
3. **Disagreement Resolution favors Classical Ordering by 16:1:** When classical ordering and the neural policy disagree on the top-ranked move ($86\%$ of positions at Depth 6):
   - The classical top move becomes the eventual principal variation (PV) move in **$74.4\%$** of cases ($32/43$).
   - The neural policy top move becomes the eventual PV move in only **$4.7\%$** of cases ($2/43$).
   - Neither move becomes the PV move in **$20.9\%$** of cases ($9/43$).
4. **Search Tree Invariance:** Total tree size differs from classical baseline C1 by $-0.49\%$ at D4, $-0.96\%$ at D5, and $+1.20\%$ at D6. Tree-wide first-move beta-cutoff rate remains invariant within $\pm 0.05\%$ ($83.78\%$ in C1 vs $83.83\%$ in N8-A at D6).
5. **Conclusion:** N8-A produced a neutral tournament result in v0.58 not because neural move ordering was failing gracefully, but because **classical search heuristics (specifically iterative-deepening TT persistence) completely dominate the search tree, rendering the neural policy functionally inert at the root**.

---

## 2. Experimental Methodology & Instrumentation

### 2.1 Instrumentation Architecture
Every legal root move $m_i \in [0, N-1]$ was captured with:
- $S_{\text{class}}(m_i)$: Classical move-ordering score (captures, killers, history, TT).
- $R_{\text{class}}(m_i) \in [1, N]$: Rank in pure classical ordering.
- $\pi(m_i) \in [0, 1]$: MicroPolicyNet softmax probability.
- $S_{\text{neural}}(m_i) \in [20000, 70000]$: Assigned neural ordering score.
- $R_{\text{neural}}(m_i) \in [1, N]$: Rank in neural policy recommendation.
- $R_{\text{search}}(m_i) \in [1, N]$: Actual search order index in alpha-beta.
- Eventual PV move $m_{\text{PV}}$ established at nominal search termination.

### 2.2 Validation Corpus (50 Positions)
The development validation corpus comprises 50 positions stratified across:
- **Opening:** 31 positions (including starting position and diverse master tabiyas).
- **Tactical:** 18 positions (pin exploitation, forced mates, skewer tactics).
- **Middlegame:** 1 position.
- Root move count: Mean $29.68$ moves (Median $31.0$, Min $5$, Max $46$).

---

## 3. Empirical Results Across Depths 4, 5, and 6

### 3.1 Move Ranking Correlation & Reordering Scope
| Nominal Depth | Mean Spearman $r_s$ | Std Dev $r_s$ | Root Moves Reordered |
|---|---|---|---|
| **Depth 4** | $+0.3298$ | $0.2941$ | $86.7\%$ |
| **Depth 5** | $+0.3243$ | $0.2897$ | $86.0\%$ |
| **Depth 6** | $+0.3659$ | $0.3071$ | $85.3\%$ |

The rank correlation between classical ordering and MicroPolicyNet is weak-to-moderate ($r_s \approx +0.33$ to $+0.37$). The neural policy aggressively rearranges quiet moves ($>85\%$ of moves experience priority changes).

---

### 3.2 Top-1 Recommendation Agreement & Override Breakdown
| Nominal Depth | Neural Top == Classical Top | Neural Top Searched First | Overridden by Classical Search | Override Reason |
|---|---|---|---|---|
| **Depth 4** | 10 / 50 (20.0%) | 10 / 50 (20.0%) | **40 / 50 (80.0%)** | 40 `tt_move` (100.0%) |
| **Depth 5** | 7 / 50 (14.0%) | 7 / 50 (14.0%) | **43 / 50 (86.0%)** | 43 `tt_move` (100.0%) |
| **Depth 6** | 7 / 50 (14.0%) | 7 / 50 (14.0%) | **43 / 50 (86.0%)** | 43 `tt_move` (100.0%) |

**Core Finding:** In every single position where the neural policy top recommendation disagreed with classical ordering, the neural move was blocked from being searched first by the transposition-table move (`tt_move`) generated during iteration $d-1$.

```
Search Order Tier Hierarchy:
[Tier 1] Transposition Table Move   10,000,000  <-- ALWAYS SEARCHED FIRST
[Tier 2] Queen Promotion              900,000
[Tier 3] Underpromotion               800,000
[Tier 4] MVV/LVA Captures             100,000 - 100,050
[Tier 5] Killer Move 1                 90,000
[Tier 6] Killer Move 2                 80,000
[Tier 7] Neural Policy Moves           20,000 - 70,000  <-- CAPPED BELOW KILLERS
[Tier 8] Classical History Moves        1 - 70,000
```

---

### 3.3 Disagreement Resolution: Classical vs Neural Accuracy
When the neural policy's top recommendation differed from the classical top recommendation:

| Nominal Depth | Disagreements ($N_{\text{disagree}}$) | Eventual PV = Classical Top | Eventual PV = Neural Top | Neither Matched PV | Classical Advantage Ratio |
|---|---|---|---|---|---|
| **Depth 4** | 40 / 50 | 27 (67.5%) | 2 (5.0%) | 11 (27.5%) | **13.5 : 1** |
| **Depth 5** | 43 / 50 | 33 (76.7%) | 3 (7.0%) | 7 (16.3%) | **11.0 : 1** |
| **Depth 6** | 43 / 50 | 32 (74.4%) | 2 (4.7%) | 9 (20.9%) | **16.0 : 1** |

When the models disagree, the classical heuristic (anchored by the previous iteration's PV move) is **11 to 16 times more likely** to find the true best move than MicroPolicyNet.

---

### 3.4 Eventual PV Move Prediction Accuracy
Overall accuracy of heuristics predicting the final best move across all 50 positions:

| Nominal Depth | Classical Top-1 Accuracy | Neural Top-1 Accuracy | Neural Top-3 Accuracy |
|---|---|---|---|
| **Depth 4** | 32 / 50 (**64.0%**) | 7 / 50 (**14.0%**) | 19 / 50 (**38.0%**) |
| **Depth 5** | 37 / 50 (**74.0%**) | 7 / 50 (**14.0%**) | 20 / 50 (**40.0%**) |
| **Depth 6** | 38 / 50 (**76.0%**) | 8 / 50 (**16.0%**) | 21 / 50 (**42.0%**) |

MicroPolicyNet achieves only $14\% - 16\%$ Top-1 accuracy in predicting the alpha-beta search's chosen move, compared to $64\% - 76\%$ for classical ordering.

---

### 3.5 Computational Efficiency & Search Tree Comparison
| Nominal Depth | Metric | Baseline C1 | Candidate N8-A | Relative Difference |
|---|---|---|---|---|
| **Depth 4** | Total Nodes | 602,172 | 599,233 | **$-0.49\%$** |
| | First-Move Cutoff Rate | $81.09\%$ | $80.96\%$ | $-0.13\text{ pp}$ |
| | Neural Overhead | 0 calls | 50 calls ($14.50\text{ ms}$) | $290.1\ \mu\text{s/call}$ |
| **Depth 5** | Total Nodes | 1,355,639 | 1,342,657 | **$-0.96\%$** |
| | First-Move Cutoff Rate | $82.21\%$ | $82.23\%$ | $+0.02\text{ pp}$ |
| | Neural Overhead | 0 calls | 100 calls ($27.59\text{ ms}$) | $275.9\ \mu\text{s/call}$ |
| **Depth 6** | Total Nodes | 5,431,472 | 5,496,457 | **$+1.20\%$** |
| | First-Move Cutoff Rate | $83.78\%$ | $83.83\%$ | $+0.05\text{ pp}$ |
| | Neural Overhead | 0 calls | 150 calls ($42.88\text{ ms}$) | $285.8\ \mu\text{s/call}$ |

---

## 4. Synthesis & Root Cause Analysis

Why did v0.58 yield $+1.7$ Elo ($p = 0.9020$)?
1. **Root Gating Ineffectiveness:** In N8-A, policy ordering is applied strictly at `ply == 0`. At `ply == 0`, the TT move from iteration $d-1$ is searched first in $>85\%$ of positions. The neural policy only reorders quiet moves that fail low against alpha.
2. **Subtree Absence:** For all child nodes (`ply >= 1`), `MaxPly = 0` disabled neural ordering completely. More than $99.99\%$ of tree nodes were ordered exclusively by classical heuristics.
3. **Low Standalone Accuracy:** With a Top-1 accuracy of only $\approx 16\%$, the policy network is significantly less reliable than classical alpha-beta iterative deepening ($74\%-76\%$). If neural scores were allowed to override the TT move, playing strength would degrade sharply.

Phase 1 establishes that learned policy ordering at the root node has almost zero causal influence on tree exploration. Phase 2 will isolate whether learned chess information outperforms randomized control orderings.

