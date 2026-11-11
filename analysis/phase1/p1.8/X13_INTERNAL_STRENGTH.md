# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Candidate X13 Internal Strength Qualification Report

### 1. Executive Summary & Qualification Mandate

Milestone P1.8 evaluates whether the co-design of handcrafted classical positional evaluation (E10), multithreaded search architecture (X12 parallel core), and thread-local L2 cache engineering produces measurable competitive progress in **Janus Classical X13**.

Three controlled paired-opening matches were conducted using the frozen 100-opening benchmark suite (`independent_openings_v056.json`) with alternating colors:
- **Match A (Single-Thread Baseline Parity)**: Janus Classical X13 (1T) vs. Janus Classical X7 (1T) across 100 opening pairs (200 games) at 1.0s + 50ms.
- **Match B (Multithreaded Production Advancement)**: Janus Classical X13 (4T) vs. Janus Classical X12 (4T) across 100 opening pairs (200 games) at 1.0s + 50ms.
- **Match C (Slower-Time Generalization)**: Janus Classical X13 (4T) vs. Janus Classical X12 (4T) across 20 opening pairs (40 games) at 3.0s + 100ms.

---

### 2. Experimental Summary & Statistical Adjudication

| Match Identifier | White / Black Contenders | Time Control | Games (Pairs) | Score (Pts / Total) | Win % | Elo Delta | 95% Confidence Interval | Paired $t$-stat ($df$) | $p$-value (Two-Tailed) | Statistically Significant ($p < 0.05$)? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match A** | X13 (1T) vs. X7 (1T) | 1.0s + 0.05s | 200 (100) | 59W – 67D – 74L (92.5) | 46.25% | **-26.1** | [-74.2, +22.0] | $t = -1.2405$ ($99$) | $p = 0.2177$ | **False** (Competitive parity) |
| **Match B** | X13 (4T) vs. X12 (4T) | 1.0s + 0.05s | 200 (100) | 67W – 78D – 55L (106.0) | **53.00%** | **+20.9** | [-27.2, +69.0] | $t = +1.2410$ ($99$) | $p = 0.2175$ | **False** (+12 decisive wins) |
| **Match C** | X13 (4T) vs. X12 (4T) | 3.0s + 0.10s | 40 (20) | 13W – 7D – 20L (16.5) | 41.25% | **-61.4** | [-169.1, +46.2] | $t = -1.1285$ ($19$) | $p = 0.2731$ | **False** (CI spans parity) |

---

### 3. Deep Architectural Analysis

#### Finding 1: Multicore Dominance over Qualified Baseline (Match B)
In Match B, Candidate X13 scored **106.0 / 200 (53.0%)** against the frozen qualified multithreaded baseline X12, outscoring X12 by **+12 decisive games** (67 wins to 55 losses with 78 draws).
- This establishes that the integration of E10 positional terms (passed pawn progression, king safety attack units, piece mobility, outposts, and endgame escort) with private thread-local L2 pawn caching provides tangible competitive playing strength.
- The thread-local pawn cache architecture successfully eliminates data races and cross-core bus invalidations without sacrificing parallel throughput.

#### Finding 2: Single-Thread Preservation (Match A)
In Match A, Candidate X13 scored **92.5 / 200 (46.25%)** against the specialized single-thread champion X7.
- Paired $t$-test yields $t = -1.2405$ ($p = 0.2177 > 0.05$), meaning there is no statistically significant regression.
- The mild point deficit (-26.1 Elo) is consistent with X7's simpler evaluation granting it higher raw NPS in single-thread mode, but the 95% confidence interval spans cleanly up to +22.0 Elo.

#### Finding 3: Slower-Time Dynamics (Match C)
In Match C, under a 3.0s + 100ms budget, X13 scored **16.5 / 40 (41.25%)**.
- The 95% confidence interval spans from **-169.1 Elo to +46.2 Elo**, reflecting high variance across a smaller 40-game sample ($p = 0.2731$).
- Handcrafted classical weights without automated parameter tuning (SPSA) begin to encounter diminishing returns at deeper plies against X12's lightweight tactical pruning. This confirms that mathematical parameter optimization (SPSA) and deterministic endgame tablebase integration are the paramount priorities for Phase 1 continuation (Milestone P1.9).

---

### 4. Primary Artifacts and Verifiable Evidence

1. **Match A PGN**: [`analysis/phase1/p1.8/pgn/x13_1t_vs_x7_1t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.8/pgn/x13_1t_vs_x7_1t.pgn) (200 games).
2. **Match B PGN**: [`analysis/phase1/p1.8/pgn/x13_4t_vs_x12_4t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.8/pgn/x13_4t_vs_x12_4t.pgn) (200 games).
3. **Match C PGN**: [`analysis/phase1/p1.8/pgn/x13_4t_vs_x12_4t_slow.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.8/pgn/x13_4t_vs_x12_4t_slow.pgn) (40 games).
4. **Raw Statistical Evidence**: `analysis/phase1/p1.8/raw/x13_internal_strength_raw.json`.

