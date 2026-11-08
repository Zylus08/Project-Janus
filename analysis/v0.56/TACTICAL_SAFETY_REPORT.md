# Project Janus v0.56 — Tactical Safety & Differential Benchmark Report

**Milestone:** v0.56  
**Auditor:** Principal Chess Engine Architect & Tactical Search Researcher  
**Date:** 2026-11-05  
**Candidate Architecture:** Janus Native N7 (`UseSEEOrdering=true, UseSEEInQuiescence=true`)  
**Control Baseline:** Janus Native N5 (`UseSEEOrdering=false, UseSEEInQuiescence=false`)  
**Corpus:** 64 Positions across 4 Stratified Suites  
**Raw Data:** [`analysis/v0.56/raw/tactical_safety_results.json`](file:///E:/ChessXML/project-janus/analysis/v0.56/raw/tactical_safety_results.json)  

---

## 1. Executive Summary & Denominator Clarity

To address the documentation discrepancy noted in Phase 0, all tactical metrics in Milestone v0.56 explicitly distinguish between:
1. **Total Scored Positions Evaluated ($N=64$):** Positions with independently defined ground truth expected moves.
2. **Solved Solutions at Depth 5 ($16/64$, $25.0\%$):** Number of positions where the search discovered the exact solution at nominal Depth 5.
3. **Baseline Solution Retention ($16/16$, $100.0\%$):** Proportion of baseline solutions retained by Candidate $S_3$ (zero regressions).
4. **Move Agreement ($64/64$, $100.0\%$):** Exact move agreement between Candidate $S_3$ and Baseline $S_0$.

$$\begin{array}{|l|c|c|c|c|c|}
\hline
\textbf{Suite Name} & \textbf{Positions} & \textbf{S0 Solved} & \textbf{S3 Solved} & \textbf{S3 vs S0 Agreement} & \textbf{S3 Node Reduction} \\
\hline
\text{Tactical Regression} & 12 & 4 & 4 & 12 / 12\text{ (100.0\%)} & -9.36\% \\
\text{Validation Suite} & 16 & 3 & 3 & 16 / 16\text{ (100.0\%)} & -9.57\% \\
\text{Independent Tactical v0.53} & 20 & 9 & 9 & 20 / 20\text{ (100.0\%)} & -12.35\% \\
\text{Capture Evaluation Corpus} & 16 & 0 & 0 & 16 / 16\text{ (100.0\%)} & -4.60\% \\
\hline
\textbf{Combined Total} & \mathbf{64} & \mathbf{16} & \mathbf{16} & \mathbf{64 / 64\text{ (100.0\%)}} & \mathbf{-9.05\%} \\
\hline
\end{array}$$

---

## 2. Invariant Verification & Tactical Preservation

### 2.1 Zero Tactical Blind Spots
A theoretical concern with capture reordering is whether placing losing captures ($\text{SEE} < 0$) below quiet killer moves might blind the engine to tactical refutations that begin with an apparent sacrifice.
- In all 64 tested benchmark positions, Candidate $S_3$ agreed **100.0%** ($64/64$) with the baseline's move choices.
- Every tactical solution found by $S_0$ ($16/16$) was found identically by $S_3$.
- Zero solutions were dropped, and zero tactical regressions occurred.

### 2.2 Tree Compression on Tactical Suites
Across the 64 positions at Depth 5:
- Baseline $S_0$ searched **1,467,965 nodes**.
- Candidate $S_3$ searched **1,335,100 nodes**.
- Net node reduction: **$-132,865\text{ nodes} \ (-9.05\%)$**.

On the `independent_tactical` suite, node reductions reached **$-12.35\%$** (392,067 vs 447,324 nodes) because demoting losing captures eliminated multiple deep branches where the engine previously searched sacrificial refutations ahead of quiet cutoff moves.

**Tactical Safety Verdict:** **FORMALLY PASSED. Zero regressions, 100% solution retention, -9.05% tree compression.**
