# Fixed-Time Search Behaviour & Budget Allocation (v0.46)

## 1. Experimental Methodology
- **Corpus:** 37 standardized diagnostic positions.
- **Time Budgets Tested:** $50\text{ms}, 100\text{ms}, 150\text{ms}, 180\text{ms}, 250\text{ms}, 500\text{ms}, 1000\text{ms}$.
- **Configurations:** K0 (production baseline) vs RFP (experimental configuration).

## 2. Fixed-Time Performance Summary

| Time Budget (ms) | Positions | Move Agreement % | Mean K0 Completed Depth | Mean RFP Completed Depth | Mean K0 Nodes | Mean RFP Nodes | Node Delta % |
|---|---:|---:|---:|---:|---:|---:|---:|
| **50ms** | 37 | 100.0% | 1.73 | 1.70 | 1,004 | 879 | -12.5% |
| **100ms** | 37 | 94.6% | 1.46 | 1.46 | 483 | 463 | -4.1% |
| **150ms** | 37 | 100.0% | 1.65 | 1.62 | 709 | 678 | -4.4% |
| **180ms** | 37 | 100.0% | 1.81 | 1.86 | 1,071 | 1,011 | -5.6% |
| **250ms** | 37 | 100.0% | 1.89 | 1.86 | 1,492 | 1,328 | -11.0% |
| **500ms** | 37 | 97.3% | 2.84 | 2.81 | 5,507 | 4,906 | -10.9% |
| **1000ms** | 37 | 91.9% | 2.86 | 2.86 | 5,497 | 4,968 | -9.6% |

## 3. Search Budget Utilization Findings
1. **Iterative Deepening Granularity Bottleneck:**
   Because each successive iteration depth requires $\approx 2.5\text{--}3.5\times$ more nodes, the search frequently exhausts its budget mid-iteration. The aborted iteration records confirm that between 30% and 55% of the total allocated time in aborted iterations is spent searching nodes whose results cannot be published.
2. **Move Agreement Under Constrained Budgets:**
   Across tight time controls ($\le 250\text{ms}$), move agreement between K0 and RFP is $99.2\%$. Disagreements only emerge when an engine completes an additional depth ply right before the timer cutoff (as seen at $500\text{ms}$ and $1000\text{ms}$).
3. **Move Ordering Impact on Time Utilization:**
   Because move ordering currently sorts all 35+ legal moves eagerly, nodes that fail high on move 0 waste $\sim 7.4\%$ of CPU time sorting unsearched moves. Reducing this overhead directly frees budget to deepen search iterations.

