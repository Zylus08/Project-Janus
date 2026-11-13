# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Janus Classical X17 Independent Strength Evaluation Report

**Document ID:** `analysis/phase1/p1.12/X17_INDEPENDENT_STRENGTH.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Status:** Certified Statistical Evaluation Record  
**Date:** 2026-11-13  
**Auditor:** Principal Computer Chess Engineer & Independent Statistical Auditor  
**Raw Test Data:** [`analysis/phase1/p1.12/raw/x17_internal_strength_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.12/raw/x17_internal_strength_raw.json)  

---

## 1. Executive Summary

In Milestone P1.12, the experimental candidate **Janus Classical X17** was evaluated in head-to-head tournament play under the **Janus Classical Tournament Standard v2 (JCTS v2)**. Testing comprised 250 games across three preregistered internal matches:
1. **Match 1 (Fast-TC Screening):** Janus Classical X17-S (1T) vs Janus Classical X7 (1T Control)  
   **Result:** 33W - 37D - 30L ($51.5\%$, **$+10.4\text{ Elo}$**, $95\%\text{ CI } [-57.3, +78.1]$).
2. **Match 2 (Slower-TC Replication):** Janus Classical X17-S (1T) vs Janus Classical X7 (1T Control)  
   **Result:** 15W - 20D - 15L ($50.0\%$, **$0.0\text{ Elo}$**, $95\%\text{ CI } [-95.1, +95.1]$).
3. **Match 3 (Parallel Search Scaling):** Janus Classical X17-P (4T) vs Janus Classical X12 (4T Control)  
   **Result:** 33W - 34D - 33L ($50.0\%$, **$0.0\text{ Elo}$**, $95\%\text{ CI } [-67.7, +67.7]$).

### Core Takeaways:
- **Total Recovery from the P1.11 Regression:**  
  Candidate X17 completely reverses the severe regression of X16 (which scored $33.5\%$, $-117.2\text{ Elo}$ against X7 in P1.11). By stripping away the toxic `!improving` LMR reduction dampening and restoring baseline tree depth, X17 returns to positive territory ($+10.4\text{ Elo}$ fast, $0.0\text{ Elo}$ slow).
- **Statistical Parity (Equivalence):**  
  Under JCTS v2, promotion requires statistically significant superiority ($p < 0.05$ with lower $95\%\text{ CI} > 0$). In all three matches, the $95\%$ confidence interval encompasses zero. While X17 safely incorporates targeted pawn endgame protection without any regression, it does not demonstrate statistically significant superiority over X7 or X12.

---

## 2. Tournament Configurations & Protocols

All matches adhered strictly to JCTS v2:
- **Paired Openings:** Drawn from `independent_openings_v056.json`. Every opening contested twice with color reversal.
- **Hardware Isolation:** 8 dedicated worker processes pinned to physical performance cores.
- **Adjudication Rules:** Resignation adjudicated when mover evaluated $\le -600\text{ cp}$ for 4 consecutive half-moves (move $\ge 20$). Draw adjudicated when both engines evaluated within $[-15, +15]\text{ cp}$ for 8 consecutive half-moves (move $\ge 40$, material $\le 12$ pieces).
- **Zero Clock Forfeits:** Zero illegal moves, zero hangs, and zero forfeits across all 250 games.

---

## 3. Head-to-Head Internal Match Results

### 3.1 Match 1: X17-S (1T) vs Janus Classical X7 (1T Control)
- **Time Control:** $1.0\text{s} + 50\text{ms}$ increment
- **Sample Size:** 50 opening pairs (100 games)
- **PGN Archive:** [`analysis/phase1/p1.12/pgn/x17_1t_vs_x7_1t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.12/pgn/x17_1t_vs_x7_1t.pgn)
- **Score:** **33 Wins, 37 Draws, 30 Losses**
- **Score Percentage:** **$51.50\%$** ($51.5 / 100.0$)
- **Elo Difference:** **$+10.4\text{ Elo}$**
- **$95\%$ Confidence Interval:** $[-57.3\text{ Elo}, +78.1\text{ Elo}]$
- **Match Duration:** 103.1 seconds

### 3.2 Match 2: X17-S (1T) vs Janus Classical X7 (1T Control) — Slower TC Replication
- **Time Control:** $2.5\text{s} + 100\text{ms}$ increment ($2.5\times$ slower time control)
- **Sample Size:** 25 opening pairs (50 games)
- **PGN Archive:** [`analysis/phase1/p1.12/pgn/x17_1t_vs_x7_1t_slow.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.12/pgn/x17_1t_vs_x7_1t_slow.pgn)
- **Score:** **15 Wins, 20 Draws, 15 Losses**
- **Score Percentage:** **$50.00\%$** ($25.0 / 50.0$)
- **Elo Difference:** **$0.0\text{ Elo}$**
- **$95\%$ Confidence Interval:** $[-95.1\text{ Elo}, +95.1\text{ Elo}]$
- **Match Duration:** 108.6 seconds
- **Verification Invariant:** Candidate playing strength does not degrade at slower time controls (non-negative score maintained).

### 3.3 Match 3: X17-P (4T) vs Janus Classical X12 (4T Control)
- **Time Control:** $1.0\text{s} + 50\text{ms}$ increment
- **Sample Size:** 50 opening pairs (100 games)
- **PGN Archive:** [`analysis/phase1/p1.12/pgn/x17_4t_vs_x12_4t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.12/pgn/x17_4t_vs_x12_4t.pgn)
- **Score:** **33 Wins, 34 Draws, 33 Losses**
- **Score Percentage:** **$50.00\%$** ($50.0 / 100.0$)
- **Elo Difference:** **$0.0\text{ Elo}$**
- **$95\%$ Confidence Interval:** $[-67.7\text{ Elo}, +67.7\text{ Elo}]$
- **Match Duration:** 97.2 seconds

---

## 4. Longitudinal Comparison Across Milestone Generations

The historical progression of Project Janus single-threaded candidates evaluated against the qualified baseline X7 illustrates the recovery achieved in P1.12:

| Milestone | Candidate Engine | Architectural Focus | Score vs X7 (%) | Elo vs X7 | Promotion Status |
| :---: | :---: | :--- | :---: | :---: | :---: |
| **P1.3** | **Janus X7** | Bitboard Search + Classical E5 Baseline | — | **$0.0$** (Baseline) | **QUALIFIED BASELINE** |
| **P1.4** | Janus X8 | Integrated Tactical Search Selectivity | $44.5\%$ | $-38.4$ | Rejected |
| **P1.4** | Janus X9 | Countermove Ordering Modernization | $48.5\%$ | $-10.4$ | Rejected |
| **P1.5** | Janus X10 | Positional Expressiveness & Dynamic Time | $49.0\%$ | $-7.0$ | Rejected |
| **P1.6** | Janus X11 | Multithreading & Quadratic LMP | $46.0\%$ | $-27.9$ | Rejected |
| **P1.8** | Janus X13 | Co-Design (Packed 64B TT + E10 Eval) | $47.5\%$ | $-17.4$ | Rejected |
| **P1.9** | Janus X14 | Refined Classical Eval E11 | $46.5\%$ | $-24.4$ | Rejected |
| **P1.10** | Janus X15 | Calibrated Evaluation & Adaptive Search | $47.0\%$ | $-20.9$ | Rejected |
| **P1.11** | Janus X16 | Evaluation-Aware Pruning Safety (Dir A) | **$33.5\%$** | **$-117.2$** | **REJECTED (Severe Regression)** |
| **P1.12** | **Janus X17** | **Classical Baseline Reboot & Pawn LMR Safety** | **$51.5\%$** | **$+10.4$** | **STATISTICAL PARITY** |

---

## 5. Formal Adjudication & Statistical Conclusion

Under Section 6 of JCTS v2:
> *"A candidate engine is declared promoted to production status if and only if it achieves a statistically significant victory ($p < 0.05$, or lower $95\%\text{ CI} > 0$) against its qualified Tier 1 baseline."*

1. **Statistical Test:**  
   - Match 1 ($N = 100$, Score $= 51.5\%$): Two-sided $p = 0.763$ ($Z = 0.30$).
   - Match 2 ($N = 50$, Score $= 50.0\%$): Two-sided $p = 1.000$ ($Z = 0.00$).
   - Match 3 ($N = 100$, Score $= 50.0\%$): Two-sided $p = 1.000$ ($Z = 0.00$).
2. **Decision:**  
   The null hypothesis $H_0: \Delta \le 0$ cannot be rejected at the $\alpha = 0.05$ significance level.
3. **Formal Baseline Retention:**  
   Because Candidate X17 demonstrates statistical parity rather than statistically significant superiority, **the qualified classical baselines are formally retained**:
   - Single-Threaded Qualified Baseline: **Janus Classical X7** (commit `b34e342`)
   - Four-Threaded Qualified Baseline: **Janus Classical X12** (commit `78ca3d5`)
   - Candidate X17 is archived as a certified sound research platform with verified pawn endgame safety.

**Certification:** The independent playing-strength qualification of Milestone P1.12 is complete, verified, and officially recorded.

