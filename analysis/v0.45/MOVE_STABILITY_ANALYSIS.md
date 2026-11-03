# Move Stability & Decision Quality Analysis — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Status:** COMPLETE

---

## 1. Executive Summary

A core question in search optimization is whether pruning heuristics improve, degrade, or leave unchanged the stability and objective chess quality of selected moves.

Using the paired fixed-depth ladder data (depths 2 to 5), the fixed-time budget ladder data, and an external reference oracle (Stockfish 19 at depth 12), we evaluated move stability and decision quality across all 37 positions in the diagnostic corpus.

---

## 2. Iteration Move Volatility Across Depths

In iterative deepening, a move flip occurs when the best move changes between iteration $d$ and iteration $d+1$:

| Transition | Total Opportunities | K0 Move Flips | RFP Move Flips | Flip Concordance |
|---|---:|---:|---:|---:|
| **Depth 2 $\to$ 3** | 37 | 10 (27.0%) | 10 (27.0%) | 100% |
| **Depth 3 $\to$ 4** | 37 | 14 (37.8%) | 14 (37.8%) | 100% |
| **Depth 4 $\to$ 5** | 37 | 9 (24.3%) | 9 (24.3%) | 100% |
| **TOTAL (All Transitions)** | **111** | **33 (29.7%)** | **33 (29.7%)** | **100%** |

### Key Insight:
- In nearly 30% of all search depth transitions, Janus changes its chosen move as nominal depth increases.
- Move volatility is **100% identical** between K0 and RFP.
- This directly explains why an interrupted iteration creates a move divergence: if one engine completes depth 3 while the other engine is forced to fall back to depth 2, there is a $\sim 27\%$ probability that they will play different moves simply due to the iteration depth transition!

---

## 3. Decision Quality Relative to Stockfish 19 (Depth 12)

At the actual match time allocation ($180\text{ ms}$):
- **Stockfish Agreement Rate (K0):** $8 / 37$ (**$21.6\%$**)
- **Stockfish Agreement Rate (RFP):** $8 / 37$ (**$21.6\%$**)
- **Critical Disagreements ($\ge 100\text{ cp}$ blunders):** Zero observed differences between K0 and RFP.

Under realistic fixed-time budgets, RFP's marginal search efficiency does not translate into measurably superior decisions relative to the external oracle. Decision quality remains on par with baseline K0.

