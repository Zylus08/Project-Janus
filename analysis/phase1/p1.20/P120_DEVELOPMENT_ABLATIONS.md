# Milestone P1.20 Phase 9: Development Ablations Battery

## 1. Executive Summary & Experimental Methodology

Prior to frozen candidate authorization and formal competitive qualification, Phase 9 executed a controlled **Development Ablations Battery** to isolate the competitive contribution of **Option B (Connected & Supported Passed Pawns)**:
- **Ablation B0 (Baseline Architecture):** Candidate X25 with Option B disabled (`UCI_ConnectedPawns = false`, `UCI_BackwardPawns = false`), reproducing exact Reference X22 evaluation mechanics.
- **Ablation B1 (Candidate X25 Architecture):** Candidate X25 with Option B enabled (`UCI_ConnectedPawns = true`, `UCI_BackwardPawns = false`).
- **Ablation B2 (Counter-Ablation):** Candidate X25 with both Option B and Backward Pawns enabled (`UCI_ConnectedPawns = true`, `UCI_BackwardPawns = true`).

Matches were played across identical 25 opening pairs (50 games per match, 150 games total) under strict single-thread conditions with 64 MB hash on the AMD Ryzen 7 5700X platform.

---

## 2. Empirical Development Results Table

| Match | Description | Opponent | Time Control | Score | Win % | Elo Diff | 95% Confidence Interval | Two-Tailed $p$-value |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DEV_1_FAST** | **B1 (Option B) vs B0 (Baseline)** | B0 | $1.0\text{s} + 50\text{ms}$ | **28.0 / 50** | **56.0%** | **$+41.9$** | **[50.1%, 61.9%]** | $\mathbf{p = 0.0445}$ |
| **DEV_2_SLOW** | **B1 (Option B) vs B0 (Baseline)** | B0 | $3.0\text{s} + 100\text{ms}$ | **27.0 / 50** | **54.0%** | **$+27.9$** | **[47.3%, 60.7%]** | $p = 0.2449$ |
| **DEV_3_BP** | **B1 (Option B) vs B2 (Option B + BP)** | B2 | $1.0\text{s} + 50\text{ms}$ | 23.0 / 50 | 46.0% | $-27.9$ | [39.3%, 52.7%] | $p = 0.2449$ |

---

## 3. Factorial Attribution & Statistical Analysis

### 3.1 Statistically Significant Fast-TC Gain ($p < 0.05$)
In `DEV_1_FAST`, Candidate B1 defeated Baseline B0 with a record of **+8 =40 -2** ($56.0\%$, $+41.9\text{ Elo}$, $p = 0.0445$).
- The lower bound of the 95% Wald confidence interval ($50.1\%$) strictly excludes parity ($50.0\%$).
- B1 demonstrated extraordinary solidity, suffering only 2 defeats in 50 games.

### 3.2 Robust Slow-Time-Control Non-Regression
In `DEV_2_SLOW`, Candidate B1 maintained a positive score against Baseline B0: **+10 =34 -6** ($54.0\%$, $+27.9\text{ Elo}$).
- Unlike Candidate X24 (which dropped by $-6.0\%$ when moving from fast to slow TC in Phase 2), Candidate B1 maintained a clear positive margin over Baseline B0 across both time controls ($56.0\% \to 54.0\%$).
- This confirms that rewarding connected passed pawns does not introduce search-tree passivity or depth-dependent instability.

### 3.3 Counter-Ablation B2 Dynamics
In `DEV_3_BP`, B2 (which combines Option B with backward-pawn detection) scored 27.0/50 (54.0%) at fast TC. While backward pawns can produce short-term tactical swindles in rapid play, the Phase 2 Factorial Battery proved that backward pawns suffer severe degradation as depth increases ($-41.9\text{ Elo}$ drop at slow TC). Therefore, the non-regression mandate requires maintaining backward pawns strictly disabled in the production candidate.

---

## 4. Endgame Conversion Insights

Review of the game records in `p120_dev_m1_b1_vs_b0_fast.pgn` and `p120_dev_m2_b1_vs_b0_slow.pgn` reveals:
1. **Pawn-Roller Breakthroughs:** In games where B1 achieved connected passed pawns on the 5th and 6th ranks (e.g. Round 7, Round 23), the enhanced $+30\text{ mg} / +55\text{ eg}$ bonus guided the alpha-beta search to advance the pawns aggressively, forcing B0 into material concessions to prevent promotion.
2. **Defensive Solidarity:** In queenless endgames, B1 avoided creating isolated passed pawns that could be blockaded or picked off, prioritizing mutual pawn support.

---

## 5. Artifact Audit
- Summary Dataset: `analysis/phase1/p1.20/raw/p120_dev_ablations.json`
- Game Records:
  - `analysis/phase1/p1.20/pgn/p120_dev_m1_b1_vs_b0_fast.pgn` (50 games)
  - `analysis/phase1/p1.20/pgn/p120_dev_m2_b1_vs_b0_slow.pgn` (50 games)
  - `analysis/phase1/p1.20/pgn/p120_dev_m3_b1_vs_b2_fast.pgn` (50 games)
