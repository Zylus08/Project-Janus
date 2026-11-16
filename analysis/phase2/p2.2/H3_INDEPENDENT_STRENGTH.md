# Project Janus — Phase 2, Milestone P2.2
## Phase 13: Independent Strength Qualification & Baseline Audit

**Author:** Principal Computer Chess Architect & Tournament Integrity Auditor  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Tournament Integrity, Baseline Relationships & Conditional Evaluation  

---

### 1. Executive Summary

Phase 13 documents the independent playing-strength relationships established in Milestone P2.2.
Because Candidate H3 training was deferred to Milestone P2.3 in strict compliance with the evidence-driven charter, tournament play during P2.2 focused on the **critical baseline qualification match**:
$$\textbf{Janus Hybrid H2 vs Janus Classical R1.0 (50 Games)}$$
to definitively resolve whether hybrid evaluation represents an improvement over classical evaluation.

---

### 2. Empirical Tournament Qualification Battery (P2.2)

```
========================================================================================================================
TOURNAMENT BATTERY RESULTS SUMMARY (P2.2)
========================================================================================================================
Match Comparison                | TC           | Games | Pts   | Score  | Elo    | Paired 95% CI  | Pentanomial (LL..WW)
--------------------------------+--------------+-------+-------+--------+--------+----------------+---------------------
H2 (Hybrid) vs R1 (Classical)   | 5.0s + 0.05s | 50    | 4.0   | 8.0%   | -424.3 | [3.3%, 12.7%]  | [17, 8, 0, 0, 0]
========================================================================================================================
Total Games: 50 | Crashes: 0 | Illegal Moves: 0 | Time Forfeits: 0 | PGN: analysis/phase2/p2.2/raw/match_h2_vs_r1.pgn
```

#### Detailed Statistical Findings
- **Score:** 4.0 / 50 (+0 =8 -42) for Hybrid H2.
- **Pentanomial Breakdown:**
  - 17 Double-Losses (LL): Both games in the opening pair lost by H2.
  - 8 Loss-Draws (LD): H2 held a draw in one game and lost the other.
  - 0 Draw-Draws (DD), 0 Win-Losses (WL), 0 Win-Draws (WD), 0 Double-Wins (WW).
- **Two-Tailed p-value:** $p = 0.0000$ ($p < 10^{-4}$), confirming that Classical R1's superiority over Hybrid H2 is statistically irrefutable.

---

### 3. Comprehensive Phase 2 Empirical Landscape

Combining the P2.1 and P2.2 tournament batteries (500 total games):

```
                       +-----------------------------+
                       |    Janus Classical R1.0     |
                       |    (100% Strength Anchor)   |
                       +-----------------------------+
                                      |
                     +424 Elo         |         +727 Elo
                   (92.0% score)      |       (98.5% score)
                                      v
                       +-----------------------------+
                       |       Janus Hybrid H2       |
                       |    (50% Class + 50% H1)     |
                       +-----------------------------+
                                      |
                                      | +798 Elo
                                      | (99.0% score)
                                      v
                       +-----------------------------+
                       |     Janus Hybrid H1         |
                       |    (Pure DP-PS-768 NNUE)    |
                       +-----------------------------+
```

**Key Takeaways:**
1. **Classical R1 remains the undisputed strength control of Project Janus.**
2. Pure H1 is crippled by scale compression, lack of king conditioning, and 6x inference overhead.
3. Hybrid H2 performs well against infant H1 (+798 Elo) only because its 50% classical component prevents outright blunders, but against pure Classical R1, the contaminated neural component degrades performance by $-424\text{ Elo}$.

---

### 4. Qualification Criteria for Milestone P2.3 Strength Benchmarks

When Candidate H3 (HalfKP-40960, $\ge 500\text{k}$ training positions) is evaluated in Milestone P2.3, it will be subjected to the following mandatory strength gates:
- **Gate 1:** H3 (NNUE) vs H1 (Frozen NNUE) — Must demonstrate $\ge 80\%$ win rate.
- **Gate 2:** H3 (Hybrid) vs Classical R1 — Must demonstrate non-inferiority ($> 45\%$ win rate).
- **Gate 3:** H3 (NNUE) vs Classical R1 — Primary milestone advancement hypothesis ($> 50\%$ win rate).
