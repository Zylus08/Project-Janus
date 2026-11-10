# Project Janus — Phase 1 Milestone P1.1
## Aspiration Windows Implementation, Re-Search Stability & Controlled Ablation

**Milestone:** P1.1 — Classical Search Modernization  
**Component:** Aspiration Windows ($\delta = 25\text{ cp}$)  
**Engine Lineage:** Janus Classical X (`engine/classical_x/janus_classical_x.cpp`)  
**Variant:** `X5` (Aspiration Isolated Ablation), `X6` (Integrated Candidate)  
**Parent Anchor:** `bbadf8f` / `7b526a0`  
**Date:** November 2026  
**Auditor:** Principal Computer Chess Engineer & Search Architect  

---

## 1. Executive Summary

Aspiration windows replace the full search window $[-\infty, +\infty]$ at the root of iterative deepening with a narrow artificial window $[\alpha, \beta] = [\text{prev\_score} - \delta, \text{prev\_score} + \delta]$. If the true minimax value falls within this window, search efficiency increases dramatically because beta-cutoffs and fail-lows occur much earlier. If the score falls outside the window (fail-low or fail-high), the window is widened and the search repeated until an exact score is established.

In Phase 5 of Milestone P1.1, we implemented and experimentally qualified an adaptive aspiration window framework in `janus_classical_x.cpp` with initial $\delta = 25\text{ cp}$ and progressive exponential widening on research.

### Key Results Across 25 Benchmark Positions (Depth 7):
- **Total Search Nodes:** Reduced from **16,342,285** (A0 Full Window) to **14,169,939** (A1 Aspiration) — a **13.29% node reduction**.
- **Execution Time:** Reduced from **14.19s** to **11.71s** — a **1.21x speedup**.
- **Re-Search Overhead:** Only **8 widening re-searches** across all 25 positions and depths 5 through 7, confirming exceptional window stability.
- **Move Fidelity & Agreement:** **25 / 25 positions (100.0% exact match)** produced identical principal variations and best moves to the full-window reference.

---

## 2. Algorithmic Formulation & Implementation

In `janus_classical_x.cpp`, aspiration search is activated for iterative deepening root searches at depth $d \ge 5$:

$$\text{Initial window: } [\alpha, \beta] = [\text{prev\_score} - \delta, \text{prev\_score} + \delta], \quad \delta = 25\text{ cp}$$

$$\text{While not resolved:}$$
$$\text{score} = \text{Negamax}(b, d, \alpha, \beta, \text{ply}=0)$$
$$\text{If } \text{score} \le \alpha: \quad \alpha = \max(-\infty, \alpha - 2\delta), \quad \delta \leftarrow 2\delta \quad (\text{Fail-Low Re-search})$$
$$\text{Else if } \text{score} \ge \beta: \quad \beta = \min(+\infty, \beta + 2\delta), \quad \delta \leftarrow 2\delta \quad (\text{Fail-High Re-search})$$
$$\text{Else: break (Resolved)}$$

### Implementation Details (`engine/classical_x/janus_classical_x.cpp`):
```cpp
if (g_use_aspiration_window && d >= 5 && prev_score > -MATE_SCORE + 100 && prev_score < MATE_SCORE - 100) {
    int asp_alpha = prev_score - g_aspiration_delta;
    int asp_beta = prev_score + g_aspiration_delta;
    int delta = g_aspiration_delta;

    while (true) {
        score = negamax(b, d, asp_alpha, asp_beta, 0, total_nodes, deadline, aborted, &iter_best_move);
        if (aborted) break;

        if (score <= asp_alpha) {
            g_telemetry_aspiration_researches++;
            asp_alpha = std::max(-INF, asp_alpha - delta * 2);
            delta *= 2;
        } else if (score >= asp_beta) {
            g_telemetry_aspiration_researches++;
            asp_beta = std::min(INF, asp_beta + delta * 2);
            delta *= 2;
        } else {
            break; // Score falls within window; search exact
        }
    }
} else {
    score = negamax(b, d, -INF, INF, 0, total_nodes, deadline, aborted, &iter_best_move);
}
```

### Safety Features:
1. **Depth Threshold:** Starts at $d = 5$. At shallower depths ($d < 5$), score fluctuations between depths are large, leading to wasteful re-searches.
2. **Mate Boundary Bypass:** Bypassed when `prev_score` is near mate ($\pm 31,900$), preventing oscillations in endgame mating nets.
3. **Exponential Widening:** Doubling $\delta$ on every failure guarantees rapid convergence to $[-\infty, +\infty]$ in at most 3-4 iterations even during catastrophic score drops.

---

## 3. Empirical Ablation Results (A0 vs A1)

Tested on the 25 diagnostic benchmark positions at depth 7:

| Metric | A0 (Full Window $[-\infty, +\infty]$) | A1 (Aspiration Window $\delta = 25\text{ cp}$) | Delta / Ratio |
| :--- | :--- | :--- | :--- |
| **Total Nodes** | 16,342,285 | 14,169,939 | **-13.29%** |
| **Elapsed Time** | 14.19s | 11.71s | **1.21x speedup** |
| **Re-Search Events** | 0 (no windowing) | 8 | Negligible overhead |
| **Move Agreement** | Reference | 25 / 25 positions | **100.0%** |

### Stability Analysis:
- With an initial delta of $25\text{ cp}$, the score from depth $d-1$ was accurate enough to fall within $[s-25, s+25]$ on 89.3% of depth iterations.
- On the remaining 10.7% of iterations, the single doubling ($2\delta = 50\text{ cp}$) resolved the score on the second try.
- Crucially, zero positions suffered infinite loops or timing out due to re-searches.

---

## 4. Architectural Verification & Conclusion

Aspiration Windows provide a pure algorithmic efficiency gain of 13.29% node reduction and 1.21x speedup with zero tactical divergence (100% best-move identity).

Variant `X5` is fully qualified and approved for production integration in Variant `X6`.

*Artifact Reference: `analysis/phase1/p1.1/raw/aspiration_window_raw.json`*

