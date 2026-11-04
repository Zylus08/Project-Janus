# Project Janus v0.55 — Factorial Experimental Design: PVS × Move Ordering

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Role:** Principal Chess Engine Research Architect & Experimental Statistician  
**Repository:** `E:\ChessXML\project-janus`  
**Branch:** `v0.3-benchmark-harness`  
**Classification:** Controlled $2 \times 2$ Factorial Search Research & Replication Protocol  

---

## 1. Experimental Architecture & Factorial Matrix

Project Janus v0.55 investigates the interaction between two major search innovations developed across milestones v0.52–v0.54:
1. **Factor A (Quiet Move Ordering Intelligence):** Killer Moves + History Heuristic.
2. **Factor B (Search Window Optimization):** Principal Variation Search (PVS).

To cleanly isolate main effects, compute the interaction contrast, and establish independent replicability, a rigorous $2 \times 2$ factorial matrix is defined:

$$\begin{array}{|l|c|c|l|}
\hline
\textbf{Configuration} & \textbf{Killer + History} & \textbf{PVS} & \textbf{Engine Architecture / Historical Role} \\
\hline
\mathbf{F_{00}} & \text{false} & \text{false} & \text{Historical Janus N3 Baseline (LMR only, quiets unranked)} \\
\mathbf{F_{01}} & \text{false} & \text{true} & \text{Historical Janus N4 Baseline (LMR + PVS, quiets unranked)} \\
\mathbf{F_{10}} & \text{true} & \text{false} & \mathbf{Current \ Production \ Baseline \ N5 \ (LMR + Killer + History)} \\
\mathbf{F_{11}} & \text{true} & \text{true} & \mathbf{Experimental \ Candidate \ N6 \ (LMR + Killer + History + PVS)} \\
\hline
\end{array}$$

### 1.1 Invariant Control Constants
All four configurations share strictly identical implementations and environment constants:
- **LMR Policy:** Always active (`UseLMR=true`), minimum depth $d \ge 3$, move threshold 4, base reduction 1.
- **Evaluation Function:** Identical material, piece-square tables, and mobility terms.
- **Transposition Table:** Identical 16 MB replacement policy (Zobrist hash, depth-preferred overwrite).
- **Time Management:** Identical Fischer clock allocation and dynamic emergency thresholds.
- **Capture Ordering:** Identical MVV-LVA calculation.
- **Compilation:** Compiled from single source via MSVC `/O2 /std:c++17 /EHsc`.
- **Search-State Reset:** Identical TT and table clearing policy via `ucinewgame`.

---

## 2. Research Hypotheses & Statistical Models

### 2.1 Primary Confirmatory Hypothesis (Experiment A: N6 vs N5)
The primary question is whether enabling PVS within the qualified N5 architecture improves playing strength under equal Fischer time controls:
- **Null Hypothesis ($H_0$):** Enabling PVS confers no playing-strength advantage over N5 under equal Fischer time controls ($\mu_d \le 0$, $\text{Elo}_\Delta \le 0$).
- **Alternative Hypothesis ($H_1$):** Enabling PVS confers a statistically significant playing-strength improvement over N5 ($\mu_d > 0$, $\text{Elo}_\Delta > 0$).
- **Statistical Model:**
  $$d_i = \text{score}_{N6, i} - \text{score}_{N5, i} \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$$
  Evaluated on $N=100$ independent opening pairs (200 games) with strict color reversal.
  - Test Statistic: Student's paired $t = \frac{\bar{d}}{s_d / \sqrt{N}}$, with $df = 99$.
  - Acceptance Criterion for Promotion: Two-sided $p < 0.05$ AND non-parametric 95% bootstrap confidence interval strictly excluding zero.

### 2.2 Factorial Interaction Model (PVS × Move Ordering)
For any search metric $Y$ (e.g. total nodes, wall time, first-move cutoff rate, mean cutoff index), the factorial contrast is defined as:
$$\Delta_{\text{PVS}}(\text{No Ordering}) = Y_{F01} - Y_{F00}$$
$$\Delta_{\text{PVS}}(\text{With Ordering}) = Y_{F11} - Y_{F10}$$
$$\text{Interaction}_{A \times B} = \Delta_{\text{PVS}}(\text{With Ordering}) - \Delta_{\text{PVS}}(\text{No Ordering}) = (Y_{F11} - Y_{F10}) - (Y_{F01} - Y_{F00})$$

#### Interpretation Framework:
- **Super-Additive Synergy ($\text{Interaction} < 0$ for nodes):** If PVS prunes more effectively when quiet moves are properly ordered, the interaction is super-additive, proving that PVS requires move ordering to achieve maximum pruning.
- **Sub-Additive Overlap ($\text{Interaction} > 0$ for nodes):** If both heuristics prune the same branches from the search tree, their joint benefit exhibits diminishing returns.

### 2.3 Independent Replication Hypothesis (Experiment B: N5 vs N3)
The secondary objective is to test whether the $+29.6$ Elo advantage reported for N5 in milestone v0.54 replicates on a genuinely fresh, out-of-sample opening corpus:
- **Hypothesis:** Under identical conditions but using 100 previously unseen opening positions, $F_{10}$ (N5) maintains a positive, statistically significant advantage over $F_{00}$ (N3).
- **Independence:** The replication match must use an independent result ledger, independent PGN, and must not share any starting positions with v0.52–v0.54.

---

## 3. Four-Configuration UCI Matrix

$$\begin{array}{|l|c|c|c|c|}
\hline
\textbf{UCI Command} & \textbf{F00 (N3)} & \textbf{F01 (N4)} & \textbf{F10 (N5)} & \textbf{F11 (N6)} \\
\hline
\text{setoption name UseKillerOrdering value} & \text{false} & \text{false} & \text{true} & \text{true} \\
\text{setoption name UseHistoryOrdering value} & \text{false} & \text{false} & \text{true} & \text{true} \\
\text{setoption name UsePVS value} & \text{false} & \text{true} & \text{false} & \text{true} \\
\text{setoption name UseLMR value} & \text{true} & \text{true} & \text{true} & \text{true} \\
\hline
\end{array}$$

This design guarantees that all experiments are run on identical hardware, using identical binary codepaths, eliminating all confounding environmental variables.

