# Fixed-Depth Search Efficiency Baseline (v0.46)

## 1. Experimental Protocol
- **Corpus:** 37 standardized diagnostic positions (`analysis/v0.46/corpus/diagnostic_corpus.json`), comprising 32 tactical and 5 positional middlegame and endgame positions.
- **Configurations Tested:**
  1. **K0 (Production Baseline):** `enable_rfp=False`
  2. **RFP (Experimental Configuration):** `enable_rfp=True`, `rfp_max_depth=2`, `rfp_margin_per_depth=120`
- **Evaluated Depths:** Fixed nominal depths $d \in \{2, 3, 4, 5\}$.
- **Transposition Table Isolation:** Clean instance per position search to avoid inter-position TT leakage.

## 2. Quantitative Search Efficiency Summary

| Configuration | Nominal Depth | Positions | Mean Nodes | Mean NPS | Mean Elapsed (s) | 1st Move Cutoff % | Cumulative Ordering Time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **K0** | 2 | 37 | 685.1 | 7,295 | 0.129s | 68.6% | 0.303s |
| **K0** | 3 | 37 | 4,921.3 | 8,734 | 0.750s | 70.3% | 1.627s |
| **K0** | 4 | 37 | 10,951.3 | 7,491 | 1.630s | 81.1% | 5.025s |
| **K0** | 5 | 37 | 33,832.1 | 7,313 | 5.215s | 75.8% | 14.305s |
| **RFP** | 2 | 37 | 683.5 | 13,683 | 0.079s | 68.2% | 0.194s |
| **RFP** | 3 | 37 | 4,917.2 | 17,785 | 0.526s | 70.1% | 1.112s |
| **RFP** | 4 | 37 | 9,790.2 | 13,054 | 1.238s | 75.1% | 3.091s |
| **RFP** | 5 | 37 | 30,723.6 | 14,476 | 3.259s | 71.2% | 7.937s |

## 3. Aggregate Node Count & Efficiency Differential

### Total Nodes Searched:
- **Depth 4:**
  - K0: 405,197 nodes
  - RFP: 362,238 nodes
  - **Reduction:** $-10.60\%$
- **Depth 5:**
  - K0: 1,251,786 nodes
  - RFP: 1,136,772 nodes
  - **Reduction:** $-9.19\%$

## 4. Key Observations & Inefficiencies
1. **First-Move Cutoff Ceiling:**
   First-move cutoff rates level off around $75\%\text{--}81\%$ at depths 4 and 5. In roughly $20\%\text{--}25\%$ of all cutoff nodes, the search evaluates 2 or more moves before finding a refutation.
2. **Move-Ordering Sort Overhead:**
   Cumulative time spent in `moves.sort()` at depth 5 accounts for 14.305 seconds out of ~193 seconds total search time (~7.4% of total runtime purely executing Python lambda comparison sorts).
3. **Branching Factor:**
   Effective branching factor from depth 3 to 4 is approximately $2.23$, and from depth 4 to 5 is approximately $3.09$ for K0.

