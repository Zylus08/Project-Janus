# PROJECT JANUS v0.53 — TACTICAL SAFETY & DIFFERENTIAL BENCHMARK REPORT

**Phase:** Phase 5 — Tactical Safety & Differential Benchmark  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N4 (C++17, LMR enabled, PVS enabled)  
**Baseline Engine:** Janus Native N3 (C++17, LMR enabled, PVS disabled)  
**External Diagnostic Reference:** Stockfish 19 (`45bc8e4969...`)  
**Search Conditions:** Fixed Depth 5, Single Thread, Clean TT per position  

---

## 1. Executive Summary

Phase 5 evaluated the tactical preservation and differential move stability of Principal Variation Search (PVS) implemented in Native N4 compared against the frozen production baseline Native N3.

Testing encompassed **48 benchmark positions** across three distinct suites:
1. **Tactical Regression Suite (12 positions):** Inherited from v0.51 and v0.52 to ensure known tactical patterns remain preserved.
2. **Validation Suite (16 positions):** The standardized middlegame and endgame diagnostic corpus.
3. **Independent Tactical Suite v0.53 (20 positions):** A newly curated, non-overlapping corpus covering forks, pins, skewers, deflections, overloaded defenders, back-rank weaknesses, and tactical endgames.

### Key Results:
- **Move Agreement:** **48 / 48 positions (100.0%)** exact move agreement between N4 and N3.
- **Tactical Regressions:** **0 regressions**. Every position solved by N3 was solved identically by N4.
- **Tactical Performance:** 16 / 48 (33.3%) solved at fixed depth 5 by both engines (limited by 5-ply horizon for deep combinations).
- **Search Effort:** Overall node count decreased by **8.20%** across the 48 positions (1,233,953 nodes in N4 vs. 1,344,208 nodes in N3).
- **PVS Re-Search Efficiency:** Null-window searches successfully failed low in over 99% of cases; PVS re-search rate was under 0.5%, demonstrating that move ordering is sufficiently effective to prevent speculative search blowups.

---

## 2. Benchmark Corpus Breakdown

| Corpus Suite | Positions | N3 Solved | N4 Solved | Dropped Solutions | Agreement | N3 Nodes | N4 Nodes | Node Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tactical Regression** | 12 | 4 | 4 | 0 | 12 / 12 (100%) | 373,611 | 330,023 | -11.67% |
| **Validation Suite** | 16 | 3 | 3 | 0 | 16 / 16 (100%) | 450,576 | 403,828 | -10.38% |
| **Independent Tactical** | 20 | 9 | 9 | 0 | 20 / 20 (100%) | 520,021 | 500,102 | -3.83% |
| **Total / Aggregate** | **48** | **16** | **16** | **0** | **48 / 48 (100%)** | **1,344,208** | **1,233,953** | **-8.20%** |

---

## 3. Detailed Results by Corpus

### 3.1 Tactical Regression Suite (12 Positions)

| ID | Theme | Best Move (N3 / N4) | Solved? | Agreement | N3 Nodes | N4 Nodes | Delta (%) | PVS Re-searches |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `tac_01_mate_in_2` | Forced mate | `d5f6` / `d5f6` | Yes | Agreed | 44,765 | 40,635 | -9.23% | 8 |
| `tac_02_hanging_piece` | Hanging piece | `d1d5` / `d1d5` | Yes | Agreed | 27,249 | 24,057 | -11.71% | 15 |
| `tac_03_knight_fork` | Royal fork | `d4f5` / `d4f5` | No | Agreed | 34,923 | 30,591 | -12.40% | 19 |
| `tac_04_back_rank` | Back rank | `a2a3` / `a2a3` | No | Agreed | 34,228 | 31,525 | -7.90% | 23 |
| `tac_05_pin_exploit` | Absolute pin | `f3e5` / `f3e5` | Yes | Agreed | 43,158 | 38,710 | -10.31% | 29 |
| `tac_06_skewer` | Skewer | `a1d1` / `a1d1` | No | Agreed | 37,185 | 32,842 | -11.68% | 27 |
| `tac_07_deflection` | Deflection | `a2a3` / `a2a3` | No | Agreed | 24,204 | 22,060 | -8.86% | 10 |
| `tac_08_overload` | Overloaded defender | `f3e5` / `f3e5` | No | Agreed | 29,885 | 26,118 | -12.61% | 15 |
| `tac_09_discovered_check` | Discovered attack | `e4f6` / `e4f6` | No | Agreed | 31,102 | 27,654 | -11.09% | 18 |
| `tac_10_clearance` | Clearance | `d2d4` / `d2d4` | Yes | Agreed | 28,495 | 24,198 | -15.08% | 12 |
| `tac_11_smothered_mate` | Smothered mate | `f3g5` / `f3g5` | No | Agreed | 22,126 | 18,924 | -14.47% | 6 |
| `tac_12_perpetual_defense` | Perpetual check | `e1d1` / `e1d1` | No | Agreed | 16,291 | 12,709 | -21.99% | 4 |

### 3.2 Validation Suite (16 Positions)

All 16 validation positions produced identical moves between N3 and N4:
- In all 16 positions, node counts decreased uniformly by between 5.8% and 18.2%.
- The mean node reduction was 10.38%.
- Neither engine exhibited move flapping or evaluation inversion.

### 3.3 Independent Tactical Suite v0.53 (20 Positions)

The 20 independent tactical positions confirmed:
- Solved rate: 9 / 20 (45.0%) at Depth 5 for both N3 and N4.
- Exact agreement: 20 / 20 (100.0%).
- Node reduction: 3.83% average reduction. Certain sharp tactical trees required PVS re-searches on tactical cutoffs, which appropriately validated that the re-search mechanism correctly triggers and updates the alpha bound.

---

## 4. Search Mechanism Telemetry

Across all 48 test positions, telemetry recorded:
1. **Full-Window Searches:** Dropped by over 77% compared to standard alpha-beta, confirming that after the PV move is searched, virtually all subsequent moves are probed with $[-\alpha - 1, -\alpha]$.
2. **Null-Window Cutoffs:** Over 99% of null-window searches terminated with $score \le \alpha$, proving that the move ordering heuristics (TT move, captures via MVV-LVA, killers, and history) reliably place the best moves first.
3. **PVS Re-Searches:** Occurred on less than 0.5% of searched nodes. When a re-search did trigger, it traversed the full window $[-\beta, -\alpha]$ without state corruption or TT table pollution.

---

## 5. Gate 5 Verification & Disposition

- [x] **Zero dropped tactical solutions:** 16 solved by N3 $\rightarrow$ 16 solved by N4.
- [x] **100% move agreement:** 48/48 across all three corpora.
- [x] **Positive search efficiency:** 8.20% overall node reduction at nominal depth 5.
- [x] **Zero crashes, hangs, or assertion failures.**

**Disposition:** Gate 5 is **PASSED** with zero defects. Proceed to Phase 6 (Fixed-Depth PVS Ablation).

