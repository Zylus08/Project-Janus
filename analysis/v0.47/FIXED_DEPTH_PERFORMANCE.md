# Fixed-Depth Performance Evaluation (v0.47 Phase F)

## 1. Objective and Corpus Overview

Phase F measures the computational overhead reduction and effective search throughput of Candidate L1 (Lazy Move Selection) across the 37-position diagnostic corpus over depths 2, 3, 4, and 5.

All 296 search evaluations (37 positions × 4 depths × 2 configurations) were executed under identical conditions with full ordering diagnostic telemetry enabled.

## 2. Comparative Efficiency by Depth

| Metric | Depth 2 | Depth 3 | Depth 4 | Depth 5 |
|---|---:|---:|---:|---:|
| **K0 Total Runtime** | 4.90 s | 25.61 s | 63.38 s | 201.33 s |
| **L1 Total Runtime** | 3.30 s | 18.30 s | 53.70 s | 160.23 s |
| **Runtime Delta (%)** | **-32.56%** | **-28.54%** | **-15.27%** | **-20.41%** |
| **Absolute Time Saved** | 1.60 s | 7.31 s | 9.68 s | **41.10 s** |
| **K0 Total Nodes** | 25,347 | 182,087 | 405,197 | 1,251,786 |
| **L1 Total Nodes** | 25,347 | 180,924 | 407,705 | 1,252,292 |
| **Node Count Delta (%)** | **+0.00%** | -0.64% | +0.62% | **+0.04%** |
| **K0 Effective NPS** | 5,174 | 7,110 | 6,393 | 6,217 |
| **L1 Effective NPS** | 7,672 | 9,886 | 7,591 | **7,815** |
| **NPS Throughput Gain** | **+48.3%** | **+39.0%** | **+18.7%** | **+25.7%** |
| **L1 Lazy Sorts Avoided** | 1 | 1,491 | 2,969 | **14,510** |
| **Move Agreement** | 37 / 37 (100.0%) | 36 / 37 (97.3%) | 36 / 37 (97.3%) | 35 / 37 (94.6%) |
| **Score Agreement** | 37 / 37 (100.0%) | 37 / 37 (100.0%) | 35 / 37 (94.6%) | 36 / 37 (97.3%) |

## 3. Position-Category Breakdown at Depth 5

The 37 diagnostic positions comprise Tactical, Quiet Positional, and Endgame categories.

| Category | Positions | K0 Time (s) | L1 Time (s) | Time Delta (%) | Lazy Sorts Saved | Mean First-Move Cutoff Rate |
|---|---:|---:|---:|---:|---:|---:|
| **Tactical** | 15 | 86.42 | 68.11 | **-21.19%** | 6,842 | 84.6% |
| **Endgame** | 10 | 48.15 | 37.94 | **-21.20%** | 4,218 | 79.2% |
| **Quiet Positional** | 12 | 66.76 | 54.18 | **-18.84%** | 3,450 | 62.4% |
| **Total** | **37** | **201.33** | **160.23** | **-20.41%** | **14,510** | **75.79%** |

## 4. Key Empirical Findings

1. **Confirmation of Hypothesis H1:** Replacing eager sorting with lazy selection avoids scoring and sorting unsearched move tails. At depth 5, Candidate L1 saved **14,510 full sorting operations**, yielding a net **20.41% wall-clock search speedup** and raising search throughput from 6,217 NPS to 7,815 NPS (+25.7%).
2. **Category Sensitivity (Hypothesis H2):** In positions with high first-move cutoff rates (tactical and endgame positions with ~80–85% first-move cutoffs), lazy selection produced over 21% runtime reduction. In quiet positional positions with lower first-move cutoff rates (~62%), runtime was reduced by 18.84%.
3. **Decision Stability:** Across all 37 positions at depth 5, 94.6% of selected best moves and 97.3% of search root scores were identical, demonstrating that lazy move selection retains high search fidelity while eliminating unnecessary overhead.

