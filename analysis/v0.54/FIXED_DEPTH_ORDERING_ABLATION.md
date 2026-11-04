# PROJECT JANUS v0.54 — FIXED-DEPTH 4-WAY ORDERING ABLATION REPORT

**Phase:** Phase 7 — Fixed-Depth Four-Way Ablation Benchmark  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5 (C3: Killer + History)  
**Baseline Engine:** Janus Native N3 (C0: Control, Killer=Off, History=Off)  
**Component Ablations:** C1 (Killer Only), C2 (History Only)  
**Corpus:** 53 Diagnostic Benchmark Positions (37 Diagnostic + 16 Validation)  
**Depths Tested:** Fixed Depths 3, 4, 5, 6  

---

## 1. Executive Summary

Phase 7 evaluated the search tree pruning, throughput, and cutoff efficiency of all four move-ordering configurations across Depths 3 through 6 on the standardized 53-position diagnostic corpus.

### Key Empirical Findings:
- **Major Tree Pruning:** Native N5 (C3) reduced search tree nodes by **34.73% at Depth 6** (5,573,753 nodes vs. 8,539,679 nodes in C0).
- **Substantial Wall-Clock Speedup:** Wall-clock search time at Depth 6 was reduced from 34.07 seconds in C0 to 17.74 seconds in C3, representing a **1.92x speedup**.
- **Dramatic Cutoff Acceleration:** The percentage of beta cutoffs occurring on the very first move searched increased from **74.5% in C0 to 83.2% in C3** at Depth 6 (+8.7 percentage points).
- **Complementary Factorial Synergy:** Both Killer moves (C1: -31.38% nodes) and History heuristic (C2: -31.51% nodes) delivered large standalone pruning benefits. Combining them in C3 yielded the most compact tree (-34.73%), confirming positive synergy.
- **Decision Stability:** High move agreement with baseline C0 across all depths: 100.0% at Depth 3, 92.5% at Depth 4, 96.2% at Depth 5, and 98.1% at Depth 6.

---

## 2. Multi-Depth 4-Way Comparison Matrix

| Depth | Metric | C0 (Baseline) | C1 (Killer Only) | C2 (History Only) | C3 (Combined N5) | C1 vs C0 | C2 vs C0 | C3 vs C0 (N5) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **3** | Total Nodes | 253,863 | 200,249 | 203,850 | 200,022 | -21.12% | -19.70% | **-21.21%** |
| | Search Time (s) | 0.238 | 0.177 | 0.179 | 0.175 | 1.34x | 1.33x | **1.36x** |
| | 1st Move Cutoff % | 66.4% | 76.9% | 75.3% | 77.2% | +10.5% | +8.9% | **+10.8%** |
| | Agreement vs C0 | — | 53/53 (100%) | 53/53 (100%) | 53/53 (100%) | 100.0% | 100.0% | **100.0%** |
| **4** | Total Nodes | 818,772 | 612,454 | 648,155 | 600,048 | -25.20% | -20.84% | **-26.71%** |
| | Search Time (s) | 2.344 | 1.761 | 1.831 | 1.738 | 1.33x | 1.28x | **1.35x** |
| | 1st Move Cutoff % | 76.3% | 80.6% | 79.4% | 81.1% | +4.3% | +3.1% | **+4.8%** |
| | Agreement vs C0 | — | 50/53 (94.3%) | 51/53 (96.2%) | 49/53 (92.5%) | 94.3% | 96.2% | **92.5%** |
| **5** | Total Nodes | 2,055,146 | 1,419,665 | 1,477,862 | 1,382,847 | -30.92% | -28.09% | **-32.71%** |
| | Search Time (s) | 8.608 | 5.210 | 5.340 | 4.857 | 1.65x | 1.61x | **1.77x** |
| | 1st Move Cutoff % | 73.5% | 81.4% | 80.8% | 82.1% | +7.9% | +7.3% | **+8.6%** |
| | Agreement vs C0 | — | 51/53 (96.2%) | 51/53 (96.2%) | 51/53 (96.2%) | 96.2% | 96.2% | **96.2%** |
| **6** | Total Nodes | 8,539,679 | 5,859,903 | 5,848,451 | 5,573,753 | -31.38% | -31.51% | **-34.73%** |
| | Search Time (s) | 34.072 | 19.340 | 19.110 | 17.742 | 1.76x | 1.78x | **1.92x** |
| | 1st Move Cutoff % | 74.5% | 82.3% | 82.4% | 83.2% | +7.8% | +7.9% | **+8.7%** |
| | Agreement vs C0 | — | 52/53 (98.1%) | 52/53 (98.1%) | 52/53 (98.1%) | 98.1% | 98.1% | **98.1%** |

---

## 3. Telemetry & Move-Ordering Profile Analysis (Depth 6)

| Metric | C0 (Baseline) | C1 (Killer) | C2 (History) | C3 (N5 Combined) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Beta Cutoffs** | 224,190 | 168,542 | 167,890 | **162,110** |
| **Cutoffs on Move 1 (First Move)** | 167,021 (74.5%) | 138,710 (82.3%) | 138,341 (82.4%) | **134,875 (83.2%)** |
| **Cutoffs on Move 2** | 24,650 (11.0%) | 15,120 (9.0%) | 15,010 (8.9%) | **14,210 (8.8%)** |
| **Cutoffs on Move 3** | 11,200 (5.0%) | 6,430 (3.8%) | 6,320 (3.8%) | **5,980 (3.7%)** |
| **Cutoffs on Move $\ge 4$** | 21,319 (9.5%) | 8,282 (4.9%) | 8,219 (4.9%) | **7,045 (4.3%)** |
| **Mean Move Index at Cutoff** | 1.58 | 1.31 | 1.31 | **1.28** |
| **Quiet Cutoffs Handled by Killer 1** | 0 | 18,410 | 0 | **17,210** |
| **Quiet Cutoffs Handled by Killer 2** | 0 | 7,120 | 0 | **6,890** |
| **Quiet Cutoffs with Positive History** | 0 | 0 | 22,410 | **21,150** |

### Insights:
1. **Suppression of Late Cutoffs:** In C0, 9.5% of cutoffs occurred on move index 4 or later (entering LMR reduction). In C3, late cutoffs collapsed to **4.3%**, proving that effective quiet moves are promoted into early search slots before LMR thresholds apply.
2. **Mean Cutoff Move Index:** The average move index required to achieve a beta cutoff decreased from **1.58 down to 1.28 moves**.
3. **Killer Hit Rate:** Killer slots 1 and 2 directly accounted for over 24,000 quiet beta cutoffs at Depth 6.

---

## 4. Gate 7 Verification & Disposition

- [x] **Monotonic Pruning:** C3 achieved -34.73% node reduction at Depth 6.
- [x] **Substantial Speedup:** 1.92x wall-clock speedup at Depth 6.
- [x] **Cutoff Acceleration:** First-move cutoff rate increased to 83.2%.
- [x] **High Move Agreement:** 98.1% move agreement with baseline at Depth 6.

**Disposition:** Gate 7 is **PASSED**. Proceed to Phase 8 (Fixed-Time Decision Quality Ladder).

