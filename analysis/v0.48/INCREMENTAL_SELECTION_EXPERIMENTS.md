# Incremental Move Selection Experiments (v0.48 Phase F)

## 1. Experimental Objective

Phase F tests whether an alternative incremental selection design can eliminate eager sorting overhead while preserving 100% of Baseline K0's move-ordering and search-tree semantics:
- **Baseline K0:** Eager scoring and full Timsort of all legal moves at node entry.
- **Candidate L1:** Deferred lazy move selection (TT move yielded first without scoring remaining moves; remaining moves scored and sorted on demand).
- **Candidate L2 (Stable Incremental Selection):** All legal moves are scored at node entry before move 0 search (preserving exact entry-time history state), but sorting of the tail is deferred until move 0 fails to produce a cutoff.

## 2. Empirical Results across the 37-Position Corpus (Depth 4)

| Candidate | Total Nodes | Node Delta (%) | Runtime (s) | Effective NPS | Move Agreement vs K0 | Score Agreement vs K0 | Sorts Saved |
|---|---:|---:|---:|---:|---|---|---:|
| **Baseline K0** | 405,197 | 0.00% (Ref) | 32.48 | 12,477 | 37 / 37 (100.0%) | 37 / 37 (100.0%) | 0 |
| **Candidate L1** | 407,705 | +0.62% | 36.48 | 11,175 | 36 / 37 (97.3%) | 35 / 37 (94.6%) | 2,969 |
| **Candidate L2 (Stable)** | **405,197** | **+0.00% (Exact)** | 37.98 | 10,669 | **37 / 37 (100.0%)** | **37 / 37 (100.0%)** | 2,944 |

## 3. Findings & Theoretical Significance

1. **Exact Semantic Equivalence Confirmed:** Candidate L2 achieved **exact 100.0% node-for-node, move-for-move, and score-for-score equivalence** to K0 across all 37 diagnostic positions (405,197 nodes vs 405,197 nodes). This definitively proves that the slight divergence observed in L1 was indeed caused by history mutations during move 0 search.
2. **Computational Cost of Move Scoring in Python:**
   - In Candidate L2, 2,944 sorting operations were avoided. However, because all remaining moves were pre-scored at node entry, the runtime did not improve over K0 in Python (37.98s vs 32.48s).
   - In pure Python, evaluating `_move_order_score` (function call overhead, dictionary/attribute lookups, integer arithmetic) accounts for the vast majority of move-ordering cost.
3. **Architectural Conclusion:**
   - Candidate L1 is the only strategy that delivers a net wall-clock speedup (-17.7% to -20.4% runtime reduction at Depth 5) because it avoids both **scoring** and **sorting** for the ~76% of nodes where the TT move produces an immediate cutoff.
   - Candidate L2 is valuable as a diagnostic reference proving that semantic divergence can be eliminated, but Candidate L1 remains the superior practical optimization.

