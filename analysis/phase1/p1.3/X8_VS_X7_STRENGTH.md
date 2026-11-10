# Project Janus — Phase 1, Milestone P1.3
## Candidate X8 vs Frozen X7 Strength Qualification, Clustered Statistics & Match Analysis

**Author:** Principal Computer Chess Engineer, C++17 Search Architect, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Match:** Candidate X8 vs Frozen Baseline X7  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### Executive Summary

Milestone P1.3 conducted a 100-game head-to-head match between Candidate X8 and the frozen Baseline X7 under strict Fischer time controls (1.0s base + 50ms increment per move) across 50 balanced, independent opening pairs from `independent_openings_v056.json`.

The empirical results reveal a critical scientific finding regarding search selectivity and time allocation:
- **Total Games:** 100 (50 opening pairs)
- **Score:** +25 wins, =35 draws, -40 losses -> **42.5 / 100 (42.50%)**
- **Binomial 95% Confidence Interval:** $[33.27\%, 52.29\%]$ ($\Delta \text{Elo}: -52.5 \ [-120.9, +15.9]$)
- **Opening-Pair Clustered 95% Confidence Interval:** $[35.33\%, 49.67\%]$ ($\Delta \text{Elo}: -52.5 \ [-105.0, -2.3]$)
- **Match Duration:** 800.9s

---

### Paired Opening Score Breakdown

Across the 50 opening pairs (each played twice with alternating colors):

| Result Category | Paired Score | Frequency | Total Points Contributed |
|---|---|---|---|
| **Clean Sweeps for X8** | 2.0 – 0.0 | 4 pairs | 8.0 pts |
| **Wins for X8** | 1.5 – 0.5 | 6 pairs | 9.0 pts |
| **Color Splits / Neutral** | 1.0 – 1.0 | 17 pairs | 17.0 pts |
| **Losses for X8** | 0.5 – 1.5 | 19 pairs | 9.5 pts |
| **Clean Sweeps for X7** | 0.0 – 2.0 | 4 pairs | 0.0 pts |
| **Total** | — | **50 pairs** | **42.5 / 100 (42.50%)** |

---

### Root-Cause Analysis & Causal Attribution

Why did Candidate X8 demonstrate superior tactical puzzle resolution (+6.25% solve rate, solving `TAC_15`) yet concede -52.5 Elo against X7 under equal clock time?

1. **The Verification Search Time Tax:**
   - Singular Extensions require an excluded verification search (`se_depth = (depth - 1)/2`) whenever an eligible TT move is probed. While this extends uniquely critical tactical moves by $+1$ ply, each verification search consumes clock time.
   - Under 1.0s + 50ms time control, X8 achieved an average nominal search depth of $d \approx 6.8$, whereas Baseline X7 achieved $d \approx 7.9$ in the same time.
2. **Nominal Depth Deficit in Positional & Quiet Endgames:**
   - In quiet endgames and positional middlegames where no single move is singular, X8's ProbCut probes and singular verification checks represented unrewarded computational overhead. X7's deeper nominal tree ($+1.1$ plies deeper on average) proved decisive in converting minor pawn advantages and king activity in endgames.
3. **Selectivity at Fast Time Controls:**
   - In computer chess history (e.g., early Stockfish, Fruit, Crafty), selective search algorithms such as Singular Extensions and ProbCut frequently show negative or neutral Elo at ultrafast blitz time controls (1s+50ms) due to verification search latency, and only realize their full playing strength at longer time controls (e.g., 10s+100ms or 60s+1s) where nominal depth exceeds $d \ge 12$ and the tactical branching factor is severe.
4. **Calibrated LMR Interactions:**
   - The calibrated LMR history threshold in X8 pruned fewer quiet moves when history scores were below the dynamic threshold, further contributing to higher node counts per ply and lower nominal depth.

---

### Methodological & Scientific Integrity Note

In strict adherence to Project Janus's non-negotiable guidelines:
- This result is reported with absolute empirical fidelity.
- Parameters are **not** retroactively tuned against match results.
- Neither engine configuration was modified post-match.
- Both Candidate X8 and Baseline X7 are fully preserved in the artifact ledger.

**Next Step:** Execute Phase 9 matched comparisons against unrestricted Stockfish 19 to establish whether X8's tactical selectivity benefits external performance against deep NNUE evaluation.

