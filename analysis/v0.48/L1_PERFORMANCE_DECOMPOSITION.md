# L1 Performance Decomposition & TT Opportunity Analysis (v0.48 Phase B)

## 1. Executive Summary

Phase B isolates the mechanisms underlying Candidate L1's runtime performance improvements over Baseline K0. Across 37 diagnostic positions evaluated from Depth 2 through Depth 5, Candidate L1 consistently yields substantial runtime and ordering overhead reductions with minimal node count variance.

## 2. Empirical Performance Metrics Across Fixed Depths

| Metric | Depth 2 | Depth 3 | Depth 4 | Depth 5 |
|---|---:|---:|---:|---:|
| **K0 Wall-Clock Runtime** | 2.11 s | 13.10 s | 32.71 s | 102.16 s |
| **L1 Wall-Clock Runtime** | 1.63 s | 11.09 s | 29.82 s | 84.10 s |
| **Runtime Delta (%)** | **-22.78%** | **-15.39%** | **-8.82%** | **-17.68%** |
| **K0 Nodes** | 25,347 | 182,087 | 405,197 | 1,251,786 |
| **L1 Nodes** | 25,347 | 180,924 | 407,705 | 1,252,292 |
| **Node Delta (%)** | **+0.00%** | -0.64% | +0.62% | **+0.04%** |
| **K0 Ordering Time** | 0.14 s | 0.76 s | 2.54 s | 7.11 s |
| **L1 Ordering Time** | 0.10 s | 0.48 s | 2.18 s | 4.91 s |
| **Ordering Time Delta (%)** | **-28.08%** | **-37.02%** | **-14.08%** | **-30.87%** |
| **1st-Move Cutoff Rate (K0)** | 68.6% | 70.3% | 81.1% | 75.8% |
| **1st-Move Cutoff Rate (L1)** | 68.6% | 70.5% | 80.8% | 76.0% |
| **TT Move Cutoffs (L1)** | 1 | 1,491 | 2,970 | 14,521 |
| **L1 Lazy Sorts Saved** | 1 | 1,491 | 2,969 | **14,510** |

## 3. TT Move Opportunity & Cutoff Attribution

At Depth 5 across the 37 positions:
1. **Total Beta Cutoffs:** 67,778 cutoffs.
2. **First-Move Cutoffs:** 51,530 cutoffs (76.03% of all beta cutoffs).
3. **TT Move Immediate Cutoffs:** 14,521 cutoffs.
4. **TT Cutoff Proportion:** In cold-TT fixed-depth search, TT moves account for **21.42% of all beta cutoffs** and **28.18% of first-move cutoffs**.
5. **Sorts Avoided:** At every node where the TT move produced an immediate cutoff, the full move-list scoring and sorting was completely bypassed. At depth 5, **14,510 full sorts** were avoided.
6. **Move 0 Cutoffs on Non-TT Moves:** In the remaining first-move cutoffs (~37,000 cutoffs), the cutoff occurred on the top-ranked capture or killer move after a full sort was executed.

## 4. Runtime Breakdown

- **Move Scoring & Sorting Overhead:** In K0, eager sorting consumed 7.11s at Depth 5. Under L1, deferring sorts until after TT evaluation reduced ordering time to 4.91s (-30.87% reduction).
- **Secondary Savings:** Bypassing eager sorting also avoids allocating sorted move list references and reduces garbage collection pressure during tree recursion.

