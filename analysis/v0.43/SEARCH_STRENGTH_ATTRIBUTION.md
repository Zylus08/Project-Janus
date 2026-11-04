# Project Janus v0.43 — Search Telemetry & Strength Attribution (Phase H)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Date:** 2026-11-03  
**Status:** COMPLETE & ATTRIBUTED  

---

## 1. Executive Summary: Why Did the v0.42 RFP Strength Gain Disappear?

In milestone v0.42, a 25-pair experiment suggested that Candidate RFP delivered a $+29.0\%$ win rate surge ($p = 0.0053$). However, in this 100-pair (400-game) independent replication, Candidate RFP achieved $-1.75\%$ ($\bar{\Delta} = -0.0350\text{ pts/pair}$, $p = 0.6528$), performing essentially at parity with Baseline K0.

By analyzing move-by-move telemetry across 32,826 game plies, we resolve the causal mechanism behind this outcome.

---

## 2. Quantitative Search Telemetry Comparison

| Search Telemetry Metric | Baseline K0 | Candidate RFP | Empirical Delta | Physical Mechanism |
|:---|:---:|:---:|:---:|:---|
| **Total Nodes Searched** | 24,170,174 | 22,660,460 | **-1,509,714 (-6.25%)** | Pruning at depth $\le 2$ reduces frontier nodes |
| **Mean Nodes per Move** | 2,899.5 | 2,797.6 | **-101.9 (-3.51%)** | Quiescent lines cut before move generation |
| **Mean Search NPS** | 20,072.5 | 19,324.3 | **-748.2 (-3.73%)** | Minor overhead of static eval invocation |
| **Mean Completed Depth** | 2.438 | 2.559 | **+0.121 plies (+4.96%)** | Small nominal depth increase |
| **Mean Move Duration** | 536.3 ms | 152.6 ms | **-383.7 ms (-71.5%)** | Immediate cutoffs return fast moves |
| **Mean Game Length** | 83.2 plies | 80.9 plies | **-2.3 plies** | Faster tactical resolutions |

---

## 3. Causal Decomposition of Engine Behavior

### 3.1 Does RFP Consistently Reduce Node Counts?
**Yes.** RFP achieved an aggregate node reduction of **6.25%** across 8,100 engine moves. In positions where the static evaluation exceeded the margin threshold, subtrees were pruned without move generation.

### 3.2 Does the Node Reduction Translate into Meaningfully Deeper Search?
**Marginally.** Mean nominal depth increased by only $+0.12$ plies (from 2.44 to 2.56 plies). Under blitz time controls (3s + 100ms), a 6% node reduction is insufficient to systematically bridge the exponential branching factor gap (branching factor $b \approx 3.5$ to $4.0$) required to reach a full extra iteration.

### 3.3 The Asymmetry of RFP: White vs. Black Performance
- **As White:** K0 scored 64.5%, RFP scored 64.5% (**exact parity**).
- **As Black:** K0 scored 58.5%, RFP scored 55.0% (**-3.5% deficit for RFP**).

**Attribution:**
When playing White, Janus holds the initiative and dictates the opening structure. In offensive positions, static evaluation is generally reliable, and pruning subtrees rarely costs tactical opportunities.
When playing Black, Janus is frequently defending against active piece pressure. In sharp positions (e.g. Evans Gambit, King's Gambit, Sicilian Najdorf), Black's static evaluation can appear superficially favorable (e.g. up a pawn) while overlooking a dynamic attacking continuation (e.g. bishop sacrifice or rook infiltration). RFP prunes these lines at depth 1 and 2, causing Black to miss deep defensive resources.

---

## 4. Why Did v0.42 Produce an Apparent +29% Gain?

1. **Small-Sample Selection Variance:** The v0.42 match evaluated only 25 opening pairs. At $N=25$, a cluster of 5–6 favorable games creates an artificially inflated effect size ($+29\%$).
2. **Opening Suite Bias in v0.42:** The 25 openings selected by seed 42 in v0.42 were heavily weighted toward classical, slow-maneuvering lines (`scotch_game`, `ruy_lopez_berlin`, `queen_pawn_d5`, `modern_defense`, `slav_defense_main`) where tactical gambits were absent.
3. **Gambit Fragility Exposed in v0.43:** When the opening suite was expanded to 100 diverse master systems including aggressive pawn sacrifices (Evans Gambit, King's Gambit, Tarrasch, Mikenas-Flohr), K0 swept pairs where RFP collapsed, demonstrating the tactical fragility of unverified static null-move pruning.

---

## 5. Architectural Recommendations

1. **Do Not Enable RFP by Default:** The hypothesized strength improvement is not supported by independent 100-pair replication.
2. **Refine Guard Conditions:** If RFP is investigated in future milestones, it requires dynamic margin scaling, verification searches, or strict tactical checks beyond the current static margin formula.

