# Project Janus v0.53 — Principal Variation Search (PVS) Design Specification

**Milestone:** v0.53  
**Date:** 2026-11-05  
**Auditor / Search Architect:** Principal Chess Engine Search Architect  

---

## 1. Theoretical Foundation & Governing Principles

In conventional alpha-beta search, every child node is evaluated with the full window $[-\beta, -\alpha]$. 
However, under effective move ordering (where the best move is searched first with high probability), all subsequent legal sibling moves ($m_2, m_3, \dots, m_n$) are expected to fail low ($score \le \alpha$).

**Principal Variation Search (PVS)** exploits this property:
1. The first legal move ($m_1$) is searched with the full window $[-\beta, -\alpha]$ to establish the initial value of $\alpha$ and find the candidate principal variation.
2. All subsequent legal moves ($m_i, i > 1$) are searched with a **null window** (zero-width window) around $\alpha$:
   $$\text{Child Window: } [-\alpha - 1, -\alpha]$$
3. A null-window search tests a binary hypothesis: *is this move strictly better than $\alpha$?*
   - If $score \le \alpha$ (Fail-Low): The hypothesis is refuted. The move cannot improve the principal variation. The search tree is pruned exponentially faster than with a wide window.
   - If $score > \alpha$ and $score < \beta$ (Fail-High / Interior Alpha Improvement): The hypothesis is confirmed. The move is unexpectedly superior to the current best move. A full-window re-search $[-\beta, -\alpha]$ is executed at full depth to ascertain its exact value.
   - If $score \ge \beta$ (Beta Cutoff): A cutoff is established immediately.

---

## 2. PVS Window Sign Negation & Bound Invariants

In negamax, child parameters are negated and swapped:
- Full window: `child_alpha = -beta`, `child_beta = -alpha`.
- Null window around $\alpha$:
  $$\text{child\_alpha} = -\alpha - 1, \quad \text{child\_beta} = -\alpha$$
- Child returns $score_{\text{child}}$.
- Parent computes: $score = -score_{\text{child}}$.

### Bound Arithmetic Invariants:
```
If score <= alpha:
    -> Move failed low against alpha.
    -> Bound is soundly an UPPER bound.
    -> No re-search required.

If score > alpha and score < beta:
    -> Move beat alpha, establishing a candidate PV.
    -> But score was obtained with an artificial ceiling (beta' = alpha + 1).
    -> Must re-search with true beta to obtain the exact score.

If score >= beta:
    -> Move caused a beta cutoff.
    -> Bound is soundly a LOWER bound.
    -> Subtree loop breaks immediately.
```

---

## 3. Interaction Between PVS and LMR (3-Tier Re-Search Hierarchy)

When both PVS (`UsePVS=true`) and LMR (`UseLMR=true`) are active, search traversal for legal child move $m$ at nominal depth $d$ obeys the following hierarchy:

```
                                  Legal Child Move m
                                         |
                                         v
                         Is moves_searched == 1 (PV Move)?
                               /                    \
                            Yes                      No
                            /                          \
              Search Full Nominal Depth                 Is move eligible for LMR?
               Window: [-beta, -alpha]                 /                         \
                                                    Yes                           No
                                                    /                               \
                                        Probe at Reduced Depth            Probe at Full Nominal Depth
                                        Window: [-alpha-1, -alpha]         Window: [-alpha-1, -alpha]
                                                   |                                    |
                                          score > alpha?                       score > alpha && score < beta?
                                            /        \                                 /             \
                                          Yes         No                             Yes              No
                                          /            \                             /                 \
                             Stage 2: Full Depth    Fail Low! (Pruned)    PVS Re-Search: Full Depth   Fail Low! (Pruned)
                          Window: [-alpha-1, -alpha]                       Window: [-beta, -alpha]
                                       |
                              score > alpha && score < beta?
                                 /                  \
                               Yes                   No
                               /                      \
                    Stage 3: Full Depth          Fail Low! (Pruned)
                  Window: [-beta, -alpha]
```

### Exact Code Implementation:
```cpp
int child_depth = depth - 1;
int score = 0;
uint16_t child_best = 0;

if (moves_searched == 1 || !g_use_pvs) {
    // PV Move: Search with full window
    score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
    g_pvs_full_window_searches++;
} else {
    // Non-PV Moves: Search with null window [-alpha - 1, -alpha]
    if (is_lmr_eligible) {
        g_lmr_eligible_moves++;
        int reduction = g_lmr_base_reduction;
        int reduced_depth = std::max(1, child_depth - reduction);
        g_lmr_reduced_moves++;
        g_pvs_null_window_searches++;

        // Stage 1: Reduced Depth Null-Window Probe
        score = -negamax(b, reduced_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);

        // Stage 2: If reduced probe beat alpha, re-search at full nominal depth with null window
        if (score > alpha && !aborted) {
            g_lmr_researches++;
            g_pvs_null_window_searches++;
            score = -negamax(b, child_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
        }
    } else {
        // Non-LMR Move: Full depth null-window probe
        g_pvs_null_window_searches++;
        score = -negamax(b, child_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
    }

    // Stage 3: PVS Re-Search
    // If the null-window search returned a score inside (alpha, beta), re-search with full window [-beta, -alpha]
    if (score > alpha && score < beta && !aborted) {
        g_pvs_researches++;
        g_pvs_full_window_searches++;
        score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
    }
}
```

---

## 4. Transposition Table Bound Invariants

Null-window searches produce sharper bound classification:
- If `best_score <= orig_alpha`: The node failed low. Recorded as `TT_UPPER` bound.
- If `best_score >= beta`: The node failed high. Recorded as `TT_LOWER` bound.
- If `best_score > orig_alpha && best_score < beta`: The score was verified by a full-window search. Recorded as `TT_EXACT` bound.

Mate scores are normalized with `score_to_tt(score, ply)` and clamped against transposition table storage limits.

---

## 5. UCI Protocol Configuration & Telemetry

The native engine supports the following runtime UCI options:
```
option name UsePVS type check default false
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
```

- When `UsePVS=false` (default during qualification), the engine executes the exact v0.52 N3 search.
- When `UsePVS=true`, the engine activates null-window probing and PVS re-search logic.
- Dedicated telemetry counters track full-window, null-window, PVS re-searches, and cutoffs.

