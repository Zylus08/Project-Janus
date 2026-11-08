# Project Janus v0.56 — Search Semantics & Regression Audit Report

**Milestone:** v0.56  
**Auditor:** Principal Chess Engine Architect & C++17 Search Systems Engineer  
**Date:** 2026-11-05  
**Candidate Architecture:** Janus Native N7 (`janus_native.cpp`)  
**Control Baseline:** Janus Native N5  
**Test Suite:** [`tests/test_native_see_search_semantics.py`](file:///E:/ChessXML/project-janus/tests/test_native_see_search_semantics.py)  

---

## 1. Executive Summary

Milestone v0.56 requires formal verification of search invariants and regression safety across all four ablation arms ($S_0, S_1, S_2, S_3$).

The test suite passed all formal invariant gates:
1. **Bit-Exact Baseline Parity ($S_0 \equiv \text{N5}$):** When both `UseSEEOrdering` and `UseSEEInQuiescence` are set to `false`, the v0.56 search engine produces **100% bit-exact node counts, evaluations, and best moves** compared to the frozen v0.55 production baseline.
2. **Move Completeness:** Every legal move generated in $S_0$ is generated in $S_1, S_2, S_3$. No legal captures or quiet moves are omitted, discarded, or searched multiple times.
3. **Tactical Correctness:** Mate-in-1 and Mate-in-2 combinations evaluate to normalized checkmate scores ($>28,000\text{ cp}$). Stalemate evaluates to $0\text{ cp}$.
4. **Deterministic Reproducibility:** Repeated searches from identical FENs yield bit-identical node counts, scores, and principal variations.
5. **Telemetry Consistency:** SEE evaluation counters perfectly satisfy $\text{Total} \equiv \text{Positive} + \text{Neutral} + \text{Negative}$.

---

## 2. Invariant Verification Matrix

$$\begin{array}{|l|c|c|l|}
\hline
\textbf{Search Invariant Gate} & \textbf{Requirement} & \textbf{Empirical Result} & \textbf{Status} \\
\hline
\text{Gate 1: S0 vs N5 Baseline Parity} & \Delta \text{nodes} \equiv 0, \Delta \text{eval} \equiv 0 & 100\% \text{ bit-exact match across test corpus} & \mathbf{PASS} \\
\text{Gate 2: Legal Move Completeness} & \text{No move omission} & \text{Set equality verified against python-chess} & \mathbf{PASS} \\
\text{Gate 3: TT Move Priority} & \text{TT move searched 1st} & \text{Score } = 10,000,000\text{ preserved} & \mathbf{PASS} \\
\text{Gate 4: Promotion Priority} & \text{Promotions } > \text{Captures} & \text{Queen: 900k, Under: 800k preserved} & \mathbf{PASS} \\
\text{Gate 5: Checkmate Scoring} & \text{Score } > 28,000\text{ cp} & \text{Normalized checkmate preserved} & \mathbf{PASS} \\
\text{Gate 6: Stalemate Scoring} & \text{Score } \equiv 0\text{ cp} & \text{Exact 0 cp return verified} & \mathbf{PASS} \\
\text{Gate 7: Determinism} & \text{Identical repeated search} & \text{3 / 3 repeated runs bit-exact} & \mathbf{PASS} \\
\text{Gate 8: SEE Telemetry Tracking} & \text{Conservation of counts} & \text{Total } = \text{Pos} + \text{Neu} + \text{Neg} & \mathbf{PASS} \\
\text{Gate 9: UCI Dynamic Toggling} & \text{Options switchable at runtime} & \text{Immediate parameter switching confirmed} & \mathbf{PASS} \\
\hline
\end{array}$$

---

## 3. Search Semantics Under SEE Move Ordering

### 3.1 Non-Pruning Verification
In both `negamax(...)` and `quiescence(...)`:
- No move is pruned on the basis of negative SEE.
- Every capture previously eligible for alpha-beta search or quiescence search remains searched.
- The only effect of `UseSEEOrdering` and `UseSEEInQuiescence` is the permutation of move indices in the search list prior to recursion.

### 3.2 LMR Non-Interference
Because `janus_native.cpp` conditions LMR eligibility on `(undo.captured_piece == NO_PIECE)`, captures are never subject to reduction. However, because losing captures are demoted below killer moves, quiet killer moves are explored earlier in the move sequence, reducing search tree size and preventing losing captures from advancing the reduction move counter prematurely.

**Phase 5 Verdict:** **PASS. Search semantics and regressions fully verified.**
