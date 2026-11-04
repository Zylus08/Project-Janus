# Decision-Quality Baseline (v0.46)

## 1. Experimental Methodology
- **Reference Standard:** Stockfish 19 evaluated at depth 14 on all 37 diagnostic corpus positions (`analysis/v0.46/reference/stockfish_reference_ladder.json`).
- **Reference Stability Check:**
  - $31 / 37$ positions ($83.8\%$) exhibit identical best moves between depth 12 and depth 14, confirming that the reference continuation is well-converged.
- **Engine Configurations:** Janus K0 (production baseline) and Janus RFP across nominal depths $d \in \{2, 3, 4, 5\}$.

## 2. Decision-Quality Metrics across Depths

| Engine Config | Search Depth | Agreement with SF d14 | Agreement % | Mean Evaluation Error vs SF d14 (cp) |
|---|---:|---:|---:|---:|
| **K0** | 2 | 9 / 37 | 24.3% | 54.4 cp |
| **K0** | 3 | 13 / 37 | 35.1% | 31.6 cp |
| **K0** | 4 | 15 / 37 | 40.5% | 21.6 cp |
| **K0** | 5 | 14 / 37 | 37.8% | 24.3 cp |
| **RFP** | 2 | 9 / 37 | 24.3% | 54.4 cp |
| **RFP** | 3 | 13 / 37 | 35.1% | 31.6 cp |
| **RFP** | 4 | 15 / 37 | 40.5% | 21.6 cp |
| **RFP** | 5 | 14 / 37 | 37.8% | 24.4 cp |

## 3. Key Findings

### 1. Depth Monotonicity and Plateau
- Scaling depth from $d=2 \to d=4$ yields a monotonic increase in best-move agreement ($24.3\% \to 40.5\%$) and a corresponding reduction in evaluation error ($54.4\text{ cp} \to 21.6\text{ cp}$).
- At $d=5$, agreement levels off at $37.8\%$ ($14/37$). The primary limiter of decision quality beyond depth 4 is evaluation inaccuracy and horizon effects in non-tactical lines, rather than search depth alone.

### 2. K0 vs RFP Decision Equivalence at Fixed Depth
- Across all 148 position-depth trials ($37 \times 4$), **K0 and RFP produced $0$ move disagreements** ($100\%$ move identity).
- This confirms the v0.44/v0.45 finding: RFP preserves fixed-depth decision quality completely while pruning ~9–10% of search nodes.

