# Project Janus v0.55 — Factorial Interaction Report: PVS × Move Ordering

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Lead Architect & Statistician:** Principal Chess Engine Research Architect & Systems Engineer  
**Experimental Design:** $2 \times 2$ Factorial Search Interaction Model  
**Configurations Evaluated:**
- $F_{00}$: `UseKiller=false`, `UseHistory=false`, `UsePVS=false` (Historical N3)
- $F_{01}$: `UseKiller=false`, `UseHistory=false`, `UsePVS=true`  (Historical N4)
- $F_{10}$: `UseKiller=true`,  `UseHistory=true`,  `UsePVS=false` (Production N5)
- $F_{11}$: `UseKiller=true`,  `UseHistory=true`,  `UsePVS=true`  (Candidate N6)

---

## 1. Executive Summary & Central Architectural Insight

Milestone v0.55 formulated and tested the central hypothesis:
> *"Does improved killer/history move ordering make Principal Variation Search more effective, converting the computational savings observed in v0.53 into a statistically demonstrable playing-strength improvement?"*

The empirical answer is **NO**:
1. **Computational Tree Pruning Confirmed:** PVS does compress the search tree on top of N5 ($-237,052$ nodes, $-4.25\%$ at Depth 6), delivering a $1.84\times$ speedup over N3 and $1.07\times$ speedup over N5.
2. **Sub-Additive Interaction Contrast:** The computational interaction contrast is **$+607,947\text{ nodes}$ ($+7.12\%$)**, proving that PVS and Move Ordering exhibit sub-additive overlap rather than super-additive synergy.
3. **Playing-Strength Neutrality:** In head-to-head match play under equal Fischer clocks (200 games, 100 pairs), Candidate N6 scored **$99.0 / 200$ ($49.50\%$, $-3.47$ Elo, $p = 0.83425$)** against Production N5. PVS does **not** convert its minor node savings into measurable playing strength.

---

## 2. Multi-Level Interaction Analysis

$$\begin{array}{|l|c|c|c|}
\hline
\textbf{Interaction Level} & \textbf{PVS w/o Ordering } (F_{01} - F_{00}) & \textbf{PVS with Ordering } (F_{11} - F_{10}) & \textbf{Interaction Contrast } (Int) \\
\hline
\textbf{1. Total Nodes (Depth 6)} & -844,999 \ (-9.89\%) & -237,052 \ (-4.25\%) & \mathbf{+607,947\text{ nodes} \ (+7.12\%)} \\
\textbf{2. Wall Time (Depth 6)} & -1.92\text{ s} \ (1.15\times) & -0.56\text{ s} \ (1.07\times) & \mathbf{+1.36\text{ s \ (Sub-additive)}} \\
\textbf{3. 1st-Move Cutoff (Depth 6)} & +0.63\% & +0.86\% & \mathbf{+0.23\%} \\
\textbf{4. LMR Researches (Depth 6)} & -104 \ (-6.89\%) & -38 \ (-7.48\%) & \mathbf{+66\text{ (Diminishing tail)}} \\
\textbf{5. Median Depth (3000ms)} & 0.0\text{ plies} & +0.5\text{ plies} & \mathbf{+0.5\text{ plies}} \\
\textbf{6. Tactical Solve Rate} & 16 / 16 \ (100.0\%) & 16 / 16 \ (100.0\%) & \mathbf{0.0\% \ (Exact parity)} \\
\textbf{7. Match Playing Strength} & -8.70\text{ Elo} \ (p = 0.566) & -3.47\text{ Elo} \ (p = 0.834) & \mathbf{\approx 0\text{ Elo \ (Neutrality)}} \\
\hline
\end{array}$$

---

## 3. Why Node Compression Did Not Produce Strength Improvement

In chess engine development, it is frequently assumed that reducing nodes automatically increases playing strength. Milestone v0.55 refutes this assumption for PVS within Janus:

### 3.1 Minimax Mathematical Equivalence
PVS is an exact minimax pruning algorithm. For any fixed depth $d$, PVS returns the exact same score and move as full-window alpha-beta (as proven in `FACTORIAL_CORRECTNESS_REPORT.md`). PVS never changes *what* move is preferred at a given depth; it only reduces the number of nodes required to prove the bound.

### 3.2 Threshold Mechanics of Iterative Deepening
In fixed-time search (e.g. Fischer 3.0s + 100ms), an engine only plays a different move if it completes an **additional full iteration** of iterative deepening.
- The average branching factor of Janus is $b \approx 3.0$ to $4.0$.
- To reach depth $d+1$, an engine requires approximately $300\%\text{ to } 400\%$ more nodes.
- PVS delivers a **$4.25\%$ to $5.29\%$ node reduction** on top of N5.
- A $4.25\%$ reduction accelerates search speed by only $1.07\times$, which is insufficient to cross the exponential threshold for an extra search iteration in the vast majority of middlegame positions ($>95\%$ of positions stop at the exact same depth as N5).

### 3.3 The Pruning Overlap with Killer/History Ordering
Prior to v0.54, quiet moves were unordered, meaning that non-PV subtrees had high branching factors. In that environment (v0.53), PVS pruned $9.89\%$ of the tree.
However, once Killer and History heuristics were introduced in v0.54:
- The first-move cutoff rate rose to $>83\%$.
- Cutoffs at move 4+ collapsed by $79.6\%$.
- The non-PV subtrees that PVS is designed to prune with null-window bounds were already pruned by killer/history cutoffs!
Therefore, PVS's marginal contribution was squeezed down to just $4.25\%$, producing no discernible tournament edge.

---

## 4. Architectural Synthesis

1. **Move Ordering is the King of Alpha-Beta Efficiency:**
   Experiment B proved that Killer + History ordering produces **$+77.71$ Elo ($p = 0.000007$)** out-of-sample. Ordering quiet moves correctly has a massive impact on playing strength because it prevents catastrophic tactical blunders across all depths.
2. **PVS is Algorithmically Sound but Strength-Neutral:**
   PVS provides elegant search-window tightness and modest tree savings without regressions, but under equal Fischer time controls, it does not alter game outcomes.
3. **Production Recommendation:**
   Retain Janus Native N5 as the frozen production default. Keep PVS integrated and configurable as a UCI option (`UsePVS=false`).
